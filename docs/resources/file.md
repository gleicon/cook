# File Resource

Manage files, directories, templates, and permissions.

## Overview

The File resource handles file system operations:

- Create and manage files with inline content or from source
- Create and manage directories
- Set file permissions (mode, owner, group)
- Render Jinja2 templates
- Delete files and directories

## Basic Usage

### File with Inline Content

```python
from cook import File

File("/etc/motd", content="Welcome to the server")
```

### File from Source

```python
File("/etc/nginx/nginx.conf", source="./configs/nginx.conf")
```

### Directory

```python
File("/var/www/app", ensure="directory", mode=0o755)
```

### File with Permissions

```python
File(
    "/var/www/index.html",
    content="<h1>Hello World</h1>",
    owner="www-data",
    group="www-data",
    mode=0o644
)
```

## Parameters

### path

**Required**. File or directory path on the target system.

```python
File("/etc/hostname", content="webserver01")
```

### content

Inline file content as a string.

**Mutually exclusive with** `source` and `template`.

```python
File("/etc/issue", content="Authorized access only")
```

### source

Path to source file on the local system. Content is read and transferred to the target.

**Mutually exclusive with** `content` and `template`.

```python
File("/etc/ssh/sshd_config", source="./configs/sshd_config")
```

### template

Path to Jinja2 template file on the local system. Template is rendered with `vars` and transferred to the target.

**Mutually exclusive with** `content` and `source`.

```python
File(
    "/etc/nginx/sites-available/mysite",
    template="./templates/nginx-site.j2",
    vars={"domain": "example.com", "port": 80}
)
```

### vars

Dictionary of variables for template rendering. Only used with `template` parameter.

```python
File(
    "/etc/app/config.yml",
    template="./templates/config.yml.j2",
    vars={
        "database_host": "localhost",
        "database_port": 5432,
        "debug": False
    }
)
```

### ensure

Resource state: `"file"`, `"directory"`, or `"absent"`.

**Default:** `"file"`

```python
# Ensure file exists
File("/var/log/app.log", ensure="file")

# Ensure directory exists
File("/var/lib/app", ensure="directory")

# Ensure file is removed
File("/tmp/old-config", ensure="absent")
```

### mode

File permissions as octal integer.

```python
# Read/write for owner, read-only for group and others
File("/etc/app.conf", content="config", mode=0o644)

# Executable script
File("/usr/local/bin/backup.sh", source="./backup.sh", mode=0o755)

# Directory with restricted access
File("/var/secrets", ensure="directory", mode=0o700)
```

### owner

Owner username for the file or directory.

```python
File("/var/www/index.html", content="<h1>Hello</h1>", owner="www-data")
```

### group

Group name for the file or directory.

```python
File("/var/www/index.html", content="<h1>Hello</h1>", group="www-data")
```

## Templates

File resources support Jinja2 templates for dynamic content generation.

### Basic Template

Template file: `nginx-site.j2`

```nginx
server {
    listen 80;
    server_name {{ domain }};

    location / {
        proxy_pass http://127.0.0.1:{{ port }};
    }
}
```

Cook configuration:

```python
File(
    "/etc/nginx/sites-available/mysite",
    template="./nginx-site.j2",
    vars={"domain": "example.com", "port": 3000}
)
```

Result:

```nginx
server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}
```

### Conditional Content

Template file: `app-config.j2`

```yaml
database:
  host: {{ db_host }}
  port: {{ db_port }}

{% if enable_cache %}
cache:
  enabled: true
  ttl: {{ cache_ttl }}
{% endif %}

debug: {{ debug }}
```

Cook configuration:

```python
File(
    "/etc/app/config.yml",
    template="./app-config.j2",
    vars={
        "db_host": "localhost",
        "db_port": 5432,
        "enable_cache": True,
        "cache_ttl": 300,
        "debug": False
    }
)
```

### Lists in Templates

Template file: `hosts.j2`

```
127.0.0.1 localhost
{% for host in additional_hosts %}
{{ host.ip }} {{ host.name }}
{% endfor %}
```

Cook configuration:

```python
File(
    "/etc/hosts",
    template="./hosts.j2",
    vars={
        "additional_hosts": [
            {"ip": "10.0.0.1", "name": "db01"},
            {"ip": "10.0.0.2", "name": "cache01"},
        ]
    }
)
```

## Examples

### Web Application Structure

```python
from cook import File

# Application directory
File("/opt/apps/myapp", ensure="directory", mode=0o755)

# Data directory with restricted permissions
File("/opt/apps/myapp/data", ensure="directory", mode=0o750, owner="www-data")

# Configuration from template
File(
    "/opt/apps/myapp/config.json",
    template="./templates/app-config.j2",
    vars={
        "port": 3000,
        "database": "/opt/apps/myapp/data/app.db"
    },
    owner="www-data",
    mode=0o640
)

# Static content
File(
    "/opt/apps/myapp/public/index.html",
    source="./public/index.html",
    owner="www-data",
    mode=0o644
)
```

### SSH Configuration

```python
File(
    "/etc/ssh/sshd_config",
    source="./configs/sshd_config",
    mode=0o600,
    owner="root",
    group="root"
)
```

