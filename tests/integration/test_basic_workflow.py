"""
Integration tests for basic Cook workflows.

Tests the full plan/apply cycle with real resources.
"""

import os
import tempfile
import pytest
from pathlib import Path

from cook.core.executor import Executor, reset_executor
from cook.core.resource import Platform
from cook.resources.file import File
from cook.resources.pkg import Package


class TestBasicWorkflow:
    """Test basic plan/apply workflows."""

    def setup_method(self):
        """Reset executor before each test."""
        reset_executor()

    def test_file_create_workflow(self):
        """Test creating a file through plan/apply."""
        executor = Executor()

        # Create temp file path
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_file = f.name
        os.unlink(test_file)  # Delete so we can test creation

        try:
            # Add file resource
            file_resource = File(test_file, content="test content\n", mode=0o644)
            executor.add(file_resource)

            # Plan
            plan_result = executor.plan()
            assert plan_result.has_changes
            assert plan_result.change_count == 1

            # Apply
            apply_result = executor.apply(plan_result)
            assert apply_result.success
            assert len(apply_result.changed_resources) == 1

            # Verify file exists
            assert os.path.exists(test_file)
            with open(test_file) as f:
                assert f.read() == "test content\n"

            # Test idempotency
            reset_executor()
            executor = Executor()
            executor.add(File(test_file, content="test content\n", mode=0o644))

            plan_result = executor.plan()
            assert not plan_result.has_changes

        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.unlink(test_file)

    def test_directory_create_workflow(self):
        """Test creating a directory through plan/apply."""
        executor = Executor()

        # Create temp directory path
        test_dir = tempfile.mkdtemp()
        os.rmdir(test_dir)  # Delete so we can test creation

        try:
            # Add directory resource
            dir_resource = File(test_dir, ensure="directory", mode=0o755)
            executor.add(dir_resource)

            # Plan
            plan_result = executor.plan()
            assert plan_result.has_changes

            # Apply
            apply_result = executor.apply(plan_result)
            assert apply_result.success

            # Verify directory exists
            assert os.path.isdir(test_dir)

        finally:
            # Cleanup
            if os.path.exists(test_dir):
                os.rmdir(test_dir)

    def test_multiple_resources(self):
        """Test managing multiple resources."""
        executor = Executor()

        test_dir = tempfile.mkdtemp()
        test_file = os.path.join(test_dir, "test.txt")

        try:
            # Add multiple resources
            executor.add(File(test_dir, ensure="directory", mode=0o755))
            executor.add(File(test_file, content="multi-resource test\n", mode=0o644))

            # Plan
            plan_result = executor.plan()
            assert plan_result.change_count == 2

            # Apply
            apply_result = executor.apply(plan_result)
            assert apply_result.success
            assert len(apply_result.changed_resources) == 2

            # Verify both exist
            assert os.path.isdir(test_dir)
            assert os.path.exists(test_file)

        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.unlink(test_file)
            if os.path.exists(test_dir):
                os.rmdir(test_dir)


class TestStateIntegration:
    """Test state persistence integration."""

    def setup_method(self):
        """Reset executor before each test."""
        reset_executor()

    def test_state_tracking(self):
        """Test that state is tracked after apply."""
        executor = Executor()
        executor.enable_state_tracking()

        test_file = tempfile.mktemp()

        try:
            # Create resource
            executor.add(File(test_file, content="state test\n", mode=0o644))

            # Apply
            plan_result = executor.plan()
            apply_result = executor.apply(plan_result)

            assert apply_result.success

            # Check state was saved
            from cook.state import Store
            with Store() as store:
                state = store.get_resource(f"file:{test_file}")
                assert state is not None
                assert state.type == "file"
                assert state.status == "success"

        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.unlink(test_file)


class TestRecordingIntegration:
    """Test recording mode integration."""

    def test_command_parser(self):
        """Test parsing shell commands."""
        from cook.record.parser import CommandParser

        parser = CommandParser()

        # Test apt install
        result = parser.parse("apt install nginx")
        assert result is not None
        assert result.type == "package"
        assert result.data["name"] == "nginx"

        # Test systemctl
        result = parser.parse("systemctl enable nginx")
        assert result is not None
        assert result.type == "service"
        assert result.data["name"] == "nginx"
        assert result.data["enabled"] is True

        # Test mkdir
        result = parser.parse("mkdir -p /var/www")
        assert result is not None
        assert result.type == "file"
        assert result.data["path"] == "/var/www"
        assert result.data["ensure"] == "directory"

    def test_code_generator(self):
        """Test generating code from parsed resources."""
        from cook.record.parser import CommandParser, ParsedResource
        from cook.record.generator import CodeGenerator

        resources = [
            ParsedResource(
                type="package",
                data={"name": "nginx", "packages": None},
                command="apt install nginx"
            ),
            ParsedResource(
                type="file",
                data={"path": "/var/www", "ensure": "directory", "mode": 0o755},
                command="mkdir -p /var/www"
            ),
        ]

        generator = CodeGenerator()
        code = generator.generate(resources)

        # Verify generated code
        assert "from cook import" in code
        assert "Package" in code
        assert "File" in code
        assert 'Package("nginx")' in code
        assert '"/var/www"' in code
