#!/usr/bin/env python3
"""
Advanced Performance Analyzer for SpritePal

This analyzer focuses on real-world performance bottlenecks identified from the Week 1 profiling:
1. CPU-intensive operations (identified 2.7s bottleneck in sprite operations)
2. Memory allocation patterns (fixed 100x improvement in memory leaks)
3. I/O efficiency (ROM reading, cache operations)
4. Algorithm optimization opportunities
5. Threading and concurrency bottlenecks

Post-memory-leak analysis targeting remaining performance opportunities.
"""

import gc
import mmap
import struct
import sys
import tempfile
import time
import tracemalloc
from collections import deque
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from performance_profiler import PerformanceProfiler, save_report
from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class OptimizationOpportunity:
    """Represents a specific optimization opportunity"""
    category: str  # CPU, Memory, I/O, Algorithm, Threading
    severity: str  # Critical, High, Medium, Low
    description: str
    current_performance: str
    expected_improvement: str
    implementation_effort: str  # Low, Medium, High
    code_location: str
    optimization_strategy: str


class RealWorldProfiler:
    """Profile real SpritePal operations to identify optimization opportunities"""

    def __init__(self):
        self.profiler = PerformanceProfiler()
        self.optimization_opportunities = []

    def profile_byte_operations_bottleneck(self):
        """
        Profile the int.to_bytes bottleneck identified in sprite operations.
        This was consuming 0.83s out of 2.77s total (30% of time).
        """
        logger.info("Profiling byte conversion operations...")

        self.profiler.start_profiling()

        def test_byte_conversion_patterns():
            """Test different byte conversion approaches"""
            test_data_size = 100000

            # Current approach (identified bottleneck)
            start_time = time.time()
            current_results = []
            for i in range(test_data_size):
                # This mirrors the bottleneck: (i * 4 + j).to_bytes(4, 'little')
                result = (i * 4).to_bytes(4, 'little')
                current_results.append(result)
            current_time = time.time() - start_time

            # Optimized approach 1: Pre-allocate bytearray
            start_time = time.time()
            optimized_results = bytearray(test_data_size * 4)
            for i in range(test_data_size):
                value = i * 4
                optimized_results[i*4:(i+1)*4] = value.to_bytes(4, 'little')
            optimized_time_1 = time.time() - start_time

            # Optimized approach 2: Struct packing
            start_time = time.time()
            struct_results = []
            pack_func = struct.pack
            for i in range(test_data_size):
                result = pack_func('<I', i * 4)  # Little-endian unsigned int
                struct_results.append(result)
            struct_time = time.time() - start_time

            # Optimized approach 3: Batch struct packing
            start_time = time.time()
            values = [i * 4 for i in range(test_data_size)]
            struct.pack(f'<{test_data_size}I', *values)
            batch_time = time.time() - start_time

            return {
                'current_time': current_time,
                'optimized_time_1': optimized_time_1,
                'struct_time': struct_time,
                'batch_time': batch_time,
                'improvement_1': current_time / optimized_time_1 if optimized_time_1 > 0 else 0,
                'improvement_struct': current_time / struct_time if struct_time > 0 else 0,
                'improvement_batch': current_time / batch_time if batch_time > 0 else 0
            }

        result = self.profiler.profile_operation("byte_conversion_optimization", test_byte_conversion_patterns)
        metrics = self.profiler.generate_comprehensive_report()
        self.profiler.stop_profiling()

        # Analyze results and create optimization opportunity
        if result['success'] and 'result' in result:
            perf_data = result['result']
            best_improvement = max(
                perf_data.get('improvement_1', 1),
                perf_data.get('improvement_struct', 1),
                perf_data.get('improvement_batch', 1)
            )

            if best_improvement > 1.5:  # 50% improvement threshold
                self.optimization_opportunities.append(OptimizationOpportunity(
                    category="CPU",
                    severity="High",
                    description="Optimize byte conversion operations in sprite data processing",
                    current_performance=f"{perf_data.get('current_time', 0):.3f}s for 100k operations",
                    expected_improvement=f"{best_improvement:.1f}x speedup using optimized byte operations",
                    implementation_effort="Low",
                    code_location="run_performance_analysis.py:325 (sprite data generation)",
                    optimization_strategy="Replace individual to_bytes() calls with struct.pack() or batch operations"
                ))

        return metrics, result

    def profile_memory_allocation_patterns(self):
        """Profile memory allocation patterns in sprite processing"""
        logger.info("Profiling memory allocation patterns...")

        # Enable detailed memory tracking
        tracemalloc.start()
        snapshot1 = tracemalloc.take_snapshot()

        self.profiler.start_profiling()

        def test_memory_allocation_patterns():
            """Test different memory allocation approaches"""

            # Pattern 1: Large object creation (current approach)
            large_objects = []
            for i in range(100):
                # Simulate 64KB ROM chunks (as in sprite operations)
                chunk = bytearray(65536)
                # Fill with data (this is the memory-intensive part)
                for j in range(0, 65536, 4):
                    chunk[j:j+4] = (i * 4 + j).to_bytes(4, 'little')
                large_objects.append(chunk)

            # Pattern 2: Memory pool approach
            memory_pool = deque(maxlen=10)  # Reuse objects
            pooled_objects = []

            for i in range(100):
                if memory_pool:
                    chunk = memory_pool.popleft()
                    # Clear the chunk
                    chunk[:] = b'\x00' * len(chunk)
                else:
                    chunk = bytearray(65536)

                # Fill with data
                for j in range(0, min(1000, 65536), 4):  # Reduced for testing
                    chunk[j:j+4] = (i * 4 + j).to_bytes(4, 'little')

                pooled_objects.append(chunk)

                # Return to pool when done (simulation)
                if len(pooled_objects) > 10:
                    returned_chunk = pooled_objects.pop(0)
                    memory_pool.append(returned_chunk)

            # Force garbage collection to measure impact
            gc.collect()

            # Cleanup
            del large_objects
            del pooled_objects
            del memory_pool

            return {'status': 'completed'}

        result = self.profiler.profile_operation("memory_allocation_patterns", test_memory_allocation_patterns)

        # Take snapshot after operation
        snapshot2 = tracemalloc.take_snapshot()

        # Analyze memory growth
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')

        metrics = self.profiler.generate_comprehensive_report()
        self.profiler.stop_profiling()
        tracemalloc.stop()

        # Analyze memory allocation patterns
        if top_stats:
            memory_growth = sum(stat.size_diff for stat in top_stats if stat.size_diff > 0)
            if memory_growth > 1024 * 1024:  # > 1MB growth
                self.optimization_opportunities.append(OptimizationOpportunity(
                    category="Memory",
                    severity="Medium",
                    description="Optimize memory allocation in large data structure creation",
                    current_performance=f"Memory growth: {memory_growth / 1024 / 1024:.1f}MB",
                    expected_improvement="50-80% reduction in memory allocation overhead",
                    implementation_effort="Medium",
                    code_location="sprite_data_operations (ROM chunk creation)",
                    optimization_strategy="Implement object pooling for large allocations, use memory-mapped files for ROM data"
                ))

        return metrics, result


    def _create_test_files(self):
        """Create test files of different sizes for I/O testing"""
        test_files = []

        # Small file (typical sprite size)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.spr') as f:
            test_data = b'SPRITE_DATA' * 100  # 1.1KB
            f.write(test_data)
            test_files.append(f.name)

        # Medium file (typical ROM section)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.rom') as f:
            test_data = b'ROM_DATA_CHUNK' * 4096  # ~64KB
            f.write(test_data)
            test_files.append(f.name)

        # Large file (full ROM simulation)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as f:
            # Write in chunks to avoid memory issues
            chunk = b'LARGE_ROM_DATA' * 1024  # ~14KB chunks
            for _ in range(100):  # ~1.4MB total
                f.write(chunk)
            test_files.append(f.name)

        return test_files

    def _test_sequential_read(self, test_files):
        """Test sequential read pattern (current approach)"""
        start_time = time.time()
        for file_path in test_files:
            with Path(file_path).open('rb') as f:
                data = f.read()
                # Process data (simulate sprite extraction)
                len(data) // 512
        return time.time() - start_time

    def _test_buffered_read(self, test_files):
        """Test buffered read pattern"""
        start_time = time.time()
        for file_path in test_files:
            path_obj = Path(file_path)
            with path_obj.open('rb', buffering=8192) as f:
                while True:
                    chunk = f.read(512)  # Read in sprite-sized chunks
                    if not chunk:
                        break
                    # Process chunk
                    _ = len(chunk)
        return time.time() - start_time

    def _test_memory_mapped_read(self, test_files):
        """Test memory-mapped file access"""
        start_time = time.time()
        for file_path in test_files:
            with Path(file_path).open('rb') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                    # Process in chunks
                    file_size = len(mmapped_file)
                    for offset in range(0, file_size, 512):
                        chunk = mmapped_file[offset:offset+512]
                        _ = len(chunk)
        return time.time() - start_time

    def _cleanup_test_files(self, test_files):
        """Clean up test files"""
        for file_path in test_files:
            with suppress(OSError):
                Path(file_path).unlink(missing_ok=True)

    def _analyze_io_performance(self, io_data):
        """Analyze I/O performance and create optimization opportunities"""
        sequential_time = io_data.get('sequential_time', 1)
        best_time = min(
            io_data.get('buffered_time', sequential_time),
            io_data.get('mmap_time', sequential_time)
        )

        if sequential_time / best_time > 1.3:  # 30% improvement threshold
            improvement = sequential_time / best_time
            self.optimization_opportunities.append(OptimizationOpportunity(
                category="I/O",
                severity="Medium",
                description="Optimize ROM file reading patterns",
                current_performance=f"Sequential read: {sequential_time:.3f}s for {io_data.get('total_size_mb', 0):.1f}MB",
                expected_improvement=f"{improvement:.1f}x faster I/O using memory-mapped files or optimized buffering",
                implementation_effort="Medium",
                code_location="ROM reading operations in extractor classes",
                optimization_strategy="Use memory-mapped files for large ROM access, implement read-ahead buffering"
            ))

    def profile_io_operations(self):
        """Profile I/O operations and cache efficiency"""
        logger.info("Profiling I/O operations...")

        self.profiler.start_profiling()

        def test_io_patterns():
            """Test different I/O access patterns"""
            test_files = self._create_test_files()

            try:
                sequential_time = self._test_sequential_read(test_files)
                buffered_time = self._test_buffered_read(test_files)
                mmap_time = self._test_memory_mapped_read(test_files)

                return {
                    'sequential_time': sequential_time,
                    'buffered_time': buffered_time,
                    'mmap_time': mmap_time,
                    'files_processed': len(test_files),
                    'total_size_mb': sum(Path(f).stat().st_size for f in test_files) / 1024 / 1024
                }

            finally:
                self._cleanup_test_files(test_files)

        result = self.profiler.profile_operation("io_optimization", test_io_patterns)
        metrics = self.profiler.generate_comprehensive_report()
        self.profiler.stop_profiling()

        # Analyze I/O performance
        if result['success'] and 'result' in result:
            io_data = result['result']
            self._analyze_io_performance(io_data)

        return metrics, result

    def profile_algorithm_complexity(self):
        """Profile algorithmic complexity in sprite finding operations"""
        logger.info("Profiling algorithmic complexity...")

        self.profiler.start_profiling()

        def test_algorithm_complexity():
            """Test different algorithmic approaches"""

            # Simulate sprite searching patterns
            rom_size = 1000000  # 1MB ROM simulation

            # Pattern 1: Naive linear search (O(n))
            start_time = time.time()
            search_pattern = b'\x00\x01\x02\x03'  # Simple pattern
            rom_data = bytearray(rom_size)

            # Fill with some pattern data
            for i in range(0, rom_size, 100):
                if i + 4 < rom_size:
                    rom_data[i:i+4] = search_pattern

            # Linear search
            linear_matches = []
            for offset in range(0, rom_size - 4, 16):  # Step=16 (default scan step)
                if rom_data[offset:offset+4] == search_pattern:
                    linear_matches.append(offset)
            linear_time = time.time() - start_time

            # Pattern 2: Optimized search using Boyer-Moore-like approach
            start_time = time.time()
            optimized_matches = []

            # Create simple skip table for pattern
            pattern_len = len(search_pattern)
            skip_table = {}
            for i, byte in enumerate(search_pattern[:-1]):
                skip_table[byte] = pattern_len - 1 - i

            offset = 0
            while offset <= rom_size - pattern_len:
                match = True
                for i in range(pattern_len):
                    if rom_data[offset + i] != search_pattern[i]:
                        match = False
                        # Skip based on character that caused mismatch
                        skip = skip_table.get(rom_data[offset + i], pattern_len)
                        offset += max(1, skip)
                        break

                if match:
                    optimized_matches.append(offset)
                    offset += 16  # Continue with normal step

            optimized_time = time.time() - start_time

            # Pattern 3: Chunked parallel-style processing
            start_time = time.time()
            chunk_size = rom_size // 4
            chunked_matches = []

            for chunk_start in range(0, rom_size, chunk_size):
                chunk_end = min(chunk_start + chunk_size, rom_size)
                chunk_data = rom_data[chunk_start:chunk_end]

                # Search within chunk
                for offset in range(0, len(chunk_data) - 4, 16):
                    if chunk_data[offset:offset+4] == search_pattern:
                        chunked_matches.append(chunk_start + offset)

            chunked_time = time.time() - start_time

            return {
                'linear_time': linear_time,
                'optimized_time': optimized_time,
                'chunked_time': chunked_time,
                'linear_matches': len(linear_matches),
                'optimized_matches': len(optimized_matches),
                'chunked_matches': len(chunked_matches),
                'rom_size_mb': rom_size / 1024 / 1024
            }

        result = self.profiler.profile_operation("algorithm_complexity", test_algorithm_complexity)
        metrics = self.profiler.generate_comprehensive_report()
        self.profiler.stop_profiling()

        # Analyze algorithmic improvements
        if result['success'] and 'result' in result:
            algo_data = result['result']
            linear_time = algo_data.get('linear_time', 1)
            best_time = min(
                algo_data.get('optimized_time', linear_time),
                algo_data.get('chunked_time', linear_time)
            )

            if linear_time / best_time > 1.2:  # 20% improvement threshold
                improvement = linear_time / best_time
                self.optimization_opportunities.append(OptimizationOpportunity(
                    category="Algorithm",
                    severity="Medium",
                    description="Optimize sprite search algorithms",
                    current_performance=f"Linear search: {linear_time:.3f}s for {algo_data.get('rom_size_mb', 0):.1f}MB",
                    expected_improvement=f"{improvement:.1f}x faster using optimized search patterns",
                    implementation_effort="Medium",
                    code_location="sprite_finder.py, ROM scanning loops",
                    optimization_strategy="Implement Boyer-Moore search, chunk-based parallel processing"
                ))

        return metrics, result

    def generate_optimization_report(self) -> str:
        """Generate comprehensive optimization report with prioritized recommendations"""

        if not self.optimization_opportunities:
            return "No significant optimization opportunities identified."

        # Sort by severity and expected improvement
        severity_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
        self.optimization_opportunities.sort(
            key=lambda x: (severity_order.get(x.severity, 99), x.category)
        )

        report = []
        report.append("=" * 80)
        report.append("SPRITEPAL ADVANCED PERFORMANCE OPTIMIZATION REPORT")
        report.append("=" * 80)
        report.append("")
        report.append(f"Analysis Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Optimization Opportunities: {len(self.optimization_opportunities)}")
        report.append("")

        # Group by category
        categories = {}
        for opp in self.optimization_opportunities:
            if opp.category not in categories:
                categories[opp.category] = []
            categories[opp.category].append(opp)

        for category, opportunities in categories.items():
            report.append(f"{category.upper()} OPTIMIZATIONS")
            report.append("-" * 40)

            for i, opp in enumerate(opportunities, 1):
                report.append(f"{i}. {opp.description}")
                report.append(f"   Severity: {opp.severity}")
                report.append(f"   Current: {opp.current_performance}")
                report.append(f"   Expected: {opp.expected_improvement}")
                report.append(f"   Effort: {opp.implementation_effort}")
                report.append(f"   Location: {opp.code_location}")
                report.append(f"   Strategy: {opp.optimization_strategy}")
                report.append("")

        # Implementation priority
        report.append("IMPLEMENTATION PRIORITY")
        report.append("-" * 40)

        high_impact = [opp for opp in self.optimization_opportunities
                      if opp.severity in ['Critical', 'High']]

        if high_impact:
            report.append("HIGH PRIORITY (Implement First):")
            for opp in high_impact:
                report.append(f"• {opp.description}")
                report.append(f"  Expected: {opp.expected_improvement}")

        medium_impact = [opp for opp in self.optimization_opportunities
                        if opp.severity == 'Medium']

        if medium_impact:
            report.append("")
            report.append("MEDIUM PRIORITY (Implement After High Priority):")
            for opp in medium_impact:
                report.append(f"• {opp.description}")
                report.append(f"  Expected: {opp.expected_improvement}")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)


