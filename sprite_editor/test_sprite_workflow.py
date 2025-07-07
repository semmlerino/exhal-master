#!/usr/bin/env python3
"""
Comprehensive test suite for sprite_workflow.py CLI utility

Tests workflow automation functionality including:
- Command parsing and routing
- Extract command functionality
- Inject command functionality  
- Quick inject functionality
- Help system
- Error handling scenarios
"""

import unittest
import tempfile
import os
import sys
import subprocess
from unittest.mock import patch, MagicMock, call
from PIL import Image
import sprite_workflow


class TestSpriteWorkflowCommandParsing(unittest.TestCase):
    """Test command parsing and routing."""

    def test_extract_command(self):
        """Test extract command routing."""
        with patch.object(sys, 'argv', ['sprite_workflow.py', 'extract']):
            with patch('sprite_workflow.extract_sprites') as mock_extract:
                sprite_workflow.main()
                mock_extract.assert_called_once()

    def test_inject_command_with_file(self):
        """Test inject command routing with file argument."""
        with patch.object(sys, 'argv', ['sprite_workflow.py', 'inject', 'test.png']):
            with patch('sprite_workflow.inject_sprites') as mock_inject:
                sprite_workflow.main()
                mock_inject.assert_called_once_with('test.png')

    def test_inject_command_missing_file(self):
        """Test inject command without file argument."""
        with patch.object(sys, 'argv', ['sprite_workflow.py', 'inject']):
            with patch('builtins.print') as mock_print:
                sprite_workflow.main()
                mock_print.assert_any_call("Error: Please specify PNG file to inject")

    def test_quick_command_with_file(self):
        """Test quick command routing with file argument."""
        with patch.object(sys, 'argv', ['sprite_workflow.py', 'quick', 'test.png']):
            with patch('sprite_workflow.quick_inject') as mock_quick:
                sprite_workflow.main()
                mock_quick.assert_called_once_with('test.png')

    def test_quick_command_missing_file(self):
        """Test quick command without file argument."""
        with patch.object(sys, 'argv', ['sprite_workflow.py', 'quick']):
            with patch('builtins.print') as mock_print:
                sprite_workflow.main()
                mock_print.assert_any_call("Error: Please specify PNG file")

    def test_help_commands(self):
        """Test various help command variations."""
        help_commands = ['help', '-h', '--help']
        for cmd in help_commands:
            with patch.object(sys, 'argv', ['sprite_workflow.py', cmd]):
                with patch('sprite_workflow.show_help') as mock_help:
                    sprite_workflow.main()
                    mock_help.assert_called_once()

    def test_unknown_command(self):
        """Test handling of unknown command."""
        with patch.object(sys, 'argv', ['sprite_workflow.py', 'unknown']):
            with patch('builtins.print') as mock_print:
                with patch('sprite_workflow.show_help') as mock_help:
                    sprite_workflow.main()
                    mock_print.assert_any_call("Unknown command: unknown")
                    mock_help.assert_called_once()

    def test_no_arguments(self):
        """Test behavior when no arguments provided."""
        with patch.object(sys, 'argv', ['sprite_workflow.py']):
            with patch('sprite_workflow.show_help') as mock_help:
                sprite_workflow.main()
                mock_help.assert_called_once()


class TestSpriteWorkflowRunCommand(unittest.TestCase):
    """Test the run_command helper function."""

    @patch('subprocess.run')
    def test_run_command_success(self, mock_run):
        """Test successful command execution."""
        # Mock successful command
        mock_result = MagicMock()
        mock_result.stdout = "Success output"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Run command
        cmd = ['echo', 'test']
        with patch('builtins.print') as mock_print:
            result = sprite_workflow.run_command(cmd)

        # Verify
        self.assertTrue(result)
        mock_run.assert_called_once_with(cmd, capture_output=True, text=True)
        mock_print.assert_any_call("Running: echo test")
        mock_print.assert_any_call("Success output")

    @patch('subprocess.run')
    def test_run_command_failure(self, mock_run):
        """Test failed command execution."""
        # Mock failed command
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "Error message"
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        # Run command
        cmd = ['false']
        with patch('builtins.print') as mock_print:
            result = sprite_workflow.run_command(cmd)

        # Verify
        self.assertFalse(result)
        mock_print.assert_any_call("Error message")

    @patch('subprocess.run')
    def test_run_command_with_both_outputs(self, mock_run):
        """Test command with both stdout and stderr."""
        # Mock command with both outputs
        mock_result = MagicMock()
        mock_result.stdout = "Standard output"
        mock_result.stderr = "Standard error"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Run command
        cmd = ['test']
        with patch('builtins.print') as mock_print:
            result = sprite_workflow.run_command(cmd)

        # Verify both outputs are printed
        self.assertTrue(result)
        mock_print.assert_any_call("Standard output")
        mock_print.assert_any_call("Standard error")


