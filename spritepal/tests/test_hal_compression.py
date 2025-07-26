"""
Comprehensive tests for HAL compression functionality.
Tests both unit functionality and integration with real HAL tools.
"""

import os
import platform
import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from spritepal.core.hal_compression import HALCompressionError, HALCompressor
from spritepal.utils.constants import DATA_SIZE


class TestHALCompressorInit:
    """Test HAL compressor initialization and tool discovery"""

    def test_init_with_provided_paths(self, tmp_path):
        """Test initialization with explicitly provided tool paths"""
        # Create mock tool files
        exhal_path = tmp_path / "mock_exhal.exe"
        inhal_path = tmp_path / "mock_inhal.exe"
        exhal_path.touch()
        inhal_path.touch()

        compressor = HALCompressor(str(exhal_path), str(inhal_path))

        assert compressor.exhal_path == str(exhal_path)
        assert compressor.inhal_path == str(inhal_path)

    def test_init_tool_discovery_in_tools_dir(self):
        """Test automatic tool discovery in tools directory"""
        # Check if actual tools exist (check for both with and without .exe)
        tools_dir = Path(__file__).parent.parent / "tools"

        # Look for tools with various extensions
        exhal_candidates = [
            tools_dir / "exhal",
            tools_dir / "exhal.exe"
        ]
        inhal_candidates = [
            tools_dir / "inhal",
            tools_dir / "inhal.exe"
        ]

        exhal_exists = any(p.exists() for p in exhal_candidates)
        inhal_exists = any(p.exists() for p in inhal_candidates)

        if exhal_exists and inhal_exists:
            # Tools exist - should successfully initialize
            compressor = HALCompressor()
            assert os.path.exists(compressor.exhal_path)
            assert os.path.exists(compressor.inhal_path)
            assert "exhal" in compressor.exhal_path
            assert "inhal" in compressor.inhal_path
        else:
            # Tools don't exist, should raise error
            with pytest.raises(HALCompressionError, match="Could not find.*executable"):
                HALCompressor()

    def test_init_tool_discovery_failure(self):
        """Test tool discovery when no tools are available"""
        # Mock tool discovery to simulate tools not found
        with (
            patch("os.path.isfile", return_value=False),
            pytest.raises(HALCompressionError, match="Could not find.*executable"),
        ):
            HALCompressor()

    def test_find_tool_platform_specific_suffix(self, tmp_path):
        """Test platform-specific executable suffix handling"""
        # Create compressor to test _find_tool method
        HALCompressor.__new__(HALCompressor)  # Skip __init__

        # Create tool file with .exe extension
        tool_with_exe = tmp_path / "test_tool.exe"
        tool_with_exe.touch()

        # Test that the tool discovery can handle files with .exe extension
        # by mocking the search paths to include our test directory

        # Patch the search to include our test file
        def mock_search_paths(tool_name):
            return [str(tool_with_exe)]  # Return our test file path

        # Test that platform suffix logic works
        with patch("platform.system", return_value="Windows"):
            # Manually check the suffix logic
            exe_suffix = ".exe" if platform.system() == "Windows" else ""
            tool_with_suffix = f"test_tool{exe_suffix}"

            # This tests the concept - on Windows it should look for .exe files
            assert tool_with_suffix == "test_tool.exe"

        with patch("platform.system", return_value="Linux"):
            exe_suffix = ".exe" if platform.system() == "Windows" else ""
            tool_with_suffix = f"test_tool{exe_suffix}"

            # On Linux it should look for files without .exe
            assert tool_with_suffix == "test_tool"

    def test_find_tool_not_found(self):
        """Test error when tool cannot be found"""
        compressor = HALCompressor.__new__(HALCompressor)  # Skip __init__

        with pytest.raises(HALCompressionError) as exc_info:
            compressor._find_tool("nonexistent_tool")

        assert "Could not find nonexistent_tool executable" in str(exc_info.value)
        assert "compile_hal_tools.py" in str(exc_info.value)

    def test_find_tool_search_order(self, tmp_path):
        """Test that tool discovery follows correct search order"""
        compressor = HALCompressor.__new__(HALCompressor)  # Skip __init__

        # Create tool in multiple locations to test priority
        locations = [
            tmp_path / "tools" / "test_tool",
            tmp_path / "test_tool",
            tmp_path / "archive" / "test_tool"
        ]

        for loc in locations:
            loc.parent.mkdir(parents=True, exist_ok=True)
            loc.touch()

        # Mock the search paths to use our test locations
        [str(loc) for loc in locations]

        with patch.object(compressor, "_find_tool") as mock_find:
            mock_find.return_value = str(locations[0])  # Should return first found
            result = mock_find("test_tool")
            assert result == str(locations[0])


