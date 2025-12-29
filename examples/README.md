# Cook Examples

## Basic Examples

### simple.py

File operations. Tests Cook installation.

```bash
cook plan examples/simple.py
cook apply examples/simple.py
```

### nginx-reload.py

Service reload triggers.

```bash
cook plan examples/nginx-reload.py
cook apply examples/nginx-reload.py
```

### web-server.py

Nginx with static site.

```bash
sudo cook plan examples/web-server.py
sudo cook apply examples/web-server.py
```

## Stack Examples

### lemp-stack.py

LEMP stack: Linux, Nginx, MySQL, PHP-FPM

```bash
sudo cook apply examples/lemp-stack.py --yes
curl http://localhost/
curl http://localhost/info.php
```

### wordpress.py

WordPress with MySQL

```bash
sudo cook apply examples/wordpress.py --yes
```

Visit http://localhost for WordPress setup.

### wordpress-pgsql.py

WordPress with PostgreSQL

```bash
sudo cook apply examples/wordpress-pgsql.py --yes
```

Note: WordPress doesn't natively support PostgreSQL. Use MySQL for production.

## Multi-Server

### multi-server/database.py

PostgreSQL database server.

```bash
# Local
sudo cook apply multi-server/database.py

# Remote
cook apply multi-server/database.py --host db.example.com --user admin --sudo
```

See [multi-server/README.md](multi-server/README.md).

## Patterns

### Functions

```python
from cook import File, Package, Service

def install_web_server(domain, port=80):
    Package("nginx")
    File(f"/etc/nginx/sites-available/{domain}",
         content=f"server {{ listen {port}; server_name {domain}; }}")
    Service("nginx", running=True)

install_web_server("blog.example.com")
install_web_server("shop.example.com", port=8080)
```

### Data-Driven

```python
SITES = [
    {"name": "blog", "port": 3000},
    {"name": "shop", "port": 4000},
]

for site in SITES:
    File(f"/var/www/{site['name']}", ensure="directory")
    File(f"/etc/nginx/sites-available/{site['name']}",
         content=f"server {{ listen {site['port']}; }}")
```

## Environment Variables

```bash
export DOMAIN="myapp.local"
export MYSQL_ROOT_PASSWORD="secure_password"
cook apply examples/lemp-stack.py

export DB_NAME="production_db"
export DB_USER="app_user"
export DB_PASSWORD="secure_pass"
cook apply multi-server/database.py
```

## Remote Deployment

```bash
cook plan examples/web-server.py --host test.example.com --user admin
cook apply examples/web-server.py --host test.example.com --user admin --sudo --yes
```

## Security

Examples use default passwords for development only.

Production checklist:
- Change all default passwords
- Generate new security keys
- Configure SSL/TLS
- Set up firewall rules
- Configure automated backups
- Review file permissions
- Enable monitoring
- Set up fail2ban

## Troubleshooting

Permission errors:

```bash
sudo cook apply examples/lemp-stack.py
```

Port conflicts:

```bash
sudo netstat -tulpn | grep :80
sudo systemctl stop nginx
```

Service status:

```bash
sudo systemctl status nginx
sudo systemctl status php8.1-fpm
sudo journalctl -u nginx -f
```

## Example Template

```python
"""
[Example Name]

[Description]

Usage:
    sudo cook apply examples/example.py --yes
"""

from cook import Package, File, Service
import os

SETTING = os.getenv("SETTING", "default")

Package("example-package")

File("/etc/example/config",
     content="...",
     mode=0o644)

Service("example", running=True, enabled=True)
```
