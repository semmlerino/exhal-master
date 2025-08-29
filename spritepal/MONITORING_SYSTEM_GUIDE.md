# SpritePal Monitoring System Guide

## Overview

SpritePal's continuous monitoring system provides comprehensive observability into application performance, errors, usage patterns, and system health. This system is designed to be privacy-conscious, lightweight, and actionable.

## Features

### 1. Performance Monitoring
- **Operation Timings**: Track execution time of ROM loading, sprite extraction, thumbnail generation, and injection operations
- **Memory Usage**: Monitor memory consumption patterns and detect potential leaks
- **Bottleneck Identification**: Automatically identify performance bottlenecks and slow operations
- **Cache Effectiveness**: Track cache hit rates and performance improvements

### 2. Error Tracking
- **Comprehensive Error Capture**: Automatically capture and categorize all application errors
- **Error Fingerprinting**: Deduplicate similar errors to reduce noise
- **Context Preservation**: Maintain operation context when errors occur
- **Frequency Analysis**: Track error patterns and identify recurring issues

### 3. Usage Analytics
- **Feature Usage Tracking**: Monitor which features are used most frequently
- **Workflow Analysis**: Track multi-step user workflows and identify common patterns
- **Success Rate Monitoring**: Track operation success rates across different features
- **Usage Patterns**: Identify peak usage times and feature adoption

### 4. Health Monitoring
- **System Resources**: Monitor CPU, memory, and thread usage
- **Resource Trends**: Track resource usage over time to identify trends
- **Health Thresholds**: Configurable warning and critical thresholds
- **Automatic Health Checks**: Periodic system health assessments

### 5. Privacy & Security
- **No Personal Data**: System does not collect any personal information
- **Configurable Tracking**: All monitoring features can be enabled/disabled
- **Local Storage**: All data is stored locally on the user's machine
- **Anonymization**: File paths and sensitive data are anonymized in exports

## Quick Start

### Enable/Disable Monitoring

```python
from core.managers.registry import get_monitoring_manager

# Get monitoring manager
monitoring_manager = get_monitoring_manager()

# Check if monitoring is enabled (via settings)
from utils.settings_manager import get_settings_manager
settings = get_settings_manager()
enabled = settings.get("monitoring", "enabled", True)
```

### Basic Usage Examples

#### 1. Monitor a Function with Decorators

```python
from core.monitoring import monitor_operation, track_feature_usage

@monitor_operation("rom_loading")
def load_rom(self, rom_path: str):
    # Your ROM loading code here
    return rom_data

@track_feature_usage("sprite_gallery", "thumbnail_click")
def on_thumbnail_clicked(self, index: int):
    # Handle thumbnail click
    self.show_sprite_details(index)
```

#### 2. Monitor Operations with Context Managers

```python
from core.monitoring import monitor_performance

def extract_sprites(self, rom_data: bytes):
    with monitor_performance("sprite_extraction", {"rom_size": len(rom_data)}):
        # Extraction logic here
        sprites = self.perform_extraction(rom_data)
        return sprites
```

#### 3. Track Multi-Step Workflows

```python
from core.monitoring import WorkflowTracker

def complete_injection_workflow(self, sprites, rom_path):
    workflow = WorkflowTracker("sprite_injection")
    
    try:
        workflow.step("validate_sprites")
        self.validate_sprites(sprites)
        
        workflow.step("backup_rom")
        self.backup_rom(rom_path)
        
        workflow.step("inject_sprites")
        self.inject_sprites_to_rom(sprites, rom_path)
        
        workflow.step("verify_injection")
        self.verify_injection(rom_path)
        
        workflow.complete(success=True)
        
    except Exception as e:
        workflow.fail(str(e))
        raise
```

#### 4. Use Monitoring Mixin in UI Components

```python
from core.monitoring import MonitoringMixin
from PySide6.QtWidgets import QWidget

class SpriteGalleryWidget(QWidget, MonitoringMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_monitoring("sprite_gallery")
    
    def load_thumbnails(self):
        with self.monitor("load_thumbnails"):
            # Loading logic
            self.generate_thumbnails()
        
        # Track successful completion
        self.track_usage("thumbnails_loaded", success=True)
```

