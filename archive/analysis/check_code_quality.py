#!/usr/bin/env python3
"""
Simple code quality checker for sprite editor
"""

import ast
import sys
from pathlib import Path


def check_file(filepath):
    """Check a Python file for common issues"""
    issues = []

    with open(filepath) as f:
        content = f.read()

    # Check for basic issues
    lines = content.splitlines()

    # Line length
    for i, line in enumerate(lines, 1):
        if len(line) > 120:
            issues.append(f"{filepath}:{i}: Line too long ({len(line)} > 120)")

    # Trailing whitespace
    for i, line in enumerate(lines, 1):
        if line.endswith((" ", "\t")):
            issues.append(f"{filepath}:{i}: Trailing whitespace")

    # Check imports
    try:
        tree = ast.parse(content)

        # Find unused imports (basic check)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    imports.append(alias.name)

        # Check for wildcard imports
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "*":
                        issues.append(f"{filepath}: Wildcard import from {node.module}")

    except SyntaxError as e:
        issues.append(f"{filepath}:{e.lineno}: Syntax error: {e.msg}")

    return issues

def main():
    """Check all Python files in sprite_editor"""
    all_issues = []

    # Check main module files
    for pyfile in Path("sprite_editor").glob("*.py"):
        if pyfile.name != "__pycache__":
            issues = check_file(pyfile)
            all_issues.extend(issues)

    # Check test files
    for pyfile in Path("sprite_editor/tests").glob("*.py"):
        if pyfile.name != "__pycache__":
            issues = check_file(pyfile)
            all_issues.extend(issues)

    if all_issues:
        print(f"Found {len(all_issues)} issues:")
        for issue in sorted(all_issues):
            print(f"  {issue}")
        return 1
    print("No major issues found!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
