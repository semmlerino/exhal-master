#!/usr/bin/env python3
"""Check for structural issues like missing __init__.py and circular imports."""

import ast
import os
from collections import defaultdict
from pathlib import Path


def check_missing_init_files(root_dir):
    """Find directories with Python files but no __init__.py."""
    missing_init = []

    for root, _dirs, files in os.walk(root_dir):
        # Skip special directories
        if any(skip in root for skip in [".venv", "venv", "__pycache__", "node_modules", ".git", "htmlcov"]):
            continue

        # Check if directory has Python files
        py_files = [f for f in files if f.endswith(".py") and f != "__init__.py"]

        if py_files:
            init_file = Path(root) / "__init__.py"
            if not init_file.exists():
                relative_path = Path(root).relative_to(root_dir)
                missing_init.append(str(relative_path))

    return missing_init


def analyze_imports_for_cycles(root_dir):
    """Simple circular import detection."""
    # Map module to its imports
    module_imports = defaultdict(set)

    for root, _dirs, files in os.walk(root_dir):
        # Skip special directories
        if any(skip in root for skip in [".venv", "venv", "__pycache__", "node_modules", ".git"]):
            continue

        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = Path(root) / file
            relative_path = file_path.relative_to(root_dir)

            # Convert path to module name
            module_parts = list(relative_path.parts[:-1])
            if file != "__init__.py":
                module_parts.append(relative_path.stem)
            module_name = ".".join(module_parts)

            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module:
                            if node.level == 0:
                                # Absolute import
                                module_imports[module_name].add(node.module)
                            else:
                                # Relative import - try to resolve
                                parts = module_parts[:-node.level] if node.level <= len(module_parts) else []
                                if node.module:
                                    parts.append(node.module)
                                if parts:
                                    resolved = ".".join(parts)
                                    module_imports[module_name].add(resolved)

            except:
                pass

    # Simple cycle detection
    cycles = []
    for module, imports in module_imports.items():
        for imported in imports:
            # Direct cycle
            if imported in module_imports and module in module_imports[imported]:
                cycle = sorted([module, imported])
                cycle_str = f"{cycle[0]} <-> {cycle[1]}"
                if cycle_str not in cycles:
                    cycles.append(cycle_str)

    return cycles, module_imports


def check_package_installations():
    """Check if required packages are installed."""
    packages = {
        "PyQt6": "PyQt6",
        "PySide6": "PySide6",
        "PIL": "Pillow",
        "numpy": "numpy",
        "pytest": "pytest",
        "ruff": "ruff",
        "basedpyright": "basedpyright"
    }

    installed = []
    missing = []

    for import_name, package_name in packages.items():
        try:
            if import_name == "PIL":
                import PIL
            elif import_name == "PyQt6":
                import PyQt6
            elif import_name == "PySide6":
                import PySide6
            elif import_name == "numpy":
                import numpy
            elif import_name == "pytest":
                import pytest
            elif import_name == "ruff":
                import ruff
            elif import_name == "basedpyright":
                import basedpyright
            installed.append(package_name)
        except ImportError:
            missing.append(package_name)

    return installed, missing


def main():
    root_dir = Path(__file__).parent

    print("=== SpritePal Structure Analysis ===\n")

    # Check missing __init__.py files
    print("Checking for missing __init__.py files...")
    missing_init = check_missing_init_files(root_dir)

    if missing_init:
        print(f"\n❌ Found {len(missing_init)} directories missing __init__.py:")
        for dir_path in missing_init[:10]:
            print(f"  - {dir_path}/")
        if len(missing_init) > 10:
            print(f"  ... and {len(missing_init) - 10} more")
    else:
        print("✅ All Python packages have __init__.py files")

    # Check for circular imports
    print("\n\nChecking for circular imports...")
    cycles, module_imports = analyze_imports_for_cycles(root_dir)

    if cycles:
        print(f"\n⚠️  Found {len(cycles)} potential circular imports:")
        for cycle in cycles[:10]:
            print(f"  - {cycle}")
        if len(cycles) > 10:
            print(f"  ... and {len(cycles) - 10} more")
    else:
        print("✅ No obvious circular imports detected")

    # Check package installations
    print("\n\nChecking package installations...")
    installed, missing = check_package_installations()

    if installed:
        print("\n✅ Installed packages:")
        for pkg in installed:
            print(f"  - {pkg}")

    if missing:
        print("\n❌ Missing packages:")
        for pkg in missing:
            print(f"  - {pkg}")

    # Show import statistics
    print("\n\n=== Import Statistics ===")
    print(f"Total modules analyzed: {len(module_imports)}")

    # Find modules with most imports
    most_imports = sorted(module_imports.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    print("\nModules with most imports:")
    for module, imports in most_imports:
        print(f"  {module}: {len(imports)} imports")

    # Find most imported modules
    import_count = defaultdict(int)
    for imports in module_imports.values():
        for imp in imports:
            import_count[imp] += 1

    most_imported = sorted(import_count.items(), key=lambda x: x[1], reverse=True)[:10]
    print("\nMost imported modules:")
    for module, count in most_imported:
        print(f"  {module}: imported by {count} modules")


if __name__ == "__main__":
    main()
