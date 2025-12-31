# Resources Overview

Resources are the fundamental building blocks in Cook. Each resource represents a desired state of a system component.

## Resource Types

Cook provides five core resource types:

### [File](file.md)

Manage files, directories, and templates.

```python
File("/etc/app/config.json",
     content='{"port": 8080}',
     mode=0o644,
     owner="app",
     group="app")
```

**Use for:**

- Configuration files
- Directory structures
- File permissions
- Template rendering (Jinja2)

### [Package](package.md)

Install and manage system packages.

```python
Package("nginx")

Package("dev-tools", packages=[
    "git",
    "curl",
    "vim"
])
```

**Use for:**

- Installing software
- Managing package versions
- Removing packages

### [Repository](repository.md)

Manage package repositories and system updates.

```python
Repository("apt-update", action="update")
Repository("apt-upgrade", action="upgrade")

Repository("docker",
           repo="deb https://download.docker.com/linux/ubuntu focal stable",
           key_url="https://download.docker.com/linux/ubuntu/gpg")
```

**Use for:**

- Updating package cache
- System upgrades
- Adding third-party repositories
- Managing GPG keys

### [Service](service.md)

Control system services.

```python
Service("nginx",
        running=True,
        enabled=True)
```

**Use for:**

- Starting/stopping services
- Enabling services at boot
- Service reload triggers

### [Exec](exec.md)

Execute commands with idempotency guards.

```python
Exec("setup-database",
     command="mysql < /tmp/schema.sql",
     creates="/var/lib/mysql/app_db")
```

**Use for:**

- One-time setup commands
- Conditional execution
- Custom operations

## Resource Pattern

All resources follow the Check-Plan-Apply pattern:

### Check

Inspect current system state.

```python
resource.check(platform)
# Returns: {"exists": True, "content": "...", ...}
```

### Plan

Compare current state to desired state.

```python
plan = resource.plan(platform)
# Returns: Plan(action=Action.UPDATE, changes=[...])
```

### Apply

Execute changes to reach desired state.

```python
resource.apply(plan, platform)
```

## Common Parameters

Most resources support these parameters:

**name**

Resource identifier. Must be unique within resource type.

```python
Package("nginx")  # name="nginx"
```

**ensure**

Desired state: "present" or "absent"

```python
Package("apache2", ensure="absent")
```

## Resource Registration

Resources automatically register with the global executor:

```python
from cook import Package

# Automatically registered
Package("nginx")
Package("curl")
```

Access registered resources:

```python
from cook.core.executor import get_executor

executor = get_executor()
resources = executor.list_resources()
```

## Dependencies

Resources execute in registration order. Use explicit ordering for dependencies:

```python
# Install nginx first
Package("nginx")

# Then configure
nginx_conf = File("/etc/nginx/nginx.conf", source="./nginx.conf")

# Then start with reload trigger
Service("nginx",
        running=True,
        enabled=True,
        reload_on=[nginx_conf])
```

## Platform Detection

Resources adapt to the platform automatically:

```python
from cook.core import Platform

platform = Platform.detect()
# Platform(system='Linux', distro='ubuntu', version='22.04', arch='x86_64')
```

Supported platforms:

- Ubuntu/Debian (apt)
- Fedora/RHEL (dnf)
- Arch Linux (pacman)
- macOS (brew, launchctl)

## Error Handling

Resources raise exceptions on failure:

```python
try:
    from cook.core.executor import Executor
    executor = Executor()
    result = executor.apply()
except RuntimeError as e:
    print(f"Apply failed: {e}")
```

## State Tracking

Enable state persistence:

```python
from cook.core.executor import Executor

executor = Executor()
executor.enable_state_tracking()

# State stored in SQLite database
```

## Resource Reference

Detailed documentation for each resource type:

- [File Resource](file.md)
- [Package Resource](package.md)
- [Repository Resource](repository.md)
- [Service Resource](service.md)
- [Exec Resource](exec.md)