## Configuration

### Settings Structure

The monitoring system uses the following settings structure:

```python
MONITORING_SETTINGS = {
    "enabled": True,                    # Master enable/disable
    "health_check_interval_ms": 60000,  # Health check frequency
    "retention_hours": 168,             # Data retention (1 week)
    "export_format": "json",           # Default export format
    "privacy_mode": True,              # Anonymize sensitive data
    "auto_export_enabled": False,      # Automatic report generation
    
    "performance_thresholds": {
        "rom_loading_warning_ms": 2000,
        "extraction_warning_ms": 3000,
        "thumbnail_warning_ms": 1000,
        "injection_warning_ms": 2000,
        "memory_warning_mb": 500,
        "cpu_warning_percent": 50
    },
    
    "feature_tracking": {
        "track_ui_interactions": True,
        "track_workflow_patterns": True,
        "track_error_patterns": True,
        "track_performance_bottlenecks": True,
        "track_cache_effectiveness": True
    }
}
```

### Configuring Monitoring

```python
from core.managers.monitoring_settings import (
    enable_monitoring, disable_monitoring, 
    set_monitoring_privacy_mode, set_data_retention
)

# Enable/disable monitoring
enable_monitoring(settings_manager)
disable_monitoring(settings_manager)

# Configure privacy mode
set_monitoring_privacy_mode(settings_manager, enabled=True)

# Set data retention to 7 days
set_data_retention(settings_manager, hours=168)

# Configure health check interval to 30 seconds
set_health_check_interval(settings_manager, interval_seconds=30)
```

## Monitoring Dashboard

### Opening the Dashboard

```python
from ui.dialogs.monitoring_dashboard import MonitoringDashboard

# Show monitoring dashboard
dashboard = MonitoringDashboard()
dashboard.show()
```

### Dashboard Features

1. **Performance Tab**: View operation timings, success rates, and memory usage
2. **Errors Tab**: See error frequencies, top errors, and severity breakdown
3. **Usage Tab**: Analyze feature usage patterns and success rates
4. **Health Tab**: Monitor system resource usage and health trends
5. **Insights Tab**: Get actionable insights and recommendations

### Dashboard Controls

- **Time Range**: Select 1 hour, 6 hours, 24 hours, or 7 days
- **Refresh Interval**: Configure automatic refresh from 5 seconds to 5 minutes
- **Manual Refresh**: Update data immediately
- **Export Report**: Export monitoring data to JSON or CSV

## Data Export and Reporting

### Manual Export

```python
from core.managers.registry import get_monitoring_manager

monitoring_manager = get_monitoring_manager()

# Export last 24 hours to JSON
output_path = monitoring_manager.export_data("json", hours=24)
print(f"Report exported to: {output_path}")

# Export to CSV with custom path
custom_path = Path("/path/to/custom/report.csv")
monitoring_manager.export_data("csv", hours=168, output_path=custom_path)
```

### Programmatic Report Generation

```python
# Generate comprehensive report
report = monitoring_manager.generate_report(hours=24)

print(f"Report ID: {report.report_id}")
print(f"Generated at: {report.generated_at}")

# Performance summary
for operation, stats in report.performance_summary.items():
    print(f"{operation}: {stats['duration_stats']['mean_ms']:.1f}ms average")

# Error summary
if report.error_summary['total_errors'] > 0:
    print(f"Total errors: {report.error_summary['total_errors']}")

# Key insights
for insight in report.insights:
    print(f"Insight: {insight}")

# Recommendations
for rec in report.recommendations:
    print(f"Recommendation: {rec}")
```

### Automated Export

```python
from core.managers.monitoring_settings import configure_auto_export

# Enable auto-export every 24 hours
configure_auto_export(settings_manager, enabled=True, interval_hours=24)
```

## Performance Analysis

### Getting Operation Statistics

