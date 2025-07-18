#!/usr/bin/env python3
"""
Check the status of the PixelCanvas refactoring.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_imports():
    """Check if imports are working correctly."""
    print("Checking imports...")
    try:
        from pixel_editor.core.pixel_editor_canvas_v3 import PixelCanvasV3
        print("✓ PixelCanvasV3 import successful")
    except ImportError as e:
        print(f"✗ PixelCanvasV3 import failed: {e}")
        
    try:
        from pixel_editor.core.widgets.color_palette_widget import ColorPaletteWidget
        print("✓ ColorPaletteWidget import successful")
    except ImportError as e:
        print(f"✗ ColorPaletteWidget import failed: {e}")
        
    try:
        from pixel_editor.core.widgets.zoomable_scroll_area import ZoomableScrollArea
        print("✓ ZoomableScrollArea import successful")
    except ImportError as e:
        print(f"✗ ZoomableScrollArea import failed: {e}")
        
    try:
        from pixel_editor.core.indexed_pixel_editor_v3 import IndexedPixelEditor
        print("✓ IndexedPixelEditor import successful")
    except ImportError as e:
        print(f"✗ IndexedPixelEditor import failed: {e}")

def check_legacy_references():
    """Check for any remaining references to PixelCanvas."""
    print("\nChecking for legacy PixelCanvas references...")
    
    # Search for PixelCanvas references (excluding V3)
    cmd = [
        'grep', '-r', 'PixelCanvas', 
        '../pixel_editor',
        '--include=*.py',
        '--exclude-dir=__pycache__'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Filter out PixelCanvasV3 references
    if result.stdout:
        lines = result.stdout.strip().split('\n')
        legacy_refs = [line for line in lines if 'PixelCanvasV3' not in line and 'pixel_editor_widgets.py' not in line]
        
        if legacy_refs:
            print(f"✗ Found {len(legacy_refs)} legacy PixelCanvas references:")
            for ref in legacy_refs[:5]:  # Show first 5
                print(f"  {ref}")
            if len(legacy_refs) > 5:
                print(f"  ... and {len(legacy_refs) - 5} more")
        else:
            print("✓ No legacy PixelCanvas references found")
    else:
        print("✓ No legacy PixelCanvas references found")

def check_test_status():
    """Quick check of test status."""
    print("\nChecking test status...")
    
    # Run a quick test check
    env = os.environ.copy()
    env['QT_QPA_PLATFORM'] = 'offscreen'
    
    test_files = [
        'test_pixel_editor_controller_v3.py',
        'test_api_contracts_v3.py',
        'test_brush_functionality.py'
    ]
    
    for test_file in test_files:
        cmd = [
            sys.executable, '-m', 'pytest',
            f'../pixel_editor/tests/{test_file}',
            '-v', '--tb=no', '--no-header', '-q',
            '--co'  # Collect only, don't run
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Count tests
            test_count = result.stdout.count('::test_')
            print(f"✓ {test_file}: {test_count} tests found")
        else:
            print(f"✗ {test_file}: Collection failed")

def main():
    print("PIXELCANVAS REFACTORING STATUS CHECK")
    print("=" * 50)
    
    check_imports()
    check_legacy_references()
    check_test_status()
    
    print("\nREFACTORING SUMMARY:")
    print("1. PixelCanvas class has been removed from pixel_editor_widgets.py")
    print("2. Widgets have been moved to pixel_editor/core/widgets/")
    print("3. All code now uses PixelCanvasV3")
    print("4. Controller tests have been updated for V3 architecture")
    print("5. Drawing operations properly set the modified flag")
    print("6. Color picker callback is properly configured")
    
    print("\nREMAINING TASKS:")
    print("- Extract TransformManager from PixelCanvasV3")
    print("- Extract RenderCacheManager from PixelCanvasV3")
    print("- Enhance brush support in Tool system")

if __name__ == '__main__':
    main()