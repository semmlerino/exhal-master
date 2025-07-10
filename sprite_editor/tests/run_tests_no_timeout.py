#!/usr/bin/env python3
"""
Run tests in groups to identify timeout issues
"""
import subprocess
import sys
import time
from pathlib import Path

# Group tests by type
test_groups = {
    "controllers": [
        "test_controllers.py",
        "test_extract_controller.py",
        "test_inject_controller.py",
        "test_main_controller.py",
        "test_palette_controller.py",
        "test_viewer_controller.py",
    ],
    "models": [
        "test_models.py",
        "test_project_management.py",
        "test_settings_manager.py",
    ],
    "gui": [
        "test_gui_views.py",
        "test_gui_workflows.py",
        "test_enhanced_gui_interaction.py",
    ],
    "workers": ["test_workers.py"],
    "core": [
        "test_sprite_editor_core.py",
        "test_sprite_editor_core_coverage.py",
        "test_sprite_extractor.py",
        "test_sprite_injector.py",
        "test_sprite_assembler.py",
        "test_sprite_disassembler.py",
    ],
    "utils": [
        "test_tile_utils.py",
        "test_palette_utils.py",
        "test_validation.py",
        "test_file_operations.py",
    ],
    "workflows": [
        "test_sprite_workflow.py",
        "test_png_to_snes.py",
        "test_snes_tiles_to_png.py",
    ],
    "integration": [
        "test_integration.py",
        "test_oam_integration.py",
        "test_oam_palette_mapper.py",
        "test_oam_palette_mapper_coverage.py",
    ],
    "app": [
        "test_application.py",
        "test_initialization_bug.py",
        "test_unified_sprite_editor.py",
    ],
}


def run_test_group(group_name, test_files):
    """Run a group of tests with timeout"""
    print(f"\n{'='*60}")
    print(f"Running {group_name} tests...")
    print(f"{'='*60}")

    for test_file in test_files:
        test_path = Path("sprite_editor/tests") / test_file
        if not test_path.exists():
            print(f"  ⚠️  {test_file} - NOT FOUND")
            continue

        print(f"\n  Running {test_file}...", end="", flush=True)
        start_time = time.time()

        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", str(test_path), "-v", "-q", "--tb=short"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout per file
            )

            elapsed = time.time() - start_time

            if result.returncode == 0:
                # Count passed tests
                passed = result.stdout.count(" PASSED")
                print(f" ✓ ({passed} tests, {elapsed:.1f}s)")
            else:
                # Count failures
                failed = result.stdout.count(" FAILED")
                print(f" ✗ ({failed} failures, {elapsed:.1f}s)")
                if "--tb=short" in result.stdout:
                    print(f"    Error: {result.stdout.split('FAILED')[0].strip()}")

        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            print(f" ⏱️  TIMEOUT ({elapsed:.1f}s)")
            return False

    return True


def main():
    """Run all test groups"""
    print("Running pytest tests in groups to identify timeouts...")

    timeout_groups = []

    for group_name, test_files in test_groups.items():
        if not run_test_group(group_name, test_files):
            timeout_groups.append(group_name)

    print(f"\n{'='*60}")
    print("Summary:")
    print(f"{'='*60}")

    if timeout_groups:
        print(f"\n⏱️  Groups with timeouts: {', '.join(timeout_groups)}")
        return 1
    print("\n✓ All tests completed without timeouts!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
