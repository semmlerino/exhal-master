#!/usr/bin/env python3
from __future__ import annotations

"""Fix all bare except: clauses automatically."""

import re
from pathlib import Path


def fix_bare_exceptions():
    """Fix all bare except: clauses automatically."""

    # Files found to have bare exceptions
    files_to_fix = [
        'test_composed_dialog_complete.py',
        'test_qsignalspy_api.py',
        'test_headless_safety.py',
        'tests/integration/test_qt_signal_slot_integration.py',
        'tests/integration/test_dialog_singleton_signals.py',
        'tests/test_performance_benchmarks.py',
        'tests/test_unified_manual_offset_performance.py',
        'tests/test_qt_signal_architecture.py',
        'tests/test_unified_dialog_migration.py',
    ]

    fixed_count = 0

    for file_path in files_to_fix:
        path = Path(file_path)
        if not path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue

        content = path.read_text()
        original = content

        # Pattern 1: Replace bare except: with except Exception:
        # Match except: at any indentation level
        content = re.sub(
            r'^(\s*)except\s*:\s*$',
            r'\1except Exception:',
            content,
            flags=re.MULTILINE
        )

        # Pattern 2: If there's a bare except with just pass after it, add logging
        # This requires checking if logging is imported
        if 'import logging' in content or 'from utils.logging_config import get_logger' in content:
            # Has logging available
            content = re.sub(
                r'^(\s*)except Exception:\s*\n\s*pass\s*$',
                r'\1except Exception as e:\n\1    # Caught exception during operation\n\1    pass',
                content,
                flags=re.MULTILINE
            )

        if content != original:
            path.write_text(content)
            # Count how many replacements were made
            replacements = content.count('except Exception:') - original.count('except Exception:')
            fixed_count += replacements
            print(f"✓ Fixed {file_path} ({replacements} bare exceptions)")
        else:
            print(f"ℹ️  No changes needed in {file_path}")

    print(f"\n✅ Total bare exceptions fixed: {fixed_count}")
    return fixed_count

if __name__ == "__main__":
    fix_bare_exceptions()
