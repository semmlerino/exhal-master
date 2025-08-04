"""
Simplified unit tests for Manual Offset Dialog Singleton pattern.

These tests focus specifically on the singleton pattern behavior
without requiring complex Qt setup, using pure mocking to verify
the critical singleton functionality.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from spritepal.ui.rom_extraction_panel import ManualOffsetDialogSingleton


@pytest.mark.no_manager_setup
@pytest.mark.unit
class TestManualOffsetDialogSingletonUnit:
    """Unit tests for ManualOffsetDialogSingleton pattern."""

    @pytest.fixture(autouse=True)
    def setup_singleton_cleanup(self):
        """Ensure singleton is clean before and after each test."""
        ManualOffsetDialogSingleton._cleanup_instance()
        yield
        ManualOffsetDialogSingleton._cleanup_instance()

    @pytest.fixture
    def mock_dialog(self):
        """Create a mock dialog instance."""
        mock = MagicMock()
        mock.isVisible.return_value = True
        mock.finished.connect = MagicMock()
        mock.rejected.connect = MagicMock()
        mock.destroyed.connect = MagicMock()
        mock.deleteLater = MagicMock()
        return mock

    @pytest.fixture
    def mock_panel(self):
        """Create a mock ROM panel."""
        return MagicMock()

    def test_singleton_instance_creation(self, mock_panel):
        """Test that singleton creates and stores instance."""
        with patch('spritepal.ui.rom_extraction_panel.UnifiedManualOffsetDialog') as mock_dialog_class:
            mock_instance = MagicMock()
            mock_instance.isVisible.return_value = True  
            mock_instance.finished.connect = MagicMock()
            mock_instance.rejected.connect = MagicMock()
            mock_instance.destroyed.connect = MagicMock()
            mock_dialog_class.return_value = mock_instance
            
            # Get dialog for first time
            dialog = ManualOffsetDialogSingleton.get_dialog(mock_panel)
            
            # Should create new instance
            mock_dialog_class.assert_called_once_with(mock_panel)
            assert dialog is mock_instance
            assert ManualOffsetDialogSingleton._instance is mock_instance
            assert ManualOffsetDialogSingleton._creator_panel is mock_panel

    def test_singleton_reuse_same_instance(self, mock_panel):
        """Test that subsequent calls return same instance."""
        with patch('spritepal.ui.rom_extraction_panel.UnifiedManualOffsetDialog') as mock_dialog_class:
            mock_instance = MagicMock()
            mock_instance.isVisible.return_value = True
            mock_instance.finished.connect = MagicMock()
            mock_instance.rejected.connect = MagicMock()
            mock_instance.destroyed.connect = MagicMock()
            mock_dialog_class.return_value = mock_instance
            
            # First call
            dialog1 = ManualOffsetDialogSingleton.get_dialog(mock_panel)
            
            # Second call
            dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_panel)
            
            # Should only create once
            mock_dialog_class.assert_called_once()
            assert dialog1 is dialog2
            assert dialog1 is mock_instance

    def test_singleton_cleanup_on_stale_reference(self, mock_panel):
        """Test cleanup when dialog reference becomes stale."""
        with patch('spritepal.ui.rom_extraction_panel.UnifiedManualOffsetDialog') as mock_dialog_class:
            # First instance that becomes stale
            stale_instance = MagicMock()
            stale_instance.isVisible.side_effect = RuntimeError("wrapped C/C++ object deleted")
            
            # New instance created after cleanup
            new_instance = MagicMock()
            new_instance.isVisible.return_value = True
            new_instance.finished.connect = MagicMock()
            new_instance.rejected.connect = MagicMock()
            new_instance.destroyed.connect = MagicMock()
            
            mock_dialog_class.side_effect = [stale_instance, new_instance]
            
            # First call creates stale instance
            dialog1 = ManualOffsetDialogSingleton.get_dialog(mock_panel)
            assert dialog1 is stale_instance
            
            # Second call should handle stale reference and create new instance
            dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_panel)
            
            # Should have created two instances (stale + new)
            assert mock_dialog_class.call_count == 2
            assert dialog2 is new_instance
            assert ManualOffsetDialogSingleton._instance is new_instance

    def test_singleton_is_dialog_open_method(self, mock_panel):
        """Test is_dialog_open method."""
        # No dialog exists
        assert not ManualOffsetDialogSingleton.is_dialog_open()
        
        with patch('spritepal.ui.rom_extraction_panel.UnifiedManualOffsetDialog') as mock_dialog_class:
            mock_instance = MagicMock()
            mock_instance.isVisible.return_value = True
            mock_instance.finished.connect = MagicMock()
            mock_instance.rejected.connect = MagicMock()
            mock_instance.destroyed.connect = MagicMock()
            mock_dialog_class.return_value = mock_instance
            
            # Create dialog
            ManualOffsetDialogSingleton.get_dialog(mock_panel)
            
            # Should be open
            assert ManualOffsetDialogSingleton.is_dialog_open()
            
            # Make dialog not visible
            mock_instance.isVisible.return_value = False
            assert not ManualOffsetDialogSingleton.is_dialog_open()

    def test_singleton_get_current_dialog_method(self, mock_panel):
        """Test get_current_dialog method."""
        # No dialog exists
        assert ManualOffsetDialogSingleton.get_current_dialog() is None
        
        with patch('spritepal.ui.rom_extraction_panel.UnifiedManualOffsetDialog') as mock_dialog_class:
            mock_instance = MagicMock()
            mock_instance.isVisible.return_value = True
            mock_instance.finished.connect = MagicMock()
            mock_instance.rejected.connect = MagicMock()
            mock_instance.destroyed.connect = MagicMock()
            mock_dialog_class.return_value = mock_instance
            
            # Create dialog
            dialog = ManualOffsetDialogSingleton.get_dialog(mock_panel)
            
            # Should return the dialog
            current = ManualOffsetDialogSingleton.get_current_dialog()
            assert current is dialog
            assert current is mock_instance
            
            # Make dialog not visible
            mock_instance.isVisible.return_value = False
            assert ManualOffsetDialogSingleton.get_current_dialog() is None

    def test_singleton_cleanup_instance_method(self, mock_panel):
        """Test _cleanup_instance method."""
        with patch('spritepal.ui.rom_extraction_panel.UnifiedManualOffsetDialog') as mock_dialog_class:
            mock_instance = MagicMock()
            mock_instance.isVisible.return_value = True
            mock_instance.finished.connect = MagicMock()
            mock_instance.rejected.connect = MagicMock()
            mock_instance.destroyed.connect = MagicMock()
            mock_dialog_class.return_value = mock_instance
            
            # Create dialog
            ManualOffsetDialogSingleton.get_dialog(mock_panel)
            
            # Verify instance exists
            assert ManualOffsetDialogSingleton._instance is not None
            assert ManualOffsetDialogSingleton._creator_panel is not None
            
            # Cleanup
            ManualOffsetDialogSingleton._cleanup_instance()
            
            # Verify cleanup
            assert ManualOffsetDialogSingleton._instance is None
            assert ManualOffsetDialogSingleton._creator_panel is None

    def test_singleton_dialog_closed_callback(self, mock_panel):
        """Test _on_dialog_closed callback."""
        with patch('spritepal.ui.rom_extraction_panel.UnifiedManualOffsetDialog') as mock_dialog_class:
            mock_instance = MagicMock()
            mock_instance.isVisible.return_value = True
            mock_instance.finished.connect = MagicMock()
            mock_instance.rejected.connect = MagicMock()
            mock_instance.destroyed.connect = MagicMock()
            mock_instance.deleteLater = MagicMock()
            mock_dialog_class.return_value = mock_instance
            
            # Create dialog
            ManualOffsetDialogSingleton.get_dialog(mock_panel)
            assert ManualOffsetDialogSingleton._instance is not None
            
            # Simulate dialog closed
            ManualOffsetDialogSingleton._on_dialog_closed()
            
            # Should call deleteLater and cleanup
            mock_instance.deleteLater.assert_called_once()
            assert ManualOffsetDialogSingleton._instance is None

    def test_singleton_dialog_destroyed_callback(self, mock_panel):
        """Test _on_dialog_destroyed callback."""
        with patch('spritepal.ui.rom_extraction_panel.UnifiedManualOffsetDialog') as mock_dialog_class:
            mock_instance = MagicMock()
            mock_instance.isVisible.return_value = True
            mock_instance.finished.connect = MagicMock()
            mock_instance.rejected.connect = MagicMock()
            mock_instance.destroyed.connect = MagicMock()
            mock_dialog_class.return_value = mock_instance
            
            # Create dialog
            ManualOffsetDialogSingleton.get_dialog(mock_panel)
            assert ManualOffsetDialogSingleton._instance is not None
            
            # Simulate dialog destroyed
            ManualOffsetDialogSingleton._on_dialog_destroyed()
            
            # Should cleanup
            assert ManualOffsetDialogSingleton._instance is None

    def test_singleton_signal_connections(self, mock_panel):
        """Test that signals are properly connected for cleanup."""
        with patch('spritepal.ui.rom_extraction_panel.UnifiedManualOffsetDialog') as mock_dialog_class:
            mock_instance = MagicMock()
            mock_instance.isVisible.return_value = True
            finished_connect = MagicMock()
            rejected_connect = MagicMock()
            destroyed_connect = MagicMock()
            mock_instance.finished.connect = finished_connect
            mock_instance.rejected.connect = rejected_connect
            mock_instance.destroyed.connect = destroyed_connect
            mock_dialog_class.return_value = mock_instance
            
            # Create dialog
            ManualOffsetDialogSingleton.get_dialog(mock_panel)
            
            # Verify signal connections
            finished_connect.assert_called_once_with(ManualOffsetDialogSingleton._on_dialog_closed)
            rejected_connect.assert_called_once_with(ManualOffsetDialogSingleton._on_dialog_closed)
            destroyed_connect.assert_called_once_with(ManualOffsetDialogSingleton._on_dialog_destroyed)

    def test_singleton_different_creator_panels_same_instance(self):
        """Test that different creator panels still get same instance."""
        panel1 = MagicMock()
        panel2 = MagicMock()
        
        with patch('spritepal.ui.rom_extraction_panel.UnifiedManualOffsetDialog') as mock_dialog_class:
            mock_instance = MagicMock()
            mock_instance.isVisible.return_value = True
            mock_instance.finished.connect = MagicMock()
            mock_instance.rejected.connect = MagicMock()
            mock_instance.destroyed.connect = MagicMock()
            mock_dialog_class.return_value = mock_instance
            
            # First panel gets dialog
            dialog1 = ManualOffsetDialogSingleton.get_dialog(panel1)
            
            # Second panel should get same dialog
            dialog2 = ManualOffsetDialogSingleton.get_dialog(panel2)
            
            # Should only create once, same instance
            mock_dialog_class.assert_called_once_with(panel1)  # Called with first panel
            assert dialog1 is dialog2
            assert ManualOffsetDialogSingleton._creator_panel is panel1  # First panel "owns" it


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])