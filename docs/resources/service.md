# Service Resource

Manage system services (systemd, launchctl) and service lifecycle.

## Overview

The Service resource handles service management:

- Start and stop services
- Enable and disable services at boot
- Automatic reload on configuration changes
- Automatic restart on binary updates
- Cross-platform support (Linux systemd, macOS launchctl)

## Supported Service Managers

| Platform | Service Manager | Start/Stop | Enable/Disable | Reload | Restart |
| -------- | --------------- | ---------- | -------------- | ------ | ------- |
| Linux    | systemd         | Yes        | Yes            | Yes    | Yes     |
| macOS    | launchctl       | Yes        | Limited        | No     | Yes     |

## Basic Usage

### Start Service

```python
from cook import Service

Service("nginx", running=True)
```

### Enable Service at Boot

```python
Service("nginx", running=True, enabled=True)
```

### Stop Service

```python
Service("apache2", running=False)
```

### Disable Service

```python
Service("apache2", enabled=False)
```

## Parameters

### name

**Required**. Service name as recognized by the service manager.

```python
Service("nginx", running=True)
```

On systemd, this corresponds to the unit name (e.g., `nginx.service`).

### running

Whether the service should be running.

- `True`: Service must be running
- `False`: Service must be stopped
- `None`: No running state enforcement (default)

```python
# Ensure service is running
Service("nginx", running=True)

# Ensure service is stopped
Service("apache2", running=False)
```

### enabled

Whether the service should be enabled at boot.

- `True`: Service starts at boot
- `False`: Service does not start at boot
- `None`: No boot state enforcement (default)

```python
# Enable at boot
Service("nginx", enabled=True)

# Disable at boot
Service("apache2", enabled=False)
```

### reload_on

List of resources that trigger a service reload when changed.

```python
nginx_conf = File("/etc/nginx/nginx.conf", source="./nginx.conf")

Service("nginx", running=True, reload_on=[nginx_conf])
```

When `nginx_conf` changes, the service is reloaded (not restarted).

### restart_on

List of resources that trigger a service restart when changed.

```python
app_binary = File("/usr/local/bin/app", source="./app")

Service("app", running=True, restart_on=[app_binary])
```

When `app_binary` changes, the service is restarted.

## Automatic Reload and Restart

Services can automatically reload or restart when dependencies change.

### Reload on Configuration Change

Use `reload_on` for configuration file changes. This reloads the service without dropping connections.

```python
from cook import File, Service

# Nginx configuration
nginx_conf = File("/etc/nginx/nginx.conf", source="./nginx.conf")

# Reload nginx when config changes
Service("nginx", running=True, enabled=True, reload_on=[nginx_conf])
```

Workflow:
1. Cook detects `nginx.conf` changed
2. Cook applies file changes
3. Cook reloads nginx service (graceful reload)

### Restart on Binary Update

Use `restart_on` for binary or critical file changes. This fully restarts the service.

```python
from cook import File, Service

# Application binary
app_binary = File("/opt/apps/myapp/app", source="./app", mode=0o755)

# Application service file
app_service = File(
    "/etc/systemd/system/myapp.service",
    source="./myapp.service"
)

# Restart when binary or service file changes
Service("myapp", running=True, enabled=True, restart_on=[app_binary, app_service])
```

Workflow:
1. Cook detects `app` binary changed
2. Cook applies file changes
3. Cook restarts myapp service (full restart)

### Multiple Triggers

Combine reload and restart triggers:

```python
from cook import File, Service

# Configuration files
nginx_conf = File("/etc/nginx/nginx.conf", source="./nginx.conf")
site_conf = File("/etc/nginx/sites-available/mysite", source="./mysite.conf")

# Binary files
nginx_binary = File("/usr/sbin/nginx", source="./nginx", mode=0o755)

# Reload on config changes, restart on binary changes
Service(
    "nginx",
    running=True,
    enabled=True,
    reload_on=[nginx_conf, site_conf],
    restart_on=[nginx_binary]
)
```

## Examples

### Web Server

```python
from cook import Package, File, Service

# Install nginx
Package("nginx")

# Configure nginx
nginx_conf = File("/etc/nginx/nginx.conf", source="./nginx.conf")
site_conf = File("/etc/nginx/sites-available/default", source="./default.conf")

# Manage service
Service("nginx", running=True, enabled=True, reload_on=[nginx_conf, site_conf])
```

### Application Server

```python
from cook import File, Service

# Application files
app_dir = File("/opt/apps/myapp", ensure="directory", mode=0o755)
app_binary = File("/opt/apps/myapp/app", source="./app", mode=0o755)
app_config = File("/opt/apps/myapp/config.yml", source="./config.yml")

# Systemd service file
service_file = File(
    "/etc/systemd/system/myapp.service",
    template="./myapp.service.j2",
    vars={"user": "app", "workdir": "/opt/apps/myapp"}
)

# Manage service
Service(
    "myapp",
    running=True,
    enabled=True,
    reload_on=[app_config],
    restart_on=[app_binary, service_file]
)
```

### Database Server

```python
from cook import Package, Service

# Install PostgreSQL
Package("postgresql")

# Ensure service is running and enabled
Service("postgresql", running=True, enabled=True)
```

### Docker Daemon

```python
from cook import Package, File, Service

# Install Docker
Package("docker", packages=["docker-ce", "docker-ce-cli", "containerd.io"])

# Docker daemon configuration
daemon_config = File(
    "/etc/docker/daemon.json",
    source="./docker-daemon.json",
    mode=0o644
)

# Manage Docker service
Service("docker", running=True, enabled=True, restart_on=[daemon_config])
```

