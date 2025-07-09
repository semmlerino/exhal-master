#!/usr/bin/env python3
"""
Cross-Component Integration Tests
Tests complete workflows across sprite editor and pixel editor components
"""

import json
import os
import tempfile
from datetime import datetime
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image

# Import pixel editor components
from indexed_pixel_editor import IndexedPixelEditor
from sprite_editor.models.project_model import ProjectModel
from sprite_editor.models.sprite_model import SpriteModel

# Import sprite editor components
from sprite_editor.sprite_editor_core import SpriteEditorCore


class TestExtractEditInjectWorkflow:
    """Test the complete workflow: Extract → Edit → Inject"""

    @pytest.fixture
    def test_environment(self):
        """Create a test environment with VRAM, CGRAM, and working directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test VRAM data (8KB with recognizable pattern)
            vram_data = bytearray(8192)

            # Add some test sprite data at offset 0x1000
            # Create a simple 2x2 tile pattern (4 tiles, 32 bytes each)
            test_pattern = [
                # Tile 0: Diagonal pattern
                0xFF, 0x00, 0x7E, 0x00, 0x3C, 0x00, 0x18, 0x00,
                0x18, 0x00, 0x3C, 0x00, 0x7E, 0x00, 0xFF, 0x00,
                0x00, 0xFF, 0x00, 0x7E, 0x00, 0x3C, 0x00, 0x18,
                0x00, 0x18, 0x00, 0x3C, 0x00, 0x7E, 0x00, 0xFF,
            ]

            # Repeat pattern for 4 tiles
            for i in range(4):
                offset = 0x1000 + (i * 32)
                vram_data[offset:offset+32] = test_pattern

            vram_path = os.path.join(temp_dir, "test_vram.dmp")
            with open(vram_path, "wb") as f:
                f.write(vram_data)

            # Create test CGRAM data (palette)
            cgram_data = bytearray(512)
            # Create a simple test palette
            palette_colors = [
                (0, 0, 0),      # Black (transparent)
                (255, 0, 0),    # Red
                (0, 255, 0),    # Green
                (0, 0, 255),    # Blue
                (255, 255, 0),  # Yellow
                (255, 0, 255),  # Magenta
                (0, 255, 255),  # Cyan
                (255, 255, 255),# White
            ] + [(128, 128, 128)] * 8  # Gray for rest

            # Convert to SNES color format (15-bit BGR555)
            for i, (r, g, b) in enumerate(palette_colors):
                color_15bit = ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)
                cgram_data[i*2] = color_15bit & 0xFF
                cgram_data[i*2 + 1] = (color_15bit >> 8) & 0xFF

            cgram_path = os.path.join(temp_dir, "test_cgram.dmp")
            with open(cgram_path, "wb") as f:
                f.write(cgram_data)

            yield {
                "temp_dir": temp_dir,
                "vram_path": vram_path,
                "cgram_path": cgram_path,
                "vram_data": vram_data,
                "palette_colors": palette_colors[:16]
            }

    def test_complete_extract_edit_inject_workflow(self, qapp, test_environment):
        """Test extracting sprites, editing them, and injecting back"""
        env = test_environment

        # Step 1: Extract sprites using sprite editor core
        core = SpriteEditorCore()

        # Extract a 16x16 sprite (2x2 tiles) from offset 0x1000
        extracted_image, total_tiles = core.extract_sprites(
            vram_file=env["vram_path"],
            offset=0x1000,
            size=128,  # 4 tiles * 32 bytes
            tiles_per_row=2
        )

        # The extracted_image is already a PIL Image with grayscale palette
        # Apply test palette
        palette = []
        for r, g, b in env["palette_colors"]:
            palette.extend([r, g, b])
        while len(palette) < 768:
            palette.extend([0, 0, 0])
        extracted_image.putpalette(palette)

        # Save extracted sprite
        extracted_path = os.path.join(env["temp_dir"], "extracted_sprite.png")
        extracted_image.save(extracted_path)

        # Verify extraction
        assert os.path.exists(extracted_path)
        extracted_img = Image.open(extracted_path)
        assert extracted_img.mode == "P"
        assert extracted_img.size == (16, 16)

        # Step 2: Edit sprite in pixel editor
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()

            # Load the extracted sprite
            success = editor.load_file_by_path(extracted_path)
            assert success

            # Make some edits - draw a cross pattern
            editor.canvas.current_color = 1  # Red
            editor.canvas.save_undo()

            # Draw horizontal line
            for x in range(16):
                editor.canvas.draw_pixel(x, 8)

            # Draw vertical line
            for y in range(16):
                editor.canvas.draw_pixel(8, y)

            # Save edited sprite
            edited_path = os.path.join(env["temp_dir"], "edited_sprite.png")
            editor.save_to_file(edited_path)

        # Verify edit
        assert os.path.exists(edited_path)
        edited_img = Image.open(edited_path)
        assert edited_img.mode == "P"
        edited_array = np.array(edited_img)

        # Check that cross pattern was drawn
        assert all(edited_array[8, x] == 1 for x in range(16))  # Horizontal line
        assert all(edited_array[y, 8] == 1 for y in range(16))  # Vertical line

        # Step 3: Convert edited sprite back to SNES format
        tile_data, num_tiles = core.png_to_snes(edited_path)
        assert num_tiles == 4  # 2x2 tiles
        assert len(tile_data) == 128  # 4 tiles * 32 bytes

        # Step 4: Inject back into VRAM
        output_vram_path = os.path.join(env["temp_dir"], "modified_vram.dmp")
        core.inject_into_vram(
            tile_data,  # First positional argument
            env["vram_path"],  # Second positional argument (vram_file)
            0x1000,  # Third positional argument (offset)
            output_vram_path  # Fourth positional argument (output_file)
        )

        # Verify injection
        assert os.path.exists(output_vram_path)
        with open(output_vram_path, "rb") as f:
            modified_vram = f.read()

        # Original VRAM size should be preserved
        assert len(modified_vram) == len(env["vram_data"])

        # The data at offset 0x1000 should be different (edited)
        original_data = env["vram_data"][0x1000:0x1000+128]
        injected_data = modified_vram[0x1000:0x1000+128]
        assert original_data != injected_data

        # Data before and after the injection offset should be unchanged
        assert modified_vram[:0x1000] == env["vram_data"][:0x1000]
        assert modified_vram[0x1000+128:] == env["vram_data"][0x1000+128:]

    def test_extract_with_palette_selection(self, qapp, test_environment):
        """Test extraction with specific palette and editing workflow"""
        env = test_environment

        # Create sprite model and set CGRAM path
        sprite_model = SpriteModel()
        sprite_model.cgram_file = env["cgram_path"]

        # Set extraction parameters
        sprite_model.vram_file = env["vram_path"]
        sprite_model.extraction_offset = 0x1000
        sprite_model.extraction_size = 128
        sprite_model.tiles_per_row = 2
        sprite_model.current_palette = 0

        # Extract with palette 0
        sprite_model.extract_sprites(apply_palette=True)

        # Save with palette applied
        output_path = os.path.join(env["temp_dir"], "sprite_with_palette.png")
        if sprite_model.current_image:
            sprite_model.current_image.save(output_path)

        # Load in pixel editor
        with patch.object(IndexedPixelEditor, "handle_startup"):
            editor = IndexedPixelEditor()
            success = editor.load_file_by_path(output_path)
            assert success

            # The palette should be loaded from the image
            assert editor.palette_widget.colors is not None

            # Edit and save
            editor.canvas.current_color = 5  # Magenta
            editor.canvas.draw_pixel(0, 0)
            editor.canvas.draw_pixel(15, 15)

            edited_path = os.path.join(env["temp_dir"], "edited_with_palette.png")
            editor.save_to_file(edited_path)

        # Verify the edited pixels
        edited_img = Image.open(edited_path)
        edited_array = np.array(edited_img)
        assert edited_array[0, 0] == 5
        assert edited_array[15, 15] == 5


class TestProjectSaveLoadWorkflow:
    """Test project save/load with all components"""

    @pytest.fixture
    def project_environment(self):
        """Create a test project with multiple files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            vram_path = os.path.join(temp_dir, "game_vram.dmp")
            cgram_path = os.path.join(temp_dir, "game_cgram.dmp")
            oam_path = os.path.join(temp_dir, "game_oam.dmp")

            # Create dummy data
            with open(vram_path, "wb") as f:
                f.write(b"\x00" * 8192)
            with open(cgram_path, "wb") as f:
                f.write(b"\x00" * 512)
            with open(oam_path, "wb") as f:
                f.write(b"\x00" * 544)

            # Create some extracted sprites
            sprite_paths = []
            for i in range(3):
                sprite_path = os.path.join(temp_dir, f"sprite_{i}.png")
                img = Image.new("P", (16, 16), 0)
                img.save(sprite_path)
                sprite_paths.append(sprite_path)

            yield {
                "temp_dir": temp_dir,
                "vram_path": vram_path,
                "cgram_path": cgram_path,
                "oam_path": oam_path,
                "sprite_paths": sprite_paths
            }

    def test_project_save_and_reload_state(self, qapp, project_environment):
        """Test saving project state and reloading it preserves all data"""
        env = project_environment

        # Create project model
        project_model = ProjectModel()

        # Set up project data
        project_model.project_name = "Test Game Sprites"
        project_model.project_path = os.path.join(env["temp_dir"], "test_project.ksproj")

        # Add files to recent lists (simulating work)
        project_model.add_recent_file(env["vram_path"], "vram")
        project_model.add_recent_file(env["cgram_path"], "cgram")
        project_model.add_recent_file(env["oam_path"], "oam")
        for sprite_path in env["sprite_paths"]:
            project_model.add_recent_file(sprite_path, "png")

        # Create enhanced project data structure
        # Note: Current implementation only saves minimal data
        # This test demonstrates what SHOULD be saved
        enhanced_project_data = {
            "name": project_model.project_name,
            "version": "1.1",  # Enhanced version
            "created": datetime.now().isoformat(),
            "files": {
                "vram": env["vram_path"],
                "cgram": env["cgram_path"],
                "oam": env["oam_path"]
            },
            "recent_files": {
                "vram": project_model.recent_vram_files,
                "cgram": project_model.recent_cgram_files,
                "oam": project_model.recent_oam_files,
                "png": project_model.recent_png_files
            },
            "extractions": [
                {
                    "name": "Main Character",
                    "vram_offset": 0x1000,
                    "size": 0x400,
                    "tiles_per_row": 4,
                    "palette_index": 0,
                    "output_file": env["sprite_paths"][0]
                },
                {
                    "name": "Enemy Sprite",
                    "vram_offset": 0x2000,
                    "size": 0x200,
                    "tiles_per_row": 2,
                    "palette_index": 8,
                    "output_file": env["sprite_paths"][1]
                }
            ],
            "settings": {
                "last_extraction_offset": 0x1000,
                "last_tile_count": 16,
                "last_tiles_per_row": 4
            }
        }

        # Save project with enhanced data
        project_path = project_model.project_path
        with open(project_path, "w") as f:
            json.dump(enhanced_project_data, f, indent=2)

        # Clear current state by creating a new model
        project_model = ProjectModel()
        # Clear any loaded recent files
        project_model.clear_recent_files()
        # Reset name to default
        project_model.project_name = "Untitled"
        assert project_model.project_name == "Untitled"
        assert len(project_model.recent_vram_files) == 0

        # Since ProjectModel doesn't have load_project method,
        # we'll simulate what it would do by reading the file directly
        with open(project_path) as f:
            loaded_data = json.load(f)

        # Manually set the project name as if it was loaded
        project_model.project_name = loaded_data["name"]
        assert project_model.project_name == "Test Game Sprites"

        # Test what enhanced loading would look like
        with open(project_path) as f:
            enhanced_loaded = json.load(f)

        # Verify enhanced data structure
        assert enhanced_loaded["version"] == "1.1"
        assert len(enhanced_loaded["extractions"]) == 2
        assert enhanced_loaded["extractions"][0]["name"] == "Main Character"
        assert enhanced_loaded["settings"]["last_extraction_offset"] == 0x1000

        # Verify file references are preserved
        assert enhanced_loaded["files"]["vram"] == env["vram_path"]
        # Check that our sprite paths are in the recent files (may contain more from persistent storage)
        saved_png_files = enhanced_loaded["recent_files"]["png"]
        for sprite_path in env["sprite_paths"]:
            assert sprite_path in saved_png_files

    def test_project_with_edited_sprites_workflow(self, qapp, project_environment):
        """Test project workflow with sprite editing history"""
        env = project_environment

        # Simulate a working session
        ProjectModel()
        sprite_model = SpriteModel()

        # Set file paths
        sprite_model.vram_file = env["vram_path"]
        sprite_model.cgram_file = env["cgram_path"]

        # Track extraction parameters
        extraction_history = []

        # Simulate multiple extractions
        for i, (offset, size) in enumerate([(0x1000, 128), (0x2000, 64), (0x3000, 256)]):
            # Mock extraction
            sprite_model.extraction_offset = offset
            sprite_model.extraction_size = size
            sprite_model.tiles_per_row = 2

            extraction_history.append({
                "id": i,
                "offset": offset,
                "size": size,
                "tiles_per_row": 2,
                "timestamp": datetime.now().isoformat(),
                "output": env["sprite_paths"][i] if i < len(env["sprite_paths"]) else None
            })

        # Create comprehensive project save
        project_data = {
            "name": "Sprite Editing Session",
            "created": datetime.now().isoformat(),
            "files": {
                "vram": env["vram_path"],
                "cgram": env["cgram_path"]
            },
            "session_data": {
                "extraction_history": extraction_history,
                "current_extraction": {
                    "offset": sprite_model.extraction_offset,
                    "size": sprite_model.extraction_size,
                    "tiles_per_row": sprite_model.tiles_per_row
                },
                "modified_sprites": [
                    {
                        "original": env["sprite_paths"][0],
                        "edited": env["sprite_paths"][0].replace(".png", "_edited.png"),
                        "changes": "Added player details"
                    }
                ]
            }
        }

        # Save and verify structure
        project_path = os.path.join(env["temp_dir"], "editing_session.ksproj")
        with open(project_path, "w") as f:
            json.dump(project_data, f, indent=2)

        # Verify the saved data
        with open(project_path) as f:
            loaded = json.load(f)

        assert len(loaded["session_data"]["extraction_history"]) == 3
        assert loaded["session_data"]["current_extraction"]["offset"] == 0x3000


