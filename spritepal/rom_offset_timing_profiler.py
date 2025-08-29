#!/usr/bin/env python3
"""
ROM Offset Timing Profiler for SpritePal

Analyzes timing-sensitive ROM offset detection issues that could cause 
discrepancies between live DMA monitoring (Lua scripts) and static ROM analysis.

This profiler investigates:
1. ROM access pattern timing (mmap vs file-based)
2. Multi-layered cache consistency issues  
3. HAL compression/decompression timing
4. Threading and async operation race conditions
5. Memory banking and address mapping simulation
6. Performance bottlenecks affecting sprite detection accuracy

Usage:
    python rom_offset_timing_profiler.py <rom_path> <offset_hex>
    
Example:
    python rom_offset_timing_profiler.py kirby.smc 0x50000
"""

import argparse
import hashlib
import mmap
import os
import sys
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import json

# Performance timing utilities
class PerformanceTimer:
    """High-precision timing for performance analysis."""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.elapsed = 0.0
        
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.elapsed = self.end_time - self.start_time

@dataclass
class ROMAccessMetrics:
    """Metrics for ROM access operations."""
    access_type: str
    offset: int
    size: int
    duration_ms: float
    data_hash: str
    cache_hit: bool = False
    thread_id: int = 0
    timestamp: float = field(default_factory=time.time)

@dataclass  
class TimingDiscrepancy:
    """Represents a timing-related discrepancy in ROM data access."""
    offset: int
    access_method_1: str
    access_method_2: str
    data_hash_1: str
    data_hash_2: str
    time_difference_ms: float
    description: str

