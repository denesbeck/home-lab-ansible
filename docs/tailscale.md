# Tailscale Configuration

## Overview

Tailscale provides remote access to the home lab. The server acts as a subnet router, advertising its LAN IP (`192.168.64.15/32`) so remote clients can reach services via their `*.arcade-lab.io` domain names.

## How It Works

1. Pi-hole resolves all `*.arcade-lab.io` subdomains to `192.168.64.15` (LAN IP)
2. The server advertises `192.168.64.15/32` as a subnet route to the Tailnet
3. Remote Tailscale clients query Pi-hole at `100.104.44.113`, get back `192.168.64.15`, and reach it via the subnet route

## ACL Policy

The Tailnet uses tag-based access controls. Tags are assigned to devices in the [Tailscale admin console](https://login.tailscale.com/admin/machines).

### Tags

| Tag | Purpose |
|---|---|
| `tag:server` | The Ubuntu server running all services (Pi-hole, Jellyfin, Grafana, etc.) |
| `tag:trusted` | Personal devices with full access to the server |

### Rules

```json
{
  "action": "accept",
  "src": ["tag:trusted"],
  "dst": ["tag:server:*", "192.168.64.15/32:*"]
}
```

This single rule allows trusted devices to reach the server via both its Tailscale IP and the subnet route, on all ports. All other traffic is denied by default.

### Auto-Approvers

```json
{
  "autoApprovers": {
    "routes": {
      "192.168.64.15/32": ["tag:server"]
    }
  }
}
```

Automatically approves the subnet route when advertised by a `tag:server` node, removing the need to manually approve it in the admin console.

## Ansible Variables (`vars/tailscale.yml`)

| Variable | Description |
|---|---|
| `tailscale_auth_key` | One-time auth key from the [Tailscale admin console](https://login.tailscale.com/admin/settings/keys) |
| `tailscale_advertise_routes` | Subnet route to advertise (currently `192.168.64.15/32`) |

## Manual Steps

After running the playbook for the first time:

1. Tag the server as `tag:server` in the Tailscale admin console
2. Tag your devices as `tag:trusted`
3. Apply the ACL policy above in [Access Controls](https://login.tailscale.com/admin/acls)
4. If not using `autoApprovers`: approve the subnet route under the server's route settings
