#!/usr/bin/env python3
"""
Tests for sprite_workflow module
Tests complete workflow orchestration with comprehensive coverage
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sprite_editor.sprite_workflow import (
    extract_sprites,
    inject_sprites,
    main,
    quick_inject,
    run_command,
    show_help,
)


@pytest.fixture
def temp_files(tmp_path):
    """Create temporary test files"""
    # Create test PNG file
    png_file = tmp_path / "test_sprites.png"
    png_file.write_text("fake png content")

    # Create VRAM file
    vram_file = tmp_path / "VRAM.dmp"
    vram_file.write_bytes(b"fake vram data" * 100)

    return {"png": str(png_file), "vram": str(vram_file), "dir": str(tmp_path)}


@pytest.mark.unit
class TestRunCommand:
    """Test command execution functionality"""

    def test_run_command_success(self):
        """Test successful command execution"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Command output"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch("builtins.print") as mock_print:
                result = run_command(["echo", "test"])

        assert result is True
        mock_run.assert_called_once_with(
            ["echo", "test"], capture_output=True, text=True
        )
        mock_print.assert_any_call("Running: echo test")
        mock_print.assert_any_call("Command output")

    def test_run_command_failure(self):
        """Test failed command execution"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error message"

        with patch("subprocess.run", return_value=mock_result):
            with patch("builtins.print") as mock_print:
                result = run_command(["false"])

        assert result is False
        mock_print.assert_any_call("Running: false")
        mock_print.assert_any_call("Error message")

    def test_run_command_with_both_outputs(self):
        """Test command with both stdout and stderr"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success output"
        mock_result.stderr = "Warning message"

        with patch("subprocess.run", return_value=mock_result):
            with patch("builtins.print") as mock_print:
                result = run_command(["test"])

        assert result is True
        mock_print.assert_any_call("Success output")
        mock_print.assert_any_call("Warning message")

    def test_run_command_empty_outputs(self):
        """Test command with no output"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            with patch("builtins.print") as mock_print:
                result = run_command(["true"])

        assert result is True
        # Should only print the running command
        mock_print.assert_called_once_with("Running: true")


@pytest.mark.unit
class TestExtractSprites:
    """Test sprite extraction workflow"""

    def test_extract_sprites_success(self):
        """Test successful sprite extraction"""
        with patch("sprite_editor.sprite_workflow.run_command") as mock_run:
            mock_run.return_value = True

            with patch("builtins.print") as mock_print:
                extract_sprites()

        # Should call run_command twice (grayscale and colored)
        assert mock_run.call_count == 2

        # Check first call (grayscale extraction)
        first_call = mock_run.call_args_list[0][0][0]
        assert first_call == [
            "python3",
            "sprite_extractor.py",
            "--offset",
            "0xC000",
            "--size",
            "0x4000",
            "--output",
            "sprites_to_edit.png",
        ]

        # Check second call (colored reference)
        second_call = mock_run.call_args_list[1][0][0]
        assert "sprites_reference_colored.png" in second_call
        assert "--palette" in second_call
        assert "8" in second_call

        # Check print messages
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("EXTRACTING SPRITES" in call for call in print_calls)
        assert any("sprites_to_edit.png" in call for call in print_calls)
        assert any("NEXT STEPS:" in call for call in print_calls)

    def test_extract_sprites_first_command_fails(self):
        """Test when first extraction command fails"""
        with patch("sprite_editor.sprite_workflow.run_command") as mock_run:
            mock_run.side_effect = [False, True]  # First fails, second succeeds

            with patch("builtins.print") as mock_print:
                extract_sprites()

        # Should still try both commands
        assert mock_run.call_count == 2

        # Should not print success message for first command
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        success_calls = [call for call in print_calls if "sprites_to_edit.png" in call]
        assert len(success_calls) == 0  # No success message

    def test_extract_sprites_second_command_fails(self):
        """Test when second extraction command fails"""
        with patch("sprite_editor.sprite_workflow.run_command") as mock_run:
            mock_run.side_effect = [True, False]  # First succeeds, second fails

            with patch("builtins.print") as mock_print:
                extract_sprites()

        assert mock_run.call_count == 2

        # Should print success for first but not second
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("sprites_to_edit.png" in call for call in print_calls)
        assert not any("sprites_reference_colored.png" in call for call in print_calls)

    def test_extract_sprites_both_commands_fail(self):
        """Test when both extraction commands fail"""
        with patch("sprite_editor.sprite_workflow.run_command") as mock_run:
            mock_run.return_value = False

            with patch("builtins.print") as mock_print:
                extract_sprites()

        assert mock_run.call_count == 2

        # Should print headers but no success messages
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("EXTRACTING SPRITES" in call for call in print_calls)
        assert not any("✅" in call for call in print_calls)


@pytest.mark.unit
class TestInjectSprites:
    """Test sprite injection workflow"""

    def test_inject_sprites_success(self, temp_files):
        """Test successful sprite injection"""
        with patch("sprite_editor.sprite_workflow.run_command") as mock_run:
            mock_run.return_value = True

            with patch("builtins.print") as mock_print:
                result = inject_sprites(temp_files["png"])

        assert result is None  # Function doesn't return boolean

        # Check command was called correctly
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "python3"
        assert cmd[1] == "sprite_injector.py"
        assert cmd[2] == temp_files["png"]
        assert "--output" in cmd
        assert "--preview" in cmd

        # Check output filename generation
        expected_output = f"VRAM_{Path(temp_files['png']).stem}.dmp"
        assert expected_output in cmd

        # Check success messages
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("INJECTING EDITED SPRITES" in call for call in print_calls)
        assert any("SUCCESS!" in call for call in print_calls)

    def test_inject_sprites_file_not_found(self):
        """Test injection with non-existent file"""
        with patch("builtins.print") as mock_print:
            result = inject_sprites("/nonexistent/file.png")

        assert result is False
        mock_print.assert_any_call("Error: File '/nonexistent/file.png' not found")

    def test_inject_sprites_command_fails(self, temp_files):
        """Test injection when command fails"""
        with patch("sprite_editor.sprite_workflow.run_command") as mock_run:
            mock_run.return_value = False

            with patch("builtins.print") as mock_print:
                inject_sprites(temp_files["png"])

        # Should still call command
        mock_run.assert_called_once()

        # Should not print success messages
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert not any("SUCCESS!" in call for call in print_calls)

    def test_inject_sprites_output_filename_generation(self, temp_files):
        """Test output filename generation logic"""
        # Create test file with complex name
        complex_file = os.path.join(temp_files["dir"], "my.edited.sprites.png")
        Path(complex_file).write_text("test")

        with patch("sprite_editor.sprite_workflow.run_command") as mock_run:
            mock_run.return_value = True

            inject_sprites(complex_file)

        cmd = mock_run.call_args[0][0]
        output_idx = cmd.index("--output") + 1
        output_file = cmd[output_idx]

        assert output_file == "VRAM_my.edited.sprites.dmp"


@pytest.mark.unit
class TestQuickInject:
    """Test quick injection functionality"""

    def test_quick_inject_success(self, temp_files):
        """Test successful quick injection"""
        with patch("subprocess.run") as mock_run:
            quick_inject(temp_files["png"])

        mock_run.assert_called_once_with(
            ["python3", "sprite_injector.py", temp_files["png"]]
        )

    def test_quick_inject_file_not_found(self):
        """Test quick inject with non-existent file"""
        with patch("builtins.print") as mock_print:
            quick_inject("/nonexistent/file.png")

        mock_print.assert_called_with("Error: File '/nonexistent/file.png' not found")

    def test_quick_inject_no_output_capture(self, temp_files):
        """Test that quick inject doesn't capture output"""
        with patch("subprocess.run") as mock_run:
            quick_inject(temp_files["png"])

        # Should call subprocess.run without capture_output
        args, kwargs = mock_run.call_args
        assert "capture_output" not in kwargs
        assert "text" not in kwargs


