import json
import os
import urllib.request
import urllib.error

import boto3


ec2 = boto3.client("ec2")
ssm = boto3.client("ssm")
sns = boto3.client("sns")


def handler(event, context):
    message = json.loads(event["Records"][0]["Sns"]["Message"])
    state = message.get("NewStateValue")

    if state == "ALARM":
        return _handle_failover()
    elif state == "OK":
        return _handle_teardown()
    else:
        print(f"Ignoring state: {state}")
        return


def _handle_failover():
    if _find_failover_instance():
        print("Failover instance already running, skipping")
        return

    tailscale_key = _get_ssm_param(os.environ["SSM_TAILSCALE_KEY"])
    discord_webhook = _get_ssm_param(os.environ["SSM_DISCORD_WEBHOOK"])
    tailscale_auth_key = _create_tailscale_auth_key(tailscale_key)

    user_data = _build_user_data(
        tailscale_auth_key=tailscale_auth_key,
        discord_webhook=discord_webhook,
        s3_bucket=os.environ["S3_BACKUP_BUCKET"],
    )

    response = ec2.run_instances(
        LaunchTemplate={"LaunchTemplateId": os.environ["LAUNCH_TEMPLATE_ID"]},
        MinCount=1,
        MaxCount=1,
        UserData=user_data,
    )

    instance_id = response["Instances"][0]["InstanceId"]
    print(f"Launched failover instance: {instance_id}")

    alert_msg = (
        f"[Vaultwarden DR] Failover triggered.\n\n"
        f"The on-prem server has been unreachable for 5+ minutes. "
        f"A failover EC2 instance ({instance_id}) is launching with the latest S3 backup.\n\n"
        f"Once ready, it will be accessible at https://{os.environ['FAILOVER_DOMAIN']}.\n\n"
        f"The instance will be automatically terminated when heartbeat recovers for 10+ minutes."
    )

    _notify_sns("Vaultwarden DR - Failover Triggered", alert_msg)
    _notify_discord(
        discord_webhook,
        f"**[Vaultwarden DR]** Failover triggered. EC2 instance `{instance_id}` is launching with the latest backup.",
    )

    return {"instance_id": instance_id}


def _handle_teardown():
    instance_id = _find_failover_instance()
    if not instance_id:
        print("No failover instance found, nothing to tear down")
        return

    print(f"Terminating failover instance: {instance_id}")
    ec2.terminate_instances(InstanceIds=[instance_id])

    discord_webhook = _get_ssm_param(os.environ["SSM_DISCORD_WEBHOOK"])

    alert_msg = (
        f"[Vaultwarden DR] Recovery detected.\n\n"
        f"The on-prem server has been sending heartbeats for 10+ consecutive minutes. "
        f"Failover instance ({instance_id}) has been terminated automatically."
    )

    _notify_sns("Vaultwarden DR - Recovery Complete", alert_msg)
    _notify_discord(
        discord_webhook,
        f"**[Vaultwarden DR]** Recovery detected. Failover instance `{instance_id}` terminated automatically.",
    )

    return {"terminated_instance": instance_id}


def _find_failover_instance():
    response = ec2.describe_instances(
        Filters=[
            {"Name": "tag:vaultwarden-failover", "Values": ["active"]},
            {"Name": "instance-state-name", "Values": ["pending", "running"]},
        ]
    )
    instances = [
        i for r in response["Reservations"] for i in r["Instances"]
    ]
    return instances[0]["InstanceId"] if instances else None


def _get_ssm_param(name):
    response = ssm.get_parameter(Name=name, WithDecryption=True)
    return response["Parameter"]["Value"]