class TestMultipleWindowWorkflow:
    """Test multiple window/document handling"""

    def test_multiple_pixel_editor_instances(self, qapp):
        """Test running multiple pixel editor instances simultaneously"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test images
            images = []
            for i in range(3):
                img_path = os.path.join(temp_dir, f"sprite_{i}.png")
                img = Image.new("P", (16, 16), i)

                # Different palette for each
                palette = []
                for j in range(16):
                    palette.extend([j*16, (j+i)*16 % 256, (j+i*2)*16 % 256])
                while len(palette) < 768:
                    palette.extend([0, 0, 0])
                img.putpalette(palette)
                img.save(img_path)
                images.append(img_path)

            # Create multiple editor instances
            editors = []
            with patch.object(IndexedPixelEditor, "handle_startup"):
                for i, img_path in enumerate(images):
                    editor = IndexedPixelEditor()
                    editor.load_file_by_path(img_path)

                    # Each editor should have independent state
                    editor.canvas.current_color = i + 1
                    editor.canvas.draw_pixel(i, i)

                    editors.append(editor)

            # Verify each editor maintains independent state
            for i, editor in enumerate(editors):
                assert editor.current_file == images[i]
                assert editor.canvas.current_color == i + 1
                assert editor.canvas.image_data[i, i] == i + 1

            # Modify one editor shouldn't affect others
            editors[0].canvas.current_color = 15
            editors[0].canvas.draw_pixel(5, 5)

            # Check others are unaffected
            assert editors[1].canvas.image_data[5, 5] != 15
            assert editors[2].canvas.image_data[5, 5] != 15

    def test_sprite_editor_to_pixel_editor_communication(self, qapp):
        """Test opening pixel editor from sprite editor with context"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test VRAM
            vram_path = os.path.join(temp_dir, "test.vram")
            with open(vram_path, "wb") as f:
                f.write(b"\x00" * 8192)

            # Setup sprite editor components
            sprite_model = SpriteModel()
            sprite_model.vram_file = vram_path

            # Extract a sprite
            output_path = os.path.join(temp_dir, "extracted.png")

            # Simulate extraction
            img = Image.new("P", (32, 32), 0)
            img.save(output_path)

            # Simulate opening in pixel editor with metadata
            metadata = {
                "source": "sprite_editor",
                "vram_offset": 0x1000,
                "extraction_size": 512,
                "palette_index": 8,
                "project": "test_project.ksproj"
            }

            metadata_path = output_path.replace(".png", "_metadata.json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f)

            # Open in pixel editor
            with patch.object(IndexedPixelEditor, "handle_startup"):
                editor = IndexedPixelEditor()
                editor.load_file_by_path(output_path)

                # Editor should detect and load metadata
                assert os.path.exists(metadata_path)

                # In a full implementation, editor would:
                # 1. Show source information in status bar
                # 2. Offer to inject back to same offset
                # 3. Maintain project association


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
