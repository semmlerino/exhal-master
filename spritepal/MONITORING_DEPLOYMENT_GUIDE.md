# SpritePal Monitoring Deployment Guide

## Overview

This guide covers the deployment and configuration of SpritePal's comprehensive monitoring system in production environments. The monitoring system provides real-time performance metrics, error tracking, usage analytics, and system health monitoring with less than 1% overhead.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [Deployment](#deployment)
5. [Dashboard Usage](#dashboard-usage)
6. [Alerting](#alerting)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

## Quick Start

### 1. Basic Setup

```bash
# Navigate to SpritePal directory
cd /path/to/spritepal

# Check monitoring status
python monitoring_production.py --status

# Start monitoring daemon
python monitoring_production.py --daemon

# View real-time dashboard
python monitoring_dashboard.py
```

### 2. Integration with Application

```python
from core.managers.monitoring_manager import MonitoringManager

# Initialize monitoring
monitor = MonitoringManager()

# Monitor an operation
with monitor.monitor_operation("sprite_extraction", {"rom": "game.sfc"}):
    # Your operation code here
    extract_sprites()

# Track errors
monitor.track_error("ExtractionError", str(e), "sprite_extraction")

# Track feature usage
monitor.track_feature_usage("batch_extraction", "completed", success=True)
```

## Architecture

### Components

1. **MonitoringManager**: Core monitoring engine
   - Performance collection
   - Error tracking
   - Usage analytics
   - Health monitoring

2. **ProductionMonitor**: Production orchestrator
   - Configuration management
   - Metric export
   - Alert system
   - Report generation

3. **MonitoringDashboard**: Real-time visualization
   - Interactive terminal UI
   - Multiple view modes
   - Live metric updates

### Data Flow

```
Application Code
     ↓
MonitoringManager (collects metrics)
     ↓
ProductionMonitor (processes & exports)
     ↓
┌─────────────┬──────────────┬─────────────┐
│  Dashboard  │  Export Files │   Alerts    │
│  (Real-time)│  (Historical) │  (Actions)  │
└─────────────┴──────────────┴─────────────┘
```

## Configuration

### Configuration File: `config/monitoring_config.json`

```json
{
  "monitoring": {
    "enabled": true,
    "environment": "production",
    "health_check_interval_ms": 60000,
    "export_format": "json",
    "retention_hours": 168,
    "thresholds": {
      "cpu_percent": {
        "warning": 50.0,
        "critical": 80.0
      },
      "memory_mb": {
        "warning": 500.0,
        "critical": 1000.0
      }
    },
    "sampling": {
      "performance_sample_rate": 1.0,
      "error_sample_rate": 1.0
    },
    "export": {
      "enabled": true,
      "path": "./monitoring_data",
      "rotation": {
        "enabled": true,
        "max_files": 7,
        "max_size_mb": 100
      }
    },
    "alerts": {
      "enabled": true,
      "channels": ["log", "file"],
      "rules": [
        {
          "name": "high_memory_usage",
          "condition": "memory_percent > 30",
          "severity": "warning",
          "cooldown_minutes": 15
        }
      ]
    }
  }
}
```

### Key Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `enabled` | Enable/disable monitoring | `true` |
| `health_check_interval_ms` | Health check frequency | `60000` (1 min) |
| `retention_hours` | Data retention period | `168` (1 week) |
| `export.path` | Metric export directory | `./monitoring_data` |
| `export.rotation.max_files` | Max export files to keep | `7` |
| `alerts.rules` | Alert condition rules | See config |

## Deployment

### 1. Development Environment

```bash
# Quick monitoring check
python monitoring_production.py --status

# Export current metrics
python monitoring_production.py --export
```

### 2. Production Environment

#### Systemd Service (Linux)

Create `/etc/systemd/system/spritepal-monitoring.service`:

```ini
[Unit]
Description=SpritePal Monitoring Service
After=network.target

[Service]
Type=simple
User=spritepal
WorkingDirectory=/opt/spritepal
ExecStart=/usr/bin/python3 /opt/spritepal/monitoring_production.py --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable spritepal-monitoring
sudo systemctl start spritepal-monitoring
sudo systemctl status spritepal-monitoring
```

#### Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt

CMD ["python", "monitoring_production.py", "--daemon"]
```

### 3. Integration Points

#### Application Startup

```python
# In your main application file
from monitoring_production import ProductionMonitor

# Initialize monitoring at startup
monitor = ProductionMonitor()

# Application code...
```

#### Critical Operations

```python
# Wrap critical operations
with monitor.monitor_operation("rom_loading", {"size_mb": rom_size}):
    rom_data = load_rom(rom_path)

# Track success/failure
try:
    result = process_sprites()
    monitor.track_feature_usage("sprite_processing", "success")
except Exception as e:
    monitor.track_error(type(e).__name__, str(e), "sprite_processing")
    raise
```

## Dashboard Usage

### Starting the Dashboard

```bash
# Default view (overview)
python monitoring_dashboard.py

# Start with specific view
python monitoring_dashboard.py -m performance

# Custom refresh interval (seconds)
python monitoring_dashboard.py -r 10
```

### Dashboard Commands

| Key | Action |
|-----|--------|
| `O` | Overview mode |
| `P` | Performance details |
| `E` | Error analysis |
| `H` | Health metrics |
| `R` | Force refresh |
| `Q` | Quit dashboard |
| `1-5` | Set refresh interval |

### View Modes

#### Overview Mode
- System health summary
- Performance highlights
- Recent errors
- Usage statistics

#### Performance Mode
- Detailed timing statistics
- Operation breakdown
- Memory impact analysis
- Percentile distributions

#### Error Mode
- Error categorization
- Severity breakdown
- Top error patterns
- Error trends

#### Health Mode
- Resource utilization
- Trend analysis
- Cache effectiveness
- System insights

## Alerting

### Alert Configuration

Alerts are configured in `monitoring_config.json`:

```json
{
  "alerts": {
    "rules": [
      {
        "name": "high_cpu_usage",
        "condition": "cpu_percent > 75",
        "severity": "warning",
        "cooldown_minutes": 30
      },
      {
        "name": "memory_leak_suspected",
        "condition": "memory_trend == 'increasing' && memory_percent > 25",
        "severity": "critical",
        "cooldown_minutes": 15
      }
    ]
  }
}
```

### Alert Channels

1. **Log Channel**: Writes to console/system logs
2. **File Channel**: Appends to `monitoring_data/alerts.log`
3. **Custom Channels**: Extend `ProductionMonitor._trigger_alert()`

### Alert Response

When an alert triggers:

1. Check `monitoring_data/alerts.log` for details
2. Review dashboard for current metrics
3. Export detailed metrics: `python monitoring_production.py --export`
4. Analyze trends in exported JSON files

## Troubleshooting

### Common Issues

#### 1. High Memory Usage Alert

**Symptoms**: Memory usage > 30% warnings

**Solutions**:
- Check for memory leaks in sprite processing
- Verify cache size limits are configured
- Review thumbnail generation batch sizes

```python
# Check current memory state
python -c "from monitoring_production import ProductionMonitor; m = ProductionMonitor(); m.print_status()"
```

#### 2. Performance Degradation

**Symptoms**: P95 latency increasing

**Solutions**:
- Review slow operations in performance view
- Check disk I/O patterns
- Verify parallel processing is working

```bash
# View detailed performance metrics
python monitoring_dashboard.py -m performance
```

#### 3. Error Rate Spike

**Symptoms**: Sudden increase in errors

**Solutions**:
- Check error dashboard for patterns
- Review recent code changes
- Verify external dependencies

```bash
# Analyze error patterns
python monitoring_dashboard.py -m errors
```

### Debug Commands

```bash
# Check monitoring system health
python -c "from core.managers.monitoring_manager import MonitoringManager; m = MonitoringManager(); m._initialize(); print(m.get_health_status())"

# Export all metrics immediately
python monitoring_production.py --export

# View raw metric files
ls -la monitoring_data/metrics_*.json

# Tail alert log
tail -f monitoring_data/alerts.log
```

## Best Practices

### 1. Metric Collection

✅ **DO:**
- Wrap all I/O operations with monitoring
- Track both success and failure paths
- Include relevant context in operations
- Use consistent operation names

❌ **DON'T:**
- Monitor trivial operations (< 1ms)
- Include sensitive data in context
- Create unbounded metric cardinality
- Ignore monitoring overhead

### 2. Performance Optimization

- **Batch Operations**: Monitor batches, not individual items
- **Sampling**: Use sampling for high-frequency operations
- **Async Export**: Metrics export runs in background thread
- **Rotation**: Configure automatic cleanup of old data

### 3. Alert Configuration

- **Meaningful Thresholds**: Base on baseline measurements
- **Cooldown Periods**: Prevent alert fatigue
- **Severity Levels**: Use appropriate severity
- **Actionable Alerts**: Each alert should have clear response

### 4. Production Deployment

1. **Start Small**: Deploy with monitoring disabled, enable gradually
2. **Baseline First**: Collect baseline metrics before setting alerts
3. **Regular Review**: Weekly review of metrics and alerts
4. **Capacity Planning**: Use trends for resource planning

### 5. Monitoring the Monitor

```python
# Self-check script
import psutil
import os

# Check monitor process
for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
    if 'monitoring' in proc.info['name']:
        print(f"Monitor PID: {proc.info['pid']}")
        print(f"Memory: {proc.info['memory_percent']:.2f}%")
```

## Performance Impact

The monitoring system is designed for minimal overhead:

| Component | Overhead |
|-----------|----------|
| Metric Collection | < 0.1% CPU |
| Health Checks | < 0.2% CPU (1/min) |
| Memory Usage | < 10MB |
| Disk I/O | < 100KB/min |
| **Total Impact** | **< 1%** |

## Metrics Exported

### Performance Metrics
- Operation count and duration
- Success/failure rates
- Percentile distributions (P50, P75, P90, P95, P99)
- Memory delta per operation

### Error Metrics
- Error counts by type
- Error frequency patterns
- Stack trace fingerprints
- Operation correlation

### Usage Metrics
- Feature utilization
- User workflows
- Success patterns
- Duration analysis

### Health Metrics
- CPU utilization
- Memory usage (RSS, percentage)
- Thread count
- File descriptors
- Cache hit rates

## Advanced Topics

### Custom Metrics

```python
# Add custom metric collector
class CustomCollector:
    def collect(self):
        return {
            "custom_metric": calculate_value(),
            "timestamp": datetime.now()
        }

# Register with monitor
monitor._custom_collectors.append(CustomCollector())
```

### Export to External Systems

```python
# Export to Prometheus
def export_to_prometheus():
    metrics = monitor.get_all_metrics()
    # Convert to Prometheus format
    # Push to gateway

# Export to CloudWatch
def export_to_cloudwatch():
    metrics = monitor.get_all_metrics()
    # Send to CloudWatch API
```

### Distributed Tracing

```python
# Add trace context
with monitor.monitor_operation("distributed_op", 
                              {"trace_id": trace_id, 
                               "span_id": span_id}):
    perform_operation()
```

## Support

For issues or questions:

1. Check exported metrics in `monitoring_data/`
2. Review alert log for patterns
3. Use dashboard for real-time diagnosis
4. Enable debug logging if needed

## Conclusion

The SpritePal monitoring system provides comprehensive observability with minimal overhead. Proper configuration and deployment ensures optimal performance tracking, early problem detection, and data-driven optimization opportunities.

Remember: Good monitoring is invisible when everything works, invaluable when it doesn't.