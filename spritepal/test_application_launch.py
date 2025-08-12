#!/usr/bin/env python3
"""
Test that simulates application launch from different working directories
to verify the HAL compression fix works in realistic scenarios.
"""

import os
import sys
from pathlib import Path

# Add spritepal to Python path for imports
spritepal_dir = Path(__file__).parent
sys.path.insert(0, str(spritepal_dir))

def test_manager_initialization_from_different_dirs():
    """Test that manager initialization works from different directories"""
    
    print("TESTING MANAGER INITIALIZATION WITH FIXED HAL DETECTION")
    print("="*60)
    
    original_cwd = os.getcwd()
    test_dirs = [
        (spritepal_dir, "spritepal directory"),
        (spritepal_dir.parent, "exhal-master directory"),  
        (Path("/tmp"), "temp directory"),
    ]
    
    results = []
    
    for test_dir, name in test_dirs:
        try:
            print(f"\n=== Testing from {name} ===")
            print(f"Changing working directory to: {test_dir}")
            os.chdir(test_dir)
            print(f"Current working directory: {os.getcwd()}")
            
            # Import and test managers that use HALCompressor
            try:
                # Test HALCompressor directly
                from core.hal_compression import HALCompressor
                compressor = HALCompressor()
                print(f"✅ HALCompressor: Found tools at {compressor.exhal_path}")
                
                # Test managers that depend on HAL compression
                from core.managers import get_injection_manager
                injection_manager = get_injection_manager()
                print(f"✅ InjectionManager: Initialized successfully")
                
                # Test managers initialization (similar to application startup)
                from core.managers import get_extraction_manager, get_session_manager
                extraction_manager = get_extraction_manager()
                session_manager = get_session_manager()
                print(f"✅ All managers: Initialized successfully")
                
                results.append((name, True, "All managers initialized successfully"))
                
            except Exception as e:
                print(f"❌ Manager initialization failed: {e}")
                results.append((name, False, str(e)))
                
        except Exception as e:
            print(f"❌ Test setup failed: {e}")
            results.append((name, False, f"Test setup failed: {e}"))
        finally:
            # Restore original directory
            os.chdir(original_cwd)
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST RESULTS SUMMARY")
    print(f"{'='*60}")
    
    passed = 0
    for test_name, success, details in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:20} : {status}")
        if not success:
            print(f"                       Details: {details}")
        if success:
            passed += 1
    
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 SUCCESS: The intermittent exhal detection issue has been fixed!")
        print("   The application will now work regardless of working directory.")
    else:
        print("⚠️  Some tests failed. Additional investigation may be needed.")
    
    return passed == total

if __name__ == "__main__":
    test_manager_initialization_from_different_dirs()