### Systemd Service

```python
File(
    "/etc/systemd/system/myapp.service",
    template="./templates/myapp.service.j2",
    vars={
        "user": "www-data",
        "working_directory": "/opt/apps/myapp",
        "exec_start": "/opt/apps/myapp/start.sh"
    },
    mode=0o644
)
```

### Nginx Configuration

```python
File(
    "/etc/nginx/sites-available/myapp",
    template="./templates/nginx.conf.j2",
    vars={
        "domain": "myapp.com",
        "port": 3000,
        "ssl_cert": "/etc/letsencrypt/live/myapp.com/fullchain.pem",
        "ssl_key": "/etc/letsencrypt/live/myapp.com/privkey.pem"
    }
)
```

### Remove Old Files

```python
# Remove temporary files
File("/tmp/old-cache", ensure="absent")
File("/tmp/old-logs", ensure="absent")
```

## File Modes

Common permission patterns:

| Mode      | Octal | Usage                             |
| --------- | ----- | --------------------------------- |
| rw-r--r-- | 0o644 | Regular files (config, data)      |
| rwxr-xr-x | 0o755 | Executables, directories          |
| rw------- | 0o600 | Sensitive files (keys, passwords) |
| rwx------ | 0o700 | Sensitive directories             |
| rw-rw-r-- | 0o664 | Shared files                      |
| rwxrwxr-x | 0o775 | Shared directories                |

Examples:

```python
# Configuration file readable by all
File("/etc/app.conf", content="config", mode=0o644)

# Private SSH key
File("/home/user/.ssh/id_rsa", source="./id_rsa", mode=0o600)

# Executable script
File("/usr/local/bin/deploy.sh", source="./deploy.sh", mode=0o755)

# Web root directory
File("/var/www/html", ensure="directory", mode=0o755)
```

## Idempotency

File resources are idempotent. Repeated application produces the same result.

### Content Changes

Files are updated only when content differs:

```python
File("/etc/motd", content="Welcome v1")
# First run: Creates file
# Second run: No changes
```

```python
File("/etc/motd", content="Welcome v2")
# Detects content change, updates file
```

### Permission Changes

Permissions are updated only when they differ:

```python
File("/var/www/index.html", content="<h1>Hello</h1>", mode=0o644)
# First run: Creates with mode 0o644
# Second run: No changes

File("/var/www/index.html", content="<h1>Hello</h1>", mode=0o444)
# Detects mode change, updates permissions
```

## Platform Compatibility

File resources work across platforms with automatic command adaptation:

- **Linux**: Uses GNU coreutils (stat, chmod, chown)
- **macOS**: Uses BSD versions of commands
- **stat format**: Automatically detects GNU vs BSD stat

The resource handles platform differences transparently.

## Security Considerations

### Sensitive Files

Protect sensitive files with restrictive permissions:

```python
# SSH private key
File(
    "/home/deploy/.ssh/id_rsa",
    source="./keys/deploy_rsa",
    mode=0o600,
    owner="deploy",
    group="deploy"
)

# Database credentials
File(
    "/etc/app/db_password",
    content=os.getenv("DB_PASSWORD"),
    mode=0o600,
    owner="app",
    group="app"
)
```

### Directory Permissions

Restrict directory access when containing sensitive data:

```python
# Application secrets directory
File(
    "/var/secrets",
    ensure="directory",
    mode=0o700,
    owner="app"
)

# SSL certificate directory
File(
    "/etc/ssl/private",
    ensure="directory",
    mode=0o710,
    owner="root",
    group="ssl-cert"
)
```

### Template Variables

Avoid embedding secrets directly in templates. Use environment variables:

```python
import os

File(
    "/etc/app/config.yml",
    template="./config.yml.j2",
    vars={
        "api_key": os.getenv("API_KEY"),
        "db_password": os.getenv("DB_PASSWORD")
    },
    mode=0o600
)
```

## Common Patterns

### Multi-File Application Setup

```python
from cook import File

APP_DIR = "/opt/apps/myapp"

# Directory structure
File(APP_DIR, ensure="directory", mode=0o755)
File(f"{APP_DIR}/config", ensure="directory", mode=0o755)
File(f"{APP_DIR}/data", ensure="directory", mode=0o750, owner="app")
File(f"{APP_DIR}/logs", ensure="directory", mode=0o755, owner="app")

# Configuration files
File(f"{APP_DIR}/config/app.yml", template="./app.yml.j2", vars={...})
File(f"{APP_DIR}/config/database.yml", template="./db.yml.j2", vars={...})

# Application files
File(f"{APP_DIR}/start.sh", source="./start.sh", mode=0o755)
```

### Configuration Management

```python
# Environment-specific configuration
env = os.getenv("ENV", "production")

File(
    "/etc/app/config.yml",
    template="./config.yml.j2",
    vars={
        "environment": env,
        "debug": env == "development",
        "log_level": "debug" if env == "development" else "info"
    }
)
```

## API Reference

See [cook/resources/file.py](https://github.com/gleicon/cook/blob/main/cook/resources/file.py) for complete source code and implementation details.
