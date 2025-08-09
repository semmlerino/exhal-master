#!/usr/bin/env python3
"""
Manual Offset Dialog Performance Test

This script runs comprehensive performance analysis on the manual offset dialog
to identify bottlenecks causing black box display issues instead of proper sprites.

Usage:
    python test_manual_offset_performance.py [ROM_PATH]
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from performance_profilers.manual_offset_performance_profiler import (
    PerformanceProfiler, 
    create_performance_test_suite,
    PerformanceStage
)
from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
from core.managers.extraction_manager import ExtractionManager
from utils.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


class ManualOffsetPerformanceTest:
    """Comprehensive performance test for manual offset dialog."""
    
    def __init__(self, rom_path: str):
        self.rom_path = rom_path
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.dialog = None
        self.profiler = None
        self.results_dir = Path("performance_results")
        self.results_dir.mkdir(exist_ok=True)
        
    def setup_dialog(self) -> bool:
        """Set up the manual offset dialog with ROM data."""
        try:
            logger.info(f"Setting up manual offset dialog with ROM: {self.rom_path}")
            
            # Create extraction manager
            extraction_manager = ExtractionManager()
            extraction_manager.set_rom_path(self.rom_path)
            
            # Get ROM size
            rom_size = os.path.getsize(self.rom_path)
            logger.info(f"ROM size: {rom_size} bytes ({rom_size/1024/1024:.1f}MB)")
            
            # Create dialog
            self.dialog = UnifiedManualOffsetDialog()
            self.dialog.set_rom_data(self.rom_path, rom_size, extraction_manager)
            
            # Show dialog
            self.dialog.show()
            
            logger.info("Manual offset dialog setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up dialog: {e}")
            return False
    
    def run_comprehensive_tests(self) -> None:
        """Run all performance tests and generate reports."""
        if not self.setup_dialog():
            return
        
        logger.info("Starting comprehensive performance tests...")
        
        # Create profiler and test suite
        self.profiler, run_tests = create_performance_test_suite(self.dialog)
        
        # Connect profiler signals for real-time monitoring
        self.profiler.performance_alert.connect(self._on_performance_alert)
        self.profiler.bottleneck_detected.connect(self._on_bottleneck_detected)
        
        # Run basic performance tests
        logger.info("Phase 1: Basic slider movement tests")
        stage_stats, black_box_analysis = run_tests()
        
        # Run advanced tests
        logger.info("Phase 2: Advanced interaction tests")
        self._run_advanced_tests()
        
        # Run stress tests
        logger.info("Phase 3: Stress testing")
        self._run_stress_tests()
        
        # Generate final analysis
        final_stage_stats, final_analysis = self.profiler.stop_profiling()
        
        # Generate and save reports
        self._generate_reports(final_stage_stats, final_analysis)
        
        logger.info("Performance testing complete")
    
    def _run_advanced_tests(self) -> None:
        """Run advanced interaction scenarios."""
        logger.info("Running advanced interaction tests...")
        
        test_scenarios = [
            ("Rapid Sequential Navigation", self._test_rapid_sequential),
            ("Random Jump Navigation", self._test_random_jumps), 
            ("Boundary Testing", self._test_boundary_conditions),
            ("Cache Stress Testing", self._test_cache_stress),
            ("Memory Pressure Testing", self._test_memory_pressure)
        ]
        
        for scenario_name, test_func in test_scenarios:
            logger.info(f"Running: {scenario_name}")
            try:
                test_func()
                # Allow processing between tests
                self.app.processEvents()
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Error in {scenario_name}: {e}")
    
    def _test_rapid_sequential(self) -> None:
        """Test rapid sequential offset changes."""
        start_offset = 0x200000
        
        for i in range(50):  # 50 rapid changes
            offset = start_offset + (i * 0x800)  # 2KB steps
            if hasattr(self.dialog, 'set_offset'):
                self.dialog.set_offset(offset)
            time.sleep(0.02)  # 20ms = 50fps
    
    def _test_random_jumps(self) -> None:
        """Test random large jumps in ROM."""
        import random
        
        offsets = []
        for _ in range(20):
            offset = random.randint(0x100000, 0x3F0000)
            offset = (offset // 0x1000) * 0x1000  # Align to 4KB
            offsets.append(offset)
        
        for offset in offsets:
            if hasattr(self.dialog, 'set_offset'):
                self.dialog.set_offset(offset)
            time.sleep(0.1)  # Allow processing
    
    def _test_boundary_conditions(self) -> None:
        """Test edge cases and boundary conditions."""
        rom_size = os.path.getsize(self.rom_path)
        
        boundary_offsets = [
            0x0,  # Start of ROM
            0x8000,  # Common header boundary
            0x100000,  # 1MB mark
            rom_size // 2,  # Middle of ROM
            rom_size - 0x10000,  # Near end
            rom_size - 0x1000,  # Very near end
        ]
        
        for offset in boundary_offsets:
            if offset < rom_size:
                if hasattr(self.dialog, 'set_offset'):
                    self.dialog.set_offset(offset)
                time.sleep(0.2)
    
    def _test_cache_stress(self) -> None:
        """Test cache with many different offsets."""
        base_offset = 0x200000
        
        # Create a pattern that will stress the cache
        offsets = []
        for i in range(100):
            # Create a pattern that exceeds cache size
            offset = base_offset + (i * 0x4000)  # 16KB steps  
            offsets.append(offset)
        
        # Access them in a pattern that stresses cache replacement
        for offset in offsets:
            if hasattr(self.dialog, 'set_offset'):
                self.dialog.set_offset(offset)
            time.sleep(0.01)  # Fast access
    
    def _test_memory_pressure(self) -> None:
        """Test behavior under memory pressure."""
        # Create some memory pressure by allocating large objects
        memory_pressure_objects = []
        
        try:
            # Allocate 100MB in chunks to create pressure
            for i in range(10):
                chunk = bytearray(10 * 1024 * 1024)  # 10MB chunks
                memory_pressure_objects.append(chunk)
                
                # Test dialog under pressure
                offset = 0x200000 + (i * 0x10000)
                if hasattr(self.dialog, 'set_offset'):
                    self.dialog.set_offset(offset)
                time.sleep(0.1)
        
        finally:
            # Clean up memory pressure
            del memory_pressure_objects
    
    def _run_stress_tests(self) -> None:
        """Run stress tests to identify breaking points."""
        logger.info("Running stress tests...")
        
        # Continuous rapid updates for 30 seconds
        logger.info("Stress test: Continuous rapid updates")
        start_time = time.time()
        offset_counter = 0
        
        while time.time() - start_time < 30.0:  # 30 seconds
            offset = 0x200000 + (offset_counter * 0x100)
            offset_counter = (offset_counter + 1) % 1000  # Cycle through offsets
            
            if hasattr(self.dialog, 'set_offset'):
                self.dialog.set_offset(offset)
            
            time.sleep(0.005)  # 5ms = 200fps (very aggressive)
            
            # Process events to prevent UI freezing
            if offset_counter % 10 == 0:
                self.app.processEvents()
    
    def _on_performance_alert(self, message: str, severity: float) -> None:
        """Handle performance alerts from profiler."""
        severity_text = "HIGH" if severity > 0.8 else "MEDIUM" if severity > 0.5 else "LOW"
        logger.warning(f"PERFORMANCE ALERT [{severity_text}]: {message}")
    
    def _on_bottleneck_detected(self, stage: PerformanceStage, duration_ms: float) -> None:
        """Handle bottleneck detection from profiler."""
        logger.warning(f"BOTTLENECK DETECTED: {stage.name} took {duration_ms:.1f}ms")
    
    def _generate_reports(self, stage_stats, analysis) -> None:
        """Generate comprehensive performance reports."""
        timestamp = int(time.time())
        
        # Generate main report
        report = self.profiler.generate_report(stage_stats, analysis)
        report_file = self.results_dir / f"performance_report_{timestamp}.txt"
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Performance report saved to: {report_file}")
        
        # Export detailed data
        data_file = self.results_dir / f"performance_data_{timestamp}.json"
        self.profiler.export_detailed_data(str(data_file))
        
        # Generate summary for console output
        self._print_summary(analysis, stage_stats)
    
    def _print_summary(self, analysis, stage_stats) -> None:
        """Print performance summary to console."""
        print("\n" + "="*60)
        print("MANUAL OFFSET PERFORMANCE SUMMARY")
        print("="*60)
        
        print(f"\nROOT CAUSE ANALYSIS:")
        print(f"Likely Cause: {analysis.likely_root_cause}")
        print(f"Confidence: {analysis.confidence_score*100:.1f}%")
        
        print(f"\nKEY FINDINGS:")
        all_issues = (analysis.timing_issues + analysis.memory_issues + 
                     analysis.cache_issues + analysis.thread_issues + 
                     analysis.widget_issues)
        
        if all_issues:
            for issue in all_issues[:5]:  # Top 5 issues
                print(f"  • {issue}")
        else:
            print("  • No major performance issues detected")
        
        print(f"\nPERFORMANCE BREAKDOWN:")
        for stage, stats in stage_stats.items():
            if stats.total_events > 0:
                status = "⚠️ SLOW" if stats.p95_duration_ms > 50 else "✅ FAST"
                print(f"  {stage.name}: {stats.avg_duration_ms:.1f}ms avg, "
                      f"{stats.p95_duration_ms:.1f}ms p95 {status}")
        
        print(f"\nTOP RECOMMENDATIONS:")
        for i, rec in enumerate(analysis.recommendations[:3], 1):
            print(f"  {i}. {rec}")
        
        if analysis.confidence_score > 0.7:
            print(f"\n🎯 HIGH CONFIDENCE DIAGNOSIS:")
            print(f"   {analysis.likely_root_cause}")
        elif analysis.confidence_score > 0.4:
            print(f"\n🔍 MODERATE CONFIDENCE - Further investigation needed")
        else:
            print(f"\n❓ LOW CONFIDENCE - Multiple potential causes identified")
        
        print("="*60)
    
    def cleanup(self) -> None:
        """Clean up test resources."""
        if self.profiler:
            self.profiler.cleanup()
        
        if self.dialog:
            self.dialog.close()
            self.dialog.deleteLater()


def main():
    """Main entry point for performance testing."""
    parser = argparse.ArgumentParser(description="Manual Offset Dialog Performance Test")
    parser.add_argument("rom_path", nargs="?", 
                       help="Path to ROM file for testing")
    parser.add_argument("--quick", action="store_true",
                       help="Run quick tests only (skip stress testing)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Setup logging
    if args.debug:
        setup_logging(level="DEBUG")
    else:
        setup_logging(level="INFO")
    
    # Get ROM path
    rom_path = args.rom_path
    if not rom_path:
        # Try to find a test ROM
        test_roms = [
            "test_rom.smc",
            "test_rom.sfc", 
            "../test_data/test_rom.smc",
            "roms/test_rom.smc"
        ]
        
        for test_rom in test_roms:
            if os.path.exists(test_rom):
                rom_path = test_rom
                break
        
        if not rom_path:
            print("No ROM file specified and no test ROM found.")
            print("Usage: python test_manual_offset_performance.py ROM_PATH")
            return 1
    
    if not os.path.exists(rom_path):
        print(f"ROM file not found: {rom_path}")
        return 1
    
    logger.info(f"Starting performance test with ROM: {rom_path}")
    
    # Run tests
    test_runner = ManualOffsetPerformanceTest(rom_path)
    
    try:
        test_runner.run_comprehensive_tests()
        return 0
        
    except KeyboardInterrupt:
        logger.info("Performance testing interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Error during performance testing: {e}")
        return 1
        
    finally:
        test_runner.cleanup()


if __name__ == "__main__":
    sys.exit(main())