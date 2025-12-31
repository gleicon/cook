# Minimidia SaaS Infrastructure

Complete production infrastructure configuration for a Node.js SaaS application.

## What's Included

- **Repository Management**: APT updates, NodeSource, Docker repositories
- **Package Installation**: Nginx, Node.js, Certbot, Docker, SQLite
- **Application Setup**: Directory structure, systemd service
- **Reverse Proxy**: Nginx with TLS termination
- **TLS Certificates**: Let's Encrypt automatic SSL
- **Security**: Systemd hardening, firewall rules, security headers
- **Monitoring**: Log rotation, health checks

## Quick Start

```bash
# Set environment variables
export DOMAIN=minimidia.com
export ADMIN_EMAIL=admin@minimidia.com

# Plan deployment
sudo cook plan examples/minimidia.py

# Deploy
sudo cook apply examples/minimidia.py --yes
```

## Application Code

The `server.js` file is a placeholder. Replace it with your actual Node.js application code.

Alternatively, create your own server.js that matches your application requirements.

## Files

- `minimidia.py` - Main Cook configuration
- `package.json` - Node.js dependencies
- `server.js` - Application server (customize this)
- `minimidia.service` - Systemd service definition
- `nginx.conf.j2` - Nginx configuration template

## Key Techniques

### Multi-Phase Nginx Configuration

This example demonstrates Cook's **resource redefinition** feature for TLS certificate setup:

**Phase 1: HTTP-only Configuration**
```python
File(
    f"/etc/nginx/sites-available/{DOMAIN}",
    template="./files/nginx.conf.j2",
    vars={"ssl_enabled": False}  # HTTP only
)
```

**Phase 2: Obtain Certificate**
```python
Exec(
    "certbot-obtain-certificate",
    command=f"certbot certonly --nginx -d {DOMAIN} ...",
    creates=f"/etc/letsencrypt/live/{DOMAIN}/fullchain.pem"
)
```

**Phase 3: Update to HTTPS** (replaces Phase 1 definition)
```python
File(
    f"/etc/nginx/sites-available/{DOMAIN}",
    template="./files/nginx.conf.j2",
    vars={"ssl_enabled": True}  # HTTPS enabled
)
```

This pattern is necessary because:
- Let's Encrypt HTTP-01 challenge requires HTTP access
- After obtaining certificate, nginx should enforce HTTPS
- Resource redefinition allows natural workflow expression
- No temporary files or workarounds needed

**How it works:**
- Cook's executor implements "last definition wins" semantics
- When the same resource path is defined twice, the final definition is used
- Execution order is preserved (nginx config stays at its original position)
- The final state has HTTPS enabled after certificate is obtained

See the main README for more information on resource redefinition.

## Environment Variables

- `DOMAIN` - Your domain name (default: minimidia.com)
- `ADMIN_EMAIL` - Email for Let's Encrypt (default: admin@minimidia.com)
- `APP_PORT` - Application port (default: 3000)

## Post-Deployment

```bash
# Check application status
sudo systemctl status minimidia

# View logs
sudo journalctl -u minimidia -f

# Test the deployment
curl https://minimidia.com/health

# Check for configuration drift
sudo cook check-drift

# Fix any drift
sudo cook check-drift --fix
```

## Security Notes

- Application runs as `www-data` (non-privileged)
- Systemd security hardening enabled
- TLS 1.2+ with strong ciphers
- Security headers configured
- Firewall rules configured (UFW)

## Backup

Important directories to backup:
- `/opt/apps/minimidia/data/` - SQLite database
- `/etc/letsencrypt/` - TLS certificates

## Monitoring

Health check endpoint: `https://minimidia.com/health`

Returns:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-01T00:00:00.000Z",
  "uptime": 12345,
  "database": "connected"
}
```
