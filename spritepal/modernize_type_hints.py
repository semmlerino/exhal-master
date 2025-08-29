#!/usr/bin/env python3
"""
Type Safety Modernization Script for Python 3.10+

This script modernizes Python type hints to use the new syntax introduced in Python 3.10+:
- Replace A | B with A | B
- Replace T | None with T | None
- Replace list[T] with list[T]
- Replace dict[K, V] with dict[K, V]
- Replace tuple[T, ...] with tuple[T, ...]
- Replace set[T] with set[T]
- Add from __future__ import annotations where needed
- Use TypeAlias for complex type definitions
- Modernize import statements
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Any


class TypeHintModernizer:
    """Modernizes Python type hints to use Python 3.10+ syntax."""

    def __init__(self):
        self.changes_made = 0
        self.files_processed = 0

        # Patterns for type hint modernization
        self.modernization_patterns = [
            # Union types
            (r'\bUnion\[([^\]]+)\]', self._modernize_union),
            # Optional types
            (r'\bOptional\[([^\]]+)\]', r'\1 | None'),
            # Generic container types
            (r'\bList\[([^\]]+)\]', r'list[\1]'),
            (r'\bDict\[([^\]]+)\]', r'dict[\1]'),
            (r'\bTuple\[([^\]]+)\]', r'tuple[\1]'),
            (r'\bSet\[([^\]]+)\]', r'set[\1]'),
            (r'\bFrozenSet\[([^\]]+)\]', r'frozenset[\1]'),
            # OrderedDict should become dict for Python 3.7+ (dict is ordered)
            (r'\bOrderedDict\[([^\]]+)\]', r'dict[\1]'),
            # Type aliases
            (r'\bType\[([^\]]+)\]', r'type[\1]'),
        ]

        # Import patterns to remove after modernization
        self.import_removals = [
            r'from typing import.*?Union[,\s]*',
            r'from typing import.*?Optional[,\s]*',
            r'from typing import.*?List[,\s]*',
            r'from typing import.*?Dict[,\s]*',
            r'from typing import.*?Tuple[,\s]*',
            r'from typing import.*?Set[,\s]*',
            r'from typing import.*?FrozenSet[,\s]*',
            r'from typing import.*?Type[,\s]*',
        ]

    def _modernize_union(self, match: re.Match[str]) -> str:
        """Convert A | B | C to A | B | C."""
        content = match.group(1)
        # Split on commas but respect nested brackets
        parts = self._split_respect_brackets(content)
        return ' | '.join(part.strip() for part in parts)

    def _split_respect_brackets(self, content: str) -> list[str]:
        """Split on commas while respecting nested brackets."""
        parts = []
        current = ""
        bracket_depth = 0

        for char in content:
            if char in '[({':
                bracket_depth += 1
            elif char in '])}':
                bracket_depth -= 1
            elif char == ',' and bracket_depth == 0:
                parts.append(current)
                current = ""
                continue
            current += char

        if current:
            parts.append(current)

        return parts

    def _needs_future_annotations(self, content: str) -> bool:
        """Check if file needs 'from __future__ import annotations'."""
        # Check if already has future annotations
        if 'from __future__ import annotations' in content:
            return False

        # Check if file uses forward references that would benefit
        patterns = [
            r"'[A-Za-z_][A-Za-z0-9_]*'",  # String type annotations
            r'"[A-Za-z_][A-Za-z0-9_]*"',  # String type annotations
            r'Self',  # Self type hints
            r'-> [A-Z][A-Za-z0-9_]*',  # Return type annotations
        ]

        return any(re.search(pattern, content) for pattern in patterns)

    def _clean_import_line(self, line: str) -> str | None:
        """Clean up import lines after modernization."""
        if 'from typing import' not in line:
            return line

        # Extract the imports
        match = re.search(r'from typing import\s*(.+)', line)
        if not match:
            return None

        imports_part = match.group(1).strip()
        if not imports_part:
            return None

        # Split imports and clean them
        imports = [imp.strip() for imp in imports_part.split(',') if imp.strip()]

        # Filter out modernized types but keep others
        modernized_types = {'Union', 'Optional', 'List', 'Dict', 'Tuple', 'Set', 'FrozenSet', 'Type', 'OrderedDict'}
        kept_imports = [imp for imp in imports if imp not in modernized_types]

        if not kept_imports:
            return None

        # Reconstruct the import line
        return f"from typing import {', '.join(kept_imports)}"

    def _add_type_alias_imports(self, content: str) -> str:
        """Add TypeAlias import if needed."""
        if 'TypeAlias' in content and 'from typing import' in content:
            # Find the typing import line and add TypeAlias if not present
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'from typing import' in line and 'TypeAlias' not in line:
                    # Add TypeAlias to the import
                    lines[i] = line.replace('from typing import', 'from typing import TypeAlias,').replace(',,', ',')
                    break
            content = '\n'.join(lines)
        return content

    def modernize_file(self, file_path: Path) -> bool:
        """Modernize a single Python file."""
        try:
            # Read the file
            content = file_path.read_text(encoding='utf-8')
            original_content = content

            # Apply modernization patterns
            for pattern, replacement in self.modernization_patterns:
                if callable(replacement):
                    content = re.sub(pattern, replacement, content)
                else:
                    content = re.sub(pattern, replacement, content)

            # Add future annotations if needed
            if self._needs_future_annotations(content) and 'from __future__ import annotations' not in content:
                lines = content.split('\n')

                # Find the right place to insert (after module docstring, before other imports)
                insert_index = 0
                in_docstring = False
                docstring_quotes = None

                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if i == 0 and (stripped.startswith('"""') or stripped.startswith("'''")):
                        # Module docstring
                        docstring_quotes = stripped[:3]
                        in_docstring = True
                        if stripped.count(docstring_quotes) >= 2:
                            # Single line docstring
                            insert_index = i + 1
                            break
                    elif in_docstring and docstring_quotes and docstring_quotes in line:
                        insert_index = i + 1
                        in_docstring = False
                        break
                    elif not in_docstring and stripped and not stripped.startswith('#'):
                        insert_index = i
                        break

                # Insert the future import
                if insert_index < len(lines):
                    lines.insert(insert_index, 'from __future__ import annotations')
                    lines.insert(insert_index + 1, '')  # Add blank line
                else:
                    lines.append('from __future__ import annotations')
                    lines.append('')

                content = '\n'.join(lines)

            # Clean up import lines
            lines = content.split('\n')
            cleaned_lines = []

            for line in lines:
                # Clean up typing imports
                if 'from typing import' in line:
                    cleaned = self._clean_import_line(line)
                    if cleaned:
                        cleaned_lines.append(cleaned)
                else:
                    cleaned_lines.append(line)

            content = '\n'.join(cleaned_lines)

            # Add TypeAlias imports if needed
            content = self._add_type_alias_imports(content)

            # Remove excessive blank lines
            content = re.sub(r'\n{3,}', '\n\n', content)

            # Only write if content changed
            if content != original_content:
                file_path.write_text(content, encoding='utf-8')
                self.changes_made += 1
                return True

            return False

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return False

    def modernize_directory(self, directory: Path, pattern: str = "*.py") -> dict[str, Any]:
        """Modernize all Python files in a directory."""
        results = {
            'files_processed': 0,
            'files_modified': 0,
            'errors': []
        }

        for file_path in directory.rglob(pattern):
            # Skip __pycache__ and other generated directories
            if any(part.startswith('.') or part == '__pycache__' for part in file_path.parts):
                continue

            try:
                results['files_processed'] += 1
                if self.modernize_file(file_path):
                    results['files_modified'] += 1
                    print(f"✓ Modernized: {file_path}")
                else:
                    print(f"- No changes: {file_path}")

            except Exception as e:
                error_msg = f"Error processing {file_path}: {e}"
                results['errors'].append(error_msg)
                print(f"✗ {error_msg}")

        return results

    def validate_syntax(self, file_path: Path) -> bool:
        """Validate that the file has correct Python syntax after modernization."""
        try:
            content = file_path.read_text(encoding='utf-8')
            ast.parse(content)
            return True
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return False
        except Exception as e:
            print(f"Error validating {file_path}: {e}")
            return False

