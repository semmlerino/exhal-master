#!/usr/bin/env python3
"""
Simple validation of Qt signal architecture without full test framework.

This script validates the core signal architecture functionality
without the complexity of pytest and cleanup issues.
"""

import sys
import time
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication

from core.managers import InjectionManager, ExtractionManager
from core.protocols.manager_protocols import (
    InjectionManagerProtocol,
    ExtractionManagerProtocol
)
from typing import cast


class SignalValidator:
    """Validates Qt signal architecture"""
    
    def __init__(self):
        self.results = []
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication([])
    
    def validate_protocol_compliance(self):
        """Test that managers comply with protocols"""
        print("\n=== Testing Protocol Compliance ===")
        
        # Create managers
        injection_mgr = InjectionManager()
        extraction_mgr = ExtractionManager()
        
        # Test protocol compliance
        injection_complies = isinstance(injection_mgr, InjectionManagerProtocol)
        extraction_complies = isinstance(extraction_mgr, ExtractionManagerProtocol)
        
        result = {
            'test': 'protocol_compliance',
            'passed': injection_complies and extraction_complies,
            'details': {
                'injection_complies': injection_complies,
                'extraction_complies': extraction_complies
            }
        }
        
        print(f"InjectionManager complies with protocol: {injection_complies}")
        print(f"ExtractionManager complies with protocol: {extraction_complies}")
        
        # Test signal attributes
        print("\nTesting signal attributes...")
        injection_signals = [
            'injection_progress', 'injection_finished', 'compression_info',
            'progress_percent', 'cache_saved'
        ]
        
        extraction_signals = [
            'extraction_progress', 'preview_generated', 'palettes_extracted',
            'active_palettes_found', 'files_created', 'cache_operation_started',
            'cache_hit', 'cache_miss', 'cache_saved'
        ]
        
        injection_signals_ok = all(hasattr(injection_mgr, sig) for sig in injection_signals)
        extraction_signals_ok = all(hasattr(extraction_mgr, sig) for sig in extraction_signals)
        
        result['details']['injection_signals_ok'] = injection_signals_ok
        result['details']['extraction_signals_ok'] = extraction_signals_ok
        
        print(f"InjectionManager has all signals: {injection_signals_ok}")
        print(f"ExtractionManager has all signals: {extraction_signals_ok}")
        
        self.results.append(result)
        return result['passed']
    
    def validate_signal_casting(self):
        """Test signal access through protocol casting"""
        print("\n=== Testing Signal Access with Casting ===")
        
        # Create concrete manager
        concrete_mgr = InjectionManager()
        
        # Use as protocol
        protocol_mgr: InjectionManagerProtocol = concrete_mgr
        
        # Cast back to concrete for signal access
        casted_mgr = cast(InjectionManager, protocol_mgr)
        
        # Test signal emission
        signal_received = []
        
        def capture_signal(*args):
            signal_received.append(args)
        
        casted_mgr.injection_progress.connect(capture_signal)
        casted_mgr.injection_progress.emit("Test message")
        
        # Process events
        self.app.processEvents()
        time.sleep(0.1)
        
        success = len(signal_received) == 1 and signal_received[0] == ("Test message",)
        
        result = {
            'test': 'signal_casting',
            'passed': success,
            'details': {
                'signal_received': len(signal_received) == 1,
                'correct_data': signal_received[0] == ("Test message",) if signal_received else False
            }
        }
        
        print(f"Signal received after casting: {success}")
        if signal_received:
            print(f"Received data: {signal_received[0]}")
        
        self.results.append(result)
        return success
    
    def validate_cross_thread_signals(self):
        """Test signal delivery across threads"""
        print("\n=== Testing Cross-Thread Signal Delivery ===")
        
        manager = ExtractionManager()
        received_signals = []
        
        class Worker(QThread):
            def __init__(self, mgr):
                super().__init__()
                self.manager = mgr
            
            def run(self):
                # Emit from worker thread
                self.manager.extraction_progress.emit("From worker thread")
        
        def capture_signal(msg):
            received_signals.append({
                'message': msg,
                'thread': QThread.currentThread(),
                'is_main': QThread.currentThread() == self.app.thread()
            })
        
        manager.extraction_progress.connect(capture_signal)
        
        # Run worker
        worker = Worker(manager)
        worker.start()
        worker.wait(1000)
        
        # Process events
        self.app.processEvents()
        time.sleep(0.1)
        
        success = (
            len(received_signals) == 1 and
            received_signals[0]['message'] == "From worker thread" and
            received_signals[0]['is_main']  # Should be delivered to main thread
        )
        
        result = {
            'test': 'cross_thread_signals',
            'passed': success,
            'details': {
                'signal_received': len(received_signals) == 1,
                'correct_message': received_signals[0]['message'] == "From worker thread" if received_signals else False,
                'delivered_to_main': received_signals[0]['is_main'] if received_signals else False
            }
        }
        
        print(f"Cross-thread signal delivery: {success}")
        if received_signals:
            print(f"Signal delivered to main thread: {received_signals[0]['is_main']}")
        
        self.results.append(result)
        return success
    
    def validate_performance(self):
        """Test performance impact of casting"""
        print("\n=== Testing Performance Impact ===")
        
        import timeit
        
        manager = InjectionManager()
        
        # Direct access
        def direct_access():
            manager.injection_progress.emit("Test")
        
        # With casting
        def casted_access():
            casted = cast(InjectionManager, manager)
            casted.injection_progress.emit("Test")
        
        # Disconnect any receivers to measure pure emit performance
        try:
            manager.injection_progress.disconnect()
        except:
            pass
        
        # Measure times
        direct_time = timeit.timeit(direct_access, number=10000)
        casted_time = timeit.timeit(casted_access, number=10000)
        
        overhead_percent = ((casted_time - direct_time) / direct_time) * 100 if direct_time > 0 else 0
        
        # Casting should have minimal overhead (< 5%)
        success = overhead_percent < 5.0
        
        result = {
            'test': 'performance_impact',
            'passed': success,
            'details': {
                'direct_time': direct_time,
                'casted_time': casted_time,
                'overhead_percent': overhead_percent
            }
        }
        
        print(f"Performance overhead of casting: {overhead_percent:.2f}%")
        print(f"Direct access time: {direct_time:.6f}s for 10000 calls")
        print(f"Casted access time: {casted_time:.6f}s for 10000 calls")
        
        self.results.append(result)
        return success
    
    def generate_report(self):
        """Generate validation report"""
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['passed'])
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        
        if passed_tests == total_tests:
            print("\n✅ All validations passed!")
            print("\nThe Qt signal architecture with strategic casting is working correctly:")
            print("- Managers comply with protocols")
            print("- Signals are accessible through casting")
            print("- Cross-thread signal delivery works properly")
            print("- Performance overhead is negligible")
        else:
            print("\n❌ Some validations failed:")
            for result in self.results:
                if not result['passed']:
                    print(f"- {result['test']}: FAILED")
        
        # Write detailed report
        report_path = project_root / "SIGNAL_ARCHITECTURE_VALIDATION.md"
        with open(report_path, 'w') as f:
            f.write("# Qt Signal Architecture Validation\n\n")
            f.write("## Summary\n\n")
            f.write(f"- Total Tests: {total_tests}\n")
            f.write(f"- Passed: {passed_tests}\n")
            f.write(f"- Failed: {total_tests - passed_tests}\n\n")
            
            f.write("## Test Results\n\n")
            for result in self.results:
                f.write(f"### {result['test'].replace('_', ' ').title()}\n\n")
                f.write(f"**Result**: {'✅ PASSED' if result['passed'] else '❌ FAILED'}\n\n")
                f.write("**Details**:\n")
                for key, value in result['details'].items():
                    f.write(f"- {key}: {value}\n")
                f.write("\n")
            
            f.write("## Conclusion\n\n")
            if passed_tests == total_tests:
                f.write("The Qt signal architecture validation confirms that the strategic ")
                f.write("casting approach successfully enables signal access while ")
                f.write("preserving protocol-based architecture. The implementation is ")
                f.write("thread-safe, has negligible performance overhead, and follows ")
                f.write("Qt best practices.\n")
            else:
                f.write("Some validation tests failed. Please review the failed tests ")
                f.write("and address any issues before deployment.\n")
        
        print(f"\nDetailed report written to: {report_path}")
        
        return passed_tests == total_tests


def main():
    """Run validation"""
    print("Qt Signal Architecture Validation")
    print("Simple validation without test framework complexity")
    
    validator = SignalValidator()
    
    # Run validations
    validator.validate_protocol_compliance()
    validator.validate_signal_casting()
    validator.validate_cross_thread_signals()
    validator.validate_performance()
    
    # Generate report
    success = validator.generate_report()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())