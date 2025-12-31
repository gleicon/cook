"""
Unit tests for Repository resource.

Tests repository management operations in isolation using mocks.
"""

import pytest
from unittest.mock import Mock, MagicMock

from cook.core import Platform, Action
from cook.core.executor import reset_executor
from cook.resources.repository import Repository
from cook.transport import NullTransport


class MockTransport:
    """Mock transport for testing."""

    def __init__(self):
        self.files = {}
        self.commands = []
        self.shells = []

    def file_exists(self, path):
        return path in self.files

    def read_file(self, path):
        if path in self.files:
            return self.files[path].encode("utf-8")
        raise FileNotFoundError(path)

    def write_file(self, path, content):
        self.files[path] = content.decode("utf-8") if isinstance(content, bytes) else content

    def run_command(self, cmd):
        self.commands.append(cmd)
        return ("", 0)

    def run_shell(self, cmd):
        self.shells.append(cmd)
        # Mock responses for common commands
        if "lsb_release -cs" in cmd:
            return ("jammy", 0)
        if "apt list --upgradable" in cmd:
            return ("nginx/jammy 1.18.0-1 amd64 [upgradable from: 1.17.0-1]", 0)
        if "date +%s" in cmd or "stat" in cmd:
            return ("7200", 0)  # 2 hours old
        return ("", 0)


