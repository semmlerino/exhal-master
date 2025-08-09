"""
File handling utilities for SpritePal tests.

This module provides functions for creating, managing, and cleaning up
test files and directories, reducing duplication across test files.
"""

import shutil
import tempfile
from pathlib import Path

from .data_generators import generate_cgram_data, generate_oam_data


def create_temp_directory(prefix: str = "spritepal_test_") -> str:
    """
    Create a temporary directory for testing.

    Args:
        prefix: Prefix for the directory name

    Returns:
        Path to the created temporary directory
    """
    return tempfile.mkdtemp(prefix=prefix)


def create_test_files(
    base_path: str,
    file_types: list[str],
    **kwargs
) -> dict[str, str]:
    """
    Create a set of test files in the specified directory.

    Args:
        base_path: Base directory path
        file_types: List of file types to create ("vram", "cgram", "oam", "rom")
        **kwargs: Additional parameters for data generation

    Returns:
        Dictionary mapping file types to their paths
    """
    base_path_obj = Path(base_path)
    base_path_obj.mkdir(parents=True, exist_ok=True)

    file_paths = {}

    for file_type in file_types:
        if file_type == "vram":
            data = _generate_vram_data(**kwargs)
            filename = base_path_obj / "test_vram.dmp"

        elif file_type == "cgram":
            data = generate_cgram_data(kwargs.get("palette_count", 16))
            filename = base_path_obj / "test_cgram.dmp"

        elif file_type == "oam":
            data = generate_oam_data(kwargs.get("oam_entries", 128))
            filename = base_path_obj / "test_oam.dmp"

        elif file_type == "rom":
            data = _generate_rom_data(**kwargs)
            filename = base_path_obj / "test_rom.sfc"

        elif file_type == "png":
            # Create a test PNG image
            from .data_generators import create_test_image

            img = create_test_image(
                kwargs.get("width", 128),
                kwargs.get("height", 128),
                kwargs.get("mode", "L"),
                kwargs.get("pattern", "gradient")
            )
            filename = base_path_obj / "test_sprite.png"
            img.save(filename)
            file_paths[file_type] = str(filename)
            continue

        elif file_type == "palette":
            # Create a test palette JSON file
            import json

            from .data_generators import generate_palette_data

            palettes = generate_palette_data(
                kwargs.get("palette_count", 1),
                kwargs.get("colors_per_palette", 16),
                kwargs.get("style", "varied")
            )

            filename = base_path_obj / "test_palette.pal.json"
            with open(filename, "w") as f:
                json.dump(palettes[0], f)  # Save first palette

            file_paths[file_type] = str(filename)
            continue

        elif file_type == "metadata":
            # Create a test metadata JSON file
            import json

            metadata = {
                "width": kwargs.get("width", 128),
                "height": kwargs.get("height", 128),
                "palette_count": kwargs.get("palette_count", 16),
                "format": "4bpp",
                "sprite_name": kwargs.get("sprite_name", "test_sprite"),
                "palettes": {
                    str(i): f"test_sprite_pal{i}.pal.json"
                    for i in range(8, 16)
                }
            }

            filename = base_path_obj / "test_sprite.metadata.json"
            with open(filename, "w") as f:
                json.dump(metadata, f, indent=2)

            file_paths[file_type] = str(filename)
            continue

        else:
            raise ValueError(f"Unknown file type: {file_type}")

        # Write binary data files
        with open(filename, "wb") as f:
            f.write(data)

        file_paths[file_type] = str(filename)

    return file_paths


def _generate_vram_data(**kwargs) -> bytearray:
    """Generate VRAM data with sprite data at the correct offset."""
    from utils.constants import BYTES_PER_TILE, VRAM_SPRITE_OFFSET

    vram_size = kwargs.get("vram_size", 0x10000)  # 64KB
    data = bytearray(vram_size)

    # Add sprite data at VRAM offset
    sprite_tiles = kwargs.get("sprite_tiles", 10)
    for i in range(sprite_tiles):
        offset = VRAM_SPRITE_OFFSET + i * BYTES_PER_TILE
        if offset + BYTES_PER_TILE <= len(data):
            # Generate tile data
            for j in range(BYTES_PER_TILE):
                data[offset + j] = (i + j) % 256

    return data


