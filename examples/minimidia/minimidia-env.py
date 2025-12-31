"""
Minimidia Multi-Environment Configuration

Supports multiple deployment environments: development, staging, production

Usage:
    # Development
    sudo cook plan examples/minimidia-env.py
    sudo COOK_ENV=development cook apply examples/minimidia-env.py --yes

    # Staging
    sudo COOK_ENV=staging DOMAIN=staging.minimidia.com cook apply examples/minimidia-env.py --yes

    # Production
    sudo COOK_ENV=production DOMAIN=minimidia.com cook apply examples/minimidia-env.py --yes

Environment Variables:
    COOK_ENV - Environment name: development, staging, production (required)
    DOMAIN - Domain name (auto-generated if not set)
    ADMIN_EMAIL - Email for Let's Encrypt
    APP_PORT - Application port
"""

from cook import File, Package, Service, Exec, Repository
import os
import sys

# ============================================================================
# Environment Configuration
# ============================================================================

# Detect environment
ENV = os.getenv("COOK_ENV", "development")
if ENV not in ["development", "staging", "production"]:
    print(f"Error: COOK_ENV must be one of: development, staging, production")
    print(f"Got: {ENV}")
    sys.exit(1)

# Environment-specific configurations
ENVIRONMENTS = {
    "development": {
        "domain": os.getenv("DOMAIN", "dev.minimidia.local"),
        "app_port": int(os.getenv("APP_PORT", "3000")),
        "admin_email": os.getenv("ADMIN_EMAIL", "dev@minimidia.com"),
        "node_env": "development",
        "enable_ssl": False,  # No SSL for local development
        "enable_docker": True,
        "log_level": "debug",
        "auto_restart": False,
    },
    "staging": {
        "domain": os.getenv("DOMAIN", "staging.minimidia.com"),
        "app_port": int(os.getenv("APP_PORT", "3000")),
        "admin_email": os.getenv("ADMIN_EMAIL", "staging@minimidia.com"),
        "node_env": "staging",
        "enable_ssl": True,
        "enable_docker": True,
        "log_level": "info",
        "auto_restart": True,
    },
    "production": {
        "domain": os.getenv("DOMAIN", "minimidia.com"),
        "app_port": int(os.getenv("APP_PORT", "3000")),
        "admin_email": os.getenv("ADMIN_EMAIL", "admin@minimidia.com"),
        "node_env": "production",
        "enable_ssl": True,
        "enable_docker": True,
        "log_level": "warn",
        "auto_restart": True,
    },
}

config = ENVIRONMENTS[ENV]
APP_DIR = f"/opt/apps/minimidia-{ENV}"

print("=" * 75)
print(f"    Minimidia SaaS - {ENV.upper()} Environment")
print("=" * 75)
print(f"  Environment:  {ENV}")
print(f"  Domain:       {config['domain']}")
print(f"  App Dir:      {APP_DIR}")
print(f"  App Port:     {config['app_port']}")
print(f"  Node ENV:     {config['node_env']}")
print(f"  SSL Enabled:  {config['enable_ssl']}")
print(f"  Auto Restart: {config['auto_restart']}")
print()

# ============================================================================
# System Setup (all environments)
# ============================================================================

if ENV == "production":
    print("Phase 1: System Updates (Production only)")
    Repository("apt-update", action="update")
    Repository("apt-upgrade", action="upgrade")

# Add repositories (all environments need Node.js)
Repository(
    "nodesource",
    action="add",
    repo="deb https://deb.nodesource.com/node_20.x nodistro main",
    key_url="https://deb.nodesource.com/gpgkey/nodesource.gpg.key",
    filename="nodesource.list"
)

if config["enable_docker"]:
    Repository(
        "docker",
        action="add",
        repo="deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable",
        key_url="https://download.docker.com/linux/ubuntu/gpg",
        filename="docker.list"
    )

Repository("apt-update-repos", action="update")

# ============================================================================
# Package Installation
# ============================================================================

print("Phase 2: Package Installation")

Package("nginx")
Package("nodejs")

if config["enable_ssl"]:
    Package("certbot", packages=["certbot", "python3-certbot-nginx"])

if config["enable_docker"]:
    Package("docker", packages=[
        "docker-ce",
        "docker-ce-cli",
        "containerd.io",
        "docker-compose-plugin",
    ])

Package("sqlite", packages=["sqlite3", "libsqlite3-dev"])
Package("build-essential", packages=["build-essential", "python3"])

# Development tools for non-production
if ENV != "production":
    Package("dev-tools", packages=["htop", "tree", "jq", "curl", "git"])

# ============================================================================
# Application Setup
# ============================================================================

print("Phase 3: Application Setup")

File(APP_DIR, ensure="directory", mode=0o755)
File(f"{APP_DIR}/data", ensure="directory", mode=0o750, owner="www-data", group="www-data")
File(f"{APP_DIR}/logs", ensure="directory", mode=0o755, owner="www-data", group="www-data")

# Environment-specific configuration
File(
    f"{APP_DIR}/.env",
    content=f"""NODE_ENV={config['node_env']}
PORT={config['app_port']}
HOST=127.0.0.1
DOMAIN={config['domain']}
DB_PATH=./data/minimidia-{ENV}.db
LOG_LEVEL={config['log_level']}
ENVIRONMENT={ENV}
""",
    mode=0o600,
    owner="www-data",
    group="www-data"
)

