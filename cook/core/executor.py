"""
Executor - manages resource planning and application.

The executor:
1. Collects resources from config
2. Generates execution plan
3. Applies changes
4. Tracks state (optional)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import time
import os
import socket
from datetime import datetime

from cook.core.resource import Resource, Plan, Action, Platform
from cook.transport import Transport, LocalTransport


@dataclass
class PlanResult:
    """
    Result of planning phase.

    Contains plans for all resources and summary statistics.
    """
    plans: Dict[str, Plan] = field(default_factory=dict)
    errors: List[Exception] = field(default_factory=list)

    @property
    def change_count(self) -> int:
        """Count of resources with changes."""
        return sum(1 for plan in self.plans.values() if plan.has_changes())

    @property
    def has_changes(self) -> bool:
        """Check if any resource has changes."""
        return self.change_count > 0

    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0


@dataclass
class ApplyResult:
    """
    Result of apply phase.

    Contains success/failure info and changed resource IDs.
    """
    changed_resources: List[str] = field(default_factory=list)
    errors: List[Exception] = field(default_factory=list)
    duration: float = 0.0

    @property
    def success(self) -> bool:
        """Check if apply succeeded without errors."""
        return len(self.errors) == 0


class Executor:
    """
    Resource executor implementing plan/apply workflow.

    Example:
        executor = Executor(platform)
        executor.add(File("/etc/nginx.conf", content="..."))
        executor.add(Service("nginx", running=True))

        # Plan
        plan_result = executor.plan()
        print(f"Will change {plan_result.change_count} resources")

        # Apply
        apply_result = executor.apply(plan_result)
        print(f"Changed {len(apply_result.changed_resources)} resources")
    """

    def __init__(
        self,
        platform: Optional[Platform] = None,
        config_file: Optional[str] = None,
        transport: Optional[Transport] = None,
    ):
        """
        Initialize executor.

        Args:
            platform: Platform info (auto-detected if None)
            config_file: Path to config file (for state tracking)
            transport: Transport for command execution (default: LocalTransport)
        """
        self.transport = transport or LocalTransport()
        self.platform = platform or Platform.detect(self.transport)
        self.resources: List[Resource] = []
        self._registry: Dict[str, Resource] = {}
        self.config_file = config_file
        self._enable_state = False

    def add(self, resource: Resource) -> Resource:
        """
        Add resource to executor.

        Args:
            resource: Resource instance

        Returns:
            The resource (for chaining/references)
        """
        if resource.id in self._registry:
            raise ValueError(f"Duplicate resource: {resource.id}")

        # Set transport on resource
        resource._transport = self.transport

        self.resources.append(resource)
        self._registry[resource.id] = resource
        return resource

    def get(self, resource_id: str) -> Optional[Resource]:
        """Get resource by ID."""
        return self._registry.get(resource_id)

    def enable_state_tracking(self) -> None:
        """Enable state persistence."""
        self._enable_state = True

    def plan(self) -> PlanResult:
        """
        Generate execution plan for all resources.

        Returns:
            PlanResult with plans and any errors
        """
        result = PlanResult()

        for resource in self.resources:
            try:
                plan = resource.plan(self.platform)
                result.plans[resource.id] = plan
            except Exception as e:
                result.errors.append(e)

        return result

    def apply(self, plan_result: PlanResult) -> ApplyResult:
        """
        Apply execution plan.

        Args:
            plan_result: Result from plan()

        Returns:
            ApplyResult with changed resources and errors
        """
        result = ApplyResult()
        start_time = time.time()

        # Phase 1: Apply all resource changes
        for resource in self.resources:
            plan = plan_result.plans.get(resource.id)
            if not plan or not plan.has_changes():
                continue

            try:
                resource.apply(plan, self.platform)
                result.changed_resources.append(resource.id)

                # Refresh actual state after apply
                resource._actual_state = resource.check(self.platform)
            except Exception as e:
                result.errors.append(e)
                # Continue with other resources even if one fails

        result.duration = time.time() - start_time

        # Phase 2: Service reload/restart triggers
        if result.changed_resources:
            self._trigger_service_reloads(result.changed_resources)

        # Phase 3: Save state (if enabled)
        if self._enable_state:
            self._save_state(plan_result, result)

        return result

    def _trigger_service_reloads(self, changed_resource_ids: List[str]) -> None:
        """
        Trigger service reloads/restarts based on changed resources.

        Args:
            changed_resource_ids: List of resource IDs that changed
        """
        # Import Service here to avoid circular import
        from cook.resources.service import Service

        for resource in self.resources:
            # Check if resource is a Service
            if not isinstance(resource, Service):
                continue

            # Check if service should restart (takes precedence over reload)
            if resource.should_restart(changed_resource_ids):
                print(f"  ↻ {resource.id} restarted")
                resource.restart(self.platform)
                continue

            # Check if service should reload
            if resource.should_reload(changed_resource_ids):
                print(f"  ⟳ {resource.id} reloaded")
                resource.reload(self.platform)

    def _save_state(self, plan_result: PlanResult, apply_result: ApplyResult) -> None:
        """
        Save resource state to database.

        Args:
            plan_result: Plan result
            apply_result: Apply result
        """
        try:
            from cook.state import Store, ResourceState, HistoryEntry
        except ImportError:
            # State persistence not available
            return

        with Store() as store:
            user = os.getenv("USER", "unknown")
            hostname = socket.gethostname()
            timestamp = datetime.now()

            for resource in self.resources:
                plan = plan_result.plans.get(resource.id)
                if not plan:
                    continue

                # Determine status
                if resource.id in apply_result.changed_resources:
                    status = "success"
                else:
                    status = "unchanged"

                # Save resource state
                state = ResourceState(
                    id=resource.id,
                    type=resource.resource_type(),
                    desired_state=resource._desired_state,
                    actual_state=resource._actual_state,
                    applied_at=timestamp,
                    applied_by=user,
                    hostname=hostname,
                    config_file=self.config_file or "unknown",
                    status=status,
                )
                store.save_resource(state)

                # Add history entry if changed
                if resource.id in apply_result.changed_resources:
                    changes = {c.field: {"from": c.from_value, "to": c.to_value}
                              for c in plan.changes}

                    entry = HistoryEntry(
                        timestamp=timestamp,
                        resource_id=resource.id,
                        action=plan.action.value,
                        user=user,
                        hostname=hostname,
                        success=resource.id in apply_result.changed_resources,
                        changes=changes,
                    )
                    store.add_history(entry)

    def clear(self) -> None:
        """Clear all resources."""
        self.resources.clear()
        self._registry.clear()


class Registry:
    """
    Global resource registry for use in config files.

    Provides a singleton pattern for resource collection.
    """

    _instance: Optional['Registry'] = None
    _executor: Optional[Executor] = None

    @classmethod
    def get_instance(cls) -> 'Registry':
        """Get singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset registry (useful for testing)."""
        cls._instance = None
        cls._executor = None

    def __init__(self):
        """Initialize registry with executor."""
        if Registry._executor is None:
            Registry._executor = Executor()

    @property
    def executor(self) -> Executor:
        """Get executor instance."""
        return Registry._executor

    def add(self, resource: Resource) -> Resource:
        """Add resource to executor."""
        return self.executor.add(resource)


# Global registry instance
_registry = Registry.get_instance()


def get_executor() -> Executor:
    """Get global executor instance."""
    return _registry.executor


def reset_executor() -> None:
    """Reset global executor (useful for testing)."""
    Registry.reset()
    global _registry
    _registry = Registry.get_instance()
