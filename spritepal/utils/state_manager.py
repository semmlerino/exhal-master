"""
Lightweight state management for temporary UI state.

This module provides in-memory state management for temporary data that doesn't
need disk persistence. Perfect for dialog positions, widget states, and other
runtime state that should not be saved between application sessions.
"""
from __future__ import annotations

import pickle
import sys
import threading
import time
import uuid
from collections import OrderedDict
from typing import Any


class StateEntry:
    """
    Wrapper for stored state values with metadata.

    Tracks creation time, access patterns, and optional TTL for automatic expiry.
    """

    def __init__(self, value: Any, ttl_seconds: float | None = None):
        """
        Initialize a state entry.

        Args:
            value: The value to store
            ttl_seconds: Optional time-to-live in seconds
        """
        self.value = value
        self.created_at = time.time()
        self.accessed_at = time.time()
        self.ttl_seconds = ttl_seconds
        self.access_count = 0

        # Track size for memory management
        try:
            # Use pickle to get accurate size for complex objects
            self.size_bytes = len(pickle.dumps(value))
        except (TypeError, pickle.PicklingError):
            # Fall back to sys.getsizeof for unpickleable objects
            self.size_bytes = sys.getsizeof(value)

    def is_expired(self) -> bool:
        """
        Check if this entry has expired based on TTL.

        Returns:
            True if expired, False otherwise
        """
        if self.ttl_seconds is None:
            return False
        return time.time() - self.created_at > self.ttl_seconds

    def touch(self) -> None:
        """Update access time and increment counter."""
        self.accessed_at = time.time()
        self.access_count += 1

class StateSnapshot:
    """
    Immutable snapshot of state at a point in time.

    Used for save/restore points and undo functionality.
    """

    def __init__(self, states: dict[str, Any], namespace: str | None = None):
        """
        Create a state snapshot.

        Args:
            states: Dictionary of state values
            namespace: Optional namespace that was captured
        """
        self.id = str(uuid.uuid4())
        self.timestamp = time.time()
        self.namespace = namespace
        # Deep copy the states to ensure immutability
        try:
            self.states = pickle.loads(pickle.dumps(states))
        except (TypeError, pickle.PicklingError):
            # Fall back to shallow copy for unpickleable objects
            self.states = states.copy()

    def get_age_seconds(self) -> float:
        """
        Get the age of this snapshot in seconds.

        Returns:
            Age in seconds
        """
        return time.time() - self.timestamp

