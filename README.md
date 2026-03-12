# 🧪 home-lab-ansible

Ansible automation for provisioning and configuring a single-node Ubuntu home lab server. Manages Docker containers, networking, storage, security, monitoring, and media services under the `arcade-lab.io` domain.

## Architecture

All services run on a single Ubuntu server. Docker containers are bound exclusively to `127.0.0.1` and exposed through an NGINX reverse proxy with SSL termination. Remote access is provided via Tailscale VPN with subnet routing, and Pi-hole handles local DNS resolution for all subdomains.

```
Internet / Tailscale VPN
         │
    ┌────▼─────┐
    │  NGINX   │  (reverse proxy, SSL)
    │  :80/443 │
    └────┬─────┘
         │  127.0.0.1
         ├──► Pi-hole        (:800)    DNS + ad blocking
         ├──► Portainer      (:9000)   container management
         ├──► Grafana        (:3000)   dashboards
         ├──► Prometheus     (:9090)   metrics
         ├──► Transmission   (:9091)   torrent client
         ├──► Filebrowser    (:8080)   web file manager
         └──► Jellyfin       (:8096)   media server
```

## Services

| Service | Type | Subdomain | Description |
|---|---|---|---|
| **Pi-hole** | Docker | `pi-hole.arcade-lab.io` | DNS server with ad blocking and local DNS records |
| **Portainer** | Docker | `portainer.arcade-lab.io` | Docker container management UI |
| **Grafana** | Docker | `grafana.arcade-lab.io` | Monitoring dashboards |
| **Prometheus** | Docker | `prometheus.arcade-lab.io` | Metrics collection |
| **Transmission** | Docker | `transmission.arcade-lab.io` | BitTorrent client |
| **Filebrowser** | Docker | `filebrowser.arcade-lab.io` | Web-based file manager for movies, photos, and private storage |
| **Jellyfin** | Docker | `jellyfin.arcade-lab.io` | Media server (4GB RAM, 4 CPU limit) |
| **NGINX** | Native | — | Reverse proxy with SSL for all services |
| **Samba** | Native | — | SMB3 file sharing (3 shares: private, photos, movies) |
| **Tailscale** | Native | — | VPN with subnet routing for remote access |
| **UPS Monitor** | Native | — | Router ping-based power outage detection with graceful shutdown |

## Project Structure

```
├── ansible.cfg              # Ansible configuration
├── config/                  # Jinja2 templates
│   ├── cloudflare.ini.j2    # Certbot Cloudflare DNS credentials
│   ├── nginx.conf.j2        # NGINX reverse proxy virtual hosts
│   ├── smb.conf.j2          # Samba shares configuration
│   └── ssh.j2               # Hardened sshd_config
├── docs/                    # Documentation
│   └── tailscale.md         # Tailscale subnet routing architecture
├── inventory/
│   └── hosts.ini            # Single-host inventory
├── playbooks/               # Service playbooks
│   ├── main.yml             # Master orchestrator
│   ├── backup.yml           # Photo backup with rotation + daily restart cron
│   ├── docker.yml           # Docker CE installation
│   ├── filebrowser.yml      # Filebrowser container
│   ├── jellyfin.yml         # Jellyfin media server container
│   ├── monitoring.yml       # Prometheus/Grafana stack
│   ├── nginx.yml            # NGINX reverse proxy + SSL
│   ├── pihole.yml           # Pi-hole DNS container
│   ├── portainer.yml        # Portainer container
│   ├── samba.yml            # Samba file sharing
│   ├── ssh.yml              # SSH hardening
│   ├── tailscale.yml        # Tailscale VPN
│   ├── transmission.yml     # Transmission container
│   ├── ufw.yml              # UFW firewall rules
│   ├── update.yml           # System updates
│   ├── ups-monitor.yml      # UPS power outage monitor
│   └── volumes.yml          # Disk mounts via fstab
├── scripts/
│   └── wait_for_network.sh  # Network readiness check for Docker
├── tasks/                   # Reusable task files
│   ├── generate-password.yml
│   ├── reset-docker.yml
│   ├── restart.yml
│   └── update-packages.yml
└── vars/                    # Variables (gitignored, contains secrets)
    ├── certbot.yml
    ├── filebrowser.yml
    ├── fstab.yml
    ├── jellyfin.yml
    ├── pihole.yml
    ├── portainer.yml
    ├── ssh.yml
    ├── tailscale.yml
    ├── transmission.yml
    └── ups-monitor.yml
```

