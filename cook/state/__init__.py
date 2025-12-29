"""
State persistence for Cook.

Tracks resource state, changes, and history using SQLite.
"""

from cook.state.store import Store, ResourceState, HistoryEntry

__all__ = ["Store", "ResourceState", "HistoryEntry"]