@pytest.mark.unit
class TestShowHelp:
    """Test help display functionality"""

    def test_show_help(self):
        """Test help message display"""
        with patch("builtins.print") as mock_print:
            show_help()

        mock_print.assert_called_once()
        help_text = mock_print.call_args[0][0]

        # Check key content is in help text
        assert "Kirby Sprite Editing Workflow" in help_text
        assert "COMMANDS:" in help_text
        assert "extract" in help_text
        assert "inject" in help_text
        assert "quick" in help_text
        assert "FULL WORKFLOW:" in help_text
        assert "EXAMPLES:" in help_text
        assert "IMPORTANT NOTES:" in help_text


@pytest.mark.unit
class TestMainFunction:
    """Test main entry point"""

    def test_main_no_arguments(self, monkeypatch):
        """Test main with no arguments"""
        monkeypatch.setattr("sys.argv", ["sprite_workflow.py"])

        with patch("sprite_editor.sprite_workflow.show_help") as mock_help:
            main()

        mock_help.assert_called_once()

    def test_main_extract_command(self, monkeypatch):
        """Test main with extract command"""
        monkeypatch.setattr("sys.argv", ["sprite_workflow.py", "extract"])

        with patch("sprite_editor.sprite_workflow.extract_sprites") as mock_extract:
            main()

        mock_extract.assert_called_once()

    def test_main_inject_command_success(self, monkeypatch, temp_files):
        """Test main with inject command"""
        monkeypatch.setattr(
            "sys.argv", ["sprite_workflow.py", "inject", temp_files["png"]]
        )

        with patch("sprite_editor.sprite_workflow.inject_sprites") as mock_inject:
            main()

        mock_inject.assert_called_once_with(temp_files["png"])

    def test_main_inject_command_missing_file(self, monkeypatch):
        """Test inject command without file argument"""
        monkeypatch.setattr("sys.argv", ["sprite_workflow.py", "inject"])

        with patch("builtins.print") as mock_print:
            main()

        mock_print.assert_any_call("Error: Please specify PNG file to inject")
        mock_print.assert_any_call("Usage: python sprite_workflow.py inject <file.png>")

    def test_main_quick_command_success(self, monkeypatch, temp_files):
        """Test main with quick command"""
        monkeypatch.setattr(
            "sys.argv", ["sprite_workflow.py", "quick", temp_files["png"]]
        )

        with patch("sprite_editor.sprite_workflow.quick_inject") as mock_quick:
            main()

        mock_quick.assert_called_once_with(temp_files["png"])

    def test_main_quick_command_missing_file(self, monkeypatch):
        """Test quick command without file argument"""
        monkeypatch.setattr("sys.argv", ["sprite_workflow.py", "quick"])

        with patch("builtins.print") as mock_print:
            main()

        mock_print.assert_called_with("Error: Please specify PNG file")

    def test_main_help_commands(self, monkeypatch):
        """Test various help command formats"""
        help_variants = ["help", "-h", "--help"]

        for help_cmd in help_variants:
            monkeypatch.setattr("sys.argv", ["sprite_workflow.py", help_cmd])

            with patch("sprite_editor.sprite_workflow.show_help") as mock_help:
                main()

            mock_help.assert_called_once()

    def test_main_unknown_command(self, monkeypatch):
        """Test main with unknown command"""
        monkeypatch.setattr("sys.argv", ["sprite_workflow.py", "unknown"])

        with patch("builtins.print") as mock_print:
            with patch("sprite_editor.sprite_workflow.show_help") as mock_help:
                main()

        mock_print.assert_called_with("Unknown command: unknown")
        mock_help.assert_called_once()

    def test_main_case_insensitive(self, monkeypatch):
        """Test that commands are case insensitive"""
        monkeypatch.setattr("sys.argv", ["sprite_workflow.py", "EXTRACT"])

        with patch("sprite_editor.sprite_workflow.extract_sprites") as mock_extract:
            main()

        mock_extract.assert_called_once()


