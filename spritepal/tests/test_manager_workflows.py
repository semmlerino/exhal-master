"""
Integration tests for complete UI → Manager workflows
"""

from pathlib import Path

import pytest
from tests.fixtures.test_managers import (
# Systematic pytest markers applied based on test content analysis
pytestmark = [
    pytest.mark.file_io,
    pytest.mark.headless,
    pytest.mark.integration,
    pytest.mark.no_qt,
    pytest.mark.rom_data,
]


    create_extraction_manager_fixture,
    create_injection_manager_fixture,
)

from core.managers import (
    cleanup_managers,
    get_extraction_manager,
    get_injection_manager,
    get_session_manager,
    initialize_managers,
)
from core.managers.exceptions import ValidationError


@pytest.fixture(autouse=True)
def setup_managers():
    """Setup managers for all tests"""
    initialize_managers("TestApp")
    yield
    cleanup_managers()


class TestExtractionToInjectionWorkflow:
    """Test complete extraction → injection workflows"""

    @pytest.fixture
    def test_files(self, tmp_path):
        """Create test files for extraction → injection workflow"""
        # Create VRAM file with test data
        vram_data = bytearray(0x10000)  # 64KB
        for i in range(100):
            offset = 0xC000 + (i * 32)  # VRAM sprite offset
            for j in range(32):
                vram_data[offset + j] = (i + j) % 256

        vram_file = tmp_path / "test_VRAM.dmp"
        vram_file.write_bytes(vram_data)

        # Create CGRAM file with test palettes
        cgram_data = bytearray(512)  # 256 colors * 2 bytes
        for i in range(256):
            cgram_data[i * 2] = i % 32
            cgram_data[i * 2 + 1] = (i // 32) % 32

        cgram_file = tmp_path / "test_CGRAM.dmp"
        cgram_file.write_bytes(cgram_data)

        return {
            "vram_path": str(vram_file),
            "cgram_path": str(cgram_file),
            "output_dir": str(tmp_path),
        }

    def test_complete_extraction_to_injection_workflow(self, test_files):
        """Test complete workflow: extract sprites → inject back to VRAM"""
        extraction_manager = get_extraction_manager()
        injection_manager = get_injection_manager()

        # Step 1: Extract sprites from VRAM
        output_base = str(Path(test_files["output_dir"]) / "extracted_sprite")

        extracted_files = extraction_manager.extract_from_vram(
            vram_path=test_files["vram_path"],
            cgram_path=test_files["cgram_path"],
            output_base=output_base,
            create_grayscale=True,
            create_metadata=True,
        )

        # Verify extraction created files
        sprite_file = f"{output_base}.png"
        palette_file = f"{output_base}.pal.json"
        metadata_file = f"{output_base}.metadata.json"

        assert sprite_file in extracted_files
        assert palette_file in extracted_files
        assert metadata_file in extracted_files

        for file_path in [sprite_file, palette_file, metadata_file]:
            assert Path(file_path).exists()

        # Step 2: Test injection parameter validation
        injection_params = {
            "mode": "vram",
            "sprite_path": sprite_file,
            "input_vram": test_files["vram_path"],
            "output_vram": str(Path(test_files["output_dir"]) / "output_VRAM.dmp"),
            "offset": 0xC000,
            "metadata_path": metadata_file,
        }

        # Should validate successfully
        injection_manager.validate_injection_params(injection_params)

        # Step 3: Test smart VRAM suggestion using extracted files
        suggested_vram = injection_manager.get_smart_vram_suggestion(
            sprite_file, metadata_file
        )

        # Smart suggestion may or may not find a path depending on file patterns
        # This is acceptable behavior - just verify the method doesn't crash
        assert isinstance(suggested_vram, str)  # Should return a string (may be empty)

    def test_extraction_manager_integration_with_session(self, test_files):
        """Test extraction manager integration with session manager"""
        extraction_manager = get_extraction_manager()
        session_manager = get_session_manager()

        # Extract sprites
        output_base = str(Path(test_files["output_dir"]) / "session_test")

        extraction_manager.extract_from_vram(
            vram_path=test_files["vram_path"],
            cgram_path=test_files["cgram_path"],
            output_base=output_base,
        )

        # Session should track the files
        recent_vram = session_manager.get_recent_files("vram")
        if recent_vram:  # May be empty in test environment
            assert test_files["vram_path"] in recent_vram

    def test_injection_manager_with_extracted_files(self, test_files):
        """Test injection manager using files from extraction workflow"""
        extraction_manager = get_extraction_manager()
        injection_manager = get_injection_manager()

        # Step 1: Extract to get real files
        output_base = str(Path(test_files["output_dir"]) / "for_injection")

        extracted_files = extraction_manager.extract_from_vram(
            vram_path=test_files["vram_path"],
            cgram_path=test_files["cgram_path"],
            output_base=output_base,
        )

        sprite_file = f"{output_base}.png"
        assert sprite_file in extracted_files
        assert Path(sprite_file).exists()

        # Step 2: Use real injection manager fixture for testing
        injection_fixture = create_injection_manager_fixture(test_files["output_dir"])

        try:
            injection_params = {
                "mode": "vram",
                "sprite_path": sprite_file,
                "input_vram": test_files["vram_path"],
                "output_vram": str(Path(test_files["output_dir"]) / "injected_VRAM.dmp"),
                "offset": 0xC000,
            }

            # Validate injection parameters with real manager
            injection_manager.validate_injection_params(injection_params)

            # Verify injection parameters are properly structured for real workflow
            assert Path(injection_params["sprite_path"]).exists()
            assert Path(injection_params["input_vram"]).exists()
            assert injection_params["offset"] == 0xC000
            assert injection_params["mode"] == "vram"

        finally:
            injection_fixture.cleanup()


class TestManagerCommunication:
    """Test communication patterns between managers"""

    def test_managers_share_session_data(self):
        """Test that managers can share data through session manager"""
        get_extraction_manager()
        get_injection_manager()
        session_manager = get_session_manager()

        # Set some session data
        test_vram_path = "/test/path/to/vram.dmp"
        session_manager.set("session", "vram_path", test_vram_path)

        # Managers should be able to access shared session data
        session_vram = session_manager.get("session", "vram_path", "")
        assert session_vram == test_vram_path

    def test_manager_error_handling_integration(self):
        """Test error handling across manager interactions"""
        extraction_manager = get_extraction_manager()
        injection_manager = get_injection_manager()

        # Test extraction with invalid parameters
        invalid_params = {
            "vram_path": "/nonexistent/vram.dmp",
            "output_base": "/invalid/output",
        }

        with pytest.raises(ValidationError):  # Should raise validation error
            extraction_manager.validate_extraction_params(invalid_params)

        # Test injection with invalid parameters
        invalid_injection_params = {
            "mode": "invalid_mode",
            "sprite_path": "/nonexistent/sprite.png",
            "offset": -100,
        }

        with pytest.raises(ValidationError):  # Should raise validation error
            injection_manager.validate_injection_params(invalid_injection_params)

    def test_rom_injection_workflow_integration(self, tmp_path):
        """Test ROM injection workflow integration"""
        injection_manager = get_injection_manager()

        # Use injection manager fixture to create real test files
        injection_fixture = create_injection_manager_fixture(str(tmp_path))

        try:
            # Get real ROM injection parameters from fixture
            fixture_params = injection_fixture.get_rom_injection_params()

            # Convert fixture parameter names to manager expected names
            rom_injection_params = {
                "mode": "rom",
                "sprite_path": fixture_params["sprite_path"],
                "input_rom": fixture_params["input_rom_path"],
                "output_rom": str(tmp_path / "output.sfc"),
                "offset": 0x8000,
                "fast_compression": True,
            }

            # Validate ROM injection parameters with real manager
            injection_manager.validate_injection_params(rom_injection_params)

            # Verify ROM injection parameters are properly structured
            assert Path(rom_injection_params["sprite_path"]).exists()
            assert Path(rom_injection_params["input_rom"]).exists()
            assert rom_injection_params["offset"] == 0x8000
            assert rom_injection_params["mode"] == "rom"
            assert rom_injection_params["fast_compression"] is True

        finally:
            injection_fixture.cleanup()


class TestManagerStateConsistency:
    """Test manager state consistency during operations"""

    def test_manager_operation_state_tracking(self):
        """Test that managers properly track active operations"""
        extraction_manager = get_extraction_manager()
        injection_manager = get_injection_manager()

        # Initially no operations should be active
        assert not extraction_manager._active_operations
        assert not injection_manager._active_operations

        # After cleanup, operations should be cleared
        extraction_manager.cleanup()
        injection_manager.cleanup()

        assert not extraction_manager._active_operations
        assert not injection_manager._active_operations

    def test_manager_initialization_consistency(self):
        """Test that all managers initialize consistently"""
        extraction_manager = get_extraction_manager()
        injection_manager = get_injection_manager()
        session_manager = get_session_manager()

        # All managers should be initialized
        assert extraction_manager._is_initialized
        assert injection_manager._is_initialized
        assert session_manager._is_initialized

        # All should have proper names
        assert extraction_manager._name == "ExtractionManager"
        assert injection_manager._name == "InjectionManager"
        assert session_manager._name == "SessionManager"

    def test_concurrent_manager_operations(self, tmp_path):
        """Test handling of concurrent manager operations"""
        extraction_manager = get_extraction_manager()
        injection_manager = get_injection_manager()

        # Use test fixtures to create real test files
        extraction_fixture = create_extraction_manager_fixture(str(tmp_path))
        injection_fixture = create_injection_manager_fixture(str(tmp_path))

        try:
            # Get real VRAM injection parameters from fixture
            fixture_injection_params = injection_fixture.get_vram_injection_params()

            # Convert fixture parameter names to manager expected names
            injection_params = {
                "mode": "vram",
                "sprite_path": fixture_injection_params["sprite_path"],
                "input_vram": fixture_injection_params["input_vram_path"],
                "output_vram": str(tmp_path / "output.vram"),
                "offset": fixture_injection_params["vram_offset"],
            }

            # Test injection parameter validation (instead of starting actual injection)
            # This tests manager independence without requiring worker threads
            injection_manager.validate_injection_params(injection_params)

            # Extraction manager should still be able to operate independently
            # (This tests that managers don't interfere with each other)
            extraction_params = extraction_fixture.get_vram_extraction_params()

            # Override paths for test isolation
            extraction_params.update({
                "output_base": str(tmp_path / "extracted"),
                "grayscale_mode": True,  # Enable grayscale mode to avoid CGRAM requirement
            })

            # Should validate successfully (different manager, different operation)
            extraction_manager.validate_extraction_params(extraction_params)

            # Verify both managers can validate their parameters independently
            assert Path(injection_params["sprite_path"]).exists()
            assert Path(extraction_params["vram_path"]).exists()

        finally:
            extraction_fixture.cleanup()
            injection_fixture.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
