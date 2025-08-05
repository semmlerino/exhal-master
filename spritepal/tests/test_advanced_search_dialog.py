"""
Comprehensive tests for advanced search dialog functionality.

Tests dialog creation and UI elements, search parameter validation, result display,
signal connections, and proper mocking of search workers.
"""

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Generator
from unittest.mock import Mock, patch

import pytest
from core.parallel_sprite_finder import SearchResult
from PyQt6.QtCore import QThread
from ui.dialogs.advanced_search_dialog import (
    AdvancedSearchDialog,
    SearchFilter,
    SearchHistoryEntry,
    SearchWorker,
)

logger = logging.getLogger(__name__)


@pytest.fixture
def temp_rom_file() -> Generator[str, None, None]:
    """Create temporary ROM file for testing."""
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".smc") as f:
        # Create a simple 1MB ROM
        rom_data = b"\x00" * 0x100000
        f.write(rom_data)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def search_filter() -> SearchFilter:
    """Create SearchFilter for testing."""
    return SearchFilter(
        min_size=1024,
        max_size=65536,
        min_tiles=4,
        max_tiles=256,
        alignment=0x100,
        include_compressed=True,
        include_uncompressed=False,
        confidence_threshold=0.7
    )


@pytest.fixture
def search_history_entry(search_filter: SearchFilter) -> SearchHistoryEntry:
    """Create SearchHistoryEntry for testing."""
    return SearchHistoryEntry(
        timestamp=datetime.now(),
        search_type="Parallel",
        query="0x1000 - 0x10000",
        filters=search_filter,
        results_count=42
    )


@pytest.fixture
def mock_parallel_finder() -> Generator[Mock, None, None]:
    """Mock ParallelSpriteFinder to prevent thread pool creation in tests."""
    with patch("ui.dialogs.advanced_search_dialog.ParallelSpriteFinder") as mock_cls:
        mock_instance = Mock()
        mock_instance.shutdown = Mock()
        mock_instance.search_parallel = Mock(return_value=[])
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_search_dialog(qtbot, temp_rom_file, mock_parallel_finder):
    """Create mocked AdvancedSearchDialog for testing."""
    with patch("ui.dialogs.advanced_search_dialog.SearchWorker"):
        dialog = AdvancedSearchDialog(temp_rom_file)
        qtbot.addWidget(dialog)
        yield dialog
        # Ensure any workers are cleaned up
        if hasattr(dialog, "search_worker") and dialog.search_worker:
            dialog.search_worker.cancel()
            dialog.search_worker.wait(1000)


class TestSearchFilter:
    """Test SearchFilter data class."""

    def test_search_filter_creation(self):
        """Test SearchFilter creation with all fields."""
        filter_obj = SearchFilter(
            min_size=512,
            max_size=32768,
            min_tiles=2,
            max_tiles=128,
            alignment=0x80,
            include_compressed=True,
            include_uncompressed=True,
            confidence_threshold=0.6
        )

        assert filter_obj.min_size == 512
        assert filter_obj.max_size == 32768
        assert filter_obj.min_tiles == 2
        assert filter_obj.max_tiles == 128
        assert filter_obj.alignment == 0x80
        assert filter_obj.include_compressed is True
        assert filter_obj.include_uncompressed is True
        assert filter_obj.confidence_threshold == 0.6


class TestSearchHistoryEntry:
    """Test SearchHistoryEntry data class."""

    def test_search_history_entry_creation(self, search_filter):
        """Test SearchHistoryEntry creation."""
        timestamp = datetime.now()
        entry = SearchHistoryEntry(
            timestamp=timestamp,
            search_type="Visual",
            query="Reference: 0x5000",
            filters=search_filter,
            results_count=15
        )

        assert entry.timestamp == timestamp
        assert entry.search_type == "Visual"
        assert entry.query == "Reference: 0x5000"
        assert entry.filters == search_filter
        assert entry.results_count == 15

    def test_to_display_string(self, search_history_entry):
        """Test display string formatting."""
        display_str = search_history_entry.to_display_string()

        assert search_history_entry.search_type in display_str
        assert search_history_entry.query in display_str
        assert str(search_history_entry.results_count) in display_str
        assert "results" in display_str