@pytest.mark.integration
class TestSpriteWorkflowIntegration:
    """Integration tests for sprite workflow"""

    def test_full_workflow_simulation(self, temp_files):
        """Test simulated full workflow"""
        # Step 1: Extract
        with patch("sprite_editor.sprite_workflow.run_command") as mock_run:
            mock_run.return_value = True

            extract_sprites()

        assert mock_run.call_count == 2

        # Step 2: Inject
        with patch("sprite_editor.sprite_workflow.run_command") as mock_run:
            mock_run.return_value = True

            inject_sprites(temp_files["png"])

        mock_run.assert_called_once()

    def test_workflow_with_real_file_operations(self, tmp_path):
        """Test workflow with actual file operations"""
        # Create realistic test files
        png_file = tmp_path / "edited_sprites.png"
        png_file.write_text("fake png content")

        # Test inject with real file
        with patch("sprite_editor.sprite_workflow.run_command") as mock_run:
            mock_run.return_value = True

            inject_sprites(str(png_file))

        # Verify command includes correct paths
        cmd = mock_run.call_args[0][0]
        assert str(png_file) in cmd
        assert "VRAM_edited_sprites.dmp" in cmd

    def test_error_recovery_workflow(self, temp_files):
        """Test error handling in complete workflow"""
        # Test extract with failures
        with patch("sprite_editor.sprite_workflow.run_command") as mock_run:
            mock_run.side_effect = [False, False]  # Both commands fail

            with patch("builtins.print"):
                extract_sprites()

        # Should attempt both extractions despite failures
        assert mock_run.call_count == 2

        # Test inject with missing file
        with patch("builtins.print") as mock_print:
            result = inject_sprites("/missing/file.png")

        assert result is False
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("not found" in call for call in print_calls)

    def test_command_line_integration(self, monkeypatch, temp_files):
        """Test command line argument processing"""
        test_cases = [
            (["sprite_workflow.py"], "show_help"),
            (["sprite_workflow.py", "extract"], "extract_sprites"),
            (["sprite_workflow.py", "inject", temp_files["png"]], "inject_sprites"),
            (["sprite_workflow.py", "quick", temp_files["png"]], "quick_inject"),
            (["sprite_workflow.py", "help"], "show_help"),
        ]

        for args, expected_function in test_cases:
            monkeypatch.setattr("sys.argv", args)

            with patch(
                f"sprite_editor.sprite_workflow.{expected_function}"
            ) as mock_func:
                main()

            mock_func.assert_called_once()
