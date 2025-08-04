"""
HAL compression/decompression module for SpritePal.
Interfaces with exhal/inhal C tools for ROM sprite injection.
"""

import builtins
import contextlib
import os
import platform
import re
import shutil
import subprocess
import tempfile

from utils.constants import DATA_SIZE
from utils.logging_config import get_logger

logger = get_logger(__name__)


class HALCompressionError(Exception):
    """Raised when HAL compression/decompression fails"""


class HALCompressor:
    """Handles HAL compression/decompression for ROM injection"""

    def __init__(
        self, exhal_path: str | None = None, inhal_path: str | None = None
    ):
        """
        Initialize HAL compressor.

        Args:
            exhal_path: Path to exhal executable (decompressor)
            inhal_path: Path to inhal executable (compressor)
        """
        logger.info("Initializing HAL compressor")
        # Try to find tools in various locations
        self.exhal_path: str = self._find_tool("exhal", exhal_path)
        self.inhal_path: str = self._find_tool("inhal", inhal_path)
        logger.info(f"HAL compressor initialized with exhal={self.exhal_path}, inhal={self.inhal_path}")

    def _find_tool(self, tool_name: str, provided_path: str | None = None) -> str:
        """Find HAL compression tool executable"""
        logger.info(f"Searching for {tool_name} tool")

        if provided_path:
            logger.debug(f"Checking provided path: {provided_path}")
            if os.path.isfile(provided_path):
                logger.info(f"Using provided {tool_name} at: {provided_path}")
                return provided_path
            logger.warning(f"Provided path does not exist: {provided_path}")

        # Platform-specific executable suffix
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
            tool_name,
        ]

        logger.debug(f"Searching {len(search_paths)} locations for {tool_name}")
        for i, path in enumerate(search_paths, 1):
            full_path = os.path.abspath(path)
            if os.path.isfile(full_path):
                logger.info(f"Found {tool_name} at location {i}/{len(search_paths)}: {full_path}")
                # Check if file is executable
                if not os.access(full_path, os.X_OK):
                    logger.warning(f"Found {tool_name} but it may not be executable: {full_path}")
                return full_path
            logger.debug(f"Location {i}/{len(search_paths)}: Not found at {full_path}")

        logger.error(f"Could not find {tool_name} executable in any search path")
        raise HALCompressionError(
            f"Could not find {tool_name} executable. "
            f"Please run 'python compile_hal_tools.py' to build for your platform."
        )

    def decompress_from_rom(
        self, rom_path: str, offset: int, output_path: str | None = None
    ) -> bytes:
        """
        Decompress data from ROM at specified offset.

        Args:
            rom_path: Path to ROM file
            offset: Offset in ROM where compressed data starts
            output_path: path to save decompressed data

        Returns:
            Decompressed data as bytes
        """
        logger.info(f"Decompressing from ROM: {rom_path} at offset 0x{offset:X}")
        # Create temporary output file if not specified
        if output_path is None:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                output_path = tmp.name

        try:
            # Run exhal: exhal romfile offset outfile
            cmd = [self.exhal_path, rom_path, f"0x{offset:X}", output_path]
            logger.debug(f"Running command: {' '.join(cmd)}")

            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            logger.debug(f"Command completed with return code: {result.returncode}")

            if result.stdout:
                logger.debug(f"stdout: {result.stdout.strip()}")
            if result.stderr:
                logger.debug(f"stderr: {result.stderr.strip()}")

            if result.returncode != 0:
                logger.error(f"Decompression failed with return code {result.returncode}")
                raise HALCompressionError(f"Decompression failed: {result.stderr}")

            # Read decompressed data
            with open(output_path, "rb") as f:
                data = f.read()

            logger.info(f"Successfully decompressed {len(data)} bytes from ROM offset 0x{offset:X}")
            return data

        finally:
            # Clean up temp file if we created one
            if output_path and output_path.startswith(tempfile.gettempdir()):
                with contextlib.suppress(builtins.BaseException):
                    os.unlink(output_path)

    def compress_to_file(
        self, input_data: bytes, output_path: str, fast: bool = False
    ) -> int:
        """
        Compress data to a file.

        Args:
            input_data: Data to compress
            output_path: Path to save compressed data
            fast: Use fast compression mode

        Returns:
            Size of compressed data
        """
        logger.info(f"Compressing {len(input_data)} bytes to file: {output_path}")

        # Check size limit
        if len(input_data) > DATA_SIZE:
            logger.error(f"Input data too large: {len(input_data)} bytes (max {DATA_SIZE})")
            raise HALCompressionError(
                f"Input data too large: {len(input_data)} bytes (max {DATA_SIZE})"
            )

        # Write input to temp file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(input_data)
            tmp_path = tmp.name

        try:
            # Run inhal: inhal [-fast] -n infile outfile
            cmd = [self.inhal_path]
            if fast:
                cmd.append("-fast")
                logger.debug("Using fast compression mode")
            cmd.extend(["-n", tmp_path, output_path])

            logger.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            logger.debug(f"Command completed with return code: {result.returncode}")

            if result.stdout:
                logger.debug(f"stdout: {result.stdout.strip()}")
            if result.stderr:
                logger.debug(f"stderr: {result.stderr.strip()}")

            if result.returncode != 0:
                logger.error(f"Compression failed with return code {result.returncode}: {result.stderr}")
                raise HALCompressionError(f"Compression failed: {result.stderr}")

            # Get compressed size
            compressed_size = os.path.getsize(output_path)
            compression_ratio = (len(input_data) - compressed_size) / len(input_data) * 100
            logger.info(f"Compressed to {compressed_size} bytes ({compression_ratio:.1f}% reduction)")
            return compressed_size

        finally:
            # Clean up temp file
            with contextlib.suppress(builtins.BaseException):
                os.unlink(tmp_path)

    def compress_to_rom(
        self,
        input_data: bytes,
        rom_path: str,
        offset: int,
        output_rom_path: str | None = None,
        fast: bool = False
    ) -> tuple[bool, str]:
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
        logger.info(f"Compressing {len(input_data)} bytes to ROM: {rom_path} at offset 0x{offset:X}")

        # Check size limit
        if len(input_data) > DATA_SIZE:
            logger.error(f"Input data too large: {len(input_data)} bytes (max {DATA_SIZE})")
            return (
                False,
                f"Input data too large: {len(input_data)} bytes (max {DATA_SIZE})"
            )

        # If no output path, modify in place
        if output_rom_path is None:
            output_rom_path = rom_path
            logger.debug("Modifying ROM in place")
        else:
            # Copy ROM to output path first
            logger.debug(f"Copying ROM to output path: {output_rom_path}")
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
                logger.debug("Using fast compression mode")
            cmd.extend([tmp_path, output_rom_path, f"0x{offset:X}"])

            logger.debug(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            logger.debug(f"Command completed with return code: {result.returncode}")

            if result.stdout:
                logger.debug(f"stdout: {result.stdout.strip()}")
            if result.stderr:
                logger.debug(f"stderr: {result.stderr.strip()}")

            if result.returncode != 0:
                logger.error(f"ROM injection failed with return code {result.returncode}")
                return False, f"ROM injection failed: {result.stderr}"

            # Extract size info from output if available
            compressed_size = "unknown"
            if "bytes" in result.stdout:
                # Try to parse compressed size from output
                match = re.search(r"(\d+)\s+bytes", result.stdout)
                if match:
                    compressed_size = match.group(1)

            logger.info(f"Successfully injected compressed data ({compressed_size} bytes) at offset 0x{offset:X}")
            return (
                True,
                f"Successfully injected compressed data ({compressed_size} bytes) at offset 0x{offset:X}"
            )

        finally:
            # Clean up temp file
            with contextlib.suppress(builtins.BaseException):
                os.unlink(tmp_path)

    def test_tools(self) -> tuple[bool, str]:
        """Test if HAL compression tools are available and working"""
        logger.info("Testing HAL compression tools")

        def _test_tool(tool_path: str, tool_name: str) -> str | None:
            """Helper to test a single HAL tool. Returns error message or None if success."""
            logger.debug(f"Testing {tool_name} at: {tool_path}")
            result = subprocess.run(
                [tool_path], check=False, capture_output=True, text=True
            )
            # Check both stdout and stderr for tool output
            output = (result.stdout + result.stderr).lower()
            if tool_name.lower() not in output and "usage" not in output:
                logger.error(f"{tool_name} tool not working correctly. Output: {output[:100]}")
                return f"{tool_name} tool not working correctly"
            return None

        try:
            # Test both tools
            error_msg = _test_tool(self.exhal_path, "exhal")
            if error_msg:
                return False, error_msg

            error_msg = _test_tool(self.inhal_path, "inhal")
            if error_msg:
                return False, error_msg

        except FileNotFoundError:
            logger.exception("HAL tools not found")
            error_msg = f"HAL tools not found. Please run 'python compile_hal_tools.py' to build for {platform.system()}"
        except OSError as e:
            logger.exception("OS error testing tools")
            if platform.system() == "Windows" and hasattr(e, "winerror") and getattr(e, "winerror", None) == 193:
                error_msg = "Wrong platform binaries. Please run 'python compile_hal_tools.py' to build for Windows"
            else:
                error_msg = f"Error testing tools: {e!s}"
        except subprocess.SubprocessError as e:
            logger.exception("Subprocess error testing tools")
            error_msg = f"Error running tools: {e!s}"
        except ValueError as e:
            logger.exception("Value error testing tools")
            error_msg = f"Invalid tool configuration: {e!s}"
        else:
            logger.info("HAL compression tools are working correctly")
            return True, "HAL compression tools are working correctly"

        return False, error_msg
