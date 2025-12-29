"""
Comprehensive web server setup example.

This demonstrates:
- Package installation
- File management (configs, directories)
- Service management
- Command execution
- Resource dependencies

Installs:
- nginx web server
- Creates web root
- Sets up configuration
- Ensures service is running

Note: Requires sudo to run, designed for Ubuntu/Debian systems.

Run with:
    sudo cook plan examples/web-server.py
    sudo cook apply examples/web-server.py
"""

from cook import File, Package, Service, Exec

# Install nginx
Package("nginx")

# Create web root directory
web_root = File(
    "/var/www/mysite",
    ensure="directory",
    mode=0o755
)

# Create index.html
File(
    "/var/www/mysite/index.html",
    content="""<!DOCTYPE html>
<html>
<head>
    <title>Cook Example Site</title>
</head>
<body>
    <h1>Hello from Cook!</h1>
    <p>This server was configured using Cook.</p>
</body>
</html>
""",
    mode=0o644
)

# Nginx configuration
nginx_conf = File(
    "/etc/nginx/sites-available/mysite",
    content="""
server {
    listen 80;
    server_name _;

    root /var/www/mysite;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
""",
    mode=0o644
)

# Enable site (create symlink)
Exec(
    "enable-site",
    command="ln -sf /etc/nginx/sites-available/mysite /etc/nginx/sites-enabled/mysite",
    creates="/etc/nginx/sites-enabled/mysite"
)

# Remove default nginx site
Exec(
    "remove-default",
    command="rm -f /etc/nginx/sites-enabled/default",
    unless="test ! -f /etc/nginx/sites-enabled/default"
)

# Ensure nginx is running and will reload on config changes
Service(
    "nginx",
    running=True,
    enabled=True,
    reload_on=[nginx_conf]
)

print("Web server configuration loaded")
print("After applying, visit http://localhost to see your site")