```python
# Get ROM loading performance over last week
rom_stats = monitoring_manager.get_performance_stats("rom_loading", hours=168)

if rom_stats:
    print(f"ROM Loading Performance:")
    print(f"  Average: {rom_stats['duration_stats']['mean_ms']:.1f}ms")
    print(f"  95th percentile: {rom_stats['duration_stats']['p95_ms']:.1f}ms")
    print(f"  Success rate: {rom_stats['success_rate']:.1%}")
    print(f"  Sample count: {rom_stats['sample_count']}")
```

### Identifying Bottlenecks

```python
# Get insights about performance issues
insights = monitoring_manager.generate_insights(hours=24)

for insight in insights:
    if "Performance concern" in insight:
        print(f"⚠️  {insight}")
    elif "Reliability concern" in insight:
        print(f"🔴 {insight}")
```

### Memory Analysis

```python
# Check current system health
health = monitoring_manager.get_health_status()

current = health['current']
print(f"Memory usage: {current['memory_mb']:.1f}MB")
print(f"CPU usage: {current['cpu_percent']:.1f}%")
print(f"Thread count: {current['thread_count']}")
print(f"Healthy: {current['healthy']}")

# Check trends
trends = health['trends']
for metric, trend in trends.items():
    print(f"{metric}: {trend['current']:.1f}{trend['unit']} ({trend['trend']})")
```

## Error Analysis

### Error Summary

```python
# Get error summary for last 24 hours
error_summary = monitoring_manager.get_error_summary(hours=24)

print(f"Total errors: {error_summary['total_occurrences']}")
print("\nTop error types:")
for error_type, count in error_summary['by_type'].items():
    print(f"  {error_type}: {count}")

print("\nErrors by operation:")
for operation, count in error_summary['by_operation'].items():
    print(f"  {operation}: {count}")
```

### Tracking Custom Errors

```python
# Track custom errors with context
try:
    risky_operation()
except CustomException as e:
    monitoring_manager.track_error(
        error_type="CustomException",
        error_message=str(e),
        operation="risky_operation",
        stack_trace=traceback.format_exc(),
        context={
            "user_input": user_data,
            "system_state": get_system_state()
        },
        severity="ERROR"
    )
```

## Usage Analytics

### Feature Usage Analysis

```python
# Get usage statistics
usage_stats = monitoring_manager.get_usage_stats(hours=24)

print(f"Total events: {usage_stats['total_events']}")

print("\nMost used features:")
for feature, count in usage_stats['most_used_features'].items():
    print(f"  {feature}: {count} uses")

print("\nSuccess rates:")
for feature, rate in usage_stats['success_rates'].items():
    print(f"  {feature}: {rate:.1%}")
```

### Workflow Analysis

```python
# Analyze specific workflow
workflow_analysis = monitoring_manager._usage_analytics.get_workflow_analysis("sprite_extraction")

if workflow_analysis:
    print(f"Workflow: {workflow_analysis['workflow']}")
    print(f"Total events: {workflow_analysis['total_events']}")
    print(f"Success rate: {workflow_analysis['success_rate']:.1%}")
    print(f"Recent steps: {workflow_analysis['recent_sequence']}")
```

## Best Practices

### 1. Monitoring Integration

- **Use Decorators**: Apply `@monitor_operation` to key functions for automatic monitoring
- **Context Managers**: Use `monitor_performance()` for complex operations
- **Workflow Tracking**: Use `WorkflowTracker` for multi-step processes
- **UI Integration**: Use `MonitoringMixin` for UI components

### 2. Performance Monitoring

- **Monitor Key Operations**: Focus on ROM loading, extraction, thumbnail generation, and injection
- **Include Context**: Add relevant context (file sizes, operation parameters) to metrics
- **Set Appropriate Thresholds**: Configure performance thresholds based on expected operation times
- **Regular Analysis**: Review performance data regularly to identify trends

### 3. Error Handling

- **Comprehensive Context**: Include relevant context when tracking errors
- **Appropriate Severity**: Use correct severity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Error Categories**: Group related errors by type and operation
- **Recovery Tracking**: Track error recovery attempts and success rates

### 4. Privacy Considerations

