#!/usr/bin/env python3
"""
Comprehensive import validation for SpritePal codebase.
Checks for missing imports, circular dependencies, and other import issues.
"""

import ast
import importlib.util
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


class ImportValidator:
    """Validates imports across the entire codebase."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.issues: dict[str, list[dict]] = defaultdict(list)
        self.imports_by_file: dict[str, set[str]] = {}
        self.module_graph: dict[str, set[str]] = defaultdict(set)
        self.stdlib_modules = self._get_stdlib_modules()
        self.known_packages = {
            "PySide6", "PIL", "Pillow", "pytest", "numpy",
            "scipy", "ruff", "basedpyright", "coverage"
        }

    def _get_stdlib_modules(self) -> set[str]:
        """Get a set of standard library module names."""
        import sys
        stdlib = set(sys.builtin_module_names)
        # Add common stdlib modules
        stdlib.update({
            "os", "sys", "time", "datetime", "json", "pathlib",
            "collections", "itertools", "functools", "typing",
            "subprocess", "threading", "multiprocessing", "queue",
            "weakref", "gc", "inspect", "ast", "dis", "traceback",
            "logging", "warnings", "re", "math", "random", "statistics",
            "io", "struct", "pickle", "copy", "hashlib", "base64",
            "urllib", "http", "socket", "ssl", "email", "platform",
            "argparse", "configparser", "tempfile", "shutil", "glob",
            "fnmatch", "sqlite3", "csv", "xml", "html", "gzip", "zipfile",
            "tarfile", "bz2", "lzma", "zlib", "contextlib", "dataclasses",
            "enum", "abc", "concurrent", "asyncio", "importlib", "pkgutil",
            "unittest", "doctest", "pdb", "cProfile", "timeit", "trace",
            "ctypes", "array", "bisect", "heapq", "decimal",
            "fractions", "secrets", "uuid", "textwrap",
            "difflib", "pprint", "reprlib", "atexit", "signal", "faulthandler",
            "builtins", "__future__", "types", "codecs", "encodings",
            "locale", "gettext", "stat", "fileinput", "filecmp", "calendar",
            "sched", "readline", "rlcompleter", "operator", "pwd", "grp",
            "termios", "tty", "pty", "fcntl", "select", "selectors", "errno",
            "resource", "syslog", "ipaddress", "hmac", "binascii", "crypt",
            "cgi", "cgitb", "wsgiref", "xmlrpc", "imaplib", "poplib",
            "smtplib", "telnetlib", "ftplib", "nntplib", "netrc", "getpass",
            "cmd", "shlex", "pydoc", "tabnanny", "compileall", "py_compile",
            "zipapp", "runpy", "modulefinder", "sysconfig", "distutils", "venv", "ensurepip", "tkinter",
            "turtle", "turtledemo", "idle", "plistlib", "webbrowser"
        })
        return stdlib

    def validate_file(self, file_path: Path) -> None:
        """Validate imports in a single Python file."""
        relative_path = file_path.relative_to(self.root_dir)

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, str(file_path))
            imports = self._extract_imports(tree)
            self.imports_by_file[str(relative_path)] = imports

            # Check each import
            for import_name, line_no, is_relative, from_module in self._walk_imports(tree):
                self._check_import(file_path, import_name, line_no, is_relative, from_module)

            # Build module dependency graph
            module_path = self._path_to_module(relative_path)
            for imp in imports:
                if imp.startswith("."):
                    # Relative import
                    resolved = self._resolve_relative_import(module_path, imp)
                    if resolved:
                        self.module_graph[module_path].add(resolved)
                else:
                    # Absolute import
                    self.module_graph[module_path].add(imp.split(".")[0])

        except SyntaxError as e:
            self.issues["syntax_errors"].append({
                "file": str(relative_path),
                "error": str(e),
                "line": e.lineno
            })
        except Exception as e:
            self.issues["parse_errors"].append({
                "file": str(relative_path),
                "error": str(e)
            })

    def _extract_imports(self, tree: ast.AST) -> set[str]:
        """Extract all import names from an AST."""
        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

        return imports

    def _walk_imports(self, tree: ast.AST):
        """Walk through all imports in the AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    yield alias.name, node.lineno, False, None
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                level = node.level
                is_relative = level > 0

                if module:
                    yield module, node.lineno, is_relative, level

                for alias in node.names:
                    full_name = f"{module}.{alias.name}" if module else alias.name
                    yield full_name, node.lineno, is_relative, level

    def _check_import(self, file_path: Path, import_name: str, line_no: int,
                     is_relative: bool, from_level: int | None) -> None:
        """Check if an import is valid."""
        relative_path = file_path.relative_to(self.root_dir)

        # Skip checking some imports
        if import_name == "*":
            return

        # Extract base module name
        base_module = import_name.split(".")[0]

        # Check if it's a known package or stdlib
        if base_module in self.stdlib_modules:
            return

        if base_module in self.known_packages:
            # Check if the package is actually installed
            if not self._is_package_installed(base_module):
                self.issues["missing_dependencies"].append({
                    "file": str(relative_path),
                    "line": line_no,
                    "import": import_name,
                    "package": base_module
                })
            return

        # Handle relative imports
        if is_relative:
            module_path = self._path_to_module(relative_path)
            resolved = self._resolve_relative_import(module_path, "." * (from_level or 1) + import_name)

            if not resolved:
                self.issues["invalid_relative_imports"].append({
                    "file": str(relative_path),
                    "line": line_no,
                    "import": import_name,
                    "level": from_level
                })
                return

            # Check if the resolved module exists
            if not self._module_exists(resolved):
                self.issues["missing_modules"].append({
                    "file": str(relative_path),
                    "line": line_no,
                    "import": import_name,
                    "resolved": resolved
                })
        # Check absolute imports
        elif not self._is_project_module(base_module):
            # Unknown third-party module
            if not self._is_package_installed(base_module):
                self.issues["unknown_imports"].append({
                    "file": str(relative_path),
                    "line": line_no,
                    "import": import_name
                })
        # Project module - check if it exists
        elif not self._module_exists(import_name):
            self.issues["missing_modules"].append({
                "file": str(relative_path),
                "line": line_no,
                "import": import_name
            })

    def _path_to_module(self, path: Path) -> str:
        """Convert file path to module name."""
        parts = path.parts
        if path.suffix == ".py":
            parts = (*parts[:-1], path.stem)

        # Remove __init__ from module path
        if parts[-1] == "__init__":
            parts = parts[:-1]

        return ".".join(parts)

    def _resolve_relative_import(self, current_module: str, relative_import: str) -> str | None:
        """Resolve a relative import to an absolute module name."""
        if not relative_import.startswith("."):
            return relative_import

        level = len(relative_import) - len(relative_import.lstrip("."))
        import_part = relative_import[level:]

        # Split current module into parts
        parts = current_module.split(".")

        # Go up 'level' directories
        if level > len(parts):
            return None

        base_parts = parts[:-level] if level > 0 else parts

        if import_part:
            return ".".join([*base_parts, import_part])
        return ".".join(base_parts)

    def _is_package_installed(self, package_name: str) -> bool:
        """Check if a package is installed."""
        # Map some package names
        package_map = {
            "PIL": "Pillow",
            "cv2": "opencv-python"
        }

        check_name = package_map.get(package_name, package_name)

        try:
            spec = importlib.util.find_spec(check_name)
            return spec is not None
        except (ImportError, ValueError, AttributeError):
            return False

    def _is_project_module(self, module_name: str) -> bool:
        """Check if a module is part of the project."""
        project_modules = {"core", "ui", "utils", "tests", "scripts"}
        return module_name in project_modules

    def _module_exists(self, module_name: str) -> bool:
        """Check if a module exists in the project."""
        parts = module_name.split(".")

        # Check as a module
        module_path = self.root_dir / Path(*parts[:-1]) / f"{parts[-1]}.py"
        if module_path.exists():
            return True

        # Check as a package
        package_path = self.root_dir / Path(*parts) / "__init__.py"
        if package_path.exists():
            return True

        # Check if parent is a module with the attribute
        if len(parts) > 1:
            parent_module = ".".join(parts[:-1])
            if self._module_exists(parent_module):
                # Could be an attribute of the parent module
                return True

        return False

    def check_circular_dependencies(self) -> None:
        """Check for circular import dependencies."""
        visited = set()
        rec_stack = set()

        def has_cycle(module: str, path: list[str]) -> list[str | None]:
            visited.add(module)
            rec_stack.add(module)
            path.append(module)

            for neighbor in self.module_graph.get(module, set()):
                if neighbor not in visited:
                    cycle = has_cycle(neighbor, path.copy())
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    return [*path[cycle_start:], neighbor]

            rec_stack.remove(module)
            return None

        for module in self.module_graph:
            if module not in visited:
                cycle = has_cycle(module, [])
                if cycle:
                    self.issues["circular_imports"].append({
                        "cycle": " -> ".join(cycle)
                    })

    def check_missing_init_files(self) -> None:
        """Check for missing __init__.py files in packages."""
        for root, _dirs, files in os.walk(self.root_dir):
            # Skip special directories
            if any(part.startswith(".") or part in {"__pycache__", "venv"}
                   for part in Path(root).parts):
                continue

            # Check if directory contains Python files
            if any(f.endswith(".py") for f in files):
                init_file = Path(root) / "__init__.py"
                if not init_file.exists():
                    relative_path = Path(root).relative_to(self.root_dir)
                    self.issues["missing_init_files"].append({
                        "directory": str(relative_path)
                    })

    def check_platform_specific_imports(self) -> None:
        """Check for platform-specific import issues."""
        platform_modules = {
            "win32": "Windows",
            "win32api": "Windows",
            "win32con": "Windows",
            "winreg": "Windows",
            "msvcrt": "Windows",
            "pwd": "Unix",
            "grp": "Unix",
            "termios": "Unix",
            "fcntl": "Unix",
            "resource": "Unix"
        }

        for file_path, imports in self.imports_by_file.items():
            for imp in imports:
                base_module = imp.split(".")[0]
                if base_module in platform_modules:
                    self.issues["platform_specific_imports"].append({
                        "file": file_path,
                        "import": imp,
                        "platform": platform_modules[base_module]
                    })

    def validate_all(self) -> dict[str, list[dict]]:
        """Run all validation checks."""
        # Find all Python files
        python_files = []
        for root, _dirs, files in os.walk(self.root_dir):
            # Skip special directories
            if any(part.startswith(".") or part in ["venv", "__pycache__", "node_modules"]
                   for part in Path(root).parts):
                continue

            for file in files:
                if file.endswith(".py"):
                    python_files.append(Path(root) / file)

        # Validate each file
        print(f"Validating {len(python_files)} Python files...")
        for file_path in python_files:
            self.validate_file(file_path)

        # Run additional checks
        print("Checking for circular dependencies...")
        self.check_circular_dependencies()

        print("Checking for missing __init__.py files...")
        self.check_missing_init_files()

        print("Checking for platform-specific imports...")
        self.check_platform_specific_imports()

        return dict(self.issues)

    def generate_requirements_txt(self) -> str:
        """Generate a requirements.txt based on found imports."""
        # Collect all third-party imports
        third_party = set()

        for imports in self.imports_by_file.values():
            for imp in imports:
                base = imp.split(".")[0]
                if (base not in self.stdlib_modules and
                    not self._is_project_module(base)):
                    third_party.add(base)

        # Map import names to package names
        package_map = {
            "PIL": "Pillow",
            "cv2": "opencv-python",
            "sklearn": "scikit-learn",
            "yaml": "PyYAML",
            "wx": "wxPython",
            "cairo": "pycairo",
            "gi": "PyGObject",
            "OpenGL": "PyOpenGL",
            "serial": "pyserial",
            "usb": "pyusb",
            "bluetooth": "pybluez",
            "magic": "python-magic",
            "bs4": "beautifulsoup4",
            "lxml": "lxml",
            "requests": "requests",
            "urllib3": "urllib3",
            "cryptography": "cryptography",
            "jwt": "PyJWT",
            "click": "click",
            "flask": "Flask",
            "django": "Django",
            "fastapi": "fastapi",
            "pydantic": "pydantic",
            "pytest": "pytest",
            "hypothesis": "hypothesis",
            "tox": "tox",
            "black": "black",
            "mypy": "mypy",
            "pylint": "pylint",
            "flake8": "flake8",
            "isort": "isort",
            "poetry": "poetry",
            "setuptools": "setuptools",
            "wheel": "wheel",
            "twine": "twine"
        }

        requirements = []
        for pkg in sorted(third_party):
            package_name = package_map.get(pkg, pkg)
            if self._is_package_installed(pkg):
                requirements.append(package_name)
            else:
                requirements.append(f"# {package_name}  # Not installed")

        return "\n".join(requirements)


