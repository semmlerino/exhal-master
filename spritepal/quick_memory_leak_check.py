#!/usr/bin/env python3
"""
Quick Memory Leak Check for SpritePal

This script performs a focused test on the specific memory leak pattern that was
causing 100MB/sec growth: rapid manager initialization cycles.

It can be run quickly to verify the core fix is working.
"""

import gc
import sys
import time
from pathlib import Path

import psutil
from PyQt6.QtWidgets import QApplication

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

def measure_manager_leak():
    """Measure memory leak from rapid manager initialization"""
    process = psutil.Process(os.getpid())
    
    def get_memory_mb():
        gc.collect()
        return process.memory_info().rss / 1024 / 1024
    
    print("Quick memory leak check: Manager initialization cycles")
    print("=" * 60)
    
    # Baseline
    baseline = get_memory_mb()
    print(f"Baseline memory: {baseline:.2f} MB")
    
    # Import after baseline to isolate the test
    from core.managers.registry import ManagerRegistry
    
    # Rapid manager cycles (this was causing 100MB/sec growth)
    start_time = time.time()
    start_memory = get_memory_mb()
    
    cycles = 20  # Reduced for quick test
    print(f"Running {cycles} rapid manager initialization cycles...")
    
    for i in range(cycles):
        try:
            # This pattern was causing the major leak
            registry = ManagerRegistry()
            registry.initialize_managers("QuickTest")
            
            # Brief usage
            session_mgr = registry.get_session_manager()
            extraction_mgr = registry.get_extraction_manager()
            injection_mgr = registry.get_injection_manager()
            
            # Cleanup (this is where the fix should take effect)
            registry.cleanup_managers()
            
            if (i + 1) % 5 == 0:
                current_memory = get_memory_mb()
                print(f"  Cycle {i+1}/{cycles}: {current_memory:.2f} MB")
        
        except Exception as e:
            print(f"Error in cycle {i+1}: {e}")
            return False
    
    end_time = time.time()
    end_memory = get_memory_mb()
    
    # Calculate metrics
    memory_growth = end_memory - start_memory
    time_elapsed = end_time - start_time
    growth_rate_mb_per_sec = memory_growth / time_elapsed if time_elapsed > 0 else 0
    memory_per_cycle_kb = (memory_growth * 1024) / cycles if cycles > 0 else 0
    
    print(f"\nResults:")
    print(f"  Start memory: {start_memory:.2f} MB")
    print(f"  End memory: {end_memory:.2f} MB")
    print(f"  Memory growth: {memory_growth:.2f} MB")
    print(f"  Time elapsed: {time_elapsed:.2f} seconds")
    print(f"  Growth rate: {growth_rate_mb_per_sec:.3f} MB/sec")
    print(f"  Memory per cycle: {memory_per_cycle_kb:.1f} KB")
    
    # Success criteria (much stricter than the full test)
    if growth_rate_mb_per_sec < 0.5:  # Very strict: < 0.5 MB/sec
        print(f"\n✅ SUCCESS: Memory leak fix is working!")
        print(f"   Growth rate {growth_rate_mb_per_sec:.3f} MB/sec is well below 100 MB/sec")
        return True
    else:
        print(f"\n❌ FAILURE: Memory leak still present!")
        print(f"   Growth rate {growth_rate_mb_per_sec:.3f} MB/sec is too high")
        print(f"   (Previous leak was ~100 MB/sec)")
        return False

def main():
    """Main function"""
    # Create minimal Qt application
    app = QApplication(sys.argv)
    
    try:
        success = measure_manager_leak()
        
        if success:
            print("\n🎉 Memory leak fixes are working correctly!")
            sys.exit(0)
        else:
            print("\n⚠️  Memory leak fixes need more work!")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        try:
            app.quit()
        except:
            pass

if __name__ == "__main__":
    main()