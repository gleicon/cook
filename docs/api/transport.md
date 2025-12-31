# Transport API

Transport layer for local and remote execution.

## Overview

Transport abstracts command execution and file operations:

- **LocalTransport**: Execute commands locally
- **SSHTransport**: Execute commands via SSH (future)
- **NullTransport**: No-op transport for testing

Resources use transport for all system interactions, enabling the same configuration to work locally or remotely.

## Transport Interface

All transports implement these methods:

### File Operations

```python
# Check if file exists
exists: bool = transport.file_exists("/path/to/file")

# Read file content
content: bytes = transport.read_file("/path/to/file")

# Write file content
transport.write_file("/path/to/file", b"content")
```

### Command Execution

```python
# Run command
output: str
code: int
output, code = transport.run_command(["ls", "-la", "/tmp"])

# Run shell command
output, code = transport.run_shell("echo 'hello' > /tmp/test.txt")
```

## LocalTransport

Execute commands on the local system.

### Usage

```python
from cook.transport import LocalTransport

transport = LocalTransport()

# File operations
exists = transport.file_exists("/etc/hosts")
content = transport.read_file("/etc/hosts")

# Command execution
output, code = transport.run_command(["uname", "-a"])
print(f"Output: {output}")
print(f"Exit code: {code}")
```

### Configuration

LocalTransport is the default for all resources:

```python
from cook import File

# Uses LocalTransport by default
File("/etc/motd", content="Welcome")
```

### Examples

#### File Operations

```python
from cook.transport import LocalTransport

transport = LocalTransport()

# Check existence
if transport.file_exists("/etc/motd"):
    # Read content
    content = transport.read_file("/etc/motd")
    print(content.decode())

# Write content
transport.write_file("/tmp/test.txt", b"Hello World")
```

#### Command Execution

```python
transport = LocalTransport()

# Run command
output, code = transport.run_command(["ls", "-la", "/tmp"])
if code == 0:
    print(f"Directory listing:\n{output}")

# Run shell command
output, code = transport.run_shell("cat /etc/os-release | grep VERSION")
print(output)
```

## SSHTransport

Execute commands on remote systems via SSH (future implementation).

### Planned Usage

```python
from cook.transport import SSHTransport

# Connect to remote host
transport = SSHTransport(
    host="server.example.com",
    username="deploy",
    key_file="/home/user/.ssh/id_rsa"
)

# Use with resources
from cook import File

file = File("/etc/motd", content="Welcome")
file._transport = transport

# Execute remotely
from cook.core.executor import get_executor
from cook.core import Platform

executor = get_executor()
platform = Platform.detect(transport)
executor.execute(platform)
```

### Planned Features

- SSH key authentication
- Password authentication
- Connection pooling
- SFTP for file transfer
- Command output streaming

## NullTransport

No-op transport for testing.

### Usage

```python
from cook.transport import NullTransport

transport = NullTransport()

# All operations return empty/false
exists = transport.file_exists("/any/path")  # Always False
content = transport.read_file("/any/path")    # Empty bytes
output, code = transport.run_command(["ls"])  # Empty output, code 0
```

### Testing Example

```python
from cook import File
from cook.transport import NullTransport
from cook.core import Platform, Action

# Create resource
file = File("/etc/motd", content="Welcome")

# Use null transport (no actual operations)
file._transport = NullTransport()

# Check state (won't actually check file)
platform = Platform.detect()
state = file.check(platform)
print(state)  # {"exists": False, ...}
```

## Using Transport in Resources

Resources access transport via `self._transport`:

### File Operations

```python
class MyResource(Resource):
    def check(self, platform: Platform) -> Dict[str, Any]:
        # Check if file exists
        if self._transport.file_exists("/path/to/file"):
            # Read file
            content = self._transport.read_file("/path/to/file")
            return {"exists": True, "content": content.decode()}
        return {"exists": False}

    def apply(self, plan: Plan, platform: Platform) -> None:
        # Write file
        content = "Hello World".encode()
        self._transport.write_file("/path/to/file", content)
```

### Command Execution

```python
class MyResource(Resource):
    def check(self, platform: Platform) -> Dict[str, Any]:
        # Run command
        output, code = self._transport.run_command(["systemctl", "is-active", "nginx"])
        return {"running": code == 0}

    def apply(self, plan: Plan, platform: Platform) -> None:
        # Start service
        output, code = self._transport.run_command(["systemctl", "start", "nginx"])
        if code != 0:
            raise RuntimeError(f"Failed to start service: {output}")
```

### Shell Commands

```python
class MyResource(Resource):
    def apply(self, plan: Plan, platform: Platform) -> None:
        # Run shell command with pipes/redirects
        output, code = self._transport.run_shell(
            "cat /var/log/app.log | grep ERROR > /tmp/errors.txt"
        )
```

