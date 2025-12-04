#!/usr/bin/env python3
from __future__ import annotations

"""Test QSignalSpy API to find correct access method."""

from PySide6.QtCore import QObject, Signal
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication([])

class TestObject(QObject):
    test_signal = Signal(int, str)

obj = TestObject()
spy = QSignalSpy(obj.test_signal)

# Emit a signal
obj.test_signal.emit(42, "test")

# Test different access methods
print(f"count(): {spy.count()}")
print(f"size(): {spy.size()}")

# Try different access methods
try:
    print(f"spy[0]: {spy[0]}")
except Exception as e:
    print(f"spy[0] failed: {e}")

try:
    print(f"spy.at(0): {spy.at(0)}")
except Exception as e:
    print(f"spy.at(0) failed: {e}")

try:
    print(f"list(spy): {list(spy)}")
except Exception as e:
    print(f"list(spy) failed: {e}")

# Check if there's a way to get the data
print(f"dir(spy): {[m for m in dir(spy) if not m.startswith('_')]}")

# Try getting signal data
if spy.count() > 0:
    try:
        # PySide6 might use a different approach
        for i in range(spy.count()):
            print(f"Signal {i}: {spy.at(i)}")
    except Exception:
        pass
