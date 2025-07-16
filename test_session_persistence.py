#!/usr/bin/env python3
"""
Test session persistence functionality in SpritePal
"""

import os
import sys
import json
from pathlib import Path

# Add SpritePal to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spritepal.utils.settings_manager import SettingsManager


def test_settings_manager():
    """Test the settings manager functionality"""
    print("Testing SpritePal Session Persistence")
    print("=" * 40)
    
    # Create a test settings manager
    settings = SettingsManager("SpritePalTest")
    
    # Test 1: Save session data
    print("\n1. Testing session data save/load")
    test_session = {
        "vram_path": "test_vram.dmp",
        "cgram_path": "test_cgram.dmp", 
        "oam_path": "test_oam.dmp",
        "output_name": "test_sprites_editor",
        "create_grayscale": True,
        "create_metadata": True
    }
    
    settings.save_session_data(test_session)
    loaded_session = settings.get_session_data()
    
    if loaded_session == test_session:
        print("✓ Session data saved and loaded correctly")
    else:
        print("✗ Session data mismatch")
        print(f"  Expected: {test_session}")
        print(f"  Got: {loaded_session}")
    
    # Test 2: UI settings
    print("\n2. Testing UI settings save/load")
    test_ui = {
        "window_width": 1024,
        "window_height": 768,
        "window_x": 100,
        "window_y": 50
    }
    
    settings.save_ui_data(test_ui)
    loaded_ui = settings.get_ui_data()
    
    if loaded_ui == test_ui:
        print("✓ UI settings saved and loaded correctly")
    else:
        print("✗ UI settings mismatch")
        print(f"  Expected: {test_ui}")
        print(f"  Got: {loaded_ui}")
    
    # Test 3: File path validation
    print("\n3. Testing file path validation")
    
    # Create test files
    test_files = ["test_vram.dmp", "test_cgram.dmp"]
    for f in test_files:
        Path(f).touch()
    
    validated_paths = settings.validate_file_paths()
    
    if validated_paths["vram_path"] == "test_vram.dmp" and validated_paths["cgram_path"] == "test_cgram.dmp":
        print("✓ File path validation working correctly")
    else:
        print("✗ File path validation failed")
        print(f"  Got: {validated_paths}")
    
    # Test 4: Has valid session
    print("\n4. Testing valid session detection")
    has_valid = settings.has_valid_session()
    
    if has_valid:
        print("✓ Valid session detected correctly")
    else:
        print("✗ Valid session not detected")
    
    # Test 5: Settings file creation
    print("\n5. Testing settings file")
    settings_file = Path(".spritepaltest_settings.json")
    
    if settings_file.exists():
        print("✓ Settings file created successfully")
        
        # Check file content
        with open(settings_file, 'r') as f:
            data = json.load(f)
        
        if "session" in data and "ui" in data:
            print("✓ Settings file has correct structure")
        else:
            print("✗ Settings file structure incorrect")
    else:
        print("✗ Settings file not created")
    
    # Cleanup
    print("\n6. Cleaning up test files")
    for f in test_files + [".spritepaltest_settings.json"]:
        if os.path.exists(f):
            os.remove(f)
    print("✓ Test files cleaned up")
    
    print("\n✓ Session persistence test complete!")


def test_with_real_files():
    """Test with actual dump files if available"""
    print("\n" + "=" * 40)
    print("Testing with actual dump files")
    print("=" * 40)
    
    # Look for real dump files
    dump_patterns = [
        "*VRAM*.dmp",
        "*VideoRam*.dmp",
        "*CGRAM*.dmp",
        "*CgRam*.dmp"
    ]
    
    found_files = []
    for pattern in dump_patterns:
        files = list(Path.cwd().glob(pattern))
        found_files.extend(files)
    
    if found_files:
        print(f"Found {len(found_files)} dump files:")
        for f in found_files:
            print(f"  - {f.name}")
            
        # Test settings manager with real files
        settings = SettingsManager("SpritePalRealTest")
        
        # Create session with real files
        real_session = {
            "vram_path": str(found_files[0]) if found_files else "",
            "cgram_path": str(found_files[1]) if len(found_files) > 1 else "",
            "oam_path": "",
            "output_name": "cave_sprites_editor",
            "create_grayscale": True,
            "create_metadata": True
        }
        
        settings.save_session_data(real_session)
        
        # Test validation
        validated = settings.validate_file_paths()
        print(f"\nValidated paths: {validated}")
        
        has_valid = settings.has_valid_session()
        print(f"Has valid session: {has_valid}")
        
        # Cleanup
        settings_file = Path(".spritepalrealtest_settings.json")
        if settings_file.exists():
            os.remove(settings_file)
        
        print("✓ Real file test complete!")
    else:
        print("No dump files found for testing")


if __name__ == "__main__":
    test_settings_manager()
    test_with_real_files()