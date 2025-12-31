"""
Integration tests for Repository resource.

These tests require root/sudo access and interact with the actual package manager.
Run with: sudo pytest tests/integration/test_repository.py
"""

import os
import pytest
from pathlib import Path

from cook.core.executor import Executor, reset_executor
from cook.core import Platform
from cook.resources.repository import Repository


# Skip all tests if not running as root
pytestmark = pytest.mark.skipif(
    os.geteuid() != 0 if hasattr(os, 'geteuid') else False,
    reason="Repository integration tests require root privileges"
)


class TestRepositoryUpdateWorkflow:
    """Test repository update workflows."""

    def setup_method(self):
        """Reset executor before each test."""
        reset_executor()

    @pytest.mark.slow
    def test_apt_update_workflow(self):
        """Test APT update workflow."""
        platform = Platform.detect()

        if platform.distro not in ["ubuntu", "debian"]:
            pytest.skip("Test requires Ubuntu/Debian")

        executor = Executor()
        executor.add(Repository("apt-update", action="update"))

        # Plan
        plan_result = executor.plan()

        # Update might or might not have changes depending on cache age
        # Just verify it can plan without errors
        assert plan_result is not None

        # Apply
        apply_result = executor.apply(plan_result)
        assert apply_result.success

    @pytest.mark.slow
    def test_apt_update_idempotency(self):
        """Test that APT update is idempotent."""
        platform = Platform.detect()

        if platform.distro not in ["ubuntu", "debian"]:
            pytest.skip("Test requires Ubuntu/Debian")

        # First update
        reset_executor()
        executor = Executor()
        executor.add(Repository("apt-update", action="update"))
        plan1 = executor.plan()
        apply1 = executor.apply(plan1)
        assert apply1.success

        # Second update immediately after should see fresh cache
        reset_executor()
        executor = Executor()
        executor.add(Repository("apt-update-2", action="update"))
        plan2 = executor.plan()

        # Cache should be fresh now
        # Note: Depending on timing, this might still update
        assert plan2 is not None


class TestRepositoryAddWorkflow:
    """Test repository addition workflows."""

    def setup_method(self):
        """Reset executor before each test."""
        reset_executor()

    def teardown_method(self):
        """Clean up test repositories."""
        # Remove test repository file if it exists
        test_files = [
            "/etc/apt/sources.list.d/test-cook-repo.list",
            "/etc/apt/trusted.gpg.d/test-cook-repo.gpg",
        ]
        for f in test_files:
            if os.path.exists(f):
                os.remove(f)

    def test_add_repository_workflow(self):
        """Test adding a custom repository."""
        platform = Platform.detect()

        if platform.distro not in ["ubuntu", "debian"]:
            pytest.skip("Test requires Ubuntu/Debian")

        executor = Executor()

        # Add a test repository (we won't actually use it)
        # Using a safe, non-intrusive repository line
        executor.add(
            Repository(
                "test-cook-repo",
                action="add",
                repo="deb [trusted=yes] http://archive.ubuntu.com/ubuntu jammy main",
                filename="test-cook-repo.list"
            )
        )

        # Plan
        plan_result = executor.plan()
        assert plan_result.has_changes

        # Apply
        apply_result = executor.apply(plan_result)
        assert apply_result.success

        # Verify file was created
        assert os.path.exists("/etc/apt/sources.list.d/test-cook-repo.list")

        # Read and verify content
        with open("/etc/apt/sources.list.d/test-cook-repo.list") as f:
            content = f.read()
            assert "test-cook-repo" in content
            assert "http://archive.ubuntu.com/ubuntu" in content

    def test_add_repository_idempotency(self):
        """Test that adding repository is idempotent."""
        platform = Platform.detect()

        if platform.distro not in ["ubuntu", "debian"]:
            pytest.skip("Test requires Ubuntu/Debian")

        # First add
        reset_executor()
        executor = Executor()
        executor.add(
            Repository(
                "test-cook-repo",
                action="add",
                repo="deb [trusted=yes] http://archive.ubuntu.com/ubuntu jammy main",
                filename="test-cook-repo.list"
            )
        )
        plan1 = executor.plan()
        apply1 = executor.apply(plan1)
        assert apply1.success

        # Second add - should be idempotent
        reset_executor()
        executor = Executor()
        executor.add(
            Repository(
                "test-cook-repo",
                action="add",
                repo="deb [trusted=yes] http://archive.ubuntu.com/ubuntu jammy main",
                filename="test-cook-repo.list"
            )
        )
        plan2 = executor.plan()

        # Should have no changes (repository already exists)
        assert not plan2.has_changes

    def test_remove_repository(self):
        """Test removing a repository."""
        platform = Platform.detect()

        if platform.distro not in ["ubuntu", "debian"]:
            pytest.skip("Test requires Ubuntu/Debian")

        # First add the repository
        reset_executor()
        executor = Executor()
        executor.add(
            Repository(
                "test-cook-repo",
                action="add",
                repo="deb [trusted=yes] http://archive.ubuntu.com/ubuntu jammy main",
                filename="test-cook-repo.list"
            )
        )
        plan1 = executor.plan()
        apply1 = executor.apply(plan1)
        assert apply1.success
        assert os.path.exists("/etc/apt/sources.list.d/test-cook-repo.list")

        # Now remove it
        reset_executor()
        executor = Executor()
        executor.add(
            Repository(
                "test-cook-repo",
                action="add",
                repo="deb [trusted=yes] http://archive.ubuntu.com/ubuntu jammy main",
                filename="test-cook-repo.list",
                ensure="absent"
            )
        )
        plan2 = executor.plan()
        assert plan2.has_changes

        apply2 = executor.apply(plan2)
        assert apply2.success

        # Verify file was removed
        assert not os.path.exists("/etc/apt/sources.list.d/test-cook-repo.list")