def _create_tailscale_auth_key(api_key):
    data = json.dumps({
        "capabilities": {
            "devices": {
                "create": {
                    "reusable": False,
                    "ephemeral": True,
                    "tags": ["tag:failover"],
                }
            }
        },
        "expirySeconds": 3600,
    }).encode()

    req = urllib.request.Request(
        "https://api.tailscale.com/api/v2/tailnet/-/keys",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())["key"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Tailscale API error {e.code}: {body}")
        raise


def _build_user_data(tailscale_auth_key, discord_webhook, s3_bucket):
    script = USER_DATA_TEMPLATE.replace("{{TAILSCALE_AUTH_KEY}}", tailscale_auth_key)
    script = script.replace("{{DISCORD_WEBHOOK_URL}}", discord_webhook)
    script = script.replace("{{S3_BACKUP_BUCKET}}", s3_bucket)
    script = script.replace("{{FAILOVER_DOMAIN}}", os.environ["FAILOVER_DOMAIN"])
    script = script.replace("{{NOTIFICATION_EMAIL}}", os.environ["NOTIFICATION_EMAIL"])
    script = script.replace("{{CF_ZONE}}", os.environ["CF_ZONE"])

    import base64
    return base64.b64encode(script.encode()).decode()


USER_DATA_TEMPLATE = r"""#!/bin/bash

TAILSCALE_AUTH_KEY="{{TAILSCALE_AUTH_KEY}}"
DISCORD_WEBHOOK_URL="{{DISCORD_WEBHOOK_URL}}"
S3_BACKUP_BUCKET="{{S3_BACKUP_BUCKET}}"
FAILOVER_DOMAIN="{{FAILOVER_DOMAIN}}"
NOTIFICATION_EMAIL="{{NOTIFICATION_EMAIL}}"

exec > /var/log/user-data.log 2>&1

notify_discord() {
    curl -s -H "Content-Type: application/json" \
        -d "{\"content\": \"$1\"}" \
        "$DISCORD_WEBHOOK_URL" || true
}

on_error() {
    notify_discord "**[Vaultwarden DR]** User-data script FAILED at line $1."
    aws s3 cp /var/log/user-data.log "s3://${S3_BACKUP_BUCKET}/logs/user-data-$(date +%s).log" || true
}
trap 'on_error $LINENO' ERR

set -euo pipefail

apt-get update -y
apt-get install -y docker.io sqlite3 unzip curl nginx

curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
unzip -q /tmp/awscliv2.zip -d /tmp
/tmp/aws/install
rm -rf /tmp/awscliv2.zip /tmp/aws

curl -fsSL https://tailscale.com/install.sh | sh
tailscale up --authkey="$TAILSCALE_AUTH_KEY" --hostname=vaultwarden-failover

systemctl enable docker
systemctl start docker

LATEST_BACKUP=$(aws s3api list-objects-v2 \
    --bucket "$S3_BACKUP_BUCKET" \
    --prefix "vaultwarden_" \
    --query 'sort_by(Contents, &LastModified)[-1].Key' \
    --output text)

if [ -z "$LATEST_BACKUP" ] || [ "$LATEST_BACKUP" = "None" ]; then
    notify_discord "Vaultwarden failover FAILED: no backups found in S3."
    exit 1
fi

mkdir -p /tmp/vaultwarden-restore
aws s3 cp "s3://$S3_BACKUP_BUCKET/$LATEST_BACKUP" /tmp/vaultwarden-restore/backup.tar.gz
tar -xzf /tmp/vaultwarden-restore/backup.tar.gz -C /tmp/vaultwarden-restore

mkdir -p /home/vaultwarden
mv /tmp/vaultwarden-restore/data /home/vaultwarden/data
rm -rf /tmp/vaultwarden-restore

TAILSCALE_IP=$(tailscale ip -4)
IMDS_TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 300")
REGION=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" http://169.254.169.254/latest/meta-data/placement/region)

CF_TOKEN=$(aws ssm get-parameter --name "/vaultwarden-dr/cloudflare-api-token" --with-decryption --region "$REGION" --query 'Parameter.Value' --output text)

CF_ZONE_ID=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones?name={{CF_ZONE}}" \
    -H "Authorization: Bearer $CF_TOKEN" \
    -H "Content-Type: application/json" | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"][0]["id"])')

CF_RECORD=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records?type=A&name=$FAILOVER_DOMAIN" \
    -H "Authorization: Bearer $CF_TOKEN" \
    -H "Content-Type: application/json")

CF_RECORD_ID=$(echo "$CF_RECORD" | python3 -c 'import sys,json; r=json.load(sys.stdin)["result"]; print(r[0]["id"] if r else "")')

if [ -n "$CF_RECORD_ID" ]; then
    curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records/$CF_RECORD_ID" \
        -H "Authorization: Bearer $CF_TOKEN" \
        -H "Content-Type: application/json" \
        --data "{\"type\":\"A\",\"name\":\"$FAILOVER_DOMAIN\",\"content\":\"$TAILSCALE_IP\",\"ttl\":60,\"proxied\":false}"
else
    curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records" \
        -H "Authorization: Bearer $CF_TOKEN" \
        -H "Content-Type: application/json" \
        --data "{\"type\":\"A\",\"name\":\"$FAILOVER_DOMAIN\",\"content\":\"$TAILSCALE_IP\",\"ttl\":60,\"proxied\":false}"
fi

apt-get install -y certbot python3-certbot-dns-cloudflare

mkdir -p /root/.secrets
cat > /root/.secrets/cloudflare.ini <<CFEOF
dns_cloudflare_api_token = $CF_TOKEN
CFEOF
chmod 600 /root/.secrets/cloudflare.ini

certbot certonly \
    --dns-cloudflare \
    --dns-cloudflare-credentials /root/.secrets/cloudflare.ini \
    --dns-cloudflare-propagation-seconds 30 \
    -d "$FAILOVER_DOMAIN" \
    --non-interactive --agree-tos --email "$NOTIFICATION_EMAIL"

rm -rf /root/.secrets

docker run -d \
    --name vaultwarden \
    --restart always \
    -v /home/vaultwarden/data:/data \
    -p 127.0.0.1:8080:80 \
    -e DOMAIN="https://$FAILOVER_DOMAIN" \
    -e SIGNUPS_ALLOWED=false \
    -e INVITATIONS_ALLOWED=false \
    -e SHOW_PASSWORD_HINT=false \
    vaultwarden/server:latest

cat > /etc/nginx/sites-available/vaultwarden <<NGINXEOF
server {
    listen 443 ssl;
    server_name $FAILOVER_DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$FAILOVER_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$FAILOVER_DOMAIN/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    location /notifications/hub {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
NGINXEOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/vaultwarden /etc/nginx/sites-enabled/
systemctl restart nginx

notify_discord "Vaultwarden failover ready at \`https://$FAILOVER_DOMAIN\`. Backup restored: \`$LATEST_BACKUP\`. Tailscale IP: \`$TAILSCALE_IP\`"
"""


def _notify_sns(subject, message):
    sns.publish(
        TopicArn=os.environ["SNS_NOTIFICATIONS_ARN"],
        Subject=subject,
        Message=message,
    )


def _notify_discord(webhook_url, message):
    data = json.dumps({"content": message}).encode()
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "VaultwardenDR/1.0",
        },
    )
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Failed to notify Discord: {e.code} {body}")
    except urllib.error.URLError as e:
        print(f"Failed to notify Discord: {e}")
