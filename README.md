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

## Foundations of Cook Workflows:

- Resource is a unit of configuration that represents a desired state of a system.
- Plan is a collection of resources that represent a desired state of a system.
- Action is a unit of work that can be performed on a resource.
- File is a unit of configuration that represents a desired state of a file.
- Package is a unit of configuration that represents a desired state of a package.
  - Repository is a support of the Package system, it represents system updates and repository management
- Service is a unit of configuration that represents a desired state of a service.
- Exec is a unit of configuration that represents a desired state of an executable.

### Core Resources

Resources are abstractions for Operational System and Configuration building blocks. Technically speaking:

- **File** - Files, directories, templates (based on Jinja2)
- **Package** - apt, dnf, pacman, brew
- **Repository** - Package repositories, system updates, and repository management
- **Service** - systemd, launchctl
- **Exec** - Execute commands with safety guards

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
sudo cook record start          # Start recording (requires pty access)
cook record generate <file>     # Generate config from recording
```

## SSH Transport


Commands can be applied locally or remotely. The locality abstraction is named `Transport`. The most used `Transport` is based on SSH. 

You could either install `cook` and your programs on a server and run it locally - enforcing a periodic drift check by cron and emulating a traditional configuration management approach - or run it remotely through SSH more in a image creation fashion like `Ansible`.

Apart from that, the difference would be where the state is stored.

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

## Resource Redefinition (Multi-Phase Configurations)

Cook supports redefining resources at different phases of deployment. When a resource with the same path is defined multiple times, the **last definition wins**, enabling progressive refinement patterns.

**Use Case:** TLS certificate setup requires different nginx configurations at different phases:

```python
from cook import File, Exec

# Phase 1: HTTP-only config (for Let's Encrypt verification)
File(
    "/etc/nginx/sites-available/mysite.com",
    template="nginx.conf.j2",
    vars={"ssl_enabled": False}
)

# Obtain certificate using HTTP-01 challenge
Exec(
    "certbot-obtain",
    command="certbot certonly --nginx -d mysite.com ...",
    creates="/etc/letsencrypt/live/mysite.com/fullchain.pem"
)

# Phase 2: Update config to enable HTTPS (replaces previous definition)
File(
    "/etc/nginx/sites-available/mysite.com",
    template="nginx.conf.j2",
    vars={"ssl_enabled": True}
)
```

**Key Benefits:**
- **Natural workflow expression**: No workarounds or temporary file names needed
- **Maintains execution order**: Resource position is preserved even when redefined
- **Idiomatic pattern**: Matches behavior of mature IaC tools (Puppet, Ansible)

**See:** `examples/minimidia/minimidia.py` for a complete real-world example.

## Repository Management

Manage package repositories, system updates, and package manager operations:

```python
from cook import Repository, Package

# Update package cache
Repository("apt-update", action="update")

# Upgrade all packages
Repository("apt-upgrade", action="upgrade")

# Example: Add NodeSource repository for Node.js
Repository(
    "nodesource",
    action="add",
    repo="deb https://deb.nodesource.com/node_20.x nodistro main",
    key_url="https://deb.nodesource.com/gpgkey/nodesource.gpg.key",
    filename="nodesource.list"
)

# Example: Add Docker repository
Repository(
    "docker",
    action="add",
    repo="deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable",
    key_url="https://download.docker.com/linux/ubuntu/gpg",
    filename="docker.list"
)

# Update cache after adding repositories
Repository("apt-update-repos", action="update")

# Now install packages from the new repositories
Package("nodejs")
Package("docker-ce")
```

### Repository Actions

- **update**: Update package cache (apt-get update, dnf check-update, etc.)
- **upgrade**: Upgrade all packages (apt-get upgrade, dnf upgrade, etc.)
- **add**: Add a new repository with optional GPG key

### Supported Package Managers

- **apt** (Debian/Ubuntu): Full support for repositories, keys, and PPAs
- **dnf** (Fedora/RHEL): Repository management with GPG keys
- **pacman** (Arch Linux): Repository configuration
- **brew** (macOS): Tap management

### Ubuntu PPAs

```python
# Add a PPA (Ubuntu/Debian)
Repository(
    "ondrej-php",
    action="add",
    ppa="ppa:ondrej/php"
)
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
- **minimidia.py** - Complete SaaS infrastructure with Node.js, Nginx, TLS, Docker
- **minimidia-env.py** - Multi-environment deployment (dev/staging/prod)
- **wordpress.py** - WordPress with MySQL
- **wordpress-pgsql.py** - WordPress with PostgreSQL
- **multi-server/database.py** - PostgreSQL database server

See [examples/README.md](examples/README.md).

## Comparison

The chart below is not a benchmark or a pros/cons comparison. It is a radar of where cook sits. All these frameworks are established, have companies behind them and serve thousands of Enterprise customers to their merit.

| Feature         | Cook   | Ansible | Pyinfra | Terraform |
| --------------- | ------ | ------- | ------- | --------- |
| Language        | Python | YAML    | Python  | HCL       |
| Drift Detection | Yes    | No      | No      | Yes       |
| Recording Mode  | Yes    | No      | No      | No        |
| AI Integration  | Yes    | No      | No      | No        |

## Project Status

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
