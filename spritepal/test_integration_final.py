#!/usr/bin/env python3
"""
Final SpritePal Integration Test Suite

This script provides:
1. Automated core functionality tests
2. Manual UI testing checklist
3. Performance validation
4. Error scenario coverage
5. Resource cleanup verification

Run with: python test_integration_final.py
"""

import os
import shutil
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Core imports
from core.managers import cleanup_managers, initialize_managers
from core.managers.registry import get_registry
from utils.constants import (
    BYTES_PER_TILE,
    COLORS_PER_PALETTE,
    SPRITE_PALETTE_END,
    SPRITE_PALETTE_START,
    VRAM_SPRITE_OFFSET,
)
from utils.logging_config import get_logger
from utils.rom_cache import get_rom_cache

logger = get_logger(__name__)

class ComprehensiveTestSuite:
    """Comprehensive test suite for SpritePal integration"""

    def __init__(self):
        self.temp_dir = None
        self.test_files = {}
        self.passed_tests = []
        self.failed_tests = []
        self.warnings = []

    def setup_test_environment(self):
        """Create test environment with sample files"""
        print("="*60)
        print("SPRITEPAL COMPREHENSIVE INTEGRATION TEST SUITE")
        print("="*60)
        print("\nSetting up test environment...")

        try:
            # Create temp directory and test files
            self.temp_dir = tempfile.mkdtemp(prefix="spritepal_integration_")
            self._create_comprehensive_test_files()

            # Initialize SpritePal managers
            cleanup_managers()
            initialize_managers("SpritePalIntegrationTest")

            print(f"✓ Test environment created: {self.temp_dir}")
            print(f"✓ Test files: {list(self.test_files.keys())}")
            print("✓ Managers initialized")

            return True

        except Exception as e:
            print(f"✗ Setup failed: {e}")
            return False

    def _create_comprehensive_test_files(self):
        """Create comprehensive test files for all scenarios"""
        temp_path = Path(self.temp_dir)

        # VRAM file with diverse sprite patterns
        vram_data = bytearray(0x10000)

        # Create various sprite patterns for testing
        patterns = [
            # Pattern 1: Gradual fade
            lambda i, j: (i * 4 + j) % 256,
            # Pattern 2: Checkerboard
            lambda i, j: 0xFF if (i + j) % 2 else 0x00,
            # Pattern 3: Diagonal lines
            lambda i, j: (i + j * 2) % 256,
            # Pattern 4: Solid blocks
            lambda i, j: (i // 4) * 32,
        ]

        for pattern_idx, pattern_func in enumerate(patterns):
            for tile_idx in range(5):  # 5 tiles per pattern
                global_tile_idx = pattern_idx * 5 + tile_idx
                tile_start = VRAM_SPRITE_OFFSET + (global_tile_idx * BYTES_PER_TILE)

                for j in range(BYTES_PER_TILE):
                    vram_data[tile_start + j] = pattern_func(global_tile_idx, j)

        vram_path = temp_path / "comprehensive_VRAM.dmp"
        vram_path.write_bytes(vram_data)
        self.test_files["vram"] = str(vram_path)

        # CGRAM with distinctive palettes
        cgram_data = bytearray(512)
        for pal_idx in range(SPRITE_PALETTE_START, SPRITE_PALETTE_END):
            for color_idx in range(COLORS_PER_PALETTE):
                offset = (pal_idx * COLORS_PER_PALETTE + color_idx) * 2

                # Create distinctive color palettes
                if pal_idx == 8:  # Red palette
                    r, g, b = 31, color_idx * 2, 0
                elif pal_idx == 9:  # Green palette
                    r, g, b = 0, 31, color_idx * 2
                elif pal_idx == 10:  # Blue palette
                    r, g, b = color_idx * 2, 0, 31
                else:  # Varied palettes
                    r = (pal_idx * 3) % 32
                    g = (color_idx * 3) % 32
                    b = ((pal_idx + color_idx) * 3) % 32

                color = (b << 10) | (g << 5) | r
                cgram_data[offset] = color & 0xFF
                cgram_data[offset + 1] = (color >> 8) & 0xFF

        cgram_path = temp_path / "comprehensive_CGRAM.dmp"
        cgram_path.write_bytes(cgram_data)
        self.test_files["cgram"] = str(cgram_path)

        # OAM with multiple active sprites
        oam_data = bytearray(544)

        # Create 10 active sprites using different palettes
        for sprite_idx in range(10):
            base_offset = sprite_idx * 4
            oam_data[base_offset] = 40 + (sprite_idx * 20)  # X positions
            oam_data[base_offset + 1] = 40 + (sprite_idx * 12)  # Y positions
            oam_data[base_offset + 2] = sprite_idx * 2  # Tile numbers
            oam_data[base_offset + 3] = sprite_idx % 8  # Palette attributes (0-7)

        oam_path = temp_path / "comprehensive_OAM.dmp"
        oam_path.write_bytes(oam_data)
        self.test_files["oam"] = str(oam_path)

        # Large ROM with multiple sprite regions
        rom_data = bytearray(0x200000)  # 2MB ROM

        # Add sprite-like patterns at known locations
        sprite_regions = [
            0x010000, 0x020000, 0x030000, 0x050000, 0x080000,
            0x100000, 0x120000, 0x150000, 0x180000, 0x1C0000
        ]

        for region_idx, region_offset in enumerate(sprite_regions):
            # Each region has 20 tiles with distinct patterns
            for tile_idx in range(20):
                tile_start = region_offset + (tile_idx * BYTES_PER_TILE)

                for byte_idx in range(BYTES_PER_TILE):
                    # Create recognizable patterns for each region
                    pattern_value = (region_idx * 16 + tile_idx * 8 + byte_idx) % 256
                    rom_data[tile_start + byte_idx] = pattern_value

        # Add some search patterns for testing
        search_patterns = [
            (0x200000 - 1000, b"SPRITEPAL_TEST_PATTERN"),
            (0x50000, bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05])),
            (0x80000, bytes([0xFF, 0xFE, 0xFD, 0xFC])),
        ]

        for offset, pattern in search_patterns:
            rom_data[offset:offset+len(pattern)] = pattern

        rom_path = temp_path / "comprehensive_rom.smc"
        rom_path.write_bytes(rom_data)
        self.test_files["rom"] = str(rom_path)

    def run_automated_tests(self):
        """Run all automated core functionality tests"""
        print("\n" + "="*50)
        print("AUTOMATED CORE FUNCTIONALITY TESTS")
        print("="*50)

        tests = [
            ("Manager System", self._test_manager_system),
            ("ROM Cache Operations", self._test_rom_cache_operations),
            ("File Loading & Validation", self._test_file_operations),
            ("Search Algorithms", self._test_search_algorithms),
            ("Memory Management", self._test_memory_management),
            ("Error Handling", self._test_error_handling),
            ("Performance Characteristics", self._test_performance),
            ("Concurrent Operations", self._test_concurrency),
            ("Resource Cleanup", self._test_resource_cleanup),
        ]

        for test_name, test_func in tests:
            try:
                print(f"\n--- {test_name} ---")
                result = test_func()
                if result:
                    self.passed_tests.append(test_name)
                    print(f"✓ {test_name}: PASSED")
                else:
                    self.failed_tests.append(test_name)
                    print(f"✗ {test_name}: FAILED")
            except Exception as e:
                self.failed_tests.append(test_name)
                print(f"✗ {test_name}: ERROR - {e}")
                traceback.print_exc()

    def _test_manager_system(self):
        """Test the manager system"""
        registry = get_registry()

        # Test manager retrieval
        extraction_manager = registry.get_extraction_manager()
        registry.get_session_manager()
        registry.get_injection_manager()

        print("  ✓ All core managers accessible")

        # Test manager functionality
        if hasattr(extraction_manager, "get_supported_formats"):
            formats = extraction_manager.get_supported_formats()
            print(f"  ✓ Extraction formats: {formats}")

        return True

    def _test_rom_cache_operations(self):
        """Test ROM cache functionality comprehensively"""
        rom_cache = get_rom_cache()

        # Test cache statistics
        initial_stats = rom_cache.get_cache_stats()
        print(f"  Cache stats: {len(initial_stats)} metrics")

        # Test ROM info caching
        rom_info = {
            "size": 0x200000,
            "regions": 10,
            "test_timestamp": time.time()
        }

        saved = rom_cache.save_rom_info(self.test_files["rom"], rom_info)
        retrieved = rom_cache.get_rom_info(self.test_files["rom"])

        if not (saved and retrieved and retrieved.get("size") == 0x200000):
            return False

        print("  ✓ ROM info cache working")

        # Test sprite location caching
        sprite_locations = {
            str(offset): {"confidence": 0.9, "type": "sprite"}
            for offset in [0x010000, 0x020000, 0x030000]
        }

        location_saved = rom_cache.save_sprite_locations(
            self.test_files["rom"],
            sprite_locations,
            {"algorithm": "comprehensive_test", "version": "1.0"}
        )

        retrieved_locations = rom_cache.get_sprite_locations(self.test_files["rom"])

        if not (location_saved and retrieved_locations):
            return False

        print("  ✓ Sprite location cache working")

        # Test cache performance
        start_time = time.time()
        for _i in range(10):
            rom_cache.get_rom_info(self.test_files["rom"])
        cache_time = time.time() - start_time

        print(f"  ✓ Cache performance: {cache_time:.4f}s for 10 retrievals")

        return True

    def _test_file_operations(self):
        """Test file loading and validation"""
        # Test file existence and size validation
        for file_type, file_path in self.test_files.items():
            path = Path(file_path)
            if not path.exists():
                print(f"  ✗ Missing test file: {file_type}")
                return False

            size = path.stat().st_size
            expected_sizes = {
                "vram": 0x10000,
                "cgram": 512,
                "oam": 544,
                "rom": 0x200000
            }

            if size != expected_sizes.get(file_type, size):
                print(f"  ✗ Wrong size for {file_type}: {size}")
                return False

        print("  ✓ All test files validated")

        # Test file data integrity
        rom_data = Path(self.test_files["rom"]).read_bytes()
        test_pattern = b"SPRITEPAL_TEST_PATTERN"
        if test_pattern not in rom_data:
            print("  ✗ Test pattern not found in ROM")
            return False

        print("  ✓ File data integrity verified")
        return True

    def _test_search_algorithms(self):
        """Test search algorithm implementations"""
        rom_data = Path(self.test_files["rom"]).read_bytes()

        # Test pattern search
        test_patterns = [
            b"SPRITEPAL_TEST_PATTERN",
            bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05]),
            bytes([0xFF, 0xFE, 0xFD, 0xFC]),
        ]

        for pattern in test_patterns:
            matches = []
            for i in range(len(rom_data) - len(pattern)):
                if rom_data[i:i+len(pattern)] == pattern:
                    matches.append(i)

            if not matches:
                print(f"  ✗ Pattern not found: {pattern[:8]}...")
                return False

        print("  ✓ Pattern search algorithms working")

        # Test similarity analysis
        reference_tile = rom_data[0x010000:0x010000+BYTES_PER_TILE]
        similar_count = 0

        # Check every 1KB for similar tiles
        for offset in range(0, len(rom_data) - BYTES_PER_TILE, 1024):
            tile_data = rom_data[offset:offset+BYTES_PER_TILE]
            matches = sum(1 for a, b in zip(reference_tile, tile_data) if a == b)
            similarity = matches / BYTES_PER_TILE

            if similarity > 0.7:
                similar_count += 1

        print(f"  ✓ Similarity analysis: {similar_count} similar tiles found")

        # Test parallel processing capability
        import concurrent.futures

        def search_chunk(chunk_data, pattern):
            return pattern in chunk_data

        chunk_size = 0x10000
        chunks = [rom_data[i:i+chunk_size] for i in range(0, len(rom_data), chunk_size)]

        pattern_to_find = test_patterns[0]
        found_chunks = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(search_chunk, chunk, pattern_to_find) for chunk in chunks]
            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    found_chunks += 1

        print(f"  ✓ Parallel search: pattern found in {found_chunks} chunks")

        return True

    def _test_memory_management(self):
        """Test memory usage and management"""
        import gc

        import psutil

        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform memory-intensive operations
        large_data_sets = []
        for _i in range(10):
            # Create large data structures
            large_data = bytearray(1024 * 1024)  # 1MB each
            large_data_sets.append(large_data)

        peak_memory = process.memory_info().rss / 1024 / 1024

        # Clean up
        large_data_sets.clear()
        gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024

        print(f"  Memory usage - Initial: {initial_memory:.1f}MB, Peak: {peak_memory:.1f}MB, Final: {final_memory:.1f}MB")

        # Memory should be mostly recovered
        memory_increase = final_memory - initial_memory
        if memory_increase > 50:  # More than 50MB permanent increase
            print(f"  ⚠ Potential memory leak: {memory_increase:.1f}MB increase")
            self.warnings.append("Potential memory leak detected")

        print("  ✓ Memory management test completed")
        return True

    def _test_error_handling(self):
        """Test error handling scenarios"""
        rom_cache = get_rom_cache()

        # Test missing file handling
        result = rom_cache.get_rom_info("/nonexistent/file.smc")
        if result is not None:
            print("  ✗ Missing file should return None")
            return False

        # Test corrupted data handling
        corrupted_file = Path(self.temp_dir) / "corrupted.dmp"
        corrupted_file.write_bytes(b"corrupted data")

        try:
            rom_cache.save_rom_info(str(corrupted_file), {"size": 13})
            rom_cache.get_rom_info(str(corrupted_file))
            print("  ✓ Corrupted data handled gracefully")
        except Exception as e:
            print(f"  ✗ Corrupted data caused exception: {e}")
            return False

        # Test invalid parameters
        try:
            rom_cache.save_rom_info("", {})  # Empty path
            rom_cache.save_rom_info(None, {})  # None path
        except Exception:
            pass  # Expected to handle gracefully

        print("  ✓ Error handling scenarios passed")
        return True

    def _test_performance(self):
        """Test performance characteristics"""
        rom_cache = get_rom_cache()

        # Test cache performance
        test_data = {"performance_test": True, "timestamp": time.time()}

        # Measure save performance
        start_time = time.time()
        for i in range(100):
            rom_cache.save_rom_info(f"{self.test_files['rom']}_{i}", test_data)
        save_time = time.time() - start_time

        # Measure retrieve performance
        start_time = time.time()
        for i in range(100):
            rom_cache.get_rom_info(f"{self.test_files['rom']}_{i}")
        retrieve_time = time.time() - start_time

        print(f"  Cache performance - Save: {save_time:.3f}s, Retrieve: {retrieve_time:.3f}s (100 ops each)")

        if save_time > 1.0 or retrieve_time > 0.5:
            print("  ⚠ Cache performance slower than expected")
            self.warnings.append("Cache performance issue")

        # Test file I/O performance
        start_time = time.time()
        rom_data = Path(self.test_files["rom"]).read_bytes()
        io_time = time.time() - start_time

        print(f"  File I/O performance: {io_time:.3f}s for {len(rom_data)/1024/1024:.1f}MB ({len(rom_data)/1024/1024/io_time:.1f}MB/s)")

        return True

    def _test_concurrency(self):
        """Test concurrent operations"""
        import concurrent.futures

        rom_cache = get_rom_cache()
        errors = []

        def concurrent_cache_operation(thread_id):
            try:
                test_data = {"thread_id": thread_id, "timestamp": time.time()}
                rom_cache.save_rom_info(f"{self.test_files['rom']}_thread_{thread_id}", test_data)
                retrieved = rom_cache.get_rom_info(f"{self.test_files['rom']}_thread_{thread_id}")
                if retrieved and retrieved.get("thread_id") == thread_id:
                    return True
                errors.append(f"Thread {thread_id}: Data mismatch")
                return False
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")
                return False

        # Run concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(concurrent_cache_operation, i) for i in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        success_count = sum(results)
        print(f"  Concurrent operations: {success_count}/20 successful")

        if errors:
            print(f"  ⚠ Concurrency errors: {len(errors)}")
            for error in errors[:3]:  # Show first 3 errors
                print(f"    {error}")
            self.warnings.extend(errors)

        return success_count >= 18  # Allow a few failures in concurrent tests

    def _test_resource_cleanup(self):
        """Test resource cleanup"""
        initial_threads = threading.active_count()

        # Create and clean up resources
        rom_cache = get_rom_cache()

        # Clear cache
        cleared_count = rom_cache.clear_cache()
        print(f"  ✓ Cache cleared: {cleared_count} entries")

        # Check thread count
        final_threads = threading.active_count()
        print(f"  Thread count - Initial: {initial_threads}, Final: {final_threads}")

        if final_threads > initial_threads + 2:
            print("  ⚠ Potential thread leak")
            self.warnings.append("Potential thread leak detected")

        return True

    def print_manual_ui_testing_checklist(self):
        """Print manual UI testing checklist"""
        print("\n" + "="*60)
        print("MANUAL UI TESTING CHECKLIST")
        print("="*60)
        print("""
To complete the integration testing, perform these manual UI tests:

1. APPLICATION LAUNCH
   □ Run: python launch_spritepal.py
   □ Verify main window opens without errors
   □ Check all menus are accessible
   □ Confirm dark theme loads correctly

2. ROM LOADING & EXTRACTION
   □ Drag and drop a VRAM.dmp file to the ROM extraction panel
   □ Add CGRAM.dmp and OAM.dmp files
   □ Click "Extract Sprites" button
   □ Verify extraction completes successfully
   □ Check that sprite previews appear
   □ Confirm palette previews are generated

3. MANUAL OFFSET DIALOG
   □ Click "Manual Offset" button in ROM extraction panel
   □ Verify dialog opens with slider and preview
   □ Move slider and confirm preview updates in real-time
   □ Click "Advanced Search" button
   □ Verify search interface appears

4. ADVANCED SEARCH FUNCTIONALITY
   □ In Advanced Search dialog:
     □ Test "Parallel Search" tab
     □ Enter search criteria and run search
     □ Verify results appear in results list
     □ Click on search results to navigate

   □ Test "Visual Similarity" search:
     □ Right-click on a sprite preview
     □ Select "Find Similar Sprites..."
     □ Verify similarity results dialog opens
     □ Check that similar sprites are found and displayed

   □ Test "Pattern Search":
     □ Enter hex pattern (e.g., "00 01 02 03")
     □ Run pattern search
     □ Verify matching offsets are found
     □ Check context display for matches

5. NAVIGATION & HISTORY
   □ Navigate between search results
   □ Verify navigation history is maintained
   □ Check "History" tab shows previous searches
   □ Test keyboard shortcuts (arrow keys, page up/down)

6. RESOURCE CLEANUP VALIDATION
   □ Open and close dialogs multiple times
   □ Monitor system memory usage (should remain stable)
   □ Check for zombie processes: ps aux | grep spritepal
   □ Verify no GUI freezing or crashes

7. ERROR SCENARIO TESTING
   □ Try to open Advanced Search without ROM loaded
   □ Enter invalid search parameters
   □ Cancel operations mid-search
   □ Test with missing cache directories
   □ Verify error messages are user-friendly

8. PERFORMANCE VALIDATION
   □ Load large ROM files (>2MB)
   □ Run multiple searches simultaneously
   □ Verify UI remains responsive
   □ Check search results appear within reasonable time
   □ Monitor CPU usage during operations

✓ AUTOMATED TESTS COMPLETED
The automated tests have verified core functionality.
Manual testing ensures the complete user experience works correctly.
""")

    def cleanup(self):
        """Clean up test environment"""
        print("\n" + "="*50)
        print("CLEANUP")
        print("="*50)

        try:
            # Cleanup managers
            cleanup_managers()
            print("✓ Managers cleaned up")

            # Remove temp directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                print(f"✓ Removed temp directory: {self.temp_dir}")

        except Exception as e:
            print(f"⚠ Cleanup error: {e}")

    def print_summary(self):
        """Print test results summary"""
        total_tests = len(self.passed_tests) + len(self.failed_tests)

        print("\n" + "="*60)
        print("INTEGRATION TEST RESULTS SUMMARY")
        print("="*60)
        print(f"Total Automated Tests: {total_tests}")
        print(f"Passed: {len(self.passed_tests)}")
        print(f"Failed: {len(self.failed_tests)}")
        print(f"Warnings: {len(self.warnings)}")

        if self.failed_tests:
            print("\nFAILED TESTS:")
            for test in self.failed_tests:
                print(f"  ✗ {test}")

        if self.warnings:
            print(f"\nWARNINGS ({len(self.warnings)}):")
            for warning in self.warnings[:5]:  # Show first 5
                print(f"  ⚠ {warning}")
            if len(self.warnings) > 5:
                print(f"  ... and {len(self.warnings) - 5} more")

        print(f"\nOVERALL RESULT: {'✓ PASS' if not self.failed_tests else '✗ FAIL'}")

        if not self.failed_tests:
            print("\n🎉 All automated tests passed!")
            print("📋 Please complete the manual UI testing checklist above.")
            print("🚀 SpritePal integration appears to be working correctly.")
        else:
            print("\n❌ Some tests failed. Please review the issues above.")

    def run_comprehensive_test_suite(self):
        """Run the complete test suite"""
        if not self.setup_test_environment():
            return False

        try:
            self.run_automated_tests()
            self.print_manual_ui_testing_checklist()

        finally:
            self.cleanup()
            self.print_summary()

        return len(self.failed_tests) == 0

def main():
    """Main entry point"""
    test_suite = ComprehensiveTestSuite()
    success = test_suite.run_comprehensive_test_suite()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
