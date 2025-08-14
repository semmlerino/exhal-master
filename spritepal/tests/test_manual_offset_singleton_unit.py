"""
Simplified unit tests for Manual Offset Dialog Singleton pattern.

These tests focus specifically on the singleton pattern behavior
without requiring complex Qt setup, using pure mocking to verify
the critical singleton functionality.
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Import mock dialog infrastructure
from tests.infrastructure.mock_dialogs import MockUnifiedManualOffsetDialog, patch_dialog_imports

# Apply dialog patching BEFORE any UI imports
# Test characteristics: Singleton management
pytestmark = [
    pytest.mark.dialog,
    pytest.mark.file_io,
    pytest.mark.headless,
    pytest.mark.mock_dialogs,
    pytest.mark.mock_only,
    pytest.mark.no_qt,
    pytest.mark.rom_data,
    pytest.mark.serial,
    pytest.mark.singleton,
    pytest.mark.unit,
    pytest.mark.cache,
    pytest.mark.ci_safe,
    pytest.mark.signals_slots,
]


patch_dialog_imports()

# Now safe to import the singleton after patching
from ui.rom_extraction_panel import ManualOffsetDialogSingleton


@pytest.mark.no_manager_setup
@pytest.mark.unit
@pytest.mark.mock_dialogs
class TestManualOffsetDialogSingletonUnit:
    """Unit tests for ManualOffsetDialogSingleton pattern."""

    @pytest.fixture(autouse=True)
    def setup_singleton_cleanup(self):
        """Ensure singleton is clean before and after each test."""
        # Clean up any existing instance
        if ManualOffsetDialogSingleton._instance is not None:
            if hasattr(ManualOffsetDialogSingleton._instance, 'close'):
                ManualOffsetDialogSingleton._instance.close()
            ManualOffsetDialogSingleton._instance = None
        ManualOffsetDialogSingleton._destroyed = False
        
        yield ManualOffsetDialogSingleton, MockUnifiedManualOffsetDialog
        
        # Clean up after test
        if ManualOffsetDialogSingleton._instance is not None:
            if hasattr(ManualOffsetDialogSingleton._instance, 'close'):
                ManualOffsetDialogSingleton._instance.close()
            ManualOffsetDialogSingleton._instance = None
        ManualOffsetDialogSingleton._destroyed = False

    @pytest.fixture
    def mock_dialog(self):
        """Create a mock dialog instance."""
        dialog = MockUnifiedManualOffsetDialog()
        return dialog

    @pytest.fixture
    def mock_panel(self):
        """Create a mock extraction panel."""
        panel = MagicMock()
        panel.rom_cache = MagicMock()
        panel.rom_cache.get_cache_stats.return_value = {"hits": 0, "misses": 0}
        panel.rom_extractor = MagicMock()
        panel.extraction_manager = MagicMock()
        panel.parent.return_value = None
        return panel

    def test_singleton_instance_creation(self, setup_singleton_cleanup, mock_panel):
        """Test that singleton creates instance on first call."""
        ManualOffsetDialogSingleton, MockDialogClass = setup_singleton_cleanup
        
        # Create mock dialog instance with proper signals
        mock_dialog = MockDialogClass()
        mock_dialog.finished = MagicMock()
        mock_dialog.rejected = MagicMock()
        mock_dialog.destroyed = MagicMock()
        mock_dialog.finished.connect = MagicMock()
        mock_dialog.rejected.connect = MagicMock()
        mock_dialog.destroyed.connect = MagicMock()
        
        # Mock at the import location in ui.rom_extraction_panel 
        with patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog', return_value=mock_dialog) as MockDialog:
            with patch.object(ManualOffsetDialogSingleton, '_ensure_main_thread', return_value=None):
                # First call should create instance
                dialog = ManualOffsetDialogSingleton.get_dialog(mock_panel)
                
                assert dialog is not None
                assert ManualOffsetDialogSingleton._instance is dialog
                assert dialog is mock_dialog
                # Verify the dialog constructor was called
                MockDialog.assert_called_once()

    def test_singleton_reuse_same_instance(self, setup_singleton_cleanup, mock_panel):
        """Test that singleton returns same instance on multiple calls."""
        ManualOffsetDialogSingleton, MockDialogClass = setup_singleton_cleanup
        
        # Create mock dialog instance
        mock_dialog = MockDialogClass()
        mock_dialog.finished = MagicMock()
        mock_dialog.rejected = MagicMock()
        mock_dialog.destroyed = MagicMock()
        mock_dialog.finished.connect = MagicMock()
        mock_dialog.rejected.connect = MagicMock()
        mock_dialog.destroyed.connect = MagicMock()
        
        with patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog', return_value=mock_dialog) as MockDialog:
            with patch.object(ManualOffsetDialogSingleton, '_ensure_main_thread', return_value=None):
                # First call
                dialog1 = ManualOffsetDialogSingleton.get_dialog(mock_panel)
                
                # Second call  
                dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_panel)
                
                # Should return same instance
                assert dialog1 is dialog2
                assert ManualOffsetDialogSingleton._instance is dialog1
                # Dialog constructor should only be called once
                MockDialog.assert_called_once()

    def test_singleton_is_dialog_open_method(self, setup_singleton_cleanup, mock_panel):
        """Test is_dialog_open method."""
        ManualOffsetDialogSingleton, MockDialogClass = setup_singleton_cleanup
        
        # No dialog exists
        assert not ManualOffsetDialogSingleton.is_dialog_open()
        
        # Create mock dialog instance
        mock_dialog = MockDialogClass()
        mock_dialog.visible = False  # Start as hidden
        mock_dialog.isVisible = MagicMock(return_value=False)
        mock_dialog.finished = MagicMock()
        mock_dialog.rejected = MagicMock()
        mock_dialog.destroyed = MagicMock()
        mock_dialog.finished.connect = MagicMock()
        mock_dialog.rejected.connect = MagicMock()
        mock_dialog.destroyed.connect = MagicMock()
        
        with patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog', return_value=mock_dialog):
            with patch.object(ManualOffsetDialogSingleton, '_ensure_main_thread', return_value=None):
                # Create dialog
                dialog = ManualOffsetDialogSingleton.get_dialog(mock_panel)
                
                # Dialog should not be visible initially
                assert not ManualOffsetDialogSingleton.is_dialog_open()
                
                # Make dialog visible
                dialog.visible = True
                dialog.isVisible.return_value = True
                assert ManualOffsetDialogSingleton.is_dialog_open()
                
                # Make dialog not visible
                dialog.visible = False
                dialog.isVisible.return_value = False
                assert not ManualOffsetDialogSingleton.is_dialog_open()

    def test_singleton_get_current_dialog_method(self, setup_singleton_cleanup, mock_panel):
        """Test get_current_dialog method."""
        ManualOffsetDialogSingleton, MockDialogClass = setup_singleton_cleanup
        
        # No dialog exists
        assert ManualOffsetDialogSingleton.get_current_dialog() is None
        
        # Create mock dialog instance
        mock_dialog = MockDialogClass()
        mock_dialog.visible = False
        mock_dialog.isVisible = MagicMock(return_value=False)
        mock_dialog.finished = MagicMock()
        mock_dialog.rejected = MagicMock()
        mock_dialog.destroyed = MagicMock()
        mock_dialog.finished.connect = MagicMock()
        mock_dialog.rejected.connect = MagicMock()
        mock_dialog.destroyed.connect = MagicMock()
        
        with patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog', return_value=mock_dialog):
            with patch.object(ManualOffsetDialogSingleton, '_ensure_main_thread', return_value=None):
                # Create dialog
                dialog = ManualOffsetDialogSingleton.get_dialog(mock_panel)
                
                # Dialog not visible initially
                assert ManualOffsetDialogSingleton.get_current_dialog() is None
                
                # Make dialog visible
                dialog.visible = True
                dialog.isVisible.return_value = True
                
                # Should return the dialog
                current = ManualOffsetDialogSingleton.get_current_dialog()
                assert current is dialog
                
                # Make dialog not visible
                dialog.visible = False
                dialog.isVisible.return_value = False
                assert ManualOffsetDialogSingleton.get_current_dialog() is None

    def test_singleton_with_parent_panel(self, setup_singleton_cleanup, mock_panel):
        """Test singleton creation with parent panel."""
        ManualOffsetDialogSingleton, MockDialogClass = setup_singleton_cleanup
        
        # Create mock dialog instance
        mock_dialog = MockDialogClass()
        mock_dialog.finished = MagicMock()
        mock_dialog.rejected = MagicMock()
        mock_dialog.destroyed = MagicMock()
        mock_dialog.finished.connect = MagicMock()
        mock_dialog.rejected.connect = MagicMock()
        mock_dialog.destroyed.connect = MagicMock()
        
        with patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog', return_value=mock_dialog):
            with patch.object(ManualOffsetDialogSingleton, '_ensure_main_thread', return_value=None):
                # Create dialog with panel
                dialog = ManualOffsetDialogSingleton.get_dialog(mock_panel)
                
                # Should store panel reference
                assert dialog is not None
                assert ManualOffsetDialogSingleton._instance is dialog
                
                # The panel should have managers
                assert mock_panel.extraction_manager is not None
                assert mock_panel.rom_extractor is not None
                
                # Dialog can have managers set via set_managers method
                dialog.set_managers(mock_panel.extraction_manager, mock_panel.rom_extractor)
                assert dialog.extraction_manager == mock_panel.extraction_manager
                assert dialog.rom_extractor == mock_panel.rom_extractor