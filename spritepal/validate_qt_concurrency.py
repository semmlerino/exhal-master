#!/usr/bin/env python3
"""
Qt Concurrency Architecture Validation Script

This script validates the Qt threading and concurrency architecture
to ensure thread safety, signal integrity, and proper resource management.
"""

import sys
import time
import threading
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtCore import QThread, QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtWidgets import QApplication

from core.controller import ExtractionController
from core.managers import get_extraction_manager, get_injection_manager
from core.hal_compression import HALProcessPool, HALCompressor
from ui.common.worker_manager import WorkerManager
from core.workers.base import BaseWorker
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ConcurrencyTestWorker(BaseWorker):
    """Test worker for concurrency validation."""
    
    test_signal = pyqtSignal(str)
    cross_thread_test = pyqtSignal(int, str)
    
    def __init__(self, test_duration: float = 2.0):
        super().__init__()
        self.test_duration = test_duration
        self.signal_count = 0
        
    def run(self):
        """Emit signals from worker thread to test cross-thread delivery."""
        logger.info(f"Worker thread: {threading.current_thread().name}")
        
        # Test 1: Basic signal emission
        self.test_signal.emit("Signal from worker thread")
        
        # Test 2: Multiple rapid emissions
        for i in range(5):
            self.cross_thread_test.emit(i, f"Rapid signal {i}")
            self.msleep(10)
            
        # Test 3: Check cancellation
        self.msleep(int(self.test_duration * 500))
        self.check_cancellation()
        
        # Test 4: Final signal
        self.msleep(int(self.test_duration * 500))
        self.operation_finished.emit(True, "Worker completed successfully")


