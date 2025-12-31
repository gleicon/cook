# Core API

Core abstractions and patterns in Cook.

## Overview

Cook's core API provides the foundation for all resources and execution:

- **Resource**: Base class for all resources (File, Package, Service, etc.)
- **Plan**: Execution plan showing what will change
- **Action**: Type of change (CREATE, UPDATE, DELETE, NONE)
- **Change**: Individual property change
- **Platform**: System information (OS, distro, version)
- **Executor**: Manages resource execution and dependencies

## Check-Plan-Apply Pattern

Cook uses a three-phase execution model similar to Terraform:

### 1. Check Phase

Inspect current system state:

```python
class MyResource(Resource):
    def check(self, platform: Platform) -> Dict[str, Any]:
        # Return current state as dictionary
        return {
            "exists": True,
            "version": "1.0.0",
            "enabled": True
        }
```

### 2. Plan Phase

Compare current state to desired state and generate a plan:

```python
# Cook automatically generates plan by comparing:
# - Actual state (from check())
# - Desired state (from desired_state())

# Plan shows:
# - Action: CREATE, UPDATE, DELETE, or NONE
# - Changes: List of property changes
```

### 3. Apply Phase

Execute the plan:

```python
class MyResource(Resource):
    def apply(self, plan: Plan, platform: Platform) -> None:
        if plan.action == Action.CREATE:
            # Create resource
            pass
        elif plan.action == Action.UPDATE:
            # Update resource
            for change in plan.changes:
                # Apply each change
                pass
        elif plan.action == Action.DELETE:
            # Delete resource
            pass
```

## Resource Base Class

All resources inherit from `Resource`:

```python
from cook.core import Resource, Platform, Plan, Action
from typing import Dict, Any

class MyResource(Resource):
    def __init__(self, name: str, **options):
        super().__init__(name, **options)
        # Resource-specific initialization

    def resource_type(self) -> str:
        # Return resource type identifier
        return "myresource"

    def check(self, platform: Platform) -> Dict[str, Any]:
        # Return current state
        return {"exists": False}

    def desired_state(self) -> Dict[str, Any]:
        # Return desired state
        return {"exists": True}

    def apply(self, plan: Plan, platform: Platform) -> None:
        # Execute changes
        pass
```

### Resource Properties

Every resource has:

- `id`: Unique identifier (`{type}:{name}`)
- `name`: Resource name
- `_transport`: Transport for executing commands
- `_actual_state`: Current system state (from check)
- `_desired_state`: Target state (from desired_state)

### Resource Methods

#### resource_type()

Return resource type identifier:

```python
def resource_type(self) -> str:
    return "pkg"  # For Package resource
```

Used in resource IDs: `pkg:nginx`

#### check(platform)

Inspect current system state:

```python
def check(self, platform: Platform) -> Dict[str, Any]:
    # Query system
    exists = self._transport.file_exists("/etc/myapp.conf")

    return {
        "exists": exists,
        "version": "1.0.0" if exists else None
    }
```

#### desired_state()

Define target state:

```python
def desired_state(self) -> Dict[str, Any]:
    return {
        "exists": True,
        "version": "2.0.0"
    }
```

#### apply(plan, platform)

Execute changes:

```python
def apply(self, plan: Plan, platform: Platform) -> None:
    if plan.action == Action.CREATE:
        # Create resource
        self._transport.run_command(["create", "resource"])
    elif plan.action == Action.UPDATE:
        # Update resource
        for change in plan.changes:
            # Handle each change
            pass
```

## Plan

Execution plan showing what will change.

### Properties

```python
@dataclass
class Plan:
    action: Action              # What action to take
    changes: List[Change]       # List of changes
    reason: str                 # Why this action
```

### Methods

```python
plan = Plan(action=Action.UPDATE, changes=[...])

# Check if plan has changes
if plan.has_changes():
    print("Changes detected")

# String representation
print(plan)
# Output:
# Action: update
#   version: 1.0.0 → 2.0.0
#   enabled: false → true
```

### Example

```python
from cook.core import Plan, Action, Change

plan = Plan(
    action=Action.UPDATE,
    changes=[
        Change("version", "1.0.0", "2.0.0"),
        Change("enabled", False, True)
    ],
    reason="Version upgrade required"
)

print(plan)
# Action: update
# Reason: Version upgrade required
#   version: 1.0.0 → 2.0.0
#   enabled: false → true
```

## Action

Resource action enumeration.

### Values

```python
class Action(Enum):
    NONE = "none"       # No changes
    CREATE = "create"   # Resource doesn't exist
    UPDATE = "update"   # Resource exists but differs
    DELETE = "delete"   # Resource should be removed
```

### Usage

```python
from cook.core import Action

if plan.action == Action.CREATE:
    # Create new resource
    pass
elif plan.action == Action.UPDATE:
    # Update existing resource
    pass
elif plan.action == Action.DELETE:
    # Remove resource
    pass
elif plan.action == Action.NONE:
    # No changes needed
    pass
```

## Change

Individual property change.

### Properties

```python
@dataclass
class Change:
    field: str          # Property name
    from_value: Any     # Current value
    to_value: Any       # Target value
```

### Example

```python
from cook.core import Change

change = Change("version", "1.0.0", "2.0.0")
print(change)
# version: 1.0.0 → 2.0.0

# Access properties
print(change.field)       # "version"
print(change.from_value)  # "1.0.0"
print(change.to_value)    # "2.0.0"
```

## Platform

System information (OS, distribution, version, architecture).

### Properties

```python
@dataclass
class Platform:
    system: str    # Linux, Darwin, Windows
    distro: str    # ubuntu, debian, fedora, arch, etc.
    version: str   # OS version
    arch: str      # x86_64, arm64, etc.
```

