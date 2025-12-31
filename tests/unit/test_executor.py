"""
Unit tests for Cook executor.

Tests the executor's resource management and plan/apply workflow.
"""

import pytest
import tempfile
import os

from cook.core import Platform, Action, Resource
from cook.core.executor import Executor, reset_executor
from cook.resources.file import File


# Simple mock resource for testing that doesn't auto-register
class MockResource(Resource):
    """Mock resource for testing."""

    def __init__(self, name: str, value: str = ""):
        super().__init__(name)
        self.value = value

    def resource_type(self) -> str:
        return "mock"

    def check(self, platform: Platform):
        return {"exists": False}

    def desired_state(self):
        return {"exists": True, "value": self.value}

    def apply(self, plan, platform):
        pass


class TestExecutorResourceManagement:
    """Unit tests for executor resource management."""

    def test_add_single_resource(self):
        """Test adding a single resource to executor."""
        executor = Executor()
        resource = MockResource("test1", "value1")
        executor.add(resource)

        assert len(executor.resources) == 1
        assert executor.get(resource.id) == resource

    def test_add_multiple_resources(self):
        """Test adding multiple different resources."""
        executor = Executor()

        res1 = MockResource("res1", "value1")
        res2 = MockResource("res2", "value2")
        res3 = MockResource("res3", "value3")

        executor.add(res1)
        executor.add(res2)
        executor.add(res3)

        assert len(executor.resources) == 3
        assert executor.get(res1.id) == res1
        assert executor.get(res2.id) == res2
        assert executor.get(res3.id) == res3

    def test_resource_replacement_last_wins(self):
        """
        Test that redefining a resource replaces the previous definition.

        This is the key behavior for multi-phase configurations where
        the same resource needs to be updated at different phases.
        """
        executor = Executor()

        # First definition - HTTP config
        res1 = MockResource("config", "http config")
        executor.add(res1)

        assert len(executor.resources) == 1
        assert executor.get("mock:config").value == "http config"

        # Second definition - HTTPS config (should replace first)
        res2 = MockResource("config", "https config")
        executor.add(res2)

        # Should still have only one resource (not two)
        assert len(executor.resources) == 1

        # The resource should be the new one
        assert executor.get("mock:config") == res2
        assert executor.get("mock:config").value == "https config"

        # Should NOT be the old one
        assert executor.get("mock:config") != res1

    def test_resource_replacement_maintains_order(self):
        """
        Test that replacing a resource maintains its position in execution order.

        This is important to ensure that dependencies and execution order
        are preserved even when resources are redefined.
        """
        executor = Executor()

        res1 = MockResource("res1", "first")
        res2 = MockResource("res2", "second")
        res3 = MockResource("res3", "third")

        executor.add(res1)
        executor.add(res2)
        executor.add(res3)

        # Replace the middle resource
        res2_updated = MockResource("res2", "second updated")
        executor.add(res2_updated)

        # Should still have 3 resources
        assert len(executor.resources) == 3

        # Check order is preserved (res2 should still be in the middle)
        assert executor.resources[0].id == "mock:res1"
        assert executor.resources[1].id == "mock:res2"
        assert executor.resources[2].id == "mock:res3"

        # But the value should be updated
        assert executor.resources[1].value == "second updated"

    def test_multiple_redefinitions(self):
        """Test that a resource can be redefined multiple times."""
        executor = Executor()

        # Define and redefine multiple times
        for i in range(5):
            res = MockResource("multi", f"version {i}")
            executor.add(res)

        # Should only have one resource
        assert len(executor.resources) == 1

        # Should have the last version
        assert executor.get("mock:multi").value == "version 4"


class TestExecutorPlanApply:
    """Unit tests for executor plan/apply workflow."""

    def test_plan_no_changes(self):
        """Test planning when no changes are needed."""
        executor = Executor()
        platform = Platform.detect()

        # Create a temp file with specific content
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("existing content")
            test_file = f.name

        try:
            # Define resource matching existing state
            file_res = File(test_file, content="existing content", mode=0o644)
            os.chmod(test_file, 0o644)
            executor.add(file_res)

            # Plan should show no changes
            plan_result = executor.plan()
            assert not plan_result.has_changes
            assert plan_result.change_count == 0

        finally:
            os.unlink(test_file)

    def test_plan_with_changes(self):
        """Test planning when changes are needed."""
        executor = Executor()
        platform = Platform.detect()

        test_file = "/tmp/test-executor-plan.txt"
        if os.path.exists(test_file):
            os.unlink(test_file)

        try:
            # Define resource for non-existent file
            file_res = File(test_file, content="new content", mode=0o644)
            executor.add(file_res)

            # Plan should show changes (file needs to be created)
            plan_result = executor.plan()
            assert plan_result.has_changes
            assert plan_result.change_count == 1

            # Verify the plan action
            plan = plan_result.plans.get(file_res.id)
            assert plan.action == Action.CREATE

        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)

    def test_plan_replaced_resource(self):
        """
        Test that planning works correctly with replaced resources.

        This ensures that when a resource is redefined, the plan
        is generated based on the final (latest) definition.
        """
        executor = Executor()
        platform = Platform.detect()

        test_file = "/tmp/test-executor-replaced.txt"
        if os.path.exists(test_file):
            os.unlink(test_file)

        try:
            # First definition
            file1 = File(test_file, content="first version", mode=0o644)
            executor.add(file1)

            # Second definition (replaces first)
            file2 = File(test_file, content="second version", mode=0o600)
            executor.add(file2)

            # Plan should be based on the SECOND definition
            plan_result = executor.plan()
            plan = plan_result.plans.get(f"file:{test_file}")

            assert plan.action == Action.CREATE

            # Find content change
            content_change = next((c for c in plan.changes if c.field == "content"), None)
            assert content_change is not None
            assert content_change.to_value == "second version"

        finally:
            if os.path.exists(test_file):
                os.unlink(test_file)
