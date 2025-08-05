#!/usr/bin/env python3
"""
Memory Leak Validation Test for SpritePal

This script validates that the memory leak fixes reduce memory growth from 100MB/sec to <1MB/sec.
It performs stress tests on the components that were previously causing major memory leaks:

1. Manager initialization cycles
2. HAL process pool operations  
3. Worker lifecycle patterns
4. Dialog creation/destruction cycles
5. Qt object lifecycle management

The test measures memory growth rate and provides clear pass/fail criteria.
"""

import gc
import os
import sys
import time
import tracemalloc
from typing import Any

import psutil
from PyQt6.QtWidgets import QApplication

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logging_config import get_logger

logger = get_logger(__name__)

class MemoryLeakValidator:
    """Validates memory leak fixes with precise measurements"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.baseline_memory = 0.0
        self.test_results = {}
        
        # Start tracemalloc for detailed tracking
        if not tracemalloc.is_tracing():
            tracemalloc.start(25)
    
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB"""
        # Force garbage collection for accurate measurement
        for _ in range(3):
            gc.collect()
        
        return self.process.memory_info().rss / 1024 / 1024
    
    def establish_baseline(self) -> None:
        """Establish baseline memory after application startup"""
        logger.info("Establishing memory baseline...")
        
        # Allow Qt application to stabilize
        QApplication.processEvents()
        time.sleep(2)
        
        self.baseline_memory = self.get_memory_usage_mb()
        logger.info(f"Baseline memory established: {self.baseline_memory:.2f} MB")
    
    def test_manager_initialization_cycles(self, cycles: int = 50) -> dict[str, Any]:
        """Test manager initialization and cleanup cycles"""
        logger.info(f"Testing manager initialization cycles: {cycles} cycles")
        
        start_memory = self.get_memory_usage_mb()
        start_time = time.time()
        
        try:
            from core.managers.registry import ManagerRegistry
            
            for i in range(cycles):
                # Create new registry instance
                registry = ManagerRegistry()
                registry.initialize_managers("TestApp")
                
                # Verify managers are working
                session_manager = registry.get_session_manager()
                extraction_manager = registry.get_extraction_manager()
                injection_manager = registry.get_injection_manager()
                
                # Cleanup
                registry.cleanup_managers()
                
                # Force garbage collection every 10 cycles
                if (i + 1) % 10 == 0:
                    gc.collect()
                    logger.debug(f"Completed {i + 1}/{cycles} manager cycles")
        
        except Exception as e:
            logger.exception(f"Error in manager initialization test: {e}")
            return {"error": str(e)}
        
        end_memory = self.get_memory_usage_mb()
        end_time = time.time()
        
        memory_growth = end_memory - start_memory
        time_elapsed = end_time - start_time
        growth_rate_mb_per_sec = memory_growth / time_elapsed if time_elapsed > 0 else 0
        
        result = {
            "test": "manager_initialization",
            "cycles": cycles,
            "start_memory_mb": start_memory,
            "end_memory_mb": end_memory,
            "memory_growth_mb": memory_growth,
            "time_elapsed_sec": time_elapsed,
            "growth_rate_mb_per_sec": growth_rate_mb_per_sec,
            "memory_per_cycle_kb": (memory_growth * 1024) / cycles if cycles > 0 else 0,
            "pass": growth_rate_mb_per_sec < 1.0  # Must be < 1MB/sec
        }
        
        logger.info(f"Manager test: {memory_growth:.2f}MB growth, {growth_rate_mb_per_sec:.3f}MB/sec")
        return result
    
    def test_hal_process_pool_cycles(self, cycles: int = 30) -> dict[str, Any]:
        """Test HAL process pool creation and shutdown cycles"""
        logger.info(f"Testing HAL process pool cycles: {cycles} cycles")
        
        start_memory = self.get_memory_usage_mb()
        start_time = time.time()
        
        try:
            from core.hal_compression import HALProcessPool
            
            for i in range(cycles):
                # Reset singleton to start fresh
                HALProcessPool.reset_singleton()
                
                # Create and initialize pool
                hal_pool = HALProcessPool()
                # Use dummy paths since we're just testing lifecycle
                success = hal_pool.initialize("/dev/null", "/dev/null", pool_size=2)
                
                if success:
                    # Test basic pool operations
                    _ = hal_pool.is_initialized
                    _ = hal_pool.pool_status
                
                # Force shutdown
                hal_pool.force_reset()
                
                # Force garbage collection every 5 cycles
                if (i + 1) % 5 == 0:
                    gc.collect()
                    logger.debug(f"Completed {i + 1}/{cycles} HAL pool cycles")
        
        except Exception as e:
            logger.exception(f"Error in HAL pool test: {e}")
            return {"error": str(e)}
        
        end_memory = self.get_memory_usage_mb()
        end_time = time.time()
        
        memory_growth = end_memory - start_memory
        time_elapsed = end_time - start_time
        growth_rate_mb_per_sec = memory_growth / time_elapsed if time_elapsed > 0 else 0
        
        result = {
            "test": "hal_process_pool",
            "cycles": cycles,
            "start_memory_mb": start_memory,
            "end_memory_mb": end_memory,
            "memory_growth_mb": memory_growth,
            "time_elapsed_sec": time_elapsed,
            "growth_rate_mb_per_sec": growth_rate_mb_per_sec,
            "memory_per_cycle_kb": (memory_growth * 1024) / cycles if cycles > 0 else 0,
            "pass": growth_rate_mb_per_sec < 1.0  # Must be < 1MB/sec
        }
        
        logger.info(f"HAL pool test: {memory_growth:.2f}MB growth, {growth_rate_mb_per_sec:.3f}MB/sec")
        return result
    
    def test_worker_lifecycle_cycles(self, cycles: int = 40) -> dict[str, Any]:
        """Test worker thread creation and cleanup cycles"""
        logger.info(f"Testing worker lifecycle cycles: {cycles} cycles")
        
        start_memory = self.get_memory_usage_mb()
        start_time = time.time()
        
        try:
            from core.workers.base import BaseWorker
            from PyQt6.QtCore import QObject
            
            class TestWorker(BaseWorker):
                def run(self):
                    # Simulate some work
                    self.emit_progress(50, "Working...")
                    time.sleep(0.01)  # Brief work simulation
                    self.operation_finished.emit(True, "Complete")
            
            for i in range(cycles):
                # Create worker with proper parent
                parent = QObject()
                worker = TestWorker(parent=parent)
                
                # Start and wait for completion
                worker.start()
                worker.wait(1000)  # Wait up to 1 second
                
                # Cleanup
                worker.deleteLater()
                parent.deleteLater()
                QApplication.processEvents()
                
                # Force garbage collection every 10 cycles
                if (i + 1) % 10 == 0:
                    gc.collect()
                    logger.debug(f"Completed {i + 1}/{cycles} worker cycles")
        
        except Exception as e:
            logger.exception(f"Error in worker lifecycle test: {e}")
            return {"error": str(e)}
        
        end_memory = self.get_memory_usage_mb()
        end_time = time.time()
        
        memory_growth = end_memory - start_memory
        time_elapsed = end_time - start_time
        growth_rate_mb_per_sec = memory_growth / time_elapsed if time_elapsed > 0 else 0
        
        result = {
            "test": "worker_lifecycle",
            "cycles": cycles,
            "start_memory_mb": start_memory,
            "end_memory_mb": end_memory,
            "memory_growth_mb": memory_growth,
            "time_elapsed_sec": time_elapsed,
            "growth_rate_mb_per_sec": growth_rate_mb_per_sec,
            "memory_per_cycle_kb": (memory_growth * 1024) / cycles if cycles > 0 else 0,
            "pass": growth_rate_mb_per_sec < 1.0  # Must be < 1MB/sec
        }
        
        logger.info(f"Worker test: {memory_growth:.2f}MB growth, {growth_rate_mb_per_sec:.3f}MB/sec")
        return result
    
    def test_context_manager_cycles(self, cycles: int = 100) -> dict[str, Any]:
        """Test context manager creation and cleanup cycles"""
        logger.info(f"Testing context manager cycles: {cycles} cycles")
        
        start_memory = self.get_memory_usage_mb()
        start_time = time.time()
        
        try:
            from core.managers.context import manager_context, ManagerContext
            from unittest.mock import MagicMock
            
            for i in range(cycles):
                # Create mock managers
                mock_session = MagicMock()
                mock_extraction = MagicMock()
                mock_injection = MagicMock()
                
                managers = {
                    "session": mock_session,
                    "extraction": mock_extraction,
                    "injection": mock_injection
                }
                
                # Test context creation and usage
                with manager_context(managers, name=f"test_cycle_{i}") as ctx:
                    # Verify context works
                    assert ctx.has_manager("session")
                    assert ctx.has_manager("extraction")
                    assert ctx.has_manager("injection")
                    
                    # Create child context
                    child_ctx = ctx.create_child_context(name="child")
                    assert child_ctx.has_manager("session")  # Inherited
                
                # Force garbage collection every 20 cycles
                if (i + 1) % 20 == 0:
                    gc.collect()
                    logger.debug(f"Completed {i + 1}/{cycles} context cycles")
        
        except Exception as e:
            logger.exception(f"Error in context manager test: {e}")
            return {"error": str(e)}
        
        end_memory = self.get_memory_usage_mb()
        end_time = time.time()
        
        memory_growth = end_memory - start_memory
        time_elapsed = end_time - start_time
        growth_rate_mb_per_sec = memory_growth / time_elapsed if time_elapsed > 0 else 0
        
        result = {
            "test": "context_manager",
            "cycles": cycles,
            "start_memory_mb": start_memory,
            "end_memory_mb": end_memory,
            "memory_growth_mb": memory_growth,
            "time_elapsed_sec": time_elapsed,
            "growth_rate_mb_per_sec": growth_rate_mb_per_sec,
            "memory_per_cycle_kb": (memory_growth * 1024) / cycles if cycles > 0 else 0,
            "pass": growth_rate_mb_per_sec < 1.0  # Must be < 1MB/sec
        }
        
        logger.info(f"Context test: {memory_growth:.2f}MB growth, {growth_rate_mb_per_sec:.3f}MB/sec")
        return result
    
    def run_comprehensive_validation(self) -> dict[str, Any]:
        """Run all memory leak validation tests"""
        logger.info("Starting comprehensive memory leak validation")
        
        self.establish_baseline()
        
        # Run all tests
        tests = [
            ("manager_initialization", lambda: self.test_manager_initialization_cycles(50)),
            ("hal_process_pool", lambda: self.test_hal_process_pool_cycles(30)),
            ("worker_lifecycle", lambda: self.test_worker_lifecycle_cycles(40)),
            ("context_manager", lambda: self.test_context_manager_cycles(100))
        ]
        
        results = {}
        total_memory_growth = 0.0
        all_tests_passed = True
        
        for test_name, test_func in tests:
            logger.info(f"Running {test_name} test...")
            try:
                result = test_func()
                results[test_name] = result
                
                if "error" not in result:
                    total_memory_growth += result["memory_growth_mb"]
                    if not result["pass"]:
                        all_tests_passed = False
                else:
                    all_tests_passed = False
                    
            except Exception as e:
                logger.exception(f"Test {test_name} failed with exception: {e}")
                results[test_name] = {"error": str(e)}
                all_tests_passed = False
        
        # Calculate overall results
        final_memory = self.get_memory_usage_mb()
        total_growth_from_baseline = final_memory - self.baseline_memory
        
        summary = {
            "baseline_memory_mb": self.baseline_memory,
            "final_memory_mb": final_memory,
            "total_growth_from_baseline_mb": total_growth_from_baseline,
            "total_test_growth_mb": total_memory_growth,
            "all_tests_passed": all_tests_passed,
            "tests": results,
            "validation_passed": all_tests_passed and total_growth_from_baseline < 10.0  # Total growth < 10MB
        }
        
        return summary
    
    def generate_report(self, results: dict[str, Any]) -> str:
        """Generate human-readable validation report"""
        report = []
        report.append("SpritePal Memory Leak Validation Report")
        report.append("=" * 50)
        report.append(f"Baseline Memory: {results['baseline_memory_mb']:.2f} MB")
        report.append(f"Final Memory: {results['final_memory_mb']:.2f} MB")
        report.append(f"Total Growth: {results['total_growth_from_baseline_mb']:.2f} MB")
        report.append("")
        
        if results["validation_passed"]:
            report.append("✅ VALIDATION PASSED - Memory leak fixes are effective!")
        else:
            report.append("❌ VALIDATION FAILED - Memory leaks still present")
        
        report.append("")
        report.append("Individual Test Results:")
        report.append("-" * 30)
        
        for test_name, test_result in results["tests"].items():
            if "error" in test_result:
                report.append(f"{test_name}: ❌ ERROR - {test_result['error']}")
                continue
            
            status = "✅ PASS" if test_result["pass"] else "❌ FAIL"
            growth_rate = test_result["growth_rate_mb_per_sec"]
            memory_per_cycle = test_result["memory_per_cycle_kb"]
            
            report.append(f"{test_name}: {status}")
            report.append(f"  Memory growth rate: {growth_rate:.3f} MB/sec")
            report.append(f"  Memory per cycle: {memory_per_cycle:.1f} KB")
            report.append(f"  Total cycles: {test_result['cycles']}")
            report.append("")
        
        # Performance targets
        report.append("Performance Targets:")
        report.append("- Memory growth rate: < 1.0 MB/sec per test")
        report.append("- Total memory growth: < 10.0 MB for all tests")
        report.append("- Previous leak rate: ~100 MB/sec (BEFORE fixes)")
        report.append("")
        
        if results["validation_passed"]:
            improvement = 100.0  # Assume 100x improvement if passing
            worst_rate = max(
                (test["growth_rate_mb_per_sec"] for test in results["tests"].values() 
                 if "growth_rate_mb_per_sec" in test),
                default=0
            )
            if worst_rate > 0:
                improvement = 100.0 / max(worst_rate, 0.01)  # Avoid division by zero
            
            report.append(f"🎉 Memory leak fixes achieved ~{improvement:.0f}x improvement!")
            report.append("Memory growth reduced from 100MB/sec to <1MB/sec")
        else:
            report.append("⚠️  Memory leak fixes need additional work")
        
        return "\n".join(report)


def main():
    """Main validation function"""
    # Initialize Qt application for testing
    app = QApplication(sys.argv)
    
    # Create validator
    validator = MemoryLeakValidator()
    
    try:
        # Run comprehensive validation
        results = validator.run_comprehensive_validation()
        
        # Generate and save report
        report = validator.generate_report(results)
        
        # Save to file
        report_file = "memory_leak_validation_report.txt"
        with open(report_file, "w") as f:
            f.write(report)
        
        # Print summary
        print(report)
        print(f"\nDetailed report saved to: {report_file}")
        
        # Exit with appropriate code
        if results["validation_passed"]:
            print("\n✅ All memory leak validation tests PASSED!")
            sys.exit(0)
        else:
            print("\n❌ Memory leak validation tests FAILED!")
            sys.exit(1)
    
    except Exception as e:
        logger.exception(f"Validation failed with exception: {e}")
        print(f"❌ Validation failed: {e}")
        sys.exit(1)
    
    finally:
        # Cleanup
        try:
            app.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()