#!/usr/bin/env python3
"""
Run pixel editor tests with proper configuration for headless environments.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_tests():
    """Run pixel editor tests with appropriate settings."""
    
    # Set environment for headless testing
    env = os.environ.copy()
    env['QT_QPA_PLATFORM'] = 'offscreen'
    env['QT_LOGGING_RULES'] = '*.debug=false'
    
    # Test categories
    test_suites = [
        # Unit tests (no GUI)
        {
            'name': 'Unit Tests',
            'path': '../pixel_editor/tests',
            'markers': 'not gui and not integration',
            'extra_args': []
        },
        # API contracts
        {
            'name': 'API Contract Tests', 
            'path': '../pixel_editor/tests/test_api_contracts*.py',
            'markers': None,
            'extra_args': []
        },
        # Controller tests
        {
            'name': 'Controller Tests',
            'path': '../pixel_editor/tests/test_pixel_editor_controller_v3.py',
            'markers': None,
            'extra_args': []
        },
        # Brush tests
        {
            'name': 'Brush Tests',
            'path': '../pixel_editor/tests/test_brush_functionality.py',
            'markers': None,
            'extra_args': []
        },
        # Component boundary tests
        {
            'name': 'Component Boundary Tests',
            'path': '../pixel_editor/tests/test_component_boundaries.py',
            'markers': None,
            'extra_args': []
        }
    ]
    
    all_passed = True
    results = []
    
    for suite in test_suites:
        print(f"\n{'='*60}")
        print(f"Running {suite['name']}")
        print(f"{'='*60}")
        
        cmd = [
            sys.executable, '-m', 'pytest',
            suite['path'],
            '-v',
            '--tb=short',
            '--no-header',
            '-q'
        ]
        
        if suite['markers']:
            cmd.extend(['-m', suite['markers']])
            
        cmd.extend(suite['extra_args'])
        
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout per suite
            )
            
            if result.returncode == 0:
                print(f"✓ {suite['name']} PASSED")
                results.append((suite['name'], 'PASSED', ''))
            else:
                print(f"✗ {suite['name']} FAILED")
                print("STDOUT:", result.stdout[-500:])  # Last 500 chars
                print("STDERR:", result.stderr[-500:])
                results.append((suite['name'], 'FAILED', result.stderr))
                all_passed = False
                
        except subprocess.TimeoutExpired:
            print(f"✗ {suite['name']} TIMEOUT")
            results.append((suite['name'], 'TIMEOUT', 'Test suite timed out'))
            all_passed = False
        except Exception as e:
            print(f"✗ {suite['name']} ERROR: {e}")
            results.append((suite['name'], 'ERROR', str(e)))
            all_passed = False
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    for name, status, error in results:
        status_symbol = '✓' if status == 'PASSED' else '✗'
        print(f"{status_symbol} {name}: {status}")
        if error and len(error) < 100:
            print(f"  {error}")
    
    print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(run_tests())