- **Enable Privacy Mode**: Always enable privacy mode in production
- **Avoid Personal Data**: Never include personal information in monitoring data
- **Anonymize Paths**: Use anonymized file paths in exports
- **User Control**: Provide users with control over monitoring features

### 5. Performance Impact

- **Minimal Overhead**: The monitoring system is designed for minimal performance impact
- **Configurable Limits**: Set appropriate limits on data retention and collection
- **Batch Operations**: Use batch operations for bulk monitoring data
- **Cleanup**: Regular cleanup of old monitoring data

## Troubleshooting

### Common Issues

#### 1. Monitoring Not Working
```python
# Check if monitoring is enabled
from utils.settings_manager import get_settings_manager
settings = get_settings_manager()
enabled = settings.get("monitoring", "enabled", True)

if not enabled:
    print("Monitoring is disabled in settings")

# Check if monitoring manager is initialized
try:
    from core.managers.registry import get_monitoring_manager
    manager = get_monitoring_manager()
    print(f"Monitoring manager initialized: {manager.is_initialized()}")
except Exception as e:
    print(f"Failed to get monitoring manager: {e}")
```

#### 2. No Data in Dashboard
```python
# Check data retention settings
retention_hours = settings.get("monitoring", "retention_hours", 168)
print(f"Data retention: {retention_hours} hours")

# Check if there's any data
usage_stats = monitoring_manager.get_usage_stats(hours=retention_hours)
print(f"Total events in retention period: {usage_stats.get('total_events', 0)}")
```

#### 3. High Memory Usage
```python
# Check monitoring data sizes
print(f"Performance metrics: {len(monitoring_manager._performance_collector.metrics)}")
print(f"Error events: {len(monitoring_manager._error_tracker.errors)}")
print(f"Usage events: {len(monitoring_manager._usage_analytics.events)}")
print(f"Health metrics: {len(monitoring_manager._health_monitor.metrics)}")

# Reduce retention if needed
set_data_retention(settings_manager, hours=72)  # 3 days instead of 7
```

#### 4. Export Issues
```python
# Check export directory permissions
from core.managers.monitoring_settings import MonitoringSettings
export_dir = MonitoringSettings.get_export_directory(settings_manager)
print(f"Export directory: {export_dir}")
print(f"Directory writable: {os.access(export_dir, os.W_OK)}")
```

### Debug Mode

Enable debug logging for monitoring components:

```python
import logging
logging.getLogger("monitoring_dashboard").setLevel(logging.DEBUG)
logging.getLogger("managers.MonitoringManager").setLevel(logging.DEBUG)
```

## API Reference

### Core Classes

- `MonitoringManager`: Main monitoring coordinator
- `PerformanceCollector`: Collects performance metrics
- `ErrorTracker`: Tracks and categorizes errors
- `UsageAnalytics`: Analyzes feature usage patterns
- `HealthMonitor`: Monitors system health
- `MonitoringDashboard`: Real-time monitoring dashboard

### Decorators and Utilities

- `@monitor_operation`: Monitor function execution
- `@track_feature_usage`: Track feature usage
- `@monitor_rom_operation`: Specialized ROM operation monitoring
- `@monitor_ui_interaction`: UI interaction tracking
- `WorkflowTracker`: Multi-step workflow tracking
- `MonitoringMixin`: Add monitoring to classes

### Settings Management

- `MonitoringSettings`: Configuration management
- `enable_monitoring()`, `disable_monitoring()`: Toggle monitoring
- `set_monitoring_privacy_mode()`: Configure privacy
- `configure_auto_export()`: Set up automatic exports

## Integration Examples

See `examples/monitoring_integration_examples.py` for comprehensive integration examples including:

- ROM extraction monitoring
- UI widget integration
- Worker thread monitoring
- Cache performance tracking
- Error handling patterns
- Performance analysis utilities

## Conclusion

The SpritePal monitoring system provides comprehensive observability while maintaining user privacy and application performance. By integrating monitoring throughout your code and regularly analyzing the collected data, you can identify performance bottlenecks, track feature usage, and maintain high application quality.

For questions or issues with the monitoring system, refer to the test files in `tests/test_monitoring_system.py` for detailed usage examples and edge case handling.