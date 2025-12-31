"""
Repository resource - manage package repositories and package manager operations.

Supports:
- apt (Debian/Ubuntu) - repository management, update, upgrade
- dnf (Fedora/RHEL) - repository management, update, upgrade
- pacman (Arch) - repository management, update, upgrade
- brew (macOS) - tap management, update, upgrade
"""

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, Optional

from cook.core import Action, Plan, Platform, Resource
from cook.core.executor import get_executor
from cook.logging import get_cook_logger

logger = get_cook_logger(__name__)


class Repository(Resource):
    """
    Repository resource for managing package repositories and system updates.

    Actions:
    - update: Update package cache (apt-get update, dnf check-update, etc.)
    - upgrade: Upgrade all packages (apt-get upgrade, dnf upgrade, etc.)
    - add: Add a new repository with optional GPG key

    Examples:
        # Update package cache
        Repository("apt-update", action="update")

        # Upgrade all packages
        Repository("apt-upgrade", action="upgrade")

        # Add NodeSource repository
        Repository("nodesource",
                   repo="deb https://deb.nodesource.com/node_20.x nodistro main",
                   key_url="https://deb.nodesource.com/gpgkey/nodesource.gpg.key",
                   key_id="9FD3B784BC1C6FC31A8A0A1C1655A0AB68576280")

        # Add Docker repository
        Repository("docker",
                   repo="deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable",
                   key_url="https://download.docker.com/linux/ubuntu/gpg",
                   key_id="9DC858229FC7DD38854AE2D88D81803C0EBFCD88")

        # Add PPA (Ubuntu)
        Repository("ondrej-php",
                   ppa="ppa:ondrej/php")

        # Homebrew tap (macOS)
        Repository("homebrew-core", tap="homebrew/core")
    """

    def __init__(
        self,
        name: str,
        action: str = "add",  # "add", "update", "upgrade"
        repo: Optional[str] = None,
        key_url: Optional[str] = None,
        key_id: Optional[str] = None,
        key_server: str = "keyserver.ubuntu.com",
        ppa: Optional[str] = None,
        tap: Optional[str] = None,
        filename: Optional[str] = None,
        ensure: str = "present",  # "present", "absent"
        **options,
    ):
        """
        Initialize repository resource.

        Args:
            name: Repository name/identifier
            action: "add", "update", or "upgrade"
            repo: Repository line (e.g., "deb https://... stable main")
            key_url: URL to GPG key
            key_id: GPG key ID (fingerprint)
            key_server: GPG key server (default: keyserver.ubuntu.com)
            ppa: PPA name (Ubuntu only, e.g., "ppa:ondrej/php")
            tap: Homebrew tap (macOS only, e.g., "homebrew/core")
            filename: Custom filename for sources list (default: {name}.list)
            ensure: "present" or "absent"
            **options: Additional options
        """
        super().__init__(name, **options)

        self.action = action.lower()
        self.repo = repo
        self.key_url = key_url
        self.key_id = key_id
        self.key_server = key_server
        self.ppa = ppa
        self.tap = tap
        self.filename = filename or f"{name}.list"
        self.ensure = ensure

        # Validate action
        valid_actions = ["add", "update", "upgrade"]
        if self.action not in valid_actions:
            raise ValueError(
                f"Invalid action '{self.action}'. Must be one of: {valid_actions}"
            )

        # Validate inputs based on action
        if self.action == "add":
            if not any([self.repo, self.ppa, self.tap]):
                raise ValueError(
                    "Repository 'add' action requires one of: repo, ppa, or tap"
                )

        # Auto-register
        get_executor().add(self)

    def resource_type(self) -> str:
        return "repository"

    def check(self, platform: Platform) -> Dict[str, Any]:
        """Check current repository state."""
        pm = self._get_package_manager(platform)

        if self.action == "update":
            return self._check_update(pm, platform)
        elif self.action == "upgrade":
            return self._check_upgrade(pm, platform)
        elif self.action == "add":
            return self._check_repository(pm, platform)

        return {"exists": False}

    def desired_state(self) -> Dict[str, Any]:
        """Return desired repository state."""
        if self.action == "update":
            # Update should run when cache is stale
            # Desired state has needs_update=False (cache should be fresh)
            # If actual needs_update=True, an UPDATE action is triggered
            return {"exists": True, "needs_update": False}
        elif self.action == "upgrade":
            # Upgrade should run when packages are upgradable
            # Desired state has needs_upgrade=False (all packages up to date)
            # If actual needs_upgrade=True, an UPDATE action is triggered
            return {"exists": True, "needs_upgrade": False}
        elif self.action == "add":
            return {
                "exists": self.ensure == "present",
                "repo_line": self.repo,
                "has_key": self.key_url is not None or self.key_id is not None,
            }

        return {"exists": False}

    def apply(self, plan: Plan, platform: Platform) -> None:
        """Apply repository changes."""
        pm = self._get_package_manager(platform)

        if self.action == "update":
            self._do_update(pm, platform)
        elif self.action == "upgrade":
            self._do_upgrade(pm, platform)
        elif self.action == "add":
            if plan.action == Action.CREATE:
                self._add_repository(pm, platform)
            elif plan.action == Action.DELETE:
                self._remove_repository(pm, platform)

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

    # ========================================================================
    # APT (Debian/Ubuntu)
    # ========================================================================

    def _check_update(self, pm: str, platform: Platform) -> Dict[str, Any]:
        """Check if package cache needs updating."""
        if pm == "apt":
            # Check age of apt cache
            cache_file = "/var/lib/apt/periodic/update-success-stamp"
            if self._transport.file_exists(cache_file):
                # Get file age in seconds
                output, code = self._transport.run_shell(
                    f"echo $(($(date +%s) - $(stat -c %Y {cache_file})))"
                )
                if code == 0:
                    age_seconds = int(output.strip())
                    # Consider cache fresh if < 1 hour old
                    needs_update = age_seconds > 3600
                    return {
                        "exists": True,
                        "needs_update": needs_update,
                        "cache_age_seconds": age_seconds,
                    }

            # Cache doesn't exist or couldn't check - needs update
            return {"exists": True, "needs_update": True}

        elif pm == "dnf":
            # DNF always needs update check (it's fast)
            return {"exists": True, "needs_update": True}

        elif pm == "pacman":
            # Check package database age
            db_file = "/var/lib/pacman/sync/core.db"
            if self._transport.file_exists(db_file):
                output, code = self._transport.run_shell(
                    f"echo $(($(date +%s) - $(stat -c %Y {db_file})))"
                )
                if code == 0:
                    age_seconds = int(output.strip())
                    needs_update = age_seconds > 3600
                    return {
                        "exists": True,
                        "needs_update": needs_update,
                        "cache_age_seconds": age_seconds,
                    }

            return {"exists": True, "needs_update": True}

        elif pm == "brew":
            # Brew update is always recommended
            return {"exists": True, "needs_update": True}

        return {"exists": False}

    def _check_upgrade(self, pm: str, platform: Platform) -> Dict[str, Any]:
        """Check if packages need upgrading."""
        if pm == "apt":
            # Check for upgradable packages
            output, code = self._transport.run_shell(
                "apt list --upgradable 2>/dev/null | grep -v 'Listing'"
            )
            upgradable = len(output.strip().split("\n")) if output.strip() else 0
            return {
                "exists": True,
                "needs_upgrade": upgradable > 0,
                "upgradable_count": upgradable,
            }

        elif pm == "dnf":
            output, code = self._transport.run_shell(
                "dnf check-update --quiet | wc -l"
            )
            upgradable = int(output.strip()) if output.strip().isdigit() else 0
            return {
                "exists": True,
                "needs_upgrade": upgradable > 0,
                "upgradable_count": upgradable,
            }

        elif pm == "pacman":
            output, code = self._transport.run_shell("pacman -Qu | wc -l")
            upgradable = int(output.strip()) if output.strip().isdigit() else 0
            return {
                "exists": True,
                "needs_upgrade": upgradable > 0,
                "upgradable_count": upgradable,
            }

        elif pm == "brew":
            output, code = self._transport.run_shell("brew outdated | wc -l")
            upgradable = int(output.strip()) if output.strip().isdigit() else 0
            return {
                "exists": True,
                "needs_upgrade": upgradable > 0,
                "upgradable_count": upgradable,
            }

        return {"exists": False}

    def _check_repository(self, pm: str, platform: Platform) -> Dict[str, Any]:
        """Check if repository is configured."""
        if pm == "apt":
            if self.ppa:
                # Check for PPA in sources
                ppa_name = self.ppa.replace("ppa:", "")
                source_file = f"/etc/apt/sources.list.d/{ppa_name.replace('/', '-')}-*.list"
                output, code = self._transport.run_shell(f"ls {source_file} 2>/dev/null")
                return {
                    "exists": code == 0,
                    "source_file": output.strip() if code == 0 else None,
                }
            else:
                # Check for custom repository
                source_file = f"/etc/apt/sources.list.d/{self.filename}"
                exists = self._transport.file_exists(source_file)

                if exists and self.repo:
                    # Verify content matches
                    content = self._transport.read_file(source_file).decode("utf-8")
                    # Expand $(lsb_release -cs) in repo line
                    expanded_repo = self._expand_repo_vars(self.repo, platform)
                    matches = expanded_repo in content

                    return {
                        "exists": matches,
                        "source_file": source_file,
                        "repo_line": expanded_repo,
                    }

                return {"exists": exists, "source_file": source_file}

        elif pm == "dnf":
            # Check for repo file in /etc/yum.repos.d/
            repo_file = f"/etc/yum.repos.d/{self.name}.repo"
            exists = self._transport.file_exists(repo_file)
            return {"exists": exists, "repo_file": repo_file}

        elif pm == "pacman":
            # Check pacman.conf for repository
            conf_file = "/etc/pacman.conf"
            if self._transport.file_exists(conf_file):
                content = self._transport.read_file(conf_file).decode("utf-8")
                exists = f"[{self.name}]" in content
                return {"exists": exists}
            return {"exists": False}

        elif pm == "brew":
            if self.tap:
                # Check if tap is installed
                output, code = self._transport.run_command(["brew", "tap"])
                taps = output.split("\n")
                exists = self.tap in taps
                return {"exists": exists, "tap": self.tap}
            return {"exists": False}

        return {"exists": False}

    def _do_update(self, pm: str, platform: Platform) -> None:
        """Update package cache."""
        logger.info(f"Updating package cache ({pm})...")

        if pm == "apt":
            output, code = self._transport.run_shell(
                "DEBIAN_FRONTEND=noninteractive apt-get update -y"
            )
            if code != 0:
                raise RuntimeError(f"apt-get update failed: {output}")

        elif pm == "dnf":
            output, code = self._transport.run_command(["dnf", "check-update", "-y"])
            # dnf check-update returns 100 if updates are available, 0 if not
            if code not in [0, 100]:
                raise RuntimeError(f"dnf check-update failed: {output}")

        elif pm == "pacman":
            output, code = self._transport.run_command(["pacman", "-Sy"])
            if code != 0:
                raise RuntimeError(f"pacman -Sy failed: {output}")

        elif pm == "brew":
            output, code = self._transport.run_command(["brew", "update"])
            if code != 0:
                raise RuntimeError(f"brew update failed: {output}")

    def _do_upgrade(self, pm: str, platform: Platform) -> None:
        """Upgrade all packages."""
        logger.info(f"Upgrading packages ({pm})...")

        if pm == "apt":
            output, code = self._transport.run_shell(
                "DEBIAN_FRONTEND=noninteractive apt-get upgrade -y"
            )
            if code != 0:
                raise RuntimeError(f"apt-get upgrade failed: {output}")

        elif pm == "dnf":
            output, code = self._transport.run_command(["dnf", "upgrade", "-y"])
            if code != 0:
                raise RuntimeError(f"dnf upgrade failed: {output}")

        elif pm == "pacman":
            output, code = self._transport.run_command(["pacman", "-Su", "--noconfirm"])
            if code != 0:
                raise RuntimeError(f"pacman -Su failed: {output}")

        elif pm == "brew":
            output, code = self._transport.run_command(["brew", "upgrade"])
            if code != 0:
                raise RuntimeError(f"brew upgrade failed: {output}")

    def _add_repository(self, pm: str, platform: Platform) -> None:
        """Add repository."""
        logger.info(f"Adding repository '{self.name}'...")

        if pm == "apt":
            if self.ppa:
                # Add PPA using add-apt-repository
                output, code = self._transport.run_shell(
                    f"DEBIAN_FRONTEND=noninteractive add-apt-repository -y {self.ppa}"
                )
                if code != 0:
                    raise RuntimeError(f"Failed to add PPA: {output}")
            else:
                # Add custom repository
                # 1. Add GPG key if provided
                if self.key_url:
                    self._add_apt_key_from_url(self.key_url, platform)
                elif self.key_id:
                    self._add_apt_key_from_keyserver(
                        self.key_id, self.key_server, platform
                    )

                # 2. Add repository line
                expanded_repo = self._expand_repo_vars(self.repo, platform)
                source_file = f"/etc/apt/sources.list.d/{self.filename}"
                content = f"# {self.name}\n{expanded_repo}\n"
                self._transport.write_file(source_file, content.encode("utf-8"))

                logger.info(f"Repository added to {source_file}")

        elif pm == "dnf":
            # Create .repo file
            repo_file = f"/etc/yum.repos.d/{self.name}.repo"
            content = self._generate_dnf_repo_file()
            self._transport.write_file(repo_file, content.encode("utf-8"))

        elif pm == "pacman":
            # Add to pacman.conf
            if self.repo:
                conf_file = "/etc/pacman.conf"
                repo_block = f"\n[{self.name}]\n{self.repo}\n"
                # Append to config
                output, code = self._transport.run_shell(
                    f"echo '{repo_block}' >> {conf_file}"
                )
                if code != 0:
                    raise RuntimeError(f"Failed to add repository: {output}")

        elif pm == "brew":
            if self.tap:
                output, code = self._transport.run_command(["brew", "tap", self.tap])
                if code != 0:
                    raise RuntimeError(f"Failed to add tap: {output}")

    def _remove_repository(self, pm: str, platform: Platform) -> None:
        """Remove repository."""
        logger.info(f"Removing repository '{self.name}'...")

        if pm == "apt":
            if self.ppa:
                output, code = self._transport.run_shell(
                    f"DEBIAN_FRONTEND=noninteractive add-apt-repository --remove -y {self.ppa}"
                )
                if code != 0:
                    raise RuntimeError(f"Failed to remove PPA: {output}")
            else:
                source_file = f"/etc/apt/sources.list.d/{self.filename}"
                self._transport.run_command(["rm", "-f", source_file])

        elif pm == "dnf":
            repo_file = f"/etc/yum.repos.d/{self.name}.repo"
            self._transport.run_command(["rm", "-f", repo_file])

        elif pm == "brew":
            if self.tap:
                self._transport.run_command(["brew", "untap", self.tap])

    def _add_apt_key_from_url(self, key_url: str, platform: Platform) -> None:
        """Add APT GPG key from URL."""
        # Modern approach: add to /etc/apt/trusted.gpg.d/
        key_filename = f"{self.name}.gpg"
        key_path = f"/etc/apt/trusted.gpg.d/{key_filename}"

        # Download and add key
        cmd = f"curl -fsSL {key_url} | gpg --dearmor -o {key_path}"
        output, code = self._transport.run_shell(cmd)
        if code != 0:
            raise RuntimeError(f"Failed to add GPG key: {output}")

        logger.info(f"GPG key added to {key_path}")

    def _add_apt_key_from_keyserver(
        self, key_id: str, key_server: str, platform: Platform
    ) -> None:
        """Add APT GPG key from keyserver."""
        key_filename = f"{self.name}.gpg"
        key_path = f"/etc/apt/trusted.gpg.d/{key_filename}"

        # Fetch key from keyserver
        cmd = f"gpg --keyserver {key_server} --recv-keys {key_id} && gpg --export {key_id} > {key_path}"
        output, code = self._transport.run_shell(cmd)
        if code != 0:
            raise RuntimeError(f"Failed to fetch GPG key: {output}")

        logger.info(f"GPG key {key_id} added to {key_path}")

    def _expand_repo_vars(self, repo_line: str, platform: Platform) -> str:
        """Expand variables in repository line."""
        if "$(lsb_release -cs)" in repo_line:
            # Get codename
            output, code = self._transport.run_shell("lsb_release -cs")
            if code == 0:
                codename = output.strip()
                repo_line = repo_line.replace("$(lsb_release -cs)", codename)

        return repo_line

    def _generate_dnf_repo_file(self) -> str:
        """Generate DNF repository file content."""
        content = f"[{self.name}]\n"
        content += f"name={self.name}\n"

        if self.repo:
            content += f"baseurl={self.repo}\n"

        if self.key_url:
            content += f"gpgkey={self.key_url}\n"
            content += "gpgcheck=1\n"
        else:
            content += "gpgcheck=0\n"

        content += "enabled=1\n"

        return content
