"""
Migration helpers for transitioning from MockFactory to RealComponentFactory.

This module provides tools to help migrate tests from using MockFactory's
unsafe mock-based testing to RealComponentFactory's type-safe real component testing.

Usage:
    # Analyze a test file for mock usage
    python -m tests.infrastructure.migration_helpers analyze tests/test_controller.py
    
    # Get migration report for entire test suite
    python -m tests.infrastructure.migration_helpers report
    
    # Generate migration script
    python -m tests.infrastructure.migration_helpers generate tests/test_controller.py
"""

import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class MockUsage:
    """Represents a mock usage instance in a test file."""
    file_path: str
    line_number: int
    mock_type: str
    code_snippet: str
    suggested_replacement: str
    migration_difficulty: str  # "easy", "medium", "hard"


@dataclass
class MigrationStatus:
    """Tracks migration status for a test file."""
    file_path: str
    total_mocks: int = 0
    migrated_count: int = 0
    remaining_count: int = 0
    cast_operations: int = 0
    mock_imports: list[str] = field(default_factory=list)
    mock_usages: list[MockUsage] = field(default_factory=list)
    last_analyzed: Optional[float] = None

    @property
    def migration_percentage(self) -> float:
        """Calculate migration completion percentage."""
        if self.total_mocks == 0:
            return 100.0
        return (self.migrated_count / self.total_mocks) * 100