### Disable Unwanted Service

```python
Service("apache2", running=False, enabled=False)
```

## Systemd Service Files

Create custom systemd services with File resource:

### Simple Service

Template: `myapp.service.j2`

```ini
[Unit]
Description=My Application
After=network.target

[Service]
Type=simple
User={{ user }}
WorkingDirectory={{ workdir }}
ExecStart={{ exec_start }}
Restart=always

[Install]
WantedBy=multi-user.target
```

Cook configuration:

```python
from cook import File, Service

# Create service file
service_file = File(
    "/etc/systemd/system/myapp.service",
    template="./myapp.service.j2",
    vars={
        "user": "app",
        "workdir": "/opt/apps/myapp",
        "exec_start": "/opt/apps/myapp/start.sh"
    }
)

# Reload systemd daemon when service file changes
# (systemd-specific - requires custom Exec resource)

# Manage service
Service("myapp", running=True, enabled=True, restart_on=[service_file])
```

### Service with Environment Variables

Template: `myapp-env.service.j2`

```ini
[Unit]
Description=My Application
After=network.target

[Service]
Type=simple
User={{ user }}
WorkingDirectory={{ workdir }}
Environment="PORT={{ port }}"
Environment="LOG_LEVEL={{ log_level }}"
ExecStart={{ exec_start }}
Restart=always

[Install]
WantedBy=multi-user.target
```

Cook configuration:

```python
File(
    "/etc/systemd/system/myapp.service",
    template="./myapp-env.service.j2",
    vars={
        "user": "app",
        "workdir": "/opt/apps/myapp",
        "exec_start": "/opt/apps/myapp/app",
        "port": 3000,
        "log_level": "info"
    }
)

Service("myapp", running=True, enabled=True)
```

## Idempotency

Service resources are idempotent. Running the same configuration multiple times produces the same result.

```python
Service("nginx", running=True, enabled=True)
# First run: Starts and enables nginx
# Second run: Detects nginx already running and enabled, no changes
```

Service state changes are detected:

```python
Service("nginx", running=True)
# If nginx is stopped, Cook starts it
# If nginx is running, Cook makes no changes
```

## Platform-Specific Behavior

### Linux (systemd)

```python
Service("nginx", running=True, enabled=True)
```

Equivalent to:

```bash
systemctl start nginx
systemctl enable nginx
```

Check status:

```bash
systemctl is-active nginx
systemctl is-enabled nginx
```

Reload:

```bash
systemctl reload nginx
```

Restart:

```bash
systemctl restart nginx
```

### macOS (launchctl)

```python
Service("nginx", running=True)
```

Equivalent to:

```bash
launchctl start nginx
```

**Note:** macOS service management differs from Linux. Services are defined in plist files in `/Library/LaunchDaemons/` or `~/Library/LaunchAgents/`.

## Common Patterns

### Web Application Stack

```python
from cook import Package, File, Service

# Install packages
Package("nginx")
Package("postgresql")

# Nginx configuration
nginx_conf = File("/etc/nginx/nginx.conf", source="./nginx.conf")

# Services
Service("postgresql", running=True, enabled=True)
Service("nginx", running=True, enabled=True, reload_on=[nginx_conf])
```

### Systemd Socket Activation

```python
# Socket file
File(
    "/etc/systemd/system/myapp.socket",
    source="./myapp.socket"
)

# Service file
File(
    "/etc/systemd/system/myapp.service",
    source="./myapp.service"
)

# Manage socket (service starts on demand)
Service("myapp.socket", running=True, enabled=True)
```

### Service with Health Check

```python
from cook import File, Service, Exec

# Service files
app_binary = File("/opt/apps/myapp/app", source="./app", mode=0o755)

# Start service
Service("myapp", running=True, enabled=True, restart_on=[app_binary])

# Health check (verify service is responding)
Exec(
    "health-check",
    command="curl -f http://localhost:3000/health || exit 1",
    retry=3
)
```

## Security Considerations

### Service User

Run services with dedicated users, not root:

```ini
[Service]
User=app
Group=app
```

### Service Hardening

Use systemd hardening features:

```ini
[Service]
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/apps/myapp/data
```

### Service Restart Limits

Prevent restart loops:

```ini
[Service]
Restart=on-failure
RestartSec=5s
StartLimitBurst=3
StartLimitIntervalSec=60s
```

## Troubleshooting

### Service Fails to Start

Check service status:

```bash
systemctl status nginx
journalctl -u nginx -n 50
```

Verify service file syntax:

```bash
systemd-analyze verify /etc/systemd/system/myapp.service
```

### Service Not Enabled

Ensure service file is installed before enabling:

```python
service_file = File("/etc/systemd/system/myapp.service", source="./myapp.service")

# systemd requires daemon-reload after service file changes
# This can be done with Exec resource

Service("myapp", enabled=True)
```

### Reload Not Working

Not all services support reload. Use restart instead:

```python
Service("myapp", running=True, restart_on=[config_file])
```

## Limitations

### macOS launchctl

- No direct enable/disable support (services are enabled by plist file presence)
- No reload operation (use restart)
- Service names follow reverse-domain format (e.g., `com.example.myapp`)

### Service Dependencies

Cook does not automatically handle systemd dependencies (After, Requires, Wants). Define these in the service unit file.

## API Reference

See [cook/resources/service.py](https://github.com/gleicon/cook/blob/main/cook/resources/service.py) for complete source code and implementation details.
