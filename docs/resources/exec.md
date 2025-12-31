# Exec Resource

Execute arbitrary commands with idempotency guards and security validation.

## Overview

The Exec resource runs shell commands:

- Execute commands with idempotency guards
- Conditional execution (creates, unless, only_if)
- Environment variables and working directory
- Security validation for command injection
- Dry-run mode for safe testing
- Command change tracking

## Security

**IMPORTANT:** Exec runs commands via shell. Enable security validation to prevent command injection.

### Safe by Default

Security validation is enabled by default:

```python
from cook import Exec

# Safe mode enabled automatically
Exec("backup", command="tar czf /backup/data.tar.gz /var/data")
```

### Security Levels

| Level    | Behavior                           |
| -------- | ---------------------------------- |
| `strict` | Block dangerous patterns (default) |
| `warn`   | Warn but allow dangerous patterns  |
| `none`   | No validation (dangerous)          |

```python
# Strict mode (default)
Exec("backup", command="tar czf /backup/data.tar.gz /var/data", security_level="strict")

# Warning mode
Exec("backup", command="tar czf /backup/data.tar.gz /var/data", security_level="warn")

# No validation (use with extreme caution)
Exec("backup", command="tar czf /backup/data.tar.gz /var/data", security_level="none")
```

## Basic Usage

### Simple Command

```python
from cook import Exec

Exec("update-cache", command="apt-get update")
```

### Idempotent Execution

Use guards to make commands idempotent:

```python
# Run only if file doesn't exist
Exec(
    "download-installer",
    command="curl -o /tmp/installer.sh https://example.com/install.sh",
    creates="/tmp/installer.sh"
)
```

### Conditional Execution

```python
# Run only if condition fails
Exec(
    "install-composer",
    command="curl -sS https://getcomposer.org/installer | php",
    unless="which composer"
)

# Run only if condition succeeds
Exec(
    "setup-database",
    command="mysql < /tmp/schema.sql",
    only_if="systemctl is-active mysql"
)
```

## Parameters

### name

**Required**. Resource identifier and description.

```python
Exec("backup-database", command="...")
```

### command

**Required**. Shell command to execute.

```python
Exec("update", command="apt-get update")
```

### creates

Only run command if this file or directory does not exist.

```python
Exec(
    "create-database",
    command="createdb myapp",
    creates="/var/lib/postgresql/data/myapp"
)
```

After first run, file exists, command will not run again.

### unless

Only run command if this guard command fails (returns non-zero exit code).

```python
Exec(
    "install-nodejs",
    command="curl -fsSL https://deb.nodesource.com/setup_20.x | bash -",
    unless="which node"
)
```

If `which node` succeeds (node installed), command does not run.

### only_if

Only run command if this guard command succeeds (returns zero exit code).

```python
Exec(
    "restart-app",
    command="systemctl restart myapp",
    only_if="systemctl is-active myapp"
)
```

Only restarts if service is currently active.

### cwd

Working directory for command execution.

```python
Exec(
    "build-app",
    command="npm run build",
    cwd="/opt/apps/myapp"
)
```

Equivalent to:

```bash
cd /opt/apps/myapp && npm run build
```

### environment

Environment variables for command.

```python
Exec(
    "deploy",
    command="./deploy.sh",
    environment={
        "ENVIRONMENT": "production",
        "API_KEY": "secret-key"
    }
)
```

### dry_run

Preview mode. Shows what would be executed without running the command.

```python
Exec(
    "deploy",
    command="./deploy.sh",
    dry_run=True
)
```

### safe_mode

Enable security validation. Default: `True`.

**Recommended:** Keep enabled unless you have a specific reason to disable it.

```python
# Safe mode enabled (default)
Exec("backup", command="tar czf /backup/data.tar.gz /var/data")

# Disable with extreme caution
Exec("backup", command="tar czf /backup/data.tar.gz /var/data", safe_mode=False)
```

### allow_pipes

Allow pipe character (|) in commands. Default: `True`.

```python
Exec(
    "process-logs",
    command="cat /var/log/app.log | grep ERROR",
    allow_pipes=True
)
```

### allow_redirects

Allow redirect characters (>, <) in commands. Default: `True`.

```python
Exec(
    "save-output",
    command="echo 'data' > /tmp/output.txt",
    allow_redirects=True
)
```

## Idempotency Guards

Use guards to ensure commands run only when needed.

### creates Guard

Run only if file does not exist:

