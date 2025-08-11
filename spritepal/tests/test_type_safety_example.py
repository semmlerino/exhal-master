# pyright: basic  # Less strict for test files
# pyright: reportPrivateUsage=false  # Allow testing private methods
# pyright: reportUnknownMemberType=warning  # Mock attributes are dynamic
# pyright: reportUnknownArgumentType=warning  # Test data may be dynamic

"""
Type-safe test example demonstrating best practices for SpritePal tests.

This module shows proper patterns for:
- Using real objects over mocks when possible
- Type-safe mock creation with protocols
- Proper use of pyright ignore comments
- Qt signal testing with proper types
- Fixture typing and dependency injection
"""

from collections.abc import Generator
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock, Mock

import pytest

if TYPE_CHECKING:
    from tests.infrastructure.test_protocols import (
        MockExtractionManagerProtocol,
        MockMainWindowProtocol,
        MockQtBotProtocol,
    )

# Test markers for proper classification
pytestmark = [
    pytest.mark.headless,  # Safe for headless environments
    pytest.mark.unit,      # Fast unit tests
    pytest.mark.mock_only, # Uses only mocks
    pytest.mark.parallel_safe,  # Safe for parallel execution
]


class TestTypeSafetyPatterns:
    """Demonstrate type-safe testing patterns."""

    def test_real_object_preference(self) -> None:
        """Demonstrate using real objects over mocks when possible."""
        # PREFER: Real objects for better type safety and test confidence
        test_data = {
            "vram_path": "test.dmp",
            "cgram_path": "test_cgram.dmp", 
            "output_base": "test_sprites",
            "create_grayscale": True,
        }
        
        # Real validation logic - no mocks needed
        assert isinstance(test_data["vram_path"], str)
        assert test_data["create_grayscale"] is True
        
        # Type checker knows these are the correct types
        vram_path: str = test_data["vram_path"]
        create_grayscale: bool = test_data["create_grayscale"]
        
        assert len(vram_path) > 0
        assert create_grayscale

    def test_typed_mock_usage(
        self, 
        mock_main_window: "MockMainWindowProtocol"
    ) -> None:
        """Demonstrate type-safe mock usage with protocols."""
        # Mock is properly typed via protocol
        mock_main_window.get_extraction_params.return_value = {  # pyright: ignore[reportUnknownMemberType]
            "vram_path": "test.dmp",
            "output_base": "sprites"
        }
        
        # Type checker knows the interface
        result = mock_main_window.get_extraction_params()
        assert isinstance(result, dict)
        assert "vram_path" in result
        
        # Signal testing with proper types
        mock_main_window.extract_requested.emit("test_signal")  # pyright: ignore[reportUnknownMemberType]
        mock_main_window.extract_requested.assert_any_call("test_signal")  # pyright: ignore[reportUnknownMemberType]

    def test_qt_signal_type_safety(self, safe_qtbot: "MockQtBotProtocol") -> None:
        """Demonstrate type-safe Qt signal testing."""
        # Create a real Qt object for signal testing when possible
        from unittest.mock import Mock
        
        # Mock object with typed signals
        test_object = Mock()
        test_object.data_changed = MagicMock()
        
        # Type-safe signal spy setup
        safe_qtbot.addWidget(test_object)
        
        # Emit signal with known types
        test_object.data_changed.emit("test_data")  # pyright: ignore[reportUnknownMemberType]
        
        # Verify with type safety
        test_object.data_changed.assert_called_once_with("test_data")  # pyright: ignore[reportUnknownMemberType]

    def test_proper_type_ignore_usage(self) -> None:
        """Demonstrate proper use of pyright ignore comments."""
        mock_service = Mock()
        
        # GOOD: Specific pyright rule for Mock dynamic attributes
        mock_service.dynamic_method.return_value = "test"  # pyright: ignore[reportUnknownMemberType]
        
        # GOOD: Document why ignore is needed
        mock_service.side_effect = ValueError("Test error")  # pyright: ignore[reportUnknownMemberType]  # Mock-specific attribute
        
        result = mock_service.dynamic_method()
        assert result == "test"

    def test_manager_dependency_injection(
        self,
        mock_extraction_manager: "MockExtractionManagerProtocol"
    ) -> None:
        """Demonstrate type-safe manager dependency injection."""
        # Manager is properly typed via protocol
        mock_extraction_manager.validate_extraction_params.return_value = True  # pyright: ignore[reportUnknownMemberType]
        
        # Type checker knows the interface
        is_valid = mock_extraction_manager.validate_extraction_params({
            "vram_path": "test.dmp",
            "output_base": "sprites"
        })
        
        assert is_valid is True
        mock_extraction_manager.validate_extraction_params.assert_called_once()  # pyright: ignore[reportUnknownMemberType]

    @pytest.mark.parametrize(
        "input_value,expected_type,expected_result",
        [
            ("valid_string", str, True),
            (42, int, True),
            (None, type(None), False),
        ],
        ids=["string_input", "int_input", "none_input"]
    )
    def test_parametrized_with_types(
        self, 
        input_value: str | int | None,
        expected_type: type[str] | type[int] | type[None],
        expected_result: bool
    ) -> None:
        """Demonstrate type-safe parametrized testing."""
        # Type checker knows the parameter types
        assert isinstance(input_value, expected_type) == expected_result
        
        if input_value is not None:
            # Type narrowing works properly
            assert len(str(input_value)) > 0


class TestAsyncTypePatterns:
    """Demonstrate type-safe async testing patterns."""

    @pytest.mark.asyncio
    async def test_async_operation_typing(self) -> None:
        """Demonstrate type-safe async testing."""
        from asyncio import sleep
        
        # Real async operation - no mocking needed
        await sleep(0.01)
        
        # Type checker knows this is an async function
        result = await self._async_helper("test_data")
        assert result == "processed: test_data"

    async def _async_helper(self, data: str) -> str:
        """Helper method with proper async typing."""
        await sleep(0.001)  # Simulate async work
        return f"processed: {data}"


