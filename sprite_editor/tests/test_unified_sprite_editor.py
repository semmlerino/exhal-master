"""
Tests for the unified sprite editor that would catch initialization order bugs
"""

import sys
from pathlib import Path

# Add parent directory to path to import sprite_editor_unified
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication, QListWidget, QMenu


# Create QApplication once for all tests
@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for tests"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_unified_editor():
    """Create a mock UnifiedSpriteEditor for testing initialization phases"""
    from sprite_editor_unified import UnifiedSpriteEditor

    # Create editor with proper initialization
    editor = MagicMock(spec=UnifiedSpriteEditor)
    editor.recent_files = []
    editor.recent_menu = MagicMock(spec=QMenu)
    # Bind the actual method to the mock
    editor.update_recent_menu = UnifiedSpriteEditor.update_recent_menu.__get__(editor)
    return editor


class TestUnifiedSpriteEditorInitialization:
    """Test initialization order and widget availability"""

    def test_update_recent_menu_before_ui_creation(self, mock_unified_editor):
        """Test that update_recent_menu handles missing recent_list widget"""
        editor = mock_unified_editor

        # Call update_recent_menu before recent_list exists
        # This should have caused the AttributeError
        editor.update_recent_menu()

        # Should not crash
        editor.recent_menu.clear.assert_called_once()

    def test_update_recent_menu_after_partial_ui_creation(self, qapp):
        """Test update_recent_menu after recent_list is created"""

        from sprite_editor_unified import UnifiedSpriteEditor

        # Create a minimal editor with mocked parts
        with patch.object(UnifiedSpriteEditor, "__init__", lambda x: None):
            editor = UnifiedSpriteEditor()
            editor.recent_files = ["/path/to/file1.kss", "/path/to/file2.kss"]
            editor.recent_menu = MagicMock(spec=QMenu)
            editor.recent_list = MagicMock(spec=QListWidget)

            # Mock QAction to avoid parent widget issues
            with patch("sprite_editor_unified.QAction") as mock_qaction:
                mock_action = MagicMock()
                mock_qaction.return_value = mock_action

                # Bind the actual method
                editor.update_recent_menu = (
                    UnifiedSpriteEditor.update_recent_menu.__get__(editor)
                )

                # Now update_recent_menu should work with the list widget
                editor.update_recent_menu()

                # Both menu and list should be cleared
                editor.recent_menu.clear.assert_called_once()
                editor.recent_list.clear.assert_called_once()

                # List should have items added
                assert editor.recent_list.addItem.call_count == 2

    def test_full_initialization_order(self, qapp):
        """Test the complete initialization sequence"""
        from sprite_editor_unified import UnifiedSpriteEditor

        # Track initialization order
        init_order = []

        original_init_ui = UnifiedSpriteEditor.init_ui
        original_create_menu_bar = UnifiedSpriteEditor.create_menu_bar
        original_create_left_panel = UnifiedSpriteEditor.create_left_panel
        original_update_recent_menu = UnifiedSpriteEditor.update_recent_menu

        def track_init_ui(self):
            init_order.append("init_ui")
            original_init_ui(self)

        def track_create_menu_bar(self):
            init_order.append("create_menu_bar")
            init_order.append(f'recent_list_exists: {hasattr(self, "recent_list")}')
            original_create_menu_bar(self)

        def track_create_left_panel(self):
            init_order.append("create_left_panel_start")
            result = original_create_left_panel(self)
            init_order.append("create_left_panel_end")
            init_order.append(f'recent_list_exists: {hasattr(self, "recent_list")}')
            return result

        def track_update_recent_menu(self):
            init_order.append("update_recent_menu")
            init_order.append(f'recent_list_exists: {hasattr(self, "recent_list")}')
            original_update_recent_menu(self)

        with patch.object(UnifiedSpriteEditor, "init_ui", track_init_ui):
            with patch.object(
                UnifiedSpriteEditor, "create_menu_bar", track_create_menu_bar
            ):
                with patch.object(
                    UnifiedSpriteEditor, "create_left_panel", track_create_left_panel
                ):
                    with patch.object(
                        UnifiedSpriteEditor,
                        "update_recent_menu",
                        track_update_recent_menu,
                    ):
                        with patch.object(UnifiedSpriteEditor, "load_settings"):
                            # Create the editor
                            editor = UnifiedSpriteEditor()

        # Verify initialization order
        assert "init_ui" in init_order
        assert "create_menu_bar" in init_order
        # update_recent_menu is now called from load_settings, not during init_ui
        # so it won't be in init_order from the UI creation phase

        # update_recent_menu should now be called from load_settings after UI is ready
        # Check if it was called during menu creation (which we fixed)
        menu_bar_idx = init_order.index("create_menu_bar")
        left_panel_idx = init_order.index("create_left_panel_end")

        # Verify update_recent_menu is NOT called between menu bar and left panel creation
        calls_between = init_order[menu_bar_idx:left_panel_idx]
        assert (
            "update_recent_menu" not in calls_between
        ), "update_recent_menu should not be called before recent_list exists"

        # After full initialization, everything should exist
        assert hasattr(editor, "recent_files")
        assert hasattr(editor, "recent_menu")
        assert hasattr(editor, "recent_list")


