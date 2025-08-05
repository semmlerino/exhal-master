#!/usr/bin/env python3
"""
Comprehensive validation script for new search features implementation.

This script validates:
1. ParallelSpriteFinder implementation
2. Visual Similarity Search
3. Pattern Search functionality
4. Background Indexing
5. Integration with existing infrastructure
6. Performance characteristics
"""

import importlib
import sys
import traceback
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def check_imports() -> dict[str, list[str]]:
    """Check if all required modules can be imported."""
    issues = {}

    modules_to_check = [
        # Core search modules
        ("core.parallel_sprite_finder", ["ParallelSpriteFinder", "AdaptiveSpriteFinder", "SearchResult", "SearchChunk"]),
        ("core.visual_similarity_search", ["VisualSimilarityEngine", "SpriteGroupFinder", "SpriteHash", "SimilarityMatch"]),

        # Worker modules
        ("ui.rom_extraction.workers.sprite_search_worker", ["SpriteSearchWorker"]),
        ("ui.rom_extraction.workers.similarity_indexing_worker", ["SimilarityIndexingWorker"]),
        ("ui.rom_extraction.workers.search_worker", ["SpriteSearchWorker"]),

        # Dialog modules
        ("ui.dialogs.advanced_search_dialog", ["AdvancedSearchDialog", "SearchWorker", "SearchFilter", "SearchHistoryEntry"]),

        # Dependencies
        ("PIL", ["Image"]),
        ("numpy", ["ndarray"]),
    ]

    for module_name, expected_classes in modules_to_check:
        try:
            module = importlib.import_module(module_name)
            missing = []
            for cls in expected_classes:
                if not hasattr(module, cls):
                    missing.append(cls)
            if missing:
                issues[module_name] = missing
        except ImportError as e:
            issues[module_name] = [f"Import error: {e!s}"]
        except Exception as e:
            issues[module_name] = [f"Unexpected error: {e!s}"]

    return issues


def check_missing_imports_in_files() -> dict[str, list[str]]:
    """Check for missing imports in implementation files."""
    missing_imports = {}

    files_to_check = [
        ("ui/dialogs/advanced_search_dialog.py", ["import re", "import mmap"]),
        ("core/parallel_sprite_finder.py", ["from concurrent.futures import ThreadPoolExecutor"]),
        ("core/visual_similarity_search.py", ["import numpy as np", "from PIL import Image"]),
        ("ui/rom_extraction/workers/similarity_indexing_worker.py", ["from core.visual_similarity_search import VisualSimilarityEngine"]),
    ]

    for file_path, required_imports in files_to_check:
        file_full_path = Path(__file__).parent / file_path
        if not file_full_path.exists():
            missing_imports[file_path] = ["File not found"]
            continue

        with open(file_full_path) as f:
            content = f.read()

        missing = []
        for import_stmt in required_imports:
            if import_stmt not in content:
                missing.append(import_stmt)

        if missing:
            missing_imports[file_path] = missing

    return missing_imports


def check_thread_safety() -> dict[str, list[str]]:
    """Check for potential thread safety issues."""
    thread_issues = {}

    # Check ParallelSpriteFinder
    try:
        from core.parallel_sprite_finder import ParallelSpriteFinder

        # Check executor initialization
        finder = ParallelSpriteFinder(num_workers=2)
        if not hasattr(finder, "executor"):
            thread_issues["ParallelSpriteFinder"] = ["Missing executor attribute"]
        elif finder.executor is None:
            thread_issues["ParallelSpriteFinder"] = ["Executor is None"]

        # Check shutdown method
        if not hasattr(finder, "shutdown"):
            thread_issues["ParallelSpriteFinder"] = [*thread_issues.get("ParallelSpriteFinder", []), "Missing shutdown method"]
        else:
            try:
                finder.shutdown()
            except Exception as e:
                thread_issues["ParallelSpriteFinder"] = [*thread_issues.get("ParallelSpriteFinder", []), f"Shutdown error: {e!s}"]

    except Exception as e:
        thread_issues["ParallelSpriteFinder"] = [f"Initialization error: {e!s}"]

    # Check worker decorators
    try:
        from ui.rom_extraction.workers.sprite_search_worker import SpriteSearchWorker

        # Check if handle_worker_errors decorator is used
        if hasattr(SpriteSearchWorker, "run"):
            run_method = SpriteSearchWorker.run
            if not hasattr(run_method, "__wrapped__"):
                thread_issues["SpriteSearchWorker"] = ["run method not decorated with @handle_worker_errors"]
    except Exception as e:
        thread_issues["Worker decorators"] = [f"Check failed: {e!s}"]

    return thread_issues


