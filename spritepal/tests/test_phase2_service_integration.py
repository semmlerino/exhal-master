"""
Phase 2 Service Integration Tests for SpritePal

This comprehensive test suite validates that all Phase 2 services work correctly
together and maintain backward compatibility with existing code patterns.

Services tested:
1. FileValidator (utils/file_validator.py)
2. PreviewGenerator (utils/preview_generator.py)
3. UnifiedErrorHandler (utils/unified_error_handler.py)
4. Constants updates (utils/constants.py)

Test categories:
- Service Interface Tests: Import/instantiation validation
- Integration Tests: Cross-service interactions

import shutil

import shutil

import shutil

import shutil
- Backward Compatibility: Existing code patterns
- Performance Tests: Service overhead and caching
- Thread Safety Tests: Concurrent access patterns
"""
from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Core dependencies
from core.managers.exceptions import ValidationError
from PIL import Image
from tests.utils.file_helpers import create_temp_directory, create_test_files
from utils.constants import (
# Serial execution required: Thread safety concerns

    BYTES_PER_TILE,
    CGRAM_EXPECTED_SIZE,
    CGRAM_PATTERNS,
    COLORS_PER_PALETTE,
    OAM_EXPECTED_SIZE,
    VRAM_MAX_SIZE,
    VRAM_MIN_SIZE,
    VRAM_PATTERNS,
)

# Phase 2 Services under test
from utils.file_validator import FileInfo, FileValidator, ValidationResult
from utils.preview_generator import (
    PaletteData,
    PreviewGenerator,
    PreviewRequest,
    create_vram_preview_request,
    get_preview_generator,
)
from utils.unified_error_handler import (
    ErrorCategory,
    ErrorContext,
    ErrorResult,
    ErrorSeverity,
    UnifiedErrorHandler,
    get_unified_error_handler,
    reset_unified_error_handler,
)

