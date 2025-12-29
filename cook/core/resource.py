"""
Core resource abstraction for Cook.

All resources (File, Package, Service, etc.) inherit from Resource
and implement the Check/Plan/Apply pattern.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, TYPE_CHECKING
import platform as platform_module

if TYPE_CHECKING:
    from cook.transport import Transport


class Action(Enum):
    """Resource actions during apply."""
    NONE = "none"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class Change:
    """Represents a single property change."""
    field: str
    from_value: Any
    to_value: Any

    def __str__(self):
        return f"{self.field}: {self.from_value} → {self.to_value}"


@dataclass
class Plan:
    """
    Execution plan for a resource.

    Similar to Terraform's plan, shows what will change.
    """
    action: Action
    changes: List[Change] = field(default_factory=list)
    reason: str = ""

    def has_changes(self) -> bool:
        """Check if plan has any changes."""
        return self.action != Action.NONE and len(self.changes) > 0

    def __str__(self):
        if self.action == Action.NONE:
            return "No changes"

        lines = [f"Action: {self.action.value}"]
        if self.reason:
            lines.append(f"Reason: {self.reason}")
        for change in self.changes:
            lines.append(f"  {change}")
        return "\n".join(lines)


@dataclass
class Platform:
    """Platform information (OS, distro, version)."""
    system: str  # Linux, Darwin, Windows
    distro: str  # ubuntu, debian, arch, etc.
    version: str
    arch: str

    @classmethod
    def detect(cls, transport: Optional["Transport"] = None) -> "Platform":
        """
        Detect platform information.

        Args:
            transport: Transport to use for detection (None = local)

        Returns:
            Platform information
        """
        # Use local detection if no transport provided
        if transport is None:
            system = platform_module.system()
            arch = platform_module.machine()

            # Detect distro on Linux
            distro = "unknown"
            version = ""

            if system == "Linux":
                try:
                    import distro as distro_lib
                    distro = distro_lib.id()
                    version = distro_lib.version()
                except ImportError:
                    # Fallback: read /etc/os-release
                    try:
                        with open("/etc/os-release") as f:
                            for line in f:
                                if line.startswith("ID="):
                                    distro = line.split("=")[1].strip().strip('"')
                                elif line.startswith("VERSION_ID="):
                                    version = line.split("=")[1].strip().strip('"')
                    except FileNotFoundError:
                        pass
            elif system == "Darwin":
                distro = "macos"
                version = platform_module.mac_ver()[0]

            return cls(
                system=system,
                distro=distro,
                version=version,
                arch=arch,
            )

        # Remote platform detection via transport
        else:
            # Detect system
            output, _ = transport.run_shell("uname -s")
            system = output.strip()

            # Detect architecture
            output, _ = transport.run_shell("uname -m")
            arch = output.strip()

            distro = "unknown"
            version = ""

            # Detect distro on Linux
            if system == "Linux":
                # Try reading /etc/os-release
                try:
                    content = transport.read_file("/etc/os-release").decode()
                    for line in content.split("\n"):
                        if line.startswith("ID="):
                            distro = line.split("=")[1].strip().strip('"')
                        elif line.startswith("VERSION_ID="):
                            version = line.split("=")[1].strip().strip('"')
                except (FileNotFoundError, Exception):
                    pass
            elif system == "Darwin":
                distro = "macos"
                output, _ = transport.run_shell("sw_vers -productVersion")
                version = output.strip()

            return cls(
                system=system,
                distro=distro,
                version=version,
                arch=arch,
            )


class Resource(ABC):
    """
    Base class for all resources.

    Resources follow the Check → Plan → Apply pattern:
    1. Check: Inspect current state
    2. Plan: Determine what needs to change
    3. Apply: Make the changes
    """

    def __init__(self, name: str, **options):
        """
        Initialize resource.

        Args:
            name: Resource identifier (e.g., "/etc/nginx.conf", "nginx")
            **options: Resource-specific options
        """
        self.name = name
        self.options = options
        self._desired_state: Dict[str, Any] = {}
        self._actual_state: Dict[str, Any] = {}
        self._transport: Optional["Transport"] = None  # Set by executor

    @property
    def id(self) -> str:
        """
        Unique resource identifier.

        Format: resource_type:name
        Example: file:/etc/nginx.conf, pkg:nginx
        """
        return f"{self.resource_type()}:{self.name}"

    @abstractmethod
    def resource_type(self) -> str:
        """Return resource type string (file, pkg, svc, exec)."""
        pass

    @abstractmethod
    def check(self, platform: Platform) -> Dict[str, Any]:
        """
        Check current state of the resource.

        Args:
            platform: Platform information

        Returns:
            Dictionary of current state properties

        Example:
            {"exists": True, "content": "...", "mode": 0o644}
        """
        pass

    @abstractmethod
    def desired_state(self) -> Dict[str, Any]:
        """
        Return desired state properties.

        Returns:
            Dictionary of desired state properties

        Example:
            {"exists": True, "content": "...", "mode": 0o644}
        """
        pass

    def plan(self, platform: Platform) -> Plan:
        """
        Generate execution plan by comparing desired vs actual state.

        Args:
            platform: Platform information

        Returns:
            Plan object describing changes
        """
        self._actual_state = self.check(platform)
        self._desired_state = self.desired_state()

        # Determine action
        exists = self._actual_state.get("exists", False)
        should_exist = self._desired_state.get("exists", True)

        if not exists and should_exist:
            action = Action.CREATE
            reason = "Resource does not exist"
        elif exists and not should_exist:
            action = Action.DELETE
            reason = "Resource should not exist"
        elif not exists and not should_exist:
            action = Action.NONE
            reason = "Resource correctly absent"
        else:
            # Resource exists and should exist - check for changes
            changes = self._detect_changes()
            if changes:
                action = Action.UPDATE
                reason = "Properties differ from desired state"
                return Plan(action=action, changes=changes, reason=reason)
            else:
                action = Action.NONE
                reason = "No changes needed"

        # Generate changes list for CREATE/DELETE
        changes = []
        if action == Action.CREATE:
            for key, value in self._desired_state.items():
                if key != "exists":
                    changes.append(Change(key, None, value))
        elif action == Action.DELETE:
            for key, value in self._actual_state.items():
                if key != "exists":
                    changes.append(Change(key, value, None))

        return Plan(action=action, changes=changes, reason=reason)

    def _detect_changes(self) -> List[Change]:
        """
        Detect changes between actual and desired state.

        Returns:
            List of Change objects
        """
        changes = []

        # Check all desired properties
        for key, desired_value in self._desired_state.items():
            if key == "exists":
                continue

            actual_value = self._actual_state.get(key)

            # Handle None values
            if desired_value is None and actual_value is None:
                continue

            # Compare values
            if actual_value != desired_value:
                changes.append(Change(key, actual_value, desired_value))

        return changes

    @abstractmethod
    def apply(self, plan: Plan, platform: Platform) -> None:
        """
        Apply the execution plan.

        Args:
            plan: Execution plan from plan()
            platform: Platform information

        Raises:
            Exception if apply fails
        """
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name!r})"

    def __str__(self):
        return self.id
