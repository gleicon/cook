# Cook

## TL;DR

Configuration management in Python for the Impatient.

## Long form

Once upon a time configuration management was all that we had. Chef, CFEngine, Ansible, Puppet, Saltstack and others were the way to scale out teams and keep consistent production environments. 

After a while we got Docker and Dockerfile became the way to express an image that could be changed or thrown away not package by package but entirely. 

This is good and practical but at the same time, the effort on configuration management drifted to infrastructure as code, led by Terraform and others and configuring a VM was a side consideration - as IaC was at the height of server configuration management, it is a pendulum.

Getting back to a simple server configuration approach served me as I had to migrate apps from cloud to physical servers and the provisioning was limited. I also wanted to express the quick-and-dirty without having to learn an enterprise framework - which all of the above became and also without having to vibe code shell scripts downloadable by curl.

Hence cook, a Pythonic way to describe and manage a server configuration, which can be tested, dry ran and also connect with other ways of communicating to servers. 

It comes with a recorder kind of like Ascii Cinema where it see how you like to configure your server, learn from it and create code that can replicate it.

There is also a MCP server which can be configured on your preferred coding agent to transform it into a sysadmin. Having provisioning instructions translated to code is safer than letting your agent learn your cloud cli and hallucinate over it.

It works for containers, for big servers and for fleet of virtual machines all the same. Being a python application opens up to integration, better observability and drift control and translator of other frameworks and configurations.

## Features

- Pure Python configuration (no YAML/DSL)
- Drift detection and auto-correction
- Recording mode to capture manual changes (learning mode)
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

| Feature         | Cook   | Ansible | Pyinfra | Terraform |
| --------------- | ------ | ------- | ------- | --------- |
| Language        | Python | YAML    | Python  | HCL       |
| Drift Detection | Yes    | No      | No      | Yes       |
| Recording Mode  | Yes    | No      | No      | No        |
| AI Integration  | Yes    | No      | No      | No        |

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
