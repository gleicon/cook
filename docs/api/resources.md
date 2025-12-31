# Resources API

Guide to using and creating Cook resources.

## Overview

Resources are the building blocks of Cook configurations. Each resource represents a piece of desired system state.

## Built-in Resources

Cook provides five core resources:

| Resource                                 | Purpose                      | Example                                     |
| ---------------------------------------- | ---------------------------- | ------------------------------------------- |
| [File](../resources/file.md)             | Manage files and directories | `File("/etc/motd", content="...")`          |
| [Package](../resources/package.md)       | Install system packages      | `Package("nginx")`                          |
| [Repository](../resources/repository.md) | Manage package repositories  | `Repository("apt-update", action="update")` |
| [Service](../resources/service.md)       | Manage system services       | `Service("nginx", running=True)`            |
| [Exec](../resources/exec.md)             | Run arbitrary commands       | `Exec("backup", command="...")`             |

## Resource Lifecycle

All resources follow the Check-Plan-Apply pattern:

### 1. Check Phase

Resource inspects current system state:

```python
from cook import File

file = File("/etc/motd", content="Welcome")
# During check phase, reads /etc/motd
# Returns: {"exists": True, "content": "Old message"}
```

### 2. Plan Phase

Cook compares actual vs desired state:

```python
# Actual state:  {"exists": True, "content": "Old message"}
# Desired state: {"exists": True, "content": "Welcome"}

# Generated plan:
# Action: UPDATE
# Changes:
#   content: "Old message" → "Welcome"
```

### 3. Apply Phase

Resource executes changes:

```python
# Writes "Welcome" to /etc/motd
```

## Resource Identity

Each resource has a unique ID:

```python
from cook import File, Package

file = File("/etc/motd", content="Welcome")
print(file.id)  # "file:/etc/motd"

pkg = Package("nginx")
print(pkg.id)  # "pkg:nginx"
```

ID format: `{resource_type}:{name}`

## Resource Dependencies

Resources automatically track dependencies through references:

### Reload on Change

```python
from cook import File, Service

# Configuration file
nginx_conf = File("/etc/nginx/nginx.conf", source="./nginx.conf")

# Service reloads when config changes
Service("nginx", running=True, reload_on=[nginx_conf])
```

### Restart on Change

```python
from cook import File, Service

# Application binary
app_binary = File("/usr/local/bin/app", source="./app", mode=0o755)

# Service restarts when binary changes
Service("app", running=True, restart_on=[app_binary])
```

### Execution Order

Cook automatically orders resources based on dependencies:

```python
from cook import File, Package, Service

# Cook executes in this order:
Package("nginx")                                    # 1. Install first
config = File("/etc/nginx/nginx.conf", ...)        # 2. Then configure
Service("nginx", running=True, reload_on=[config]) # 3. Then manage service
```

## Resource Parameters

### Common Parameters

All resources support these parameters:

```python
from cook import File

File(
    "/etc/motd",
    content="Welcome",
    # Common parameters:
    # (none currently - resource-specific)
)
```

### Resource-Specific Parameters

Each resource type has its own parameters:

```python
# File resource
File(
    path="/etc/motd",
    content="Welcome",      # File-specific
    mode=0o644,            # File-specific
    owner="root"           # File-specific
)

# Package resource
Package(
    name="nginx",
    version="1.18.0",      # Package-specific
    ensure="present"       # Package-specific
)

# Service resource
Service(
    name="nginx",
    running=True,          # Service-specific
    enabled=True,          # Service-specific
    reload_on=[...]        # Service-specific
)
```

## Creating Custom Resources

### Basic Custom Resource

```python
from cook.core import Resource, Platform, Plan, Action
from cook.core.executor import get_executor
from typing import Dict, Any

class DatabaseUser(Resource):
    """Create database users."""

    def __init__(self, username: str, password: str, database: str, **options):
        super().__init__(username, **options)
        self.username = username
        self.password = password
        self.database = database

        # Auto-register with executor
        get_executor().add(self)

    def resource_type(self) -> str:
        return "dbuser"

    def check(self, platform: Platform) -> Dict[str, Any]:
        """Check if user exists."""
        cmd = f"psql -c \"SELECT 1 FROM pg_user WHERE usename='{self.username}'\""
        output, code = self._transport.run_shell(cmd)

        return {
            "exists": code == 0 and "1 row" in output
        }

    def desired_state(self) -> Dict[str, Any]:
        """User should exist."""
        return {
            "exists": True
        }

    def apply(self, plan: Plan, platform: Platform) -> None:
        """Create user."""
        if plan.action == Action.CREATE:
            cmd = f"psql -c \"CREATE USER {self.username} WITH PASSWORD '{self.password}'\""
            self._transport.run_shell(cmd)

            # Grant access
            cmd = f"psql -c \"GRANT ALL ON DATABASE {self.database} TO {self.username}\""
            self._transport.run_shell(cmd)
```

### Using Custom Resource

```python
# Create database user
DatabaseUser("app_user", password="secret", database="myapp")

# Execute
from cook.core.executor import get_executor
from cook.core import Platform

executor = get_executor()
platform = Platform.detect()
executor.execute(platform)
```

### Advanced Custom Resource

With update and delete support:

