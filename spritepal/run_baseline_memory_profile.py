#!/usr/bin/env python3
"""
Run Baseline Memory Profile for SpritePal

This script runs a quick baseline memory profile to establish concrete metrics
for measuring memory leak improvements. It focuses on the most critical components
and provides actionable measurements.

Usage:
    python run_baseline_memory_profile.py
    python run_baseline_memory_profile.py --rom path/to/rom.sfc
    python run_baseline_memory_profile.py --quick  # Fast baseline only
"""

import argparse
import os
import sys
from datetime import datetime

from memory_leak_profiler import MemoryLeakProfiler
from PyQt6.QtWidgets import QApplication


def print_header():
    """Print the script header."""
    print("SpritePal Memory Leak Baseline Profiler")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Purpose: Establish baseline metrics for leak detection")
    print()


def setup_environment():
    """Set up the testing environment."""
    # Ensure Qt application exists
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # Handle headless environments
    if os.environ.get("DISPLAY") is None and sys.platform.startswith("linux"):
        print("Headless environment detected, configuring for testing...")
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    return app


def run_quick_baseline(profiler: MemoryLeakProfiler) -> dict:
    """Run quick baseline measurements for immediate feedback."""
    print("Running Quick Baseline Measurements")
    print("-" * 35)

    # Establish baseline
    baseline = profiler.establish_baseline()

    results = {
        "baseline_memory_mb": baseline.process_memory_mb,
        "baseline_objects": sum(baseline.python_objects.values()),
        "baseline_qt_objects": sum(baseline.qt_objects.values()),
        "baseline_threads": baseline.thread_count,
    }

    print(f"Process Memory: {results['baseline_memory_mb']:.2f} MB")
    print(f"Python Objects: {results['baseline_objects']:,}")
    print(f"Qt Objects: {results['baseline_qt_objects']:,}")
    print(f"Active Threads: {results['baseline_threads']}")

    return results


def run_critical_component_tests(profiler: MemoryLeakProfiler) -> dict:
    """Run memory leak tests on the most critical components."""
    print("\nRunning Critical Component Tests")
    print("-" * 35)

    results = {}

    # Test 1: Manual Offset Dialog (highest priority)
    print("Testing Manual Offset Dialog (5 cycles)...")
    try:
        from ui.dialogs.manual_offset_unified_integrated import ManualOffsetDialog
        result = profiler.profile_dialog_lifecycle("ManualOffsetDialog", ManualOffsetDialog, cycles=5)
        results["manual_offset"] = {
            "memory_per_cycle_kb": result.memory_leaked_per_cycle_mb * 1000,
            "total_leaked_mb": result.memory_leaked_mb,
            "severity": result.leak_severity,
            "objects_leaked": sum(abs(v) for v in result.objects_leaked.values())
        }
        print(f"  Result: {result.leak_severity} ({result.memory_leaked_per_cycle_mb * 1000:.1f} KB per cycle)")
    except Exception as e:
        print(f"  FAILED: {e}")
        results["manual_offset"] = {"error": str(e)}

    # Test 2: Advanced Search Dialog
    print("Testing Advanced Search Dialog (5 cycles)...")
    try:
        from ui.dialogs.advanced_search_dialog import AdvancedSearchDialog
        result = profiler.profile_dialog_lifecycle("AdvancedSearchDialog", AdvancedSearchDialog, cycles=5)
        results["advanced_search"] = {
            "memory_per_cycle_kb": result.memory_leaked_per_cycle_mb * 1000,
            "total_leaked_mb": result.memory_leaked_mb,
            "severity": result.leak_severity,
            "objects_leaked": sum(abs(v) for v in result.objects_leaked.values())
        }
        print(f"  Result: {result.leak_severity} ({result.memory_leaked_per_cycle_mb * 1000:.1f} KB per cycle)")
    except Exception as e:
        print(f"  FAILED: {e}")
        results["advanced_search"] = {"error": str(e)}

    # Test 3: Preview Workers (critical for performance)
    print("Testing Preview Workers (10 operations)...")
    try:
        from ui.rom_extraction.workers.preview_worker import SpritePreviewWorker
        result = profiler.profile_worker_operations("PreviewWorker", lambda: SpritePreviewWorker(), operations=10)
        leaked_workers = result.leak_details.get("leaked_workers", 0)
        results["preview_workers"] = {
            "memory_per_operation_kb": result.memory_leaked_per_cycle_mb * 1000,
            "total_leaked_mb": result.memory_leaked_mb,
            "leaked_workers": leaked_workers,
            "severity": result.leak_severity
        }
        print(f"  Result: {result.leak_severity} ({result.memory_leaked_per_cycle_mb * 1000:.1f} KB per operation, "
              f"{leaked_workers} leaked workers)")
    except Exception as e:
        print(f"  FAILED: {e}")
        results["preview_workers"] = {"error": str(e)}

    return results