class MockToRealMigrator:
    """
    Helps migrate tests from MockFactory to RealComponentFactory.
    
    Provides analysis, suggestions, and tracking for test migration.
    """

    # Mock patterns to detect
    MOCK_PATTERNS = {
        r'MockFactory\.create_(\w+)': 'MockFactory method',
        r'create_mock_(\w+)': 'Mock creation function',
        r'Mock\(\)': 'Direct Mock instantiation',
        r'cast\([^,]+,\s*[^)]+\)': 'Type cast operation',
        r'from unittest\.mock import': 'Mock import',
        r'from \.mock_factory import': 'MockFactory import',
    }

    # Replacement mappings
    REPLACEMENTS = {
        'MockFactory.create_main_window': 'RealComponentFactory().create_main_window',
        'MockFactory.create_extraction_manager': 'RealComponentFactory().create_extraction_manager',
        'MockFactory.create_injection_manager': 'RealComponentFactory().create_injection_manager',
        'MockFactory.create_session_manager': 'RealComponentFactory().create_session_manager',
        'MockFactory.create_extraction_worker': 'RealComponentFactory().create_extraction_worker',
        'MockFactory.create_injection_worker': 'RealComponentFactory().create_injection_worker',
        'MockFactory.create_rom_cache': 'RealComponentFactory().create_rom_cache',
        'create_mock_main_window': 'real_factory.create_main_window',
        'create_mock_extraction_manager': 'real_factory.create_extraction_manager',
        'create_mock_injection_manager': 'real_factory.create_injection_manager',
    }

    def __init__(self, test_root: Path | None = None):
        """
        Initialize the migrator.
        
        Args:
            test_root: Root directory for tests (defaults to tests/)
        """
        if test_root is None:
            test_root = Path(__file__).parent.parent
        self.test_root = test_root
        self._migration_cache: dict[str, MigrationStatus] = {}

    def analyze_test_file(self, file_path: Path) -> MigrationStatus:
        """
        Analyze a test file for mock usage.
        
        Args:
            file_path: Path to the test file
            
        Returns:
            MigrationStatus with analysis results
        """
        status = MigrationStatus(file_path=str(file_path))
        status.last_analyzed = time.time()

        if not file_path.exists():
            return status

        content = file_path.read_text()
        lines = content.splitlines()

        # Check for mock imports
        status.mock_imports = self._find_mock_imports(content)

        # Find mock usages
        for line_num, line in enumerate(lines, 1):
            for pattern, mock_type in self.MOCK_PATTERNS.items():
                if re.search(pattern, line):
                    # Skip if it's a comment
                    if line.strip().startswith('#'):
                        continue

                    usage = self._create_mock_usage(
                        file_path, line_num, line, mock_type
                    )
                    status.mock_usages.append(usage)

                    # Count cast operations separately
                    if mock_type == 'Type cast operation':
                        status.cast_operations += 1

        # Calculate totals
        status.total_mocks = len(status.mock_usages)
        status.remaining_count = status.total_mocks

        # Cache the status
        self._migration_cache[str(file_path)] = status

        return status

    def _find_mock_imports(self, content: str) -> list[str]:
        """Find all mock-related imports in the content."""
        imports = []

        import_patterns = [
            r'from unittest\.mock import (.+)',
            r'from \.mock_factory import (.+)',
            r'from tests\.infrastructure\.mock_factory import (.+)',
            r'import unittest\.mock',
        ]

        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            imports.extend(matches)

        return imports

    def _create_mock_usage(
        self,
        file_path: Path,
        line_num: int,
        line: str,
        mock_type: str
    ) -> MockUsage:
        """Create a MockUsage instance with suggested replacement."""
        # Find the best replacement
        suggested = "No automated replacement available"
        difficulty = "hard"

        for old_pattern, new_pattern in self.REPLACEMENTS.items():
            if old_pattern in line:
                suggested = line.replace(old_pattern, new_pattern)
                difficulty = "easy"
                break

        # Check for cast operations
        if 'cast(' in line:
            suggested = "Remove cast() - RealComponentFactory returns properly typed objects"
            difficulty = "medium"

        return MockUsage(
            file_path=str(file_path),
            line_number=line_num,
            mock_type=mock_type,
            code_snippet=line.strip(),
            suggested_replacement=suggested,
            migration_difficulty=difficulty
        )

    def suggest_replacements(self, status: MigrationStatus) -> list[str]:
        """
        Generate replacement suggestions for a migration status.
        
        Args:
            status: MigrationStatus to generate suggestions for
            
        Returns:
            List of suggestion strings
        """
        suggestions = []

        # Import suggestions
        if status.mock_imports:
            suggestions.append(
                "IMPORTS: Replace mock imports with:\n"
                "  from tests.infrastructure.real_component_factory import RealComponentFactory"
            )

        # Group by difficulty
        easy = [u for u in status.mock_usages if u.migration_difficulty == "easy"]
        medium = [u for u in status.mock_usages if u.migration_difficulty == "medium"]
        hard = [u for u in status.mock_usages if u.migration_difficulty == "hard"]

        if easy:
            suggestions.append(f"\nEASY MIGRATIONS ({len(easy)} instances):")
            for usage in easy[:3]:  # Show first 3
                suggestions.append(f"  Line {usage.line_number}: {usage.suggested_replacement}")

        if medium:
            suggestions.append(f"\nMEDIUM MIGRATIONS ({len(medium)} instances):")
            suggestions.append("  - Remove type cast() operations")
            suggestions.append("  - Update type hints to use real types")

        if hard:
            suggestions.append(f"\nHARD MIGRATIONS ({len(hard)} instances):")
            suggestions.append("  - May require restructuring test logic")
            suggestions.append("  - Consider using RealComponentFactory.inject_test_data()")

        # Performance note
        if status.total_mocks > 10:
            suggestions.append(
                "\nPERFORMANCE TIP: Consider using RealComponentFactory as a fixture "
                "to reuse components across tests."
            )

        return suggestions

    def scan_test_directory(self, directory: Path | None = None) -> dict[str, MigrationStatus]:
        """
        Scan an entire test directory for mock usage.
        
        Args:
            directory: Directory to scan (defaults to test_root)
            
        Returns:
            Dictionary mapping file paths to MigrationStatus
        """
        if directory is None:
            directory = self.test_root

        results = {}

        for test_file in directory.rglob("test_*.py"):
            status = self.analyze_test_file(test_file)
            if status.total_mocks > 0:
                results[str(test_file)] = status

        return results

    def track_migration_progress(self) -> dict[str, Any]:
        """
        Track overall migration progress across all tests.
        
        Returns:
            Dictionary with migration statistics
        """
        all_results = self.scan_test_directory()

        total_files = len(all_results)
        total_mocks = sum(s.total_mocks for s in all_results.values())
        total_migrated = sum(s.migrated_count for s in all_results.values())
        total_casts = sum(s.cast_operations for s in all_results.values())

        # Files fully migrated
        fully_migrated = sum(
            1 for s in all_results.values()
            if s.migration_percentage == 100
        )

        # Group by difficulty
        by_difficulty = {
            'easy': 0,
            'medium': 0,
            'hard': 0
        }

        for status in all_results.values():
            for usage in status.mock_usages:
                by_difficulty[usage.migration_difficulty] += 1

        return {
            'total_test_files': total_files,
            'files_with_mocks': total_files,
            'files_fully_migrated': fully_migrated,
            'total_mock_usages': total_mocks,
            'total_migrated': total_migrated,
            'total_remaining': total_mocks - total_migrated,
            'cast_operations': total_casts,
            'overall_percentage': (total_migrated / total_mocks * 100) if total_mocks > 0 else 100,
            'migration_by_difficulty': by_difficulty,
            'top_files_needing_migration': self._get_top_files_needing_migration(all_results, 5)
        }

    def _get_top_files_needing_migration(
        self,
        results: dict[str, MigrationStatus],
        limit: int = 5
    ) -> list[dict[str, Any]]:
        """Get the top files that need migration work."""
        sorted_files = sorted(
            results.items(),
            key=lambda x: x[1].remaining_count,
            reverse=True
        )

        top_files = []
        for file_path, status in sorted_files[:limit]:
            rel_path = Path(file_path).relative_to(self.test_root)
            top_files.append({
                'file': str(rel_path),
                'remaining_mocks': status.remaining_count,
                'cast_operations': status.cast_operations,
                'difficulty': self._assess_migration_difficulty(status)
            })

        return top_files

    def _assess_migration_difficulty(self, status: MigrationStatus) -> str:
        """Assess overall migration difficulty for a file."""
        if status.cast_operations > 10:
            return "hard"

        difficulties = [u.migration_difficulty for u in status.mock_usages]
        if 'hard' in difficulties:
            return "hard"
        if 'medium' in difficulties:
            return "medium"
        return "easy"

    def generate_migration_script(self, file_path: Path) -> str:
        """
        Generate a migration script for a test file.
        
        Args:
            file_path: Path to the test file
            
        Returns:
            Python code string for migration
        """
        status = self.analyze_test_file(file_path)

        script_lines = [
            "#!/usr/bin/env python",
            '"""',
            f"Migration script for {file_path.name}",
            f"Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}",
            '"""',
            "",
            "import re",
            "from pathlib import Path",
            "",
            f"file_path = Path('{file_path}')",
            "content = file_path.read_text()",
            "",
            "# Replacements to apply",
            "replacements = [",
        ]

        # Add easy replacements
        for usage in status.mock_usages:
            if usage.migration_difficulty == "easy":
                old = usage.code_snippet
                new = usage.suggested_replacement
                script_lines.append(f"    (r'{re.escape(old)}', r'{new}'),")

        script_lines.extend([
            "]",
            "",
            "# Apply replacements",
            "for old, new in replacements:",
            "    content = content.replace(old, new)",
            "",
            "# Update imports",
            "if 'from unittest.mock import' in content:",
            "    # Add RealComponentFactory import",
            "    import_line = 'from tests.infrastructure.real_component_factory import RealComponentFactory\\n'",
            "    if import_line not in content:",
            "        # Add after other imports",
            "        lines = content.splitlines()",
            "        for i, line in enumerate(lines):",
            "            if line.startswith('import ') or line.startswith('from '):",
            "                continue",
            "            lines.insert(i, import_line.rstrip())",
            "            break",
            "        content = '\\n'.join(lines)",
            "",
            "# Write back",
            "file_path.write_text(content)",
            f"print('Migrated {file_path.name}')",
        ])

        return "\n".join(script_lines)

    def get_migration_report(self) -> str:
        """
        Generate a comprehensive migration report.
        
        Returns:
            Formatted report string
        """
        progress = self.track_migration_progress()

        report_lines = [
            "=" * 80,
            "MOCKFACTORY TO REALCOMPONENTFACTORY MIGRATION REPORT",
            "=" * 80,
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "OVERALL PROGRESS",
            "-" * 40,
            f"Test files with mocks: {progress['files_with_mocks']}",
            f"Files fully migrated: {progress['files_fully_migrated']}",
            f"Total mock usages: {progress['total_mock_usages']}",
            f"Migrated: {progress['total_migrated']}",
            f"Remaining: {progress['total_remaining']}",
            f"Progress: {progress['overall_percentage']:.1f}%",
            "",
            "MIGRATION COMPLEXITY",
            "-" * 40,
            f"Easy migrations: {progress['migration_by_difficulty']['easy']}",
            f"Medium migrations: {progress['migration_by_difficulty']['medium']}",
            f"Hard migrations: {progress['migration_by_difficulty']['hard']}",
            f"Type cast operations to remove: {progress['cast_operations']}",
            "",
            "TOP FILES NEEDING MIGRATION",
            "-" * 40,
        ]

        for file_info in progress['top_files_needing_migration']:
            report_lines.append(
                f"  {file_info['file']}: "
                f"{file_info['remaining_mocks']} mocks, "
                f"{file_info['cast_operations']} casts "
                f"({file_info['difficulty']} difficulty)"
            )

        report_lines.extend([
            "",
            "NEXT STEPS",
            "-" * 40,
            "1. Start with 'easy' difficulty files",
            "2. Use RealComponentFactory fixtures in conftest.py",
            "3. Remove unnecessary type cast() operations",
            "4. Run tests after each migration to ensure they still pass",
            "5. Use 'python -m tests.infrastructure.migration_helpers generate <file>' for scripts",
            "",
            "=" * 80,
        ])

        return "\n".join(report_lines)