# Copy application files (assuming they exist)
for filename in ["package.json", "server.js"]:
    File(
        f"{APP_DIR}/{filename}",
        source=f"./files/{filename}",
        mode=0o644
    )

Exec(
    f"npm-install-{ENV}",
    command=f"npm install {'--production' if ENV == 'production' else ''}",
    cwd=APP_DIR,
    unless="test -d node_modules"
)

# ============================================================================
# Systemd Service
# ============================================================================

print("Phase 4: Systemd Service")

# Environment-specific service name
service_name = f"minimidia-{ENV}"

File(
    f"/etc/systemd/system/{service_name}.service",
    content=f"""[Unit]
Description=Minimidia SaaS Application ({ENV.upper()})
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory={APP_DIR}
EnvironmentFile={APP_DIR}/.env

# Restart policy based on environment
{"Restart=always" if config['auto_restart'] else "Restart=on-failure"}
RestartSec=10

ExecStart=/usr/bin/node server.js
StandardOutput=journal
StandardError=journal
SyslogIdentifier={service_name}

# Security (stricter in production)
{"NoNewPrivileges=true" if ENV == "production" else ""}
{"PrivateTmp=true" if ENV == "production" else ""}

[Install]
WantedBy=multi-user.target
""",
    mode=0o644
)

Exec(f"systemd-reload-{ENV}", command="systemctl daemon-reload")
Service(service_name, running=True, enabled=True)

# ============================================================================
# Nginx Configuration
# ============================================================================

print("Phase 5: Nginx Configuration")

domain = config['domain']
nginx_site = f"/etc/nginx/sites-available/{domain}"

nginx_conf = File(
    nginx_site,
    template="./files/nginx.conf.j2",
    vars={
        "domain": domain,
        "app_port": config['app_port'],
        "app_dir": APP_DIR,
        "ssl_enabled": config['enable_ssl']
    },
    mode=0o644
)

Exec(
    f"enable-nginx-{ENV}",
    command=f"ln -sf {nginx_site} /etc/nginx/sites-enabled/{domain}",
    creates=f"/etc/nginx/sites-enabled/{domain}"
)

if ENV == "development":
    # Remove default site in development
    Exec("remove-default", command="rm -f /etc/nginx/sites-enabled/default", only_if="test -f /etc/nginx/sites-enabled/default")

Service("nginx", running=True, enabled=True, reload_on=[nginx_conf])

# ============================================================================
# TLS Certificate (Staging & Production only)
# ============================================================================

if config['enable_ssl']:
    print(f"Phase 6: TLS Certificate ({ENV})")

    # Use --staging flag for staging environment
    certbot_flags = "--staging" if ENV == "staging" else ""

    Exec(
        f"certbot-{ENV}",
        command=f"certbot certonly --nginx {certbot_flags} -d {domain} --non-interactive --agree-tos --email {config['admin_email']}",
        creates=f"/etc/letsencrypt/live/{domain}/fullchain.pem"
    )

    # Update Nginx with TLS
    File(
        nginx_site,
        template="./files/nginx.conf.j2",
        vars={
            "domain": domain,
            "app_port": config['app_port'],
            "app_dir": APP_DIR,
            "ssl_enabled": True
        },
        mode=0o644
    )

    Exec(f"nginx-reload-{ENV}", command="systemctl reload nginx")

# ============================================================================
# Environment-Specific Configuration
# ============================================================================

if ENV == "development":
    print("Phase 7: Development Tools")

    # Install nodemon for development
    Exec(
        "npm-global-nodemon",
        command="npm install -g nodemon",
        unless="which nodemon"
    )

    print("\n  Development environment ready!")
    print(f"  Access: http://{domain}")
    print(f"  Logs: journalctl -u {service_name} -f")

elif ENV == "staging":
    print("Phase 7: Staging Configuration")

    # More verbose logging for staging
    print("\n  Staging environment ready!")
    print(f"  Access: https://{domain} (Let's Encrypt staging cert)")
    print(f"  Logs: journalctl -u {service_name} -f")

elif ENV == "production":
    print("Phase 7: Production Hardening")

    # Firewall
    Exec("ufw-ssh", command="ufw allow 22/tcp", unless="ufw status | grep -q '22.*ALLOW'")
    Exec("ufw-http", command="ufw allow 80/tcp", unless="ufw status | grep -q '80.*ALLOW'")
    Exec("ufw-https", command="ufw allow 443/tcp", unless="ufw status | grep -q '443.*ALLOW'")

    # Log rotation
    File(
        "/etc/logrotate.d/minimidia-production",
        content=f"""{APP_DIR}/logs/*.log {{
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
}}
""",
        mode=0o644
    )

    print("\n  Production environment deployed!")
    print(f"  Access: https://{domain}")
    print(f"  Health: https://{domain}/health")
    print(f"  Logs: journalctl -u {service_name} -f")

print()
print("=" * 75)
print(f"  Environment: {ENV.upper()}")
print(f"  Status: systemctl status {service_name}")
print(f"  Drift Check: sudo cook check-drift")
print("=" * 75)
