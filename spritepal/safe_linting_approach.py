#!/usr/bin/env python3
"""
SAFE approach to fixing linting issues - analyze first, fix manually.
This script ONLY analyzes and reports, does NOT auto-fix.
"""

import subprocess
import sys


def check_git_status():
    """Check for uncommitted changes."""
    result = subprocess.run(
        "git status --short | wc -l",
        check=False, shell=True,
        capture_output=True,
        text=True
    )

    uncommitted = int(result.stdout.strip())
    if uncommitted > 0:
        print(f"⚠️  WARNING: {uncommitted} files with uncommitted changes!")
        print("   Recommendation: Commit or stash changes before any auto-fixes")
        return False
    return True

def analyze_import_issues():
    """Analyze import-related issues that need manual review."""
    print("\n📊 IMPORT ANALYSIS")
    print("="*60)

    # Find non-top-level imports
    result = subprocess.run(
        "grep -n '^    import \\|^        import ' $(find . -name '*.py') | wc -l",
        check=False, shell=True,
        capture_output=True,
        text=True
    )

    non_top = int(result.stdout.strip())
    print(f"Non-top-level imports: {non_top}")
    print("⚠️  These often exist for valid reasons (circular imports, conditionals)")

    # Find conditional imports
    result = subprocess.run(
        "grep -l 'if.*:.*import\\|try:.*import' $(find . -name '*.py') | wc -l",
        check=False, shell=True,
        capture_output=True,
        text=True
    )

    conditional = int(result.stdout.strip())
    print(f"Files with conditional imports: {conditional}")
    print("⚠️  DO NOT auto-move these imports!")

def identify_safe_fixes():
    """Identify which fixes are actually safe to automate."""
    print("\n✅ SAFE FIXES (can be automated)")
    print("="*60)

    safe_rules = {
        'W291': 'trailing whitespace',
        'W292': 'no newline at end of file',
        'W293': 'blank line contains whitespace',
        'E501': 'line too long (can be reviewed)',
        'F401': 'unused imports (BUT review each one)',
    }

    for rule, description in safe_rules.items():
        result = subprocess.run(
            f"../venv/bin/ruff check . --select {rule} 2>&1 | grep 'Found' | awk '{{print $2}}'",
            check=False, shell=True,
            capture_output=True,
            text=True
        )

        count = result.stdout.strip()
        if count:
            print(f"{rule}: {count} issues - {description}")

def identify_risky_fixes():
    """Identify fixes that need manual review."""
    print("\n⚠️  RISKY FIXES (need manual review)")
    print("="*60)

    risky_rules = {
        'PLC0415': 'import-outside-top-level (often intentional)',
        'SIM102': 'collapsible-if (can change logic subtly)',
        'RET505': 'superfluous-else-return (can affect readability)',
        'PLR0915': 'too-many-statements (needs refactoring)',
    }

    for rule, description in risky_rules.items():
        result = subprocess.run(
            f"../venv/bin/ruff check . --select {rule} 2>&1 | grep 'Found' | awk '{{print $2}}'",
            check=False, shell=True,
            capture_output=True,
            text=True
        )

        count = result.stdout.strip()
        if count:
            print(f"{rule}: {count} issues - {description}")

def suggest_manual_approach():
    """Suggest a safe manual approach."""
    print("\n📋 RECOMMENDED APPROACH")
    print("="*60)

    print("""
1. FIRST: Commit or stash current changes
   git add -A && git commit -m "WIP: Save current fixes"

2. Fix ONLY whitespace issues (completely safe):
   ../venv/bin/ruff check --select W --fix .

3. Review and commit:
   git diff
   git add -A && git commit -m "fix: Clean whitespace issues"

4. Fix unused imports ONE FILE at a time:
   # Check each file individually
   ../venv/bin/ruff check --select F401 path/to/file.py
   # Review if the import is really unused
   # Some imports are for side effects!

5. For complex issues (PLR0915 - too many statements):
   - Open file in editor
   - Extract methods manually
   - Test after each extraction

6. Run tests after EACH type of fix:
   ../venv/bin/python -m pytest tests/ -x --tb=short
    """)

def analyze_by_file():
    """Show which files have the most issues."""
    print("\n📁 TOP FILES NEEDING ATTENTION")
    print("="*60)

    result = subprocess.run(
        "../venv/bin/ruff check . 2>&1 | grep '.py:' | cut -d: -f1 | sort | uniq -c | sort -rn | head -10",
        check=False, shell=True,
        capture_output=True,
        text=True
    )

    print("Files with most linting issues:")
    print(result.stdout)

    print("\nRecommendation: Fix these files one at a time, testing after each.")

def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║          SAFE Linting Analysis (No Auto-Fix)               ║
║          "Measure twice, cut once"                         ║
╚════════════════════════════════════════════════════════════╝
    """)

    # Check git status first
    git_clean = check_git_status()

    if not git_clean:
        print("\n❌ STOP: Commit your changes before proceeding!")
        print("   Run: git add -A && git commit -m 'WIP: Current fixes'")
        sys.exit(1)

    # Analyze issues
    analyze_import_issues()
    identify_safe_fixes()
    identify_risky_fixes()
    analyze_by_file()
    suggest_manual_approach()

    print("\n" + "="*60)
    print("🎯 NEXT STEP: Start with whitespace fixes only (safest)")
    print("   ../venv/bin/ruff check --select W --fix .")
    print("="*60)

if __name__ == "__main__":
    main()