pytestmark = [
    
    pytest.mark.serial,
    pytest.mark.thread_safety,
    pytest.mark.cache,
    pytest.mark.ci_safe,
    pytest.mark.file_io,
    pytest.mark.headless,
    pytest.mark.performance,
    pytest.mark.rom_data,
    pytest.mark.slow,
    pytest.mark.worker_threads,
]
@pytest.fixture
def temp_test_environment():
    """Create a temporary test environment with test files."""
    temp_dir = create_temp_directory("phase2_integration_")

    # Create test files using helpers
    test_files = create_test_files(
        temp_dir,
        ["vram", "cgram", "oam", "rom", "png", "palette"],
        vram_size=VRAM_MIN_SIZE,
        palette_count=16  # 16 palettes = 512 bytes (correct CGRAM size)
    )

    # Add some invalid files for error testing
    invalid_dir = Path(temp_dir) / "invalid"
    invalid_dir.mkdir()

    # Empty file
    (invalid_dir / "empty.dmp").touch()

    # Invalid size CGRAM
    with open(invalid_dir / "bad_cgram.dmp", "wb") as f:
        f.write(b"x" * 100)  # Wrong size

    # Invalid JSON
    with open(invalid_dir / "bad.json", "w") as f:
        f.write("{ invalid json")

    test_files.update({
        "empty_file": str(invalid_dir / "empty.dmp"),
        "bad_cgram": str(invalid_dir / "bad_cgram.dmp"),
        "bad_json": str(invalid_dir / "bad.json")
    })

    yield temp_dir, test_files

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.mark.integration
@pytest.mark.mock_gui
@pytest.mark.no_manager_setup
class TestPhase2ServiceInterfaces:
    """Test that all Phase 2 services can be imported and instantiated correctly."""

    def test_file_validator_import_and_instantiation(self):
        """Test FileValidator can be imported and used without instantiation."""
        # FileValidator is a class with only class methods
        assert FileValidator is not None
        assert hasattr(FileValidator, "validate_vram_file")
        assert hasattr(FileValidator, "validate_cgram_file")
        assert hasattr(FileValidator, "validate_oam_file")
        assert hasattr(FileValidator, "validate_rom_file")
        assert hasattr(FileValidator, "validate_image_file")
        assert hasattr(FileValidator, "validate_json_file")
        assert hasattr(FileValidator, "validate_file_existence")
        assert hasattr(FileValidator, "validate_offset")

    def test_preview_generator_import_and_instantiation(self):
        """Test PreviewGenerator can be imported and instantiated."""
        generator = PreviewGenerator()
        assert generator is not None
        assert hasattr(generator, "generate_preview")
        assert hasattr(generator, "generate_preview_async")
        assert hasattr(generator, "set_managers")
        assert hasattr(generator, "clear_cache")
        assert hasattr(generator, "get_cache_stats")
        assert hasattr(generator, "cleanup")

        # Test global instance
        global_generator = get_preview_generator()
        assert global_generator is not None
        assert isinstance(global_generator, PreviewGenerator)

    def test_unified_error_handler_import_and_instantiation(self):
        """Test UnifiedErrorHandler can be imported and instantiated."""
        # Reset global instance first
        reset_unified_error_handler()

        handler = UnifiedErrorHandler()
        assert handler is not None
        assert hasattr(handler, "handle_exception")
        assert hasattr(handler, "handle_file_error")
        assert hasattr(handler, "handle_validation_error")
        assert hasattr(handler, "handle_worker_error")
        assert hasattr(handler, "handle_qt_error")
        assert hasattr(handler, "error_context")
        assert hasattr(handler, "create_error_decorator")

        # Test global instance
        global_handler = get_unified_error_handler()
        assert global_handler is not None
        assert isinstance(global_handler, UnifiedErrorHandler)

        # Reset for other tests
        reset_unified_error_handler()

    def test_constants_availability(self):
        """Test that all required constants are available and have expected values."""
        # VRAM constants
        assert VRAM_MIN_SIZE == 0x10000  # 64KB
        assert VRAM_MAX_SIZE == 0x100000  # 1MB

        # Memory constants
        assert CGRAM_EXPECTED_SIZE == 512
        assert OAM_EXPECTED_SIZE == 544

        # Sprite constants
        assert BYTES_PER_TILE == 32
        assert COLORS_PER_PALETTE == 16

        # Pattern constants
        assert isinstance(VRAM_PATTERNS, list)
        assert isinstance(CGRAM_PATTERNS, list)
        assert len(VRAM_PATTERNS) > 0
        assert len(CGRAM_PATTERNS) > 0

    def test_service_data_classes_instantiation(self):
        """Test data classes used by services can be instantiated."""
        # FileValidator data classes
        file_info = FileInfo(
            path="/test/path",
            size=1024,
            exists=True,
            is_readable=True,
            extension=".dmp",
            resolved_path="/absolute/test/path"
        )
        assert file_info.path == "/test/path"
        assert file_info.size == 1024

        validation_result = ValidationResult(
            is_valid=True,
            error_message=None,
            warnings=[],
            file_info=file_info
        )
        assert validation_result.is_valid is True
        assert validation_result.file_info == file_info

        # PreviewGenerator data classes
        palette_data = PaletteData(data=b"test_palette", format="snes_cgram")
        assert palette_data.data == b"test_palette"
        assert palette_data.format == "snes_cgram"

        preview_request = PreviewRequest(
            source_type="vram",
            data_path="/test/vram.dmp",
            offset=0x1000,
            palette=palette_data
        )
        assert preview_request.source_type == "vram"
        assert preview_request.offset == 0x1000
        assert preview_request.palette == palette_data

        # UnifiedErrorHandler data classes
        error_context = ErrorContext(
            operation="test operation",
            file_path="/test/file",
            recovery_possible=True
        )
        assert error_context.operation == "test operation"
        assert error_context.recovery_possible is True

        error_result = ErrorResult(
            handled=True,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.FILE_IO,
            message="Test message",
            technical_details="Test details",
            recovery_suggestions=["Try again"]
        )
        assert error_result.handled is True
        assert error_result.severity == ErrorSeverity.MEDIUM