class TestRecentFilesManagement:
    """Test recent files functionality"""

    def test_add_to_recent_files(self, qapp):
        """Test adding files to recent files list"""
        from sprite_editor_unified import UnifiedSpriteEditor

        with patch.object(UnifiedSpriteEditor, "load_settings"):
            editor = UnifiedSpriteEditor()

        # Test load_project adds to recent files
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                '{"name": "Test Project"}'
            )
            editor.load_project("/path/to/file1.kss")
            assert "/path/to/file1.kss" in editor.recent_files

    def test_recent_files_limit(self, qapp):
        """Test that recent files list has a maximum size"""
        from sprite_editor_unified import UnifiedSpriteEditor

        with patch.object(UnifiedSpriteEditor, "load_settings"):
            editor = UnifiedSpriteEditor()

        # Add many files via load_project
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                '{"name": "Test Project"}'
            )
            for i in range(15):
                editor.load_project(f"/path/to/file{i}.kss")

        # Should be limited to 10 files
        assert len(editor.recent_files) <= 10

    def test_recent_files_no_duplicates(self, qapp):
        """Test that adding the same file moves it to top"""
        from sprite_editor_unified import UnifiedSpriteEditor

        with patch.object(UnifiedSpriteEditor, "load_settings"):
            editor = UnifiedSpriteEditor()

        # Add files via load_project
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                '{"name": "Test Project"}'
            )
            editor.load_project("/path/to/file1.kss")
            editor.load_project("/path/to/file2.kss")
            editor.load_project("/path/to/file3.kss")

            # Re-add file1 - should move to top
            editor.load_project("/path/to/file1.kss")

        assert len(editor.recent_files) == 3
        assert editor.recent_files[0] == "/path/to/file1.kss"


class TestUIComponentAvailability:
    """Test that UI components are available when expected"""

    def test_menu_components_after_init(self, qapp):
        """Test menu components exist after initialization"""
        from sprite_editor_unified import UnifiedSpriteEditor

        with patch.object(UnifiedSpriteEditor, "load_settings"):
            editor = UnifiedSpriteEditor()

        # All menu components should exist
        assert hasattr(editor, "recent_menu")
        assert editor.recent_menu is not None

    def test_widget_components_after_init(self, qapp):
        """Test widget components exist after initialization"""
        from sprite_editor_unified import UnifiedSpriteEditor

        with patch.object(UnifiedSpriteEditor, "load_settings"):
            editor = UnifiedSpriteEditor()

        # All widgets should exist after full initialization
        assert hasattr(editor, "recent_list")
        assert editor.recent_list is not None
        assert isinstance(editor.recent_list, QListWidget)

    def test_defensive_programming_in_methods(self, qapp):
        """Test that methods handle missing attributes defensively"""
        from sprite_editor_unified import UnifiedSpriteEditor

        with patch.object(UnifiedSpriteEditor, "load_settings"):
            editor = UnifiedSpriteEditor()

        # Delete recent_list to simulate it not existing
        if hasattr(editor, "recent_list"):
            delattr(editor, "recent_list")

        # update_recent_menu should still work
        editor.update_recent_menu()  # Should not crash

        # Re-create recent_list
        editor.recent_list = QListWidget()
        editor.update_recent_menu()  # Should work normally now


# Integration test that would have caught the original bug
def test_initialization_bug_regression(qapp):
    """Regression test for the initialization order bug"""
    from sprite_editor_unified import UnifiedSpriteEditor

    initialization_errors = []

    # Monkey-patch update_recent_menu to detect the bug condition
    original_update = UnifiedSpriteEditor.update_recent_menu

    def check_update_recent_menu(self):
        if not hasattr(self, "recent_list"):
            initialization_errors.append(
                "update_recent_menu called before recent_list exists!"
            )
        original_update(self)

    with patch.object(
        UnifiedSpriteEditor, "update_recent_menu", check_update_recent_menu
    ), patch.object(UnifiedSpriteEditor, "load_settings"):
        UnifiedSpriteEditor()

    # With our fix, update_recent_menu should not be called before recent_list exists
    # This test verifies the initialization order is correct
    assert (
        len(initialization_errors) == 0
    ), f"update_recent_menu was called before recent_list exists: {initialization_errors}"
