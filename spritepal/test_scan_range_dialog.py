#!/usr/bin/env python3
from __future__ import annotations

"""Quick test to verify ScanRangeDialog defaults are correct."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from ui.dialogs.scan_range_dialog import ScanRangeDialog


def test_scan_range_dialog_defaults():
    """Test that ScanRangeDialog has correct default values."""
    QApplication.instance() or QApplication([])

    # Test with no ROM size (should use defaults)
    dialog = ScanRangeDialog(rom_size=0)
    assert dialog.start_offset == 0x40000, f"Expected start 0x40000, got 0x{dialog.start_offset:X}"
    assert dialog.end_offset == 0x200000, f"Expected end 0x200000, got 0x{dialog.end_offset:X}"
    print("✅ No ROM size: defaults correct")

    # Test with 2MB ROM
    dialog = ScanRangeDialog(rom_size=0x200000)
    assert dialog.start_offset == 0x40000, f"Expected start 0x40000, got 0x{dialog.start_offset:X}"
    assert dialog.end_offset == 0x200000, f"Expected end 0x200000, got 0x{dialog.end_offset:X}"
    print("✅ 2MB ROM: defaults correct")

    # Test with 8MB ROM (should cap at 4MB)
    dialog = ScanRangeDialog(rom_size=0x800000)
    assert dialog.start_offset == 0x40000, f"Expected start 0x40000, got 0x{dialog.start_offset:X}"
    assert dialog.end_offset == 0x400000, f"Expected end 0x400000, got 0x{dialog.end_offset:X}"
    print("✅ 8MB ROM: correctly capped at 4MB")

    # Test get_range method
    start, end = dialog.get_range()
    assert start == 0x40000, f"get_range() start incorrect: 0x{start:X}"
    assert end == 0x400000, f"get_range() end incorrect: 0x{end:X}"
    print("✅ get_range() returns correct values")

    print("\n✅ All ScanRangeDialog tests passed!")
    print(f"Default range is now: 0x{dialog.start_offset:X} - 0x{dialog.end_offset:X}")
    print("This matches the scan_worker.py defaults for full ROM scanning")

if __name__ == "__main__":
    test_scan_range_dialog_defaults()