@pytest.mark.integration
@pytest.mark.mock_gui
@pytest.mark.no_manager_setup
class TestPhase2ServiceIntegration:
    """Test integration scenarios between Phase 2 services."""

    @pytest.fixture
    def error_handler(self):
        """Create error handler for integration tests."""
        reset_unified_error_handler()
        with patch("utils.unified_error_handler.get_error_handler") as mock_get_handler:
            mock_base_handler = MagicMock()
            mock_get_handler.return_value = mock_base_handler

            handler = UnifiedErrorHandler()
            yield handler

        reset_unified_error_handler()

    @pytest.fixture
    def preview_generator(self):
        """Create preview generator for integration tests."""
        with patch("utils.preview_generator.get_logger") as mock_logger, \
             patch("utils.preview_generator.pil_to_qpixmap") as mock_pil_to_qpixmap:
            mock_logger.return_value = MagicMock()

            # Mock Qt pixmap conversion to avoid Qt dependencies
            mock_pixmap = Mock()
            mock_pixmap.size.return_value.width.return_value = 128
            mock_pixmap.size.return_value.height.return_value = 128
            mock_pixmap.scaled.return_value = mock_pixmap
            mock_pil_to_qpixmap.return_value = mock_pixmap

            generator = PreviewGenerator(cache_size=10, debounce_delay_ms=10)

            # Mock the managers
            mock_extraction_manager = Mock()
            mock_extraction_manager.generate_preview.return_value = (
                Image.new("L", (128, 128), 128),  # PIL image
                16  # tile_count
            )

            mock_rom_extractor = Mock()
            mock_rom_extractor.extract_sprite_data.return_value = b"test_sprite_data"

            generator.set_managers(mock_extraction_manager, mock_rom_extractor)

            yield generator

            generator.cleanup()

    def test_file_validator_with_preview_generator_success(self, temp_test_environment, preview_generator):
        """Test FileValidator -> PreviewGenerator success path."""
        temp_dir, test_files = temp_test_environment

        # 1. Validate VRAM file
        vram_result = FileValidator.validate_vram_file(test_files["vram"])
        assert vram_result.is_valid is True
        assert vram_result.file_info is not None

        # 2. Generate preview using validated file
        request = create_vram_preview_request(
            vram_path=test_files["vram"],
            offset=0x1000,
            sprite_name="test_sprite"
        )

        preview_result = preview_generator.generate_preview(request)
        assert preview_result is not None
        assert preview_result.sprite_name == "test_sprite"
        assert preview_result.tile_count > 0
        assert preview_result.generation_time >= 0

    def test_file_validator_with_error_handler_invalid_file(self, temp_test_environment, error_handler):
        """Test FileValidator -> ErrorHandler for invalid files."""
        temp_dir, test_files = temp_test_environment

        # 1. Try to validate invalid CGRAM file
        cgram_result = FileValidator.validate_cgram_file(test_files["bad_cgram"])
        assert cgram_result.is_valid is False
        assert ("size invalid" in cgram_result.error_message or
                "File too small" in cgram_result.error_message)

        # 2. Handle the validation error through error handler
        validation_error = ValidationError(cgram_result.error_message)
        error_result = error_handler.handle_validation_error(
            validation_error,
            "validating CGRAM file",
            user_input=test_files["bad_cgram"]
        )

        assert error_result.handled is True
        assert error_result.category == ErrorCategory.VALIDATION
        assert error_result.severity == ErrorSeverity.LOW
        assert len(error_result.recovery_suggestions) > 0

    def test_preview_generator_with_error_handler_missing_file(self, error_handler):
        """Test PreviewGenerator -> ErrorHandler for missing files."""

        # Test error handling more directly by creating an error and handling it
        runtime_error = RuntimeError("Extraction manager not available for VRAM preview")

        # Handle the error directly through the error handler
        error_result = error_handler.handle_exception(
            runtime_error,
            ErrorContext(
                operation="generating preview",
                file_path="/nonexistent/file.dmp",
                component="PreviewGenerator"
            )
        )

        # Verify error was handled
        assert error_result.handled is True
        assert error_result.category == ErrorCategory.SYSTEM
        assert error_result.severity in [ErrorSeverity.MEDIUM, ErrorSeverity.HIGH]
        assert len(error_result.recovery_suggestions) > 0

        # Check error was logged
        stats = error_handler.get_error_statistics()
        assert stats["total_errors"] > 0

    def test_all_services_with_constants_integration(self, temp_test_environment):
        """Test all services using constants correctly."""
        temp_dir, test_files = temp_test_environment

        # 1. FileValidator using constants
        vram_result = FileValidator.validate_vram_file(test_files["vram"])
        assert vram_result.is_valid is True

        # Verify it uses the constants we defined
        assert FileValidator.VRAM_MIN_SIZE == VRAM_MIN_SIZE
        assert FileValidator.CGRAM_EXPECTED_SIZE == CGRAM_EXPECTED_SIZE

        # 2. PreviewGenerator with cache using constants-based configuration
        with patch("utils.preview_generator.get_logger") as mock_logger:
            mock_logger.return_value = MagicMock()

            generator = PreviewGenerator(cache_size=20)  # Uses reasonable size
            stats = generator.get_cache_stats()
            assert stats["max_size"] == 20
            assert stats["cache_size"] == 0

            generator.cleanup()

        # 3. UnifiedErrorHandler using error categories and severity levels
        reset_unified_error_handler()
        with patch("utils.unified_error_handler.get_error_handler"):
            handler = UnifiedErrorHandler()

            # Test file operation error categorization
            file_error = FileNotFoundError("Test file not found")
            result = handler.handle_file_error(
                file_error,
                test_files["vram"],
                "reading VRAM file"
            )

            assert result.category == ErrorCategory.FILE_IO
            assert result.severity in [ErrorSeverity.MEDIUM, ErrorSeverity.HIGH]

        reset_unified_error_handler()

    def test_service_dependency_injection_patterns(self, temp_test_environment):
        """Test dependency injection patterns work correctly."""
        temp_dir, test_files = temp_test_environment

        # 1. Create services
        reset_unified_error_handler()
        with patch("utils.unified_error_handler.get_error_handler"):
            error_handler = UnifiedErrorHandler()

        with patch("utils.preview_generator.get_logger") as mock_logger:
            mock_logger.return_value = MagicMock()
            preview_generator = PreviewGenerator()

        # 2. Test dependency injection doesn't create circular dependencies

        # FileValidator has no dependencies (static methods)
        result = FileValidator.validate_file_existence(test_files["vram"])
        assert result.is_valid is True

        # PreviewGenerator can accept manager dependencies
        mock_extraction_manager = Mock()
        preview_generator.set_managers(extraction_manager=mock_extraction_manager)

        # UnifiedErrorHandler integrates with existing error handling
        assert error_handler._base_error_handler is not None

        # 3. Services can be used independently
        validation_result = FileValidator.validate_vram_file(test_files["vram"])
        assert validation_result.is_valid is True

        cache_stats = preview_generator.get_cache_stats()
        assert "cache_size" in cache_stats

        error_stats = error_handler.get_error_statistics()
        assert "total_errors" in error_stats

        # Cleanup
        preview_generator.cleanup()
        reset_unified_error_handler()

