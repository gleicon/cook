"""
Minimidia SaaS Infrastructure Configuration

Complete production infrastructure for a Node.js SaaS application with:
- Nginx reverse proxy with TLS
- Node.js application server
- SQLite database
- Let's Encrypt certificates
- Docker and Docker Compose
- Systemd service management

Usage:
    # Plan changes
    sudo cook plan minimidia/minimidia.py

    # Apply configuration
    sudo cook apply minimidia/minimidia.py --yes

    # Check for drift
    sudo cook check-drift

    # Fix any drift
    sudo cook check-drift --fix

Environment Variables:
    DOMAIN - Domain name (default: minimidia.com)
    ADMIN_EMAIL - Email for Let's Encrypt (default: admin@minimidia.com)
    APP_PORT - Application port (default: 3000)
"""

from cook import File, Package, Service, Exec, Repository
import os

# Get the directory containing this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(SCRIPT_DIR, "files")

# Configuration
DOMAIN = os.getenv("DOMAIN", "minimidia.com")
APP_DIR = "/opt/apps/minimidia"
APP_PORT = int(os.getenv("APP_PORT", "3000"))
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@minimidia.com")
NODE_VERSION = "20.x"

print("=" * 75)
print("    Minimidia SaaS Infrastructure Deployment")
print("=" * 75)
print(f"  Domain:       {DOMAIN}")
print(f"  App Dir:      {APP_DIR}")
print(f"  App Port:     {APP_PORT}")
print(f"  Admin Email:  {ADMIN_EMAIL}")
print(f"  Node Version: {NODE_VERSION}")
print()

# Phase 1: System Updates & Repository Setup
print("Phase 1: System Updates & Repository Setup")

Repository("apt-update", action="update")
Repository("apt-upgrade", action="upgrade")

# Install Node.js from NodeSource using their official setup script
Exec(
    "nodesource-setup",
    command=f"curl -fsSL https://deb.nodesource.com/setup_{NODE_VERSION} | bash -",
    unless="test -f /etc/apt/sources.list.d/nodesource.list && dpkg -l nodejs 2>/dev/null | grep -q '^ii'",
    safe_mode=False,
    security_level="none"
)

Repository(
    "docker",
    action="add",
    repo="deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable",
    key_url="https://download.docker.com/linux/ubuntu/gpg",
    filename="docker.list"
)

Repository("apt-update-after-repos", action="update")

# Phase 2: Core Package Installation
print("Phase 2: Core Package Installation")

Package("nginx")
Package("nodejs")
Package("certbot", packages=["certbot", "python3-certbot-nginx"])
Package("docker", packages=[
    "docker-ce",
    "docker-ce-cli",
    "containerd.io",
    "docker-compose-plugin",
    "docker-buildx-plugin",
])
Package("sqlite", packages=["sqlite3", "libsqlite3-dev"])
Package("build-essential", packages=["build-essential", "python3", "make", "g++"])
Package("utilities", packages=["curl", "wget", "git", "htop", "tree", "jq"])

# Phase 3: Application Directory Structure
print("Phase 3: Application Directory Structure")

File(APP_DIR, ensure="directory", mode=0o755, owner="root", group="root")
File(f"{APP_DIR}/logs", ensure="directory", mode=0o755, owner="www-data", group="www-data")
File(f"{APP_DIR}/data", ensure="directory", mode=0o750, owner="www-data", group="www-data")
File(f"{APP_DIR}/public", ensure="directory", mode=0o755, owner="www-data", group="www-data")

# Directory for Let's Encrypt ACME challenge
File("/var/www/html", ensure="directory", mode=0o755, owner="www-data", group="www-data")

# Phase 4: Node.js Application Files
print("Phase 4: Node.js Application Setup")

# Read server.js from external file
File(
    f"{APP_DIR}/server.js",
    source=os.path.join(FILES_DIR, "server.js"),
    mode=0o644,
    owner="root",
    group="root"
)

File(
    f"{APP_DIR}/package.json",
    source=os.path.join(FILES_DIR, "package.json"),
    mode=0o644,
    owner="root",
    group="root"
)

File(
    f"{APP_DIR}/.env",
    content=f"""NODE_ENV=production
PORT={APP_PORT}
HOST=127.0.0.1
DOMAIN={DOMAIN}
DB_PATH=./data/minimidia.db
LOG_LEVEL=info
""",
    mode=0o600,
    owner="www-data",
    group="www-data"
)

Exec(
    "npm-install",
    command=f"cd {APP_DIR} && npm install --production --no-audit --no-fund",
    unless=f"test -d {APP_DIR}/node_modules && test -f {APP_DIR}/node_modules/.package-lock.json",
    environment={"NODE_ENV": "production"},
    safe_mode=False,
    security_level="none"
)

# Phase 5: Systemd Service Configuration
print("Phase 5: Systemd Service Configuration")