def _generate_rom_data(**kwargs) -> bytearray:
    """Generate ROM data with embedded sprite data."""
    from .data_generators import generate_rom_data

    return generate_rom_data(
        size=kwargs.get("rom_size", 0x400000),
        add_sprites=kwargs.get("add_sprites", True),
        sprite_count=kwargs.get("sprite_count", 10)
    )


def cleanup_test_files(file_paths: list[str] | dict[str, str] | str):
    """
    Clean up test files and directories.

    Args:
        file_paths: File paths to clean up - can be a list, dict, or single path
    """
    if isinstance(file_paths, str):
        paths = [file_paths]
    elif isinstance(file_paths, dict):
        paths = list(file_paths.values())
    else:
        paths = file_paths

    for path in paths:
        path_obj = Path(path)

        try:
            if path_obj.is_file():
                path_obj.unlink()
            elif path_obj.is_dir():
                shutil.rmtree(path_obj)
        except OSError:
            # File/directory might already be deleted or inaccessible
            pass


def create_test_workspace(
    workspace_name: str = "test_workspace",
    include_files: list[str] | None = None
) -> dict[str, str]:
    """
    Create a complete test workspace with common file types.

    Args:
        workspace_name: Name of the workspace directory
        include_files: List of file types to include, defaults to common types

    Returns:
        Dictionary with workspace info and file paths
    """
    if include_files is None:
        include_files = ["vram", "cgram", "oam", "png", "palette", "metadata"]

    # Create workspace directory
    workspace_path = create_temp_directory(f"{workspace_name}_")

    # Create test files
    file_paths = create_test_files(workspace_path, include_files)

    # Add workspace path to results
    return {
        "workspace": workspace_path,
        **file_paths
    }



def ensure_directory_exists(path: str) -> str:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists

    Returns:
        The directory path (same as input)
    """
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def copy_test_files(source_files: dict[str, str], destination_dir: str) -> dict[str, str]:
    """
    Copy test files to a new directory.

    Args:
        source_files: Dictionary of file paths to copy
        destination_dir: Destination directory

    Returns:
        Dictionary with new file paths
    """
    dest_path = Path(destination_dir)
    dest_path.mkdir(parents=True, exist_ok=True)

    new_paths = {}

    for file_type, source_path in source_files.items():
        if file_type == "workspace":
            continue  # Skip workspace entries

        source = Path(source_path)
        if source.exists():
            dest_file = dest_path / source.name
            shutil.copy2(source, dest_file)
            new_paths[file_type] = str(dest_file)

    new_paths["workspace"] = str(dest_path)
    return new_paths


def get_test_data_size(file_path: str) -> int:
    """
    Get the size of a test data file.

    Args:
        file_path: Path to the file

    Returns:
        File size in bytes
    """
    return Path(file_path).stat().st_size


def verify_test_files(file_paths: dict[str, str]) -> dict[str, bool]:
    """
    Verify that test files exist and are valid.

    Args:
        file_paths: Dictionary of file paths to verify

    Returns:
        Dictionary mapping file types to their validity status
    """
    results = {}

    for file_type, file_path in file_paths.items():
        if file_type == "workspace":
            results[file_type] = Path(file_path).is_dir()
            continue

        path = Path(file_path)

        if not path.exists():
            results[file_type] = False
            continue

        # Check minimum file sizes
        size = path.stat().st_size

        if (file_type == "vram" and size < 0x1000) or (file_type == "cgram" and size < 32) or (file_type == "oam" and size < 4):  # At least 4KB
            results[file_type] = False
        else:
            results[file_type] = True

    return results
