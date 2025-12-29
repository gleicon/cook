"""
Package resource - manage system packages.

Supports:
- apt (Debian/Ubuntu)
- dnf (Fedora/RHEL)
- pacman (Arch)
- brew (macOS)
"""

import os
from typing import Dict, Any, Optional, List

from cook.core.resource import Resource, Plan, Action, Platform
from cook.core.executor import get_executor


class Package(Resource):
    """
    Package resource for installing system packages.

    Examples:
        # Single package
        Package("nginx")

        # Specific version (if supported by package manager)
        Package("nginx", version="1.18.0-1ubuntu1")

        # Ensure absent
        Package("apache2", ensure="absent")

        # Multiple packages (convenience syntax)
        Package(["gcc", "make", "autoconf"])

        # Multiple packages (named group)
        Package("build-tools", packages=["gcc", "make", "autoconf"])
    """

    def __init__(
        self,
        name,  # Can be str or List[str]
        version: Optional[str] = None,
        ensure: str = "present",  # "present", "absent", "latest"
        packages: Optional[List[str]] = None,
        **options
    ):
        """
        Initialize package resource.

        Args:
            name: Package name (str) OR list of package names (for convenience)
            version: Specific version to install
            ensure: "present", "absent", or "latest"
            packages: List of package names (if managing multiple)
            **options: Additional options
        """
        # Handle both Package("nginx") and Package(["nginx", "curl"])
        if isinstance(name, list):
            # Convenience syntax: Package([...])
            packages = name
            # Generate a resource name from first package
            resource_name = f"pkg:{packages[0]}" if packages else "pkg:empty"
        else:
            resource_name = name

        super().__init__(resource_name, **options)

        self.package_name = name if isinstance(name, str) and not packages else None
        self.packages = packages or ([name] if isinstance(name, str) else [])
        self.version = version
        self.ensure = ensure

        # Auto-register
        get_executor().add(self)

    def resource_type(self) -> str:
        return "pkg"

    def check(self, platform: Platform) -> Dict[str, Any]:
        """Check if package is installed."""
        # Get package manager
        pm = self._get_package_manager(platform)

        installed_packages = {}

        for pkg in self.packages:
            version = self._check_package(pkg, pm, platform)
            installed_packages[pkg] = {
                "installed": version is not None,
                "version": version,
            }

        return {
            "exists": all(p["installed"] for p in installed_packages.values()),
            "packages": installed_packages,
        }

    def desired_state(self) -> Dict[str, Any]:
        """Return desired package state."""
        return {
            "exists": self.ensure in ["present", "latest"],
            "version": self.version,
        }

    def apply(self, plan: Plan, platform: Platform) -> None:
        """Apply package changes."""
        pm = self._get_package_manager(platform)

        if plan.action == Action.CREATE:
            self._install(pm, platform)
        elif plan.action == Action.DELETE:
            self._remove(pm, platform)
        elif plan.action == Action.UPDATE:
            self._upgrade(pm, platform)

    def _get_package_manager(self, platform: Platform) -> str:
        """Detect package manager."""
        if platform.distro in ["ubuntu", "debian"]:
            return "apt"
        elif platform.distro in ["fedora", "rhel", "centos"]:
            return "dnf"
        elif platform.distro == "arch":
            return "pacman"
        elif platform.system == "Darwin":
            return "brew"
        else:
            raise ValueError(f"Unsupported platform: {platform.distro}")

    def _check_package(self, pkg: str, pm: str, platform: Platform) -> Optional[str]:
        """Check if package is installed and return version."""
        try:
            if pm == "apt":
                output, code = self._transport.run_command(
                    ["dpkg-query", "-W", "-f=${Version}", pkg]
                )
                return output.strip() if code == 0 else None

            elif pm == "dnf":
                output, code = self._transport.run_command(
                    ["rpm", "-q", "--queryformat", "%{VERSION}", pkg]
                )
                return output.strip() if code == 0 else None

            elif pm == "pacman":
                output, code = self._transport.run_command(["pacman", "-Q", pkg])
                if code == 0:
                    # Output: "package-name version"
                    return output.strip().split()[1]
                return None

            elif pm == "brew":
                output, code = self._transport.run_command(
                    ["brew", "list", "--versions", pkg]
                )
                if code == 0:
                    # Output: "package version"
                    parts = output.strip().split()
                    return parts[1] if len(parts) > 1 else None
                return None

        except FileNotFoundError:
            raise ValueError(f"Package manager not found: {pm}")

    def _install(self, pm: str, platform: Platform) -> None:
        """Install packages."""
        if pm == "apt":
            cmd = ["apt-get", "install", "-y"] + self.packages
            # Set DEBIAN_FRONTEND=noninteractive via environment
            output, code = self._transport.run_shell(
                f"DEBIAN_FRONTEND=noninteractive {' '.join(cmd)}"
            )
            if code != 0:
                raise RuntimeError(f"Package installation failed: {output}")
        elif pm == "dnf":
            cmd = ["dnf", "install", "-y"] + self.packages
            output, code = self._transport.run_command(cmd)
            if code != 0:
                raise RuntimeError(f"Package installation failed: {output}")
        elif pm == "pacman":
            cmd = ["pacman", "-S", "--noconfirm"] + self.packages
            output, code = self._transport.run_command(cmd)
            if code != 0:
                raise RuntimeError(f"Package installation failed: {output}")
        elif pm == "brew":
            cmd = ["brew", "install"] + self.packages
            output, code = self._transport.run_command(cmd)
            if code != 0:
                raise RuntimeError(f"Package installation failed: {output}")

    def _remove(self, pm: str, platform: Platform) -> None:
        """Remove packages."""
        if pm == "apt":
            cmd = ["apt-get", "remove", "-y"] + self.packages
            output, code = self._transport.run_shell(
                f"DEBIAN_FRONTEND=noninteractive {' '.join(cmd)}"
            )
            if code != 0:
                raise RuntimeError(f"Package removal failed: {output}")
        elif pm == "dnf":
            cmd = ["dnf", "remove", "-y"] + self.packages
            output, code = self._transport.run_command(cmd)
            if code != 0:
                raise RuntimeError(f"Package removal failed: {output}")
        elif pm == "pacman":
            cmd = ["pacman", "-R", "--noconfirm"] + self.packages
            output, code = self._transport.run_command(cmd)
            if code != 0:
                raise RuntimeError(f"Package removal failed: {output}")
        elif pm == "brew":
            cmd = ["brew", "uninstall"] + self.packages
            output, code = self._transport.run_command(cmd)
            if code != 0:
                raise RuntimeError(f"Package removal failed: {output}")

    def _upgrade(self, pm: str, platform: Platform) -> None:
        """Upgrade packages to latest version."""
        # For now, just reinstall
        self._install(pm, platform)