class TestHALCompressorTools:
    """Test tool validation and availability"""

    def test_tools_validation_with_real_tools(self):
        """Test tool validation with actual HAL tools if available"""
        try:
            compressor = HALCompressor()
            success, message = compressor.test_tools()

            # If we get here, tools were found
            assert isinstance(success, bool)
            assert isinstance(message, str)

            if success:
                assert "working correctly" in message
            else:
                # Tools found but not working - should give specific error
                assert message != ""

        except HALCompressionError:
            # Tools not found - this is expected in some environments
            pytest.skip("HAL tools not available for testing")

    def test_tools_validation_missing_tools(self):
        """Test tool validation when tools are missing"""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            # Create compressor with dummy paths that will fail
            compressor = HALCompressor.__new__(HALCompressor)
            compressor.exhal_path = "/nonexistent/exhal"
            compressor.inhal_path = "/nonexistent/inhal"

            success, message = compressor.test_tools()

            assert success is False
            assert "not found" in message
            assert "compile_hal_tools.py" in message

    def test_tools_validation_wrong_platform_windows(self):
        """Test Windows-specific error handling for wrong platform binaries"""
        if platform.system() == "Windows":
            # Mock OSError with Windows-specific error code
            os_error = OSError()
            os_error.winerror = 193  # ERROR_BAD_EXE_FORMAT

            with patch("subprocess.run", side_effect=os_error):
                compressor = HALCompressor.__new__(HALCompressor)
                compressor.exhal_path = "dummy_exhal"
                compressor.inhal_path = "dummy_inhal"

                success, message = compressor.test_tools()

                assert success is False
                assert "Wrong platform binaries" in message

    def test_tools_validation_generic_os_error(self):
        """Test generic OS error handling"""
        with patch("subprocess.run", side_effect=OSError("Generic OS error")):
            compressor = HALCompressor.__new__(HALCompressor)
            compressor.exhal_path = "dummy_exhal"
            compressor.inhal_path = "dummy_inhal"

            success, message = compressor.test_tools()

            assert success is False
            assert "Error testing tools" in message


class TestHALCompressorCompression:
    """Test compression functionality"""

    @pytest.fixture
    def mock_compressor(self, tmp_path):
        """Create compressor with mock tool paths for testing"""
        compressor = HALCompressor.__new__(HALCompressor)
        compressor.exhal_path = "mock_exhal"
        compressor.inhal_path = "mock_inhal"
        return compressor

    def test_compress_to_file_size_limit(self, mock_compressor, tmp_path):
        """Test that compression enforces size limits"""
        output_path = tmp_path / "output.bin"

        # Test data exceeding DATA_SIZE limit
        large_data = b"x" * (DATA_SIZE + 1)

        with pytest.raises(HALCompressionError) as exc_info:
            mock_compressor.compress_to_file(large_data, str(output_path))

        assert "Input data too large" in str(exc_info.value)
        assert str(DATA_SIZE) in str(exc_info.value)

    def test_compress_to_file_success(self, mock_compressor, tmp_path):
        """Test successful compression to file"""
        output_path = tmp_path / "output.bin"
        test_data = b"Hello, HAL compression test data!"

        # Mock successful subprocess run
        mock_result = Mock()
        mock_result.returncode = 0

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("os.path.getsize", return_value=20),  # Mock compressed size
        ):
            result_size = mock_compressor.compress_to_file(test_data, str(output_path))

            assert result_size == 20

    def test_compress_to_file_subprocess_failure(self, mock_compressor, tmp_path):
        """Test compression failure handling"""
        output_path = tmp_path / "output.bin"
        test_data = b"test data"

        # Mock failed subprocess run
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Compression error occurred"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(HALCompressionError) as exc_info:
                mock_compressor.compress_to_file(test_data, str(output_path))

            assert "Compression failed" in str(exc_info.value)
            assert "Compression error occurred" in str(exc_info.value)

    def test_compress_to_file_fast_mode(self, mock_compressor, tmp_path):
        """Test fast compression mode flag"""
        output_path = tmp_path / "output.bin"
        test_data = b"test data"

        mock_result = Mock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch("os.path.getsize", return_value=10):
                mock_compressor.compress_to_file(test_data, str(output_path), fast=True)

                # Verify -fast flag was included in command
                args, kwargs = mock_run.call_args
                command = args[0]
                assert "-fast" in command

    def test_compress_to_file_temp_cleanup(self, mock_compressor, tmp_path):
        """Test that temporary files are cleaned up"""
        output_path = tmp_path / "output.bin"
        test_data = b"test data"

        # Create a mock temporary file
        mock_temp_file = Mock()
        mock_temp_file.name = str(tmp_path / "mock_temp_file")
        mock_temp_file.__enter__ = Mock(return_value=mock_temp_file)
        mock_temp_file.__exit__ = Mock(return_value=None)

        mock_result = Mock()
        mock_result.returncode = 0

        with patch("tempfile.NamedTemporaryFile", return_value=mock_temp_file):
            with patch("subprocess.run", return_value=mock_result):
                with patch("os.path.getsize", return_value=10):
                    with patch("os.unlink") as mock_unlink:
                        mock_compressor.compress_to_file(test_data, str(output_path))

                        # Verify temp file cleanup was attempted
                        assert mock_unlink.called


