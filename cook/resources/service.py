"""
Service resource - manage system services.

Supports:
- systemd (Linux)
- launchctl (macOS)
- service command (fallback)
"""

from typing import Any, Dict, List, Optional

from cook.core.executor import get_executor
from cook.core import Plan, Platform, Resource


class Service(Resource):
    """
    Service resource for managing system services.

    Examples:
        # Ensure service is running
        Service("nginx", running=True)

        # Ensure enabled at boot
        Service("nginx", running=True, enabled=True)

        # Auto-reload on config changes
        nginx_conf = File("/etc/nginx/nginx.conf", ...)
        Service("nginx",
                running=True,
                reload_on=[nginx_conf])

        # Auto-restart on binary changes
        Service("app",
                running=True,
                restart_on=[app_binary])
    """

    def __init__(
        self,
        name: str,
        running: Optional[bool] = None,
        enabled: Optional[bool] = None,
        reload_on: Optional[List] = None,
        restart_on: Optional[List] = None,
        **options,
    ):
        """
        Initialize service resource.

        Args:
            name: Service name
            running: Whether service should be running
            enabled: Whether service should be enabled at boot
            reload_on: List of resources that trigger reload
            restart_on: List of resources that trigger restart
            **options: Additional options
        """
        super().__init__(name, **options)

        self.service_name = name
        self.running = running
        self.enabled = enabled
        self.reload_on = self._extract_resource_ids(reload_on or [])
        self.restart_on = self._extract_resource_ids(restart_on or [])

        # Auto-register
        get_executor().add(self)

    def _extract_resource_ids(self, resources: List) -> List[str]:
        """Extract resource IDs from resource objects or strings."""
        ids = []
        for r in resources:
            if isinstance(r, str):
                ids.append(r)
            elif hasattr(r, "id"):
                ids.append(r.id)
        return ids

    def resource_type(self) -> str:
        return "svc"

    def check(self, platform: Platform) -> Dict[str, Any]:
        """Check service state."""
        state = {
            "exists": True,  # Assume service exists
            "running": self._is_running(platform),
            "enabled": self._is_enabled(platform),
        }
        return state

    def desired_state(self) -> Dict[str, Any]:
        """Return desired service state."""
        state = {"exists": True}

        if self.running is not None:
            state["running"] = self.running
        if self.enabled is not None:
            state["enabled"] = self.enabled

        return state

    def apply(self, plan: Plan, platform: Platform) -> None:
        """Apply service changes."""
        for change in plan.changes:
            if change.field == "running":
                if change.to_value:
                    self._start(platform)
                else:
                    self._stop(platform)
            elif change.field == "enabled":
                if change.to_value:
                    self._enable(platform)
                else:
                    self._disable(platform)

    def _is_running(self, platform: Platform) -> bool:
        """Check if service is running."""
        try:
            if platform.system == "Linux":
                _, code = self._transport.run_command(
                    ["systemctl", "is-active", self.service_name]
                )
                return code == 0

            elif platform.system == "Darwin":
                _, code = self._transport.run_command(
                    ["launchctl", "list", f"com.{self.service_name}"]
                )
                return code == 0

        except Exception:
            return False

        return False

    def _is_enabled(self, platform: Platform) -> bool:
        """Check if service is enabled at boot."""
        try:
            if platform.system == "Linux":
                _, code = self._transport.run_command(
                    ["systemctl", "is-enabled", self.service_name]
                )
                return code == 0

            elif platform.system == "Darwin":
                # macOS launchctl doesn't have direct "is-enabled" check
                return True

        except Exception:
            return False

        return False

    def _start(self, platform: Platform) -> None:
        """Start service."""
        if platform.system == "Linux":
            output, code = self._transport.run_command(
                ["systemctl", "start", self.service_name]
            )
            if code != 0:
                raise RuntimeError(f"Failed to start service: {output}")
        elif platform.system == "Darwin":
            output, code = self._transport.run_command(
                ["launchctl", "start", self.service_name]
            )
            if code != 0:
                raise RuntimeError(f"Failed to start service: {output}")

    def _stop(self, platform: Platform) -> None:
        """Stop service."""
        if platform.system == "Linux":
            output, code = self._transport.run_command(
                ["systemctl", "stop", self.service_name]
            )
            if code != 0:
                raise RuntimeError(f"Failed to stop service: {output}")
        elif platform.system == "Darwin":
            output, code = self._transport.run_command(
                ["launchctl", "stop", self.service_name]
            )
            if code != 0:
                raise RuntimeError(f"Failed to stop service: {output}")

    def _enable(self, platform: Platform) -> None:
        """Enable service at boot."""
        if platform.system == "Linux":
            output, code = self._transport.run_command(
                ["systemctl", "enable", self.service_name]
            )
            if code != 0:
                raise RuntimeError(f"Failed to enable service: {output}")
        elif platform.system == "Darwin":
            # macOS services are enabled by being in LaunchAgents/LaunchDaemons
            pass

    def _disable(self, platform: Platform) -> None:
        """Disable service at boot."""
        if platform.system == "Linux":
            output, code = self._transport.run_command(
                ["systemctl", "disable", self.service_name]
            )
            if code != 0:
                raise RuntimeError(f"Failed to disable service: {output}")

    def reload(self, platform: Platform) -> None:
        """Reload service configuration."""
        if platform.system == "Linux":
            output, code = self._transport.run_command(
                ["systemctl", "reload", self.service_name]
            )
            if code != 0:
                raise RuntimeError(f"Failed to reload service: {output}")

    def restart(self, platform: Platform) -> None:
        """Restart service."""
        if platform.system == "Linux":
            output, code = self._transport.run_command(
                ["systemctl", "restart", self.service_name]
            )
            if code != 0:
                raise RuntimeError(f"Failed to restart service: {output}")
        elif platform.system == "Darwin":
            # Stop first (ignore output/errors)
            self._transport.run_command(["launchctl", "stop", self.service_name])
            # Then start and check result
            output, code = self._transport.run_command(
                ["launchctl", "start", self.service_name]
            )
            if code != 0:
                raise RuntimeError(f"Failed to restart service: {output}")

    def should_reload(self, changed_resource_ids: List[str]) -> bool:
        """Check if service should reload based on changed resources."""
        return any(rid in changed_resource_ids for rid in self.reload_on)

    def should_restart(self, changed_resource_ids: List[str]) -> bool:
        """Check if service should restart based on changed resources."""
        return any(rid in changed_resource_ids for rid in self.restart_on)
