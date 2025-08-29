#!/usr/bin/env python3
"""
Production Monitoring Integration for SpritePal

This module integrates the monitoring system into the production environment,
providing automated metric collection, alerting, and reporting.
"""

import json
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.managers.monitoring_manager import MonitoringManager


class ProductionMonitor:
    """Production monitoring orchestrator for SpritePal."""
    
    def __init__(self, config_path: Path = None):
        """Initialize production monitoring with configuration."""
        self.config_path = config_path or Path("config/monitoring_config.json")
        self.config = self._load_config()
        self.monitor = MonitoringManager()
        self.alert_cooldowns = {}
        self.export_path = Path(self.config["monitoring"]["export"]["path"])
        self.export_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self._setup_monitoring()
        self._setup_export()
        self._setup_alerts()
        
    def _load_config(self) -> dict:
        """Load monitoring configuration."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                return json.load(f)
        else:
            # Default configuration
            return {
                "monitoring": {
                    "enabled": True,
                    "environment": "production",
                    "health_check_interval_ms": 60000,
                    "export": {
                        "enabled": True,
                        "path": "./monitoring_data"
                    },
                    "alerts": {
                        "enabled": True,
                        "rules": []
                    }
                }
            }
    
    def _setup_monitoring(self):
        """Configure monitoring based on settings."""
        if not self.config["monitoring"]["enabled"]:
            print("Monitoring disabled by configuration")
            return
            
        # Initialize monitoring manager
        self.monitor._initialize()
        print(f"✓ Monitoring initialized for {self.config['monitoring']['environment']} environment")
        
    def _setup_export(self):
        """Set up metric export."""
        if not self.config["monitoring"]["export"]["enabled"]:
            return
            
        # Start export thread
        export_thread = threading.Thread(target=self._export_metrics_loop, daemon=True)
        export_thread.start()
        print("✓ Metric export configured")
        
    def _setup_alerts(self):
        """Set up alerting system."""
        if not self.config["monitoring"]["alerts"]["enabled"]:
            return
            
        # Start alert checking thread
        alert_thread = threading.Thread(target=self._check_alerts_loop, daemon=True)
        alert_thread.start()
        print("✓ Alert system configured")
    
    def _export_metrics_loop(self):
        """Continuously export metrics to files."""
        while True:
            try:
                time.sleep(300)  # Export every 5 minutes
                self._export_metrics()
            except Exception as e:
                print(f"Export error: {e}")
    
    def _export_metrics(self):
        """Export current metrics to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Collect all metrics
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "environment": self.config["monitoring"]["environment"],
            "performance": self.monitor.get_performance_stats("all", hours=1),
            "errors": self.monitor.get_error_stats(hours=1),
            "usage": self.monitor.get_usage_stats(hours=1),
            "health": self.monitor.get_health_status()
        }
        
        # Write to timestamped file
        export_file = self.export_path / f"metrics_{timestamp}.json"
        with open(export_file, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)
        
        # Rotate old files if needed
        self._rotate_export_files()
        
    def _rotate_export_files(self):
        """Remove old export files based on rotation policy."""
        rotation = self.config["monitoring"]["export"].get("rotation", {})
        if not rotation.get("enabled", False):
            return
            
        max_files = rotation.get("max_files", 7)
        max_size_mb = rotation.get("max_size_mb", 100)
        
        # Get all metric files
        metric_files = sorted(self.export_path.glob("metrics_*.json"))
        
        # Remove excess files
        if len(metric_files) > max_files:
            for old_file in metric_files[:-max_files]:
                old_file.unlink()
        
        # Check total size
        total_size = sum(f.stat().st_size for f in metric_files) / (1024 * 1024)
        if total_size > max_size_mb:
            # Remove oldest files until under limit
            for old_file in metric_files:
                if total_size <= max_size_mb:
                    break
                size_mb = old_file.stat().st_size / (1024 * 1024)
                old_file.unlink()
                total_size -= size_mb
    
    def _check_alerts_loop(self):
        """Continuously check for alert conditions."""
        while True:
            try:
                time.sleep(60)  # Check every minute
                self._check_alerts()
            except Exception as e:
                print(f"Alert check error: {e}")
    
    def _check_alerts(self):
        """Check all alert rules and trigger if needed."""
        for rule in self.config["monitoring"]["alerts"]["rules"]:
            if self._should_trigger_alert(rule):
                self._trigger_alert(rule)
    
    def _should_trigger_alert(self, rule: dict) -> bool:
        """Check if an alert rule should trigger."""
        # Check cooldown
        rule_name = rule["name"]
        if rule_name in self.alert_cooldowns:
            if datetime.now() < self.alert_cooldowns[rule_name]:
                return False
        
        # Evaluate condition
        condition = rule["condition"]
        
        # Get current metrics
        health = self.monitor.get_health_status()
        perf_stats = self.monitor.get_performance_stats("all", hours=1)
        error_stats = self.monitor.get_error_stats(hours=1)
        
        # Simple condition evaluation (extend as needed)
        if "memory_percent" in condition:
            current_memory = health.get("memory_percent", 0)
            threshold = float(condition.split(">")[1].strip())
            return current_memory > threshold
            
        elif "error_rate" in condition:
            total_ops = perf_stats.get("sample_count", 1)
            total_errors = error_stats.get("total_errors", 0)
            error_rate = total_errors / max(total_ops, 1)
            threshold = float(condition.split(">")[1].strip())
            return error_rate > threshold
            
        elif "p95_duration" in condition:
            p95 = perf_stats.get("percentiles", {}).get("p95", 0)
            threshold = float(condition.split(">")[1].strip())
            return p95 > threshold
            
        return False
    
    def _trigger_alert(self, rule: dict):
        """Trigger an alert based on the rule."""
        rule_name = rule["name"]
        severity = rule["severity"]
        cooldown_minutes = rule.get("cooldown_minutes", 60)
        
        # Set cooldown
        self.alert_cooldowns[rule_name] = datetime.now() + timedelta(minutes=cooldown_minutes)
        
        # Create alert message
        alert_msg = f"[{severity.upper()}] Alert: {rule_name} - Condition: {rule['condition']}"
        
        # Send to configured channels
        channels = self.config["monitoring"]["alerts"].get("channels", ["log"])
        
        if "log" in channels:
            print(f"⚠️  {alert_msg}")
            
        if "file" in channels:
            alert_file = self.export_path / "alerts.log"
            with open(alert_file, 'a') as f:
                f.write(f"{datetime.now().isoformat()} - {alert_msg}\n")
    
    def get_dashboard_data(self) -> dict:
        """Get current dashboard data for display."""
        return {
            "timestamp": datetime.now().isoformat(),
            "environment": self.config["monitoring"]["environment"],
            "health": self.monitor.get_health_status(),
            "performance": {
                "last_hour": self.monitor.get_performance_stats("all", hours=1),
                "last_24h": self.monitor.get_performance_stats("all", hours=24),
            },
            "errors": {
                "last_hour": self.monitor.get_error_stats(hours=1),
                "last_24h": self.monitor.get_error_stats(hours=24),
            },
            "usage": {
                "last_hour": self.monitor.get_usage_stats(hours=1),
                "last_24h": self.monitor.get_usage_stats(hours=24),
            },
            "insights": self.monitor.generate_insights(),
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> list[str]:
        """Generate actionable recommendations based on metrics."""
        recommendations = []
        
        # Check health metrics
        health = self.monitor.get_health_status()
        if health.get("memory_percent", 0) > 30:
            recommendations.append("Consider increasing memory allocation or optimizing memory usage")
        
        # Check performance
        perf_stats = self.monitor.get_performance_stats("all", hours=1)
        if perf_stats and perf_stats.get("sample_count", 0) > 0:
            avg_duration = perf_stats.get("average", 0)
            if avg_duration > 1000:
                recommendations.append("Performance degradation detected - review slow operations")
        
        # Check errors
        error_stats = self.monitor.get_error_stats(hours=1)
        if error_stats.get("total_errors", 0) > 10:
            recommendations.append("High error rate detected - investigate error logs")
        
        return recommendations
    
    def print_status(self):
        """Print current monitoring status to console."""
        data = self.get_dashboard_data()
        
        print("\n" + "="*70)
        print(" SPRITEPAL MONITORING STATUS ".center(70, "="))
        print("="*70)
        
        # Health Status
        health = data["health"]
        print(f"\n📊 System Health:")
        print(f"  CPU Usage: {health.get('cpu_percent', 0):.1f}%")
        print(f"  Memory: {health.get('memory_mb', 0):.1f}MB ({health.get('memory_percent', 0):.1f}%)")
        print(f"  Threads: {health.get('thread_count', 0)}")
        print(f"  Status: {'✅ Healthy' if health.get('healthy', False) else '⚠️ Degraded'}")
        
        # Performance Metrics (Last Hour)
        perf = data["performance"]["last_hour"]
        if perf and perf.get("sample_count", 0) > 0:
            print(f"\n⚡ Performance (Last Hour):")
            print(f"  Operations: {perf.get('sample_count', 0)}")
            print(f"  Avg Duration: {perf.get('average', 0):.2f}ms")
            print(f"  P95 Duration: {perf.get('percentiles', {}).get('p95', 0):.2f}ms")
            print(f"  Success Rate: {perf.get('success_rate', 0)*100:.1f}%")
        
        # Error Summary
        errors = data["errors"]["last_hour"]
        if errors and errors.get("total_errors", 0) > 0:
            print(f"\n❌ Errors (Last Hour):")
            print(f"  Total Errors: {errors.get('total_errors', 0)}")
            print(f"  Unique Types: {len(errors.get('by_type', {}))}")
            if errors.get("top_errors"):
                print("  Top Errors:")
                for err in errors["top_errors"][:3]:
                    print(f"    - {err['type']}: {err['count']} occurrences")
        
        # Recommendations
        if data["recommendations"]:
            print(f"\n💡 Recommendations:")
            for rec in data["recommendations"]:
                print(f"  • {rec}")
        
        print("\n" + "="*70)


def main():
    """Main entry point for production monitoring."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SpritePal Production Monitoring")
    parser.add_argument("--config", type=Path, help="Path to monitoring config file")
    parser.add_argument("--status", action="store_true", help="Print current status and exit")
    parser.add_argument("--export", action="store_true", help="Export metrics now and exit")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon process")
    
    args = parser.parse_args()
    
    # Initialize monitor
    monitor = ProductionMonitor(args.config)
    
    if args.status:
        # Print status and exit
        monitor.print_status()
        sys.exit(0)
        
    elif args.export:
        # Export metrics and exit
        monitor._export_metrics()
        print("✓ Metrics exported")
        sys.exit(0)
        
    elif args.daemon:
        # Run as daemon
        print("Starting monitoring daemon...")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                time.sleep(60)
                # Periodic status update
                monitor.print_status()
        except KeyboardInterrupt:
            print("\nMonitoring stopped")
            sys.exit(0)
    else:
        # Default: print status
        monitor.print_status()


if __name__ == "__main__":
    main()