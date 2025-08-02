"""
Protocol definitions for SpritePal core components.

These protocols define the interfaces that components depend on,
enabling dependency injection and better testability.
"""

from .manager_protocols import (
    ExtractionManagerProtocol,
    InjectionManagerProtocol,
    SessionManagerProtocol,
)

__all__ = [
    "ExtractionManagerProtocol",
    "InjectionManagerProtocol",
    "SessionManagerProtocol",
]