class TestRepositoryResource:
    """Unit tests for Repository resource."""

    def setup_method(self):
        """Reset executor before each test."""
        reset_executor()

    def test_repository_init_update(self):
        """Test Repository initialization for update action."""
        repo = Repository("apt-update", action="update")

        assert repo.name == "apt-update"
        assert repo.action == "update"
        assert repo.resource_type() == "repository"

    def test_repository_init_upgrade(self):
        """Test Repository initialization for upgrade action."""
        repo = Repository("apt-upgrade", action="upgrade")

        assert repo.name == "apt-upgrade"
        assert repo.action == "upgrade"

    def test_repository_init_add_custom(self):
        """Test Repository initialization for adding custom repository."""
        repo = Repository(
            "nodesource",
            action="add",
            repo="deb https://deb.nodesource.com/node_20.x nodistro main",
            key_url="https://deb.nodesource.com/gpgkey/nodesource.gpg.key"
        )

        assert repo.name == "nodesource"
        assert repo.action == "add"
        assert repo.repo is not None
        assert repo.key_url is not None

    def test_repository_init_add_ppa(self):
        """Test Repository initialization for adding PPA."""
        repo = Repository(
            "ondrej-php",
            action="add",
            ppa="ppa:ondrej/php"
        )

        assert repo.name == "ondrej-php"
        assert repo.ppa == "ppa:ondrej/php"

    def test_repository_init_invalid_action(self):
        """Test Repository initialization with invalid action."""
        with pytest.raises(ValueError, match="Invalid action"):
            Repository("test", action="invalid")

    def test_repository_init_add_no_repo(self):
        """Test Repository initialization for add without repository."""
        with pytest.raises(ValueError, match="requires one of"):
            Repository("test", action="add")

    def test_repository_check_update_fresh_cache(self):
        """Test checking update with fresh cache."""
        repo = Repository("apt-update", action="update")
        repo._transport = MockTransport()
        repo._transport.files["/var/lib/apt/periodic/update-success-stamp"] = ""

        platform = Platform(system="Linux", distro="ubuntu", version="22.04", arch="x86_64")

        # Mock recent cache (1 hour old)
        repo._transport.run_shell = lambda cmd: ("3600", 0) if "date +%s" in cmd else ("", 0)

        state = repo.check(platform)

        assert state["exists"] is True
        assert state["needs_update"] is False

    def test_repository_check_update_stale_cache(self):
        """Test checking update with stale cache."""
        repo = Repository("apt-update", action="update")
        repo._transport = MockTransport()
        repo._transport.files["/var/lib/apt/periodic/update-success-stamp"] = ""

        platform = Platform(system="Linux", distro="ubuntu", version="22.04", arch="x86_64")

        # Mock old cache (2 hours old)
        repo._transport.run_shell = lambda cmd: ("7200", 0) if "date +%s" in cmd else ("", 0)

        state = repo.check(platform)

        assert state["exists"] is True
        assert state["needs_update"] is True

    def test_repository_check_upgrade_needed(self):
        """Test checking upgrade when packages are upgradable."""
        repo = Repository("apt-upgrade", action="upgrade")
        repo._transport = MockTransport()

        platform = Platform(system="Linux", distro="ubuntu", version="22.04", arch="x86_64")

        state = repo.check(platform)

        assert state["exists"] is True
        assert state["needs_upgrade"] is True
        assert state["upgradable_count"] > 0

    def test_repository_check_add_not_exists(self):
        """Test checking repository that doesn't exist."""
        repo = Repository(
            "nodesource",
            action="add",
            repo="deb https://deb.nodesource.com/node_20.x nodistro main"
        )
        repo._transport = MockTransport()

        platform = Platform(system="Linux", distro="ubuntu", version="22.04", arch="x86_64")

        state = repo.check(platform)

        assert state["exists"] is False

    def test_repository_check_add_exists(self):
        """Test checking repository that exists."""
        repo = Repository(
            "nodesource",
            action="add",
            repo="deb https://deb.nodesource.com/node_20.x nodistro main",
            filename="nodesource.list"
        )
        repo._transport = MockTransport()
        repo._transport.files["/etc/apt/sources.list.d/nodesource.list"] = (
            "deb https://deb.nodesource.com/node_20.x nodistro main\n"
        )

        platform = Platform(system="Linux", distro="ubuntu", version="22.04", arch="x86_64")

        state = repo.check(platform)

        assert state["exists"] is True

    def test_repository_desired_state_update(self):
        """Test desired state for update action."""
        repo = Repository("apt-update", action="update")

        desired = repo.desired_state()

        assert desired["exists"] is True
        # Desired state is False (cache should be fresh)
        # When actual is True (cache is stale), UPDATE action is triggered
        assert desired["needs_update"] is False

    def test_repository_desired_state_upgrade(self):
        """Test desired state for upgrade action."""
        repo = Repository("apt-upgrade", action="upgrade")

        desired = repo.desired_state()

        assert desired["exists"] is True
        # Desired state is False (all packages up to date)
        # When actual is True (packages need upgrade), UPDATE action is triggered
        assert desired["needs_upgrade"] is False

    def test_repository_desired_state_add(self):
        """Test desired state for add action."""
        repo = Repository(
            "nodesource",
            action="add",
            repo="deb https://deb.nodesource.com/node_20.x nodistro main",
            key_url="https://example.com/key.gpg"
        )

        desired = repo.desired_state()

        assert desired["exists"] is True
        assert desired["repo_line"] is not None
        assert desired["has_key"] is True

    def test_repository_plan_update(self):
        """Test planning update action."""
        repo = Repository("apt-update", action="update")
        repo._transport = MockTransport()

        platform = Platform(system="Linux", distro="ubuntu", version="22.04", arch="x86_64")

        plan = repo.plan(platform)

        # Update should show changes if cache is stale
        assert plan.action in [Action.UPDATE, Action.NONE]

    def test_repository_plan_add_create(self):
        """Test planning repository addition when it doesn't exist."""
        repo = Repository(
            "nodesource",
            action="add",
            repo="deb https://deb.nodesource.com/node_20.x nodistro main"
        )
        repo._transport = MockTransport()

        platform = Platform(system="Linux", distro="ubuntu", version="22.04", arch="x86_64")

        plan = repo.plan(platform)

        assert plan.action == Action.CREATE
        assert plan.has_changes()

    def test_repository_expand_vars(self):
        """Test expansion of variables in repository line."""
        repo = Repository(
            "docker",
            action="add",
            repo="deb https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
        )
        repo._transport = MockTransport()

        platform = Platform(system="Linux", distro="ubuntu", version="22.04", arch="x86_64")

        expanded = repo._expand_repo_vars(repo.repo, platform)

        assert "$(lsb_release -cs)" not in expanded
        assert "jammy" in expanded

    def test_repository_generate_dnf_repo_file(self):
        """Test generating DNF repository file."""
        repo = Repository(
            "docker",
            action="add",
            repo="https://download.docker.com/linux/fedora/docker-ce.repo",
            key_url="https://download.docker.com/linux/fedora/gpg"
        )

        content = repo._generate_dnf_repo_file()

        assert "[docker]" in content
        assert "name=docker" in content
        assert "baseurl=" in content
        assert "gpgkey=" in content
        assert "gpgcheck=1" in content

    def test_repository_get_package_manager_ubuntu(self):
        """Test package manager detection for Ubuntu."""
        repo = Repository("test", action="update")
        platform = Platform(system="Linux", distro="ubuntu", version="22.04", arch="x86_64")

        pm = repo._get_package_manager(platform)

        assert pm == "apt"

    def test_repository_get_package_manager_fedora(self):
        """Test package manager detection for Fedora."""
        repo = Repository("test", action="update")
        platform = Platform(system="Linux", distro="fedora", version="38", arch="x86_64")

        pm = repo._get_package_manager(platform)

        assert pm == "dnf"

    def test_repository_get_package_manager_arch(self):
        """Test package manager detection for Arch."""
        repo = Repository("test", action="update")
        platform = Platform(system="Linux", distro="arch", version="", arch="x86_64")

        pm = repo._get_package_manager(platform)

        assert pm == "pacman"

    def test_repository_get_package_manager_macos(self):
        """Test package manager detection for macOS."""
        repo = Repository("test", action="update")
        platform = Platform(system="Darwin", distro="macos", version="13.0", arch="arm64")

        pm = repo._get_package_manager(platform)

        assert pm == "brew"

    def test_repository_get_package_manager_unsupported(self):
        """Test package manager detection for unsupported platform."""
        repo = Repository("test", action="update")
        platform = Platform(system="Windows", distro="windows", version="10", arch="x86_64")

        with pytest.raises(ValueError, match="Unsupported platform"):
            repo._get_package_manager(platform)

    def test_repository_id_format(self):
        """Test repository resource ID format."""
        repo = Repository("apt-update", action="update")

        assert repo.id == "repository:apt-update"

    def test_repository_ensure_absent(self):
        """Test repository with ensure=absent."""
        repo = Repository(
            "test-repo",
            action="add",
            repo="deb https://example.com/repo stable main",
            ensure="absent"
        )

        desired = repo.desired_state()

        assert desired["exists"] is False

    def test_repository_multiple_actions_same_name(self):
        """Test that different actions have different resource names."""
        # Different actions should have different resource names to avoid conflicts
        update = Repository("system-update", action="update")
        upgrade = Repository("system-upgrade", action="upgrade")

        assert update.action == "update"
        assert upgrade.action == "upgrade"
        assert update.id != upgrade.id  # Different IDs for different actions


