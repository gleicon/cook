"""
State store using SQLite.

Tracks:
- Resource state (desired vs actual)
- Change history
- Who/when/what changed
"""

import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ResourceState:
    """Represents the state of a managed resource."""
    id: str
    type: str
    desired_state: Dict[str, Any]
    actual_state: Dict[str, Any]
    applied_at: datetime
    applied_by: str
    hostname: str
    config_file: str
    status: str  # "success", "failed", "drift"


@dataclass
class HistoryEntry:
    """Represents a single change in resource history."""
    timestamp: datetime
    resource_id: str
    action: str
    user: str
    hostname: str
    success: bool
    changes: Dict[str, Any]
    error: Optional[str] = None


class Store:
    """
    SQLite-based state store for Cook.

    Stores:
    - Resource state (resources table)
    - Change history (history table)

    Example:
        store = Store()
        store.save_resource(resource_state)
        resources = store.list_resources()
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize state store.

        Args:
            db_path: Path to SQLite database (default: ~/.cook/state.db)
        """
        if db_path is None:
            db_path = self._default_path()

        self.db_path = db_path
        self._ensure_db_dir()
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    @staticmethod
    def _default_path() -> str:
        """Get default state file path."""
        home = Path.home()
        return str(home / ".cook" / "state.db")

    def _ensure_db_dir(self) -> None:
        """Ensure state directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _init_schema(self) -> None:
        """Initialize database schema."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS resources (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                desired_state TEXT NOT NULL,
                actual_state TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                applied_by TEXT NOT NULL,
                hostname TEXT NOT NULL,
                config_file TEXT NOT NULL,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                action TEXT NOT NULL,
                user TEXT NOT NULL,
                hostname TEXT NOT NULL,
                success INTEGER NOT NULL,
                changes TEXT NOT NULL,
                error TEXT,
                FOREIGN KEY (resource_id) REFERENCES resources(id)
            );

            CREATE INDEX IF NOT EXISTS idx_history_resource
                ON history(resource_id);
            CREATE INDEX IF NOT EXISTS idx_history_timestamp
                ON history(timestamp DESC);
        """)
        self.conn.commit()

    def save_resource(self, state: ResourceState) -> None:
        """
        Save or update resource state.

        Args:
            state: ResourceState to save
        """
        self.conn.execute("""
            INSERT OR REPLACE INTO resources
            (id, type, desired_state, actual_state, applied_at, applied_by,
             hostname, config_file, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            state.id,
            state.type,
            json.dumps(state.desired_state),
            json.dumps(state.actual_state),
            state.applied_at.isoformat(),
            state.applied_by,
            state.hostname,
            state.config_file,
            state.status,
        ))
        self.conn.commit()

    def get_resource(self, resource_id: str) -> Optional[ResourceState]:
        """
        Get resource state by ID.

        Args:
            resource_id: Resource identifier

        Returns:
            ResourceState or None if not found
        """
        row = self.conn.execute(
            "SELECT * FROM resources WHERE id = ?",
            (resource_id,)
        ).fetchone()

        if not row:
            return None

        return ResourceState(
            id=row["id"],
            type=row["type"],
            desired_state=json.loads(row["desired_state"]),
            actual_state=json.loads(row["actual_state"]),
            applied_at=datetime.fromisoformat(row["applied_at"]),
            applied_by=row["applied_by"],
            hostname=row["hostname"],
            config_file=row["config_file"],
            status=row["status"],
        )

    def list_resources(self) -> List[ResourceState]:
        """
        List all managed resources.

        Returns:
            List of ResourceState objects
        """
        rows = self.conn.execute(
            "SELECT * FROM resources ORDER BY applied_at DESC"
        ).fetchall()

        return [
            ResourceState(
                id=row["id"],
                type=row["type"],
                desired_state=json.loads(row["desired_state"]),
                actual_state=json.loads(row["actual_state"]),
                applied_at=datetime.fromisoformat(row["applied_at"]),
                applied_by=row["applied_by"],
                hostname=row["hostname"],
                config_file=row["config_file"],
                status=row["status"],
            )
            for row in rows
        ]

    def add_history(self, entry: HistoryEntry) -> None:
        """
        Add history entry.

        Args:
            entry: HistoryEntry to record
        """
        self.conn.execute("""
            INSERT INTO history
            (timestamp, resource_id, action, user, hostname, success, changes, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.timestamp.isoformat(),
            entry.resource_id,
            entry.action,
            entry.user,
            entry.hostname,
            1 if entry.success else 0,
            json.dumps(entry.changes),
            entry.error,
        ))
        self.conn.commit()

    def get_history(self, resource_id: str, limit: int = 10) -> List[HistoryEntry]:
        """
        Get change history for a resource.

        Args:
            resource_id: Resource identifier
            limit: Maximum number of entries to return

        Returns:
            List of HistoryEntry objects
        """
        rows = self.conn.execute("""
            SELECT * FROM history
            WHERE resource_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (resource_id, limit)).fetchall()

        return [
            HistoryEntry(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                resource_id=row["resource_id"],
                action=row["action"],
                user=row["user"],
                hostname=row["hostname"],
                success=bool(row["success"]),
                changes=json.loads(row["changes"]),
                error=row["error"],
            )
            for row in rows
        ]

    def list_drifted(self) -> List[ResourceState]:
        """
        List resources that have drifted from desired state.

        Returns:
            List of ResourceState objects with status="drift"
        """
        rows = self.conn.execute(
            "SELECT * FROM resources WHERE status = 'drift' ORDER BY applied_at DESC"
        ).fetchall()

        return [
            ResourceState(
                id=row["id"],
                type=row["type"],
                desired_state=json.loads(row["desired_state"]),
                actual_state=json.loads(row["actual_state"]),
                applied_at=datetime.fromisoformat(row["applied_at"]),
                applied_by=row["applied_by"],
                hostname=row["hostname"],
                config_file=row["config_file"],
                status=row["status"],
            )
            for row in rows
        ]

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
