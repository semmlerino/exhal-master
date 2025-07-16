#!/usr/bin/env python3
"""Run pytest for the ultrathink sprite editor project"""

import subprocess
import sys
from pathlib import Path

# Find project root and add parent to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test commands organized by type
test_commands = {
    "all": ["python3", "-m", "pytest", str(project_root), "-v"],
    "unit": ["python3", "-m", "pytest", str(project_root), "-v", "-m", "unit"],
    "integration": ["python3", "-m", "pytest", str(project_root), "-v", "-m", "integration"],
    "sprite_editor": ["python3", "-m", "pytest", str(project_root / "sprite_editor/tests"), "-v"],
    "pixel_editor": ["python3", "-m", "pytest", str(project_root / "pixel_editor/tests"), "-v"],
    "no_gui": ["python3", "-m", "pytest", str(project_root), "-v", "-k", "not gui"],
    "coverage": ["python3", "-m", "pytest", str(project_root), "--cov=sprite_editor", "--cov=pixel_editor", "--cov-report=html"],
}

def run_tests(test_type="all"):
    """Run tests based on type"""
    if test_type not in test_commands:
        print(f"Unknown test type: {test_type}")
        print(f"Available types: {', '.join(test_commands.keys())}")
        return 1
    
    cmd = test_commands[test_type]
    print(f"Running: {' '.join(cmd)}")
    
    return subprocess.call(cmd)

if __name__ == "__main__":
    test_type = sys.argv[1] if len(sys.argv) > 1 else "all"
    sys.exit(run_tests(test_type))