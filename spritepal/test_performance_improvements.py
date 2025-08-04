#!/usr/bin/env python3
"""
Performance benchmark script for sprite finding improvements.
Tests HAL process pool and empty region detection optimizations.
"""

import os
import sys
import tempfile
import time
from contextlib import contextmanager

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.hal_compression import HALCompressor
from core.region_analyzer import EmptyRegionDetector
from core.sprite_finder import SpriteFinder
from utils.constants import (
    ROM_SCAN_STEP_DEFAULT,
    ROM_SPRITE_AREA_1_END,
    ROM_SPRITE_AREA_1_START,
)
from utils.logging_config import get_logger, setup_logging

# Configure logging for benchmarking
setup_logging(log_level="INFO")
logger = get_logger(__name__)


@contextmanager
def timed_operation(name: str):
    """Context manager to time operations."""
    start = time.time()
    logger.info(f"Starting: {name}")
    yield
    elapsed = time.time() - start
    logger.info(f"Completed: {name} in {elapsed:.2f} seconds")


def create_test_rom(size_mb: int = 2) -> str:
    """Create a test ROM file with realistic data patterns."""
    logger.info(f"Creating test ROM ({size_mb}MB)")

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".smc") as f:
        rom_path = f.name

        # Write ROM data with various patterns
        total_size = size_mb * 1024 * 1024
        chunk_size = 64 * 1024  # 64KB chunks

        for i in range(0, total_size, chunk_size):
            # Simulate different ROM regions
            if i < 0x80000:  # Header/code region
                # Mostly random data
                import random
                data = bytes(random.randint(0, 255) for _ in range(chunk_size))
            elif 0x80000 <= i < 0x180000:  # Sprite regions
                # Mix of empty and sprite-like data
                if (i // chunk_size) % 3 == 0:
                    # Sprite-like data (higher entropy)
                    data = bytes((j * 17 + i) % 256 for j in range(chunk_size))
                else:
                    # Empty regions
                    data = b"\x00" * chunk_size
            else:
                # Padding regions
                data = b"\xFF" * chunk_size

            f.write(data[:min(chunk_size, total_size - i)])

    logger.info(f"Created test ROM: {rom_path}")
    return rom_path


def benchmark_hal_compression(rom_path: str, num_tests: int = 100):
    """Benchmark HAL compression with and without process pool."""
    logger.info("=== HAL Compression Benchmark ===")

    # Test offsets (simulate sprite scanning)
    test_offsets = [ROM_SPRITE_AREA_1_START + i * 0x1000 for i in range(num_tests)]

    # Test 1: Without process pool (subprocess mode)
    logger.info(f"\nTest 1: Subprocess mode ({num_tests} decompressions)")
    compressor_subprocess = HALCompressor(use_pool=False)

    results_subprocess = []
    with timed_operation("Subprocess decompression"):
        for offset in test_offsets:
            start = time.time()
            try:
                compressor_subprocess.decompress_from_rom(rom_path, offset)
                results_subprocess.append(time.time() - start)
            except Exception:
                # Expected to fail on test ROM, we're measuring overhead
                results_subprocess.append(time.time() - start)

    avg_subprocess = sum(results_subprocess) / len(results_subprocess) * 1000  # Convert to ms
    logger.info(f"Average time per decompression: {avg_subprocess:.2f}ms")

    # Test 2: With process pool
    logger.info(f"\nTest 2: Process pool mode ({num_tests} decompressions)")
    compressor_pool = HALCompressor(use_pool=True)

    # Verify pool is initialized
    pool_status = compressor_pool.pool_status
    logger.info(f"Pool status: {pool_status}")

    results_pool = []
    with timed_operation("Pool decompression"):
        for offset in test_offsets:
            start = time.time()
            try:
                compressor_pool.decompress_from_rom(rom_path, offset)
                results_pool.append(time.time() - start)
            except Exception:
                results_pool.append(time.time() - start)

    avg_pool = sum(results_pool) / len(results_pool) * 1000
    logger.info(f"Average time per decompression: {avg_pool:.2f}ms")

    # Test 3: Batch processing
    logger.info(f"\nTest 3: Batch processing ({num_tests} decompressions)")
    batch_requests = [(rom_path, offset) for offset in test_offsets]

    with timed_operation("Batch decompression"):
        batch_results = compressor_pool.decompress_batch(batch_requests)

    successful = sum(1 for success, _ in batch_results if success)
    logger.info(f"Batch results: {successful}/{len(batch_results)} successful")

    # Calculate speedup
    speedup = avg_subprocess / avg_pool if avg_pool > 0 else 0
    logger.info("\n=== HAL Performance Summary ===")
    logger.info(f"Subprocess mode: {avg_subprocess:.2f}ms per operation")
    logger.info(f"Process pool mode: {avg_pool:.2f}ms per operation")
    logger.info(f"Speedup: {speedup:.1f}x")

    return speedup


def benchmark_empty_region_detection(rom_path: str):
    """Benchmark empty region detection."""
    logger.info("\n=== Empty Region Detection Benchmark ===")

    # Read ROM data
    with open(rom_path, "rb") as f:
        rom_data = f.read()

    rom_size = len(rom_data)
    logger.info(f"ROM size: {rom_size:,} bytes")

    # Test region detection
    detector = EmptyRegionDetector()

    with timed_operation("Region analysis"):
        scan_ranges = detector.get_optimized_scan_ranges(rom_data)

    # Calculate statistics
    total_scan_bytes = sum(end - start for start, end in scan_ranges)
    skip_percentage = (1 - total_scan_bytes / rom_size) * 100

    logger.info(f"Detected {len(scan_ranges)} non-empty regions")
    logger.info(f"Total bytes to scan: {total_scan_bytes:,} ({total_scan_bytes/rom_size*100:.1f}%)")
    logger.info(f"Bytes skipped: {rom_size - total_scan_bytes:,} ({skip_percentage:.1f}%)")

    # Test individual region analysis performance
    region_size = 4096  # 4KB
    num_test_regions = 1000

    logger.info(f"\nTesting region analysis performance ({num_test_regions} regions)")
    analysis_times = []

    for i in range(0, min(rom_size, num_test_regions * region_size), region_size):
        region = rom_data[i:i + region_size]
        start = time.time()
        detector.analyze_region(region, i)
        analysis_times.append(time.time() - start)

    avg_analysis_time = sum(analysis_times) / len(analysis_times) * 1000  # ms
    logger.info(f"Average analysis time per 4KB region: {avg_analysis_time:.3f}ms")

    return skip_percentage


def benchmark_sprite_finder(rom_path: str):
    """Benchmark complete sprite finding with all optimizations."""
    logger.info("\n=== Sprite Finder Benchmark ===")

    # Create output directory
    output_dir = "benchmark_output"
    os.makedirs(output_dir, exist_ok=True)

    # Test 1: Traditional scanning (no optimizations)
    logger.info("\nTest 1: Traditional scanning")
    finder_traditional = SpriteFinder(output_dir)

    with timed_operation("Traditional sprite scanning"):
        results_traditional = finder_traditional.find_sprites_in_rom(
            rom_path,
            start_offset=ROM_SPRITE_AREA_1_START,
            end_offset=ROM_SPRITE_AREA_1_END,
            step=ROM_SCAN_STEP_DEFAULT,
            use_region_optimization=False,
            save_previews=False
        )

    logger.info(f"Found {len(results_traditional)} sprite candidates")

    # Test 2: With region optimization
    logger.info("\nTest 2: With region optimization")
    finder_optimized = SpriteFinder(output_dir)

    with timed_operation("Optimized sprite scanning"):
        results_optimized = finder_optimized.find_sprites_in_rom(
            rom_path,
            start_offset=ROM_SPRITE_AREA_1_START,
            end_offset=ROM_SPRITE_AREA_1_END,
            step=ROM_SCAN_STEP_DEFAULT,
            use_region_optimization=True,
            save_previews=False
        )

    logger.info(f"Found {len(results_optimized)} sprite candidates")


def main():
    """Run all performance benchmarks."""
    logger.info("Starting SpritePal Performance Benchmarks")
    logger.info("=" * 60)

    # Create test ROM
    rom_path = create_test_rom(size_mb=4)

    try:
        # Run benchmarks
        hal_speedup = benchmark_hal_compression(rom_path, num_tests=100)
        skip_percentage = benchmark_empty_region_detection(rom_path)
        benchmark_sprite_finder(rom_path)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("PERFORMANCE IMPROVEMENT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"HAL Process Pool Speedup: {hal_speedup:.1f}x")
        logger.info(f"Empty Region Skip Rate: {skip_percentage:.1f}%")
        logger.info(f"Combined Expected Speedup: {hal_speedup * (100/(100-skip_percentage)):.1f}x")
        logger.info("=" * 60)

    finally:
        # Cleanup
        if os.path.exists(rom_path):
            os.unlink(rom_path)
            logger.info(f"Cleaned up test ROM: {rom_path}")


if __name__ == "__main__":
    main()
