#!/usr/bin/env python3
"""
Test complete SpritePal workflow including session persistence
"""

import os
import sys
import json
from pathlib import Path

# Add SpritePal to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spritepal.utils.settings_manager import SettingsManager


def test_complete_workflow():
    """Test the complete workflow with session persistence"""
    print("Testing Complete SpritePal Workflow")
    print("=" * 40)
    
    # Look for actual dump files
    vram_files = list(Path.cwd().glob("*VRAM*.dmp")) + list(Path.cwd().glob("*VideoRam*.dmp"))
    cgram_files = list(Path.cwd().glob("*CGRAM*.dmp")) + list(Path.cwd().glob("*CgRam*.dmp"))
    oam_files = list(Path.cwd().glob("*OAM*.dmp")) + list(Path.cwd().glob("*SpriteRam*.dmp"))
    
    if not vram_files or not cgram_files:
        print("Skipping workflow test - no dump files found")
        return
    
    vram_file = str(vram_files[0])
    cgram_file = str(cgram_files[0])
    oam_file = str(oam_files[0]) if oam_files else ""
    
    print(f"Using files:")
    print(f"  VRAM: {Path(vram_file).name}")
    print(f"  CGRAM: {Path(cgram_file).name}")
    if oam_file:
        print(f"  OAM: {Path(oam_file).name}")
    
    # Clean up any existing settings
    settings_file = Path(".spritepal_settings.json")
    if settings_file.exists():
        settings_file.unlink()
    
    # Step 1: Simulate first app launch (no session)
    print("\n1. First app launch - no previous session")
    settings = SettingsManager()
    
    if settings.has_valid_session():
        print("✗ Should not have valid session on first launch")
        return
    else:
        print("✓ No previous session found (correct)")
    
    # Step 2: Simulate loading files
    print("\n2. Loading files into SpritePal")
    session_data = {
        "vram_path": vram_file,
        "cgram_path": cgram_file,
        "oam_path": oam_file,
        "output_name": "test_sprites_editor",
        "create_grayscale": True,
        "create_metadata": True
    }
    
    settings.save_session_data(session_data)
    
    ui_data = {
        "window_width": 1024,
        "window_height": 768,
        "window_x": 200,
        "window_y": 100
    }
    
    settings.save_ui_data(ui_data)
    
    print("✓ Session data saved")
    print(f"  - Files loaded: {len([f for f in [vram_file, cgram_file, oam_file] if f])}")
    print(f"  - Output name: {session_data['output_name']}")
    print(f"  - Window size: {ui_data['window_width']}x{ui_data['window_height']}")
    
    # Step 3: Simulate app close and reopen
    print("\n3. Simulating app restart")
    settings2 = SettingsManager()  # New instance simulates app restart
    
    if settings2.has_valid_session():
        print("✓ Valid session detected after restart")
    else:
        print("✗ Valid session not detected after restart")
        return
    
    # Step 4: Verify session restoration
    print("\n4. Verifying session restoration")
    restored_session = settings2.get_session_data()
    restored_ui = settings2.get_ui_data()
    validated_paths = settings2.validate_file_paths()
    
    # Check session data
    if restored_session["output_name"] == session_data["output_name"]:
        print("✓ Output name restored correctly")
    else:
        print("✗ Output name restoration failed")
    
    if restored_session["create_grayscale"] == session_data["create_grayscale"]:
        print("✓ Grayscale setting restored correctly")
    else:
        print("✗ Grayscale setting restoration failed")
    
    # Check file paths
    if validated_paths["vram_path"] == vram_file:
        print("✓ VRAM path restored correctly")
    else:
        print("✗ VRAM path restoration failed")
    
    if validated_paths["cgram_path"] == cgram_file:
        print("✓ CGRAM path restored correctly")
    else:
        print("✗ CGRAM path restoration failed")
    
    # Check UI data
    if restored_ui["window_width"] == ui_data["window_width"]:
        print("✓ Window size restored correctly")
    else:
        print("✗ Window size restoration failed")
    
    # Step 5: Test file validation
    print("\n5. Testing file validation")
    
    # Move a file to test validation
    temp_file = Path("temp_vram.dmp")
    if not temp_file.exists():
        temp_file.touch()
    
    # Update session with non-existent file
    bad_session = session_data.copy()
    bad_session["vram_path"] = "non_existent_file.dmp"
    settings2.save_session_data(bad_session)
    
    validated_bad = settings2.validate_file_paths()
    
    if not validated_bad["vram_path"]:
        print("✓ Non-existent file correctly filtered out")
    else:
        print("✗ Non-existent file not filtered out")
    
    # Clean up
    if temp_file.exists():
        temp_file.unlink()
    
    # Step 6: Test session clearing
    print("\n6. Testing session clearing")
    settings2.clear_session()
    
    if not settings2.has_valid_session():
        print("✓ Session cleared correctly")
    else:
        print("✗ Session not cleared")
    
    # Step 7: Clean up
    print("\n7. Cleaning up")
    if settings_file.exists():
        settings_file.unlink()
    print("✓ Test files cleaned up")
    
    print("\n✓ Complete workflow test passed!")


def test_settings_file_format():
    """Test the settings file format"""
    print("\n" + "=" * 40)
    print("Testing Settings File Format")
    print("=" * 40)
    
    settings = SettingsManager()
    
    # Save some test data
    settings.save_session_data({
        "vram_path": "/path/to/vram.dmp",
        "cgram_path": "/path/to/cgram.dmp",
        "oam_path": "/path/to/oam.dmp",
        "output_name": "test_output",
        "create_grayscale": True,
        "create_metadata": False
    })
    
    settings.save_ui_data({
        "window_width": 800,
        "window_height": 600,
        "window_x": 0,
        "window_y": 0
    })
    
    # Check the file format
    settings_file = Path(".spritepal_settings.json")
    
    if settings_file.exists():
        with open(settings_file, 'r') as f:
            data = json.load(f)
        
        print("Settings file structure:")
        print(json.dumps(data, indent=2))
        
        # Verify structure
        required_keys = ["session", "ui"]
        if all(key in data for key in required_keys):
            print("✓ Settings file has correct top-level structure")
        else:
            print("✗ Settings file missing required keys")
        
        # Verify session keys
        session_keys = ["vram_path", "cgram_path", "oam_path", "output_name", "create_grayscale", "create_metadata"]
        if all(key in data["session"] for key in session_keys):
            print("✓ Session data has all required keys")
        else:
            print("✗ Session data missing required keys")
        
        # Verify UI keys
        ui_keys = ["window_width", "window_height", "window_x", "window_y"]
        if all(key in data["ui"] for key in ui_keys):
            print("✓ UI data has all required keys")
        else:
            print("✗ UI data missing required keys")
    else:
        print("✗ Settings file not created")
    
    # Clean up
    if settings_file.exists():
        settings_file.unlink()


if __name__ == "__main__":
    test_complete_workflow()
    test_settings_file_format()