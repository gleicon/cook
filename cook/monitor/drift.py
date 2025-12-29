"""
Drift detection and monitoring.

Compares current system state against stored desired state.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

from cook.state import Store, ResourceState
from cook.core.resource import Platform
from cook.core.executor import get_executor


@dataclass
class DriftResult:
    """Result of drift detection."""
    resource_id: str
    drifted: bool
    differences: Dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=datetime.now)


class DriftDetector:
    """
    Detects configuration drift.

    Compares current system state with stored desired state.
    """

    def __init__(self, store: Optional[Store] = None):
        """Initialize drift detector."""
        self.store = store or Store()
        self.platform = Platform.detect()

    def check_resource(self, resource_id: str) -> Optional[DriftResult]:
        """
        Check single resource for drift.

        Args:
            resource_id: Resource identifier

        Returns:
            DriftResult or None if resource not found
        """
        state = self.store.get_resource(resource_id)
        if not state:
            return None

        # Load resource instance
        resource = self._load_resource(state)
        if not resource:
            return None

        # Check current state
        current_state = resource.check(self.platform)

        # Compare with stored state
        drifted, differences = self._compare_states(
            state.actual_state,
            current_state
        )

        # Update stored state if drifted
        if drifted:
            state.status = "drift"
            self.store.save_resource(state)

        return DriftResult(
            resource_id=resource_id,
            drifted=drifted,
            differences=differences,
        )

    def check_all(self) -> List[DriftResult]:
        """
        Check all managed resources for drift.

        Returns:
            List of DriftResult objects
        """
        results = []
        resources = self.store.list_resources()

        for state in resources:
            result = self.check_resource(state.id)
            if result:
                results.append(result)

        return results

    def _load_resource(self, state: ResourceState):
        """
        Load resource instance from stored state.

        Args:
            state: ResourceState from database

        Returns:
            Resource instance or None
        """
        # Import resource classes
        from cook.resources.file import File
        from cook.resources.pkg import Package
        from cook.resources.service import Service
        from cook.resources.exec import Exec

        resource_map = {
            "file": File,
            "pkg": Package,
            "svc": Service,
            "exec": Exec,
        }

        resource_class = resource_map.get(state.type)
        if not resource_class:
            return None

        # Create minimal resource instance for checking
        try:
            if state.type == "file":
                return resource_class(state.id.replace("file:", ""))
            elif state.type == "pkg":
                pkg_name = state.id.replace("pkg:", "")
                return resource_class(pkg_name)
            elif state.type == "svc":
                svc_name = state.id.replace("svc:", "")
                return resource_class(svc_name)
            elif state.type == "exec":
                return None  # Exec resources can't be checked for drift
        except Exception:
            return None

    def _compare_states(
        self,
        stored_state: Dict[str, Any],
        current_state: Dict[str, Any]
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Compare stored state with current state.

        Args:
            stored_state: State from database
            current_state: Current system state

        Returns:
            Tuple of (drifted: bool, differences: dict)
        """
        differences = {}
        drifted = False

        # Check each property
        for key, stored_value in stored_state.items():
            if key == "exists":
                continue

            current_value = current_state.get(key)

            # Skip None comparisons
            if stored_value is None and current_value is None:
                continue

            # Detect drift
            if stored_value != current_value:
                drifted = True
                differences[key] = {
                    "expected": stored_value,
                    "actual": current_value,
                }

        return drifted, differences

    def close(self):
        """Close store connection."""
        if self.store:
            self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