class TestSearchWorker:
    """Test SearchWorker thread functionality."""

    def test_search_worker_initialization(self):
        """Test SearchWorker initialization."""
        params = {"rom_path": "/test/rom.smc", "start_offset": 0x1000}
        worker = SearchWorker("parallel", params)

        assert worker.search_type == "parallel"
        assert worker.params == params
        assert worker.finder is None
        assert worker._cancelled is False
        assert isinstance(worker, QThread)

    def test_search_worker_signals(self):
        """Test SearchWorker has required signals."""
        worker = SearchWorker("parallel", {})

        # Check signals exist
        assert hasattr(worker, "progress")
        assert hasattr(worker, "result_found")
        assert hasattr(worker, "search_complete")
        assert hasattr(worker, "error")

    @patch("ui.dialogs.advanced_search_dialog.ParallelSpriteFinder")
    def test_run_parallel_search_basic(self, mock_finder_class, temp_rom_file):
        """Test basic parallel search execution."""
        # Setup mock finder with proper cleanup
        mock_finder = Mock()
        mock_finder.shutdown = Mock()  # Add shutdown method
        mock_finder_class.return_value = mock_finder
        mock_finder.search_parallel.return_value = []

        params = {
            "rom_path": temp_rom_file,
            "start_offset": 0x0,
            "end_offset": 0x1000,
            "num_workers": 2,
            "step_size": 0x100
        }

        worker = SearchWorker("parallel", params)

        # Mock signals to track calls
        worker.progress = Mock()
        worker.result_found = Mock()
        worker.search_complete = Mock()
        worker.error = Mock()

        # Run the search
        worker._run_parallel_search()

        # Verify finder was created and called
        mock_finder_class.assert_called_once_with(
            num_workers=2,
            step_size=0x100
        )
        mock_finder.search_parallel.assert_called_once()
        worker.search_complete.emit.assert_called_once()

    def test_apply_filters_valid_result(self, search_filter):
        """Test filter application with valid result."""
        worker = SearchWorker("parallel", {})

        result = SearchResult(
            offset=0x1000,
            size=2048,  # Within min_size/max_size
            tile_count=16,  # Within min_tiles/max_tiles
            compressed_size=1024,  # Compressed
            confidence=0.8,  # Above threshold
            metadata={}
        )

        # Alignment filter: 0x1000 % 0x100 == 0
        assert worker._apply_filters(result, search_filter) is True

    def test_apply_filters_invalid_size(self, search_filter):
        """Test filter application with invalid size."""
        worker = SearchWorker("parallel", {})

        result = SearchResult(
            offset=0x1000,
            size=500,  # Below min_size (1024)
            tile_count=16,
            compressed_size=250,
            confidence=0.8,
            metadata={}
        )

        assert worker._apply_filters(result, search_filter) is False

    def test_apply_filters_invalid_tiles(self, search_filter):
        """Test filter application with invalid tile count."""
        worker = SearchWorker("parallel", {})

        result = SearchResult(
            offset=0x1000,
            size=2048,
            tile_count=2,  # Below min_tiles (4)
            compressed_size=1024,
            confidence=0.8,
            metadata={}
        )

        assert worker._apply_filters(result, search_filter) is False

    def test_apply_filters_alignment(self, search_filter):
        """Test filter application with alignment requirement."""
        worker = SearchWorker("parallel", {})

        result = SearchResult(
            offset=0x1050,  # Not aligned to 0x100
            size=2048,
            tile_count=16,
            compressed_size=1024,
            confidence=0.8,
            metadata={}
        )

        assert worker._apply_filters(result, search_filter) is False

    def test_apply_filters_compression_type(self, search_filter):
        """Test filter application with compression type filtering."""
        worker = SearchWorker("parallel", {})

        # Uncompressed result (compressed_size >= size)
        result = SearchResult(
            offset=0x1000,
            size=2048,
            tile_count=16,
            compressed_size=2048,  # Not compressed
            confidence=0.8,
            metadata={}
        )

        # search_filter.include_uncompressed is False
        assert worker._apply_filters(result, search_filter) is False

    def test_apply_filters_confidence_threshold(self, search_filter):
        """Test filter application with confidence threshold."""
        worker = SearchWorker("parallel", {})

        result = SearchResult(
            offset=0x1000,
            size=2048,
            tile_count=16,
            compressed_size=1024,
            confidence=0.5,  # Below threshold (0.7)
            metadata={}
        )

        assert worker._apply_filters(result, search_filter) is False

    def test_cancel_functionality(self):
        """Test worker cancellation."""
        worker = SearchWorker("parallel", {})

        assert worker._cancelled is False

        worker.cancel()

        assert worker._cancelled is True
        assert worker.is_set() is True  # Cancellation token interface

    def test_run_visual_search_missing_params(self):
        """Test visual search handles missing required parameters."""
        worker = SearchWorker("visual", {})
        worker.error = Mock()

        worker._run_visual_search()

        # The implementation tries to access params["rom_path"] which throws KeyError
        worker.error.emit.assert_called_once_with("'rom_path'")

    def test_run_pattern_search_missing_params(self):
        """Test pattern search handles missing required parameters."""
        worker = SearchWorker("pattern", {})
        worker.error = Mock()

        worker._run_pattern_search()

        # The implementation tries to access params["rom_path"] which throws KeyError
        worker.error.emit.assert_called_once_with("'rom_path'")

    def test_run_unknown_search_type(self):
        """Test unknown search type handling."""
        worker = SearchWorker("unknown", {})
        worker.error = Mock()

        worker.run()

        worker.error.emit.assert_called_once_with("Unknown search type: unknown")