```python
Exec(
    "download-file",
    command="curl -o /tmp/data.json https://api.example.com/data",
    creates="/tmp/data.json"
)
# First run: Downloads file
# Second run: File exists, skips download
```

### unless Guard

Run only if guard command fails:

```python
Exec(
    "install-docker",
    command="curl -fsSL https://get.docker.com | sh",
    unless="which docker"
)
# If docker not installed: Runs installer
# If docker installed: Skips installation
```

### only_if Guard

Run only if guard command succeeds:

```python
Exec(
    "backup-database",
    command="pg_dump myapp > /backup/myapp.sql",
    only_if="systemctl is-active postgresql"
)
# Only runs if PostgreSQL is active
```

### Combining Guards

```python
Exec(
    "setup-database",
    command="mysql < /tmp/schema.sql",
    creates="/var/lib/mysql/myapp/users.frm",
    only_if="systemctl is-active mysql"
)
# Runs only if:
# 1. MySQL is active (only_if)
# 2. Table file doesn't exist (creates)
```

## Examples

### System Setup Commands

```python
from cook import Exec

# Update package cache
Exec("apt-update", command="apt-get update")

# Set timezone
Exec(
    "set-timezone",
    command="timedatectl set-timezone America/New_York",
    unless="timedatectl | grep 'America/New_York'"
)

# Set hostname
Exec(
    "set-hostname",
    command="hostnamectl set-hostname webserver01",
    unless="hostname | grep webserver01"
)
```

### Download and Install

```python
# Download installer
Exec(
    "download-installer",
    command="curl -fsSL https://get.docker.com -o /tmp/get-docker.sh",
    creates="/tmp/get-docker.sh"
)

# Run installer
Exec(
    "install-docker",
    command="sh /tmp/get-docker.sh",
    unless="which docker"
)
```

### Database Operations

```python
# Create database
Exec(
    "create-database",
    command="createdb myapp",
    creates="/var/lib/postgresql/data/myapp",
    only_if="systemctl is-active postgresql"
)

# Import schema
Exec(
    "import-schema",
    command="psql myapp < /tmp/schema.sql",
    unless="psql myapp -c '\\dt' | grep users"
)

# Create database user
Exec(
    "create-db-user",
    command="createuser -P myapp_user",
    unless="psql -c '\\du' | grep myapp_user"
)
```

### SSL Certificates

```python
from cook import Exec
import os

domain = os.getenv("DOMAIN", "example.com")
email = os.getenv("ADMIN_EMAIL", "admin@example.com")

# Obtain Let's Encrypt certificate
Exec(
    "certbot-obtain",
    command=f"certbot certonly --nginx -d {domain} --non-interactive --agree-tos -m {email}",
    creates=f"/etc/letsencrypt/live/{domain}/fullchain.pem"
)
```

### Application Deployment

```python
from cook import Exec, File

# Application directory
File("/opt/apps/myapp", ensure="directory")

# Clone repository
Exec(
    "clone-repo",
    command="git clone https://github.com/user/myapp.git /opt/apps/myapp",
    creates="/opt/apps/myapp/.git"
)

# Install dependencies
Exec(
    "install-deps",
    command="npm install --production",
    cwd="/opt/apps/myapp",
    unless="test -d /opt/apps/myapp/node_modules"
)

# Build application
Exec(
    "build-app",
    command="npm run build",
    cwd="/opt/apps/myapp",
    environment={"NODE_ENV": "production"}
)
```

### Docker Operations

```python
# Pull Docker image
Exec(
    "pull-image",
    command="docker pull nginx:latest",
    unless="docker image inspect nginx:latest"
)

# Run container
Exec(
    "run-container",
    command="docker run -d --name web -p 80:80 nginx",
    unless="docker ps | grep web"
)

# Docker Compose
Exec(
    "compose-up",
    command="docker-compose up -d",
    cwd="/opt/apps/myapp",
    creates="/opt/apps/myapp/.deployed"
)
```

### Systemd Daemon Reload

```python
from cook import File, Exec

# Create service file
service_file = File(
    "/etc/systemd/system/myapp.service",
    source="./myapp.service"
)

# Reload systemd after service file changes
Exec(
    "systemd-reload",
    command="systemctl daemon-reload"
)
```

## Security Considerations

### Command Injection Prevention

Security validation blocks dangerous patterns:

**Blocked Patterns:**
- Command chaining: `;`, `&&`, `||`
- Command substitution: `$(...)`, `` `...` ``
- Variable expansion: `${...}`
- Newline injection: `\n`, `\r`

