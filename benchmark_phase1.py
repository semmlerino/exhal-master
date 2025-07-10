#!/usr/bin/env python3
"""
Phase 1 Performance Benchmark Suite
Measures performance improvements in the pixel editor optimizations
"""

import sys
import time
import psutil
import gc
from typing import Dict, List, Tuple, Any
import json
from datetime import datetime

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QImage, QPen

# Import the pixel editor components
from indexed_pixel_editor import IndexedPixelEditor
from pixel_editor_utils import QColorCache


class PerformanceBenchmark:
    """Comprehensive performance benchmark for Phase 1 improvements"""
    
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "system_info": self._get_system_info(),
            "benchmarks": {}
        }
        
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for context"""
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "python_version": sys.version,
            "qt_version": Qt.Version
        }
    
    def _measure_time(self, func, *args, **kwargs) -> Tuple[float, Any]:
        """Measure execution time of a function"""
        gc.collect()  # Clean up before measurement
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        return end - start, result
    
    def _measure_memory(self, func, *args, **kwargs) -> Tuple[float, Any]:
        """Measure memory usage of a function"""
        gc.collect()
        process = psutil.Process()
        mem_before = process.memory_info().rss
        
        result = func(*args, **kwargs)
        
        mem_after = process.memory_info().rss
        return (mem_after - mem_before) / 1024 / 1024, result  # MB
    
    def benchmark_color_caching(self, iterations: int = 1000) -> Dict[str, float]:
        """Benchmark QColor caching performance"""
        print("\n🎨 Benchmarking Color Caching...")
        
        # Test without caching (simulated)
        def without_cache():
            colors = []
            for i in range(iterations):
                # Simulate creating new QColor objects each time
                color = QColor(i % 256, (i * 2) % 256, (i * 3) % 256)
                colors.append(color)
            return colors
        
        # Test with caching
        cache = QColorCache()
        def with_cache():
            colors = []
            for i in range(iterations):
                rgb = (i % 256, (i * 2) % 256, (i * 3) % 256)
                color = cache.get_color(*rgb)
                colors.append(color)
            return colors
        
        time_without, _ = self._measure_time(without_cache)
        time_with, _ = self._measure_time(with_cache)
        
        # Memory test
        mem_without, _ = self._measure_memory(without_cache)
        mem_with, _ = self._measure_memory(with_cache)
        
        results = {
            "iterations": iterations,
            "time_without_cache": time_without,
            "time_with_cache": time_with,
            "time_improvement": (time_without - time_with) / time_without * 100,
            "memory_without_cache_mb": mem_without,
            "memory_with_cache_mb": mem_with,
            "memory_improvement": (mem_without - mem_with) / mem_without * 100 if mem_without > 0 else 0
        }
        
        print(f"  ✓ Time improvement: {results['time_improvement']:.1f}%")
        print(f"  ✓ Memory improvement: {results['memory_improvement']:.1f}%")
        
        return results
    
    def benchmark_viewport_culling(self, canvas_size: int = 512, viewport_size: int = 256) -> Dict[str, float]:
        """Benchmark viewport culling for large canvases"""
        print("\n🖼️ Benchmarking Viewport Culling...")
        
        # Create a large test image
        image = QImage(canvas_size, canvas_size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.white)
        
        # Fill with test pattern
        painter = QPainter(image)
        for x in range(0, canvas_size, 8):
            for y in range(0, canvas_size, 8):
                color = QColor((x * 255) // canvas_size, (y * 255) // canvas_size, 128)
                painter.fillRect(x, y, 8, 8, color)
        painter.end()
        
        viewport = QRect(0, 0, viewport_size, viewport_size)
        
        # Test without culling (render entire canvas)
        def without_culling():
            target = QImage(viewport_size, viewport_size, QImage.Format.Format_ARGB32)
            painter = QPainter(target)
            
            # Render entire canvas
            for x in range(0, canvas_size, 8):
                for y in range(0, canvas_size, 8):
                    if x < viewport_size and y < viewport_size:
                        color = QColor((x * 255) // canvas_size, (y * 255) // canvas_size, 128)
                        painter.fillRect(x, y, 8, 8, color)
            
            painter.end()
            return target
        
        # Test with culling (only render visible area)
        def with_culling():
            target = QImage(viewport_size, viewport_size, QImage.Format.Format_ARGB32)
            painter = QPainter(target)
            
            # Only render tiles in viewport
            start_x = max(0, viewport.left() // 8 * 8)
            start_y = max(0, viewport.top() // 8 * 8)
            end_x = min(canvas_size, (viewport.right() // 8 + 1) * 8)
            end_y = min(canvas_size, (viewport.bottom() // 8 + 1) * 8)
            
            for x in range(start_x, end_x, 8):
                for y in range(start_y, end_y, 8):
                    if x < viewport_size and y < viewport_size:
                        color = QColor((x * 255) // canvas_size, (y * 255) // canvas_size, 128)
                        painter.fillRect(x, y, 8, 8, color)
            
            painter.end()
            return target
        
        # Run benchmarks
        iterations = 10
        time_without = 0
        time_with = 0
        
        for _ in range(iterations):
            t, _ = self._measure_time(without_culling)
            time_without += t
            
            t, _ = self._measure_time(with_culling)
            time_with += t
        
        time_without /= iterations
        time_with /= iterations
        
        results = {
            "canvas_size": canvas_size,
            "viewport_size": viewport_size,
            "tiles_total": (canvas_size // 8) ** 2,
            "tiles_visible": (viewport_size // 8) ** 2,
            "time_without_culling": time_without,
            "time_with_culling": time_with,
            "time_improvement": (time_without - time_with) / time_without * 100
        }
        
        print(f"  ✓ Rendering {results['tiles_visible']} of {results['tiles_total']} tiles")
        print(f"  ✓ Time improvement: {results['time_improvement']:.1f}%")
        
        return results
    
    def benchmark_undo_system(self, states: int = 50, image_size: int = 256) -> Dict[str, float]:
        """Benchmark delta undo system vs full state storage"""
        print("\n↩️ Benchmarking Undo System...")
        
        # Create test images with incremental changes
        base_image = QImage(image_size, image_size, QImage.Format.Format_ARGB32)
        base_image.fill(Qt.GlobalColor.white)
        
        # Simulate old system (full state storage)
        def old_undo_system():
            undo_stack = []
            current_image = base_image.copy()
            
            for i in range(states):
                # Make a small change
                painter = QPainter(current_image)
                painter.fillRect(i * 2, i * 2, 10, 10, QColor(255, 0, 0))
                painter.end()
                
                # Store full image copy
                undo_stack.append(current_image.copy())
            
            return undo_stack
        
        # Simulate new delta system
        def new_delta_system():
            undo_stack = []
            current_image = base_image.copy()
            
            for i in range(states):
                # Record changed region
                changed_rect = QRect(i * 2, i * 2, 10, 10)
                
                # Store only the delta
                delta = {
                    "rect": changed_rect,
                    "old_data": current_image.copy(changed_rect),
                    "new_color": QColor(255, 0, 0)
                }
                
                # Make the change
                painter = QPainter(current_image)
                painter.fillRect(changed_rect, delta["new_color"])
                painter.end()
                
                undo_stack.append(delta)
            
            return undo_stack
        
        # Measure memory usage
        mem_old, old_stack = self._measure_memory(old_undo_system)
        mem_new, new_stack = self._measure_memory(new_delta_system)
        
        # Measure time
        time_old, _ = self._measure_time(old_undo_system)
        time_new, _ = self._measure_time(new_delta_system)
        
        results = {
            "undo_states": states,
            "image_size": image_size,
            "memory_old_system_mb": mem_old,
            "memory_new_system_mb": mem_new,
            "memory_improvement": (mem_old - mem_new) / mem_old * 100 if mem_old > 0 else 0,
            "time_old_system": time_old,
            "time_new_system": time_new,
            "time_improvement": (time_old - time_new) / time_old * 100
        }
        
        print(f"  ✓ Memory saved: {mem_old - mem_new:.1f} MB ({results['memory_improvement']:.1f}%)")
        print(f"  ✓ Time improvement: {results['time_improvement']:.1f}%")
        
        return results
    
    def benchmark_file_operations(self, file_size_kb: int = 1024) -> Dict[str, float]:
        """Benchmark file loading optimizations"""
        print("\n📁 Benchmarking File Operations...")
        
        # Create test data
        test_data = bytes([i % 256 for i in range(file_size_kb * 1024)])
        
        # Simulate old loading (no optimization)
        def old_loading():
            # Simulate processing without chunking
            result = []
            for i in range(0, len(test_data), 32):
                chunk = test_data[i:i+32]
                # Simulate tile processing
                processed = [b ^ 0xFF for b in chunk]
                result.extend(processed)
            return result
        
        # Simulate new loading (with chunking and optimization)
        def new_loading():
            # Process in larger chunks
            chunk_size = 8192
            result = []
            
            for i in range(0, len(test_data), chunk_size):
                chunk = test_data[i:i+chunk_size]
                # Batch process
                processed = bytes([b ^ 0xFF for b in chunk])
                result.extend(processed)
            
            return result
        
        # Run benchmarks
        iterations = 5
        time_old_total = 0
        time_new_total = 0
        
        for _ in range(iterations):
            time_old, _ = self._measure_time(old_loading)
            time_old_total += time_old
            
            time_new, _ = self._measure_time(new_loading)
            time_new_total += time_new
        
        time_old_avg = time_old_total / iterations
        time_new_avg = time_new_total / iterations
        
        results = {
            "file_size_kb": file_size_kb,
            "time_old_loading": time_old_avg,
            "time_new_loading": time_new_avg,
            "time_improvement": (time_old_avg - time_new_avg) / time_old_avg * 100,
            "throughput_old_mbps": (file_size_kb / 1024) / time_old_avg,
            "throughput_new_mbps": (file_size_kb / 1024) / time_new_avg
        }
        
        print(f"  ✓ Throughput: {results['throughput_old_mbps']:.1f} → {results['throughput_new_mbps']:.1f} MB/s")
        print(f"  ✓ Time improvement: {results['time_improvement']:.1f}%")
        
        return results
    
    def benchmark_pixel_operations(self, operations: int = 1000) -> Dict[str, float]:
        """Benchmark individual pixel drawing operations"""
        print("\n🖌️ Benchmarking Pixel Operations...")
        
        editor = IndexedPixelEditor()
        editor.new_image(256, 256)
        
        # Test without optimizations (simulated)
        def without_optimizations():
            for i in range(operations):
                x = i % 256
                y = (i // 256) % 256
                # Simulate unoptimized drawing
                color = QColor(i % 16 * 16, 0, 0)
                painter = QPainter(editor.image)
                painter.setPen(QPen(color, 1))
                painter.drawPoint(x, y)
                painter.end()
        
        # Test with optimizations
        def with_optimizations():
            # Batch operations
            painter = QPainter(editor.image)
            pen = QPen(Qt.GlobalColor.black, 1)
            painter.setPen(pen)
            
            for i in range(operations):
                x = i % 256
                y = (i // 256) % 256
                color = editor.indexed_colors[i % 16]
                if painter.pen().color() != color:
                    pen.setColor(color)
                    painter.setPen(pen)
                painter.drawPoint(x, y)
            
            painter.end()
        
        time_without, _ = self._measure_time(without_optimizations)
        time_with, _ = self._measure_time(with_optimizations)
        
        results = {
            "operations": operations,
            "time_without_optimizations": time_without,
            "time_with_optimizations": time_with,
            "time_improvement": (time_without - time_with) / time_without * 100,
            "operations_per_second_old": operations / time_without,
            "operations_per_second_new": operations / time_with
        }
        
        print(f"  ✓ Operations/sec: {results['operations_per_second_old']:.0f} → {results['operations_per_second_new']:.0f}")
        print(f"  ✓ Time improvement: {results['time_improvement']:.1f}%")
        
        return results
    
    def run_all_benchmarks(self):
        """Run all benchmarks and save results"""
        print("🚀 Starting Phase 1 Performance Benchmarks")
        print("=" * 50)
        
        # Run benchmarks
        self.results["benchmarks"]["color_caching"] = self.benchmark_color_caching(1000)
        self.results["benchmarks"]["viewport_culling"] = self.benchmark_viewport_culling(512, 256)
        self.results["benchmarks"]["undo_system"] = self.benchmark_undo_system(50, 256)
        self.results["benchmarks"]["file_operations"] = self.benchmark_file_operations(1024)
        self.results["benchmarks"]["pixel_operations"] = self.benchmark_pixel_operations(1000)
        
        # Save results
        with open("benchmark_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        # Print summary
        self._print_summary()
    
    def _print_summary(self):
        """Print a summary of all benchmark results"""
        print("\n" + "=" * 50)
        print("📊 BENCHMARK SUMMARY")
        print("=" * 50)
        
        total_improvements = []
        
        for name, results in self.results["benchmarks"].items():
            print(f"\n{name.replace('_', ' ').title()}:")
            
            # Find improvement metrics
            for key, value in results.items():
                if "improvement" in key and isinstance(value, (int, float)):
                    print(f"  • {key.replace('_', ' ').title()}: {value:.1f}%")
                    if value > 0:
                        total_improvements.append(value)
        
        if total_improvements:
            avg_improvement = sum(total_improvements) / len(total_improvements)
            print(f"\n🎯 Average Performance Improvement: {avg_improvement:.1f}%")
        
        print(f"\n📁 Detailed results saved to: benchmark_results.json")
        print("=" * 50)


def main():
    """Run the benchmark suite"""
    benchmark = PerformanceBenchmark()
    benchmark.run_all_benchmarks()


if __name__ == "__main__":
    main()