class TestSpriteWorkflowExtractSprites(unittest.TestCase):
    """Test sprite extraction functionality."""

    @patch('sprite_workflow.run_command')
    def test_extract_sprites_success(self, mock_run):
        """Test successful sprite extraction."""
        # Mock successful extraction
        mock_run.return_value = True

        with patch('builtins.print') as mock_print:
            sprite_workflow.extract_sprites()

        # Should call extraction commands
        self.assertEqual(mock_run.call_count, 2)  # Main extraction + colored reference
        
        # Check the extraction command
        first_call = mock_run.call_args_list[0][0][0]
        self.assertEqual(first_call[0], 'python3')
        self.assertEqual(first_call[1], 'sprite_extractor.py')
        self.assertIn('--offset', first_call)
        self.assertIn('0xC000', first_call)

    @patch('sprite_workflow.run_command')
    def test_extract_sprites_failure(self, mock_run):
        """Test sprite extraction failure."""
        # Mock extraction failure
        mock_run.return_value = False

        with patch('builtins.print') as mock_print:
            sprite_workflow.extract_sprites()

        # Should still attempt colored reference even if main extraction fails
        self.assertEqual(mock_run.call_count, 2)


class TestSpriteWorkflowInjectSprites(unittest.TestCase):
    """Test sprite injection functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def test_inject_sprites_nonexistent_file(self):
        """Test injection with nonexistent file."""
        png_path = os.path.join(self.temp_dir, 'nonexistent.png')
        
        with patch('builtins.print') as mock_print:
            result = sprite_workflow.inject_sprites(png_path)

        # Should return False and print error
        self.assertFalse(result)
        mock_print.assert_any_call(f"Error: File '{png_path}' not found")

    @patch('sprite_workflow.run_command')
    def test_inject_sprites_success(self, mock_run):
        """Test successful sprite injection."""
        png_path = os.path.join(self.temp_dir, 'test.png')
        
        # Create test file
        img = Image.new('P', (8, 8))
        img.save(png_path)
        
        # Mock successful injection
        mock_run.return_value = True

        with patch('builtins.print') as mock_print:
            sprite_workflow.inject_sprites(png_path)

        # Should call injection command
        mock_run.assert_called_once()
        
        # Check injection command
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[0], 'python3')
        self.assertEqual(call_args[1], 'sprite_injector.py')
        self.assertEqual(call_args[2], png_path)
        self.assertIn('--preview', call_args)

    @patch('sprite_workflow.run_command')
    def test_inject_sprites_failure(self, mock_run):
        """Test sprite injection failure."""
        png_path = os.path.join(self.temp_dir, 'test.png')
        
        # Create test file
        img = Image.new('P', (8, 8))
        img.save(png_path)
        
        # Mock injection failure
        mock_run.return_value = False

        sprite_workflow.inject_sprites(png_path)

        # Should still call injection command
        mock_run.assert_called_once()

    def test_inject_sprites_output_filename_generation(self):
        """Test output filename generation."""
        png_path = os.path.join(self.temp_dir, 'my_sprites_edited.png')
        
        # Create test file
        img = Image.new('P', (8, 8))
        img.save(png_path)
        
        with patch('sprite_workflow.run_command') as mock_run:
            mock_run.return_value = True
            sprite_workflow.inject_sprites(png_path)

        # Check that output filename is generated correctly
        call_args = mock_run.call_args[0][0]
        output_arg_index = call_args.index('--output') + 1
        output_filename = call_args[output_arg_index]
        self.assertEqual(output_filename, 'VRAM_my_sprites_edited.dmp')


class TestSpriteWorkflowQuickInject(unittest.TestCase):
    """Test quick injection functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def test_quick_inject_nonexistent_file(self):
        """Test quick injection with nonexistent file."""
        png_path = os.path.join(self.temp_dir, 'nonexistent.png')
        
        with patch('builtins.print') as mock_print:
            sprite_workflow.quick_inject(png_path)

        mock_print.assert_any_call(f"Error: File '{png_path}' not found")

    @patch('subprocess.run')
    def test_quick_inject_success(self, mock_run):
        """Test successful quick injection."""
        png_path = os.path.join(self.temp_dir, 'test.png')
        
        # Create test file
        img = Image.new('P', (8, 8))
        img.save(png_path)
        
        sprite_workflow.quick_inject(png_path)

        # Should call subprocess with minimal arguments
        mock_run.assert_called_once_with(['python3', 'sprite_injector.py', png_path])


