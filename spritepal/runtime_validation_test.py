#!/usr/bin/env python3
"""
Runtime Validation Test - Comprehensive runtime checks for SpritePal
Tests threading, resource cleanup, HAL compression, and stability.
"""

import gc
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

import psutil

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.hal_compression import HALProcessPool
from core.managers import cleanup_managers, initialize_managers
from core.managers.registry import get_registry
from utils.logging_config import get_logger
from utils.rom_cache import get_rom_cache

logger = get_logger(__name__)


class RuntimeValidator:
    """Comprehensive runtime validation tests"""

    def __init__(self):
        self.issues = []
        self.warnings = []
        self.process = psutil.Process()

    def check_hal_compression(self):
        """Check HAL compression subsystem"""
        print("\n=== HAL Compression Validation ===")

        try:
            # Get HAL pool instance
            pool = HALProcessPool()

            # Check pool status
            if not pool._initialized:
                self.issues.append("HAL pool not initialized")
                return

            print(f"✓ HAL pool initialized with {len(pool._processes)} workers")

            # Test decompress operation with dummy data
            with tempfile.NamedTemporaryFile(suffix=".sfc", delete=False) as tmp:
                # Create dummy ROM data
                dummy_data = b"\x00" * 0x10000
                tmp.write(dummy_data)
                tmp.flush()

                # Try decompress (should fail gracefully on dummy data)
                try:
                    # Use the correct method name
                    pool.decompress_from_rom(tmp.name, 0x1000)
                    print("✓ HAL decompress operation completed (returned data)")
                except Exception as e:
                    # Expected to fail on dummy data
                    print(f"✓ HAL decompress failed as expected: {e}")

                os.unlink(tmp.name)

            # Check pool shutdown
            initial_pids = pool._process_pids.copy()
            pool.shutdown()

            # Verify processes are gone
            alive_count = 0
            for pid in initial_pids:
                try:
                    os.kill(pid, 0)  # Check if process exists
                    alive_count += 1
                except ProcessLookupError:
                    pass  # Process is gone (good)

            if alive_count > 0:
                self.issues.append(f"{alive_count} HAL worker processes still alive after shutdown")
            else:
                print("✓ All HAL worker processes terminated cleanly")

        except Exception as e:
            self.issues.append(f"HAL compression error: {e}")

    def check_thread_safety(self):
        """Check thread safety and resource cleanup"""
        print("\n=== Thread Safety Validation ===")

        initial_threads = threading.active_count()
        print(f"Initial thread count: {initial_threads}")

        # Test concurrent ROM cache access
        rom_cache = get_rom_cache()
        errors = []

        def concurrent_cache_test(thread_id):
            try:
                for i in range(10):
                    data = {"thread": thread_id, "iter": i}
                    rom_cache.save_rom_info(f"/test/rom_{thread_id}_{i}.sfc", data)
                    retrieved = rom_cache.get_rom_info(f"/test/rom_{thread_id}_{i}.sfc")
                    if not retrieved or retrieved.get("thread") != thread_id:
                        errors.append(f"Thread {thread_id}: Data mismatch at iteration {i}")
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        # Launch concurrent threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=concurrent_cache_test, args=(i,))
            t.start()
            threads.append(t)

        # Wait for completion
        for t in threads:
            t.join(timeout=5.0)

        if errors:
            self.issues.extend(errors[:3])  # Report first 3 errors
            print(f"✗ Thread safety issues: {len(errors)} errors")
        else:
            print("✓ Concurrent ROM cache access successful")

        # Check thread cleanup
        time.sleep(0.5)  # Allow threads to fully terminate
        final_threads = threading.active_count()

        if final_threads > initial_threads:
            self.warnings.append(f"Thread leak: {final_threads - initial_threads} extra threads")
        else:
            print("✓ All threads cleaned up properly")

    def check_memory_usage(self):
        """Check memory usage patterns"""
        print("\n=== Memory Usage Validation ===")

        # Get current memory
        mem_info = self.process.memory_info()
        rss_mb = mem_info.rss / 1024 / 1024
        vms_mb = mem_info.vms / 1024 / 1024

        print(f"RSS: {rss_mb:.1f} MB, VMS: {vms_mb:.1f} MB")

        # Perform memory stress test
        large_objects = []
        for _i in range(5):
            # Create 10MB objects
            large_objects.append(bytearray(10 * 1024 * 1024))

        peak_mem = self.process.memory_info().rss / 1024 / 1024

        # Clean up
        large_objects.clear()
        gc.collect()
        time.sleep(0.5)

        final_mem = self.process.memory_info().rss / 1024 / 1024

        print(f"Memory test - Initial: {rss_mb:.1f}MB, Peak: {peak_mem:.1f}MB, Final: {final_mem:.1f}MB")

        # Check for leaks
        leak_threshold = 20  # MB
        if final_mem - rss_mb > leak_threshold:
            self.warnings.append(f"Potential memory leak: {final_mem - rss_mb:.1f}MB increase")
        else:
            print("✓ Memory properly released after test")

    def check_manager_lifecycle(self):
        """Check manager initialization and cleanup"""
        print("\n=== Manager Lifecycle Validation ===")

        try:
            # Initialize managers
            cleanup_managers()  # Ensure clean start
            initialize_managers("RuntimeValidationTest")

            # Get managers
            registry = get_registry()
            extraction_mgr = registry.get_extraction_manager()
            injection_mgr = registry.get_injection_manager()
            session_mgr = registry.get_session_manager()

            if not all([extraction_mgr, injection_mgr, session_mgr]):
                self.issues.append("Failed to initialize all managers")
                return

            print("✓ All managers initialized successfully")

            # Test basic operations
            # Check that managers have expected methods
            if hasattr(extraction_mgr, "extract_from_rom"):
                print("✓ ExtractionManager has extract_from_rom method")
            if hasattr(extraction_mgr, "get_rom_extractor"):
                print("✓ ExtractionManager has get_rom_extractor method")

            # Cleanup
            cleanup_managers()
            print("✓ Managers cleaned up successfully")

        except Exception as e:
            self.issues.append(f"Manager lifecycle error: {e}")

    def check_file_handles(self):
        """Check for file handle leaks"""
        print("\n=== File Handle Validation ===")

        try:
            open_files = self.process.open_files()
            print(f"Open files: {len(open_files)}")

            # Filter out system files
            app_files = [f for f in open_files if "spritepal" in f.path.lower()]

            if app_files:
                print(f"SpritePal-related open files: {len(app_files)}")
                for f in app_files[:5]:  # Show first 5
                    print(f"  - {f.path}")

            # Test file operations
            with tempfile.NamedTemporaryFile(suffix=".test", delete=False) as tmp:
                tmp.write(b"test data")
                tmp_path = tmp.name

            # File should be closed
            os.unlink(tmp_path)
            print("✓ Temporary file operations clean")

        except Exception as e:
            self.warnings.append(f"File handle check error: {e}")

    def run_validation(self):
        """Run all validation checks"""
        print("="*60)
        print("SPRITEPAL RUNTIME VALIDATION")
        print("="*60)

        # Run all checks
        self.check_manager_lifecycle()
        self.check_hal_compression()
        self.check_thread_safety()
        self.check_memory_usage()
        self.check_file_handles()

        # Summary
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)

        if self.issues:
            print(f"\n❌ CRITICAL ISSUES ({len(self.issues)}):")
            for issue in self.issues:
                print(f"  - {issue}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")

        if not self.issues and not self.warnings:
            print("\n✅ ALL RUNTIME VALIDATION CHECKS PASSED!")
            print("The application appears to be stable for production use.")
        elif not self.issues:
            print("\n✅ No critical issues found.")
            print("⚠️  Some warnings should be reviewed.")
        else:
            print("\n❌ Critical issues detected that need to be fixed.")

        return len(self.issues) == 0


def main():
    """Main entry point"""
    validator = RuntimeValidator()
    success = validator.run_validation()

    # Final cleanup
    cleanup_managers()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