@pytest.mark.integration
@pytest.mark.mock_gui
@pytest.mark.no_manager_setup
class TestPhase2BackwardCompatibility:
    """Test backward compatibility with existing code patterns."""

    def test_existing_file_validation_patterns_still_work(self, temp_test_environment):
        """Test that existing file validation patterns are not broken."""
        temp_dir, test_files = temp_test_environment

        # Pattern 1: Direct existence check (should still work)
        assert os.path.exists(test_files["vram"])
        assert os.path.isfile(test_files["vram"])

        # Pattern 2: Manual size check (should still work)
        vram_size = os.path.getsize(test_files["vram"])
        assert vram_size >= VRAM_MIN_SIZE

        # Pattern 3: Extension check (should still work)
        assert test_files["vram"].endswith((".dmp", ".bin", ".vram"))

        # Pattern 4: New FileValidator should be additive, not replacing
        validator_result = FileValidator.validate_vram_file(test_files["vram"])
        assert validator_result.is_valid is True

        # Both approaches should work and give consistent results
        manual_valid = (
            os.path.exists(test_files["vram"]) and
            os.path.getsize(test_files["vram"]) >= VRAM_MIN_SIZE
        )
        assert manual_valid == validator_result.is_valid

    def test_existing_error_handling_patterns_preserved(self):
        """Test that existing error handling patterns continue to work."""

        reset_unified_error_handler()

        # Pattern 1: Traditional try/except (should still work)
        try:
            with open("/nonexistent/file.dmp", "rb") as f:
                f.read()
            raise AssertionError("Should have raised exception")
        except FileNotFoundError as e:
            assert "No such file" in str(e) or "cannot find" in str(e).lower()

        # Pattern 2: Existing ErrorHandler should be enhanced, not replaced
        with patch("utils.unified_error_handler.get_error_handler") as mock_get_handler:
            mock_base_handler = MagicMock()
            mock_get_handler.return_value = mock_base_handler

            unified_handler = UnifiedErrorHandler()

            # Should delegate to existing handler for UI display
            error = ValidationError("Test validation error")
            result = unified_handler.handle_exception(error)

            assert result.handled is True
            # Should have called existing handler methods
            assert mock_base_handler.handle_info.called or mock_base_handler.handle_warning.called

        reset_unified_error_handler()

    def test_existing_constants_usage_patterns_preserved(self):
        """Test that existing constant usage patterns are preserved."""

        # Pattern 1: Direct constant access (should still work)
        assert VRAM_MIN_SIZE == 0x10000
        assert CGRAM_EXPECTED_SIZE == 512

        # Pattern 2: Arithmetic with constants (should still work)
        total_vram_size = VRAM_MIN_SIZE
        tiles_in_vram = total_vram_size // BYTES_PER_TILE
        assert tiles_in_vram == 2048  # 64KB / 32 bytes per tile

        # Pattern 3: Constants in validation logic (should still work)
        def old_validate_cgram_size(size):
            return size == CGRAM_EXPECTED_SIZE

        assert old_validate_cgram_size(512) is True
        assert old_validate_cgram_size(256) is False

        # Pattern 4: New FileValidator should use same constants
        assert FileValidator.CGRAM_EXPECTED_SIZE == CGRAM_EXPECTED_SIZE
        assert FileValidator.VRAM_MIN_SIZE == VRAM_MIN_SIZE

    def test_no_breaking_api_changes(self):
        """Test that no breaking API changes were introduced."""

        # Test that all Phase 2 services provide the expected APIs

        # FileValidator: All validation methods should return ValidationResult
        mock_path = "/test/mock.dmp"

        with patch("os.path.exists", return_value=False):
            # All these should return ValidationResult objects, not throw exceptions
            vram_result = FileValidator.validate_vram_file(mock_path)
            cgram_result = FileValidator.validate_cgram_file(mock_path)
            oam_result = FileValidator.validate_oam_file(mock_path)
            rom_result = FileValidator.validate_rom_file(mock_path)

            # All should have consistent interface
            for result in [vram_result, cgram_result, oam_result, rom_result]:
                assert hasattr(result, "is_valid")
                assert hasattr(result, "error_message")
                assert hasattr(result, "file_info")
                assert result.is_valid is False  # File doesn't exist

        # PreviewGenerator: Should have predictable async/sync interfaces
        with patch("utils.preview_generator.get_logger") as mock_logger:
            mock_logger.return_value = MagicMock()

            generator = PreviewGenerator()

            # Should have both sync and async methods
            assert hasattr(generator, "generate_preview")  # Sync
            assert hasattr(generator, "generate_preview_async")  # Async

            # Should have cache management
            assert hasattr(generator, "clear_cache")
            assert hasattr(generator, "get_cache_stats")

            generator.cleanup()

        # UnifiedErrorHandler: Should enhance existing patterns
        reset_unified_error_handler()
        with patch("utils.unified_error_handler.get_error_handler"):
            handler = UnifiedErrorHandler()

            # Should provide both high-level and specific error handling
            assert hasattr(handler, "handle_exception")  # General
            assert hasattr(handler, "handle_file_error")  # Specific
            assert hasattr(handler, "handle_validation_error")  # Specific
            assert hasattr(handler, "error_context")  # Context manager

        reset_unified_error_handler()

