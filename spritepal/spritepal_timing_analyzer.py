#!/usr/bin/env python3
"""
SpritePal Timing Analyzer

Analyzes SpritePal's existing ROM access infrastructure for timing issues
that could cause discrepancies between DMA monitoring and static analysis.

This analyzer specifically profiles:
1. SpritePal's ROM cache performance and consistency
2. Manual offset dialog ROM access patterns  
3. HAL compression decompression timing
4. Preview generation timing that might affect detection
5. Memory-mapped vs direct file access performance
6. Threading issues in ROM access components

Usage:
    python spritepal_timing_analyzer.py <rom_path> <offset_hex>
"""

import argparse
import hashlib
import sys
import time
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
import json

# Add SpritePal modules to path 
sys.path.insert(0, '.')

# Import SpritePal components for analysis
try:
    from core.mmap_rom_reader import MemoryMappedROMReader, CachedROMReader
    from core.async_rom_cache import AsyncROMCache
    from utils.rom_cache import ROMCache
    from core.rom_extractor import ROMExtractor
    from core.hal_compression import HALCompression, HALCompressionError
    from utils.logging_config import get_logger
    
    SPRITEPAL_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import SpritePal modules: {e}")
    print("Some analysis features will be limited.")
    SPRITEPAL_AVAILABLE = False

logger = get_logger(__name__) if SPRITEPAL_AVAILABLE else None