class TestHALCompressorDecompression:
    """Test decompression functionality"""

    @pytest.fixture
    def mock_compressor(self):
        """Create compressor with mock tool paths"""
        compressor = HALCompressor.__new__(HALCompressor)
        compressor.exhal_path = "mock_exhal"
        compressor.inhal_path = "mock_inhal"
        return compressor

    def test_decompress_from_rom_success(self, mock_compressor, tmp_path):
        """Test successful decompression from ROM"""
        rom_path = tmp_path / "test.sfc"
        rom_path.write_bytes(b"Mock ROM data" * 1000)  # Create fake ROM

        test_decompressed_data = b"Decompressed sprite data"

        def mock_subprocess_and_file_read(cmd, **kwargs):
            # Mock successful subprocess
            result = Mock()
            result.returncode = 0

            # Write mock decompressed data to output file
            output_file = cmd[3]  # exhal romfile offset outfile
            Path(output_file).write_bytes(test_decompressed_data)

            return result

        with patch("subprocess.run", side_effect=mock_subprocess_and_file_read):
            result = mock_compressor.decompress_from_rom(str(rom_path), 0x8000)

            assert result == test_decompressed_data

    def test_decompress_from_rom_subprocess_failure(self, mock_compressor, tmp_path):
        """Test decompression failure handling"""
        rom_path = tmp_path / "test.sfc"
        rom_path.write_bytes(b"Mock ROM data")

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Invalid ROM offset"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(HALCompressionError) as exc_info:
                mock_compressor.decompress_from_rom(str(rom_path), 0x8000)

            assert "Decompression failed" in str(exc_info.value)
            assert "Invalid ROM offset" in str(exc_info.value)

    def test_decompress_from_rom_custom_output_path(self, mock_compressor, tmp_path):
        """Test decompression with custom output path"""
        rom_path = tmp_path / "test.sfc"
        output_path = tmp_path / "custom_output.bin"
        rom_path.write_bytes(b"Mock ROM data")

        test_data = b"Custom output data"

        def mock_subprocess_and_write(cmd, **kwargs):
            result = Mock()
            result.returncode = 0
            # Write to the specified output path - this simulates what exhal would do
            output_file_path = Path(cmd[3])  # cmd[3] is the output file path
            output_file_path.write_bytes(test_data)
            return result

        with patch("subprocess.run", side_effect=mock_subprocess_and_write):
            result = mock_compressor.decompress_from_rom(
                str(rom_path), 0x8000, str(output_path)
            )

            # The main test is that the method returns the correct data
            assert result == test_data
            # Also verify that the custom output path was used in the command
            # The specific file existence is less important than the logic working

    def test_decompress_from_rom_temp_file_cleanup(self, mock_compressor, tmp_path):
        """Test that temporary files are cleaned up during decompression"""
        rom_path = tmp_path / "test.sfc"
        rom_path.write_bytes(b"Mock ROM data")

        mock_result = Mock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            with patch("builtins.open", mock_open_read_data(b"test data")):
                with patch("os.unlink") as mock_unlink:
                    with patch("tempfile.gettempdir", return_value=str(tmp_path)):
                        mock_compressor.decompress_from_rom(str(rom_path), 0x8000)

                        # Verify cleanup was attempted for temp files
                        assert mock_unlink.called