class TestSpriteWorkflowHelp(unittest.TestCase):
    """Test help system functionality."""

    def test_show_help(self):
        """Test help display."""
        with patch('builtins.print') as mock_print:
            sprite_workflow.show_help()

        # Should print help text
        mock_print.assert_called()
        
        # Check that key help content is included
        printed_text = ' '.join([str(call.args[0]) for call in mock_print.call_args_list])
        self.assertIn('Kirby Sprite Editing Workflow', printed_text)
        self.assertIn('extract', printed_text)
        self.assertIn('inject', printed_text)
        self.assertIn('quick', printed_text)


class TestSpriteWorkflowIntegration(unittest.TestCase):
    """Integration tests for complete workflow scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    @patch('sprite_workflow.run_command')
    def test_complete_extract_workflow(self, mock_run):
        """Test complete extraction workflow."""
        mock_run.return_value = True

        with patch.object(sys, 'argv', ['sprite_workflow.py', 'extract']):
            sprite_workflow.main()

        # Should call both extraction commands
        self.assertEqual(mock_run.call_count, 2)
        
        # Check both calls are to sprite_extractor.py
        first_call = mock_run.call_args_list[0][0][0]
        second_call = mock_run.call_args_list[1][0][0]
        self.assertEqual(first_call[1], 'sprite_extractor.py')
        self.assertEqual(second_call[1], 'sprite_extractor.py')

    @patch('sprite_workflow.run_command')
    def test_complete_inject_workflow(self, mock_run):
        """Test complete injection workflow."""
        png_path = os.path.join(self.temp_dir, 'edited.png')
        
        # Create test file
        img = Image.new('P', (16, 8))
        img.save(png_path)
        
        mock_run.return_value = True

        with patch.object(sys, 'argv', ['sprite_workflow.py', 'inject', png_path]):
            sprite_workflow.main()

        # Should call injection command
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args[1], 'sprite_injector.py')
        self.assertEqual(call_args[2], png_path)

    def test_subprocess_execution(self):
        """Test executing workflow as subprocess."""
        # Test help command as subprocess (safest option)
        cmd = [sys.executable, 'sprite_workflow.py', 'help']
        result = subprocess.run(cmd, 
                              cwd='/mnt/c/CustomScripts/KirbyMax/workshop/exhal-master/sprite_editor',
                              capture_output=True, text=True)
        
        # Should succeed and show help
        self.assertEqual(result.returncode, 0)
        self.assertIn('Kirby Sprite Editing Workflow', result.stdout)

    @patch('subprocess.run')
    def test_error_handling_in_commands(self, mock_subprocess):
        """Test error handling when subprocess commands fail."""
        # Mock subprocess failure
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "Command failed"
        mock_result.returncode = 1
        mock_subprocess.return_value = mock_result

        png_path = os.path.join(self.temp_dir, 'test.png')
        img = Image.new('P', (8, 8))
        img.save(png_path)

        # Test that quick inject handles command failure gracefully
        sprite_workflow.quick_inject(png_path)
        
        # Should still call subprocess (failure is handled by the called command)
        mock_subprocess.assert_called_once()


class TestSpriteWorkflowCaseSensitivity(unittest.TestCase):
    """Test case sensitivity handling in commands."""

    def test_command_case_insensitive(self):
        """Test that commands are case insensitive."""
        test_cases = [
            (['sprite_workflow.py', 'EXTRACT'], 'sprite_workflow.extract_sprites'),
            (['sprite_workflow.py', 'Extract'], 'sprite_workflow.extract_sprites'),
            (['sprite_workflow.py', 'INJECT', 'test.png'], 'sprite_workflow.inject_sprites'),
            (['sprite_workflow.py', 'Quick', 'test.png'], 'sprite_workflow.quick_inject'),
            (['sprite_workflow.py', 'HELP'], 'sprite_workflow.show_help'),
        ]

        for argv, expected_func in test_cases:
            with patch.object(sys, 'argv', argv):
                with patch(expected_func) as mock_func:
                    if 'test.png' in argv:
                        # Create temp file for commands that need it
                        temp_dir = tempfile.mkdtemp()
                        png_path = os.path.join(temp_dir, 'test.png')
                        img = Image.new('P', (8, 8))
                        img.save(png_path)
                        argv[argv.index('test.png')] = png_path
                        
                        try:
                            sprite_workflow.main()
                            mock_func.assert_called_once()
                        finally:
                            os.remove(png_path)
                            os.rmdir(temp_dir)
                    else:
                        sprite_workflow.main()
                        mock_func.assert_called_once()


if __name__ == '__main__':
    unittest.main()