#!/usr/bin/env python3
from __future__ import annotations

"""
PySide6 to PySide6 Migration Script

This script systematically migrates all PySide6 imports to PySide6 across the codebase.
It handles API differences, creates backups, logs changes, and verifies imports.

Key transformations:
- All PySide6 imports -> PySide6 imports
- exec_() -> exec()
- Signal -> Signal
- Slot -> Slot
- Property -> Property
- Remove unnecessary QVariant usage
"""

import ast
import logging
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PySide6ToPySide6Migrator:
    """Handles comprehensive PySide6 to PySide6 migration"""

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.backup_dir = root_path / 'backup_pyqt6_migration'
        self.changes_log: list[dict[str, str]] = []
        self.failed_files: list[tuple[str, str]] = []

        # Import mapping from PySide6 to PySide6
        self.import_mappings = {
            'PySide6': 'PySide6',
            'from PySide6': 'from PySide6',
            'import PySide6': 'import PySide6',
        }

        # API mappings for method/class name changes
        self.api_mappings = {
            # Signal/Slot system
            'Signal': 'Signal',
            'Slot': 'Slot',
            'Property': 'Property',
            # Dialog exec method
            '.exec()': '.exec()',
            # Import specific mappings for typing
            'from PySide6.QtCore import Signal': 'from PySide6.QtCore import Signal',
            'from PySide6.QtCore import Slot': 'from PySide6.QtCore import Slot',
            'from PySide6.QtCore import Property': 'from PySide6.QtCore import Property',
        }

        # QVariant removal patterns (PySide6 works directly with Python types)
        self.qvariant_patterns = [
            (r'QVariant\((.*?)\)', r'\1'),  # value -> value
            (r'\.value\(\)', ''),  # Remove  calls on QVariant
            (r'from PySide6\.QtCore [,\s]*', ''),  # Remove QVariant imports
            (r'[,\s]*', ''),
        ]

    def create_backup(self, files_to_backup: list[Path]) -> bool:
        """Create backup of files that will be migrated"""
        try:
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)

            logger.info(f"Creating backup directory: {self.backup_dir}")
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Backing up {len(files_to_backup)} files that will be migrated...")

            for py_file in files_to_backup:
                relative_path = py_file.relative_to(self.root_path)
                backup_file = self.backup_dir / relative_path
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(py_file, backup_file)

            logger.info("Backup completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False

    def find_python_files_with_pyqt6(self) -> list[Path]:
        """Find all Python files containing PySide6 imports"""
        pyqt6_files = []
        python_files = list(self.root_path.rglob('*.py'))

        logger.info(f"Scanning {len(python_files)} Python files for PySide6 usage...")

        for py_file in python_files:
            # Skip backup directories, virtual environments, and archive directories
            if any(skip_dir in str(py_file) for skip_dir in [
                'backup_pyqt6_migration', '.venv', 'venv', 'archive', '__pycache__'
            ]):
                continue

            try:
                with Path(py_file).open(encoding='utf-8') as f:
                    content = f.read()

                if 'PySide6' in content:
                    pyqt6_files.append(py_file)
                    logger.debug(f"Found PySide6 usage in: {py_file}")

            except Exception as e:
                logger.warning(f"Failed to scan {py_file}: {e}")

        logger.info(f"Found {len(pyqt6_files)} files with PySide6 usage")
        return pyqt6_files

    def migrate_imports(self, content: str) -> tuple[str, list[str]]:
        """Migrate PySide6 imports to PySide6"""
        changes = []
        modified_content = content

        # Handle standard import replacements
        for pyqt_import, pyside_import in self.import_mappings.items():
            if pyqt_import in modified_content:
                old_lines = [line for line in modified_content.split('\n') if pyqt_import in line]
                modified_content = modified_content.replace(pyqt_import, pyside_import)
                for line in old_lines:
                    changes.append(f"Import: '{line.strip()}' -> '{line.strip().replace(pyqt_import, pyside_import)}'")

        return modified_content, changes

    def migrate_api_calls(self, content: str) -> tuple[str, list[str]]:
        """Migrate PySide6 API calls to PySide6 equivalents"""
        changes = []
        modified_content = content

        # Handle API method/class name changes
        for old_api, new_api in self.api_mappings.items():
            if old_api in modified_content:
                pattern = re.escape(old_api)
                matches = re.findall(pattern, modified_content)
                if matches:
                    modified_content = re.sub(pattern, new_api, modified_content)
                    changes.append(f"API: '{old_api}' -> '{new_api}' ({len(matches)} occurrences)")

        return modified_content, changes

    def remove_qvariant_usage(self, content: str) -> tuple[str, list[str]]:
        """Remove unnecessary QVariant usage for PySide6"""
        changes = []
        modified_content = content

        for pattern, replacement in self.qvariant_patterns:
            matches = re.findall(pattern, modified_content)
            if matches:
                modified_content = re.sub(pattern, replacement, modified_content)
                changes.append(f"QVariant: Removed {len(matches)} QVariant usage patterns")

        return modified_content, changes

    def handle_type_checking_imports(self, content: str) -> tuple[str, list[str]]:
        """Handle TYPE_CHECKING conditional imports"""
        changes = []
        modified_content = content

        # Handle TYPE_CHECKING blocks that might have PySide6 imports
        if 'TYPE_CHECKING' in content and 'PySide6' in content:
            lines = modified_content.split('\n')
            in_type_checking = False

            for i, line in enumerate(lines):
                if 'if TYPE_CHECKING:' in line:
                    in_type_checking = True
                elif line.strip() and not line.startswith('    ') and not line.startswith('\t'):
                    in_type_checking = False
                elif in_type_checking and 'PySide6' in line:
                    old_line = line
                    new_line = line.replace('PySide6', 'PySide6')
                    lines[i] = new_line
                    changes.append(f"TYPE_CHECKING: '{old_line.strip()}' -> '{new_line.strip()}'")

            modified_content = '\n'.join(lines)

        return modified_content, changes

    def migrate_file(self, file_path: Path) -> bool:
        """Migrate a single file from PySide6 to PySide6"""
        try:
            logger.info(f"Migrating: {file_path}")

            with Path(file_path).open(encoding='utf-8') as f:
                original_content = f.read()

            modified_content = original_content
            all_changes = []

            # Apply all migration steps
            modified_content, import_changes = self.migrate_imports(modified_content)
            all_changes.extend(import_changes)

            modified_content, api_changes = self.migrate_api_calls(modified_content)
            all_changes.extend(api_changes)

            modified_content, qvariant_changes = self.remove_qvariant_usage(modified_content)
            all_changes.extend(qvariant_changes)

            modified_content, type_checking_changes = self.handle_type_checking_imports(modified_content)
            all_changes.extend(type_checking_changes)

            # Only write if there are changes
            if modified_content != original_content:
                with Path(file_path).open('w', encoding='utf-8') as f:
                    f.write(modified_content)

                self.changes_log.append({
                    'file': str(file_path),
                    'changes': all_changes,
                    'timestamp': datetime.now().isoformat()
                })

                logger.info(f"Successfully migrated {file_path} ({len(all_changes)} changes)")
                return True
            logger.info(f"No changes needed for {file_path}")
            return True

        except Exception as e:
            error_msg = f"Failed to migrate {file_path}: {e}"
            logger.error(error_msg)
            self.failed_files.append((str(file_path), str(e)))
            return False

    def verify_imports(self) -> dict[str, bool]:
        """Test that PySide6 imports work correctly"""
        logger.info("Verifying PySide6 imports...")

        verification_results = {}

        # Common PySide6 modules to test
        test_imports = [
            'from PySide6.QtCore import QObject, Signal, Slot',
            'from PySide6.QtWidgets import QApplication, QWidget, QMainWindow',
            'from PySide6.QtGui import QPixmap, QIcon, QPalette',
        ]

        for import_stmt in test_imports:
            try:
                exec(import_stmt)
                verification_results[import_stmt] = True
                logger.info(f"✓ {import_stmt}")
            except ImportError as e:
                verification_results[import_stmt] = False
                logger.error(f"✗ {import_stmt}: {e}")
            except Exception as e:
                verification_results[import_stmt] = False
                logger.error(f"✗ {import_stmt}: Unexpected error - {e}")

        return verification_results

    def check_syntax_validity(self, file_paths: list[Path]) -> dict[str, bool]:
        """Check that migrated files have valid Python syntax"""
        logger.info("Checking syntax validity of migrated files...")

        syntax_results = {}

        for file_path in file_paths:
            try:
                with Path(file_path).open(encoding='utf-8') as f:
                    content = f.read()

                # Try to parse the AST
                ast.parse(content)
                syntax_results[str(file_path)] = True
                logger.debug(f"✓ Syntax valid: {file_path}")

            except SyntaxError as e:
                syntax_results[str(file_path)] = False
                logger.error(f"✗ Syntax error in {file_path}: {e}")
                self.failed_files.append((str(file_path), f"Syntax error: {e}"))

            except Exception as e:
                syntax_results[str(file_path)] = False
                logger.error(f"✗ Error checking {file_path}: {e}")

        valid_files = sum(1 for valid in syntax_results.values() if valid)
        total_files = len(syntax_results)
        logger.info(f"Syntax check: {valid_files}/{total_files} files valid")

        return syntax_results

    def generate_migration_report(self) -> str:
        """Generate a comprehensive migration report"""
        report_lines = [
            "="*80,
            "PySide6 to PySide6 Migration Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "="*80,
            "",
            f"Root directory: {self.root_path}",
            f"Backup directory: {self.backup_dir}",
            "",
            "SUMMARY:",
            f"- Files successfully migrated: {len(self.changes_log)}",
            f"- Files with failures: {len(self.failed_files)}",
            f"- Total changes made: {sum(len(entry['changes']) for entry in self.changes_log)}",
            "",
        ]

        if self.changes_log:
            report_lines.extend([
                "SUCCESSFUL MIGRATIONS:",
                "-" * 40,
            ])

            for entry in self.changes_log:
                report_lines.append(f"File: {entry['file']}")
                report_lines.append(f"Time: {entry['timestamp']}")
                report_lines.append(f"Changes ({len(entry['changes'])}):")
                for change in entry['changes']:
                    report_lines.append(f"  - {change}")
                report_lines.append("")

        if self.failed_files:
            report_lines.extend([
                "FAILED MIGRATIONS:",
                "-" * 40,
            ])

            for file_path, error in self.failed_files:
                report_lines.append(f"File: {file_path}")
                report_lines.append(f"Error: {error}")
                report_lines.append("")

        report_lines.extend([
            "MIGRATION COMPLETE",
            "="*80,
        ])

        return "\n".join(report_lines)

    def run_migration(self) -> bool:
        """Run the complete migration process"""
        logger.info("Starting PySide6 to PySide6 migration...")

        # Step 1: Find files to migrate
        files_to_migrate = self.find_python_files_with_pyqt6()

        if not files_to_migrate:
            logger.info("No PySide6 files found. Migration complete.")
            return True

        # Step 2: Create backup of only files that need migration
        if not self.create_backup(files_to_migrate):
            logger.error("Migration aborted due to backup failure")
            return False

        # Step 3: Migrate each file
        successful_migrations = 0
        for file_path in files_to_migrate:
            if self.migrate_file(file_path):
                successful_migrations += 1

        logger.info(f"Migration completed: {successful_migrations}/{len(files_to_migrate)} files successful")

        # Step 4: Verify syntax of migrated files
        self.check_syntax_validity(files_to_migrate)

        # Step 5: Test imports
        import_results = self.verify_imports()
        all_imports_work = all(import_results.values())

        if not all_imports_work:
            logger.warning("Some PySide6 imports failed. You may need to install PySide6:")
            logger.warning("pip install PySide6")

        # Step 6: Generate report
        report = self.generate_migration_report()
        report_path = self.root_path / 'migration_report.txt'

        with Path(report_path).open('w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Migration report written to: {report_path}")
        print("\n" + report)

        return len(self.failed_files) == 0

    def restore_backup(self) -> bool:
        """Restore files from backup if needed"""
        if not self.backup_dir.exists():
            logger.error("No backup directory found")
            return False

        try:
            logger.info("Restoring from backup...")

            backup_files = list(self.backup_dir.rglob('*.py'))
            for backup_file in backup_files:
                relative_path = backup_file.relative_to(self.backup_dir)
                target_file = self.root_path / relative_path

                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, target_file)

            logger.info(f"Restored {len(backup_files)} files from backup")
            return True

        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Migrate PySide6 codebase to PySide6',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate_to_pyside6.py                    # Migrate current directory
  python migrate_to_pyside6.py --path /my/project # Migrate specific path
  python migrate_to_pyside6.py --restore          # Restore from backup
        """
    )

    parser.add_argument(
        '--path',
        type=Path,
        default=Path(),
        help='Root path to migrate (default: current directory)'
    )

    parser.add_argument(
        '--restore',
        action='store_true',
        help='Restore files from backup instead of migrating'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making changes'
    )

    args = parser.parse_args()

    # Resolve absolute path
    root_path = args.path.resolve()

    if not root_path.exists():
        print(f"Error: Path does not exist: {root_path}")
        sys.exit(1)

    migrator = PySide6ToPySide6Migrator(root_path)

    if args.restore:
        success = migrator.restore_backup()
        sys.exit(0 if success else 1)

    if args.dry_run:
        # Just find and report files that would be changed
        files_to_migrate = migrator.find_python_files_with_pyqt6()
        print(f"\nDry run: Would migrate {len(files_to_migrate)} files:")
        for file_path in files_to_migrate:
            print(f"  - {file_path}")
        sys.exit(0)

    # Confirm before proceeding
    files_to_migrate = migrator.find_python_files_with_pyqt6()
    if files_to_migrate:
        print(f"\nFound {len(files_to_migrate)} files with PySide6 imports.")
        response = input("Proceed with migration? (y/N): ").strip().lower()
        if response != 'y':
            print("Migration cancelled.")
            sys.exit(0)

    # Run migration
    success = migrator.run_migration()

    if success:
        print("\n✓ Migration completed successfully!")
        print("  - Backup created in backup_pyqt6_migration/")
        print("  - Migration report saved as migration_report.txt")
        print("  - Run tests to verify everything works correctly")
    else:
        print("\n✗ Migration completed with errors!")
        print("  - Check migration_report.txt for details")
        print("  - Use --restore to revert changes if needed")

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