def validate_migration_safety(file_path: Path) -> tuple[bool, list[str]]:
    """
    Validate if a migration is safe to perform.
    
    Args:
        file_path: Path to test file to validate
        
    Returns:
        Tuple of (is_safe, list_of_warnings)
    """
    warnings = []
    is_safe = True

    if not file_path.exists():
        return False, ["File does not exist"]

    content = file_path.read_text()

    # Check for complex mock setups
    if 'side_effect' in content:
        warnings.append("Contains mock side_effects - manual review needed")

    if 'patch' in content:
        warnings.append("Contains @patch decorators - may need adjustment")

    if 'MagicMock' in content:
        warnings.append("Uses MagicMock - consider if real components can replace")

    # Check for mock assertions
    mock_assertions = [
        'assert_called_with',
        'assert_called_once',
        'assert_not_called',
        'call_count',
    ]

    for assertion in mock_assertions:
        if assertion in content:
            warnings.append(f"Uses {assertion} - will need alternative verification")

    # Determine safety
    if len(warnings) > 3:
        is_safe = False

    return is_safe, warnings


def main():
    """CLI interface for migration helpers."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m tests.infrastructure.migration_helpers analyze <file>")
        print("  python -m tests.infrastructure.migration_helpers report")
        print("  python -m tests.infrastructure.migration_helpers generate <file>")
        print("  python -m tests.infrastructure.migration_helpers validate <file>")
        return

    command = sys.argv[1]
    migrator = MockToRealMigrator()

    if command == "analyze" and len(sys.argv) > 2:
        file_path = Path(sys.argv[2])
        status = migrator.analyze_test_file(file_path)

        print(f"\nAnalysis of {file_path.name}:")
        print(f"  Total mocks: {status.total_mocks}")
        print(f"  Cast operations: {status.cast_operations}")
        print(f"  Mock imports: {len(status.mock_imports)}")

        suggestions = migrator.suggest_replacements(status)
        print("\nSuggestions:")
        for suggestion in suggestions:
            print(suggestion)

    elif command == "report":
        report = migrator.get_migration_report()
        print(report)

        # Save to file
        report_file = Path("migration_report.txt")
        report_file.write_text(report)
        print(f"\nReport saved to {report_file}")

    elif command == "generate" and len(sys.argv) > 2:
        file_path = Path(sys.argv[2])
        script = migrator.generate_migration_script(file_path)

        script_file = file_path.with_suffix('.migration.py')
        script_file.write_text(script)
        print(f"Migration script generated: {script_file}")

    elif command == "validate" and len(sys.argv) > 2:
        file_path = Path(sys.argv[2])
        is_safe, warnings = validate_migration_safety(file_path)

        print(f"\nValidation of {file_path.name}:")
        print(f"  Safe to migrate: {'Yes' if is_safe else 'No'}")

        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  - {warning}")

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
