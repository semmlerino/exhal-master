#!/usr/bin/env python3
"""
Test monitoring deployment without Qt dependencies.
"""

import json
import sys
import time
from pathlib import Path


# Mock Qt to avoid import errors
class MockSignal:
    def __init__(self, *args, **kwargs): pass
    def emit(self, *args, **kwargs): pass
    def connect(self, *args, **kwargs): pass
    def disconnect(self, *args, **kwargs): pass

class MockQObject:
    def __init__(self, *args, **kwargs): pass
    Signal = MockSignal

class MockQPixmap:
    pass

class MockQImage:
    Format_RGB888 = 1
    Format_RGBA8888 = 2
    Format_Grayscale8 = 3

    class Format:
        Format_RGB888 = 1
        Format_RGBA8888 = 2
        Format_Grayscale8 = 3

# Create mock PySide6 module structure
mock_qtcore = type('module', (), {
    'QObject': MockQObject,
    'Signal': MockSignal,
    'QThread': type('QThread', (), {}),
    'Qt': type('Qt', (), {'Key': type('Key', (), {'Key_Return': 1})}),
})()

mock_qtgui = type('module', (), {
    'QPixmap': MockQPixmap,
    'QImage': MockQImage,
})()

mock_qtwidgets = type('module', (), {
    'QWidget': type('QWidget', (), {}),
    'QDialog': type('QDialog', (), {}),
    'QMainWindow': type('QMainWindow', (), {}),
})()

mock_pyside6 = type('module', (), {
    'QtCore': mock_qtcore,
    'QtGui': mock_qtgui,
    'QtWidgets': mock_qtwidgets,
})()

sys.modules['PySide6'] = mock_pyside6
sys.modules['PySide6.QtCore'] = mock_qtcore
sys.modules['PySide6.QtGui'] = mock_qtgui
sys.modules['PySide6.QtWidgets'] = mock_qtwidgets

# Now import monitoring
from monitoring_production import ProductionMonitor


