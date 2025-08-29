"""Integration tests for sprite injection workflow"""
from __future__ import annotations

import os
import tempfile

import pytest
from PIL import Image

from core.extractor import SpriteExtractor
from core.injector import InjectionWorker, SpriteInjector
from core.palette_manager import PaletteManager

# Systematic pytest markers applied based on test content analysis
pytestmark = [
    pytest.mark.file_io,
    pytest.mark.headless,
    pytest.mark.integration,
    pytest.mark.no_qt,
    pytest.mark.rom_data,
    pytest.mark.signals_slots,
]

class TestInjectionWorkflowIntegration:
    """Test complete injection workflow integration"""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create subdirectories
            os.makedirs(os.path.join(tmpdir, "input"))
            os.makedirs(os.path.join(tmpdir, "output"))
            os.makedirs(os.path.join(tmpdir, "vram"))
            yield tmpdir

    @pytest.fixture
    def test_vram(self, temp_workspace):
        """Create a test VRAM file"""
        vram_path = os.path.join(temp_workspace, "vram", "test.dmp")
        # Create 64KB VRAM file with test pattern
        data = bytearray(65536)
        # Add some test sprite data at sprite offset
        sprite_offset = 0xC000
        for i in range(1024):
            data[sprite_offset + i] = i % 256

        with open(vram_path, "wb") as f:
            f.write(data)
        return vram_path

    @pytest.fixture
    def test_cgram(self, temp_workspace):
        """Create a test CGRAM file"""
        cgram_path = os.path.join(temp_workspace, "input", "test.cgram")
        # Create palette data (BGR555 format)
        data = bytearray(512)
        # Add test palettes
        for i in range(256):
            # Simple gradient
            color = (i % 32) | ((i % 32) << 5) | ((i % 32) << 10)
            data[i * 2] = color & 0xFF
            data[i * 2 + 1] = (color >> 8) & 0xFF

        with open(cgram_path, "wb") as f:
            f.write(data)
        return cgram_path

    def test_extract_modify_inject_workflow(
        self, temp_workspace, test_vram, test_cgram
    ):
        """Test full workflow: extract sprite, modify it, inject back"""
        # Step 1: Extract sprites
        extractor = SpriteExtractor()
        output_path = os.path.join(temp_workspace, "output", "extracted.png")

        # Use the correct method for extraction
        img, num_tiles = extractor.extract_sprites_grayscale(
            vram_path=test_vram, output_path=output_path
        )

        assert num_tiles > 0
        assert os.path.exists(output_path)

        # Step 2: Extract palettes
        palette_manager = PaletteManager()
        palette_manager.load_cgram(test_cgram)

        # Export sprite palettes (8-15 are sprite palettes)
        palette_files = {}
        for i in range(8, 16):
            pal_path = os.path.join(
                temp_workspace, "output", f"extracted_pal{i}.pal.json"
            )
            created_path = palette_manager.create_palette_json(i, pal_path, output_path)
            if created_path:
                palette_files[i] = created_path

        assert len(palette_files) > 0

        # Step 3: Simulate modifying the sprite
        img = Image.open(output_path)
        assert img.mode == "P"  # Should be indexed

        # Make a small modification (ensure we stay within palette)
        pixels = img.load()
        if pixels[0, 0] < 15:
            pixels[0, 0] = pixels[0, 0] + 1

        modified_path = os.path.join(temp_workspace, "output", "modified.png")
        img.save(modified_path)

        # Step 4: Inject the modified sprite back
        injector = SpriteInjector()

        # First validate
        is_valid, error_msg = injector.validate_sprite(modified_path)
        assert is_valid, f"Sprite validation failed: {error_msg}"

        # Then inject (save to same VRAM file)
        result, msg = injector.inject_sprite(
            sprite_path=modified_path,
            vram_path=test_vram,
            output_path=test_vram,  # Overwrite the original
            offset=0xC000,
        )

        assert result is True, f"Injection failed: {msg}"

        # Step 5: Verify injection worked
        # Extract again and compare
        verification_path = os.path.join(temp_workspace, "output", "verification.png")
        verification_img, _ = extractor.extract_sprites_grayscale(
            vram_path=test_vram, output_path=verification_path
        )

        # Both images should have the modification
        modified_img = Image.open(modified_path)
        verified_img = Image.open(verification_path)

        assert modified_img.getpixel((0, 0)) == verified_img.getpixel((0, 0))

    def test_injection_worker_integration(self, temp_workspace, test_vram):
        """Test InjectionWorker with signals"""
        # Create a test sprite
        sprite_path = os.path.join(temp_workspace, "output", "test_sprite.png")
        img = Image.new("P", (128, 128))

        # Create a simple palette
        palette = []
        for i in range(256):
            palette.extend([i, i, i])
        img.putpalette(palette)

        # Draw some test pattern
        pixels = img.load()
        for y in range(16):
            for x in range(128):
                pixels[x, y] = (x + y) % 16

        img.save(sprite_path)

        # Create worker (inject in-place)
        worker = InjectionWorker(sprite_path, test_vram, test_vram, 0xC000)

        # Track signals
        progress_updates = []
        completion_results = []

        worker.progress.connect(lambda msg: progress_updates.append(msg))
        worker.injection_finished.connect(
            lambda success, msg: completion_results.append((success, msg))
        )

        # Run worker
        worker.run()

        # Verify signals
        assert len(progress_updates) > 0
        assert len(completion_results) == 1
        success, message = completion_results[0]
        assert success is True
        assert "Validating sprite" in progress_updates[0]
        assert "Injection complete" in progress_updates[-1]

    def test_injection_with_metadata(self, temp_workspace, test_vram):
        """Test injection using metadata from extraction"""
        # Create metadata file with proper structure
        metadata = {
            "extraction": {
                "source": "test.dmp",
                "offset": 0xC000,
                "tile_count": 8,
                "palette_indices": [8, 9, 10],
                "extraction_date": "2024-01-01",
            }
        }

        sprite_path = os.path.join(temp_workspace, "test_sprite.png")
        metadata_path = os.path.join(temp_workspace, "test_sprite.metadata.json")

        # Create test sprite
        img = Image.new("P", (64, 64))
        palette = []
        for i in range(256):
            palette.extend([i, i, i])
        img.putpalette(palette)
        img.save(sprite_path)

        # Save metadata
        import json

        with open(metadata_path, "w") as f:
            json.dump(metadata, f)

        # Test injection with metadata
        injector = SpriteInjector()
        injector.load_metadata(metadata_path)
        extraction_info = injector.get_extraction_info()

        assert extraction_info is not None
        assert extraction_info.get("offset") == 0xC000

        # Inject using metadata offset
        offset = extraction_info.get("offset", 0xC000)
        result, msg = injector.inject_sprite(sprite_path, test_vram, test_vram, offset)
        assert result is True, f"Injection failed: {msg}"

    def test_concurrent_injection_handling(self, temp_workspace, test_vram):
        """Test handling multiple injection operations"""
        # Create multiple test sprites
        sprites = []
        for i in range(3):
            sprite_path = os.path.join(temp_workspace, f"sprite_{i}.png")
            img = Image.new("P", (32, 32))

            palette = []
            for j in range(256):
                palette.extend([j, j, j])
            img.putpalette(palette)

            # Different pattern for each sprite - ensure non-zero values
            pixels = img.load()
            for y in range(32):
                for x in range(32):
                    # Use pattern that ensures non-zero values
                    pixels[x, y] = ((i + 1) * 4 + (x + y) % 4) % 16

            img.save(sprite_path)
            sprites.append(sprite_path)

        # Inject sprites at different offsets
        injector = SpriteInjector()
        offsets = [0xC000, 0xC400, 0xC800]

        for sprite, offset in zip(sprites, offsets):
            result, msg = injector.inject_sprite(sprite, test_vram, test_vram, offset)
            assert result is True, f"Injection failed: {msg}"

        # Verify all injections succeeded
        with open(test_vram, "rb") as f:
            vram_data = f.read()

        # Check that data was written at each offset
        for offset in offsets:
            # Should have non-zero data at each injection point
            chunk = vram_data[offset : offset + 32]
            assert any(b != 0 for b in chunk)

    def test_injection_error_recovery(self, temp_workspace, test_vram):
        """Test error handling during injection"""
        # Test case 1: RGB image (wrong mode)
        rgb_sprite_path = os.path.join(temp_workspace, "rgb_sprite.png")
        img = Image.new("RGB", (64, 64))

        # Draw with many colors
        pixels = img.load()
        for y in range(64):
            for x in range(64):
                pixels[x, y] = (x * 4, y * 4, (x + y) * 2)

        img.save(rgb_sprite_path)

        # Validate RGB sprite
        injector = SpriteInjector()
        is_valid, error_msg = injector.validate_sprite(rgb_sprite_path)

        assert not is_valid
        assert "indexed" in error_msg.lower()
        assert "mode" in error_msg.lower()

        # Test case 2: Too many colors in indexed mode
        indexed_sprite_path = os.path.join(temp_workspace, "too_many_colors.png")
        img = Image.new("P", (64, 64))

        # Create palette with 32 colors (more than 16 allowed)
        palette = []
        for i in range(256):
            palette.extend([i, i, i])
        img.putpalette(palette)

        # Use more than 16 colors
        pixels = img.load()
        for y in range(64):
            for x in range(64):
                pixels[x, y] = (x + y) % 32  # Uses up to 32 different values

        img.save(indexed_sprite_path)

        # Validate indexed sprite with too many colors
        is_valid, error_msg = injector.validate_sprite(indexed_sprite_path)

        assert not is_valid
        assert "too many colors" in error_msg.lower()

        # inject_sprite doesn't validate, but convert_png_to_4bpp auto-converts RGB to indexed
        # So RGB images will actually succeed by being converted to 16 colors
        result, msg = injector.inject_sprite(
            rgb_sprite_path, test_vram, test_vram, 0xC000
        )
        assert result is True  # Should succeed due to automatic conversion

        # However, indexed images with too many colors will be handled by adaptive palette
        result, msg = injector.inject_sprite(
            indexed_sprite_path, test_vram, test_vram, 0xC000
        )
        assert result is True  # Also succeeds - convert_png_to_4bpp handles it

    def test_round_trip_preservation(self, temp_workspace, test_vram, test_cgram):
        """Test that extract->inject preserves original data"""
        # Step 1: Create known pattern in VRAM
        with open(test_vram, "rb") as f:
            original_data = f.read()

        # Step 2: Extract
        extractor = SpriteExtractor()
        extracted_path = os.path.join(temp_workspace, "extracted.png")

        # Extract using the correct API
        img, num_tiles = extractor.extract_sprites_grayscale(
            vram_path=test_vram, output_path=extracted_path
        )

        # Step 3: Inject back without modification
        injector = SpriteInjector()
        result, msg = injector.inject_sprite(
            extracted_path, test_vram, test_vram, 0xC000
        )
        assert result is True, f"Injection failed: {msg}"

        # Step 4: Compare VRAM data
        with open(test_vram, "rb") as f:
            final_data = f.read()

        # The sprite data region should be identical
        sprite_size = 32 * 32  # 32 tiles * 32 bytes per tile
        original_sprite = original_data[0xC000 : 0xC000 + sprite_size]
        final_sprite = final_data[0xC000 : 0xC000 + sprite_size]

        assert original_sprite == final_sprite, "Round trip failed to preserve data"

    def test_injection_progress_tracking(self, temp_workspace, test_vram):
        """Test progress reporting during injection"""
        # Create a larger sprite to test progress
        sprite_path = os.path.join(temp_workspace, "large_sprite.png")
        img = Image.new("P", (256, 256))

        palette = []
        for i in range(256):
            palette.extend([i, i, i])
        img.putpalette(palette)

        img.save(sprite_path)

        # Create worker with progress tracking
        worker = InjectionWorker(sprite_path, test_vram, test_vram, 0xC000)

        progress_messages = []
        worker.progress.connect(lambda msg: progress_messages.append(msg))

        worker.run()

        # Should have multiple progress updates
        assert len(progress_messages) >= 3
        assert any("Validating" in msg for msg in progress_messages)
        assert any("Converting" in msg for msg in progress_messages)
        assert any("Injecting" in msg for msg in progress_messages)

    def test_injection_boundary_validation(self, temp_workspace, test_vram):
        """Test injection at VRAM boundaries"""
        # Create sprite
        sprite_path = os.path.join(temp_workspace, "boundary_sprite.png")
        img = Image.new("P", (128, 64))

        palette = []
        for i in range(256):
            palette.extend([i, i, i])
        img.putpalette(palette)
        img.save(sprite_path)

        injector = SpriteInjector()

        # Test injection at valid boundary
        result, msg = injector.inject_sprite(sprite_path, test_vram, test_vram, 0xF000)
        assert result is True, f"Injection failed: {msg}"

        # Test injection that would exceed VRAM
        result, msg = injector.inject_sprite(sprite_path, test_vram, test_vram, 0xFE00)
        assert result is False, "Expected injection to fail - too close to end of VRAM"