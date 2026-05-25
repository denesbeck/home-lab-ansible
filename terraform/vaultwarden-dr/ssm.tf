resource "aws_ssm_parameter" "tailscale_api_key" {
  name  = "/vaultwarden-dr/tailscale-api-key"
  type  = "SecureString"
  value = var.tailscale_api_key
}

resource "aws_ssm_parameter" "discord_webhook_url" {
  name  = "/vaultwarden-dr/discord-webhook-url"
  type  = "SecureString"
  value = var.discord_webhook_url
}

resource "aws_ssm_parameter" "cloudflare_api_token" {
  name  = "/vaultwarden-dr/cloudflare-api-token"
  type  = "SecureString"
  value = var.cloudflare_api_token
}
