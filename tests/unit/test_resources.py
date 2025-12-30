"""
Unit tests for Cook resources.

Tests individual resource behavior in isolation.
"""

import os
import tempfile
import pytest

from cook.core import Platform, Action
from cook.resources.file import File
from cook.resources.service import Service


class TestFileResource:
    """Unit tests for File resource."""

    def test_file_check_missing(self):
        """Test checking a file that doesn't exist."""
        platform = Platform.detect()
        test_file = "/tmp/test-file-does-not-exist.txt"

        if os.path.exists(test_file):
            os.unlink(test_file)

        file_res = File(test_file, content="test", mode=0o644)
        state = file_res.check(platform)

        assert state["exists"] is False

    def test_file_check_existing(self):
        """Test checking a file that exists."""
        platform = Platform.detect()

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("existing content")
            test_file = f.name

        try:
            file_res = File(test_file, content="existing content", mode=0o644)
            state = file_res.check(platform)

            assert state["exists"] is True
            assert state["type"] == "file"

        finally:
            os.unlink(test_file)

    def test_file_plan_create(self):
        """Test planning file creation."""
        platform = Platform.detect()
        test_file = "/tmp/test-plan-create.txt"

        if os.path.exists(test_file):
            os.unlink(test_file)

        try:
            file_res = File(test_file, content="new content", mode=0o644)
            plan = file_res.plan(platform)

            assert plan.action == Action.CREATE
            assert plan.has_changes()
            assert any(c.field == "type" for c in plan.changes)

        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    def test_file_plan_update(self):
        """Test planning file update."""
        platform = Platform.detect()

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("old content")
            test_file = f.name

        try:
            file_res = File(test_file, content="new content", mode=0o644)
            plan = file_res.plan(platform)

            assert plan.action == Action.UPDATE
            assert plan.has_changes()
            assert any(c.field == "content" for c in plan.changes)

        finally:
            os.unlink(test_file)

    def test_directory_resource(self):
        """Test directory creation."""
        platform = Platform.detect()
        test_dir = tempfile.mkdtemp()
        os.rmdir(test_dir)  # Remove so we can test creation

        try:
            dir_res = File(test_dir, ensure="directory", mode=0o755)
            plan = dir_res.plan(platform)

            assert plan.action == Action.CREATE
            assert plan.has_changes()

            # Apply
            dir_res.apply(plan, platform)
            assert os.path.isdir(test_dir)

        finally:
            if os.path.exists(test_dir):
                os.rmdir(test_dir)

    def test_file_idempotency(self):
        """Test that file operations are idempotent."""
        platform = Platform.detect()

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("content")
            test_file = f.name

        # Set the correct mode on the temp file
        os.chmod(test_file, 0o644)

        try:
            # First check - file matches
            file_res = File(test_file, content="content", mode=0o644)
            plan = file_res.plan(platform)

            # Should have no changes (idempotent)
            assert not plan.has_changes()

        finally:
            os.unlink(test_file)


class TestPlatformDetection:
    """Unit tests for platform detection."""

    def test_platform_detect(self):
        """Test platform detection."""
        platform = Platform.detect()

        assert platform.system.lower() in ["darwin", "linux", "windows"]
        assert platform.arch in ["x86_64", "aarch64", "arm64", "i686"]

    def test_platform_distro_detection(self):
        """Test Linux distribution detection."""
        platform = Platform.detect()

        if platform.system == "linux":
            assert platform.distro is not None
            assert platform.distro in ["ubuntu", "debian", "fedora", "arch", "centos", "rhel", "alpine"]