@pytest.mark.gui
class TestAdvancedSearchDialog:
    """Test AdvancedSearchDialog GUI functionality."""

    def test_dialog_initialization(self, qtbot, temp_rom_file):
        """Test dialog initialization."""
        with patch("ui.dialogs.advanced_search_dialog.SearchWorker"):
            dialog = AdvancedSearchDialog(temp_rom_file)
            qtbot.addWidget(dialog)

        assert dialog.rom_path == temp_rom_file
        assert dialog.search_history == []
        assert dialog.current_results == []
        assert dialog.search_worker is None
        assert dialog.windowTitle() == "Advanced Sprite Search"

    def test_dialog_ui_elements(self, mock_search_dialog):
        """Test dialog has required UI elements."""
        dialog = mock_search_dialog

        # Check tabs exist
        assert dialog.tabs is not None
        assert dialog.tabs.count() == 4  # Parallel, Visual, Pattern, History

        # Check main controls
        assert dialog.search_button is not None
        assert dialog.stop_button is not None
        assert dialog.progress_bar is not None
        assert dialog.results_list is not None
        assert dialog.results_label is not None

    def test_parallel_search_tab_elements(self, mock_search_dialog):
        """Test parallel search tab has required elements."""
        dialog = mock_search_dialog

        # Check form elements exist
        assert dialog.start_offset_edit is not None
        assert dialog.end_offset_edit is not None
        assert dialog.step_size_spin is not None
        assert dialog.workers_spin is not None
        assert dialog.adaptive_check is not None

        # Check filter elements
        assert dialog.min_size_spin is not None
        assert dialog.max_size_spin is not None
        assert dialog.min_tiles_spin is not None
        assert dialog.max_tiles_spin is not None
        assert dialog.compressed_check is not None
        assert dialog.uncompressed_check is not None
        assert dialog.alignment_combo is not None

    def test_visual_search_tab_elements(self, mock_search_dialog):
        """Test visual search tab has required elements."""
        dialog = mock_search_dialog

        # Check visual search elements
        assert dialog.ref_offset_edit is not None
        assert dialog.ref_browse_button is not None
        assert dialog.ref_preview_label is not None
        assert dialog.similarity_slider is not None
        assert dialog.similarity_label is not None
        assert dialog.visual_scope_combo is not None

    def test_pattern_search_tab_elements(self, mock_search_dialog):
        """Test pattern search tab has required elements."""
        dialog = mock_search_dialog

        # Check pattern search elements
        assert dialog.hex_radio is not None
        assert dialog.regex_radio is not None
        assert dialog.pattern_edit is not None
        assert dialog.case_sensitive_check is not None
        assert dialog.whole_word_check is not None
        assert dialog.pattern_aligned_check is not None

    def test_history_tab_elements(self, mock_search_dialog):
        """Test history tab has required elements."""
        dialog = mock_search_dialog

        # Check history elements
        assert dialog.history_list is not None
        assert dialog.clear_history_button is not None
        assert dialog.export_history_button is not None

    def test_default_values(self, mock_search_dialog):
        """Test default values in form elements."""
        dialog = mock_search_dialog

        # Check default values
        assert dialog.start_offset_edit.text() == "0x0"
        assert dialog.end_offset_edit.text() == ""
        assert dialog.step_size_spin.value() == 0x100
        assert dialog.workers_spin.value() == 4
        assert dialog.adaptive_check.isChecked() is True

        # Check filter defaults
        assert dialog.compressed_check.isChecked() is True
        assert dialog.similarity_slider.value() == 80
        assert dialog.hex_radio.isChecked() is True

    def test_get_alignment_value(self, mock_search_dialog):
        """Test alignment value extraction from combo box."""
        dialog = mock_search_dialog

        # Test "Any" selection
        dialog.alignment_combo.setCurrentText("Any")
        assert dialog._get_alignment_value() == 1

        # Test hex value selection
        dialog.alignment_combo.setCurrentText("0x100")
        assert dialog._get_alignment_value() == 0x100

    @patch("ui.dialogs.advanced_search_dialog.SearchWorker")
    def test_start_parallel_search_valid_params(self, mock_worker_class, mock_search_dialog, qtbot):
        """Test starting parallel search with valid parameters."""
        dialog = mock_search_dialog
        mock_worker = Mock()
        mock_worker_class.return_value = mock_worker

        # Set valid parameters
        dialog.start_offset_edit.setText("0x1000")
        dialog.end_offset_edit.setText("0x10000")
        dialog.workers_spin.setValue(2)
        dialog.step_size_spin.setValue(0x200)

        # Start search
        dialog._start_parallel_search()

        # Verify worker creation
        mock_worker_class.assert_called_once()
        args, kwargs = mock_worker_class.call_args
        assert args[0] == "parallel"

        params = args[1]
        assert params["rom_path"] == dialog.rom_path
        assert params["start_offset"] == 0x1000
        assert params["end_offset"] == 0x10000
        assert params["num_workers"] == 2
        assert params["step_size"] == 0x200

        # Verify UI state
        assert dialog.search_button.isEnabled() is False
        assert dialog.stop_button.isEnabled() is True
        assert dialog.progress_bar.isVisible() is True

    def test_start_parallel_search_invalid_offset(self, mock_search_dialog):
        """Test starting search with invalid offset format."""
        dialog = mock_search_dialog

        # Set invalid offset
        dialog.start_offset_edit.setText("invalid")

        dialog._start_parallel_search()

        # Should show error message
        assert "Invalid offset format" in dialog.results_label.text()

    def test_start_parallel_search_empty_end_offset(self, mock_search_dialog):
        """Test starting search with empty end offset (should use None)."""
        dialog = mock_search_dialog

        with patch("ui.dialogs.advanced_search_dialog.SearchWorker") as mock_worker_class:
            mock_worker = Mock()
            mock_worker_class.return_value = mock_worker

            # Set empty end offset
            dialog.start_offset_edit.setText("0x1000")
            dialog.end_offset_edit.setText("")

            dialog._start_parallel_search()

            # Should pass None for end_offset
            args = mock_worker_class.call_args[0]
            params = args[1]
            assert params["end_offset"] is None

    def test_add_result_to_list(self, mock_search_dialog):
        """Test adding search result to results list."""
        dialog = mock_search_dialog

        result = SearchResult(
            offset=0x5000,
            size=2048,
            tile_count=32,
            compressed_size=1024,
            confidence=0.85,
            metadata={}
        )

        dialog._add_result(result)

        # Check result was added
        assert len(dialog.current_results) == 1
        assert dialog.current_results[0] == result
        assert dialog.results_list.count() == 1

        # Check list item content
        item = dialog.results_list.item(0)
        assert "0x00005000" in item.text()
        assert "2,048 bytes" in item.text()
        assert "32" in item.text()  # Tiles
        assert "85%" in item.text()  # Confidence

    def test_search_complete_handler(self, mock_search_dialog):
        """Test search completion handling."""
        dialog = mock_search_dialog

        # Add some results first
        dialog.current_results = [Mock(), Mock(), Mock()]
        dialog.search_history = [SearchHistoryEntry(
            timestamp=datetime.now(),
            search_type="Test",
            query="test",
            filters=Mock(),
            results_count=0
        )]

        dialog._search_complete([Mock(), Mock(), Mock()])

        # Check UI state reset
        assert dialog.search_button.isEnabled() is True
        assert dialog.stop_button.isEnabled() is False
        assert dialog.progress_bar.isVisible() is False

        # Check history updated
        assert dialog.search_history[-1].results_count == 3
        assert "3 sprites found" in dialog.results_label.text()

    def test_search_error_handler(self, mock_search_dialog):
        """Test search error handling."""
        dialog = mock_search_dialog

        error_msg = "Test error message"
        dialog._search_error(error_msg)

        # Check UI state reset
        assert dialog.search_button.isEnabled() is True
        assert dialog.stop_button.isEnabled() is False
        assert dialog.progress_bar.isVisible() is False

        # Check error message displayed
        assert error_msg in dialog.results_label.text()

    def test_stop_search(self, mock_search_dialog):
        """Test stopping active search."""
        dialog = mock_search_dialog

        # Mock running worker
        mock_worker = Mock()
        mock_worker.isRunning.return_value = True
        dialog.search_worker = mock_worker

        dialog._stop_search()

        # Verify worker cancellation
        mock_worker.cancel.assert_called_once()
        assert "Search cancelled" in dialog.results_label.text()

    def test_result_selection_signal(self, mock_search_dialog, qtbot):
        """Test result selection emits sprite_selected signal."""
        dialog = mock_search_dialog

        # Add a result
        result = SearchResult(
            offset=0x5000,
            size=2048,
            tile_count=32,
            compressed_size=1024,
            confidence=0.85,
            metadata={}
        )
        dialog._add_result(result)

        # Track signal emission
        with qtbot.waitSignal(dialog.sprite_selected, timeout=1000) as blocker:
            # Double-click the result
            item = dialog.results_list.item(0)
            dialog._on_result_selected(item)

        # Verify signal was emitted with correct offset
        assert blocker.args[0] == 0x5000

    def test_clear_history(self, mock_search_dialog):
        """Test clearing search history."""
        dialog = mock_search_dialog

        # Add some history
        dialog.search_history = [Mock(), Mock()]
        dialog.history_list.addItem("Test 1")
        dialog.history_list.addItem("Test 2")

        with patch.object(dialog, "_save_history") as mock_save:
            dialog._clear_history()

        # Verify history cleared
        assert len(dialog.search_history) == 0
        assert dialog.history_list.count() == 0
        mock_save.assert_called_once()

    def test_progress_update(self, mock_search_dialog):
        """Test progress bar updates."""
        dialog = mock_search_dialog

        dialog._update_progress(50, 100)

        assert dialog.progress_bar.maximum() == 100
        assert dialog.progress_bar.value() == 50

    def test_similarity_slider_label_update(self, mock_search_dialog):
        """Test similarity slider updates label."""
        dialog = mock_search_dialog

        # Simulate slider change
        dialog.similarity_slider.setValue(75)
        dialog.similarity_slider.valueChanged.emit(75)

        assert dialog.similarity_label.text() == "75%"


