# Fixed singleton.py
from __future__ import annotations

"""
Thread-safe singleton implementation for SpritePal.

This module provides a reusable singleton pattern that eliminates the need
for global variables and the PLW0603 error.
"""

import threading
from typing import Any, ClassVar, TypeVar

T = TypeVar("T")

class ThreadSafeSingleton(type):
    """
    Thread-safe singleton metaclass.

    Usage:
        class MyClass(metaclass=ThreadSafeSingleton):
            def __init__(self):
                # initialization code
                pass

    This ensures only one instance exists and handles thread safety automatically.
    """
    _instances: ClassVar[dict[type[Any], Any]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        # Fast path - check without lock
        if cls in cls._instances:
            return cls._instances[cls]

        # Slow path - create with lock
        with cls._lock:
            # Double-check pattern
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance

        return cls._instances[cls]

    @classmethod
    def clear_instance(cls, target_cls: type[T]) -> None:
        """Clear a specific singleton instance (useful for testing)."""
        with cls._lock:
            if target_cls in cls._instances:
                del cls._instances[target_cls]

    @classmethod
    def clear_all_instances(cls) -> None:
        """Clear all singleton instances (useful for testing)."""
        with cls._lock:
            cls._instances.clear()

class SimpleSingleton(type):
    """
    Simple singleton metaclass without thread safety.

    Use this for cases where thread safety is not required.
    """
    _instances: ClassVar[dict[type[Any], Any]] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

    @classmethod
    def clear_instance(cls, target_cls: type[T]) -> None:
        """Clear a specific singleton instance (useful for testing)."""
        if target_cls in cls._instances:
            del cls._instances[target_cls]