def main():
    """Main entry point."""
    root_dir = Path(__file__).parent
    validator = ImportValidator(root_dir)

    print("SpritePal Import Validation")
    print("=" * 60)

    issues = validator.validate_all()

    # Report issues
    total_issues = sum(len(v) for v in issues.values())
    print(f"\nFound {total_issues} issues:")

    if issues["syntax_errors"]:
        print(f"\n❌ Syntax Errors ({len(issues['syntax_errors'])})")
        for issue in issues["syntax_errors"][:5]:
            print(f"  - {issue['file']}:{issue['line']} - {issue['error']}")
        if len(issues["syntax_errors"]) > 5:
            print(f"  ... and {len(issues['syntax_errors']) - 5} more")

    if issues["missing_dependencies"]:
        print(f"\n❌ Missing Dependencies ({len(issues['missing_dependencies'])})")
        packages = {issue["package"] for issue in issues["missing_dependencies"]}
        for pkg in sorted(packages):
            count = sum(1 for i in issues["missing_dependencies"] if i["package"] == pkg)
            print(f"  - {pkg} ({count} imports)")

    if issues["missing_modules"]:
        print(f"\n❌ Missing Project Modules ({len(issues['missing_modules'])})")
        for issue in issues["missing_modules"][:10]:
            print(f"  - {issue['file']}:{issue['line']} - Can't find '{issue['import']}'")
        if len(issues["missing_modules"]) > 10:
            print(f"  ... and {len(issues['missing_modules']) - 10} more")

    if issues["invalid_relative_imports"]:
        print(f"\n❌ Invalid Relative Imports ({len(issues['invalid_relative_imports'])})")
        for issue in issues["invalid_relative_imports"][:5]:
            print(f"  - {issue['file']}:{issue['line']} - Invalid relative import '{issue['import']}'")
        if len(issues["invalid_relative_imports"]) > 5:
            print(f"  ... and {len(issues['invalid_relative_imports']) - 5} more")

    if issues["circular_imports"]:
        print(f"\n⚠️  Circular Imports ({len(issues['circular_imports'])})")
        for issue in issues["circular_imports"]:
            print(f"  - {issue['cycle']}")

    if issues["missing_init_files"]:
        print(f"\n⚠️  Missing __init__.py Files ({len(issues['missing_init_files'])})")
        for issue in issues["missing_init_files"][:5]:
            print(f"  - {issue['directory']}/")
        if len(issues["missing_init_files"]) > 5:
            print(f"  ... and {len(issues['missing_init_files']) - 5} more")

    if issues["platform_specific_imports"]:
        print(f"\n⚠️  Platform-Specific Imports ({len(issues['platform_specific_imports'])})")
        platforms = defaultdict(list)
        for issue in issues["platform_specific_imports"]:
            platforms[issue["platform"]].append(issue)
        for platform, platform_issues in platforms.items():
            print(f"  - {platform}: {len(platform_issues)} imports")

    if issues["unknown_imports"]:
        print(f"\n⚠️  Unknown Imports ({len(issues['unknown_imports'])})")
        unknown = set()
        for issue in issues["unknown_imports"]:
            unknown.add(issue["import"].split(".")[0])
        for imp in sorted(unknown)[:10]:
            print(f"  - {imp}")
        if len(unknown) > 10:
            print(f"  ... and {len(unknown) - 10} more")

    # Generate requirements.txt
    print("\n" + "=" * 60)
    print("Suggested requirements.txt:")
    print("-" * 30)
    requirements = validator.generate_requirements_txt()
    if requirements:
        print(requirements)
    else:
        print("# No third-party dependencies detected")

    # Save detailed report
    report_path = root_dir / "import_validation_report.json"
    with open(report_path, "w") as f:
        json.dump({
            "total_files": len(validator.imports_by_file),
            "total_issues": total_issues,
            "issues": issues,
            "imports_by_file": {k: list(v) for k, v in validator.imports_by_file.items()},
            "module_graph": {k: list(v) for k, v in validator.module_graph.items()}
        }, f, indent=2)

    print(f"\n✅ Detailed report saved to: {report_path}")

    # Return exit code based on critical issues
    critical_issues = (len(issues.get("syntax_errors", [])) +
                      len(issues.get("missing_dependencies", [])) +
                      len(issues.get("missing_modules", [])))

    if critical_issues > 0:
        print(f"\n❌ Found {critical_issues} critical issues that could cause runtime errors!")
        return 1
    print("\n✅ No critical import issues found!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