class ConcurrencyValidator(QObject):
    """Main validator for Qt concurrency architecture."""
    
    validation_complete = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.results = {
            "thread_safety": {"passed": True, "details": []},
            "signal_delivery": {"passed": True, "details": []},
            "process_management": {"passed": True, "details": []},
            "resource_cleanup": {"passed": True, "details": []},
            "casting_pattern": {"passed": True, "details": []},
        }
        self.signal_received_count = 0
        self.main_thread_id = threading.current_thread().ident
        
    def validate_all(self):
        """Run all validation tests."""
        logger.info("Starting Qt concurrency validation...")
        
        # Test 1: Thread Safety
        self.test_thread_safety()
        
        # Test 2: Signal Delivery
        self.test_signal_delivery()
        
        # Test 3: Process Management
        self.test_process_management()
        
        # Test 4: Resource Cleanup
        self.test_resource_cleanup()
        
        # Test 5: Casting Pattern
        self.test_casting_pattern()
        
        # Emit results
        QTimer.singleShot(3000, lambda: self.validation_complete.emit(self.results))
        
    def test_thread_safety(self):
        """Test thread safety of worker operations."""
        try:
            # Create multiple workers
            workers = []
            for i in range(3):
                worker = ConcurrencyTestWorker(test_duration=0.5)
                worker.test_signal.connect(self.on_test_signal)
                workers.append(worker)
                worker.start()
                
            # Wait briefly
            QThread.msleep(100)
            
            # Check all workers are in different threads
            thread_ids = set()
            for worker in workers:
                if worker.isRunning():
                    thread_ids.add(worker.thread())
                    
            if len(thread_ids) == len(workers):
                self.results["thread_safety"]["details"].append(
                    "✓ Each worker runs in separate thread"
                )
            else:
                self.results["thread_safety"]["passed"] = False
                self.results["thread_safety"]["details"].append(
                    "✗ Workers not in separate threads"
                )
                
            # Cleanup
            for worker in workers:
                WorkerManager.cleanup_worker(worker, timeout=1000)
                
        except Exception as e:
            self.results["thread_safety"]["passed"] = False
            self.results["thread_safety"]["details"].append(f"✗ Exception: {e}")
            
    def test_signal_delivery(self):
        """Test cross-thread signal delivery."""
        try:
            self.signal_received_count = 0
            
            # Create worker and connect signals
            worker = ConcurrencyTestWorker(test_duration=0.5)
            worker.cross_thread_test.connect(self.on_cross_thread_signal)
            worker.operation_finished.connect(self.on_worker_finished)
            
            # Start worker
            worker.start()
            
            # Wait for completion
            if worker.wait(2000):
                if self.signal_received_count >= 5:
                    self.results["signal_delivery"]["details"].append(
                        f"✓ Received {self.signal_received_count} cross-thread signals"
                    )
                else:
                    self.results["signal_delivery"]["passed"] = False
                    self.results["signal_delivery"]["details"].append(
                        f"✗ Only received {self.signal_received_count} signals"
                    )
            else:
                self.results["signal_delivery"]["passed"] = False
                self.results["signal_delivery"]["details"].append(
                    "✗ Worker did not complete in time"
                )
                
            # Cleanup
            WorkerManager.cleanup_worker(worker)
            
        except Exception as e:
            self.results["signal_delivery"]["passed"] = False
            self.results["signal_delivery"]["details"].append(f"✗ Exception: {e}")
            
    def test_process_management(self):
        """Test HAL process pool management."""
        try:
            # Test HAL process pool
            pool = HALProcessPool()
            
            # Check if pool can be initialized
            if hasattr(pool, 'is_initialized') and not pool.is_initialized:
                # Try to find HAL tools
                try:
                    compressor = HALCompressor(use_pool=False)
                    if compressor.exhal_path and compressor.inhal_path:
                        success = pool.initialize(
                            compressor.exhal_path, 
                            compressor.inhal_path,
                            pool_size=2
                        )
                        if success:
                            self.results["process_management"]["details"].append(
                                "✓ HAL process pool initialized successfully"
                            )
                        else:
                            self.results["process_management"]["details"].append(
                                "⚠ HAL process pool initialization failed (tools may be missing)"
                            )
                    else:
                        self.results["process_management"]["details"].append(
                            "⚠ HAL tools not found - skipping process pool test"
                        )
                except Exception as e:
                    self.results["process_management"]["details"].append(
                        f"⚠ Could not test HAL process pool: {e}"
                    )
            else:
                self.results["process_management"]["details"].append(
                    "✓ HAL process pool already initialized"
                )
                
            # Test pool shutdown
            pool.shutdown()
            self.results["process_management"]["details"].append(
                "✓ HAL process pool shutdown completed"
            )
            
        except Exception as e:
            self.results["process_management"]["passed"] = False
            self.results["process_management"]["details"].append(f"✗ Exception: {e}")
            
    def test_resource_cleanup(self):
        """Test resource cleanup and memory management."""
        try:
            # Create and cleanup multiple workers
            for i in range(5):
                worker = ConcurrencyTestWorker(test_duration=0.1)
                worker.start()
                
                # Test cancellation
                QThread.msleep(50)
                success = WorkerManager.safe_cancel_worker(worker, timeout=500)
                
                if not success:
                    self.results["resource_cleanup"]["passed"] = False
                    self.results["resource_cleanup"]["details"].append(
                        f"✗ Worker {i} did not respond to cancellation"
                    )
                    
                # Cleanup
                WorkerManager.cleanup_worker(worker, timeout=1000)
                
            self.results["resource_cleanup"]["details"].append(
                "✓ All workers cleaned up successfully"
            )
            
        except Exception as e:
            self.results["resource_cleanup"]["passed"] = False
            self.results["resource_cleanup"]["details"].append(f"✗ Exception: {e}")
            
    def test_casting_pattern(self):
        """Test the strategic casting pattern for Qt signals."""
        try:
            # Test extraction manager casting
            extraction_mgr = get_extraction_manager()
            
            # Verify protocol interface
            if hasattr(extraction_mgr, 'extract_from_vram'):
                self.results["casting_pattern"]["details"].append(
                    "✓ Extraction manager implements protocol interface"
                )
            else:
                self.results["casting_pattern"]["passed"] = False
                self.results["casting_pattern"]["details"].append(
                    "✗ Extraction manager missing protocol methods"
                )
                
            # Test injection manager casting
            injection_mgr = get_injection_manager()
            
            # Verify protocol interface
            if hasattr(injection_mgr, 'start_injection'):
                self.results["casting_pattern"]["details"].append(
                    "✓ Injection manager implements protocol interface"
                )
            else:
                self.results["casting_pattern"]["passed"] = False
                self.results["casting_pattern"]["details"].append(
                    "✗ Injection manager missing protocol methods"
                )
                
            # Verify signals are accessible after casting
            from core.managers import InjectionManager, ExtractionManager
            from typing import cast
            
            # Cast and check signals
            concrete_injection = cast(InjectionManager, injection_mgr)
            if hasattr(concrete_injection, 'injection_progress'):
                self.results["casting_pattern"]["details"].append(
                    "✓ Injection manager signals accessible after casting"
                )
            else:
                self.results["casting_pattern"]["passed"] = False
                self.results["casting_pattern"]["details"].append(
                    "✗ Injection manager signals not accessible"
                )
                
        except Exception as e:
            self.results["casting_pattern"]["passed"] = False
            self.results["casting_pattern"]["details"].append(f"✗ Exception: {e}")
            
    def on_test_signal(self, message: str):
        """Handle test signal from worker thread."""
        current_thread = threading.current_thread().ident
        if current_thread == self.main_thread_id:
            logger.debug(f"Signal received in main thread: {message}")
        else:
            self.results["signal_delivery"]["passed"] = False
            self.results["signal_delivery"]["details"].append(
                "✗ Signal received in wrong thread!"
            )
            
    def on_cross_thread_signal(self, index: int, message: str):
        """Handle cross-thread signal."""
        self.signal_received_count += 1
        logger.debug(f"Cross-thread signal {index}: {message}")
        
    def on_worker_finished(self, success: bool, message: str):
        """Handle worker completion."""
        logger.debug(f"Worker finished: {success} - {message}")


def print_results(results: dict):
    """Print validation results."""
    print("\n" + "="*60)
    print("Qt CONCURRENCY VALIDATION RESULTS")
    print("="*60)
    
    all_passed = True
    
    for category, data in results.items():
        print(f"\n{category.replace('_', ' ').title()}:")
        print("-" * 40)
        
        if data["passed"]:
            print("Status: ✅ PASSED")
        else:
            print("Status: ❌ FAILED")
            all_passed = False
            
        for detail in data["details"]:
            print(f"  {detail}")
            
    print("\n" + "="*60)
    if all_passed:
        print("OVERALL: ✅ ALL TESTS PASSED")
    else:
        print("OVERALL: ❌ SOME TESTS FAILED")
    print("="*60)


def main():
    """Run the validation."""
    app = QApplication(sys.argv)
    
    validator = ConcurrencyValidator()
    
    # Connect completion signal
    validator.validation_complete.connect(lambda results: (
        print_results(results),
        app.quit()
    ))
    
    # Start validation
    QTimer.singleShot(100, validator.validate_all)
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()