class TestRepositoryIntegration:
    """Integration-style tests with more realistic mocking."""

    def setup_method(self):
        """Reset executor before each test."""
        reset_executor()

    def test_apt_update_workflow(self):
        """Test complete APT update workflow."""
        repo = Repository("apt-update", action="update")
        transport = MockTransport()
        # Make the cache file exist and be stale
        transport.files["/var/lib/apt/periodic/update-success-stamp"] = ""

        # Override run_shell to return stale cache age
        original_run_shell = transport.run_shell
        def stale_cache_shell(cmd):
            if "date +%s" in cmd or "stat -c %Y" in cmd:
                return ("7200", 0)  # 2 hours old
            return original_run_shell(cmd)
        transport.run_shell = stale_cache_shell

        repo._transport = transport

        platform = Platform(system="Linux", distro="ubuntu", version="22.04", arch="x86_64")

        # Check state - should detect stale cache
        state = repo.check(platform)
        assert state["needs_update"] is True

        # Plan should show changes needed
        plan = repo.plan(platform)
        assert plan.has_changes()

        # Apply
        repo.apply(plan, platform)

        # Verify apt-get update was executed
        assert any("apt-get update" in str(cmd) for cmd in transport.shells)

    def test_add_repository_workflow(self):
        """Test complete add repository workflow."""
        repo = Repository(
            "docker",
            action="add",
            repo="deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable",
            key_url="https://download.docker.com/linux/ubuntu/gpg"
        )
        repo._transport = MockTransport()

        platform = Platform(system="Linux", distro="ubuntu", version="22.04", arch="x86_64")

        # Check, plan, apply
        state = repo.check(platform)
        plan = repo.plan(platform)

        assert plan.action == Action.CREATE

        repo.apply(plan, platform)

        # Verify repository file was created
        assert "/etc/apt/sources.list.d/docker.list" in repo._transport.files

        # Verify GPG key was added
        assert any("gpg" in str(cmd) for cmd in repo._transport.shells)

    def test_ppa_workflow(self):
        """Test PPA addition workflow."""
        repo = Repository(
            "ondrej-php",
            action="add",
            ppa="ppa:ondrej/php"
        )
        repo._transport = MockTransport()

        platform = Platform(system="Linux", distro="ubuntu", version="22.04", arch="x86_64")

        # Mock that the PPA does not exist
        original_run_shell = repo._transport.run_shell
        def custom_run_shell(cmd):
            if "ls /etc/apt/sources.list.d/" in cmd:
                return ("", 1)  # File not found
            return original_run_shell(cmd)
        repo._transport.run_shell = custom_run_shell

        plan = repo.plan(platform)
        assert plan.action == Action.CREATE

        repo.apply(plan, platform)

        # Verify add-apt-repository was called
        assert any("add-apt-repository" in str(cmd) for cmd in repo._transport.shells)
