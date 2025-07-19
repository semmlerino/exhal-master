"""
HAL compression/decompression module for SpritePal.
Interfaces with exhal/inhal C tools for ROM sprite injection.
"""

import builtins
import contextlib
import os
import re
import shutil
import subprocess
import tempfile
from typing import Optional

from spritepal.utils.constants import DATA_SIZE


class HALCompressionError(Exception):
    """Raised when HAL compression/decompression fails"""


class HALCompressor:
    """Handles HAL compression/decompression for ROM injection"""

    def __init__(self, exhal_path: Optional[str] = None, inhal_path: Optional[str] = None):
        """
        Initialize HAL compressor.

        Args:
            exhal_path: Path to exhal executable (decompressor)
            inhal_path: Path to inhal executable (compressor)
        """
        # Try to find tools in various locations
        self.exhal_path = self._find_tool("exhal", exhal_path)
        self.inhal_path = self._find_tool("inhal", inhal_path)

    def _find_tool(self, tool_name: str, provided_path: Optional[str] = None) -> str:
        """Find HAL compression tool executable"""
        if provided_path and os.path.isfile(provided_path):
            return provided_path

        # Platform-specific executable suffix
        import platform
        exe_suffix = ".exe" if platform.system() == "Windows" else ""
        tool_with_suffix = f"{tool_name}{exe_suffix}"
        
        # Search locations
        search_paths = [
            # Compiled tools directory (preferred)
            f"tools/{tool_with_suffix}",
            f"./tools/{tool_with_suffix}",
            # Current directory
            tool_with_suffix,
            f"./{tool_with_suffix}",
            # Archive directory (from codebase structure)
            f"../archive/obsolete_test_images/ultrathink/{tool_name}",
            f"../archive/obsolete_test_images/ultrathink/{tool_with_suffix}",
            # Parent directories
            f"../{tool_name}",
            f"../../{tool_name}",
            # System PATH
            tool_name
        ]

        for path in search_paths:
            full_path = os.path.abspath(path)
            if os.path.isfile(full_path):
                return full_path

        raise HALCompressionError(f"Could not find {tool_name} executable. "
                                f"Please run 'python compile_hal_tools.py' to build for your platform.")

    def decompress_from_rom(self, rom_path: str, offset: int, output_path: Optional[str] = None) -> bytes:
        """
        Decompress data from ROM at specified offset.

        Args:
            rom_path: Path to ROM file
            offset: Offset in ROM where compressed data starts
            output_path: Optional path to save decompressed data

        Returns:
            Decompressed data as bytes
        """
        # Create temporary output file if not specified
        if output_path is None:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                output_path = tmp.name

        try:
            # Run exhal: exhal romfile offset outfile
            cmd = [self.exhal_path, rom_path, f"0x{offset:X}", output_path]
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)

            if result.returncode != 0:
                raise HALCompressionError(f"Decompression failed: {result.stderr}")

            # Read decompressed data
            with open(output_path, "rb") as f:
                return f.read()


        finally:
            # Clean up temp file if we created one
            if output_path and output_path.startswith(tempfile.gettempdir()):
                with contextlib.suppress(builtins.BaseException):
                    os.unlink(output_path)

    def compress_to_file(self, input_data: bytes, output_path: str, fast: bool = False) -> int:
        """
        Compress data to a file.

        Args:
            input_data: Data to compress
            output_path: Path to save compressed data
            fast: Use fast compression mode

        Returns:
            Size of compressed data
        """
        # Check size limit
        if len(input_data) > DATA_SIZE:
            raise HALCompressionError(f"Input data too large: {len(input_data)} bytes (max {DATA_SIZE})")

        # Write input to temp file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(input_data)
            tmp_path = tmp.name

        try:
            # Run inhal: inhal [-fast] -n infile outfile
            cmd = [self.inhal_path]
            if fast:
                cmd.append("-fast")
            cmd.extend(["-n", tmp_path, output_path])

            result = subprocess.run(cmd, check=False, capture_output=True, text=True)

            if result.returncode != 0:
                raise HALCompressionError(f"Compression failed: {result.stderr}")

            # Get compressed size
            return os.path.getsize(output_path)

        finally:
            # Clean up temp file
            with contextlib.suppress(builtins.BaseException):
                os.unlink(tmp_path)

    def compress_to_rom(self, input_data: bytes, rom_path: str, offset: int,
                       output_rom_path: Optional[str] = None, fast: bool = False) -> tuple[bool, str]:
        """
        Compress data and inject into ROM at specified offset.

        Args:
            input_data: Data to compress and inject
            rom_path: Path to input ROM file
            offset: Offset in ROM to inject compressed data
            output_rom_path: Path for output ROM (if None, modifies in place)
            fast: Use fast compression mode

        Returns:
            Tuple of (success, message)
        """
        # Check size limit
        if len(input_data) > DATA_SIZE:
            return False, f"Input data too large: {len(input_data)} bytes (max {DATA_SIZE})"

        # If no output path, modify in place
        if output_rom_path is None:
            output_rom_path = rom_path
        else:
            # Copy ROM to output path first
            shutil.copy2(rom_path, output_rom_path)

        # Write input to temp file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(input_data)
            tmp_path = tmp.name

        try:
            # Run inhal: inhal [-fast] infile romfile offset
            cmd = [self.inhal_path]
            if fast:
                cmd.append("-fast")
            cmd.extend([tmp_path, output_rom_path, f"0x{offset:X}"])

            result = subprocess.run(cmd, check=False, capture_output=True, text=True)

            if result.returncode != 0:
                return False, f"ROM injection failed: {result.stderr}"

            # Extract size info from output if available
            compressed_size = "unknown"
            if "bytes" in result.stdout:
                # Try to parse compressed size from output
                match = re.search(r"(\d+)\s+bytes", result.stdout)
                if match:
                    compressed_size = match.group(1)

            return True, f"Successfully injected compressed data ({compressed_size} bytes) at offset 0x{offset:X}"

        finally:
            # Clean up temp file
            with contextlib.suppress(builtins.BaseException):
                os.unlink(tmp_path)

    def test_tools(self) -> tuple[bool, str]:
        """Test if HAL compression tools are available and working"""
        import platform
        
        try:
            # Test exhal
            result = subprocess.run([self.exhal_path], check=False, capture_output=True, text=True)
            # Check both stdout and stderr for tool output
            output = (result.stdout + result.stderr).lower()
            if "exhal" not in output and "usage" not in output:
                return False, "exhal tool not working correctly"

            # Test inhal
            result = subprocess.run([self.inhal_path], check=False, capture_output=True, text=True)
            # Check both stdout and stderr for tool output
            output = (result.stdout + result.stderr).lower()
            if "inhal" not in output and "usage" not in output:
                return False, "inhal tool not working correctly"

            return True, "HAL compression tools are working correctly"

        except FileNotFoundError:
            return False, f"HAL tools not found. Please run 'python compile_hal_tools.py' to build for {platform.system()}"
        except OSError as e:
            if platform.system() == "Windows" and e.winerror == 193:
                return False, f"Wrong platform binaries. Please run 'python compile_hal_tools.py' to build for Windows"
            return False, f"Error testing tools: {e!s}"
        except Exception as e:
            return False, f"Error testing tools: {e!s}"