class TestContextManagerPatterns:
    """Demonstrate type-safe context manager testing."""

    def test_resource_management(self, tmp_path: Any) -> None:  # pytest tmp_path fixture
        """Demonstrate type-safe resource management in tests."""
        test_file = tmp_path / "test_data.txt"
        
        # Real file operations - better than mocking
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("test data")
        
        # Type checker knows file operations
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert content == "test data"


class TestFixtureTypeSafety:
    """Demonstrate type-safe fixture usage."""

    @pytest.fixture
    def typed_test_data(self) -> dict[str, str | bool]:
        """Provide properly typed test data."""
        return {
            "rom_path": "test.sfc",
            "output_dir": "/tmp/output", 
            "create_metadata": True,
        }

    @pytest.fixture  
    def real_extraction_params(self, typed_test_data: dict[str, str | bool]) -> dict[str, Any]:
        """Create real extraction parameters - prefer over mocked ones."""
        return {
            **typed_test_data,
            "sprite_mode": "8x8",
            "palette_count": 8,
        }

    def test_fixture_type_safety(
        self, 
        real_extraction_params: dict[str, Any]
    ) -> None:
        """Test using type-safe fixtures."""
        # Type checker knows the structure
        assert isinstance(real_extraction_params["rom_path"], str)
        assert isinstance(real_extraction_params["create_metadata"], bool)
        
        # Real validation instead of mocked validation
        rom_path: str = real_extraction_params["rom_path"]
        assert rom_path.endswith(('.sfc', '.smc'))


# Factory pattern for type-safe test objects
class TypeSafeTestFactory:
    """Factory for creating type-safe test objects."""
    
    @staticmethod
    def create_test_extraction_request() -> dict[str, Any]:
        """Create a properly typed extraction request."""
        return {
            "vram_path": "test_vram.dmp",
            "cgram_path": "test_cgram.dmp", 
            "oam_path": "test_oam.dmp",
            "output_base": "test_sprites",
            "sprite_mode": "8x8",
            "create_grayscale": True,
            "create_metadata": False,
        }
    
    @staticmethod
    def create_mock_with_protocol() -> Mock:
        """Create a mock that conforms to a protocol."""
        mock = Mock()
        
        # Add required methods with proper signatures
        mock.validate_params = Mock(return_value=True)
        mock.process_request = Mock(return_value={"status": "success"})
        
        return mock


# Integration test showing real vs mock patterns
class TestRealVsMockPatterns:
    """Compare real object usage vs mock patterns."""

    def test_prefer_real_objects(self) -> None:
        """Demonstrate preference for real objects."""
        # GOOD: Use real data structures
        test_config = {
            "input_files": ["vram.dmp", "cgram.dmp"],
            "output_directory": "/tmp/sprites",
            "options": {
                "create_grayscale": True,
                "export_metadata": False,
            }
        }
        
        # Real validation logic
        assert len(test_config["input_files"]) == 2
        assert test_config["options"]["create_grayscale"] is True
        
        # Type safety is guaranteed by real objects
        file_count: int = len(test_config["input_files"])
        output_dir: str = test_config["output_directory"]
        
        assert file_count > 0
        assert output_dir.startswith("/tmp")

    def test_mock_when_necessary(self) -> None:
        """Demonstrate mocking only when necessary (external dependencies)."""
        # MOCK: Only for external services, file I/O, or complex dependencies
        mock_file_system = Mock()
        mock_file_system.exists.return_value = True  # pyright: ignore[reportUnknownMemberType]
        mock_file_system.read_bytes.return_value = b"test data"  # pyright: ignore[reportUnknownMemberType]
        
        # Use mock only for external dependency
        assert mock_file_system.exists("test.file")  # pyright: ignore[reportUnknownMemberType]
        data = mock_file_system.read_bytes("test.file")  # pyright: ignore[reportUnknownMemberType]
        assert data == b"test data"

    def test_combined_real_and_mock(self) -> None:
        """Demonstrate combining real objects with strategic mocking."""
        # REAL: Domain logic and data structures
        sprite_data = {
            "width": 64,
            "height": 64, 
            "tile_data": bytearray(range(256)),
            "palette": list(range(16)),
        }
        
        # MOCK: Only external file operations
        mock_writer = Mock()
        mock_writer.write_sprite.return_value = "/tmp/sprite_001.png"  # pyright: ignore[reportUnknownMemberType]
        
        # Real validation with mocked I/O
        assert sprite_data["width"] == 64
        assert len(sprite_data["tile_data"]) == 256
        
        # Mock only the external dependency
        output_path = mock_writer.write_sprite(sprite_data)  # pyright: ignore[reportUnknownMemberType]
        assert output_path.endswith(".png")  # pyright: ignore[reportUnknownMemberType]


# Performance testing with proper typing
class TestPerformancePatterns:
    """Demonstrate type-safe performance testing."""

    @pytest.mark.benchmark
    def test_performance_with_real_objects(self, benchmark: Any) -> None:  # pytest-benchmark fixture
        """Test performance using real objects."""
        def create_test_data() -> dict[str, Any]:
            return {
                "sprites": [{"id": i, "data": bytearray(64)} for i in range(100)],
                "metadata": {"count": 100, "format": "8x8"},
            }
        
        # Benchmark real object creation
        result = benchmark(create_test_data)
        
        # Type-safe assertions
        assert isinstance(result["sprites"], list)
        assert len(result["sprites"]) == 100
        assert result["metadata"]["count"] == 100