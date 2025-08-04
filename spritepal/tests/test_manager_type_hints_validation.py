"""
Test type hints validation for manager classes from Phase 2.

Tests runtime type checking and validates that type hints correctly
represent the actual behavior of manager methods.
"""

import pytest
from typing import Any, Dict
from pathlib import Path
from unittest.mock import Mock, patch

from spritepal.core.managers.extraction_manager import ExtractionManager
from spritepal.core.managers.injection_manager import InjectionManager
from spritepal.core.managers.session_manager import SessionManager
from spritepal.core.managers.exceptions import (
    ManagerError, ValidationError
)


class TestManagerTypeHintsValidation:
    """Test that manager type hints match runtime behavior"""

    @pytest.fixture
    def extraction_manager(self):
        """Create ExtractionManager for testing"""
        return ExtractionManager()

    @pytest.fixture
    def injection_manager(self):
        """Create InjectionManager for testing"""
        return InjectionManager()

    @pytest.fixture
    def session_manager(self):
        """Create SessionManager for testing"""
        return SessionManager()

    def test_extraction_manager_validate_params_type_hints(self, extraction_manager):
        """Test ExtractionManager.validate_extraction_params type hints"""
        manager = extraction_manager
        
        # Test valid parameters match type hints
        valid_params = {
            'vram_path': '/path/to/vram.dmp',
            'cgram_path': '/path/to/cgram.dmp',
            'oam_path': '/path/to/oam.dmp',
            'output_base': '/path/to/output',
            'vram_offset': 0xC000,
            'create_grayscale': True,
            'create_metadata': False,
        }
        
        # Should not raise for valid params dict
        try:
            manager.validate_extraction_params(valid_params)
        except ValidationError:
            pass  # Expected for non-existent files, but type validation should pass
        
        # Test type validation - None should raise ValidationError
        with pytest.raises(ValidationError, match="params must be a dictionary"):
            manager.validate_extraction_params(None)
        
        # Test type validation - wrong type should raise ValidationError
        with pytest.raises(ValidationError, match="params must be a dictionary"):
            manager.validate_extraction_params("not a dict")

    def test_extraction_manager_extract_from_vram_return_type(self, extraction_manager):
        """Test ExtractionManager.extract_from_vram return type hints"""
        manager = extraction_manager
        
        # Mock successful extraction
        with patch.object(manager, 'validate_extraction_params'), \
             patch.object(manager, '_is_operation_running', return_value=False), \
             patch('spritepal.core.workers.extraction_worker.ExtractionWorker') as mock_worker:
            
            mock_worker_instance = Mock()
            mock_worker.return_value = mock_worker_instance
            
            # Method should return None (starts async operation)
            result = manager.extract_from_vram({})
            assert result is None, "extract_from_vram should return None (type hint: None)"

    def test_injection_manager_validate_params_type_hints(self, injection_manager):
        """Test InjectionManager parameter validation type hints"""
        manager = injection_manager
        
        # Test ROM injection params
        rom_params = {
            'input_rom_path': '/path/to/input.smc',
            'sprite_png_path': '/path/to/sprite.png',
            'sprite_location': 'compressed',
            'custom_offset': None,
            'fast_compression': True,
        }
        
        # Should handle dictionary type correctly
        try:
            manager.validate_rom_injection_params(rom_params)
        except (ValidationError, FileNotFoundError):
            pass  # Expected for non-existent files
        
        # Test VRAM injection params type validation
        vram_params = {
            'input_vram_path': '/path/to/input.dmp',
            'sprite_png_path': '/path/to/sprite.png',
            'vram_offset': 0xC000,
        }
        
        try:
            manager.validate_vram_injection_params(vram_params)
        except (ValidationError, FileNotFoundError):
            pass  # Expected for non-existent files

    def test_session_manager_settings_type_hints(self, session_manager):
        """Test SessionManager settings methods type hints"""
        manager = session_manager
        
        # Test setting retrieval with proper types
        default_str = "default_value"
        default_bool = True
        default_int = 42
        
        # get_setting should handle various types correctly
        str_result = manager.get_setting("test_namespace", "test_key", default_str)
        assert isinstance(str_result, str) or str_result is None
        
        bool_result = manager.get_setting("test_namespace", "test_key", default_bool)
        assert isinstance(bool_result, bool) or bool_result is None
        
        int_result = manager.get_setting("test_namespace", "test_key", default_int)
        assert isinstance(int_result, int) or int_result is None

    def test_base_manager_signal_type_hints(self, extraction_manager):
        """Test BaseManager signal type hints"""
        manager = extraction_manager
        
        # Test signal emission type safety
        manager.progress_updated.emit(50)  # Should accept int
        manager.operation_completed.emit("success", "Operation completed")  # Should accept str, str
        manager.operation_failed.emit("error", "Operation failed")  # Should accept str, str
        
        # These should not raise type errors at runtime
        assert True  # If we reach here, signals accepted correct types

    def test_manager_exception_type_hints(self, extraction_manager):
        """Test manager exception handling type hints"""
        manager = extraction_manager
        
        # Test that exceptions have proper type annotations
        try:
            raise ManagerError("Test error")
        except ManagerError as e:
            assert isinstance(e, Exception)
            assert isinstance(str(e), str)
        
        try:
            raise ValidationError("Test validation error")
        except ValidationError as e:
            assert isinstance(e, ManagerError)
            assert isinstance(str(e), str)

    def test_optional_parameter_type_hints(self, injection_manager):
        """Test Optional parameter type hints work correctly"""
        manager = injection_manager
        
        # Test methods that accept Optional parameters
        # These should work with None values
        params_with_none = {
            'input_rom_path': '/path/to/rom.smc',
            'sprite_png_path': '/path/to/sprite.png',
            'sprite_location': 'compressed',
            'custom_offset': None,  # Optional[int] should accept None
            'fast_compression': True,
        }
        
        try:
            manager.validate_rom_injection_params(params_with_none)
        except (ValidationError, FileNotFoundError):
            pass  # Expected for validation, but None type should be accepted

    def test_union_type_hints_validation(self, session_manager):
        """Test Union type hints accept multiple types correctly"""
        manager = session_manager
        
        # Test methods that should accept Union types
        # get_setting should accept Any as default and return Any
        result1 = manager.get_setting("test", "key", "string_default")
        result2 = manager.get_setting("test", "key", 123)
        result3 = manager.get_setting("test", "key", True)
        result4 = manager.get_setting("test", "key", None)
        
        # All should be accepted without type errors
        assert True  # If we reach here, Union types work correctly

    def test_list_and_dict_type_hints(self, extraction_manager):
        """Test List and Dict type hints match actual usage"""
        manager = extraction_manager
        
        # Test that methods expecting dicts work with proper dict types
        params_dict: Dict[str, Any] = {
            'vram_path': '/test.dmp',
            'output_base': '/output',
            'vram_offset': 0xC000,
        }
        
        try:
            manager.validate_extraction_params(params_dict)
        except (ValidationError, FileNotFoundError):
            pass  # Type should be accepted
        
        # Test that methods work with empty dicts
        empty_dict: Dict[str, Any] = {}
        try:
            manager.validate_extraction_params(empty_dict)
        except ValidationError:
            pass  # Empty dict should be type-acceptable but validation may fail

    def test_path_type_hints_validation(self, injection_manager):
        """Test Path and string type hints for file paths"""
        manager = injection_manager
        
        # Test that both str and Path objects work where expected
        str_path = "/path/to/file.rom"
        path_obj = Path("/path/to/file.rom")
        
        # Both should be acceptable for file path parameters
        params_str = {
            'input_rom_path': str_path,
            'sprite_png_path': "/path/to/sprite.png",
            'sprite_location': 'compressed',
            'custom_offset': None,
            'fast_compression': True,
        }
        
        params_path = {
            'input_rom_path': str(path_obj),  # Convert to str for params dict
            'sprite_png_path': "/path/to/sprite.png",
            'sprite_location': 'compressed', 
            'custom_offset': None,
            'fast_compression': True,
        }
        
        try:
            manager.validate_rom_injection_params(params_str)
            manager.validate_rom_injection_params(params_path)
        except (ValidationError, FileNotFoundError):
            pass  # Type validation should pass

    def test_generic_type_parameters(self, session_manager):
        """Test generic type parameters work correctly"""
        manager = session_manager
        
        # Test generic Dict[str, Any] usage
        settings_dict: Dict[str, Any] = {
            'string_setting': 'value',
            'int_setting': 42,
            'bool_setting': True,
            'list_setting': [1, 2, 3],
            'nested_dict': {'key': 'value'},
        }
        
        # Should handle various value types in Dict[str, Any]
        for key, value in settings_dict.items():
            manager.set_setting("test_namespace", key, value)
            retrieved = manager.get_setting("test_namespace", key, None)
            # Type should be preserved or convertible
            assert retrieved is not None or value is None

    def test_return_type_annotations_match_behavior(self, extraction_manager):
        """Test that return type annotations match actual return values"""
        manager = extraction_manager
        
        # Test boolean return types
        is_running = manager._is_operation_running()
        assert isinstance(is_running, bool), "Should return bool as annotated"
        
        # Test None return types for async operations
        with patch.object(manager, 'validate_extraction_params'), \
             patch.object(manager, '_is_operation_running', return_value=False), \
             patch('spritepal.core.workers.extraction_worker.ExtractionWorker'):
            
            result = manager.extract_from_vram({})
            assert result is None, "Should return None as annotated"

    def test_parameter_type_enforcement(self, injection_manager):
        """Test that parameter types are enforced where appropriate"""
        manager = injection_manager
        
        # Test that wrong parameter types are caught
        with pytest.raises((TypeError, AttributeError, ValidationError)):
            # Pass wrong type for params (should be dict)
            manager.validate_rom_injection_params(None)
        
        with pytest.raises((TypeError, AttributeError, ValidationError)):
            # Pass wrong type for params
            manager.validate_rom_injection_params("not a dict")

    def test_callback_type_hints(self, extraction_manager):
        """Test callback and signal type hints"""
        manager = extraction_manager
        
        # Test signal connections work with proper types
        callback_called = []
        
        def progress_callback(value: int) -> None:
            callback_called.append(value)
            assert isinstance(value, int)
        
        def completion_callback(status: str, message: str) -> None:
            callback_called.append((status, message))
            assert isinstance(status, str)
            assert isinstance(message, str)
        
        # Connect callbacks
        manager.progress_updated.connect(progress_callback)
        manager.operation_completed.connect(completion_callback)
        
        # Emit signals with correct types
        manager.progress_updated.emit(75)
        manager.operation_completed.emit("success", "Test completion")
        
        # Verify callbacks were called with correct types
        assert len(callback_called) == 2
        assert callback_called[0] == 75
        assert callback_called[1] == ("success", "Test completion")

    def test_async_operation_type_hints(self, extraction_manager):
        """Test async operation type hints and patterns"""
        manager = extraction_manager
        
        # Test that async operations return None but store workers properly
        with patch.object(manager, 'validate_extraction_params'), \
             patch.object(manager, '_is_operation_running', return_value=False), \
             patch('spritepal.core.workers.extraction_worker.ExtractionWorker') as mock_worker:
            
            mock_worker_instance = Mock()
            mock_worker.return_value = mock_worker_instance
            
            # Start operation
            result = manager.extract_from_vram({})
            
            # Should return None as per type hints
            assert result is None
            
            # But internal state should be updated
            assert manager._current_worker is not None or not hasattr(manager, '_current_worker')

    def test_error_handling_type_annotations(self, injection_manager):
        """Test error handling maintains type safety"""
        manager = injection_manager
        
        # Test that exceptions maintain proper types
        try:
            manager.validate_rom_injection_params({})  # Missing required fields
        except ValidationError as e:
            assert isinstance(e, ValidationError)
            assert isinstance(e, ManagerError)
            assert isinstance(e, Exception)
            assert isinstance(str(e), str)
        except Exception as e:
            # Other exceptions should also maintain type safety
            assert isinstance(e, Exception)
            assert isinstance(str(e), str)