def run_extraction_test(profiler: MemoryLeakProfiler, rom_path: str) -> dict:
    """Run extraction operation memory test if ROM is available."""
    print(f"\nTesting Extraction Operations with ROM: {rom_path}")
    print("-" * 45)

    if not os.path.exists(rom_path):
        print(f"ROM file not found: {rom_path}")
        return {"error": "ROM file not found"}

    try:
        result = profiler.profile_extraction_operations(rom_path, operations=5)
        extraction_result = {
            "memory_per_operation_kb": result.memory_leaked_per_cycle_mb * 1000,
            "total_leaked_mb": result.memory_leaked_mb,
            "severity": result.leak_severity,
            "objects_leaked": sum(abs(v) for v in result.objects_leaked.values())
        }
        print(f"Result: {result.leak_severity} ({result.memory_leaked_per_cycle_mb * 1000:.1f} KB per operation)")
        return extraction_result
    except Exception as e:
        print(f"FAILED: {e}")
        return {"error": str(e)}


def generate_baseline_report(baseline_results: dict, component_results: dict,
                           extraction_results: dict | None = None) -> str:
    """Generate baseline report with concrete metrics."""
    report = []
    report.append("SpritePal Memory Leak Baseline Report")
    report.append("=" * 50)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

    # Baseline metrics
    report.append("BASELINE METRICS")
    report.append("-" * 20)
    report.append(f"Process Memory: {baseline_results['baseline_memory_mb']:.2f} MB")
    report.append(f"Python Objects: {baseline_results['baseline_objects']:,}")
    report.append(f"Qt Objects: {baseline_results['baseline_qt_objects']:,}")
    report.append(f"Active Threads: {baseline_results['baseline_threads']}")
    report.append("")

    # Critical component results
    report.append("CRITICAL COMPONENT LEAK MEASUREMENTS")
    report.append("-" * 40)

    total_issues = 0
    severe_issues = 0

    for component, result in component_results.items():
        if "error" in result:
            report.append(f"{component.upper()}: FAILED ({result['error']})")
            continue

        component_name = component.replace("_", " ").title()
        report.append(f"{component_name}:")

        if "memory_per_cycle_kb" in result:
            per_cycle = result["memory_per_cycle_kb"]
            report.append(f"  Memory per cycle: {per_cycle:.1f} KB")
        elif "memory_per_operation_kb" in result:
            per_op = result["memory_per_operation_kb"]
            report.append(f"  Memory per operation: {per_op:.1f} KB")

        report.append(f"  Total leaked: {result.get('total_leaked_mb', 0):.3f} MB")
        report.append(f"  Severity: {result.get('severity', 'unknown')}")
        report.append(f"  Objects leaked: {result.get('objects_leaked', 0)}")

        if "leaked_workers" in result:
            report.append(f"  Leaked workers: {result['leaked_workers']}")

        # Count issues
        severity = result.get("severity", "none")
        if severity in ["minor", "moderate", "severe"]:
            total_issues += 1
        if severity == "severe":
            severe_issues += 1

        report.append("")

    # Extraction results
    if extraction_results and "error" not in extraction_results:
        report.append("EXTRACTION OPERATIONS")
        report.append("-" * 20)
        report.append(f"Memory per operation: {extraction_results['memory_per_operation_kb']:.1f} KB")
        report.append(f"Total leaked: {extraction_results['total_leaked_mb']:.3f} MB")
        report.append(f"Severity: {extraction_results['severity']}")
        report.append("")

    # Summary and recommendations
    report.append("BASELINE SUMMARY")
    report.append("-" * 16)
    report.append(f"Components tested: {len(component_results)}")
    report.append(f"Components with leaks: {total_issues}")
    report.append(f"Severe leaks: {severe_issues}")
    report.append("")

    if severe_issues > 0:
        report.append("🔴 CRITICAL: Severe memory leaks detected!")
        report.append("   These must be fixed before any release.")
    elif total_issues > 0:
        report.append("🟡 WARNING: Memory leaks detected")
        report.append("   Address these issues to improve stability.")
    else:
        report.append("✅ GOOD: No significant memory leaks in baseline")
        report.append("   Current implementation appears stable.")

    report.append("")
    report.append("KEY METRICS FOR TRACKING IMPROVEMENTS:")
    report.append("-" * 38)

    for component, result in component_results.items():
        if "error" in result:
            continue

        component_name = component.replace("_", " ").title()

        if "memory_per_cycle_kb" in result:
            metric = result["memory_per_cycle_kb"]
            report.append(f"  {component_name}: {metric:.1f} KB per cycle")
        elif "memory_per_operation_kb" in result:
            metric = result["memory_per_operation_kb"]
            report.append(f"  {component_name}: {metric:.1f} KB per operation")

    report.append("")
    report.append("Use these metrics to verify that fixes reduce memory usage.")
    report.append("Re-run this baseline after implementing fixes to measure improvement.")

    return "\n".join(report)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run baseline memory profile for SpritePal")
    parser.add_argument("--rom", help="Path to ROM file for extraction testing")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick baseline only (no component tests)")
    parser.add_argument("--output", default="baseline_memory_report.txt",
                       help="Output file for report (default: baseline_memory_report.txt)")

    args = parser.parse_args()

    print_header()

    # Set up environment
    setup_environment()

    # Create profiler
    profiler = MemoryLeakProfiler()

    # Run quick baseline
    baseline_results = run_quick_baseline(profiler)

    if args.quick:
        print("\nQuick baseline complete. Use --help for full testing options.")
        return 0

    # Run critical component tests
    component_results = run_critical_component_tests(profiler)

    # Run extraction test if ROM provided
    extraction_results = None
    if args.rom:
        extraction_results = run_extraction_test(profiler, args.rom)

    # Generate report
    print("\nGenerating baseline report...")
    report = generate_baseline_report(baseline_results, component_results, extraction_results)

    # Save report
    with open(args.output, "w") as f:
        f.write(report)

    print(f"Baseline report saved to: {args.output}")

    # Print summary
    print("\n" + "=" * 50)
    print("BASELINE SUMMARY")
    print("=" * 50)

    failed_tests = sum(1 for r in component_results.values() if "error" in r)
    total_tests = len(component_results)
    successful_tests = total_tests - failed_tests

    issues = sum(1 for r in component_results.values()
                if "error" not in r and r.get("severity") in ["minor", "moderate", "severe"])
    severe_issues = sum(1 for r in component_results.values()
                       if "error" not in r and r.get("severity") == "severe")

    print(f"Tests completed: {successful_tests}/{total_tests}")
    print(f"Components with leaks: {issues}")
    print(f"Severe leaks: {severe_issues}")

    print(f"\nBaseline memory: {baseline_results['baseline_memory_mb']:.2f} MB")

    if severe_issues > 0:
        print("\n🔴 CRITICAL: Severe memory leaks detected in baseline!")
        print("   Fix these immediately before proceeding with development.")
        return 2
    if issues > 0:
        print("\n🟡 WARNING: Memory leaks detected in baseline")
        print("   Address these issues to improve application stability.")
        return 1
    print("\n✅ SUCCESS: No significant memory leaks in baseline!")
    print("   Application appears stable for continued development.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