## Prerequisites

- Ansible installed on the control machine
- SSH access to the target server (public key authentication)
- A `vars/` directory populated with the required variable files (see [Variables](#variables))

## Usage

### Full provisioning

Run the master playbook to provision everything in the correct order:

```bash
ansible-playbook playbooks/main.yml
```

The master playbook executes in this order: system updates, volume mounts, Samba, Docker, NGINX, SSH hardening, UFW firewall, Transmission, Filebrowser, backup, monitoring, and Portainer.

### Individual services

Run any service playbook independently:

```bash
ansible-playbook playbooks/pihole.yml
ansible-playbook playbooks/jellyfin.yml
ansible-playbook playbooks/tailscale.yml
ansible-playbook playbooks/ups-monitor.yml
```

> **Note:** Pi-hole, Jellyfin, Tailscale, and UPS Monitor are not included in `main.yml` and must be run separately.

### Utility tasks

```bash
# Restart the server
ansible-playbook tasks/restart.yml

# Full Docker cleanup (removes all containers, volumes, networks, images)
ansible-playbook tasks/reset-docker.yml
```

## Variables

All variable files live in `vars/` and are gitignored to protect secrets. You need to create these files before running the playbooks:

| File | Required Variables |
|---|---|
| `vars/certbot.yml` | Cloudflare email, API token |
| `vars/fstab.yml` | Disk UUIDs and mount points |
| `vars/ssh.yml` | SSH port, auth settings, timeouts |
| `vars/tailscale.yml` | Auth key, advertised routes |
| `vars/pihole.yml` | DNS config, local DNS records, ports |
| `vars/jellyfin.yml` | Timezone, paths, resource limits |
| `vars/transmission.yml` | Container config, download paths |
| `vars/filebrowser.yml` | Container name, paths |
| `vars/portainer.yml` | Container name, data path |
| `vars/ups-monitor.yml` | Router IP for ping monitoring |

## Security

- **SSH:** Non-standard port, public key authentication only, root login disabled, restricted user access
- **Firewall (UFW):** Default deny incoming; allows only SSH, SMB, HTTP/HTTPS, and Tailscale traffic
- **Containers:** All bound to `127.0.0.1`, accessible only through the NGINX reverse proxy
- **Samba:** SMB3-only, restricted to LAN and Tailscale subnets
- **Remote access:** Tailscale VPN with tag-based ACLs
- **Secrets:** Variable files are gitignored rather than vault-encrypted

## Storage

Four ext4 partitions are mounted via fstab (by UUID):

| Mount Point | Purpose |
|---|---|
| `/mnt/private` | Private files (Samba + Filebrowser) |
| `/mnt/photos` | Photo storage (Samba + Filebrowser + backup source) |
| `/mnt/movies` | Media library (Samba + Filebrowser + Jellyfin + Transmission) |
| `/mnt/backups` | Backup destination (rsync with 3-backup rotation) |

## Backup

A daily cron job (1:00 AM) runs `rsync` to back up `/mnt/photos` to `/mnt/backups` with timestamp-based rotation, keeping the last 3 backups. The server is also configured to restart daily at 3:00 AM.

## Monitoring

The Prometheus and Grafana stack is managed via a separate repository ([home-lab-monitoring](https://github.com/denesbeck/home-lab-monitoring)) which is cloned and started with `docker compose`. The UPS monitor script exports power metrics to Prometheus via the node_exporter textfile collector.