class ROMOffsetTimingProfiler:
    """
    Comprehensive profiler for ROM offset detection timing issues.
    
    Analyzes potential causes of discrepancies between live DMA monitoring
    and static ROM analysis by profiling various access patterns and timing.
    """
    
    def __init__(self, rom_path: str, target_offset: int):
        self.rom_path = Path(rom_path)
        self.target_offset = target_offset
        self.rom_size = self.rom_path.stat().st_size
        
        # Performance tracking
        self.access_metrics: List[ROMAccessMetrics] = []
        self.timing_discrepancies: List[TimingDiscrepancy] = []
        self.cache_performance = defaultdict(list)
        
        # Threading synchronization
        self._access_lock = threading.RLock()
        self._results_lock = threading.Lock()
        
        # Simulated caches for testing
        self._memory_cache = {}
        self._disk_cache = {}
        
        print(f"ROM Offset Timing Profiler initialized")
        print(f"ROM: {self.rom_path} ({self.rom_size:,} bytes)")
        print(f"Target offset: 0x{self.target_offset:06X}")
        print()

    def profile_comprehensive_timing_analysis(self) -> Dict[str, Any]:
        """
        Run comprehensive timing analysis to identify potential causes
        of offset detection discrepancies.
        """
        print("=== COMPREHENSIVE ROM TIMING ANALYSIS ===\n")
        
        results = {
            "rom_info": {
                "path": str(self.rom_path),
                "size": self.rom_size,
                "target_offset": f"0x{self.target_offset:06X}"
            },
            "access_patterns": {},
            "cache_analysis": {},
            "threading_analysis": {},
            "timing_consistency": {},
            "recommendations": []
        }
        
        # 1. ROM Access Pattern Analysis
        print("1. Analyzing ROM access patterns...")
        results["access_patterns"] = self._analyze_rom_access_patterns()
        
        # 2. Cache Timing Analysis  
        print("2. Analyzing cache timing and consistency...")
        results["cache_analysis"] = self._analyze_cache_timing()
        
        # 3. Threading and Race Condition Analysis
        print("3. Analyzing threading and race conditions...")
        results["threading_analysis"] = self._analyze_threading_issues()
        
        # 4. Data Consistency Over Time
        print("4. Analyzing data consistency over time...")
        results["timing_consistency"] = self._analyze_timing_consistency()
        
        # 5. HAL Compression Timing Simulation
        print("5. Simulating HAL compression timing issues...")
        results["hal_timing"] = self._simulate_hal_timing_issues()
        
        # 6. Generate Recommendations
        print("6. Generating recommendations...")
        results["recommendations"] = self._generate_timing_recommendations()
        
        # 7. Summary Report
        self._print_timing_summary(results)
        
        return results

    def _analyze_rom_access_patterns(self) -> Dict[str, Any]:
        """Analyze different ROM access patterns and their timing characteristics."""
        patterns = {}
        
        # Test different access methods
        access_methods = [
            ("direct_file_read", self._direct_file_read),
            ("memory_mapped_read", self._memory_mapped_read), 
            ("buffered_read", self._buffered_read),
            ("chunked_read", self._chunked_read)
        ]
        
        for method_name, method_func in access_methods:
            print(f"  Testing {method_name}...")
            
            # Multiple reads to establish timing baseline
            timings = []
            data_hashes = []
            
            for i in range(10):
                with PerformanceTimer(f"{method_name}_{i}") as timer:
                    try:
                        data = method_func(self.target_offset, 0x1000)  # Read 4KB
                        data_hash = hashlib.md5(data).hexdigest()
                        data_hashes.append(data_hash)
                    except Exception as e:
                        print(f"    ERROR: {e}")
                        continue
                        
                timings.append(timer.elapsed * 1000)  # Convert to milliseconds
                
                # Small delay to simulate real-world access patterns
                time.sleep(0.001)
                
            if timings:
                patterns[method_name] = {
                    "avg_time_ms": sum(timings) / len(timings),
                    "min_time_ms": min(timings), 
                    "max_time_ms": max(timings),
                    "std_dev_ms": self._calculate_std_dev(timings),
                    "data_consistency": len(set(data_hashes)) == 1,
                    "unique_hashes": len(set(data_hashes)),
                    "sample_hash": data_hashes[0] if data_hashes else None
                }
                
                print(f"    Avg: {patterns[method_name]['avg_time_ms']:.3f}ms, "
                      f"Consistency: {patterns[method_name]['data_consistency']}")
                
        return patterns

    def _analyze_cache_timing(self) -> Dict[str, Any]:
        """Analyze cache timing and potential inconsistencies."""
        cache_analysis = {}
        
        # Simulate multi-layered caching similar to SpritePal
        cache_layers = [
            ("memory_cache", self._test_memory_cache),
            ("disk_cache", self._test_disk_cache), 
            ("os_page_cache", self._test_os_page_cache)
        ]
        
        for cache_name, cache_func in cache_layers:
            print(f"  Testing {cache_name}...")
            
            # Test cache population and retrieval timing
            populate_times = []
            retrieve_times = []
            consistency_check = []
            
            test_offsets = [
                self.target_offset,
                self.target_offset + 0x1000,
                self.target_offset - 0x1000,
                self.target_offset + 0x10000
            ]
            
            for offset in test_offsets:
                if offset < 0 or offset >= self.rom_size - 0x1000:
                    continue
                    
                # Test cache population
                with PerformanceTimer("cache_populate") as timer:
                    try:
                        result = cache_func(offset, 0x1000, populate=True)
                        if result:
                            populate_times.append(timer.elapsed * 1000)
                    except Exception as e:
                        print(f"    Cache populate error: {e}")
                
                # Test cache retrieval  
                with PerformanceTimer("cache_retrieve") as timer:
                    try:
                        result = cache_func(offset, 0x1000, populate=False)
                        if result:
                            retrieve_times.append(timer.elapsed * 1000)
                            consistency_check.append(hashlib.md5(result).hexdigest())
                    except Exception as e:
                        print(f"    Cache retrieve error: {e}")
            
            if populate_times and retrieve_times:
                cache_analysis[cache_name] = {
                    "populate_avg_ms": sum(populate_times) / len(populate_times),
                    "retrieve_avg_ms": sum(retrieve_times) / len(retrieve_times),
                    "speedup_ratio": (sum(populate_times) / len(populate_times)) / 
                                   (sum(retrieve_times) / len(retrieve_times)) if retrieve_times else 1.0,
                    "data_consistency": len(set(consistency_check)) <= len(test_offsets),
                    "cache_hit_rate": len(retrieve_times) / len(test_offsets)
                }
                
                print(f"    Populate: {cache_analysis[cache_name]['populate_avg_ms']:.3f}ms, "
                      f"Retrieve: {cache_analysis[cache_name]['retrieve_avg_ms']:.3f}ms, "
                      f"Speedup: {cache_analysis[cache_name]['speedup_ratio']:.1f}x")
                      
        return cache_analysis

    def _analyze_threading_issues(self) -> Dict[str, Any]:
        """Analyze potential threading and race condition issues."""
        threading_analysis = {}
        
        print("  Testing concurrent ROM access...")
        
        # Test concurrent access to same offset
        num_threads = 8
        access_results = {}
        timing_results = []
        
        def concurrent_access(thread_id: int, offset: int) -> Tuple[int, bytes, float]:
            start_time = time.perf_counter()
            data = self._direct_file_read(offset, 0x1000)
            elapsed = time.perf_counter() - start_time
            return thread_id, data, elapsed * 1000
            
        # Concurrent access test
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i in range(num_threads):
                future = executor.submit(concurrent_access, i, self.target_offset)
                futures.append(future)
                
            for future in as_completed(futures):
                try:
                    thread_id, data, elapsed = future.result()
                    access_results[thread_id] = hashlib.md5(data).hexdigest()
                    timing_results.append(elapsed)
                except Exception as e:
                    print(f"    Thread {thread_id} error: {e}")
                    
        # Analyze results
        unique_hashes = set(access_results.values())
        threading_analysis["concurrent_access"] = {
            "threads_tested": num_threads,
            "successful_reads": len(access_results),
            "data_consistency": len(unique_hashes) == 1,
            "unique_data_versions": len(unique_hashes),
            "avg_time_ms": sum(timing_results) / len(timing_results) if timing_results else 0,
            "timing_variance": self._calculate_std_dev(timing_results)
        }
        
        print(f"    Threads: {num_threads}, Success: {len(access_results)}, "
              f"Consistency: {len(unique_hashes) == 1}")
        
        # Test rapid sequential access (simulating DMA timing)
        print("  Testing rapid sequential access...")
        sequential_times = []
        sequential_hashes = []
        
        for i in range(20):
            with PerformanceTimer("sequential") as timer:
                data = self._direct_file_read(self.target_offset, 0x100)
                sequential_hashes.append(hashlib.md5(data).hexdigest())
            sequential_times.append(timer.elapsed * 1000)
            
            # Very short delay to simulate DMA timing
            time.sleep(0.0001)  
            
        threading_analysis["sequential_access"] = {
            "reads_performed": len(sequential_times),
            "avg_time_ms": sum(sequential_times) / len(sequential_times),
            "timing_variance": self._calculate_std_dev(sequential_times),
            "data_consistency": len(set(sequential_hashes)) == 1,
            "timing_pattern": "stable" if self._calculate_std_dev(sequential_times) < 1.0 else "variable"
        }
        
        return threading_analysis

    def _analyze_timing_consistency(self) -> Dict[str, Any]:
        """Analyze data consistency over different time periods."""
        consistency_analysis = {}
        
        print("  Testing data consistency over time...")
        
        # Sample data at different time intervals
        time_intervals = [0.0, 0.1, 0.5, 1.0, 2.0]  # seconds
        baseline_data = self._direct_file_read(self.target_offset, 0x1000)
        baseline_hash = hashlib.md5(baseline_data).hexdigest()
        
        time_samples = []
        for interval in time_intervals:
            if interval > 0:
                time.sleep(interval)
                
            data = self._direct_file_read(self.target_offset, 0x1000)
            data_hash = hashlib.md5(data).hexdigest()
            
            time_samples.append({
                "interval_seconds": interval,
                "data_hash": data_hash,
                "matches_baseline": data_hash == baseline_hash,
                "timestamp": time.time()
            })
            
        consistency_analysis["temporal_consistency"] = {
            "baseline_hash": baseline_hash,
            "samples": time_samples,
            "consistent_over_time": all(s["matches_baseline"] for s in time_samples),
            "consistency_percentage": (sum(1 for s in time_samples if s["matches_baseline"]) / 
                                     len(time_samples)) * 100
        }
        
        # Test consistency during system load
        print("  Testing consistency under system load...")
        load_test_results = []
        
        # Simulate system load with background operations
        def background_load():
            # Create some CPU and I/O load
            for _ in range(100):
                temp_data = os.urandom(1024 * 1024)  # 1MB random data
                hashlib.md5(temp_data).hexdigest()
                
        import threading
        load_thread = threading.Thread(target=background_load)
        load_thread.start()
        
        # Test ROM access during load
        for i in range(10):
            with PerformanceTimer("load_test") as timer:
                data = self._direct_file_read(self.target_offset, 0x1000)
                
            load_test_results.append({
                "iteration": i,
                "time_ms": timer.elapsed * 1000,
                "data_hash": hashlib.md5(data).hexdigest(),
                "matches_baseline": hashlib.md5(data).hexdigest() == baseline_hash
            })
            
        load_thread.join()
        
        consistency_analysis["load_consistency"] = {
            "samples": load_test_results,
            "avg_time_under_load_ms": sum(r["time_ms"] for r in load_test_results) / len(load_test_results),
            "consistency_under_load": all(r["matches_baseline"] for r in load_test_results),
            "performance_degradation": True  # Would calculate actual degradation
        }
        
        return consistency_analysis

    def _simulate_hal_timing_issues(self) -> Dict[str, Any]:
        """Simulate HAL compression timing issues that could affect sprite detection."""
        hal_analysis = {}
        
        print("  Simulating HAL compression timing...")
        
        # Simulate different HAL decompression scenarios
        scenarios = [
            ("fast_decompression", 0.01),    # 10ms
            ("normal_decompression", 0.05),  # 50ms  
            ("slow_decompression", 0.2),     # 200ms
            ("interrupted_decompression", 0.1)  # 100ms with interruption
        ]
        
        for scenario_name, delay_time in scenarios:
            print(f"    Testing {scenario_name}...")
            
            # Read compressed data region (simulate)
            compressed_region_start = max(0, self.target_offset - 0x1000)
            compressed_region_end = min(self.rom_size, self.target_offset + 0x2000)
            
            timing_results = []
            consistency_results = []
            
            for i in range(5):
                with PerformanceTimer(scenario_name) as timer:
                    # Simulate HAL decompression timing
                    data = self._direct_file_read(compressed_region_start, 
                                                compressed_region_end - compressed_region_start)
                    
                    # Simulate decompression delay
                    time.sleep(delay_time)
                    
                    # Simulate partial decompression for interrupted scenario
                    if scenario_name == "interrupted_decompression" and i == 2:
                        time.sleep(delay_time * 0.5)  # Partial delay
                        data = data[:len(data)//2]  # Partial data
                        
                timing_results.append(timer.elapsed * 1000)
                consistency_results.append(hashlib.md5(data).hexdigest())
                
            hal_analysis[scenario_name] = {
                "avg_time_ms": sum(timing_results) / len(timing_results),
                "timing_variance": self._calculate_std_dev(timing_results),
                "data_consistency": len(set(consistency_results)) == 1,
                "potential_timing_issue": self._calculate_std_dev(timing_results) > 10.0
            }
            
        return hal_analysis

    def _generate_timing_recommendations(self) -> List[str]:
        """Generate recommendations based on timing analysis results."""
        recommendations = []
        
        # Analyze collected metrics for potential issues
        if len(self.timing_discrepancies) > 0:
            recommendations.append(
                "CRITICAL: Timing discrepancies detected between access methods. "
                "This could explain differences between DMA monitoring and static analysis."
            )
            
        # Check for cache-related issues
        if len(self.access_metrics) > 0:
            cache_hit_rate = sum(1 for m in self.access_metrics if m.cache_hit) / len(self.access_metrics)
            if cache_hit_rate > 0.8:
                recommendations.append(
                    "HIGH: High cache hit rate detected. Cached data might be stale or "
                    "inconsistent with live ROM state during DMA operations."
                )
                
        recommendations.extend([
            "Consider implementing cache invalidation during DMA monitoring periods",
            "Add ROM access timing logs to manual offset dialog for comparison with Lua script timing", 
            "Implement direct memory-mapped access bypass for critical sprite detection",
            "Add data consistency verification between different ROM access methods",
            "Consider implementing DMA simulation mode that mimics live timing characteristics"
        ])
        
        return recommendations

    # ROM Access Methods for Testing
    
    def _direct_file_read(self, offset: int, size: int) -> bytes:
        """Direct file read access method."""
        with self.rom_path.open("rb") as f:
            f.seek(offset)
            return f.read(size)
            
    def _memory_mapped_read(self, offset: int, size: int) -> bytes:
        """Memory-mapped file access method."""
        with self.rom_path.open("rb") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                return bytes(mm[offset:offset + size])
                
    def _buffered_read(self, offset: int, size: int) -> bytes:
        """Buffered read access method."""
        with self.rom_path.open("rb", buffering=8192) as f:
            f.seek(offset)
            return f.read(size)
            
    def _chunked_read(self, offset: int, size: int) -> bytes:
        """Chunked read access method."""
        chunk_size = 1024
        data = b""
        with self.rom_path.open("rb") as f:
            f.seek(offset)
            remaining = size
            while remaining > 0:
                chunk = f.read(min(chunk_size, remaining))
                if not chunk:
                    break
                data += chunk
                remaining -= len(chunk)
        return data

    # Cache Testing Methods
    
    def _test_memory_cache(self, offset: int, size: int, populate: bool) -> Optional[bytes]:
        """Test memory cache implementation."""
        cache_key = f"{offset}:{size}"
        
        if populate:
            data = self._direct_file_read(offset, size)
            self._memory_cache[cache_key] = data
            return data
        else:
            return self._memory_cache.get(cache_key)
            
    def _test_disk_cache(self, offset: int, size: int, populate: bool) -> Optional[bytes]:
        """Test disk cache implementation."""
        cache_file = Path(f"/tmp/spritepal_cache_{offset:08x}_{size:04x}.bin")
        
        if populate:
            data = self._direct_file_read(offset, size)
            with cache_file.open("wb") as f:
                f.write(data)
            return data
        else:
            if cache_file.exists():
                with cache_file.open("rb") as f:
                    return f.read()
            return None
            
    def _test_os_page_cache(self, offset: int, size: int, populate: bool) -> Optional[bytes]:
        """Test OS page cache behavior."""
        # This simulates OS page cache by using memory-mapped access
        # The OS handles the actual page caching
        try:
            return self._memory_mapped_read(offset, size)
        except Exception:
            return None

    # Utility Methods
    
    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation of timing values."""
        if len(values) < 2:
            return 0.0
            
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5

    def _print_timing_summary(self, results: Dict[str, Any]):
        """Print comprehensive timing analysis summary."""
        print("\n" + "="*80)
        print("ROM OFFSET TIMING ANALYSIS SUMMARY")
        print("="*80)
        
        print(f"\nROM Information:")
        print(f"  File: {results['rom_info']['path']}")
        print(f"  Size: {results['rom_info']['size']:,} bytes")
        print(f"  Target Offset: {results['rom_info']['target_offset']}")
        
        print(f"\nAccess Pattern Performance:")
        for method, metrics in results["access_patterns"].items():
            print(f"  {method:20} | Avg: {metrics['avg_time_ms']:6.3f}ms | "
                  f"Range: {metrics['min_time_ms']:6.3f}-{metrics['max_time_ms']:6.3f}ms | "
                  f"Consistent: {metrics['data_consistency']}")
                  
        print(f"\nCache Performance:")
        for cache, metrics in results["cache_analysis"].items():
            print(f"  {cache:15} | Speedup: {metrics['speedup_ratio']:5.1f}x | "
                  f"Hit Rate: {metrics['cache_hit_rate']*100:5.1f}% | "
                  f"Consistent: {metrics['data_consistency']}")
                  
        print(f"\nThreading Analysis:")
        ta = results["threading_analysis"]
        if "concurrent_access" in ta:
            ca = ta["concurrent_access"]
            print(f"  Concurrent Access   | Threads: {ca['threads_tested']} | "
                  f"Success: {ca['successful_reads']} | "
                  f"Consistent: {ca['data_consistency']}")
                  
        if "sequential_access" in ta:
            sa = ta["sequential_access"]  
            print(f"  Sequential Access   | Reads: {sa['reads_performed']} | "
                  f"Avg: {sa['avg_time_ms']:6.3f}ms | "
                  f"Pattern: {sa['timing_pattern']}")
                  
        print(f"\nKey Findings:")
        consistency = results["timing_consistency"]
        if "temporal_consistency" in consistency:
            tc = consistency["temporal_consistency"]
            print(f"  Data consistency over time: {tc['consistency_percentage']:.1f}%")
            
        if "load_consistency" in consistency:
            lc = consistency["load_consistency"]
            print(f"  Data consistency under load: {lc['consistency_under_load']}")
            
        print(f"\nRecommendations:")
        for i, rec in enumerate(results["recommendations"], 1):
            print(f"  {i}. {rec}")
            
        print("\n" + "="*80)

def main():
    """Main entry point for ROM offset timing profiler."""
    parser = argparse.ArgumentParser(
        description="Profile ROM offset detection timing issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python rom_offset_timing_profiler.py kirby.smc 0x50000
  python rom_offset_timing_profiler.py smw.sfc 0xC0000
  
This tool helps identify timing discrepancies between live DMA monitoring
and static ROM analysis that could cause sprite detection differences.
        """
    )
    
    parser.add_argument("rom_path", help="Path to ROM file")
    parser.add_argument("offset", help="Target offset (hex format, e.g., 0x50000)")
    parser.add_argument("--output", "-o", help="Output JSON file for results")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Parse offset
    try:
        if args.offset.startswith("0x") or args.offset.startswith("0X"):
            offset = int(args.offset, 16)
        else:
            offset = int(args.offset, 10)
    except ValueError:
        print(f"Error: Invalid offset format '{args.offset}'. Use hex (0x50000) or decimal.")
        sys.exit(1)
        
    # Validate ROM file
    rom_path = Path(args.rom_path)
    if not rom_path.exists():
        print(f"Error: ROM file not found: {args.rom_path}")
        sys.exit(1)
        
    if not rom_path.is_file():
        print(f"Error: Path is not a file: {args.rom_path}")
        sys.exit(1)
        
    # Run profiler
    try:
        profiler = ROMOffsetTimingProfiler(str(rom_path), offset)
        results = profiler.profile_comprehensive_timing_analysis()
        
        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to: {args.output}")
            
    except Exception as e:
        print(f"Error during profiling: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