@pytest.mark.mock_gui
class TestAdvancedSearchDialogMocked:
    """Test AdvancedSearchDialog with mocked Qt components."""

    def test_history_save_load_functionality(self, temp_rom_file):
        """Test saving and loading search history."""
        with patch("ui.dialogs.advanced_search_dialog.SearchWorker"):
            dialog = AdvancedSearchDialog(temp_rom_file)

        # Add history entry
        entry = SearchHistoryEntry(
            timestamp=datetime.now(),
            search_type="Test",
            query="0x1000-0x2000",
            filters=SearchFilter(
                min_size=1024, max_size=65536, min_tiles=4, max_tiles=256,
                alignment=0x100, include_compressed=True,
                include_uncompressed=False, confidence_threshold=0.7
            ),
            results_count=5
        )
        dialog.search_history.append(entry)

        # Save history to temporary file
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir) / "test_history.json"

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)

                # Save and load
                dialog._save_history()

                # Create new dialog and load
                new_dialog = AdvancedSearchDialog(temp_rom_file)
                new_dialog._load_history()

                # Verify history loaded
                assert len(new_dialog.search_history) == 1
                loaded_entry = new_dialog.search_history[0]
                assert loaded_entry.search_type == "Test"
                assert loaded_entry.query == "0x1000-0x2000"
                assert loaded_entry.results_count == 5


