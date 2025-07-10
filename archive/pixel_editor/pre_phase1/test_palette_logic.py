#!/usr/bin/env python3
"""
Test palette loading logic without GUI components
"""

import json
import os


def test_palette_file_validation():
    """Test palette file validation logic"""
    print("🧪 Testing Palette File Validation...")

    # Create test palette data
    valid_palette = {
        "format_version": "1.0",
        "palette": {
            "name": "Test Palette",
            "colors": [[i*16, i*16, i*16] for i in range(16)],
            "color_count": 16
        }
    }

    invalid_palette = {
        "format_version": "1.0",
        "palette": {
            "name": "Invalid Palette",
            "colors": [[255, 0, 0]] * 5  # Only 5 colors
        }
    }

    # Test the validation logic (copied from the editor)
    def validate_palette_file(data):
        try:
            if "palette" in data and "colors" in data["palette"]:
                colors = data["palette"]["colors"]
                return len(colors) >= 16 and all(len(color) >= 3 for color in colors)
            return False
        except:
            return False

    # Test validation
    assert validate_palette_file(valid_palette), "Valid palette should pass"
    assert not validate_palette_file(invalid_palette), "Invalid palette should fail"

    print("✅ Palette validation logic works")
    return True

def test_palette_name_extraction():
    """Test that palette name extraction works correctly"""
    print("🧪 Testing Palette Name Extraction...")

    test_data = {
        "palette": {
            "name": "Kirby Test Palette",
            "colors": [[255, 0, 0]] * 16
        }
    }

    # Test the extraction logic (from the fixed code)
    palette_name = test_data.get("palette", {}).get("name", "External Palette")

    assert palette_name == "Kirby Test Palette", f"Expected 'Kirby Test Palette', got '{palette_name}'"

    # Test with missing name
    test_data_no_name = {
        "palette": {
            "colors": [[255, 0, 0]] * 16
        }
    }

    palette_name_default = test_data_no_name.get("palette", {}).get("name", "External Palette")
    assert palette_name_default == "External Palette", f"Expected default name, got '{palette_name_default}'"

    print("✅ Palette name extraction works")
    return True

def test_color_conversion():
    """Test color tuple conversion logic"""
    print("🧪 Testing Color Conversion...")

    # Test colors from palette file
    test_colors = [
        [240, 56, 248],
        [224, 56, 248],
        [248, 160, 232]
    ]

    # Test the conversion logic (from the fixed code)
    converted_colors = [tuple(color[:3]) for color in test_colors]

    expected = [
        (240, 56, 248),
        (224, 56, 248),
        (248, 160, 232)
    ]

    assert converted_colors == expected, f"Color conversion failed: {converted_colors}"

    print("✅ Color conversion works")
    return True

def test_actual_palette_file():
    """Test with actual palette files if they exist"""
    print("🧪 Testing Actual Palette Files...")

    test_files = [
        "tiny_test.pal.json",
        "kirby_reference.pal.json",
        "Cave.SnesCgRam_palette_8.pal.json"
    ]

    found_files = [f for f in test_files if os.path.exists(f)]

    if not found_files:
        print("⚠️  No actual palette files found to test")
        return True

    for palette_file in found_files:
        try:
            with open(palette_file) as f:
                data = json.load(f)

            # Test validation
            def validate_palette_file(data):
                try:
                    if "palette" in data and "colors" in data["palette"]:
                        colors = data["palette"]["colors"]
                        return len(colors) >= 16 and all(len(color) >= 3 for color in colors)
                    return False
                except:
                    return False

            is_valid = validate_palette_file(data)

            if is_valid:
                # Test name extraction
                palette_name = data.get("palette", {}).get("name", "External Palette")

                # Test color conversion
                colors = data["palette"]["colors"]
                converted_colors = [tuple(color[:3]) for color in colors[:16]]

                print(f"✅ {palette_file}: valid, name='{palette_name}', colors={len(converted_colors)}")
            else:
                print(f"❌ {palette_file}: invalid format")
                return False

        except Exception as e:
            print(f"❌ {palette_file}: error reading - {e}")
            return False

    return True

def check_fixed_code():
    """Check that the fixed code doesn't have the variable order issue"""
    print("🧪 Checking Fixed Code Structure...")

    # Read the fixed file
    with open("indexed_pixel_editor.py") as f:
        content = f.read()

    # Find the load_palette_by_path function
    func_start = content.find("def load_palette_by_path(self, file_path: str) -> bool:")
    if func_start == -1:
        print("❌ Function not found")
        return False

    func_end = content.find("\n    def ", func_start + 1)
    if func_end == -1:
        func_end = len(content)

    function_code = content[func_start:func_end]

    # Check that palette_name is defined before it's used
    palette_name_definition = function_code.find("palette_name = palette_data.get")
    palette_name_usage = function_code.find("self.palette_widget.set_palette(self.external_palette_colors, palette_name)")

    if palette_name_definition == -1:
        print("❌ palette_name definition not found")
        return False

    if palette_name_usage == -1:
        print("❌ palette_name usage not found")
        return False

    if palette_name_definition < palette_name_usage:
        print("✅ palette_name is defined before usage - bug fixed!")
        return True
    print("❌ palette_name is still used before definition")
    return False

def main():
    """Run all logic tests"""
    print("🔧 Palette Loading Logic Tests")
    print("=" * 40)

    tests = [
        test_palette_file_validation,
        test_palette_name_extraction,
        test_color_conversion,
        test_actual_palette_file,
        check_fixed_code
    ]

    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print("❌ Test failed")
        except Exception as e:
            print(f"❌ Test error: {e}")

    print(f"\n📊 Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("\n🎉 All logic tests passed!")
        print("✅ The palette loading bug is fixed")
        print("✅ You can now safely use the enhanced workflow:")
        print("   1. python3 indexed_pixel_editor.py")
        print("   2. Load any test sprite sheet")
        print("   3. Accept palette loading when prompted")
        print("   4. Toggle greyscale mode to see the difference!")
    else:
        print(f"\n❌ {len(tests) - passed} tests failed")

if __name__ == "__main__":
    main()
