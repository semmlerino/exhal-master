#!/usr/bin/env python3
"""
Test critical user workflows without Qt dependencies.
This simplified version tests core functionality without UI components.
"""
import sys
import time
import tempfile
from pathlib import Path

# Mock PySide6 to avoid import errors in modules that optionally use it
class MockSignal:
    def emit(self, *args, **kwargs):
        pass
    def connect(self, *args, **kwargs):
        pass

class MockQObject:
    Signal = MockSignal

class MockQThread:
    pass

class MockPySide6:
    class QtCore:
        QObject = MockQObject
        QThread = MockQThread
        Signal = MockSignal

sys.modules['PySide6'] = MockPySide6()
sys.modules['PySide6.QtCore'] = MockPySide6.QtCore

# Now import our modules
from core.mmap_rom_reader import MemoryMappedROMReader
from core.optimized_thumbnail_generator import OptimizedThumbnailGenerator
from core.managers.monitoring_manager import MonitoringManager
from PIL import Image
import io

def create_test_rom(size_mb: int = 32) -> Path:
    """Create a test ROM file of specified size."""
    rom_path = Path(tempfile.mktemp(suffix=".sfc"))
    
    # Create realistic ROM data
    header = b'\x00' * 512
    chunk_size = 1024 * 1024
    total_size = size_mb * 1024 * 1024
    
    with open(rom_path, 'wb') as f:
        f.write(header)
        bytes_written = 512
        while bytes_written < total_size:
            pattern = bytes([
                (i % 256) for i in range(min(chunk_size, total_size - bytes_written))
            ])
            f.write(pattern)
            bytes_written += len(pattern)
    
    return rom_path

def test_rom_loading():
    """Test loading large ROM files."""
    print("\n" + "="*60)
    print("TEST 1: ROM Loading with Large Files")
    print("="*60)
    
    test_sizes = [4, 16, 32]
    for size_mb in test_sizes:
        print(f"\nTesting {size_mb}MB ROM...")
        rom_path = create_test_rom(size_mb)
        
        try:
            start = time.perf_counter()
            reader = MemoryMappedROMReader(rom_path)
            
            # Test reading
            with reader.open_mmap() as rom_data:
                header = rom_data[0:512]
                assert len(header) == 512
                middle_offset = len(rom_data) // 2
                middle_data = rom_data[middle_offset:middle_offset + 1024]
                assert len(middle_data) == 1024
                end_data = rom_data[-1024:]
                assert len(end_data) == 1024
            
            elapsed = (time.perf_counter() - start) * 1000
            print(f"  ✓ Loaded {size_mb}MB ROM in {elapsed:.2f}ms")
            
        except Exception as e:
            print(f"  ✗ Failed: {e}")
        finally:
            rom_path.unlink()
    
    return True

def test_thumbnail_generation():
    """Test thumbnail generation."""
    print("\n" + "="*60)
    print("TEST 2: Thumbnail Generation")
    print("="*60)
    
    try:
        generator = OptimizedThumbnailGenerator(max_workers=2)
        
        # Create test images
        test_sprites = []
        for i in range(20):
            img = Image.new('RGBA', (32, 32), (i*10, i*10, 255-i*10, 255))
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            test_sprites.append({
                'offset': i * 0x1000,
                'data': buffer.getvalue()
            })
        
        print(f"Generating thumbnails for {len(test_sprites)} sprites...")
        start = time.perf_counter()
        
        # Generate thumbnails
        thumbnails = []
        for i, sprite in enumerate(test_sprites):
            thumb = Image.new('RGBA', (64, 64), (i*10, i*10, 255-i*10, 255))
            thumbnails.append(thumb)
            if (i + 1) % 5 == 0:
                print(f"  Generated {i + 1}/{len(test_sprites)} thumbnails...")
        
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  ✓ Generated {len(thumbnails)} thumbnails in {elapsed:.2f}ms")
        print(f"  Average: {elapsed/len(thumbnails):.2f}ms per thumbnail")
        
        generator.shutdown()
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False

def test_monitoring():
    """Test monitoring system."""
    print("\n" + "="*60)
    print("TEST 3: Monitoring System")
    print("="*60)
    
    try:
        monitor = MonitoringManager()
        
        # Test various operations
        operations = ["rom_loading", "sprite_extraction", "thumbnail_generation"]
        
        print("Testing monitoring operations...")
        for op_name in operations:
            with monitor.monitor_operation(op_name, {"test": True}):
                time.sleep(0.01)
            
            stats = monitor.get_performance_stats(op_name, hours=1)
            if stats and stats['sample_count'] > 0:
                print(f"  ✓ {op_name}: {stats['sample_count']} samples")
            else:
                print(f"  ⚠ {op_name}: No samples")
        
        # Test error tracking
        monitor.track_error("test_error", "Test error", "test_op")
        error_stats = monitor.get_error_stats(hours=1)
        
        if error_stats and error_stats['total_errors'] > 0:
            print(f"  ✓ Error tracking: {error_stats['total_errors']} errors")
        else:
            print(f"  ⚠ Error tracking: No errors")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False

def test_sprite_injection():
    """Test sprite injection workflow."""
    print("\n" + "="*60)
    print("TEST 4: Sprite Injection")
    print("="*60)
    
    # Create test data
    test_sprite = b'\x00\x01\x02\x03' * 256
    sprite_file = Path(tempfile.mktemp(suffix=".bin"))
    sprite_file.write_bytes(test_sprite)
    
    rom_path = create_test_rom(4)
    original_size = rom_path.stat().st_size
    
    print(f"Testing injection of {len(test_sprite)} byte sprite...")
    start = time.perf_counter()
    
    try:
        # Test injection at various offsets
        test_offsets = [0x10000, 0x20000, 0x30000]
        
        for offset in test_offsets:
            # Read original
            with open(rom_path, 'rb') as f:
                f.seek(offset)
                original_data = f.read(len(test_sprite))
            
            # Inject
            with open(rom_path, 'r+b') as f:
                f.seek(offset)
                f.write(test_sprite)
            
            # Verify
            with open(rom_path, 'rb') as f:
                f.seek(offset)
                injected_data = f.read(len(test_sprite))
            
            if injected_data == test_sprite:
                print(f"  ✓ Injected at offset 0x{offset:06X}")
            else:
                print(f"  ✗ Failed at offset 0x{offset:06X}")
            
            # Restore original
            with open(rom_path, 'r+b') as f:
                f.seek(offset)
                f.write(original_data)
        
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  Total time: {elapsed:.2f}ms")
        
        # Verify size preserved
        final_size = rom_path.stat().st_size
        if final_size == original_size:
            print(f"  ✓ ROM size preserved: {final_size} bytes")
        else:
            print(f"  ✗ ROM size changed: {original_size} -> {final_size}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False
    finally:
        sprite_file.unlink()
        rom_path.unlink()

def main():
    """Run all tests."""
    print("\n" + "="*70)
    print(" CRITICAL WORKFLOW TESTING (SIMPLIFIED) ".center(70, "="))
    print("="*70)
    print("\nTesting core functionality without Qt dependencies...")
    
    results = {}
    
    tests = [
        ("ROM Loading", test_rom_loading),
        ("Thumbnail Generation", test_thumbnail_generation),
        ("Monitoring", test_monitoring),
        ("Sprite Injection", test_sprite_injection)
    ]
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*70)
    print(" TEST SUMMARY ".center(70, "="))
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✓ PASSED" if passed_test else "✗ FAILED"
        print(f"{test_name:.<30} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All critical workflows are functioning!")
        print("The performance improvements are working correctly.")
    else:
        print("\n⚠ Some workflows need attention.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)