## Transport Methods

### file_exists()

Check if file or directory exists.

```python
exists: bool = transport.file_exists("/path/to/file")
```

**Parameters:**
- `path`: File or directory path

**Returns:**
- `bool`: True if exists, False otherwise

**Example:**

```python
if transport.file_exists("/etc/nginx/nginx.conf"):
    print("Nginx is configured")
```

### read_file()

Read file content as bytes.

```python
content: bytes = transport.read_file("/path/to/file")
```

**Parameters:**
- `path`: File path

**Returns:**
- `bytes`: File content

**Raises:**
- `FileNotFoundError`: If file doesn't exist

**Example:**

```python
content = transport.read_file("/etc/hostname")
hostname = content.decode().strip()
print(f"Hostname: {hostname}")
```

### write_file()

Write content to file.

```python
transport.write_file("/path/to/file", b"content")
```

**Parameters:**
- `path`: File path
- `content`: File content as bytes

**Example:**

```python
content = "Welcome to the server".encode()
transport.write_file("/etc/motd", content)
```

### run_command()

Run command with arguments.

```python
output: str
code: int
output, code = transport.run_command(["ls", "-la", "/tmp"])
```

**Parameters:**
- `args`: List of command and arguments

**Returns:**
- Tuple of `(output: str, exit_code: int)`

**Example:**

```python
output, code = transport.run_command(["apt-get", "update"])
if code == 0:
    print("Package cache updated")
else:
    print(f"Update failed: {output}")
```

### run_shell()

Run shell command (supports pipes, redirects, etc.).

```python
output: str
code: int
output, code = transport.run_shell("echo 'hello' > /tmp/test.txt")
```

**Parameters:**
- `command`: Shell command string

**Returns:**
- Tuple of `(output: str, exit_code: int)`

**Security Warning:** Shell commands can be dangerous. Validate all inputs.

**Example:**

```python
# Pipe command output
output, code = transport.run_shell("cat /var/log/app.log | grep ERROR")

# Redirect output
output, code = transport.run_shell("echo 'data' > /tmp/output.txt")

# Command chaining
output, code = transport.run_shell("cd /tmp && ls -la")
```

## Transport Best Practices

### Use run_command() When Possible

Prefer `run_command()` over `run_shell()`:

```python
# Good: Safe from injection
output, code = transport.run_command(["ls", "-la", directory])

# Avoid: Shell injection risk
output, code = transport.run_shell(f"ls -la {directory}")
```

### Check Exit Codes

Always check command exit codes:

```python
output, code = transport.run_command(["systemctl", "start", "nginx"])
if code != 0:
    raise RuntimeError(f"Command failed: {output}")
```

### Handle Binary Files

Files are transferred as bytes:

```python
# Read binary file
content = transport.read_file("/path/to/image.png")

# Write binary file
transport.write_file("/path/to/image.png", binary_data)
```

### Text File Encoding

Handle text file encoding explicitly:

```python
# Read text file
content_bytes = transport.read_file("/etc/motd")
content_text = content_bytes.decode("utf-8")

# Write text file
content_bytes = "Welcome".encode("utf-8")
transport.write_file("/etc/motd", content_bytes)
```

## Error Handling

### File Not Found

```python
try:
    content = transport.read_file("/nonexistent/file")
except FileNotFoundError:
    print("File does not exist")
```

### Command Failure

```python
output, code = transport.run_command(["false"])
if code != 0:
    print(f"Command failed with exit code {code}")
```

### Permission Denied

```python
output, code = transport.run_command(["cat", "/root/secret"])
if code != 0:
    print(f"Permission denied: {output}")
```

## Testing with Mock Transport

Create mock transport for unit tests:

```python
class MockTransport:
    def __init__(self):
        self.files = {}
        self.commands = []

    def file_exists(self, path: str) -> bool:
        return path in self.files

    def read_file(self, path: str) -> bytes:
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path]

    def write_file(self, path: str, content: bytes) -> None:
        self.files[path] = content

    def run_command(self, args: list) -> tuple[str, int]:
        self.commands.append(args)
        return "", 0

    def run_shell(self, command: str) -> tuple[str, int]:
        self.commands.append(command)
        return "", 0

# Use in tests
def test_resource():
    transport = MockTransport()
    resource = MyResource("test")
    resource._transport = transport

    # Test operations
    platform = Platform.detect()
    resource.check(platform)

    # Verify
    assert "/path/to/file" in transport.files
    assert ["systemctl", "start", "myservice"] in transport.commands
```

## API Reference

See [cook/transport.py](https://github.com/gleicon/cook/blob/main/cook/transport.py) for complete transport implementation.

### Imports

```python
from cook.transport import LocalTransport, NullTransport
```
