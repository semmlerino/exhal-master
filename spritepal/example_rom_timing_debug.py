#!/usr/bin/env python3
"""
Example ROM Timing Debug Session

This script demonstrates how to use the ROM timing profilers to debug
discrepancies between Lua DMA monitoring and SpritePal static analysis.

Usage example for a typical debugging scenario:
1. Lua script detected sprite at ROM offset 0x50000
2. SpritePal Manual Offset Dialog shows different/no data at 0x50000
3. Use profilers to identify timing-related root cause
"""

import subprocess
import sys
import time
from pathlib import Path


def run_timing_debug_session(rom_path: str, problematic_offset: str):
    """
    Run complete timing debug session for ROM offset discrepancy.

    Args:
        rom_path: Path to ROM file
        problematic_offset: Offset where discrepancy occurs (hex format)
    """

    print("="*80)
    print("ROM TIMING DEBUG SESSION")
    print("="*80)
    print(f"ROM: {rom_path}")
    print(f"Problematic Offset: {problematic_offset}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Validate inputs
    if not Path(rom_path).exists():
        print(f"ERROR: ROM file not found: {rom_path}")
        return

    try:
        offset_int = int(problematic_offset, 16) if problematic_offset.startswith('0x') else int(problematic_offset)
        print(f"Parsed offset: 0x{offset_int:06X} ({offset_int} decimal)")
    except ValueError:
        print(f"ERROR: Invalid offset format: {problematic_offset}")
        return

    print("\n" + "="*80)
    print("PHASE 1: GENERAL ROM TIMING ANALYSIS")
    print("="*80)

    # Run general timing profiler
    print("Running comprehensive ROM timing profiler...")
    try:
        result = subprocess.run([
            sys.executable, "rom_offset_timing_profiler.py",
            rom_path, problematic_offset,
            "--output", f"timing_analysis_{offset_int:06X}.json"
        ], check=False, capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            print("✓ General timing analysis completed successfully")
            print("\nKey findings from general analysis:")
            print(result.stdout)
        else:
            print("✗ General timing analysis failed:")
            print(result.stderr)

    except subprocess.TimeoutExpired:
        print("✗ General timing analysis timed out (>2 minutes)")
    except Exception as e:
        print(f"✗ General timing analysis error: {e}")

    print("\n" + "="*80)
    print("PHASE 2: SPRITEPAL COMPONENT ANALYSIS")
    print("="*80)

    # Run SpritePal-specific analyzer
    print("Running SpritePal component timing analyzer...")
    try:
        result = subprocess.run([
            sys.executable, "spritepal_timing_analyzer.py",
            rom_path, problematic_offset,
            "--output", f"spritepal_analysis_{offset_int:06X}.json"
        ], check=False, capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            print("✓ SpritePal analysis completed successfully")
            print("\nKey findings from SpritePal analysis:")
            print(result.stdout)
        else:
            print("✗ SpritePal analysis failed:")
            print(result.stderr)

    except subprocess.TimeoutExpired:
        print("✗ SpritePal analysis timed out (>2 minutes)")
    except Exception as e:
        print(f"✗ SpritePal analysis error: {e}")

    print("\n" + "="*80)
    print("PHASE 3: MANUAL VERIFICATION")
    print("="*80)

    # Manual verification steps
    print("Manual verification steps to perform:")
    print()
    print("1. CLEAR SPRITEPAL CACHES:")
    print("   - Close SpritePal completely")
    print("   - Delete ~/.spritepal_cache directory")
    print("   - Delete any .spritepal_*_cache files")
    print("   - Restart SpritePal")
    print()
    print("2. COMPARE RAW DATA:")
    print(f"   - Use hex editor to view ROM at offset {problematic_offset}")
    print("   - Compare with Lua script DMA capture")
    print("   - Look for exact byte differences")
    print()
    print("3. TEST DIFFERENT ACCESS METHODS:")
    print("   - Try Manual Offset Dialog in SpritePal")
    print("   - Try ROM extraction using different methods")
    print("   - Note any data differences or timing issues")
    print()
    print("4. CHECK ADDRESS INTERPRETATION:")
    print(f"   - Verify {problematic_offset} is ROM file offset (not SNES address)")
    print("   - Convert SNES addresses using banking mode if necessary")
    print("   - LoROM: ((bank & 0x7F) << 15) + (addr - 0x8000)")
    print("   - HiROM: snes_addr & 0x3FFFFF")
    print()

    print("="*80)
    print("DEBUG SESSION COMPLETE")
    print("="*80)
    print()
    print("Generated files:")
    print(f"  - timing_analysis_{offset_int:06X}.json (general analysis)")
    print(f"  - spritepal_analysis_{offset_int:06X}.json (SpritePal specific)")
    print()
    print("Next steps:")
    print("  1. Review JSON output files for detailed metrics")
    print("  2. Follow manual verification steps above")
    print("  3. Implement targeted fixes based on root cause identified")
    print("  4. Re-run analysis to verify fix effectiveness")

def main():
    """Main entry point for debug session example."""

    # Example usage
    if len(sys.argv) != 3:
        print("ROM Timing Debug Session")
        print("="*40)
        print()
        print("This script runs a complete timing analysis to debug discrepancies")
        print("between Lua DMA monitoring and SpritePal static ROM analysis.")
        print()
        print("Usage:")
        print(f"  {sys.argv[0]} <rom_path> <offset>")
        print()
        print("Examples:")
        print(f"  {sys.argv[0]} kirby_dreamland_3.smc 0x50000")
        print(f"  {sys.argv[0]} super_metroid.sfc 0xC0000")
        print(f"  {sys.argv[0]} zelda_alttp.smc 0x80000")
        print()
        print("Prerequisites:")
        print("  - ROM file exists and is accessible")
        print("  - rom_offset_timing_profiler.py in same directory")
        print("  - spritepal_timing_analyzer.py in same directory")
        print("  - Python 3.8+ with required dependencies")
        print()
        sys.exit(1)

    rom_path = sys.argv[1]
    offset = sys.argv[2]

    run_timing_debug_session(rom_path, offset)

if __name__ == "__main__":
    main()