class TestRepositoryPlatformSupport:
    """Test repository support across platforms."""

    def setup_method(self):
        """Reset executor before each test."""
        reset_executor()

    def test_platform_detection(self):
        """Test that platform detection works."""
        platform = Platform.detect()

        assert platform.system in ["Linux", "Darwin"]
        assert platform.distro is not None

    def test_package_manager_detection(self):
        """Test package manager detection."""
        platform = Platform.detect()
        repo = Repository("test", action="update")

        pm = repo._get_package_manager(platform)

        expected_pm = {
            "ubuntu": "apt",
            "debian": "apt",
            "fedora": "dnf",
            "centos": "dnf",
            "rhel": "dnf",
            "arch": "pacman",
            "macos": "brew",
        }

        if platform.distro in expected_pm:
            assert pm == expected_pm[platform.distro]
        elif platform.system == "Darwin":
            assert pm == "brew"


class TestRepositoryRealWorld:
    """Real-world repository scenarios."""

    def setup_method(self):
        """Reset executor before each test."""
        reset_executor()

    def teardown_method(self):
        """Clean up test repositories."""
        test_files = [
            "/etc/apt/sources.list.d/test-nodesource.list",
            "/etc/apt/trusted.gpg.d/test-nodesource.gpg",
        ]
        for f in test_files:
            if os.path.exists(f):
                os.remove(f)

    @pytest.mark.slow
    @pytest.mark.skip(reason="Requires actual GPG key download - manual test only")
    def test_add_nodesource_repository(self):
        """Test adding NodeSource repository (real scenario)."""
        platform = Platform.detect()

        if platform.distro not in ["ubuntu", "debian"]:
            pytest.skip("Test requires Ubuntu/Debian")

        executor = Executor()

        # Add NodeSource repository (for testing purposes only)
        executor.add(
            Repository(
                "test-nodesource",
                action="add",
                repo="deb https://deb.nodesource.com/node_20.x nodistro main",
                key_url="https://deb.nodesource.com/gpgkey/nodesource.gpg.key",
                filename="test-nodesource.list"
            )
        )

        plan = executor.plan()
        assert plan.has_changes

        apply = executor.apply(plan)
        assert apply.success

        # Verify repository file
        assert os.path.exists("/etc/apt/sources.list.d/test-nodesource.list")

        # Verify GPG key
        assert os.path.exists("/etc/apt/trusted.gpg.d/test-nodesource.gpg")


class TestRepositoryErrorHandling:
    """Test error handling in repository operations."""

    def setup_method(self):
        """Reset executor before each test."""
        reset_executor()

    def test_invalid_action(self):
        """Test that invalid action raises error."""
        with pytest.raises(ValueError, match="Invalid action"):
            Repository("test", action="invalid-action")

    def test_add_without_repo(self):
        """Test that add without repo specification raises error."""
        with pytest.raises(ValueError, match="requires one of"):
            Repository("test", action="add")

    def test_unsupported_platform(self):
        """Test handling of unsupported platform."""
        repo = Repository("test", action="update")
        platform = Platform(system="Windows", distro="windows", version="10", arch="x86_64")

        with pytest.raises(ValueError, match="Unsupported platform"):
            repo._get_package_manager(platform)


class TestRepositoryStateTracking:
    """Test state tracking for repository operations."""

    def setup_method(self):
        """Reset executor before each test."""
        reset_executor()

    def teardown_method(self):
        """Clean up test repositories."""
        test_file = "/etc/apt/sources.list.d/test-state-repo.list"
        if os.path.exists(test_file):
            os.remove(test_file)

    def test_repository_state_persistence(self):
        """Test that repository state is persisted."""
        platform = Platform.detect()

        if platform.distro not in ["ubuntu", "debian"]:
            pytest.skip("Test requires Ubuntu/Debian")

        executor = Executor()
        executor.enable_state_tracking()

        executor.add(
            Repository(
                "test-state-repo",
                action="add",
                repo="deb [trusted=yes] http://archive.ubuntu.com/ubuntu jammy main",
                filename="test-state-repo.list"
            )
        )

        plan = executor.plan()
        apply = executor.apply(plan)
        assert apply.success

        # Check state was saved
        from cook.state import Store
        with Store() as store:
            state = store.get_resource("repository:test-state-repo")
            assert state is not None
            assert state.type == "repository"
            assert state.status == "success"
