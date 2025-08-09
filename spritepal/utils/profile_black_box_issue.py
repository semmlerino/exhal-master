"""
Script to profile the black box issue in the manual offset dialog.

This script activates performance monitoring and provides instructions
for reproducing and analyzing the black box issue.

Usage:
1. Run this script from the SpritePal main directory
2. Follow the instructions to reproduce black boxes
3. Review the generated performance report

The script will:
- Activate timing instrumentation
- Start performance monitoring
- Show a monitoring dialog (optional)
- Generate a detailed report after testing
"""

from __future__ import annotations

import time
import sys
import os
from pathlib import Path

# Add spritepal to Python path if needed
spritepal_root = Path(__file__).parent.parent
if str(spritepal_root) not in sys.path:
    sys.path.insert(0, str(spritepal_root))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer

from utils.preview_performance_monitor import get_monitor, show_performance_monitor
from utils.timing_patches import activate_timing_instrumentation, deactivate_timing_instrumentation
from utils.logging_config import get_logger

logger = get_logger(__name__)


def analyze_black_box_issue():
    """
    Analyze the black box issue in the manual offset dialog preview system.
    
    This function sets up comprehensive timing analysis and provides
    instructions for reproducing the issue.
    """
    print("=" * 60)
    print("SpritePal Preview Performance Profiler")
    print("Black Box Issue Analysis")
    print("=" * 60)
    print()
    
    # Check if we have a QApplication
    app = QApplication.instance()
    if app is None:
        print("ERROR: No QApplication instance found.")
        print("This script should be run from within SpritePal or with Qt initialized.")
        return
    
    # Get performance monitor
    monitor = get_monitor()
    
    print("1. Activating performance monitoring...")
    monitor.start_monitoring()
    
    print("2. Performance monitoring is now active.")
    print()
    
    # Show monitoring dialog
    show_dialog = input("Show real-time monitoring dialog? (y/n): ").lower().strip()
    monitor_dialog = None
    
    if show_dialog == 'y':
        try:
            monitor_dialog = show_performance_monitor()
            print("3. Monitoring dialog opened.")
        except Exception as e:
            print(f"3. Could not open monitoring dialog: {e}")
    else:
        print("3. Monitoring dialog skipped.")
    
    print()
    print("=" * 60)
    print("BLACK BOX REPRODUCTION INSTRUCTIONS")
    print("=" * 60)
    print()
    print("To reproduce and analyze black boxes:")
    print()
    print("1. Open the Manual Offset Dialog:")
    print("   - Load a ROM in SpritePal")
    print("   - Click 'Manual Offset' or similar")
    print()
    print("2. Reproduce Black Box Issue:")
    print("   - Drag the offset slider rapidly left and right")
    print("   - Watch for black boxes appearing in the preview")
    print("   - Try different speeds and patterns")
    print()
    print("3. Monitor Performance:")
    if monitor_dialog:
        print("   - Watch the monitoring dialog for:")
        print("     * Frame budget violations (red alerts)")
        print("     * Rapid sequence detection") 
        print("     * Slow phases (yellow/orange alerts)")
        print("     * Black box event warnings")
    else:
        print("   - Performance data is being collected in background")
    print()
    print("4. Expected Issues to Look For:")
    print("   - Preview clearing faster than updates arrive")
    print("   - WIDGET_UPDATE phase taking >16ms")
    print("   - CACHE_LOOKUP misses during rapid movement")
    print("   - THREAD_HANDOFF delays between worker and main thread")
    print("   - Multiple COORDINATOR_PROCESSING requests cancelling each other")
    print()
    
    # Wait for user to complete testing
    input("Press Enter when you're done testing (or close this script)...")
    
    print()
    print("=" * 60)
    print("GENERATING PERFORMANCE REPORT")
    print("=" * 60)
    print()
    
    # Get final performance report
    try:
        print("Collecting performance data...")
        time.sleep(1)  # Let final measurements complete
        
        report = monitor.profiler.get_performance_report()
        summary = monitor.get_performance_summary()
        
        # Generate report filename
        timestamp = int(time.time())
        report_file = spritepal_root / f"black_box_analysis_{timestamp}.json"
        
        print(f"Exporting detailed data to: {report_file}")
        monitor.export_performance_data(str(report_file))
        
        # Print key findings
        print()
        print("KEY FINDINGS:")
        print("-" * 40)
        
        if summary:
            print(f"Total requests analyzed: {summary.total_requests}")
            print(f"Average response time: {summary.avg_total_time_ms:.1f}ms")
            print(f"95th percentile time: {summary.p95_total_time_ms:.1f}ms")
            print(f"Frame budget violations: {summary.frame_budget_violations}")
            print(f"Rapid sequences detected: {summary.rapid_sequences}")
            print(f"Potential black box events: {summary.potential_black_box_events}")
            print(f"Cache hit rate: {summary.cache_hit_rate:.1%}")
            print(f"Slowest phase: {summary.worst_phase} ({summary.worst_phase_time_ms:.1f}ms)")
            
            # Analysis
            print()
            print("ANALYSIS:")
            print("-" * 40)
            
            if summary.potential_black_box_events > 0:
                print(f"⚠️  BLACK BOX RISK: {summary.potential_black_box_events} events detected")
                print("   - Preview clearing happening faster than updates")
                print("   - Consider implementing preview persistence during rapid updates")
            
            if summary.p95_total_time_ms > 16.67:
                print(f"⚠️  FRAME BUDGET EXCEEDED: {summary.p95_total_time_ms:.1f}ms > 16.7ms")
                print("   - Updates taking longer than 60 FPS budget")
                print("   - Users will perceive lag and black boxes")
            
            if summary.cache_hit_rate < 0.8:
                print(f"⚠️  LOW CACHE EFFICIENCY: {summary.cache_hit_rate:.1%} hit rate")
                print("   - Cache misses causing delays during rapid movement")
                print("   - Consider preloading adjacent offsets")
            
            if summary.worst_phase_time_ms > 50:
                print(f"⚠️  BOTTLENECK DETECTED: {summary.worst_phase} phase taking {summary.worst_phase_time_ms:.1f}ms")
                if "WIDGET_UPDATE" in summary.worst_phase:
                    print("   - Qt widget updates are slow - check for blocking operations")
                elif "DATA_EXTRACTION" in summary.worst_phase:
                    print("   - ROM data extraction is slow - optimize decompression")
                elif "COORDINATOR_PROCESSING" in summary.worst_phase:
                    print("   - Preview coordinator overhead - review debouncing logic")
        else:
            print("No performance data collected - make sure you used the manual offset dialog!")
        
        # Recent alerts
        recent_alerts = monitor.get_recent_alerts(20)
        if recent_alerts:
            print()
            print("RECENT ALERTS:")
            print("-" * 40)
            for alert in recent_alerts[-10:]:  # Last 10 alerts
                timestamp = time.strftime("%H:%M:%S", time.localtime(alert['timestamp']))
                print(f"[{timestamp}] {alert['type'].upper()}: {alert['message']}")
        
        # Phase performance breakdown
        phase_perf = report.get('phase_performance', {})
        if phase_perf:
            print()
            print("PHASE PERFORMANCE BREAKDOWN:")
            print("-" * 40)
            for phase_name, metrics in phase_perf.items():
                avg_ms = metrics.get('avg_ms', 0)
                p95_ms = metrics.get('p95_ms', 0)
                count = metrics.get('count', 0)
                violations = metrics.get('frame_budget_violations', 0)
                
                status = "✅" if p95_ms <= 16.67 else ("⚠️" if p95_ms <= 50 else "❌")
                print(f"{status} {phase_name:20} | Avg: {avg_ms:6.1f}ms | P95: {p95_ms:6.1f}ms | Count: {count:4} | Violations: {violations}")
        
        print()
        print("RECOMMENDATIONS:")
        print("-" * 40)
        print()
        
        if summary and summary.potential_black_box_events > 0:
            print("1. BLACK BOX MITIGATION:")
            print("   - Don't clear preview immediately on slider change")
            print("   - Keep last valid preview visible until new data arrives")
            print("   - Add loading indicator during data fetching")
            print("   - Implement preview fade transition instead of instant clear")
            print()
        
        if summary and summary.p95_total_time_ms > 16.67:
            print("2. PERFORMANCE OPTIMIZATION:")
            print("   - Profile and optimize the slowest phase")
            print("   - Consider lower-resolution previews during dragging") 
            print("   - Implement more aggressive caching")
            print("   - Use progressive image loading")
            print()
        
        if summary and summary.cache_hit_rate < 0.8:
            print("3. CACHE IMPROVEMENTS:")
            print("   - Preload adjacent offsets predictively")
            print("   - Increase cache size for drag operations")
            print("   - Implement smarter cache eviction policies")
            print()
        
        print("4. GENERAL RECOMMENDATIONS:")
        print("   - Use QueuedConnection for all cross-thread signals")
        print("   - Batch Qt widget updates to reduce overhead")
        print("   - Consider using QTimer.singleShot(0) for main thread operations")
        print("   - Profile individual 4bpp decoding performance")
        
    except Exception as e:
        logger.exception("Error generating performance report")
        print(f"ERROR generating report: {e}")
    
    finally:
        print()
        print("Stopping performance monitoring...")
        monitor.stop_monitoring()
        
        if monitor_dialog:
            monitor_dialog.close()
        
        print("Performance analysis complete!")
        print()
        print(f"Detailed data saved to: {report_file if 'report_file' in locals() else 'export failed'}")


def main():
    """Main entry point."""
    try:
        analyze_black_box_issue()
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user.")
    except Exception as e:
        logger.exception("Error in black box analysis")
        print(f"ERROR: {e}")
    finally:
        # Ensure instrumentation is deactivated
        try:
            deactivate_timing_instrumentation()
        except:
            pass


if __name__ == "__main__":
    main()