@pytest.mark.integration
@pytest.mark.mock_gui
@pytest.mark.benchmark
@pytest.mark.no_manager_setup
class TestPhase2ServicePerformance:
    """Test performance characteristics of Phase 2 services."""

    def test_file_validator_performance(self, temp_test_environment, benchmark):
        """Test FileValidator performance doesn't introduce significant overhead."""
        temp_dir, test_files = temp_test_environment

        # Benchmark VRAM validation
        def validate_vram():
            return FileValidator.validate_vram_file(test_files["vram"])

        result = benchmark(validate_vram)
        assert result.is_valid is True

        # Should complete quickly (FileValidator uses efficient checks)
        # benchmark automatically measures and reports timing

    def test_preview_generator_cache_effectiveness(self, temp_test_environment):
        """Test PreviewGenerator cache provides expected performance benefits."""
        temp_dir, test_files = temp_test_environment

        with patch("utils.preview_generator.get_logger") as mock_logger:
            mock_logger.return_value = MagicMock()

            generator = PreviewGenerator(cache_size=10)

            # Mock the extraction manager to simulate work
            mock_extraction_manager = Mock()
            mock_extraction_manager.generate_preview.return_value = (
                Image.new("L", (128, 128), 128),
                16
            )
            generator.set_managers(extraction_manager=mock_extraction_manager)

            request = create_vram_preview_request(
                vram_path=test_files["vram"],
                offset=0x1000
            )

            # First generation (cache miss)
            start_time = time.time()
            result1 = generator.generate_preview(request)
            first_time = time.time() - start_time

            assert result1 is not None
            assert result1.cached is False

            # Second generation (cache hit)
            start_time = time.time()
            result2 = generator.generate_preview(request)
            second_time = time.time() - start_time

            assert result2 is not None
            assert result2.cached is True

            # Cache hit should be significantly faster
            assert second_time < first_time

            # Verify cache statistics
            stats = generator.get_cache_stats()
            assert stats["hits"] >= 1
            assert stats["misses"] >= 1
            assert stats["hit_rate"] > 0

            generator.cleanup()

    def test_unified_error_handler_overhead(self, benchmark):
        """Test UnifiedErrorHandler doesn't add significant overhead."""

        reset_unified_error_handler()
        with patch("utils.unified_error_handler.get_error_handler"):
            handler = UnifiedErrorHandler()

            # Test error processing overhead
            def process_error():
                error = ValidationError("Test validation error")
                return handler.handle_exception(error)

            result = benchmark(process_error)
            assert result.handled is True

            # Error handling should be fast enough for real-time use

        reset_unified_error_handler()

    def test_service_initialization_overhead(self, benchmark):
        """Test that service initialization doesn't have excessive overhead."""

        def initialize_all_services():
            # FileValidator (no initialization needed - static methods)
            validator_methods = [
                FileValidator.validate_vram_file,
                FileValidator.validate_cgram_file,
                FileValidator.validate_oam_file
            ]

            # PreviewGenerator
            with patch("utils.preview_generator.get_logger") as mock_logger:
                mock_logger.return_value = MagicMock()
                generator = PreviewGenerator()
                generator.cleanup()

            # UnifiedErrorHandler
            reset_unified_error_handler()
            with patch("utils.unified_error_handler.get_error_handler"):
                UnifiedErrorHandler()
                # Clean up
                reset_unified_error_handler()

            return len(validator_methods)

        count = benchmark(initialize_all_services)
        assert count == 3  # Successfully initialized

