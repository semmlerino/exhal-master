"""
Protocol definitions for SpritePal core components.

These protocols define the interfaces that components depend on,
enabling dependency injection and better testability.
"""
from __future__ import annotations

from .manager_protocols import (
    ExtractionManagerProtocol,
    InjectionManagerProtocol,
    MainWindowProtocol,
    SessionManagerProtocol,
)

__all__ = [
    "ExtractionManagerProtocol",
    "InjectionManagerProtocol",
    "MainWindowProtocol",
    "SessionManagerProtocol",
]