def check_signal_definitions() -> dict[str, list[str]]:
    """Check Qt signal definitions in workers."""
    signal_issues = {}

    worker_classes = [
        ("ui.rom_extraction.workers.sprite_search_worker", "SpriteSearchWorker",
         ["sprite_found", "search_complete", "progress", "error"]),
        ("ui.rom_extraction.workers.similarity_indexing_worker", "SimilarityIndexingWorker",
         ["sprite_indexed", "index_saved", "index_loaded", "progress", "error", "finished"]),
        ("ui.dialogs.advanced_search_dialog", "SearchWorker",
         ["progress", "result_found", "search_complete", "error"]),
    ]

    for module_name, class_name, expected_signals in worker_classes:
        try:
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)

            missing_signals = []
            for signal in expected_signals:
                if not hasattr(cls, signal):
                    missing_signals.append(signal)

            if missing_signals:
                signal_issues[f"{module_name}.{class_name}"] = missing_signals

        except Exception as e:
            signal_issues[f"{module_name}.{class_name}"] = [f"Check failed: {e!s}"]

    return signal_issues


def check_initialization_order() -> dict[str, list[str]]:
    """Check for potential initialization order issues."""
    init_issues = {}

    # Check SimilarityIndexingWorker
    try:
        from ui.rom_extraction.workers.similarity_indexing_worker import (
            SimilarityIndexingWorker,
        )

        # Try to create instance (may fail if dependencies not met)
        test_rom_path = "/tmp/test.rom"
        worker = SimilarityIndexingWorker(test_rom_path)

        # Check critical attributes
        critical_attrs = ["similarity_engine", "cache_dir", "index_file", "_index_lock"]
        missing_attrs = []
        for attr in critical_attrs:
            if not hasattr(worker, attr):
                missing_attrs.append(attr)

        if missing_attrs:
            init_issues["SimilarityIndexingWorker"] = [f"Missing attributes: {', '.join(missing_attrs)}"]

    except Exception as e:
        init_issues["SimilarityIndexingWorker"] = [f"Initialization failed: {e!s}\n{traceback.format_exc()}"]

    return init_issues


def check_integration_points() -> dict[str, list[str]]:
    """Check integration with existing infrastructure."""
    integration_issues = {}

    # Check if workers inherit from correct base classes
    try:
        from ui.rom_extraction.workers.base import BaseWorker
        from ui.rom_extraction.workers.sprite_search_worker import SpriteSearchWorker

        if not issubclass(SpriteSearchWorker, BaseWorker):
            integration_issues["SpriteSearchWorker"] = ["Does not inherit from BaseWorker"]
    except Exception as e:
        integration_issues["Worker inheritance"] = [f"Check failed: {e!s}"]

    # Check manager integration
    try:
        from core.managers import get_extraction_manager
        manager = get_extraction_manager()
        if not hasattr(manager, "extract_sprite_at_offset"):
            integration_issues["ExtractionManager"] = ["Missing extract_sprite_at_offset method"]
    except Exception as e:
        integration_issues["Manager integration"] = [f"Check failed: {e!s}"]

    return integration_issues


def check_performance_characteristics() -> dict[str, Any]:
    """Basic performance characteristics check."""
    perf_info = {}

    try:
        import time

        from core.parallel_sprite_finder import ParallelSpriteFinder

        # Create test data
        test_data = b"\x01\x02\x03\x04" * 0x10000  # 256KB

        # Test chunk creation performance
        finder = ParallelSpriteFinder()
        start = time.time()
        chunks = finder._create_chunks(0, len(test_data))
        chunk_time = time.time() - start

        perf_info["chunk_creation"] = {
            "time_ms": chunk_time * 1000,
            "chunk_count": len(chunks),
            "acceptable": chunk_time < 0.01  # Should be very fast
        }

        # Test quick sprite check
        start = time.time()
        for _ in range(1000):
            finder._quick_sprite_check(test_data, 0)
        check_time = time.time() - start

        perf_info["quick_check"] = {
            "time_per_1000_checks_ms": check_time * 1000,
            "acceptable": check_time < 0.1  # 100ms for 1000 checks
        }

        finder.shutdown()

    except Exception as e:
        perf_info["error"] = str(e)

    return perf_info