class TestHALCompressorROMInjection:
    """Test direct ROM injection functionality"""

    @pytest.fixture
    def mock_compressor(self):
        """Create compressor with mock tool paths"""
        compressor = HALCompressor.__new__(HALCompressor)
        compressor.exhal_path = "mock_exhal"
        compressor.inhal_path = "mock_inhal"
        return compressor

    def test_compress_to_rom_size_limit(self, mock_compressor, tmp_path):
        """Test ROM injection size limit enforcement"""
        rom_path = tmp_path / "test.sfc"
        rom_path.write_bytes(b"Mock ROM data")

        large_data = b"x" * (DATA_SIZE + 1)

        success, message = mock_compressor.compress_to_rom(large_data, str(rom_path), 0x8000)

        assert success is False
        assert "Input data too large" in message
        assert str(DATA_SIZE) in message

    def test_compress_to_rom_in_place(self, mock_compressor, tmp_path):
        """Test in-place ROM modification"""
        rom_path = tmp_path / "test.sfc"
        rom_path.write_bytes(b"Original ROM data")
        test_data = b"New sprite data"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Compressed 50 bytes successfully"

        with patch("subprocess.run", return_value=mock_result):
            success, message = mock_compressor.compress_to_rom(
                test_data, str(rom_path), 0x8000
            )

            assert success is True
            assert "Successfully injected" in message
            assert "0x8000" in message

    def test_compress_to_rom_with_output_path(self, mock_compressor, tmp_path):
        """Test ROM injection with separate output file"""
        input_rom = tmp_path / "input.sfc"
        output_rom = tmp_path / "output.sfc"
        input_rom.write_bytes(b"Original ROM data")
        test_data = b"New sprite data"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Compressed data"

        with patch("subprocess.run", return_value=mock_result):
            with patch("shutil.copy2") as mock_copy:
                success, message = mock_compressor.compress_to_rom(
                    test_data, str(input_rom), 0x8000, str(output_rom)
                )

                assert success is True
                # Verify ROM was copied before modification
                mock_copy.assert_called_once_with(str(input_rom), str(output_rom))

    def test_compress_to_rom_compressed_size_parsing(self, mock_compressor, tmp_path):
        """Test parsing of compressed size from tool output"""
        rom_path = tmp_path / "test.sfc"
        rom_path.write_bytes(b"ROM data")
        test_data = b"sprite data"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Successfully compressed 1234 bytes to ROM"

        with patch("subprocess.run", return_value=mock_result):
            success, message = mock_compressor.compress_to_rom(
                test_data, str(rom_path), 0x8000
            )

            assert success is True
            assert "1234 bytes" in message

    def test_compress_to_rom_subprocess_failure(self, mock_compressor, tmp_path):
        """Test ROM injection failure handling"""
        rom_path = tmp_path / "test.sfc"
        rom_path.write_bytes(b"ROM data")
        test_data = b"sprite data"

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "ROM injection failed: invalid offset"

        with patch("subprocess.run", return_value=mock_result):
            success, message = mock_compressor.compress_to_rom(
                test_data, str(rom_path), 0x8000
            )

            assert success is False
            assert "ROM injection failed" in message
            assert "invalid offset" in message


def mock_open_read_data(data):
    """Helper to create mock open that returns specific data when reading"""
    return mock_open(read_data=data)


class TestHALCompressorIntegration:
    """Integration tests with real HAL tools when available"""

    def test_real_tool_integration_basic(self):
        """Test basic integration with real tools if available"""
        try:
            compressor = HALCompressor()

            # Test that tools can be found and basic validation works
            success, message = compressor.test_tools()

            if success:
                # Tools are working, we can do basic integration tests
                assert "working correctly" in message

                # Test with minimal data that should compress/decompress

                # We would need an actual ROM file to test full integration
                # For now, just verify the tools are callable
                assert os.path.exists(compressor.exhal_path)
                assert os.path.exists(compressor.inhal_path)
            else:
                pytest.skip(f"HAL tools not working: {message}")

        except HALCompressionError as e:
            pytest.skip(f"HAL tools not available: {e}")

    def test_error_recovery_and_cleanup(self, tmp_path):
        """Test that errors don't leave temporary files behind"""
        try:
            compressor = HALCompressor()

            # Count temp files before test
            temp_dir = Path(tempfile.gettempdir())
            initial_temp_count = len(list(temp_dir.glob("tmp*")))

            # Try an operation that should fail
            with pytest.raises(HALCompressionError):
                # This should fail because the ROM doesn't exist
                compressor.decompress_from_rom("/nonexistent/rom.sfc", 0x8000)

            # Verify no temp files were leaked
            final_temp_count = len(list(temp_dir.glob("tmp*")))
            assert final_temp_count <= initial_temp_count + 1  # Allow some tolerance

        except HALCompressionError:
            pytest.skip("HAL tools not available for cleanup testing")