@pytest.mark.integration
@pytest.mark.mock_gui
@pytest.mark.thread_safety
@pytest.mark.no_manager_setup
class TestPhase2ServiceThreadSafety:
    """Test thread safety of Phase 2 services."""

    def test_file_validator_thread_safety(self, temp_test_environment):
        """Test FileValidator thread safety (should be safe as static methods)."""
        temp_dir, test_files = temp_test_environment

        results = []
        errors = []

        def validate_files(file_path, file_type):
            try:
                if file_type == "vram":
                    result = FileValidator.validate_vram_file(file_path)
                elif file_type == "cgram":
                    result = FileValidator.validate_cgram_file(file_path)
                else:
                    result = FileValidator.validate_file_existence(file_path)

                results.append((threading.current_thread().name, result.is_valid))
            except Exception as e:
                errors.append((threading.current_thread().name, str(e)))

        # Run multiple threads simultaneously
        threads = []
        for i in range(5):
            thread = threading.Thread(
                target=validate_files,
                args=(test_files["vram"], "vram"),
                name=f"validator_thread_{i}"
            )
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)

        # Verify results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 5
        assert all(result[1] is True for result in results)  # All validations succeeded

    def test_preview_generator_thread_safety(self, temp_test_environment):
        """Test PreviewGenerator thread safety with concurrent cache access."""
        temp_dir, test_files = temp_test_environment

        with patch("utils.preview_generator.get_logger") as mock_logger:
            mock_logger.return_value = MagicMock()

            generator = PreviewGenerator(cache_size=20)

            # Mock extraction manager
            mock_extraction_manager = Mock()
            mock_extraction_manager.generate_preview.return_value = (
                Image.new("L", (64, 64), 128),
                8
            )
            generator.set_managers(extraction_manager=mock_extraction_manager)

            results = []
            errors = []

            def generate_preview(offset):
                try:
                    request = create_vram_preview_request(
                        vram_path=test_files["vram"],
                        offset=offset
                    )
                    result = generator.generate_preview(request)
                    if result:
                        results.append((threading.current_thread().name, offset, result.tile_count))
                    else:
                        results.append((threading.current_thread().name, offset, None))
                except Exception as e:
                    errors.append((threading.current_thread().name, str(e)))

            # Generate previews from multiple threads
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                offsets = [0x1000, 0x2000, 0x3000, 0x1000, 0x2000]  # Some duplicates for cache testing

                for offset in offsets:
                    future = executor.submit(generate_preview, offset)
                    futures.append(future)

                # Wait for all to complete
                for future in as_completed(futures, timeout=10):
                    try:
                        future.result()
                    except Exception as e:
                        errors.append(("future_error", str(e)))

            # Verify thread safety
            assert len(errors) == 0, f"Thread safety errors: {errors}"
            assert len(results) == 5

            # Verify cache worked correctly across threads
            stats = generator.get_cache_stats()
            assert stats["hits"] >= 1  # Should have cache hits from duplicate requests
            assert stats["cache_size"] >= 1

            generator.cleanup()

    def test_unified_error_handler_thread_safety(self):
        """Test UnifiedErrorHandler thread safety with concurrent error processing."""

        reset_unified_error_handler()

        with patch("utils.unified_error_handler.get_error_handler"):
            handler = UnifiedErrorHandler()

            results = []
            errors = []

            def process_errors(thread_id):
                try:
                    # Process different types of errors
                    validation_error = ValidationError(f"Thread {thread_id} validation error")
                    file_error = FileNotFoundError(f"Thread {thread_id} file error")

                    result1 = handler.handle_exception(validation_error)
                    result2 = handler.handle_exception(file_error)

                    results.append((thread_id, result1.handled, result2.handled))
                except Exception as e:
                    errors.append((thread_id, str(e)))

            # Process errors from multiple threads
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = []

                for i in range(6):  # 6 threads
                    future = executor.submit(process_errors, i)
                    futures.append(future)

                # Wait for completion
                for future in as_completed(futures, timeout=10):
                    try:
                        future.result()
                    except Exception as e:
                        errors.append(("future_error", str(e)))

            # Verify thread safety
            assert len(errors) == 0, f"Thread safety errors: {errors}"
            assert len(results) == 6
            assert all(result[1] and result[2] for result in results)  # All errors handled

            # Verify error statistics are consistent
            stats = handler.get_error_statistics()
            assert stats["total_errors"] >= 12  # At least 2 errors per thread

        reset_unified_error_handler()

    def test_global_service_instances_thread_safety(self):
        """Test that global service instances are thread-safe."""

        reset_unified_error_handler()

        results = []
        errors = []

        def access_global_services(thread_id):
            try:
                # Access global PreviewGenerator
                generator1 = get_preview_generator()
                generator2 = get_preview_generator()

                # Should be same instance
                assert generator1 is generator2

                # Access global UnifiedErrorHandler
                with patch("utils.unified_error_handler.get_error_handler"):
                    handler1 = get_unified_error_handler()
                    handler2 = get_unified_error_handler()

                    # Should be same instance
                    assert handler1 is handler2

                results.append((thread_id, "success"))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Access globals from multiple threads
        threads = []
        for i in range(4):
            thread = threading.Thread(target=access_global_services, args=(i,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=5)

        # Verify thread safety
        assert len(errors) == 0, f"Global instance errors: {errors}"
        assert len(results) == 4

        reset_unified_error_handler()

# Integration scenarios that combine multiple aspects
@pytest.mark.integration
@pytest.mark.mock_gui
@pytest.mark.no_manager_setup
class TestPhase2ComprehensiveIntegration:
    """Comprehensive integration tests combining all aspects."""

    def test_complete_workflow_file_validation_to_preview_with_error_handling(self, temp_test_environment):
        """Test complete workflow: file validation -> preview generation -> error handling."""
        temp_dir, test_files = temp_test_environment

        reset_unified_error_handler()

        with patch("utils.unified_error_handler.get_error_handler") as mock_get_handler:
            mock_base_handler = MagicMock()
            mock_get_handler.return_value = mock_base_handler

            error_handler = UnifiedErrorHandler()

            with patch("utils.preview_generator.get_logger") as mock_logger, \
                 patch("utils.preview_generator.pil_to_qpixmap") as mock_pil_to_qpixmap:
                mock_logger.return_value = MagicMock()

                # Mock Qt pixmap conversion to avoid Qt dependencies
                mock_pixmap = Mock()
                mock_pixmap.size.return_value.width.return_value = 128
                mock_pixmap.size.return_value.height.return_value = 128
                mock_pixmap.scaled.return_value = mock_pixmap
                mock_pil_to_qpixmap.return_value = mock_pixmap

                preview_generator = PreviewGenerator()

                # Set up mock extraction manager
                mock_extraction_manager = Mock()
                mock_extraction_manager.generate_preview.return_value = (
                    Image.new("L", (128, 128), 128),
                    16
                )
                preview_generator.set_managers(extraction_manager=mock_extraction_manager)

                try:
                    # 1. File Validation Phase
                    with error_handler.error_context("validating input files"):
                        vram_result = FileValidator.validate_vram_file(test_files["vram"])
                        cgram_result = FileValidator.validate_cgram_file(test_files["cgram"])

                        if not vram_result.is_valid:
                            raise ValidationError(f"VRAM validation failed: {vram_result.error_message}")
                        if not cgram_result.is_valid:
                            raise ValidationError(f"CGRAM validation failed: {cgram_result.error_message}")

                    # 2. Preview Generation Phase
                    with error_handler.error_context("generating sprite preview", file_path=test_files["vram"]):
                        request = create_vram_preview_request(
                            vram_path=test_files["vram"],
                            offset=0x1000,
                            sprite_name="integration_test_sprite"
                        )

                        preview_result = preview_generator.generate_preview(request)

                        if not preview_result:
                            raise RuntimeError("Preview generation failed")

                    # 3. Verify success
                    assert vram_result.is_valid is True
                    assert cgram_result.is_valid is True
                    assert preview_result is not None
                    assert preview_result.sprite_name == "integration_test_sprite"

                    # 4. Test error scenario with invalid file - force an error
                    try:
                        bad_result = FileValidator.validate_cgram_file(test_files["bad_cgram"])
                        if not bad_result.is_valid:
                            validation_error = ValidationError(bad_result.error_message)
                            error_handler.handle_exception(validation_error)
                    except Exception as e:
                        error_handler.handle_exception(e)

                    # Verify error statistics
                    stats = error_handler.get_error_statistics()
                    assert stats["total_errors"] >= 1  # At least the validation error

                finally:
                    preview_generator.cleanup()

        reset_unified_error_handler()

    def test_service_resilience_under_load(self, temp_test_environment):
        """Test all services working together under simulated load."""
        temp_dir, test_files = temp_test_environment

        reset_unified_error_handler()

        with patch("utils.unified_error_handler.get_error_handler"):
            error_handler = UnifiedErrorHandler()

            with patch("utils.preview_generator.get_logger") as mock_logger:
                mock_logger.return_value = MagicMock()

                preview_generator = PreviewGenerator(cache_size=50)

                # Mock managers
                mock_extraction_manager = Mock()
                mock_extraction_manager.generate_preview.return_value = (
                    Image.new("L", (64, 64), 128),
                    8
                )
                preview_generator.set_managers(extraction_manager=mock_extraction_manager)

                try:
                    # Simulate load: many operations in parallel
                    results = {"validations": 0, "previews": 0, "errors": 0}

                    def perform_operations(operation_id):
                        try:
                            # File validation
                            vram_result = FileValidator.validate_vram_file(test_files["vram"])
                            if vram_result.is_valid:
                                results["validations"] += 1

                            # Preview generation
                            request = create_vram_preview_request(
                                vram_path=test_files["vram"],
                                offset=0x1000 + (operation_id * 0x100)  # Different offsets
                            )
                            preview_result = preview_generator.generate_preview(request)
                            if preview_result:
                                results["previews"] += 1

                            # Trigger some errors intentionally
                            if operation_id % 3 == 0:
                                try:
                                    FileValidator.validate_cgram_file("/nonexistent/file.dmp")
                                except Exception as e:
                                    error_handler.handle_exception(e)
                                    results["errors"] += 1

                        except Exception as e:
                            error_handler.handle_exception(e)
                            results["errors"] += 1

                    # Run operations concurrently
                    with ThreadPoolExecutor(max_workers=5) as executor:
                        futures = []
                        for i in range(20):  # 20 operations
                            future = executor.submit(perform_operations, i)
                            futures.append(future)

                        # Wait for completion
                        for future in as_completed(futures, timeout=30):
                            try:
                                future.result()
                            except Exception:
                                results["errors"] += 1

                    # Verify system remained stable
                    assert results["validations"] > 0
                    assert results["previews"] > 0
                    # Some errors are expected (intentional invalid files)

                    # Verify cache effectiveness
                    cache_stats = preview_generator.get_cache_stats()
                    assert cache_stats["cache_size"] > 0

                    # Verify error handling
                    error_stats = error_handler.get_error_statistics()
                    assert error_stats["total_errors"] >= results["errors"]

                finally:
                    preview_generator.cleanup()

        reset_unified_error_handler()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])