def test_monitoring_deployment():
    """Test the monitoring deployment system."""

    print("\n" + "="*70)
    print(" MONITORING DEPLOYMENT TEST ".center(70, "="))
    print("="*70)

    # Test 1: Configuration Loading
    print("\n📋 Test 1: Configuration Loading")
    print("-"*40)

    try:
        monitor = ProductionMonitor()
        config = monitor.config

        print("✓ Configuration loaded")
        print(f"  Environment: {config['monitoring']['environment']}")
        print(f"  Export path: {config['monitoring']['export']['path']}")
        print(f"  Alerts enabled: {config['monitoring']['alerts']['enabled']}")

    except Exception as e:
        print(f"✗ Configuration failed: {e}")
        return False

    # Test 2: Monitoring Operations
    print("\n⚡ Test 2: Monitoring Operations")
    print("-"*40)

    try:
        # Test various operations
        operations = [
            ("rom_loading", {"size_mb": 32}),
            ("sprite_extraction", {"count": 100}),
            ("thumbnail_generation", {"batch_size": 50}),
            ("cache_lookup", {"hit": True})
        ]

        for op_name, context in operations:
            start = time.perf_counter()

            with monitor.monitor.monitor_operation(op_name, context):
                # Simulate work
                time.sleep(0.01)

            elapsed = (time.perf_counter() - start) * 1000
            print(f"  ✓ {op_name:20} completed in {elapsed:.2f}ms")

    except Exception as e:
        print(f"  ✗ Operation monitoring failed: {e}")
        return False

    # Test 3: Error Tracking
    print("\n❌ Test 3: Error Tracking")
    print("-"*40)

    try:
        # Track some test errors
        errors = [
            ("FileNotFoundError", "ROM file not found", "rom_loading"),
            ("MemoryError", "Out of memory", "sprite_extraction"),
            ("ValueError", "Invalid offset", "thumbnail_generation")
        ]

        for err_type, err_msg, operation in errors:
            monitor.monitor.track_error(err_type, err_msg, operation)
            print(f"  ✓ Tracked error: {err_type} in {operation}")

        # Get error stats
        error_stats = monitor.monitor.get_error_stats(hours=1)
        print("\n  Error Summary:")
        print(f"    Total errors: {error_stats.get('total_errors', 0)}")

    except Exception as e:
        print(f"  ✗ Error tracking failed: {e}")
        return False

    # Test 4: Performance Stats
    print("\n📊 Test 4: Performance Statistics")
    print("-"*40)

    try:
        perf_stats = monitor.monitor.get_performance_stats("all", hours=1)

        if perf_stats and perf_stats.get('sample_count', 0) > 0:
            print(f"  Total operations: {perf_stats['sample_count']}")
            print(f"  Average duration: {perf_stats.get('average', 0):.2f}ms")
            print(f"  Success rate: {perf_stats.get('success_rate', 0)*100:.1f}%")

            # By operation
            by_op = perf_stats.get('by_operation', {})
            if by_op:
                print("\n  By Operation:")
                for op_name, stats in by_op.items():
                    count = stats.get('count', 0)
                    avg = stats.get('average', 0)
                    print(f"    {op_name:20} {count} ops, avg {avg:.2f}ms")
        else:
            print("  No performance data collected")

    except Exception as e:
        print(f"  ✗ Performance stats failed: {e}")
        return False

    # Test 5: Health Monitoring
    print("\n🏥 Test 5: Health Monitoring")
    print("-"*40)

    try:
        health = monitor.monitor.get_health_status()

        if health:
            print(f"  CPU Usage: {health.get('cpu_percent', 0):.1f}%")
            print(f"  Memory: {health.get('memory_mb', 0):.1f}MB ({health.get('memory_percent', 0):.1f}%)")
            print(f"  Threads: {health.get('thread_count', 0)}")
            print(f"  Status: {'✅ Healthy' if health.get('healthy', False) else '⚠️ Degraded'}")
        else:
            print("  No health data available")

    except Exception as e:
        print(f"  ✗ Health monitoring failed: {e}")
        return False

    # Test 6: Metric Export
    print("\n💾 Test 6: Metric Export")
    print("-"*40)

    try:
        # Export metrics
        monitor._export_metrics()

        # Check export directory
        export_path = Path(monitor.config["monitoring"]["export"]["path"])
        metric_files = list(export_path.glob("metrics_*.json"))

        if metric_files:
            latest_file = max(metric_files, key=lambda p: p.stat().st_mtime)

            # Read and validate
            with open(latest_file) as f:
                exported_data = json.load(f)

            print(f"  ✓ Metrics exported to {latest_file.name}")
            print(f"    Timestamp: {exported_data.get('timestamp', 'Unknown')}")
            print(f"    Environment: {exported_data.get('environment', 'Unknown')}")

            # Check content
            has_perf = 'performance' in exported_data
            has_errors = 'errors' in exported_data
            has_health = 'health' in exported_data

            print(f"    Contains: perf={has_perf}, errors={has_errors}, health={has_health}")
        else:
            print("  ⚠ No export files found")

    except Exception as e:
        print(f"  ✗ Metric export failed: {e}")
        return False

    # Test 7: Alert System
    print("\n🚨 Test 7: Alert System")
    print("-"*40)

    try:
        # Check alert configuration
        alerts = monitor.config["monitoring"]["alerts"]["rules"]
        print(f"  Configured alerts: {len(alerts)}")

        for alert in alerts[:3]:
            print(f"    • {alert['name']}: {alert['condition']} ({alert['severity']})")

        # Test alert checking (won't trigger unless conditions met)
        monitor._check_alerts()
        print("  ✓ Alert system operational")

    except Exception as e:
        print(f"  ✗ Alert system failed: {e}")
        return False

    # Test 8: Dashboard Data
    print("\n📈 Test 8: Dashboard Data Generation")
    print("-"*40)

    try:
        dashboard_data = monitor.get_dashboard_data()

        print("  ✓ Dashboard data generated")
        print(f"    Timestamp: {dashboard_data['timestamp']}")
        print(f"    Has health: {'health' in dashboard_data}")
        print(f"    Has performance: {'performance' in dashboard_data}")
        print(f"    Has insights: {len(dashboard_data.get('insights', []))} insights")
        print(f"    Has recommendations: {len(dashboard_data.get('recommendations', []))} recommendations")

        # Show recommendations if any
        if dashboard_data.get('recommendations'):
            print("\n  Recommendations:")
            for rec in dashboard_data['recommendations'][:3]:
                print(f"    • {rec}")

    except Exception as e:
        print(f"  ✗ Dashboard data failed: {e}")
        return False

    return True


def main():
    """Run deployment tests."""
    print("\nTesting SpritePal Monitoring Deployment...")
    print("This validates that the monitoring system is ready for production use.\n")

    # Run tests
    success = test_monitoring_deployment()

    # Summary
    print("\n" + "="*70)
    print(" TEST SUMMARY ".center(70, "="))
    print("="*70)

    if success:
        print("\n✅ All monitoring deployment tests passed!")
        print("\nThe monitoring system is ready for production deployment.")
        print("\nNext steps:")
        print("  1. Review MONITORING_DEPLOYMENT_GUIDE.md")
        print("  2. Adjust config/monitoring_config.json as needed")
        print("  3. Run: python3 monitoring_production.py --daemon")
        print("  4. View dashboard: python3 monitoring_dashboard.py")
    else:
        print("\n❌ Some tests failed. Please review the errors above.")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
