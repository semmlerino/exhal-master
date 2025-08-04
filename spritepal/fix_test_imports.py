#!/usr/bin/env python3
"""
Fix PLC0415 violations in test files by moving imports to top-level.
This script focuses on the 185 test file import violations that can be safely fixed.
"""

import ast
import os
import re
from pathlib import Path

# Test files to process
TEST_PATTERNS = [
    "test_*.py",
    "tests/test_*.py",
    "tests/**/test_*.py",
]

# Imports that should stay inside functions
KEEP_INSIDE_PATTERNS = [
    # Mock setup that needs to happen before import
    r"mock.*\.patch",
    r"monkeypatch",

    # Testing import behavior
    r"pytest\.raises.*ImportError",
    r"test.*import.*error",

    # Conditional imports for testing
    r"if.*pytest",
    r"try:.*import",
]


class ImportMover(ast.NodeTransformer):
    """AST transformer to move imports from functions to module level."""

    def __init__(self):
        self.imports_to_add = []
        self.imports_found = set()

    def visit_FunctionDef(self, node):
        """Visit function definitions and extract imports."""
        new_body = []

        for stmt in node.body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                # Convert to import string
                import_str = self._import_to_string(stmt)

                # Check if we should keep it inside
                if not self._should_keep_inside(import_str, node):
                    if import_str not in self.imports_found:
                        self.imports_found.add(import_str)
                        self.imports_to_add.append(stmt)
                    # Skip adding to function body
                    continue

            new_body.append(stmt)

        node.body = new_body
        return node

    def _import_to_string(self, node):
        """Convert import node to string representation."""
        if isinstance(node, ast.Import):
            names = ", ".join(alias.name for alias in node.names)
            return f"import {names}"
        if isinstance(node, ast.ImportFrom):
            names = ", ".join(alias.name for alias in node.names)
            module = node.module or ""
            level = "." * node.level
            return f"from {level}{module} import {names}"
        return ""

    def _should_keep_inside(self, import_str, func_node):
        """Check if import should stay inside function."""
        # Check function name patterns
        func_name = func_node.name
        if any(pattern in func_name for pattern in ["mock", "patch", "import"]):
            return True

        # Check import string patterns
        for pattern in KEEP_INSIDE_PATTERNS:
            if re.search(pattern, import_str, re.IGNORECASE):
                return True

        return False


def fix_test_file(file_path: Path) -> bool:
    """Fix imports in a single test file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Parse AST
        tree = ast.parse(content)

        # Extract and move imports
        mover = ImportMover()
        new_tree = mover.visit(tree)

        if not mover.imports_to_add:
            return False  # No changes needed

        # Find where to insert imports (after docstring and existing imports)
        insert_line = 0
        for i, node in enumerate(tree.body):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
                # Skip docstring
                insert_line = i + 1
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                # After existing imports
                insert_line = i + 1
            else:
                break

        # Generate new content
        lines = content.splitlines(keepends=True)

        # Insert new imports
        new_imports = []
        for imp in mover.imports_to_add:
            new_imports.append(ast.unparse(imp) + "\n")

        # Add blank line before imports if needed
        if insert_line > 0 and not lines[insert_line - 1].strip() == "":
            new_imports.insert(0, "\n")

        # Insert imports
        for i, imp_line in enumerate(new_imports):
            lines.insert(insert_line + i, imp_line)

        # Write back
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Fix test file imports."""
    print("Fixing PLC0415 violations in test files")
    print("=" * 60)

    # Find all test files
    test_files = []
    for pattern in TEST_PATTERNS:
        test_files.extend(Path(".").glob(pattern))

    print(f"Found {len(test_files)} test files")

    # Process files
    fixed_count = 0
    for test_file in test_files:
        if fix_test_file(test_file):
            print(f"Fixed: {test_file}")
            fixed_count += 1

    print(f"\nFixed {fixed_count} files")

    # Run ruff to check remaining violations
    print("\nChecking remaining PLC0415 violations in test files...")
    os.system("./venv/bin/ruff check --select PLC0415 tests/ test_*.py | grep PLC0415 | wc -l")


if __name__ == "__main__":
    main()
