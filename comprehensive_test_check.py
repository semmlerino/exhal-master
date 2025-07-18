#!/usr/bin/env python3
"""
Comprehensive test check for the entire project.
Runs tests in batches to avoid timeouts and identify issues.
"""

import os
import sys
import subprocess
from pathlib import Path
import time

def run_test_batch(test_paths, description, timeout=60):
    """Run a batch of tests with timeout."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    
    env = os.environ.copy()
    env['QT_QPA_PLATFORM'] = 'offscreen'
    env['QT_LOGGING_RULES'] = '*.debug=false'
    
    cmd = [
        sys.executable, '-m', 'pytest',
        '-v', '--tb=short', '-x',  # Stop on first failure
        '-p', 'no:warnings',  # Disable warnings
        '-p', 'no:xvfb',  # Disable xvfb plugin (causes hangs in WSL2)
        '-m', 'not gui'  # Skip GUI tests
    ] + test_paths
    
    try:
        start_time = time.time()
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        elapsed = time.time() - start_time
        
        # Extract summary
        output_lines = result.stdout.strip().split('\n')
        summary_line = None
        for line in output_lines:
            if 'passed' in line or 'failed' in line or 'error' in line:
                if '==' in line:
                    summary_line = line
                    break
        
        if result.returncode == 0:
            print(f"✓ PASSED in {elapsed:.1f}s")
            if summary_line:
                print(f"  {summary_line.strip()}")
        else:
            print(f"✗ FAILED in {elapsed:.1f}s")
            if summary_line:
                print(f"  {summary_line.strip()}")
            # Show last few lines of output
            print("\nLast output:")
            for line in output_lines[-10:]:
                print(f"  {line}")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"✗ TIMEOUT after {timeout}s")
        return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False

def main():
    print("COMPREHENSIVE TEST CHECK")
    print("=" * 60)
    
    test_groups = [
        # Pixel editor unit tests
        {
            'paths': ['pixel_editor/tests/test_api_contracts*.py'],
            'description': 'API Contract Tests'
        },
        {
            'paths': ['pixel_editor/tests/test_pixel_editor_controller_v3.py'],
            'description': 'Controller Tests'
        },
        {
            'paths': ['pixel_editor/tests/test_brush_*.py'],
            'description': 'Brush Tests'
        },
        {
            'paths': ['pixel_editor/tests/test_component_boundaries.py'],
            'description': 'Component Boundary Tests'
        },
        {
            'paths': ['pixel_editor/tests/test_pixel_editor_integration.py'],
            'description': 'Integration Tests'
        },
        {
            'paths': ['pixel_editor/tests/test_indexed_pixel_editor_enhanced.py'],
            'description': 'Enhanced Editor Tests'
        },
        {
            'paths': ['pixel_editor/tests/test_pixel_editor_canvas_v3.py'],
            'description': 'Canvas V3 Tests'
        },
        {
            'paths': ['pixel_editor/tests/test_keyboard_shortcuts.py'],
            'description': 'Keyboard Shortcut Tests'
        },
        # Spritepal tests (sample)
        {
            'paths': ['spritepal/tests/test_controller.py'],
            'description': 'Spritepal Controller Tests'
        },
        {
            'paths': ['spritepal/tests/test_palette_manager.py'],
            'description': 'Palette Manager Tests'
        }
    ]
    
    results = []
    
    for group in test_groups:
        # Expand globs
        expanded_paths = []
        for pattern in group['paths']:
            paths = list(Path('.').glob(pattern))
            expanded_paths.extend([str(p) for p in paths])
        
        if expanded_paths:
            success = run_test_batch(expanded_paths, group['description'])
            results.append((group['description'], success))
        else:
            print(f"\n{'='*60}")
            print(f"{group['description']}")
            print(f"{'='*60}")
            print("⚠ No test files found")
            results.append((group['description'], None))
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    missing = sum(1 for _, result in results if result is None)
    
    for desc, result in results:
        if result is True:
            print(f"✓ {desc}")
        elif result is False:
            print(f"✗ {desc}")
        else:
            print(f"⚠ {desc} - No tests found")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {missing} missing")
    
    if failed > 0:
        print("\n⚠️  Some tests are failing. The refactoring is not complete.")
        return 1
    else:
        print("\n✅ All found tests are passing!")
        return 0

if __name__ == '__main__':
    sys.exit(main())