class StateManager:
    """
    Thread-safe manager for temporary application state.

    Provides hierarchical key management, TTL support, memory limits,
    and snapshot/restore functionality for temporary UI state.
    """

    def __init__(self, max_size_mb: float = 10.0):
        """
        Initialize the state manager.

        Args:
            max_size_mb: Maximum memory usage in megabytes
        """
        self._states: OrderedDict[str, StateEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._max_size_bytes = int(max_size_mb * 1024 * 1024)
        self._total_size_bytes = 0
        self._cleanup_counter = 0
        self._cleanup_interval = 100  # Cleanup every N operations

    def save_state(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        """
        Save a state value with optional TTL.

        Args:
            key: Hierarchical key (e.g., "dialog.position")
            value: Value to store (any pickleable type)
            ttl_seconds: Optional time-to-live in seconds
        """
        with self._lock:
            # Create new entry
            entry = StateEntry(value, ttl_seconds)

            # Remove old entry if exists
            if key in self._states:
                self._total_size_bytes -= self._states[key].size_bytes

            # Add new entry
            self._states[key] = entry
            self._total_size_bytes += entry.size_bytes

            # Move to end (most recently used)
            self._states.move_to_end(key)

            # Cleanup if needed
            self._maybe_cleanup()
            self._enforce_memory_limit()

    def restore_state(self, key: str, default: Any = None) -> Any:
        """
        Restore a state value.

        Args:
            key: State key
            default: Default value if key not found or expired

        Returns:
            Stored value or default
        """
        with self._lock:
            if key not in self._states:
                return default

            entry = self._states[key]

            # Check expiry
            if entry.is_expired():
                del self._states[key]
                self._total_size_bytes -= entry.size_bytes
                return default

            # Update access tracking
            entry.touch()
            self._states.move_to_end(key)

            return entry.value

    def has_state(self, key: str) -> bool:
        """
        Check if a state key exists and is not expired.

        Args:
            key: State key to check

        Returns:
            True if state exists and is valid
        """
        with self._lock:
            if key not in self._states:
                return False

            entry = self._states[key]
            if entry.is_expired():
                del self._states[key]
                self._total_size_bytes -= entry.size_bytes
                return False

            return True

    def clear_state(self, pattern: str | None = None) -> int:
        """
        Clear states matching a pattern.

        Args:
            pattern: Optional pattern (e.g., "dialog.*" for wildcard, None for all)

        Returns:
            Number of states cleared
        """
        with self._lock:
            if pattern is None:
                # Clear all
                count = len(self._states)
                self._states.clear()
                self._total_size_bytes = 0
                return count

            # Clear by pattern
            if pattern.endswith(".*"):
                # Wildcard pattern
                prefix = pattern[:-2]
                keys_to_remove = [k for k in self._states if k.startswith(prefix)]
            else:
                # Exact match
                keys_to_remove = [pattern] if pattern in self._states else []

            for key in keys_to_remove:
                entry = self._states[key]
                del self._states[key]
                self._total_size_bytes -= entry.size_bytes

            return len(keys_to_remove)

    def get_snapshot(self, namespace: str | None = None) -> StateSnapshot:
        """
        Create a snapshot of current state.

        Args:
            namespace: Optional namespace to snapshot (e.g., "dialog")

        Returns:
            Immutable state snapshot
        """
        with self._lock:
            if namespace is None:
                # Snapshot all non-expired states
                states = {}
                for key, entry in list(self._states.items()):
                    if not entry.is_expired():
                        states[key] = entry.value
                    else:
                        # Clean up expired while we're here
                        del self._states[key]
                        self._total_size_bytes -= entry.size_bytes
            else:
                # Snapshot namespace only
                states = {}
                prefix = namespace + "." if not namespace.endswith(".") else namespace
                for key, entry in self._states.items():
                    if key.startswith(prefix) and not entry.is_expired():
                        states[key] = entry.value

            return StateSnapshot(states, namespace)

    def apply_snapshot(self, snapshot: StateSnapshot, clear_existing: bool = True) -> None:
        """
        Restore state from a snapshot.

        Args:
            snapshot: Snapshot to restore
            clear_existing: Whether to clear existing states in the namespace
        """
        with self._lock:
            if clear_existing and snapshot.namespace:
                # Clear existing states in namespace
                self.clear_state(snapshot.namespace + ".*")

            # Apply snapshot states
            for key, value in snapshot.states.items():
                self.save_state(key, value)

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about current state.

        Returns:
            Dictionary with stats (memory usage, key count, etc.)
        """
        with self._lock:
            # Clean up expired entries first
            self._cleanup_expired()

            return {
                "total_keys": len(self._states),
                "memory_usage_bytes": self._total_size_bytes,
                "memory_usage_mb": self._total_size_bytes / (1024 * 1024),
                "memory_limit_mb": self._max_size_bytes / (1024 * 1024),
                "memory_usage_percent": (self._total_size_bytes / self._max_size_bytes * 100) if self._max_size_bytes > 0 else 0,
                "oldest_key": next(iter(self._states)) if self._states else None,
                "newest_key": next(reversed(self._states)) if self._states else None,
            }

    def get_keys(self, prefix: str | None = None) -> list[str]:
        """
        Get all keys, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter by

        Returns:
            List of keys
        """
        with self._lock:
            if prefix is None:
                return list(self._states.keys())
            return [k for k in self._states if k.startswith(prefix)]

    def _maybe_cleanup(self) -> None:
        """Periodically cleanup expired entries."""
        self._cleanup_counter += 1
        if self._cleanup_counter >= self._cleanup_interval:
            self._cleanup_expired()
            self._cleanup_counter = 0

    def _cleanup_expired(self) -> None:
        """Remove all expired entries."""
        expired_keys = []
        for key, entry in self._states.items():
            if entry.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            entry = self._states[key]
            del self._states[key]
            self._total_size_bytes -= entry.size_bytes

    def _enforce_memory_limit(self) -> None:
        """Enforce memory limit using LRU eviction."""
        while self._total_size_bytes > self._max_size_bytes and self._states:
            # Remove least recently used (first item)
            _key, entry = self._states.popitem(last=False)
            self._total_size_bytes -= entry.size_bytes

    def get_memory_usage(self) -> tuple[float, float]:
        """
        Get current memory usage.

        Returns:
            Tuple of (used_mb, limit_mb)
        """
        with self._lock:
            used_mb = self._total_size_bytes / (1024 * 1024)
            limit_mb = self._max_size_bytes / (1024 * 1024)
            return used_mb, limit_mb

# Singleton instance for convenient global access
_global_state_manager: StateManager | None = None
_global_lock = threading.Lock()

def get_state_manager() -> StateManager:
    """
    Get the global state manager instance.

    Returns:
        Global StateManager instance
    """
    global _global_state_manager
    if _global_state_manager is None:
        with _global_lock:
            if _global_state_manager is None:
                _global_state_manager = StateManager()
    return _global_state_manager
