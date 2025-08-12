#!/usr/bin/env python3
"""
Test script to verify the fixed exhal detection works from any working directory.
"""

import os
import tempfile
from pathlib import Path
from core.hal_compression import HALCompressor

def test_detection_from_directory(test_dir, test_name):
    """Test HAL tool detection from a specific directory"""
    original_cwd = os.getcwd()
    
    try:
        print(f"\n=== {test_name} ===")
        print(f"Changing to directory: {test_dir}")
        os.chdir(test_dir)
        print(f"Current working directory: {os.getcwd()}")
        
        # Test HALCompressor initialization
        compressor = HALCompressor()
        print(f"✅ SUCCESS: Found exhal at {compressor.exhal_path}")
        print(f"✅ SUCCESS: Found inhal at {compressor.inhal_path}")
        
        # Test the tools work
        success, message = compressor.test_tools()
        if success:
            print(f"✅ SUCCESS: Tools are working - {message}")
        else:
            print(f"❌ FAIL: Tools test failed - {message}")
            
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False
    finally:
        os.chdir(original_cwd)

def main():
    """Test the fixed detection from various working directories"""
    
    print("TESTING FIXED EXHAL DETECTION")
    print("="*50)
    
    original_cwd = os.getcwd()
    results = []
    
    # Test 1: From spritepal directory (should still work)
    success = test_detection_from_directory(
        Path(__file__).parent,
        "Test from spritepal directory"
    )
    results.append(("spritepal directory", success))
    
    # Test 2: From parent (exhal-master) directory (should now work)
    success = test_detection_from_directory(
        Path(__file__).parent.parent,
        "Test from exhal-master directory"
    )
    results.append(("exhal-master directory", success))
    
    # Test 3: From temp directory (should now work)
    with tempfile.TemporaryDirectory() as temp_dir:
        success = test_detection_from_directory(
            temp_dir,
            "Test from temp directory"
        )
        results.append(("temp directory", success))
    
    # Test 4: From user home directory (should now work)
    try:
        home_dir = Path.home()
        success = test_detection_from_directory(
            home_dir,
            "Test from home directory"
        )
        results.append(("home directory", success))
    except Exception as e:
        print(f"Skipping home directory test: {e}")
        results.append(("home directory", False))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST RESULTS SUMMARY")
    print(f"{'='*50}")
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:20} : {status}")
        if success:
            passed += 1
    
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! The working directory dependency has been fixed.")
    else:
        print("⚠️  Some tests failed. The fix may need additional work.")
    
    return passed == total

if __name__ == "__main__":
    main()