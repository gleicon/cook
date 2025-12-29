# Cook

Configuration management in Python.

## Features

- Pure Python configuration (no YAML/DSL)
- Drift detection and auto-correction
- Recording mode to capture manual changes
- MCP server for AI integration
- SSH transport with sudo support

## Quick Start

```python
from cook import File, Package, Service

Package("nginx")

File("/etc/nginx/nginx.conf",
     content="""
     events { worker_connections 1024; }
     http {
         server {
             listen 80;
             location / { return 200 'Hello'; }
         }
     }
     """,
     mode=0o644)

Service("nginx", running=True, enabled=True)
```

```bash
cook plan server.py
cook apply server.py
cook apply server.py --host prod-1.example.com --user admin --sudo
```

## Installation

Using uv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
cd cook-py
uv venv
uv pip install -e ".[all]"
source .venv/bin/activate
```

Using pip:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
```

## Core Resources

- **File** - Files, directories, templates (Jinja2)
- **Package** - apt, dnf, pacman, brew
- **Service** - systemd, launchctl
- **Exec** - Commands with idempotency guards

## Commands

```bash
cook plan <config>              # Preview changes
cook apply <config>             # Apply changes
cook state list                 # List managed resources
cook state show <resource>      # Show resource state
cook state history <resource>   # Show change history
cook state drift                # Show drifted resources
cook check-drift                # Detect drift
cook check-drift --fix          # Fix drift
sudo cook record start          # Start recording
cook record generate <file>     # Generate config from recording
```

## SSH Transport

```bash
cook plan server.py --host example.com --user admin --sudo
cook apply server.py --host example.com --user admin --key ~/.ssh/id_rsa --sudo
```

## Service Reload Triggers

```python
from cook import File, Service

nginx_conf = File("/etc/nginx/nginx.conf", source="./nginx.conf")
site_conf = File("/etc/nginx/sites-available/mysite", source="./site.conf")

Service("nginx", running=True, reload_on=[nginx_conf, site_conf])
```

## Testing

```bash
pytest tests/unit/
sudo pytest tests/integration/
./scripts/run-vm-tests.sh
```

See [tests/README.md](tests/README.md).

## Examples

- **simple.py** - Basic file operations
- **lemp-stack.py** - LEMP stack (Linux, Nginx, MySQL, PHP)
- **wordpress.py** - WordPress with MySQL
- **wordpress-pgsql.py** - WordPress with PostgreSQL
- **multi-server/database.py** - PostgreSQL database server

See [examples/README.md](examples/README.md).

## Comparison

| Feature | Cook | Ansible | Pyinfra | Terraform |
|---------|------|---------|---------|-----------|
| Language | Python | YAML | Python | HCL |
| Drift Detection | Yes | No | No | Yes |
| Recording Mode | Yes | No | No | No |
| AI Integration | Yes | No | No | No |

## Status

Beta. All core and advanced features implemented:

- Core resource pattern (Check/Plan/Apply)
- File, Package, Service, Exec resources
- CLI (plan/apply/state/record)
- Platform detection (Linux/macOS)
- SSH transport with sudo
- State persistence and history
- Drift monitoring
- Recording mode (PTY-based)
- MCP server for AI assistance

## Background

Python rewrite of Lathe (Go + Starlark). Offers native Python configuration, simpler codebase, Jinja2 templates, Paramiko SSH transport.

## License

MIT
