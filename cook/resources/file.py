"""
File resource - manage files and directories.

Handles:
- File content (inline or from source)
- File permissions (mode, owner, group)
- Directories (ensure="directory")
- Templates (Jinja2)
- Symbolic links
"""

import os
import stat
import pwd
import grp
from typing import Dict, Any, Optional
from pathlib import Path

from cook.core.resource import Resource, Plan, Action, Platform
from cook.core.executor import get_executor


class File(Resource):
    """
    File resource for managing files and directories.

    Examples:
        # Simple file with content
        File("/etc/motd", content="Welcome to the server!")

        # File from source
        File("/etc/nginx/nginx.conf", source="./configs/nginx.conf")

        # Directory
        File("/var/www/app", ensure="directory", mode=0o755)

        # With owner/group
        File("/var/www/index.html",
             content="<h1>Hello</h1>",
             owner="www-data",
             group="www-data",
             mode=0o644)

        # Template (coming soon)
        File("/etc/nginx/site.conf",
             template="./templates/nginx-site.j2",
             vars={"domain": "example.com", "port": 80})
    """

    def __init__(
        self,
        path: str,
        content: Optional[str] = None,
        source: Optional[str] = None,
        template: Optional[str] = None,
        vars: Optional[Dict[str, Any]] = None,
        ensure: str = "file",  # "file", "directory", "absent"
        mode: Optional[int] = None,
        owner: Optional[str] = None,
        group: Optional[str] = None,
        **options
    ):
        """
        Initialize file resource.

        Args:
            path: File path
            content: Inline content
            source: Path to source file
            template: Path to Jinja2 template
            vars: Template variables
            ensure: "file", "directory", or "absent"
            mode: File mode (e.g., 0o644)
            owner: Owner username
            group: Group name
            **options: Additional options
        """
        super().__init__(path, **options)

        self.path = path
        self.content = content
        self.source = source
        self.template = template
        self.vars = vars or {}
        self.ensure = ensure
        self.mode = mode
        self.owner = owner
        self.group = group

        # Auto-register with global executor
        get_executor().add(self)

    def resource_type(self) -> str:
        return "file"

    def check(self, platform: Platform) -> Dict[str, Any]:
        """Check current file state."""
        state = {
            "exists": False,
            "type": None,
            "content": None,
            "mode": None,
            "owner": None,
            "group": None,
            "size": None,
        }

        # Check if file exists via transport
        if not self._transport.file_exists(self.path):
            return state

        state["exists"] = True

        # Get file information via stat command
        output, code = self._transport.run_shell(
            f"stat -c '%F|%a|%s|%U|%G' '{self.path}' 2>/dev/null || stat -f '%HT|%Lp|%z|%Su|%Sg' '{self.path}'"
        )

        if code == 0:
            parts = output.strip().split("|")
            if len(parts) >= 5:
                file_type, mode_octal, size, owner, group = parts

                # Determine type
                if "regular" in file_type.lower():
                    state["type"] = "file"
                elif "directory" in file_type.lower():
                    state["type"] = "directory"
                elif "symbolic link" in file_type.lower():
                    state["type"] = "symlink"

                # Parse mode (octal string to int)
                try:
                    state["mode"] = int(mode_octal, 8)
                except ValueError:
                    pass

                state["size"] = int(size) if size.isdigit() else None
                state["owner"] = owner
                state["group"] = group

        # Read content for files
        if state["type"] == "file":
            try:
                content = self._transport.read_file(self.path)
                state["content"] = content.decode("utf-8")
            except (UnicodeDecodeError, Exception):
                # Binary file or read error
                state["content"] = None

        return state

    def desired_state(self) -> Dict[str, Any]:
        """Return desired file state."""
        state = {
            "exists": self.ensure != "absent",
            "type": self.ensure if self.ensure in ["file", "directory"] else None,
        }

        if self.ensure == "absent":
            return state

        # Get desired content
        if self.content is not None:
            state["content"] = self.content
        elif self.source is not None:
            state["content"] = self._read_source()
        elif self.template is not None:
            state["content"] = self._render_template()
        else:
            state["content"] = None

        # File metadata
        if self.mode is not None:
            state["mode"] = self.mode
        if self.owner is not None:
            state["owner"] = self.owner
        if self.group is not None:
            state["group"] = self.group

        return state

    def apply(self, plan: Plan, platform: Platform) -> None:
        """Apply file changes."""
        path = Path(self.path)

        if plan.action == Action.DELETE:
            self._delete(path)
        elif plan.action == Action.CREATE:
            self._create(path)
        elif plan.action == Action.UPDATE:
            self._update(path, plan)

    def _create(self, path: Path) -> None:
        """Create file or directory."""
        if self.ensure == "directory":
            # Create directory via transport
            self._transport.run_command(["mkdir", "-p", self.path])
        elif self.ensure == "file":
            # Create parent directories
            parent = str(Path(self.path).parent)
            self._transport.run_command(["mkdir", "-p", parent])

            # Write content
            if self._desired_state.get("content") is not None:
                content_bytes = self._desired_state["content"].encode("utf-8")
                self._transport.write_file(self.path, content_bytes)
            else:
                # Touch file
                self._transport.run_command(["touch", self.path])

        # Set permissions
        self._set_metadata(path)

    def _update(self, path: Path, plan: Plan) -> None:
        """Update existing file."""
        for change in plan.changes:
            if change.field == "content":
                content_bytes = change.to_value.encode("utf-8")
                self._transport.write_file(self.path, content_bytes)
            elif change.field == "mode":
                # Convert mode to octal string for chmod
                mode_str = oct(change.to_value)[2:]
                self._transport.run_command(["chmod", mode_str, self.path])
            elif change.field == "owner" or change.field == "group":
                self._set_metadata(path)

    def _delete(self, path: Path) -> None:
        """Delete file or directory."""
        # Use rm -rf for simplicity (transport-agnostic)
        self._transport.run_command(["rm", "-rf", self.path])

    def _set_metadata(self, path: Path) -> None:
        """Set file owner, group, and mode."""
        # Set owner/group via chown command
        if self.owner is not None and self.group is not None:
            self._transport.run_command(["chown", f"{self.owner}:{self.group}", self.path])
        elif self.owner is not None:
            self._transport.run_command(["chown", self.owner, self.path])
        elif self.group is not None:
            self._transport.run_command(["chgrp", self.group, self.path])

        # Set mode via chmod command
        if self.mode is not None:
            mode_str = oct(self.mode)[2:]
            self._transport.run_command(["chmod", mode_str, self.path])

    def _read_source(self) -> str:
        """Read content from source file."""
        source_path = Path(self.source)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {self.source}")
        return source_path.read_text()

    def _render_template(self) -> str:
        """Render Jinja2 template."""
        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape
        except ImportError:
            raise ImportError(
                "Jinja2 is required for template support. "
                "Install with: pip install jinja2"
            )

        template_path = Path(self.template)
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {self.template}")

        # Set up Jinja2 environment
        env = Environment(
            loader=FileSystemLoader(template_path.parent),
            autoescape=select_autoescape(),
        )

        template = env.get_template(template_path.name)
        return template.render(**self.vars)