### Detection

```python
from cook.core import Platform

# Detect local platform
platform = Platform.detect()

print(platform.system)   # "Linux"
print(platform.distro)   # "ubuntu"
print(platform.version)  # "22.04"
print(platform.arch)     # "x86_64"
```

### Usage in Resources

```python
def apply(self, plan: Plan, platform: Platform) -> None:
    if platform.system == "Linux":
        # Linux-specific logic
        if platform.distro == "ubuntu":
            # Ubuntu-specific
            pass
    elif platform.system == "Darwin":
        # macOS-specific logic
        pass
```

## Executor

Manages resource registration and execution.

### Get Executor

```python
from cook.core.executor import get_executor

executor = get_executor()
```

### Add Resources

```python
# Resources auto-register on creation
from cook import File

# This automatically adds to executor
File("/etc/motd", content="Welcome")

# Or manually
executor.add(resource)
```

### Resource Redefinition (Last Definition Wins)

When a resource with the same ID is added multiple times, **the last definition replaces previous ones**. This enables multi-phase configurations:

```python
from cook import File, Exec

# Phase 1: HTTP-only nginx config
File(
    "/etc/nginx/sites-available/mysite.com",
    template="nginx.conf.j2",
    vars={"ssl_enabled": False}
)

# Obtain SSL certificate
Exec(
    "certbot",
    command="certbot certonly --nginx -d mysite.com ...",
    creates="/etc/letsencrypt/live/mysite.com/fullchain.pem"
)

# Phase 2: Update to HTTPS config (replaces Phase 1 definition)
File(
    "/etc/nginx/sites-available/mysite.com",
    template="nginx.conf.j2",
    vars={"ssl_enabled": True}
)
```

**Behavior:**
- Resource ID is based on type and path: `file:/etc/nginx/sites-available/mysite.com`
- When the same ID is added again, it replaces the previous definition
- **Execution order is preserved** - the resource maintains its original position
- Only the final (last) definition is used during plan/apply
- This matches behavior of mature IaC tools like Puppet and Ansible

**Use Cases:**
- Progressive refinement (HTTP → HTTPS configurations)
- Multi-phase deployments requiring different states
- Certificate management workflows
- Conditional configuration updates

**Example with Order Preservation:**

```python
File("/etc/app/config1.conf", content="first")
File("/etc/app/config2.conf", content="second")  # Position 2
File("/etc/app/config3.conf", content="third")

# Update config2 - it stays at position 2 in execution order
File("/etc/app/config2.conf", content="second updated")
```

Execution order: config1 → config2 (updated) → config3

### Execute Resources

```python
from cook.core import Platform

platform = Platform.detect()

# Execute all resources
executor.execute(platform)
```

### Plan All Resources

```python
# Generate plans without executing
plans = executor.plan_all(platform)

for resource_id, plan in plans.items():
    if plan.has_changes():
        print(f"{resource_id}: {plan}")
```

## Creating Custom Resources

### Basic Resource

```python
from cook.core import Resource, Platform, Plan, Action
from cook.core.executor import get_executor
from typing import Dict, Any

class CustomResource(Resource):
    def __init__(self, name: str, value: str, **options):
        super().__init__(name, **options)
        self.value = value

        # Auto-register
        get_executor().add(self)

    def resource_type(self) -> str:
        return "custom"

    def check(self, platform: Platform) -> Dict[str, Any]:
        # Check current state
        exists = self._transport.file_exists(f"/tmp/{self.name}")

        return {
            "exists": exists,
            "value": None  # Could read from file
        }

    def desired_state(self) -> Dict[str, Any]:
        return {
            "exists": True,
            "value": self.value
        }

    def apply(self, plan: Plan, platform: Platform) -> None:
        if plan.action == Action.CREATE:
            # Create resource
            content = self.value.encode()
            self._transport.write_file(f"/tmp/{self.name}", content)
        elif plan.action == Action.UPDATE:
            # Update resource
            for change in plan.changes:
                if change.field == "value":
                    content = change.to_value.encode()
                    self._transport.write_file(f"/tmp/{self.name}", content)
        elif plan.action == Action.DELETE:
            # Delete resource
            self._transport.run_command(["rm", f"/tmp/{self.name}"])
```

### Using Custom Resource

```python
# Create resource
CustomResource("myfile", value="Hello World")

# Execute
from cook.core.executor import get_executor
from cook.core import Platform

executor = get_executor()
platform = Platform.detect()
executor.execute(platform)
```

## Transport Integration

Resources use transport for all system operations:

```python
# File operations
exists = self._transport.file_exists("/path/to/file")
content = self._transport.read_file("/path/to/file")
self._transport.write_file("/path/to/file", b"content")

# Command execution
output, code = self._transport.run_command(["ls", "-la"])

# Shell execution
output, code = self._transport.run_shell("echo 'hello'")
```

See [Transport API](transport.md) for details.

## Error Handling

### Validation Errors

Raise exceptions during initialization:

```python
def __init__(self, name: str, value: str):
    if not value:
        raise ValueError("value cannot be empty")
    super().__init__(name)
```

### Execution Errors

Raise exceptions during apply:

```python
def apply(self, plan: Plan, platform: Platform) -> None:
    output, code = self._transport.run_command(["mycommand"])
    if code != 0:
        raise RuntimeError(f"Command failed: {output}")
```

## API Reference

### Core Module

See [cook/core/resource.py](https://github.com/gleicon/cook/blob/main/cook/core/resource.py) for complete source code.

### Key Imports

```python
from cook.core import Resource, Plan, Action, Change, Platform
from cook.core.executor import get_executor, reset_executor
```
