"""
Service reload triggers example.

Demonstrates auto-reloading nginx when configuration files change.

This example:
1. Creates nginx config files
2. Sets up nginx service with reload_on triggers
3. When configs change, nginx automatically reloads

Run with:
    cook plan examples/nginx-reload.py
    cook apply examples/nginx-reload.py
"""

from cook import File, Service

# Create nginx config files
nginx_conf = File(
    "/tmp/nginx-test.conf",
    content="""
    events { worker_connections 1024; }
    http {
        include /tmp/nginx-site.conf;
    }
    """,
    mode=0o644
)

site_conf = File(
    "/tmp/nginx-site.conf",
    content="""
    server {
        listen 8080;
        location / {
            return 200 'Hello from Cook!\\n';
        }
    }
    """,
    mode=0o644
)

# Service will auto-reload when configs change
# Note: This example uses /tmp configs and won't actually affect real nginx
# In a real scenario, use /etc/nginx paths and ensure nginx is installed
#
# Service("nginx",
#         running=True,
#         reload_on=[nginx_conf, site_conf])

print("Config loaded successfully")
print("Note: Service reload example - install nginx to test service management")
