"""
MCP server implementation for Cook.

Exposes Cook operations as tools for AI assistants.
"""

import json
import sys
from typing import Any, Dict, List
from pathlib import Path


class CookMCPServer:
    """
    MCP server for Cook configuration management.

    Provides tools for AI assistants to:
    - Generate configurations from descriptions
    - Plan and apply changes
    - Query state and history
    - Detect drift
    - Generate configs from recordings
    """

    def __init__(self):
        self.name = "cook"
        self.version = "0.1.0"
        self.tools = self._register_tools()

    def _register_tools(self) -> List[Dict[str, Any]]:
        """Register available MCP tools."""
        return [
            {
                "name": "cook_generate_config",
                "description": "Generate a Cook configuration from a natural language description",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Natural language description of infrastructure to configure"
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Path to save generated config (default: generated.py)"
                        }
                    },
                    "required": ["description"]
                }
            },
            {
                "name": "cook_plan",
                "description": "Generate a plan showing what changes Cook would make",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "config_file": {
                            "type": "string",
                            "description": "Path to Cook configuration file"
                        }
                    },
                    "required": ["config_file"]
                }
            },
            {
                "name": "cook_apply",
                "description": "Apply a Cook configuration to make actual changes",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "config_file": {
                            "type": "string",
                            "description": "Path to Cook configuration file"
                        },
                        "auto_approve": {
                            "type": "boolean",
                            "description": "Skip confirmation prompt (default: false)"
                        }
                    },
                    "required": ["config_file"]
                }
            },
            {
                "name": "cook_state_list",
                "description": "List all resources managed by Cook",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "cook_state_show",
                "description": "Show detailed state for a specific resource",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "resource_id": {
                            "type": "string",
                            "description": "Resource ID (e.g., 'file:/etc/nginx.conf')"
                        }
                    },
                    "required": ["resource_id"]
                }
            },
            {
                "name": "cook_check_drift",
                "description": "Check for configuration drift",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "fix": {
                            "type": "boolean",
                            "description": "Automatically fix detected drift (default: false)"
                        }
                    }
                }
            },
            {
                "name": "cook_record_generate",
                "description": "Generate Cook config from a recording file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "recording_file": {
                            "type": "string",
                            "description": "Path to recording JSON file"
                        },
                        "output_file": {
                            "type": "string",
                            "description": "Path to save generated config"
                        }
                    },
                    "required": ["recording_file"]
                }
            }
        ]

    def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a tool call from the AI assistant.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        handlers = {
            "cook_generate_config": self._generate_config,
            "cook_plan": self._plan,
            "cook_apply": self._apply,
            "cook_state_list": self._state_list,
            "cook_state_show": self._state_show,
            "cook_check_drift": self._check_drift,
            "cook_record_generate": self._record_generate,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            return handler(arguments)
        except Exception as e:
            return {"error": str(e)}

    def _generate_config(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Cook config from description."""
        description = args["description"]
        output_file = args.get("output_file", "generated.py")

        # Simple template-based generation
        # In production, this would use an LLM to generate more sophisticated configs
        config = self._generate_from_template(description)

        with open(output_file, 'w') as f:
            f.write(config)

        return {
            "success": True,
            "output_file": output_file,
            "message": f"Generated config saved to {output_file}"
        }

    def _generate_from_template(self, description: str) -> str:
        """Generate basic config from description."""
        # Simple keyword matching for MVP
        config_parts = ['"""', f'Generated from: {description}', '"""', '', 'from cook import File, Package, Service', '']

        desc_lower = description.lower()

        # Detect nginx
        if 'nginx' in desc_lower or 'web server' in desc_lower:
            config_parts.append('# Web server setup')
            config_parts.append('Package("nginx")')
            config_parts.append('Service("nginx", running=True, enabled=True)')
            config_parts.append('')

        # Detect database
        if 'mysql' in desc_lower or 'database' in desc_lower:
            config_parts.append('# Database setup')
            config_parts.append('Package("mysql-server")')
            config_parts.append('Service("mysql", running=True, enabled=True)')
            config_parts.append('')

        if 'postgresql' in desc_lower or 'postgres' in desc_lower:
            config_parts.append('# Database setup')
            config_parts.append('Package("postgresql")')
            config_parts.append('Service("postgresql", running=True, enabled=True)')
            config_parts.append('')

        # Detect file operations
        if 'directory' in desc_lower or 'folder' in desc_lower:
            config_parts.append('# Directory setup')
            config_parts.append('File("/var/www", ensure="directory", mode=0o755)')
            config_parts.append('')

        return '\n'.join(config_parts)

    def _plan(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run cook plan."""
        config_file = args["config_file"]

        if not Path(config_file).exists():
            return {"error": f"Config file not found: {config_file}"}

        # Execute cook plan
        import subprocess
        result = subprocess.run(
            ["cook", "plan", config_file],
            capture_output=True,
            text=True
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }

    def _apply(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run cook apply."""
        config_file = args["config_file"]
        auto_approve = args.get("auto_approve", False)

        if not Path(config_file).exists():
            return {"error": f"Config file not found: {config_file}"}

        # Execute cook apply
        import subprocess
        cmd = ["cook", "apply", config_file]
        if auto_approve:
            cmd.append("--yes")

        result = subprocess.run(cmd, capture_output=True, text=True)

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }

    def _state_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List managed resources."""
        import subprocess
        result = subprocess.run(
            ["cook", "state", "list"],
            capture_output=True,
            text=True
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }

    def _state_show(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Show resource state."""
        resource_id = args["resource_id"]

        import subprocess
        result = subprocess.run(
            ["cook", "state", "show", resource_id],
            capture_output=True,
            text=True
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }

    def _check_drift(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check for drift."""
        fix = args.get("fix", False)

        import subprocess
        cmd = ["cook", "check-drift"]
        if fix:
            cmd.append("--fix")

        result = subprocess.run(cmd, capture_output=True, text=True)

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }

    def _record_generate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate config from recording."""
        recording_file = args["recording_file"]
        output_file = args.get("output_file")

        if not Path(recording_file).exists():
            return {"error": f"Recording file not found: {recording_file}"}

        import subprocess
        cmd = ["cook", "record", "generate", recording_file]
        if output_file:
            cmd.extend(["-o", output_file])

        result = subprocess.run(cmd, capture_output=True, text=True)

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }

    def run(self):
        """Run MCP server (stdio mode)."""
        print(json.dumps({
            "jsonrpc": "2.0",
            "method": "server/info",
            "params": {
                "name": self.name,
                "version": self.version,
                "capabilities": {
                    "tools": True
                }
            }
        }), flush=True)

        # Read requests from stdin
        for line in sys.stdin:
            try:
                request = json.loads(line)
                response = self._handle_request(request)
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError:
                continue

    def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": self.tools}
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            result = self.handle_tool_call(tool_name, arguments)

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }


def main():
    """MCP server entry point."""
    server = CookMCPServer()
    server.run()


if __name__ == "__main__":
    main()
