#!/usr/bin/env python3
from __future__ import annotations

"""Quick script to filter and categorize basedpyright errors by specific rules."""

import json
import subprocess
import sys
from collections import defaultdict


def main():
    # Run basedpyright and get JSON output
    result = subprocess.run([
        "python3", "-m", "basedpyright", ".", "--outputjson"
    ], check=False, capture_output=True, text=True, cwd="/mnt/c/CustomScripts/KirbyMax/workshop/exhal-master/spritepal")

    if result.returncode != 0:
        try:
            data = json.loads(result.stderr)
        except json.JSONDecodeError:
            print("Failed to parse basedpyright output")
            sys.exit(1)
    else:
        data = json.loads(result.stdout)

    # Target rules
    target_rules = {
        "reportGeneralTypeIssues",
        "reportIncompatibleMethodOverride",
        "reportOptionalSubscript",
        "reportAssignmentType"
    }

    # Filter errors by target rules
    filtered_errors = defaultdict(list)

    for error in data.get("generalDiagnostics", []):
        rule = error.get("rule", "")
        if rule in target_rules:
            filtered_errors[rule].append({
                "file": error["file"],
                "line": error["range"]["start"]["line"] + 1,  # Convert to 1-based
                "message": error["message"],
                "severity": error["severity"]
            })

    # Print summary
    print("Type Error Summary:")
    total = 0
    for rule in target_rules:
        count = len(filtered_errors[rule])
        total += count
        print(f"  {rule}: {count}")
    print(f"  Total: {total}")
    print()

    # Print details for each rule
    for rule in target_rules:
        if filtered_errors[rule]:
            print(f"\n=== {rule} ({len(filtered_errors[rule])} errors) ===")
            for error in filtered_errors[rule][:5]:  # Show first 5 of each type
                filename = error["file"].split("/")[-1]
                print(f"  {filename}:{error['line']} - {error['message']}")
            if len(filtered_errors[rule]) > 5:
                print(f"  ... and {len(filtered_errors[rule]) - 5} more")

if __name__ == "__main__":
    main()