def run_advanced_performance_analysis():
    """Run advanced performance analysis targeting identified bottlenecks"""
    logger.info("Starting advanced SpritePal performance analysis...")

    analyzer = RealWorldProfiler()

    # Profile specific bottlenecks identified from Week 1
    analyses = [
        ("Byte Operations Bottleneck", analyzer.profile_byte_operations_bottleneck),
        ("Memory Allocation Patterns", analyzer.profile_memory_allocation_patterns),
        ("I/O Operations", analyzer.profile_io_operations),
        ("Algorithm Complexity", analyzer.profile_algorithm_complexity),
    ]

    results = {}

    for analysis_name, analysis_func in analyses:
        logger.info(f"Running {analysis_name} analysis...")
        try:
            metrics, result = analysis_func()
            results[analysis_name] = {
                'metrics': metrics,
                'result': result,
                'success': True
            }
            logger.info(f"{analysis_name} analysis completed")
        except Exception as e:
            logger.error(f"{analysis_name} analysis failed: {e}")
            results[analysis_name] = {
                'error': str(e),
                'success': False
            }

    # Generate optimization report
    optimization_report = analyzer.generate_optimization_report()

    # Save detailed report
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_filename = f"spritepal_advanced_optimization_report_{timestamp}.txt"

    with Path(report_filename).open('w') as f:
        f.write(optimization_report)

    logger.info(f"Advanced optimization report saved to: {report_filename}")

    # Save individual analysis reports
    for analysis_name, analysis_data in results.items():
        if analysis_data['success']:
            metrics = analysis_data['metrics']
            filename = f"spritepal_advanced_{analysis_name.lower().replace(' ', '_')}_profile_{timestamp}.txt"
            save_report(metrics, filename)
            logger.info(f"{analysis_name} detailed report saved to: {filename}")

    # Print summary to console
    print("\n" + optimization_report)

    return results, analyzer.optimization_opportunities


if __name__ == "__main__":
    try:
        results, opportunities = run_advanced_performance_analysis()
        print("\nAdvanced performance analysis completed!")
        print(f"Identified {len(opportunities)} optimization opportunities")

        # Quick summary of top opportunities
        high_priority = [opp for opp in opportunities if opp.severity in ['Critical', 'High']]
        if high_priority:
            print("\nTop Priority Optimizations:")
            for opp in high_priority:
                print(f"• {opp.description} - {opp.expected_improvement}")

    except KeyboardInterrupt:
        print("\nAdvanced performance analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nAdvanced performance analysis failed: {e}")
        logger.exception("Advanced analysis failed with exception")
        sys.exit(1)