class TestRecordingParser:
    """Unit tests for recording mode parser."""

    def test_parse_apt_install(self):
        """Test parsing apt install commands."""
        from cook.record.parser import CommandParser

        parser = CommandParser()
        result = parser.parse("apt-get install -y nginx")

        assert result is not None
        assert result.type == "package"
        assert result.data["name"] == "nginx"

    def test_parse_apt_multiple_packages(self):
        """Test parsing apt install with multiple packages."""
        from cook.record.parser import CommandParser

        parser = CommandParser()
        result = parser.parse("apt install nginx mysql-server postgresql")

        assert result is not None
        assert result.type == "package"
        assert result.data["packages"] == ["nginx", "mysql-server", "postgresql"]

    def test_parse_systemctl(self):
        """Test parsing systemctl commands."""
        from cook.record.parser import CommandParser

        parser = CommandParser()

        # Test enable
        result = parser.parse("systemctl enable nginx")
        assert result.type == "service"
        assert result.data["name"] == "nginx"
        assert result.data["enabled"] is True

        # Test start
        result = parser.parse("systemctl start nginx")
        assert result.data["running"] is True

    def test_parse_mkdir(self):
        """Test parsing mkdir commands."""
        from cook.record.parser import CommandParser

        parser = CommandParser()
        result = parser.parse("mkdir -p /var/www/html")

        assert result.type == "file"
        assert result.data["path"] == "/var/www/html"
        assert result.data["ensure"] == "directory"

    def test_parse_chmod(self):
        """Test parsing chmod commands."""
        from cook.record.parser import CommandParser

        parser = CommandParser()
        result = parser.parse("chmod 755 /var/www")

        assert result.type == "file"
        assert result.data["path"] == "/var/www"
        assert result.data["mode"] == 0o755

    def test_parse_chown(self):
        """Test parsing chown commands."""
        from cook.record.parser import CommandParser

        parser = CommandParser()
        result = parser.parse("chown www-data:www-data /var/www")

        assert result.type == "file"
        assert result.data["path"] == "/var/www"
        assert result.data["owner"] == "www-data"
        assert result.data["group"] == "www-data"

    def test_parse_git_clone(self):
        """Test parsing git clone commands."""
        from cook.record.parser import CommandParser

        parser = CommandParser()
        result = parser.parse("git clone https://github.com/user/repo.git /opt/repo")

        assert result.type == "exec"
        assert result.data["creates"] == "/opt/repo"

    def test_ignore_comments(self):
        """Test that comments are ignored."""
        from cook.record.parser import CommandParser

        parser = CommandParser()
        result = parser.parse("# This is a comment")

        assert result is None


class TestCodeGenerator:
    """Unit tests for code generator."""

    def test_generate_package(self):
        """Test generating package resource code."""
        from cook.record.parser import ParsedResource
        from cook.record.generator import CodeGenerator

        resources = [
            ParsedResource(
                type="package",
                data={"name": "nginx", "packages": None},
                command="apt install nginx"
            )
        ]

        generator = CodeGenerator()
        code = generator.generate(resources)

        assert "from cook import" in code
        assert "Package" in code
        assert 'Package("nginx")' in code

    def test_generate_file(self):
        """Test generating file resource code."""
        from cook.record.parser import ParsedResource
        from cook.record.generator import CodeGenerator

        resources = [
            ParsedResource(
                type="file",
                data={"path": "/etc/nginx/nginx.conf", "mode": 0o644},
                command="chmod 644 /etc/nginx/nginx.conf"
            )
        ]

        generator = CodeGenerator()
        code = generator.generate(resources)

        assert "File" in code
        assert "/etc/nginx/nginx.conf" in code
        assert "0o644" in code

    def test_generate_service(self):
        """Test generating service resource code."""
        from cook.record.parser import ParsedResource
        from cook.record.generator import CodeGenerator

        resources = [
            ParsedResource(
                type="service",
                data={"name": "nginx", "running": True, "enabled": True},
                command="systemctl enable nginx"
            )
        ]

        generator = CodeGenerator()
        code = generator.generate(resources)

        assert "Service" in code
        assert 'Service("nginx"' in code
        assert "running=True" in code
        assert "enabled=True" in code
