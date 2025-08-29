#!/usr/bin/env python3
"""
Real-time Monitoring Dashboard for SpritePal

Provides an interactive terminal-based dashboard for monitoring
SpritePal performance metrics, errors, and system health.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.managers.monitoring_manager import MonitoringManager


class MonitoringDashboard:
    """Interactive monitoring dashboard for SpritePal."""
    
    def __init__(self, refresh_interval: int = 5):
        """Initialize dashboard with refresh interval in seconds."""
        self.refresh_interval = refresh_interval
        self.monitor = MonitoringManager()
        self.monitor._initialize()
        self.running = True
        self.view_mode = "overview"  # overview, performance, errors, health
        
    def clear_screen(self):
        """Clear terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def format_duration(self, ms: float) -> str:
        """Format duration in milliseconds to human readable."""
        if ms < 1:
            return f"{ms*1000:.1f}μs"
        elif ms < 1000:
            return f"{ms:.1f}ms"
        else:
            return f"{ms/1000:.2f}s"
    
    def format_bytes(self, bytes_val: float) -> str:
        """Format bytes to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f}{unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f}TB"
    
    def draw_bar(self, value: float, max_value: float, width: int = 30, 
                 warning: float = 0.7, critical: float = 0.9) -> str:
        """Draw a text-based progress bar."""
        if max_value == 0:
            return "[" + " " * width + "]"
        
        ratio = min(value / max_value, 1.0)
        filled = int(width * ratio)
        
        # Choose color based on thresholds
        if ratio >= critical:
            color = "\033[91m"  # Red
            char = "█"
        elif ratio >= warning:
            color = "\033[93m"  # Yellow
            char = "█"
        else:
            color = "\033[92m"  # Green
            char = "█"
        
        reset = "\033[0m"
        bar = color + (char * filled) + reset + ("░" * (width - filled))
        
        return f"[{bar}] {ratio*100:.1f}%"
    
    def render_header(self):
        """Render dashboard header."""
        print("="*80)
        print(" SPRITEPAL MONITORING DASHBOARD ".center(80, "="))
        print("="*80)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Mode: {self.view_mode.upper()} | Refresh: {self.refresh_interval}s")
        print("Commands: [O]verview [P]erformance [E]rrors [H]ealth [R]efresh [Q]uit")
        print("-"*80)
    
    def render_overview(self):
        """Render overview dashboard."""
        # Get metrics
        health = self.monitor.get_health_status()
        perf_1h = self.monitor.get_performance_stats("all", hours=1)
        perf_24h = self.monitor.get_performance_stats("all", hours=24)
        errors_1h = self.monitor.get_error_stats(hours=1)
        errors_24h = self.monitor.get_error_stats(hours=24)
        usage_1h = self.monitor.get_usage_stats(hours=1)
        
        # System Health
        print("\n📊 SYSTEM HEALTH")
        print("-"*40)
        
        if health:
            cpu = health.get('cpu_percent', 0)
            mem_mb = health.get('memory_mb', 0)
            mem_pct = health.get('memory_percent', 0)
            threads = health.get('thread_count', 0)
            
            print(f"CPU Usage:    {self.draw_bar(cpu, 100, warning=50, critical=80)} {cpu:.1f}%")
            print(f"Memory:       {self.draw_bar(mem_pct, 100, warning=20, critical=40)} {mem_mb:.1f}MB")
            print(f"Threads:      {threads} {'⚠️' if threads > 50 else '✅'}")
            print(f"Status:       {'✅ Healthy' if health.get('healthy', False) else '⚠️ Degraded'}")
        else:
            print("No health data available")
        
        # Performance Summary
        print("\n⚡ PERFORMANCE SUMMARY")
        print("-"*40)
        
        if perf_1h and perf_1h.get('sample_count', 0) > 0:
            print(f"Last Hour:    {perf_1h['sample_count']} operations")
            print(f"  Avg:        {self.format_duration(perf_1h.get('average', 0))}")
            print(f"  P95:        {self.format_duration(perf_1h.get('percentiles', {}).get('p95', 0))}")
            print(f"  Success:    {perf_1h.get('success_rate', 0)*100:.1f}%")
        
        if perf_24h and perf_24h.get('sample_count', 0) > 0:
            print(f"\nLast 24h:     {perf_24h['sample_count']} operations")
            print(f"  Avg:        {self.format_duration(perf_24h.get('average', 0))}")
            print(f"  Success:    {perf_24h.get('success_rate', 0)*100:.1f}%")
        
        # Error Summary
        print("\n❌ ERROR SUMMARY")
        print("-"*40)
        
        if errors_1h and errors_1h.get('total_errors', 0) > 0:
            print(f"Last Hour:    {errors_1h['total_errors']} errors")
            if errors_1h.get('top_errors'):
                for err in errors_1h['top_errors'][:3]:
                    print(f"  • {err['type']}: {err['count']}x")
        else:
            print("Last Hour:    No errors ✅")
        
        if errors_24h and errors_24h.get('total_errors', 0) > 0:
            print(f"Last 24h:     {errors_24h['total_errors']} errors")
        
        # Usage Stats
        if usage_1h and usage_1h.get('total_events', 0) > 0:
            print("\n📈 USAGE STATS (Last Hour)")
            print("-"*40)
            print(f"Total Events: {usage_1h['total_events']}")
            
            if usage_1h.get('top_features'):
                print("Top Features:")
                for feature, count in list(usage_1h['top_features'].items())[:5]:
                    print(f"  • {feature}: {count} uses")
    
    def render_performance(self):
        """Render detailed performance view."""
        perf = self.monitor.get_performance_stats("all", hours=1)
        
        print("\n⚡ DETAILED PERFORMANCE METRICS")
        print("-"*40)
        
        if not perf or perf.get('sample_count', 0) == 0:
            print("No performance data available")
            return
        
        # Overall stats
        print(f"Total Operations: {perf['sample_count']}")
        print(f"Success Rate:     {perf.get('success_rate', 0)*100:.2f}%")
        print(f"Failed:           {perf.get('failed_count', 0)}")
        
        # Timing statistics
        print("\nTiming Statistics:")
        print(f"  Average:        {self.format_duration(perf.get('average', 0))}")
        print(f"  Minimum:        {self.format_duration(perf.get('min', 0))}")
        print(f"  Maximum:        {self.format_duration(perf.get('max', 0))}")
        
        percentiles = perf.get('percentiles', {})
        if percentiles:
            print(f"  P50 (Median):   {self.format_duration(percentiles.get('p50', 0))}")
            print(f"  P75:            {self.format_duration(percentiles.get('p75', 0))}")
            print(f"  P90:            {self.format_duration(percentiles.get('p90', 0))}")
            print(f"  P95:            {self.format_duration(percentiles.get('p95', 0))}")
            print(f"  P99:            {self.format_duration(percentiles.get('p99', 0))}")
        
        # By operation
        by_op = perf.get('by_operation', {})
        if by_op:
            print("\nBy Operation:")
            for op_name, op_stats in sorted(by_op.items(), 
                                           key=lambda x: x[1].get('count', 0), 
                                           reverse=True)[:10]:
                count = op_stats.get('count', 0)
                avg = op_stats.get('average', 0)
                success = op_stats.get('success_rate', 0) * 100
                print(f"  {op_name:30} {count:5} ops | {self.format_duration(avg):>10} | {success:.1f}% success")
        
        # Memory impact
        print("\nMemory Impact:")
        print(f"  Avg Delta:      {self.format_bytes(perf.get('memory_delta_avg', 0)*1024*1024)}")
        print(f"  Max Delta:      {self.format_bytes(perf.get('memory_delta_max', 0)*1024*1024)}")
    
    def render_errors(self):
        """Render detailed error view."""
        errors = self.monitor.get_error_stats(hours=24)
        
        print("\n❌ ERROR ANALYSIS")
        print("-"*40)
        
        if not errors or errors.get('total_errors', 0) == 0:
            print("No errors in the last 24 hours ✅")
            return
        
        print(f"Total Errors:     {errors['total_errors']}")
        print(f"Total Occurrences: {errors.get('total_occurrences', 0)}")
        
        # By severity
        by_severity = errors.get('by_severity', {})
        if by_severity:
            print("\nBy Severity:")
            for severity in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']:
                if severity in by_severity:
                    count = by_severity[severity]
                    bar = "█" * min(count, 50)
                    print(f"  {severity:8} [{count:4}] {bar}")
        
        # By type
        by_type = errors.get('by_type', {})
        if by_type:
            print("\nBy Error Type:")
            for err_type, count in sorted(by_type.items(), 
                                         key=lambda x: x[1], 
                                         reverse=True)[:10]:
                print(f"  {err_type:30} {count:5} occurrences")
        
        # By operation
        by_op = errors.get('by_operation', {})
        if by_op:
            print("\nBy Operation:")
            for op, count in sorted(by_op.items(), 
                                   key=lambda x: x[1], 
                                   reverse=True)[:10]:
                print(f"  {op:30} {count:5} errors")
        
        # Top errors with details
        top_errors = errors.get('top_errors', [])
        if top_errors:
            print("\nTop Error Details:")
            for i, err in enumerate(top_errors[:5], 1):
                print(f"\n  {i}. {err['type']} in {err['operation']}")
                print(f"     Count: {err['count']} | Last: {err.get('last_seen', 'Unknown')}")
    
    def render_health(self):
        """Render detailed health view."""
        health = self.monitor.get_health_status()
        trends = self.monitor.get_health_trends(hours=1)
        
        print("\n📊 SYSTEM HEALTH DETAILS")
        print("-"*40)
        
        if not health:
            print("No health data available")
            return
        
        # Current metrics
        print("Current Metrics:")
        print(f"  CPU Usage:        {health.get('cpu_percent', 0):.1f}%")
        print(f"  Memory Usage:     {health.get('memory_mb', 0):.1f}MB ({health.get('memory_percent', 0):.1f}%)")
        print(f"  Thread Count:     {health.get('thread_count', 0)}")
        print(f"  File Descriptors: {health.get('file_descriptors', 0)}")
        
        # Trends
        if trends:
            print("\nTrends (Last Hour):")
            for metric_name, trend_data in trends.items():
                current = trend_data.get('current', 0)
                avg = trend_data.get('average', 0)
                trend = trend_data.get('trend', 'stable')
                unit = trend_data.get('unit', '')
                
                # Trend indicator
                if trend == 'increasing':
                    indicator = "📈"
                elif trend == 'decreasing':
                    indicator = "📉"
                else:
                    indicator = "➡️"
                
                print(f"  {metric_name:20} {indicator} Current: {current:.1f}{unit} | Avg: {avg:.1f}{unit}")
                print(f"    Range: {trend_data.get('min', 0):.1f} - {trend_data.get('max', 0):.1f}{unit}")
        
        # Cache effectiveness
        cache_stats = self.monitor.get_cache_effectiveness()
        if cache_stats:
            print("\nCache Performance:")
            print(f"  Hit Rate:         {cache_stats.get('hit_rate', 0)*100:.1f}%")
            print(f"  Total Hits:       {cache_stats.get('hits', 0)}")
            print(f"  Total Misses:     {cache_stats.get('misses', 0)}")
            print(f"  Cache Size:       {self.format_bytes(cache_stats.get('size_bytes', 0))}")
        
        # Insights
        insights = self.monitor.generate_insights()
        if insights:
            print("\n💡 System Insights:")
            for insight in insights[:5]:
                print(f"  • {insight}")
    
    def run(self):
        """Run the interactive dashboard."""
        import select
        import termios
        import tty
        
        # Save terminal settings
        if sys.platform != 'win32':
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        
        try:
            while self.running:
                # Clear and render
                self.clear_screen()
                self.render_header()
                
                # Render based on mode
                if self.view_mode == "overview":
                    self.render_overview()
                elif self.view_mode == "performance":
                    self.render_performance()
                elif self.view_mode == "errors":
                    self.render_errors()
                elif self.view_mode == "health":
                    self.render_health()
                
                # Check for input (non-blocking)
                if sys.platform != 'win32':
                    if select.select([sys.stdin], [], [], self.refresh_interval)[0]:
                        key = sys.stdin.read(1).lower()
                        self.handle_input(key)
                else:
                    # Windows fallback - blocking input with timeout
                    time.sleep(self.refresh_interval)
                    
        except KeyboardInterrupt:
            self.running = False
        finally:
            # Restore terminal settings
            if sys.platform != 'win32':
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            
            print("\n\nDashboard stopped.")
    
    def handle_input(self, key: str):
        """Handle keyboard input."""
        if key == 'q':
            self.running = False
        elif key == 'o':
            self.view_mode = "overview"
        elif key == 'p':
            self.view_mode = "performance"
        elif key == 'e':
            self.view_mode = "errors"
        elif key == 'h':
            self.view_mode = "health"
        elif key == 'r':
            pass  # Will refresh on next loop
        elif key in ['1', '2', '3', '4', '5']:
            # Adjust refresh interval
            self.refresh_interval = int(key)


def main():
    """Main entry point for dashboard."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SpritePal Monitoring Dashboard")
    parser.add_argument("-r", "--refresh", type=int, default=5,
                       help="Refresh interval in seconds (default: 5)")
    parser.add_argument("-m", "--mode", choices=["overview", "performance", "errors", "health"],
                       default="overview", help="Initial view mode")
    
    args = parser.parse_args()
    
    dashboard = MonitoringDashboard(refresh_interval=args.refresh)
    dashboard.view_mode = args.mode
    
    print("Starting SpritePal Monitoring Dashboard...")
    print("Press 'q' to quit")
    time.sleep(2)
    
    dashboard.run()


if __name__ == "__main__":
    main()