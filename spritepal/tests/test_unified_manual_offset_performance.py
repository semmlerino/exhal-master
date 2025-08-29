"""
Performance tests for unified manual offset dialog.

Provides benchmarking and profiling tools for dialog performance validation.
"""

from __future__ import annotations

import time
from typing import Any, Callable
from unittest.mock import Mock

import psutil

class PerformanceTargets:
    """Performance targets for validation."""
    
    STARTUP_TIME_MS = 1000  # 1 second max startup
    PREVIEW_GENERATION_MS = 500  # 500ms max preview
    MEMORY_OVERHEAD_MB = 50  # 50MB max overhead

class MemoryProfiler:
    """Memory profiling utilities."""
    
    @staticmethod
    def get_memory_usage() -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    @staticmethod
    def profile_function(func: Callable, *args, **kwargs) -> dict[str, Any]:
        """Profile memory usage of a function."""
        initial_memory = MemoryProfiler.get_memory_usage()
        
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        
        final_memory = MemoryProfiler.get_memory_usage()
        
        return {
            "result": result,
            "execution_time_ms": (end_time - start_time) * 1000,
            "memory_usage_mb": final_memory - initial_memory,
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory
        }

class StartupBenchmark:
    """Benchmark dialog startup performance."""
    
    @staticmethod
    def measure_dialog_startup(dialog_class, setup_func: Callable) -> dict[str, Any]:
        """Measure dialog startup performance."""
        start_time = time.perf_counter()
        
        # Mock parent for headless testing
        mock_parent = Mock()
        
        # Initialize dialog
        init_start = time.perf_counter()
        dialog = setup_func(dialog_class, mock_parent)
        init_end = time.perf_counter()
        
        end_time = time.perf_counter()
        
        return {
            "total_startup_time_ms": (end_time - start_time) * 1000,
            "initialization_time_ms": (init_end - init_start) * 1000,
            "component_count": getattr(dialog, "_component_count", 0),
            "dialog": dialog
        }

class PreviewPerformanceBenchmark:
    """Benchmark preview generation performance."""
    
    @staticmethod
    def measure_preview_generation(generator_func: Callable, *args) -> dict[str, Any]:
        """Measure preview generation performance."""
        start_time = time.perf_counter()
        
        try:
            result = generator_func(*args)
            success = True
        except Exception as e:
            result = None
            success = False
            
        end_time = time.perf_counter()
        
        return {
            "generation_time_ms": (end_time - start_time) * 1000,
            "success": success,
            "result": result
        }

class ServiceAdapterOverheadAnalyzer:
    """Analyze service adapter overhead."""
    
    @staticmethod
    def measure_adapter_overhead(adapter_class, operations: list) -> dict[str, Any]:
        """Measure overhead of service adapter operations."""
        adapter = adapter_class()
        
        results = {
            "total_overhead_ms": 0,
            "operation_times": {},
            "average_overhead_ms": 0
        }
        
        total_time = 0
        
        for operation_name in operations:
            if hasattr(adapter, operation_name):
                start_time = time.perf_counter()
                try:
                    getattr(adapter, operation_name)()
                except Exception:
                    pass  # Ignore errors in benchmarking
                end_time = time.perf_counter()
                
                operation_time = (end_time - start_time) * 1000
                results["operation_times"][operation_name] = operation_time
                total_time += operation_time
        
        results["total_overhead_ms"] = total_time
        results["average_overhead_ms"] = total_time / len(operations) if operations else 0
        
        return results

class PerformanceReportGenerator:
    """Generate performance reports."""
    
    @staticmethod
    def generate_report(benchmark_results: dict[str, Any]) -> str:
        """Generate a formatted performance report."""
        report_lines = [
            "=== Performance Report ===",
            ""
        ]
        
        for category, results in benchmark_results.items():
            report_lines.append(f"{category.upper()}:")
            
            if isinstance(results, dict):
                for key, value in results.items():
                    if isinstance(value, (int, float)):
                        if "time" in key.lower():
                            report_lines.append(f"  {key}: {value:.2f}ms")
                        elif "memory" in key.lower():
                            report_lines.append(f"  {key}: {value:.2f}MB")
                        else:
                            report_lines.append(f"  {key}: {value}")
                    else:
                        report_lines.append(f"  {key}: {value}")
            else:
                report_lines.append(f"  Result: {results}")
            
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    @staticmethod
    def check_targets(results: dict[str, Any]) -> dict[str, bool]:
        """Check if performance targets are met."""
        target_checks = {}
        
        # Check startup time
        startup_time = results.get("startup", {}).get("total_startup_time_ms", 0)
        target_checks["startup_time_ok"] = startup_time < PerformanceTargets.STARTUP_TIME_MS
        
        # Check preview generation
        preview_time = results.get("preview", {}).get("generation_time_ms", 0)
        target_checks["preview_time_ok"] = preview_time < PerformanceTargets.PREVIEW_GENERATION_MS
        
        # Check memory overhead
        memory_usage = results.get("memory", {}).get("memory_usage_mb", 0)
        target_checks["memory_usage_ok"] = memory_usage < PerformanceTargets.MEMORY_OVERHEAD_MB
        
        return target_checks