minimidia_service = File(
    "/etc/systemd/system/minimidia.service",
    source=os.path.join(FILES_DIR, "minimidia.service"),
    mode=0o644,
    owner="root",
    group="root"
)

Exec("systemd-reload", command="systemctl daemon-reload")

Service("minimidia", running=True, enabled=True)

# Phase 6: Nginx Configuration
print("Phase 6: Nginx Reverse Proxy Configuration")

# Create initial HTTP-only nginx config for certbot verification
nginx_conf = File(
    f"/etc/nginx/sites-available/{DOMAIN}",
    template=os.path.join(FILES_DIR, "nginx.conf.j2"),
    vars={
        "domain": DOMAIN,
        "app_port": APP_PORT,
        "app_dir": APP_DIR,
        "ssl_enabled": False
    },
    mode=0o644,
    owner="root",
    group="root"
)

Exec(
    "enable-nginx-site",
    command=f"ln -sf /etc/nginx/sites-available/{DOMAIN} /etc/nginx/sites-enabled/{DOMAIN}",
    creates=f"/etc/nginx/sites-enabled/{DOMAIN}"
)

Exec("remove-default-nginx-site", command="rm -f /etc/nginx/sites-enabled/default", only_if="test -f /etc/nginx/sites-enabled/default")

# Test nginx config and start/reload nginx
Service("nginx", running=True, enabled=True, reload_on=[nginx_conf])

# Phase 7: Let's Encrypt TLS Certificate
print("Phase 7: Let's Encrypt TLS Certificate Setup")

# NOTE: Certbot will fail if domain doesn't resolve to this server
# For testing without real DNS, skip this phase or use --dry-run
Exec(
    "certbot-obtain-certificate",
    command=f"certbot certonly --nginx -d {DOMAIN} --non-interactive --agree-tos --email {ADMIN_EMAIL} --deploy-hook 'systemctl reload nginx' --cert-name {DOMAIN}",
    creates=f"/etc/letsencrypt/live/{DOMAIN}/fullchain.pem",
    safe_mode=False,
    security_level="none"
)

# Update Nginx with TLS configuration after certificate is obtained
# This replaces the HTTP-only config from Phase 6
File(
    f"/etc/nginx/sites-available/{DOMAIN}",
    template=os.path.join(FILES_DIR, "nginx.conf.j2"),
    vars={
        "domain": DOMAIN,
        "app_port": APP_PORT,
        "app_dir": APP_DIR,
        "ssl_enabled": True
    },
    mode=0o644,
    owner="root",
    group="root"
)

# Reload nginx with TLS config (only if certificate was obtained)
Service("nginx", running=True, enabled=True)

# Phase 8: Docker Configuration
print("Phase 8: Docker Configuration")

Service("docker", running=True, enabled=True)

Exec("docker-group-www-data", command="usermod -aG docker www-data", unless="groups www-data | grep -q docker")

Exec("docker-buildx-setup", command="docker buildx create --use --name minimidia-builder 2>/dev/null || true", unless="docker buildx ls | grep -q minimidia-builder", safe_mode=False, security_level="none")

# Phase 9: Security & System Hardening
print("Phase 9: Security & System Hardening")

Exec("ufw-allow-ssh", command="ufw allow 22/tcp", unless="ufw status | grep -q '22/tcp.*ALLOW' || ! command -v ufw", safe_mode=False, security_level="none")
Exec("ufw-allow-http", command="ufw allow 80/tcp", unless="ufw status | grep -q '80/tcp.*ALLOW' || ! command -v ufw", safe_mode=False, security_level="none")
Exec("ufw-allow-https", command="ufw allow 443/tcp", unless="ufw status | grep -q '443/tcp.*ALLOW' || ! command -v ufw", safe_mode=False, security_level="none")
Exec("chown-app-data", command=f"chown -R www-data:www-data {APP_DIR}/data {APP_DIR}/logs", unless=f"test -O {APP_DIR}/data")

# Phase 10: Monitoring & Maintenance
print("Phase 10: Monitoring & Maintenance Setup")

File(
    "/etc/logrotate.d/minimidia",
    content=f"""{APP_DIR}/logs/*.log {{
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload minimidia > /dev/null 2>&1 || true
    endscript
}}
""",
    mode=0o644
)

Exec("certbot-renewal-cron", command="systemctl enable certbot.timer && systemctl start certbot.timer", unless="systemctl is-enabled certbot.timer 2>/dev/null", safe_mode=False, security_level="none")

# Deployment Summary
print()
print("=" * 75)
print("                    Deployment Complete!")
print("=" * 75)
print()
print(f"Application: https://{DOMAIN}")
print(f"Health:      https://{DOMAIN}/health")
print()
print(f"Services:")
print(f"  systemctl status minimidia")
print(f"  systemctl status nginx")
print(f"  systemctl status docker")
print()
print(f"Logs:")
print(f"  journalctl -u minimidia -f")
print(f"  tail -f /var/log/nginx/{DOMAIN}-access.log")
print()
print("=" * 75)
