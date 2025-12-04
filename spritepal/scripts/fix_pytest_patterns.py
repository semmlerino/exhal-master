#!/usr/bin/env python3
from __future__ import annotations

"""Fix pytest pattern violations PT017 and PT011."""

import ast
import re
import sys
from pathlib import Path


class PytestPatternFixer(ast.NodeTransformer):
    """AST transformer to fix pytest pattern violations."""

    def __init__(self, filename: str):
        self.filename = filename
        self.changes: list[tuple[int, str, str]] = []
        self.current_function = None
        self.imports_needed = set()

    def visit_FunctionDef(self, node):
        """Track current function context."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function
        return node

    def visit_Try(self, node):
        """Fix PT017: assertions in except blocks."""
        # Look for try/except blocks with assertions in except handlers
        for handler in node.handlers:
            if handler.name:  # Has an exception variable
                # Check for assertions on the exception
                for stmt in handler.body:
                    if isinstance(stmt, ast.Assert) and self._references_exception(stmt, handler.name):
                        # This is a PT017 violation
                        self._record_pt017_fix(node, handler)
                        self.imports_needed.add("pytest")

        self.generic_visit(node)
        return node

    def _references_exception(self, node, exc_name):
        """Check if an assertion references the exception variable."""
        return any(isinstance(child, ast.Name) and child.id == exc_name for child in ast.walk(node))

    def _record_pt017_fix(self, try_node, handler):
        """Record a fix for PT017 violation."""
        # Extract the line range
        start_line = try_node.lineno
        handler.end_lineno if hasattr(handler, "end_lineno") else handler.lineno

        # Determine what exception type is being caught
        exc_type = "Exception"
        if handler.type:
            if isinstance(handler.type, ast.Name):
                exc_type = handler.type.id
            elif isinstance(handler.type, ast.Attribute):
                exc_type = ast.unparse(handler.type)

        self.changes.append((
            start_line,
            f"PT017 in {self.current_function}: Use pytest.raises instead of try/except with assertion",
            f"with pytest.raises({exc_type}, match=...)"
        ))

def fix_pt011_in_file(filepath: Path) -> list[str]:
    """Fix PT011 violations (too broad pytest.raises)."""
    content = filepath.read_text()
    lines = content.splitlines()

    changes = []
    pattern = re.compile(r"pytest\.raises\s*\(\s*Exception\s*\)")

    for i, line in enumerate(lines, 1):
        if pattern.search(line):
            # Suggest adding match parameter or using specific exception
            changes.append(
                f"Line {i}: PT011 - pytest.raises(Exception) is too broad. "
                f"Use specific exception or add match parameter."
            )

    return changes

def analyze_file(filepath: Path) -> tuple[list[str], bool]:
    """Analyze a file for pytest pattern violations."""
    try:
        content = filepath.read_text()
        tree = ast.parse(content, filename=str(filepath))

        fixer = PytestPatternFixer(str(filepath))
        fixer.visit(tree)

        # Also check for PT011
        pt011_issues = fix_pt011_in_file(filepath)

        all_issues = []

        # Format PT017 issues
        for line, issue, suggestion in fixer.changes:
            all_issues.append(f"Line {line}: {issue} - Suggestion: {suggestion}")

        # Add PT011 issues
        all_issues.extend(pt011_issues)

        needs_pytest_import = bool(fixer.imports_needed) and "import pytest" not in content

        return all_issues, needs_pytest_import

    except Exception as e:
        return [f"Error analyzing file: {e}"], False

def suggest_fixes(test_file: Path):
    """Suggest fixes for a test file."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {test_file}")
    print("="*60)

    issues, needs_import = analyze_file(test_file)

    if not issues:
        print("✓ No pytest pattern violations found")
        return

    if needs_import:
        print("\n⚠️  Need to add: import pytest")

    print("\nIssues found:")
    for issue in issues:
        print(f"  • {issue}")

    # Show example fixes
    print("\nExample fixes:")
    print("\n1. For PT017 (assertion in except block):")
    print("   Before:")
    print("   ```python")
    print("   try:")
    print("       some_function()")
    print("   except ValueError as e:")
    print("       assert 'expected' in str(e)")
    print("   ```")
    print("   After:")
    print("   ```python")
    print("   with pytest.raises(ValueError, match='expected'):")
    print("       some_function()")
    print("   ```")

    print("\n2. For PT011 (too broad exception):")
    print("   Before:")
    print("   ```python")
    print("   with pytest.raises(Exception):")
    print("       some_function()")
    print("   ```")
    print("   After:")
    print("   ```python")
    print("   with pytest.raises(SpecificException, match='error message'):")
    print("       some_function()")
    print("   ```")

def main():
    """Main function to analyze test files."""
    test_dir = Path("tests")

    if not test_dir.exists():
        print(f"Error: {test_dir} directory not found")
        sys.exit(1)

    # Find all test files with violations
    test_files = []

    # Specific files mentioned in the grep output
    violation_files = [
        "test_dialog_instantiation.py",
        "test_error_boundary_integration.py",
        "test_injection_error_scenarios.py",
        "test_realtime_preview_integration.py"
    ]

    for filename in violation_files:
        filepath = test_dir / filename
        if filepath.exists():
            test_files.append(filepath)

    if not test_files:
        print("No test files with violations found")
        return

    print(f"Found {len(test_files)} test files with pytest pattern violations")

    for test_file in test_files:
        suggest_fixes(test_file)

    print("\n" + "="*60)
    print("Summary:")
    print("- PT017: Use pytest.raises() instead of try/except with assertions")
    print("- PT011: Use specific exceptions or match parameter with pytest.raises")
    print("\nRun 'ruff check tests/ --fix' to auto-fix some issues")

if __name__ == "__main__":
    main()
