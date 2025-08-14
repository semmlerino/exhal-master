#!/usr/bin/env python3
"""
Quick script to fix priority linting and type issues in SpritePal.
Run this to get started with the action plan.
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"📋 {description}")
    print(f"💻 Command: {cmd}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"⚠️ Warnings/Errors:\n{result.stderr}")
    
    return result.returncode == 0

def main():
    """Execute priority fixes."""
    
    print("""
╔════════════════════════════════════════════════════════════╗
║        SpritePal Priority Issue Fixer                      ║
║        Based on PRIORITY_ACTION_PLAN.md                    ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    # Check current status
    print("\n📊 CURRENT STATUS")
    print("="*60)
    
    # Get linting stats
    subprocess.run("../venv/bin/ruff check . --statistics | head -10", shell=True)
    
    print("\n🚀 STARTING QUICK WINS")
    
    # 1. Fix simple style issues automatically
    if run_command(
        "../venv/bin/ruff check --fix --select SIM,RET .",
        "Fixing simplifiable code patterns (SIM) and return statements (RET)"
    ):
        print("✅ Simple patterns fixed!")
    
    # 2. Fix import organization
    if run_command(
        "../venv/bin/ruff check --fix --select I .",
        "Organizing imports"
    ):
        print("✅ Imports organized!")
    
    # 3. Show top files needing manual attention
    print("\n📝 FILES NEEDING MANUAL ATTENTION")
    print("="*60)
    
    result = subprocess.run(
        "../venv/bin/ruff check . 2>&1 | grep -E '\.py:' | cut -d: -f1 | sort | uniq -c | sort -rn | head -10",
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result.stdout:
        print("Top files with issues:")
        print(result.stdout)
    
    # 4. Check for type errors
    print("\n🔍 TYPE ERROR CHECK")
    print("="*60)
    
    result = subprocess.run(
        "../venv/bin/basedpyright --project . 2>&1 | tail -5",
        shell=True,
        capture_output=True,
        text=True
    )
    print(result.stdout)
    
    # 5. Suggest next steps
    print("\n📋 RECOMMENDED NEXT STEPS")
    print("="*60)
    print("""
1. Fix code complexity in files with most issues:
   - Use 'Extract Method' refactoring for PLR0915 (too-many-statements)
   - Split complex conditionals for PLR0912 (too-many-branches)

2. Replace path operations with pathlib:
   - PTH123: Use Path().open() instead of open()
   - PTH110: Use Path().exists() instead of os.path.exists()
   
3. Fix import issues:
   - PLC0415: Move imports to top of file where possible
   - F401: Remove unused imports

4. Run tests to ensure nothing broke:
   ../venv/bin/python -m pytest tests/ -x --tb=short

5. For detailed plan, see PRIORITY_ACTION_PLAN.md
    """)
    
    # Show final status
    print("\n📊 FINAL STATUS")
    print("="*60)
    result = subprocess.run(
        "../venv/bin/ruff check . 2>&1 | tail -1",
        shell=True,
        capture_output=True,
        text=True
    )
    print(result.stdout)

if __name__ == "__main__":
    main()