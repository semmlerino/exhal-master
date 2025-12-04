#!/usr/bin/env python3
from __future__ import annotations

"""Find and fix file operations without context managers."""

import ast
import sys
from pathlib import Path
from typing import Any


class ResourceLeakFinder(ast.NodeVisitor):
    """Find file operations without context managers."""

    def __init__(self, source_lines: list[str]):
        self.issues = []
        self.source_lines = source_lines
        self.in_with_statement = False
        self.with_depth = 0

    def visit_With(self, node):
        """Track when we're inside a with statement."""
        self.with_depth += 1
        old_in_with = self.in_with_statement
        self.in_with_statement = True
        self.generic_visit(node)
        self.in_with_statement = old_in_with
        self.with_depth -= 1

    def visit_Call(self, node):
        """Check for problematic function calls."""
        # Check for open() without 'with'
        if isinstance(node.func, ast.Name) and node.func.id == 'open':
            if not self.in_with_statement:
                self.issues.append({
                    'line': node.lineno,
                    'type': 'open without context manager',
                    'code': self.source_lines[node.lineno - 1].strip() if node.lineno <= len(self.source_lines) else ''
                })

        # Check for Path().open() without 'with'
        elif isinstance(node.func, ast.Attribute) and node.func.attr == 'open':
            if isinstance(node.func.value, ast.Call):
                if hasattr(node.func.value.func, 'id') and node.func.value.func.id == 'Path':
                    if not self.in_with_statement:
                        self.issues.append({
                            'line': node.lineno,
                            'type': 'Path().open() without context manager',
                            'code': self.source_lines[node.lineno - 1].strip() if node.lineno <= len(self.source_lines) else ''
                        })

        self.generic_visit(node)

def scan_file(filepath: Path) -> list[dict[str, Any]]:
    """Scan a file for resource leaks."""
    try:
        source = filepath.read_text()
        source_lines = source.split('\n')
        tree = ast.parse(source, str(filepath))

        finder = ResourceLeakFinder(source_lines)
        finder.visit(tree)
        return finder.issues
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"⚠️  Skipping {filepath}: {e}")
        return []

def main():
    """Find all resource leaks in the codebase."""
    print("🔍 Scanning for resource leaks...\n")

    # Define directories to scan
    scan_dirs = ['core', 'ui', 'utils']
    exclude_patterns = ['__pycache__', '.pyc', 'test_', 'tests/']

    all_issues = {}
    total_issues = 0

    for scan_dir in scan_dirs:
        dir_path = Path(scan_dir)
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob('*.py'):
            # Skip test files and cache
            if any(pattern in str(py_file) for pattern in exclude_patterns):
                continue

            issues = scan_file(py_file)
            if issues:
                all_issues[str(py_file)] = issues
                total_issues += len(issues)

    # Report findings
    if all_issues:
        print("❌ Resource leaks found:\n")
        for filepath, issues in sorted(all_issues.items()):
            print(f"\n📄 {filepath}:")
            for issue in issues:
                print(f"  Line {issue['line']}: {issue['type']}")
                if issue['code']:
                    print(f"    Code: {issue['code']}")

        print(f"\n📊 Total issues: {total_issues}")

        # Generate fix suggestions
        print("\n💡 Fix suggestions:")
        print("Replace file operations with context managers:")
        print("""
# BEFORE:
f = open('file.txt')
data = f.read()
f.close()

# AFTER:
with open('file.txt') as f:
    data = f.read()

# BEFORE:
rom_file = Path(rom_path).open('rb')
data = rom_file.read()

# AFTER:
with Path(rom_path).open('rb') as rom_file:
    data = rom_file.read()
""")
    else:
        print("✅ No resource leaks found! All file operations use context managers.")

    return total_issues

if __name__ == "__main__":
    sys.exit(main())
