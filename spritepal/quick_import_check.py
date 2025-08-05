#!/usr/bin/env python3
"""Quick import checker focusing on key issues."""

import ast
import os
from collections import defaultdict
from pathlib import Path


def check_imports(root_dir):
    """Quick import check focusing on common issues."""

    issues = defaultdict(list)
    import_stats = defaultdict(int)

    # Walk through Python files
    for root, _dirs, files in os.walk(root_dir):
        # Skip directories
        if any(skip in root for skip in [".venv", "venv", "__pycache__", "node_modules", ".git"]):
            continue

        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = Path(root) / file
            relative_path = file_path.relative_to(root_dir)

            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            import_stats[alias.name] += 1

                            # Check for removed packages
                            if alias.name == "scipy":
                                issues["scipy_imports"].append(f"{relative_path}:{node.lineno}")

                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        import_stats[module] += 1

                        # Check for scipy
                        if module and module.startswith("scipy"):
                            issues["scipy_imports"].append(f"{relative_path}:{node.lineno}")

                        # Check for problematic relative imports
                        if node.level > 2:  # ..
                            issues["deep_relative_imports"].append(
                                f"{relative_path}:{node.lineno} - {'.' * node.level}{module}"
                            )

            except SyntaxError as e:
                issues["syntax_errors"].append(f"{relative_path}:{e.lineno} - {e.msg}")
            except Exception as e:
                issues["parse_errors"].append(f"{relative_path} - {e!s}")

    # Print results
    print("=== Import Analysis Results ===\n")

    # Top imports
    print("Top 20 imported modules:")
    for module, count in sorted(import_stats.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"  {module}: {count}")

    print(f"\nTotal unique imports: {len(import_stats)}")

    # Issues
    if issues:
        print("\n=== Issues Found ===")

        for issue_type, issue_list in issues.items():
            if issue_list:
                print(f"\n{issue_type}: {len(issue_list)}")
                for issue in issue_list[:5]:
                    print(f"  - {issue}")
                if len(issue_list) > 5:
                    print(f"  ... and {len(issue_list) - 5} more")
    else:
        print("\n✅ No critical import issues found!")

    # Check for specific packages
    print("\n=== Package Usage ===")
    packages = ["numpy", "PIL", "PySide6", "pytest", "typing", "pathlib", "json", "logging"]
    for pkg in packages:
        count = import_stats.get(pkg, 0)
        if count > 0:
            print(f"  {pkg}: {count} files")


if __name__ == "__main__":
    root_dir = Path(__file__).parent
    check_imports(root_dir)