def main():
    """Run all validation checks."""
    print("SpritePal Search Features Validation Report")
    print("=" * 60)
    print()

    # 1. Check imports
    print("1. Import Validation")
    print("-" * 30)
    import_issues = check_imports()
    if not import_issues:
        print("✅ All modules imported successfully")
    else:
        print("❌ Import issues found:")
        for module, issues in import_issues.items():
            print(f"   {module}: {', '.join(issues)}")
    print()

    # 2. Check missing imports in files
    print("2. Missing Import Statements")
    print("-" * 30)
    missing_imports = check_missing_imports_in_files()
    if not missing_imports:
        print("✅ All required imports present")
    else:
        print("❌ Missing imports found:")
        for file, imports in missing_imports.items():
            print(f"   {file}:")
            for imp in imports:
                print(f"      - {imp}")
    print()

    # 3. Check thread safety
    print("3. Thread Safety Validation")
    print("-" * 30)
    thread_issues = check_thread_safety()
    if not thread_issues:
        print("✅ Thread safety checks passed")
    else:
        print("❌ Thread safety issues:")
        for component, issues in thread_issues.items():
            print(f"   {component}:")
            for issue in issues:
                print(f"      - {issue}")
    print()

    # 4. Check signal definitions
    print("4. Qt Signal Validation")
    print("-" * 30)
    signal_issues = check_signal_definitions()
    if not signal_issues:
        print("✅ All signals properly defined")
    else:
        print("❌ Signal definition issues:")
        for component, signals in signal_issues.items():
            print(f"   {component}: Missing signals - {', '.join(signals)}")
    print()

    # 5. Check initialization order
    print("5. Initialization Order Validation")
    print("-" * 30)
    init_issues = check_initialization_order()
    if not init_issues:
        print("✅ Initialization order correct")
    else:
        print("❌ Initialization issues:")
        for component, issues in init_issues.items():
            print(f"   {component}:")
            for issue in issues:
                print(f"      - {issue}")
    print()

    # 6. Check integration points
    print("6. Integration Validation")
    print("-" * 30)
    integration_issues = check_integration_points()
    if not integration_issues:
        print("✅ Integration points valid")
    else:
        print("❌ Integration issues:")
        for component, issues in integration_issues.items():
            print(f"   {component}:")
            for issue in issues:
                print(f"      - {issue}")
    print()

    # 7. Check performance
    print("7. Performance Characteristics")
    print("-" * 30)
    perf_info = check_performance_characteristics()
    if "error" in perf_info:
        print(f"❌ Performance check failed: {perf_info['error']}")
    else:
        for test, info in perf_info.items():
            status = "✅" if info.get("acceptable", False) else "⚠️"
            print(f"{status} {test}: {info}")
    print()

    # Summary
    total_issues = (len(import_issues) + len(missing_imports) + len(thread_issues) +
                   len(signal_issues) + len(init_issues) + len(integration_issues))

    print("=" * 60)
    print(f"Summary: {'✅ All checks passed!' if total_issues == 0 else f'❌ {total_issues} issues found'}")
    print()

    # Recommendations
    if total_issues > 0:
        print("Recommendations:")
        print("-" * 30)

        if missing_imports:
            print("1. Add missing import statements:")
            print("   - In advanced_search_dialog.py: import re")
            print("   - In advanced_search_dialog.py: import mmap")

        if import_issues:
            print("2. Install missing dependencies:")
            if "numpy" in str(import_issues):
                print("   - pip install numpy")
            if "PIL" in str(import_issues):
                print("   - pip install Pillow")

        if thread_issues:
            print("3. Fix thread safety issues:")
            print("   - Ensure proper cleanup in shutdown methods")
            print("   - Use @handle_worker_errors decorator on all worker run methods")

        if signal_issues:
            print("4. Define missing Qt signals in worker classes")

        if init_issues:
            print("5. Fix initialization order issues:")
            print("   - Ensure base class __init__ is called before accessing attributes")
            print("   - Initialize all instance variables before use")

    return total_issues == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