@pytest.mark.integration
class TestSearchWorkerIntegration:
    """Integration tests with real SearchWorker execution."""

    def test_worker_thread_lifecycle(self, temp_rom_file, manager_context_factory):
        """Test SearchWorker thread lifecycle with proper manager context."""
        with manager_context_factory() as context:
            params = {
                "rom_path": temp_rom_file,
                "start_offset": 0x0,
                "end_offset": 0x1000,
                "num_workers": 1,
                "step_size": 0x100
            }

            # Mock the ParallelSpriteFinder to avoid actual search and thread pool creation
            with patch("ui.dialogs.advanced_search_dialog.ParallelSpriteFinder") as mock_finder_class:
                mock_finder = Mock()
                mock_finder.shutdown = Mock()  # Add shutdown method
                mock_finder_class.return_value = mock_finder
                mock_finder.search_parallel.return_value = []

                worker = SearchWorker("parallel", params)

                # Track signal emissions
                error_calls = []
                worker.error.connect(lambda e: error_calls.append(e))

                # Start and wait for completion
                worker.start()
                worker.wait(5000)  # 5 second timeout

                # Verify completion - the worker should complete successfully
                assert len(error_calls) == 0, f"Worker reported errors: {error_calls}"
                assert not worker.isRunning(), "Worker thread did not complete"
                assert mock_finder.search_parallel.called, "ParallelSpriteFinder.search_parallel was not called"
                
                # Clean up worker
                if worker.isRunning():
                    worker.cancel()
                    worker.wait(1000)

    def test_worker_cancellation_during_execution(self, temp_rom_file, manager_context_factory):
        """Test worker cancellation during execution with proper manager context."""
        with manager_context_factory() as context:
            params = {
                "rom_path": temp_rom_file,
                "start_offset": 0x0,
                "end_offset": 0x100000,  # Large range
                "num_workers": 1,
                "step_size": 0x100
            }

            # Mock finder with slow operation
            with patch("ui.dialogs.advanced_search_dialog.ParallelSpriteFinder") as mock_finder_class:
                mock_finder = Mock()
                mock_finder.shutdown = Mock()  # Add shutdown method
                mock_finder_class.return_value = mock_finder

                worker = SearchWorker("parallel", params)

                # Make search_parallel check cancellation
                def slow_search(*args, **kwargs):
                    cancellation_token = kwargs.get("cancellation_token")
                    if cancellation_token and cancellation_token.is_set():
                        return []
                    return []

                mock_finder.search_parallel.side_effect = slow_search

                # Start worker
                worker.start()

                # Cancel immediately
                worker.cancel()

                # Wait for completion
                worker.wait(5000)

                # Should complete quickly due to cancellation
                assert not worker.isRunning()
                assert worker.is_set() is True
                
                # Clean up worker
                if worker.isRunning():
                    worker.cancel()
                    worker.wait(1000)


