#!/usr/bin/env python3
"""Fix all spritepal. imports in the codebase"""

import os
import re
import sys


def fix_imports_in_file(filepath):
    """Fix spritepal. imports in a file"""
    if not os.path.exists(filepath):
        return False

    # Skip non-Python files
    if not filepath.endswith(".py"):
        return False

    # Skip test files and this script
    if "/tests/" in filepath or filepath.endswith("fix_all_imports.py"):
        return False

    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return False

    original_content = content

    # Fix various import patterns
    content = re.sub(r"from spritepal\.utils\.", "from utils.", content)
    content = re.sub(r"from spritepal\.ui\.", "from ui.", content)
    content = re.sub(r"from spritepal\.core\.", "from core.", content)
    content = re.sub(r"import spritepal\.utils\.", "import utils.", content)
    content = re.sub(r"import spritepal\.ui\.", "import ui.", content)
    content = re.sub(r"import spritepal\.core\.", "import core.", content)

    if content != original_content:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"  Error writing {filepath}: {e}")
            return False
    return False

def main():
    """Main function"""
    print("Fixing all spritepal. imports in Python files...")

    fixed_files = []

    # Walk through all Python files
    for root, dirs, files in os.walk("."):
        # Skip hidden directories and __pycache__
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                if fix_imports_in_file(filepath):
                    fixed_files.append(filepath)

    # Report results
    if fixed_files:
        print(f"\nFixed {len(fixed_files)} files:")
        for f in sorted(fixed_files):
            print(f"  - {f}")
    else:
        print("\nNo files needed fixing.")

    print(f"\nTotal files fixed: {len(fixed_files)}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
