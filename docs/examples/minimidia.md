# Minimidia SaaS Infrastructure

Complete production infrastructure for a Node.js SaaS application.

## Overview

This example demonstrates a production-ready deployment including:

- System updates and package management
- Third-party repository setup (NodeSource, Docker)
- Web server (Nginx) with reverse proxy
- Application server (Node.js with systemd)
- TLS certificates (Let's Encrypt)
- Database (SQLite)
- Container platform (Docker)
- Security hardening

## Architecture

```
Internet
   |
   v
[Nginx :80/443] --- TLS Termination
   |
   | Reverse Proxy
   v
[Node.js :3000] --- Application Server
   |
   v
[SQLite] --- Database
```

## Configuration

File: `examples/minimidia.py`

```python
from cook import File, Package, Service, Exec, Repository
import os

DOMAIN = os.getenv("DOMAIN", "minimidia.com")
APP_DIR = "/opt/apps/minimidia"
APP_PORT = 3000

# System updates
Repository("apt-update", action="update")
Repository("apt-upgrade", action="upgrade")

# Add repositories
Repository(
    "nodesource",
    action="add",
    repo="deb https://deb.nodesource.com/node_20.x nodistro main",
    key_url="https://deb.nodesource.com/gpgkey/nodesource.gpg.key"
)

Repository(
    "docker",
    action="add",
    repo="deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable",
    key_url="https://download.docker.com/linux/ubuntu/gpg"
)

Repository("apt-update-post", action="update")

# Install packages
Package("nginx")
Package("nodejs")
Package("certbot", packages=["certbot", "python3-certbot-nginx"])
Package("docker", packages=["docker-ce", "docker-ce-cli", "containerd.io"])
Package("sqlite", packages=["sqlite3", "libsqlite3-dev"])

# Application structure
File(APP_DIR, ensure="directory", mode=0o755)
File(f"{APP_DIR}/data", ensure="directory", mode=0o750, owner="www-data")

# Systemd service
File("/etc/systemd/system/minimidia.service",
     source="./minimidia.service",
     mode=0o644)

Service("minimidia", running=True, enabled=True)

# Nginx configuration
nginx_conf = File(f"/etc/nginx/sites-available/{DOMAIN}",
                  template="./nginx.conf.j2",
                  vars={"domain": DOMAIN, "port": APP_PORT})

Service("nginx", running=True, enabled=True, reload_on=[nginx_conf])

# TLS certificate
Exec("certbot",
     command=f"certbot certonly --nginx -d {DOMAIN} --non-interactive --agree-tos -m admin@{DOMAIN}",
     creates=f"/etc/letsencrypt/live/{DOMAIN}/fullchain.pem")
```

## Deployment

### Prerequisites

- Ubuntu 22.04 or later
- Root access or sudo privileges
- Domain name pointing to server

### Environment Variables

```bash
export DOMAIN=minimidia.com
export ADMIN_EMAIL=admin@minimidia.com
```

### Deploy

```bash
# Plan deployment
sudo cook plan examples/minimidia.py

# Apply configuration
sudo cook apply examples/minimidia.py --yes
```

### Verify

```bash
# Check services
sudo systemctl status minimidia
sudo systemctl status nginx

# Test application
curl https://minimidia.com/health

# View logs
sudo journalctl -u minimidia -f
```

## Multi-Environment Deployment

File: `examples/minimidia-env.py`

Supports development, staging, and production environments:

```bash
# Development
sudo COOK_ENV=development cook apply examples/minimidia-env.py --yes

# Staging
sudo COOK_ENV=staging DOMAIN=staging.minimidia.com cook apply examples/minimidia-env.py --yes

# Production
sudo COOK_ENV=production DOMAIN=minimidia.com cook apply examples/minimidia-env.py --yes
```

### Environment Differences

| Feature | Development | Staging | Production |
|---------|-------------|---------|------------|
| SSL/TLS | Disabled | Let's Encrypt Staging | Let's Encrypt Production |
| Auto-restart | No | Yes | Yes |
| Log level | debug | info | warn |
| Firewall | Optional | Enabled | Enabled |
| Log rotation | 7 days | 14 days | 30 days |

## Components

### Application Server

Node.js application with Express framework:

- Port: 3000 (localhost only)
- Database: SQLite
- User: www-data
- Systemd managed

### Web Server

Nginx reverse proxy:

- HTTP: Redirect to HTTPS
- HTTPS: TLS 1.2+
- Headers: Security headers enabled
- Logs: `/var/log/nginx/`

### Database

SQLite database:

- Location: `/opt/apps/minimidia/data/minimidia.db`
- Owner: www-data
- Backups: Manual (recommended: daily cron)

### TLS Certificates

Let's Encrypt via certbot:

- Auto-renewal: certbot.timer (systemd)
- Certificate: `/etc/letsencrypt/live/{domain}/`
- Renewal: Automatic every 60 days

## Security Features

### Systemd Hardening

```ini
[Service]
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/apps/minimidia/data
```

### Nginx Security Headers

```nginx
add_header Strict-Transport-Security "max-age=31536000";
add_header X-Frame-Options "SAMEORIGIN";
add_header X-Content-Type-Options "nosniff";
```

### Firewall Rules

```python
Exec("ufw-ssh", command="ufw allow 22/tcp")
Exec("ufw-http", command="ufw allow 80/tcp")
Exec("ufw-https", command="ufw allow 443/tcp")
```

## Maintenance

### Update Application

```bash
# Pull latest code
cd /opt/apps/minimidia
git pull

# Install dependencies
npm install --production

# Restart service
sudo systemctl restart minimidia
```

### Check Drift

Detect configuration drift:

```bash
sudo cook check-drift
```

Fix drift:

```bash
sudo cook check-drift --fix
```

### Certificate Renewal

Test renewal:

```bash
sudo certbot renew --dry-run
```

Manual renewal:

```bash
sudo certbot renew
```

### Logs

Application logs:

```bash
sudo journalctl -u minimidia -f
```

Nginx logs:

```bash
sudo tail -f /var/log/nginx/minimidia.com-access.log
sudo tail -f /var/log/nginx/minimidia.com-error.log
```

## Troubleshooting

### Application Won't Start

Check logs:

```bash
sudo journalctl -u minimidia -n 50
```

Check permissions:

```bash
ls -la /opt/apps/minimidia
```

### Nginx 502 Bad Gateway

Verify application is running:

```bash
curl http://127.0.0.1:3000/health
```

Check Nginx config:

```bash
sudo nginx -t
```

### Certificate Issues

Check certificate status:

```bash
sudo certbot certificates
```

Renew manually:

```bash
sudo certbot renew --force-renewal
```

## Reference

- [Repository Resource](../resources/repository.md)
- [Package Resource](../resources/package.md)
- [Service Resource](../resources/service.md)
- [File Resource](../resources/file.md)
- [Exec Resource](../resources/exec.md)