```python
class GitRepository(Resource):
    """Manage git repositories."""

    def __init__(self, path: str, url: str, branch: str = "main", **options):
        super().__init__(path, **options)
        self.path = path
        self.url = url
        self.branch = branch
        get_executor().add(self)

    def resource_type(self) -> str:
        return "git"

    def check(self, platform: Platform) -> Dict[str, Any]:
        """Check repository state."""
        if not self._transport.file_exists(f"{self.path}/.git"):
            return {"exists": False, "branch": None, "url": None}

        # Get current branch
        output, _ = self._transport.run_shell(
            f"cd {self.path} && git rev-parse --abbrev-ref HEAD"
        )
        current_branch = output.strip()

        # Get remote URL
        output, _ = self._transport.run_shell(
            f"cd {self.path} && git config --get remote.origin.url"
        )
        current_url = output.strip()

        return {
            "exists": True,
            "branch": current_branch,
            "url": current_url
        }

    def desired_state(self) -> Dict[str, Any]:
        """Desired repository state."""
        return {
            "exists": True,
            "branch": self.branch,
            "url": self.url
        }

    def apply(self, plan: Plan, platform: Platform) -> None:
        """Apply git operations."""
        if plan.action == Action.CREATE:
            # Clone repository
            self._transport.run_command(
                ["git", "clone", "-b", self.branch, self.url, self.path]
            )

        elif plan.action == Action.UPDATE:
            # Handle changes
            for change in plan.changes:
                if change.field == "branch":
                    # Checkout branch
                    self._transport.run_shell(
                        f"cd {self.path} && git checkout {change.to_value}"
                    )
                elif change.field == "url":
                    # Update remote
                    self._transport.run_shell(
                        f"cd {self.path} && git remote set-url origin {change.to_value}"
                    )

        elif plan.action == Action.DELETE:
            # Remove repository
            self._transport.run_command(["rm", "-rf", self.path])
```

## Resource Best Practices

### Idempotency

Resources should be idempotent - safe to run multiple times:

```python
def check(self, platform: Platform) -> Dict[str, Any]:
    # Always check current state accurately
    exists = self._transport.file_exists(self.path)
    return {"exists": exists}

def apply(self, plan: Plan, platform: Platform) -> None:
    # Only make changes when needed
    if plan.action == Action.CREATE:
        # Create only if doesn't exist
        pass
```

### Error Handling

Validate inputs and handle errors:

```python
def __init__(self, name: str, value: str):
    # Validate inputs
    if not name:
        raise ValueError("name cannot be empty")
    if not value:
        raise ValueError("value cannot be empty")

    super().__init__(name)

def apply(self, plan: Plan, platform: Platform) -> None:
    # Check command success
    output, code = self._transport.run_command(["mycommand"])
    if code != 0:
        raise RuntimeError(f"Command failed: {output}")
```

### Platform Detection

Use platform information for cross-platform resources:

```python
def apply(self, plan: Plan, platform: Platform) -> None:
    if platform.system == "Linux":
        if platform.distro == "ubuntu":
            self._transport.run_command(["apt-get", "install", "..."])
        elif platform.distro == "fedora":
            self._transport.run_command(["dnf", "install", "..."])
    elif platform.system == "Darwin":
        self._transport.run_command(["brew", "install", "..."])
```

### Transport Usage

Always use transport for system operations:

```python
# Good: Use transport
exists = self._transport.file_exists("/path/to/file")
content = self._transport.read_file("/path/to/file")
self._transport.write_file("/path/to/file", b"content")

# Bad: Direct file operations (won't work with SSH transport)
import os
os.path.exists("/path/to/file")  # WRONG - only works locally
```

## Resource Testing

### Unit Tests

Test resources with mock transport:

```python
from cook.transport import LocalTransport
from cook.core import Platform

class MockTransport:
    def __init__(self):
        self.files = {}
        self.commands = []

    def file_exists(self, path: str) -> bool:
        return path in self.files

    def read_file(self, path: str) -> bytes:
        return self.files.get(path, b"")

    def write_file(self, path: str, content: bytes) -> None:
        self.files[path] = content

# Test resource
def test_custom_resource():
    # Create mock transport
    transport = MockTransport()

    # Create resource
    resource = CustomResource("test", value="hello")
    resource._transport = transport

    # Check state
    platform = Platform.detect()
    state = resource.check(platform)
    assert state["exists"] == False

    # Apply changes
    plan = Plan(action=Action.CREATE, changes=[])
    resource.apply(plan, platform)

    # Verify
    assert transport.files["/tmp/test"] == b"hello"
```

## Resource Patterns

### Configuration File + Service

```python
from cook import File, Service

# Configuration file
config = File("/etc/nginx/nginx.conf", source="./nginx.conf")

# Service that reloads on config change
Service("nginx", running=True, enabled=True, reload_on=[config])
```

### Package + Service

```python
from cook import Package, Service

# Install package
Package("postgresql")

# Manage service
Service("postgresql", running=True, enabled=True)
```

### Multi-Resource Setup

```python
from cook import File, Package, Service

# Create directory
File("/opt/apps/myapp", ensure="directory", mode=0o755)

# Install dependencies
Package("app-deps", packages=["python3", "python3-pip"])

# Application files
app_config = File("/opt/apps/myapp/config.yml", source="./config.yml")
app_binary = File("/opt/apps/myapp/app", source="./app", mode=0o755)

# Service file
service_file = File(
    "/etc/systemd/system/myapp.service",
    source="./myapp.service"
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

## API Reference

### Resource Base Class

See [cook/core/resource.py](https://github.com/gleicon/cook/blob/main/cook/core/resource.py) for the base Resource class.

### Built-in Resources

- [File](../resources/file.md)
- [Package](../resources/package.md)
- [Repository](../resources/repository.md)
- [Service](../resources/service.md)
- [Exec](../resources/exec.md)

### Resource Imports

```python
# Import built-in resources
from cook import File, Package, Repository, Service, Exec

# Import core classes for custom resources
from cook.core import Resource, Platform, Plan, Action, Change
from cook.core.executor import get_executor
```