# ============================================================================
# Manager Context Integration Tests
# ============================================================================

class TestSearchDialogManagerContextIntegration:
    """Test search dialog integration with manager context system."""
    
    def test_search_dialog_manager_access(self, safe_qtbot, temp_rom_file, manager_context_factory):
        """Test that AdvancedSearchDialog can access managers through context."""
        with manager_context_factory() as context:
            with patch("ui.dialogs.advanced_search_dialog.SearchWorker"):
                dialog = AdvancedSearchDialog(temp_rom_file)
                safe_qtbot.addWidget(dialog)
                
                # Verify dialog can access required managers
                extraction_manager = context.get_manager("extraction", object)
                assert extraction_manager is not None
                
                session_manager = context.get_manager("session", object)
                assert session_manager is not None
                
                # Clean up
                dialog.close()
    
    def test_search_worker_context_isolation(self, temp_rom_file, manager_context_factory):
        """Test that SearchWorker operations are properly isolated between contexts."""
        results = {"context1_ops": 0, "context2_ops": 0, "errors": []}
        
        class ContextSearchWorker(SearchWorker):
            def __init__(self, search_type, params, context_name):
                super().__init__(search_type, params)
                self.context_name = context_name
            
            def run(self):
                try:
                    # Simulate work with context identification
                    for i in range(3):
                        if self.context_name == "context1":
                            results["context1_ops"] += 1
                        else:
                            results["context2_ops"] += 1
                        import time
                        time.sleep(0.01)
                    
                    self.search_complete.emit([])
                except Exception as e:
                    results["errors"].append(str(e))
                    self.error.emit(str(e))
        
        # Mock ParallelSpriteFinder to avoid thread pool creation
        with patch("ui.dialogs.advanced_search_dialog.ParallelSpriteFinder") as mock_finder_class:
            mock_finder = Mock()
            mock_finder.shutdown = Mock()
            mock_finder_class.return_value = mock_finder
            mock_finder.search_parallel.return_value = []
            
            # Create workers with different contexts
            with manager_context_factory(name="context1") as ctx1:
                worker1 = ContextSearchWorker("parallel", {"rom_path": temp_rom_file}, "context1")
            
            with manager_context_factory(name="context2") as ctx2:
                worker2 = ContextSearchWorker("parallel", {"rom_path": temp_rom_file}, "context2")
            
            # Start both workers
            worker1.start()
            worker2.start()
            
            # Wait for completion
            worker1.wait(3000)
            worker2.wait(3000)
            
            # Verify both contexts operated independently
            assert results["context1_ops"] == 3
            assert results["context2_ops"] == 3
            assert len(results["errors"]) == 0
            
            # Clean up workers
            for worker in [worker1, worker2]:
                if worker.isRunning():
                    worker.cancel()
                    worker.wait(1000)
    
    def test_search_dialog_thread_cleanup(self, safe_qtbot, temp_rom_file, manager_context_factory):
        """Test that SearchDialog properly cleans up worker threads."""
        with manager_context_factory() as context:
            with patch("ui.dialogs.advanced_search_dialog.SearchWorker") as mock_worker_class:
                mock_worker = Mock()
                mock_worker.isRunning.return_value = False
                mock_worker.cancel = Mock()
                mock_worker.wait = Mock()
                mock_worker_class.return_value = mock_worker
                
                dialog = AdvancedSearchDialog(temp_rom_file)
                safe_qtbot.addWidget(dialog)
                
                # Start a mock search
                dialog.search_worker = mock_worker
                mock_worker.isRunning.return_value = True
                
                # Close dialog (should trigger cleanup)
                dialog.close()
                
                # Verify worker cleanup was attempted
                mock_worker.cancel.assert_called()
                mock_worker.wait.assert_called_with(1000)