**Allowed with Flags:**
- Pipes: `|` (allowed if `allow_pipes=True`)
- Redirects: `>`, `<` (allowed if `allow_redirects=True`)

### Safe Commands

```python
# Safe: Static paths, no user input
Exec("backup", command="tar czf /backup/data.tar.gz /var/data")

# Safe: Using creates guard
Exec(
    "download",
    command="curl -o /tmp/file.tar.gz https://example.com/file.tar.gz",
    creates="/tmp/file.tar.gz"
)
```

### Unsafe Commands

```python
# UNSAFE: User input in command
user_file = input()  # User input!
Exec("backup", command=f"tar czf /backup/{user_file}")  # DANGEROUS!

# UNSAFE: Shell variable expansion
Exec("delete", command="rm -rf $TEMP_DIR")  # Variable could be anything!
```

### Environment Variables

Use environment parameter instead of embedding in command:

```python
# Good: Environment variables passed separately
Exec(
    "deploy",
    command="./deploy.sh",
    environment={"API_KEY": "secret"}
)

# Avoid: Environment variables in command
Exec("deploy", command="API_KEY=secret ./deploy.sh")
```

### Dangerous Commands

Security validation warns about:

- `rm -rf /` - Recursive delete from root
- `dd if=/dev/` - Disk operations
- `mkfs.` - Format filesystem
- `chmod 777` - World-writable permissions
- `curl ... | bash` - Pipe to shell
- `eval` - Code evaluation

### Dry Run Testing

Test commands safely with dry-run mode:

```python
# Test without executing
Exec(
    "deploy",
    command="./deploy.sh",
    dry_run=True
)
# Shows what would be executed, but doesn't run it
```

## Working Directory and Environment

### Change Working Directory

```python
Exec(
    "build",
    command="npm run build",
    cwd="/opt/apps/myapp"
)
```

Equivalent to:

```bash
cd /opt/apps/myapp && npm run build
```

### Set Environment Variables

```python
Exec(
    "compile",
    command="gcc -o app main.c",
    environment={
        "CC": "gcc",
        "CFLAGS": "-O2 -Wall"
    }
)
```

Equivalent to:

```bash
CC=gcc CFLAGS='-O2 -Wall' gcc -o app main.c
```

### Combined

```python
Exec(
    "deploy",
    command="./deploy.sh",
    cwd="/opt/apps/myapp",
    environment={
        "ENVIRONMENT": "production",
        "LOG_LEVEL": "info"
    }
)
```

## Platform Compatibility

Exec resources work on all platforms that support shell commands:

- **Linux**: Uses `/bin/sh` or `/bin/bash`
- **macOS**: Uses `/bin/sh` or `/bin/bash`
- **Other Unix-like systems**: Uses default shell

Platform-specific commands:

```python
# Linux-specific
Exec("update", command="apt-get update")

# macOS-specific
Exec("update", command="brew update")
```

## Troubleshooting

### Command Not Found

Ensure command is in PATH or use full path:

```python
# May fail if not in PATH
Exec("backup", command="mybackup.sh")

# Better: Use full path
Exec("backup", command="/usr/local/bin/mybackup.sh")
```

### Guard Command Fails

Check guard command independently:

```bash
# Test unless guard
which docker  # Should return 0 if installed

# Test only_if guard
systemctl is-active postgresql  # Should return 0 if active
```

### Security Validation Errors

Review command for dangerous patterns:

```python
# Error: Command chaining
Exec("multi", command="cmd1 && cmd2")  # BLOCKED

# Fix: Use separate Exec resources
Exec("cmd1", command="cmd1")
Exec("cmd2", command="cmd2")
```

### Environment Variables Not Working

Verify environment variable syntax:

```python
# Correct
Exec(
    "deploy",
    command="./deploy.sh",
    environment={"API_KEY": "secret"}
)

# Incorrect (command string)
Exec("deploy", command="API_KEY=secret ./deploy.sh")
```

## Limitations

### No Streaming Output

Command output is returned after execution completes. Long-running commands may appear to hang.

### Shell Dependency

Exec requires a shell to execute commands. Some minimal containers may not have a shell.

### No Interactive Commands

Commands requiring user input will hang. Use non-interactive flags:

```python
# Good: Non-interactive
Exec("install", command="apt-get install -y nginx")

# Bad: Would hang waiting for input
Exec("install", command="apt-get install nginx")
```

## API Reference

See [cook/resources/exec.py](https://github.com/gleicon/cook/blob/main/cook/resources/exec.py) for complete source code and implementation details.