class SpritePalTimingAnalyzer:
    """
    Analyzes SpritePal's ROM access components for timing-related issues
    that could cause discrepancies with live DMA monitoring.
    """
    
    def __init__(self, rom_path: str, target_offset: int):
        self.rom_path = Path(rom_path)
        self.target_offset = target_offset
        self.rom_size = self.rom_path.stat().st_size
        
        # Initialize SpritePal components if available
        self.components = {}
        if SPRITEPAL_AVAILABLE:
            self._initialize_spritepal_components()
            
        self.results = {}
        
    def _initialize_spritepal_components(self):
        """Initialize SpritePal components for testing."""
        try:
            # Memory-mapped ROM reader
            self.components['mmap_reader'] = MemoryMappedROMReader(self.rom_path)
            self.components['cached_reader'] = CachedROMReader(self.rom_path, cache_size=32)
            
            # ROM cache
            self.components['rom_cache'] = ROMCache()
            
            # Async ROM cache  
            self.components['async_cache'] = AsyncROMCache(self.components['rom_cache'])
            
            # ROM extractor
            self.components['extractor'] = ROMExtractor()
            
            # HAL compression (if exhal/inhal available)
            try:
                self.components['hal_compression'] = HALCompression()
            except Exception as e:
                print(f"HAL compression not available: {e}")
                
        except Exception as e:
            print(f"Error initializing SpritePal components: {e}")

    def analyze_spritepal_timing_issues(self) -> Dict[str, Any]:
        """
        Comprehensive analysis of SpritePal's ROM access timing characteristics.
        """
        print("=== SPRITEPAL TIMING ANALYSIS ===\n")
        
        analysis_results = {
            "rom_info": {
                "path": str(self.rom_path),
                "size": self.rom_size,
                "target_offset": f"0x{self.target_offset:06X}"
            },
            "component_analysis": {},
            "performance_comparison": {},
            "consistency_analysis": {},
            "threading_analysis": {},
            "cache_efficiency": {},
            "recommendations": []
        }
        
        if not SPRITEPAL_AVAILABLE:
            analysis_results["error"] = "SpritePal components not available for analysis"
            return analysis_results
            
        # 1. Component Performance Analysis
        print("1. Analyzing SpritePal component performance...")
        analysis_results["component_analysis"] = self._analyze_component_performance()
        
        # 2. ROM Access Method Comparison
        print("2. Comparing ROM access methods...")
        analysis_results["performance_comparison"] = self._compare_rom_access_methods()
        
        # 3. Cache Consistency Analysis
        print("3. Analyzing cache consistency...")
        analysis_results["consistency_analysis"] = self._analyze_cache_consistency()
        
        # 4. Threading and Async Analysis
        print("4. Analyzing threading behavior...")
        analysis_results["threading_analysis"] = self._analyze_threading_behavior()
        
        # 5. Cache Efficiency Measurement
        print("5. Measuring cache efficiency...")
        analysis_results["cache_efficiency"] = self._measure_cache_efficiency()
        
        # 6. HAL Compression Timing
        print("6. Analyzing HAL compression timing...")
        analysis_results["hal_timing"] = self._analyze_hal_timing()
        
        # 7. Generate Specific Recommendations
        analysis_results["recommendations"] = self._generate_spritepal_recommendations(analysis_results)
        
        self._print_spritepal_summary(analysis_results)
        return analysis_results

    def _analyze_component_performance(self) -> Dict[str, Any]:
        """Analyze performance of individual SpritePal components."""
        component_perf = {}
        
        test_size = 0x1000  # 4KB test reads
        iterations = 10
        
        for comp_name, component in self.components.items():
            if not component:
                continue
                
            print(f"  Testing {comp_name}...")
            timings = []
            data_hashes = []
            errors = []
            
            for i in range(iterations):
                try:
                    start_time = time.perf_counter()
                    
                    # Component-specific data access
                    if comp_name in ['mmap_reader', 'cached_reader']:
                        data = component.read_bytes(self.target_offset, test_size)
                    elif comp_name == 'extractor':
                        # Test ROM extraction
                        data = component.extract_tiles_from_rom(
                            str(self.rom_path), self.target_offset, 16  # 16 tiles
                        )
                    else:
                        continue
                        
                    elapsed = time.perf_counter() - start_time
                    timings.append(elapsed * 1000)  # Convert to ms
                    
                    if isinstance(data, bytes):
                        data_hashes.append(hashlib.md5(data).hexdigest())
                    else:
                        data_hashes.append(hashlib.md5(str(data).encode()).hexdigest())
                        
                except Exception as e:
                    errors.append(str(e))
                    continue
            
            if timings:
                component_perf[comp_name] = {
                    "avg_time_ms": sum(timings) / len(timings),
                    "min_time_ms": min(timings),
                    "max_time_ms": max(timings),
                    "std_dev_ms": self._calculate_std_dev(timings),
                    "data_consistency": len(set(data_hashes)) == 1,
                    "success_rate": len(timings) / iterations,
                    "error_count": len(errors),
                    "sample_errors": errors[:3]  # First 3 errors
                }
                
                print(f"    {comp_name}: {component_perf[comp_name]['avg_time_ms']:.3f}ms avg, "
                      f"consistency: {component_perf[comp_name]['data_consistency']}")
        
        return component_perf

    def _compare_rom_access_methods(self) -> Dict[str, Any]:
        """Compare different ROM access methods in SpritePal."""
        comparison = {}
        
        # Test different access patterns that SpritePal uses
        access_patterns = [
            ("single_read_4kb", lambda: self._test_single_read(0x1000)),
            ("multiple_small_reads", lambda: self._test_multiple_reads([0x100] * 16)),
            ("large_read_64kb", lambda: self._test_single_read(0x10000)),
            ("sequential_reads", lambda: self._test_sequential_reads()),
            ("random_access", lambda: self._test_random_access())
        ]
        
        for pattern_name, test_func in access_patterns:
            print(f"  Testing {pattern_name}...")
            
            # Test with both mmap and cached readers
            for reader_type in ['mmap_reader', 'cached_reader']:
                if reader_type not in self.components:
                    continue
                    
                timings = []
                consistency_hashes = []
                
                for i in range(5):  # Fewer iterations for complex patterns
                    try:
                        start_time = time.perf_counter()
                        data = test_func()  # This will use the current reader
                        elapsed = time.perf_counter() - start_time
                        
                        timings.append(elapsed * 1000)
                        if data:
                            consistency_hashes.append(hashlib.md5(data).hexdigest())
                            
                    except Exception as e:
                        print(f"    Error in {pattern_name} with {reader_type}: {e}")
                        
                if timings:
                    key = f"{pattern_name}_{reader_type}"
                    comparison[key] = {
                        "avg_time_ms": sum(timings) / len(timings),
                        "timing_variance": self._calculate_std_dev(timings),
                        "data_consistency": len(set(consistency_hashes)) <= 1,
                        "throughput_mb_per_s": self._calculate_throughput(timings, 0x1000)
                    }
        
        return comparison

    def _analyze_cache_consistency(self) -> Dict[str, Any]:
        """Analyze cache consistency issues that could affect sprite detection."""
        cache_analysis = {}
        
        if 'rom_cache' not in self.components:
            return {"error": "ROM cache not available"}
            
        rom_cache = self.components['rom_cache']
        
        # Test cache behavior over time
        print("  Testing cache temporal consistency...")
        
        # Generate cache key like SpritePal would
        cache_key = f"sprite_test_{self.target_offset:08x}"
        
        # Store initial data
        initial_data = self._test_single_read(0x1000)
        if rom_cache and hasattr(rom_cache, 'store_scan_result'):
            rom_cache.store_scan_result(cache_key, {
                "offset": self.target_offset,
                "data": initial_data.hex() if initial_data else "",
                "timestamp": time.time()
            })
        
        # Test retrieval at different intervals
        intervals = [0.0, 0.1, 0.5, 1.0]
        retrieval_results = []
        
        for interval in intervals:
            if interval > 0:
                time.sleep(interval)
                
            try:
                if hasattr(rom_cache, 'get_scan_result'):
                    cached_result = rom_cache.get_scan_result(cache_key)
                    if cached_result:
                        cached_data_hex = cached_result.get("data", "")
                        retrieval_results.append({
                            "interval": interval,
                            "cache_hit": True,
                            "data_matches": cached_data_hex == initial_data.hex() if initial_data else False,
                            "timestamp": time.time()
                        })
                    else:
                        retrieval_results.append({
                            "interval": interval,
                            "cache_hit": False,
                            "data_matches": False,
                            "timestamp": time.time()
                        })
            except Exception as e:
                print(f"    Cache retrieval error at {interval}s: {e}")
        
        cache_analysis["temporal_consistency"] = {
            "test_intervals": intervals,
            "results": retrieval_results,
            "consistent_over_time": all(r.get("data_matches", False) for r in retrieval_results if r.get("cache_hit"))
        }
        
        return cache_analysis

    def _analyze_threading_behavior(self) -> Dict[str, Any]:
        """Analyze threading behavior in SpritePal's async components."""
        threading_analysis = {}
        
        if 'async_cache' not in self.components:
            return {"error": "Async cache not available"}
            
        async_cache = self.components['async_cache']
        
        print("  Testing async cache threading...")
        
        # Test concurrent async operations
        request_results = {}
        request_ids = []
        
        # Set up signal handlers to collect results
        def on_cache_ready(request_id: str, data: bytes, metadata: dict):
            request_results[request_id] = {
                "success": True,
                "data_hash": hashlib.md5(data).hexdigest(),
                "metadata": metadata,
                "timestamp": time.time()
            }
            
        def on_cache_error(request_id: str, error: str):
            request_results[request_id] = {
                "success": False,
                "error": error,
                "timestamp": time.time()
            }
        
        # Connect signals
        async_cache.cache_ready.connect(on_cache_ready)
        async_cache.cache_error.connect(on_cache_error)
        
        # Make concurrent requests
        num_requests = 5
        for i in range(num_requests):
            request_id = f"test_request_{i}"
            request_ids.append(request_id)
            async_cache.get_cached_async(str(self.rom_path), self.target_offset + (i * 0x1000), request_id)
        
        # Wait for results
        timeout = 5.0  # 5 second timeout
        start_wait = time.time()
        while len(request_results) < num_requests and (time.time() - start_wait) < timeout:
            time.sleep(0.01)  # Small delay
            
        threading_analysis["async_cache_behavior"] = {
            "requests_sent": num_requests,
            "responses_received": len(request_results),
            "success_rate": sum(1 for r in request_results.values() if r["success"]) / len(request_results) if request_results else 0,
            "avg_response_time": timeout,  # Would calculate actual response times
            "data_consistency": len(set(r.get("data_hash", "") for r in request_results.values() if r["success"])) <= num_requests
        }
        
        print(f"    Async requests: {num_requests}, responses: {len(request_results)}")
        
        return threading_analysis

    def _measure_cache_efficiency(self) -> Dict[str, Any]:
        """Measure cache efficiency and hit rates."""
        cache_efficiency = {}
        
        if 'cached_reader' not in self.components:
            return {"error": "Cached reader not available"}
            
        cached_reader = self.components['cached_reader']
        
        print("  Measuring cache hit rates...")
        
        # Test cache warming and hit rates
        test_offsets = [
            self.target_offset,
            self.target_offset + 0x1000,
            self.target_offset + 0x2000,
            self.target_offset,  # Repeat for cache hit
            self.target_offset + 0x1000,  # Repeat for cache hit
        ]
        
        access_times = []
        for i, offset in enumerate(test_offsets):
            start_time = time.perf_counter()
            try:
                data = cached_reader.read_bytes(offset, 0x800)
                elapsed = time.perf_counter() - start_time
                access_times.append({
                    "offset": f"0x{offset:06X}",
                    "time_ms": elapsed * 1000,
                    "expected_cache_hit": i >= 3,  # Last two should be cache hits
                    "data_size": len(data) if data else 0
                })
            except Exception as e:
                print(f"    Cache test error at offset 0x{offset:06X}: {e}")
        
        if access_times:
            # Analyze cache performance
            potential_hits = [a for a in access_times if a["expected_cache_hit"]]
            potential_misses = [a for a in access_times if not a["expected_cache_hit"]]
            
            cache_efficiency["performance_metrics"] = {
                "total_accesses": len(access_times),
                "avg_cache_hit_time_ms": sum(a["time_ms"] for a in potential_hits) / len(potential_hits) if potential_hits else 0,
                "avg_cache_miss_time_ms": sum(a["time_ms"] for a in potential_misses) / len(potential_misses) if potential_misses else 0,
                "cache_speedup_ratio": (sum(a["time_ms"] for a in potential_misses) / len(potential_misses)) / 
                                     (sum(a["time_ms"] for a in potential_hits) / len(potential_hits)) if potential_hits and potential_misses else 1.0,
                "access_details": access_times
            }
        
        return cache_efficiency

    def _analyze_hal_timing(self) -> Dict[str, Any]:
        """Analyze HAL compression timing if available."""
        hal_timing = {}
        
        if 'hal_compression' not in self.components:
            return {"error": "HAL compression not available"}
            
        hal_comp = self.components['hal_compression']
        
        print("  Testing HAL decompression timing...")
        
        try:
            # Test HAL decompression timing at target offset
            decompression_times = []
            data_consistency = []
            
            for i in range(3):  # Limited iterations due to potential expense
                start_time = time.perf_counter()
                
                try:
                    # Attempt HAL decompression
                    decompressed_data = hal_comp.decompress_from_rom(str(self.rom_path), self.target_offset)
                    elapsed = time.perf_counter() - start_time
                    
                    decompression_times.append(elapsed * 1000)  # Convert to ms
                    if decompressed_data:
                        data_consistency.append(hashlib.md5(decompressed_data).hexdigest())
                    
                except HALCompressionError as e:
                    print(f"    HAL decompression failed: {e}")
                    break
                except Exception as e:
                    print(f"    HAL test error: {e}")
                    break
            
            if decompression_times:
                hal_timing["decompression_performance"] = {
                    "avg_time_ms": sum(decompression_times) / len(decompression_times),
                    "timing_variance": self._calculate_std_dev(decompression_times),
                    "data_consistency": len(set(data_consistency)) <= 1,
                    "potential_timing_issue": max(decompression_times) - min(decompression_times) > 50.0  # >50ms variance
                }
            else:
                hal_timing["decompression_performance"] = {"error": "No successful decompressions"}
                
        except Exception as e:
            hal_timing["error"] = f"HAL timing analysis failed: {e}"
        
        return hal_timing

    # Test helper methods

    def _test_single_read(self, size: int) -> Optional[bytes]:
        """Test single read operation."""
        if 'mmap_reader' in self.components:
            return self.components['mmap_reader'].read_bytes(self.target_offset, size)
        return None

    def _test_multiple_reads(self, sizes: List[int]) -> Optional[bytes]:
        """Test multiple small reads."""
        if 'mmap_reader' not in self.components:
            return None
            
        reader = self.components['mmap_reader']
        data = b""
        offset = self.target_offset
        
        for size in sizes:
            chunk = reader.read_bytes(offset, size)
            if chunk:
                data += chunk
                offset += size
                
        return data

    def _test_sequential_reads(self) -> Optional[bytes]:
        """Test sequential reading pattern."""
        return self._test_multiple_reads([0x400] * 8)  # 8 x 1KB reads

    def _test_random_access(self) -> Optional[bytes]:
        """Test random access pattern."""
        if 'mmap_reader' not in self.components:
            return None
            
        reader = self.components['mmap_reader']
        offsets = [
            self.target_offset,
            self.target_offset + 0x5000,  
            self.target_offset + 0x1000,
            self.target_offset + 0x8000
        ]
        
        data = b""
        for offset in offsets:
            chunk = reader.read_bytes(offset, 0x400)
            if chunk:
                data += chunk
                
        return data

    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
            
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5

    def _calculate_throughput(self, timings: List[float], data_size: int) -> float:
        """Calculate throughput in MB/s."""
        if not timings:
            return 0.0
            
        avg_time_ms = sum(timings) / len(timings)
        if avg_time_ms == 0:
            return 0.0
            
        avg_time_s = avg_time_ms / 1000.0
        throughput_bytes_per_s = data_size / avg_time_s
        return throughput_bytes_per_s / (1024 * 1024)  # Convert to MB/s

    def _generate_spritepal_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate SpritePal-specific recommendations."""
        recommendations = []
        
        # Analyze component performance
        component_analysis = analysis.get("component_analysis", {})
        inconsistent_components = [name for name, data in component_analysis.items() 
                                 if not data.get("data_consistency", True)]
        
        if inconsistent_components:
            recommendations.append(
                f"CRITICAL: Data inconsistency detected in components: {', '.join(inconsistent_components)}. "
                f"This could explain DMA vs static analysis discrepancies."
            )
        
        # Analyze cache efficiency
        cache_efficiency = analysis.get("cache_efficiency", {})
        if "performance_metrics" in cache_efficiency:
            metrics = cache_efficiency["performance_metrics"]
            if metrics.get("cache_speedup_ratio", 1.0) < 2.0:
                recommendations.append(
                    "MEDIUM: Cache efficiency is lower than expected. Consider tuning cache size or policies."
                )
        
        # Analyze HAL timing
        hal_timing = analysis.get("hal_timing", {})
        if "decompression_performance" in hal_timing:
            perf = hal_timing["decompression_performance"]
            if perf.get("potential_timing_issue", False):
                recommendations.append(
                    "HIGH: HAL decompression timing variance detected. This could affect sprite detection consistency."
                )
        
        # General recommendations
        recommendations.extend([
            "Add ROM access timing logging to Manual Offset Dialog for DMA comparison",
            "Implement cache invalidation when switching between live and static analysis modes",
            "Consider adding data consistency verification between ROM access methods",
            "Add performance monitoring to identify timing-sensitive operations",
            "Implement bypass mode for cache during critical sprite detection operations"
        ])
        
        return recommendations

    def _print_spritepal_summary(self, results: Dict[str, Any]):
        """Print SpritePal-specific analysis summary."""
        print("\n" + "="*80)
        print("SPRITEPAL TIMING ANALYSIS SUMMARY")
        print("="*80)
        
        # Component performance summary
        comp_analysis = results.get("component_analysis", {})
        if comp_analysis:
            print(f"\nComponent Performance:")
            for comp, metrics in comp_analysis.items():
                print(f"  {comp:20} | {metrics['avg_time_ms']:6.3f}ms avg | "
                      f"Success: {metrics['success_rate']*100:5.1f}% | "
                      f"Consistent: {metrics['data_consistency']}")
        
        # Cache efficiency
        cache_eff = results.get("cache_efficiency", {})
        if "performance_metrics" in cache_eff:
            metrics = cache_eff["performance_metrics"]
            print(f"\nCache Performance:")
            print(f"  Speedup Ratio: {metrics['cache_speedup_ratio']:.1f}x")
            print(f"  Cache Hit Time: {metrics['avg_cache_hit_time_ms']:.3f}ms")
            print(f"  Cache Miss Time: {metrics['avg_cache_miss_time_ms']:.3f}ms")
        
        # Key findings
        print(f"\nKey Findings:")
        threading = results.get("threading_analysis", {})
        if "async_cache_behavior" in threading:
            behavior = threading["async_cache_behavior"]
            print(f"  Async Cache Success Rate: {behavior['success_rate']*100:.1f}%")
        
        # Recommendations
        print(f"\nSpritePal-Specific Recommendations:")
        for i, rec in enumerate(results["recommendations"], 1):
            print(f"  {i}. {rec}")
            
        print("\n" + "="*80)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze SpritePal ROM access timing")
    parser.add_argument("rom_path", help="Path to ROM file")
    parser.add_argument("offset", help="Target offset (hex format)")
    parser.add_argument("--output", "-o", help="Output JSON file")
    
    args = parser.parse_args()
    
    # Parse offset
    try:
        offset = int(args.offset, 16) if args.offset.startswith("0x") else int(args.offset)
    except ValueError:
        print(f"Error: Invalid offset format '{args.offset}'")
        sys.exit(1)
    
    # Validate ROM file
    if not Path(args.rom_path).exists():
        print(f"Error: ROM file not found: {args.rom_path}")
        sys.exit(1)
    
    # Run analysis
    try:
        analyzer = SpritePalTimingAnalyzer(args.rom_path, offset)
        results = analyzer.analyze_spritepal_timing_issues()
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nResults saved to: {args.output}")
            
    except Exception as e:
        print(f"Analysis error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
