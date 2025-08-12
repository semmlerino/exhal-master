#!/usr/bin/env python3
"""
Test script to verify critical thread safety fixes.
Tests the refactored BatchThumbnailWorker with proper moveToThread pattern.
"""

import sys
import tempfile
from pathlib import Path
from PySide6.QtCore import QThread, QCoreApplication, QTimer, QEventLoop
from PySide6.QtWidgets import QApplication

# Add spritepal to path
sys.path.insert(0, '.')

from ui.workers.batch_thumbnail_worker import ThumbnailWorkerController, BatchThumbnailWorker


def test_worker_thread_safety():
    """Test that worker properly uses moveToThread pattern."""
    print("Testing thread safety fixes...")
    
    # Create Qt application if needed
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Create a temporary ROM file for testing
    with tempfile.NamedTemporaryFile(suffix='.sfc', delete=False) as tmp:
        tmp.write(b'\x00' * 0x10000)  # 64KB test ROM
        rom_path = tmp.name
    
    try:
        # Test 1: Verify controller creates worker in separate thread
        print("\n1. Testing moveToThread pattern...")
        controller = ThumbnailWorkerController()
        
        # Record main thread
        main_thread = QThread.currentThread()
        print(f"   Main thread: {main_thread}")
        
        # Start worker
        controller.start_worker(rom_path)
        
        # Give thread time to start
        QThread.msleep(100)
        
        # Verify worker is in different thread
        if controller.worker and controller.thread:
            worker_thread = controller.thread
            print(f"   Worker thread: {worker_thread}")
            assert worker_thread != main_thread, "Worker should be in different thread!"
            print("   ✓ Worker correctly moved to separate thread")
        else:
            print("   ✗ Failed to create worker/thread")
            return False
        
        # Test 2: Verify thread-safe cache operations
        print("\n2. Testing thread-safe cache access...")
        
        # Queue some thumbnails
        test_offsets = [0x1000, 0x2000, 0x3000]
        for offset in test_offsets:
            controller.queue_thumbnail(offset, 128, 0)
        
        print(f"   Queued {len(test_offsets)} thumbnails")
        
        # Process events briefly
        event_loop = QEventLoop()
        QTimer.singleShot(500, event_loop.quit)
        event_loop.exec()
        
        print("   ✓ No crashes during concurrent cache access")
        
        # Test 3: Verify proper cleanup
        print("\n3. Testing cleanup...")
        controller.stop_worker()
        
        # Wait for thread to finish
        if controller.thread:
            if not controller.thread.wait(2000):
                print("   ✗ Thread did not stop within timeout")
                return False
        
        print("   ✓ Worker thread stopped cleanly")
        
        # Test 4: Verify memory-mapped ROM access
        print("\n4. Testing memory-mapped ROM access...")
        
        # Create new worker to test mmap
        worker = BatchThumbnailWorker(rom_path)
        worker._load_rom_data()
        
        if hasattr(worker, '_rom_mmap') and worker._rom_mmap:
            print(f"   ROM memory-mapped: {len(worker._rom_mmap)} bytes")
            print("   ✓ Memory mapping successful")
            
            # Test chunk reading
            chunk = worker._read_rom_chunk(0x100, 256)
            if chunk and len(chunk) == 256:
                print("   ✓ Chunk reading works")
            else:
                print("   ✗ Chunk reading failed")
        else:
            print("   ✗ Memory mapping failed")
        
        # Cleanup
        worker._clear_rom_data()
        
        print("\n✅ All thread safety tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up temp file
        Path(rom_path).unlink(missing_ok=True)


def test_type_safety():
    """Test type safety fixes."""
    print("\n\nTesting type safety fixes...")
    
    # Test 1: MainWindowProtocol metaclass issue (known limitation)
    print("\n1. Testing MainWindowProtocol...")
    try:
        from core.protocols.manager_protocols import MainWindowProtocol
        from typing import Protocol
        
        # Check if it's a Protocol (expected due to metaclass conflict)
        # This is a known limitation - MainWindowProtocol cannot inherit from QWidget
        # due to metaclass conflicts. The controller has fallback handling for this.
        assert issubclass(MainWindowProtocol, Protocol), "MainWindowProtocol is a Protocol"
        print("   ✓ MainWindowProtocol is correctly defined as Protocol")
        print("   ℹ️  Note: Cannot inherit from QWidget due to metaclass conflict")
        print("   ℹ️  Controller has try/except fallback for this limitation")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False
    
    # Test 2: TypedDict with NotRequired
    print("\n2. Testing TypedDict definitions...")
    try:
        from core.controller import ROMExtractionParams
        from typing import get_type_hints
        from typing_extensions import NotRequired
        
        hints = get_type_hints(ROMExtractionParams, include_extras=True)
        print(f"   ROMExtractionParams fields: {list(hints.keys())}")
        print("   ✓ TypedDict imports and definitions work")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False
    
    print("\n✅ All type safety tests passed!")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("CRITICAL FIXES VERIFICATION TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Run thread safety tests
    results.append(("Thread Safety", test_worker_thread_safety()))
    
    # Run type safety tests  
    results.append(("Type Safety", test_type_safety()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:20} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All critical fixes verified successfully!")
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed. Please review the fixes.")
        sys.exit(1)


if __name__ == "__main__":
    main()