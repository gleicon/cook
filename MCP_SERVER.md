# Cook MCP Server

Model Context Protocol server for AI-assisted infrastructure management with Cook.

## Overview

The Cook MCP server exposes Cook operations as tools that AI assistants like Claude can use to help manage infrastructure configurations.

## Features

The MCP server provides these tools:

### cook_generate_config
Generate a Cook configuration from natural language description.

**Input:**
- `description` (required): Natural language description of infrastructure
- `output_file` (optional): Path to save config (default: generated.py)

**Example:**
```
Generate a config for nginx web server with SSL
```

### cook_plan
Show what changes Cook would make without applying them.

**Input:**
- `config_file` (required): Path to Cook configuration file

**Output:**
- Planned changes for each resource
- Actions to be taken (create, update, delete)

### cook_apply
Apply a Cook configuration to make actual changes.

**Input:**
- `config_file` (required): Path to Cook configuration file
- `auto_approve` (optional): Skip confirmation (default: false)

**Output:**
- Applied changes
- Success/failure status

### cook_state_list
List all resources currently managed by Cook.

**Output:**
- List of resource IDs
- Last applied timestamp
- Current status

### cook_state_show
Show detailed state for a specific resource.

**Input:**
- `resource_id` (required): Resource ID (e.g., "file:/etc/nginx.conf")

**Output:**
- Resource type and status
- Desired vs actual state
- Change history

### cook_check_drift
Check for configuration drift.

**Input:**
- `fix` (optional): Automatically fix drift (default: false)

**Output:**
- Drifted resources
- Differences between expected and actual state

### cook_record_generate
Generate Cook config from a recording file.

**Input:**
- `recording_file` (required): Path to recording JSON
- `output_file` (optional): Path to save generated config

**Output:**
- Generated configuration file
- Extracted resources

## Setup

### Installation

```bash
# Install Cook with all dependencies
pip install -e ".[all]"
```

### Configuration

The MCP server can be configured in Claude Desktop or other MCP clients.

**For Claude Desktop:**

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cook": {
      "command": "cook-mcp",
      "env": {}
    }
  }
}
```

**For other MCP clients:**

Use the provided configuration file:

```bash
cp cook-mcp-config.json ~/.config/mcp-servers/cook.json
```

### Testing

Test the MCP server manually:

```bash
# Run server in stdio mode
cook-mcp

# Server will output server info and wait for requests
```

## Usage Examples

### With Claude Desktop

Once configured, you can ask Claude:

```
Using Cook, generate a configuration for a LEMP stack (Linux, Nginx, MySQL, PHP)
```

Claude will use the `cook_generate_config` tool to create a config file.

```
Check what changes this config would make
```

Claude will use `cook_plan` to show planned changes.

```
Apply the configuration
```

Claude will use `cook_apply` to make the changes.

```
Check if any configurations have drifted
```

Claude will use `cook_check_drift` to detect drift.

### Programmatic Usage

```python
from cook.mcp.server import CookMCPServer

server = CookMCPServer()

# Generate config from description
result = server.handle_tool_call("cook_generate_config", {
    "description": "nginx web server with SSL",
    "output_file": "webserver.py"
})

# Plan changes
result = server.handle_tool_call("cook_plan", {
    "config_file": "webserver.py"
})

# Apply changes
result = server.handle_tool_call("cook_apply", {
    "config_file": "webserver.py",
    "auto_approve": True
})
```

## Capabilities

### What the AI Can Do

- Generate configurations from natural language descriptions
- Plan and preview changes before applying
- Apply configurations safely with confirmation
- Query resource state and history
- Detect and fix configuration drift
- Convert recorded manual changes to code

### What the AI Cannot Do

- Execute arbitrary commands
- Access files outside Cook's scope
- Modify system settings directly
- Bypass Cook's safety checks

## Security

### Safety Features

- All operations go through Cook's standard workflows
- Apply operations require confirmation (unless auto-approved)
- State tracking for audit trail
- Read-only operations by default

### Recommendations

- Review generated configs before applying
- Use `cook plan` before `cook apply`
- Enable state tracking for auditability
- Restrict MCP server access appropriately

## Troubleshooting

### Server Won't Start

```bash
# Check Cook is installed
cook --version

# Test server manually
cook-mcp
```

### Tools Not Appearing in Claude

1. Check configuration file location
2. Restart Claude Desktop
3. Check server logs

### Permission Errors

Some operations require sudo:

```bash
# Run with elevated privileges
sudo cook apply config.py
```

For MCP server, you may need to configure sudo access.

## Architecture

### Protocol

The MCP server implements the Model Context Protocol (MCP) specification:
- JSON-RPC 2.0 over stdio
- Tool discovery via `tools/list`
- Tool execution via `tools/call`

### Implementation

```
cook/mcp/
├── __init__.py       # Module exports
└── server.py         # MCP server implementation
```

The server is a simple wrapper around Cook CLI commands, translating JSON-RPC requests to Cook operations.

## Future Enhancements

Planned improvements:

- Advanced config generation using LLM
- Streaming output for long operations
- Resource templates and snippets
- Multi-server orchestration
- Rollback capabilities
- Validation and dry-run modes

## Related Documentation

- [Cook README](README.md)
- [MCP Specification](https://modelcontextprotocol.io/)
- [Cook Examples](examples/README.md)
- [Test Plan](TEST_PLAN.md)