def main():
    """Main entry point for the modernization script."""
    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1])
    else:
        target_path = Path.cwd()

    if not target_path.exists():
        print(f"Error: Path {target_path} does not exist")
        sys.exit(1)

    modernizer = TypeHintModernizer()

    print(f"Modernizing type hints in: {target_path}")
    print("=" * 60)

    if target_path.is_file():
        # Single file
        success = modernizer.modernize_file(target_path)
        if success:
            print(f"✓ Successfully modernized {target_path}")
        else:
            print(f"- No changes needed for {target_path}")

        # Validate syntax
        if not modernizer.validate_syntax(target_path):
            print(f"✗ Syntax validation failed for {target_path}")
            sys.exit(1)

    else:
        # Directory
        results = modernizer.modernize_directory(target_path)

        print("\n" + "=" * 60)
        print("MODERNIZATION SUMMARY")
        print("=" * 60)
        print(f"Files processed: {results['files_processed']}")
        print(f"Files modified: {results['files_modified']}")
        print(f"Errors: {len(results['errors'])}")

        if results['errors']:
            print("\nErrors encountered:")
            for error in results['errors']:
                print(f"  - {error}")

        # Validate all modified files
        print("\nValidating syntax...")
        validation_errors = 0
        for file_path in target_path.rglob("*.py"):
            if not modernizer.validate_syntax(file_path):
                validation_errors += 1

        if validation_errors == 0:
            print("✓ All files passed syntax validation")
        else:
            print(f"✗ {validation_errors} files failed syntax validation")
            sys.exit(1)

        print("\n✓ Type hint modernization completed successfully!")

if __name__ == "__main__":
    main()
