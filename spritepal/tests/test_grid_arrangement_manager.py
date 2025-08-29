"""
Unit tests for GridArrangementManager and related classes
"""
from __future__ import annotations

from unittest.mock import Mock

import pytest

from ui.row_arrangement.grid_arrangement_manager import (
# Systematic pytest markers applied based on test content analysis

    ArrangementType,
    GridArrangementManager,
    TileGroup,
    TilePosition,
)

pytestmark = [
    pytest.mark.headless,
    pytest.mark.mock_only,
    pytest.mark.no_qt,
    pytest.mark.parallel_safe,
    pytest.mark.rom_data,
    pytest.mark.unit,
    pytest.mark.ci_safe,
    pytest.mark.signals_slots,
    pytest.mark.slow,
]
class TestTilePosition:
    """Test the TilePosition dataclass"""

    def test_creation(self):
        """Test creating tile positions"""
        pos = TilePosition(5, 10)
        assert pos.row == 5
        assert pos.col == 10

    def test_equality(self):
        """Test tile position equality"""
        pos1 = TilePosition(1, 2)
        pos2 = TilePosition(1, 2)
        pos3 = TilePosition(2, 1)

        assert pos1 == pos2
        assert pos1 != pos3
        assert pos2 != pos3

    def test_hash(self):
        """Test tile position hashing for sets and dicts"""
        pos1 = TilePosition(1, 2)
        pos2 = TilePosition(1, 2)
        pos3 = TilePosition(2, 1)

        # Same positions should hash the same
        assert hash(pos1) == hash(pos2)
        assert hash(pos1) != hash(pos3)

        # Should work in sets
        pos_set = {pos1, pos2, pos3}
        assert len(pos_set) == 2  # pos1 and pos2 are duplicates

    def test_equality_with_other_types(self):
        """Test equality with non-TilePosition objects"""
        pos = TilePosition(1, 2)
        assert pos != (1, 2)
        assert pos != "1,2"
        assert pos is not None
        assert pos != 42

class TestTileGroup:
    """Test the TileGroup dataclass"""

    def test_creation_basic(self):
        """Test creating basic tile groups"""
        tiles = [TilePosition(0, 0), TilePosition(0, 1)]
        group = TileGroup("test_group", tiles, 2, 1)

        assert group.id == "test_group"
        assert group.tiles == tiles
        assert group.width == 2
        assert group.height == 1
        assert group.name is None

    def test_creation_with_name(self):
        """Test creating tile groups with names"""
        tiles = [TilePosition(1, 1)]
        group = TileGroup("id", tiles, 1, 1, "Named Group")

        assert group.name == "Named Group"

    def test_empty_tiles(self):
        """Test creating group with empty tiles list"""
        group = TileGroup("empty", [], 0, 0)
        assert group.tiles == []
        assert group.width == 0
        assert group.height == 0

class TestArrangementType:
    """Test the ArrangementType enum"""

    def test_enum_values(self):
        """Test enum values match expected strings"""
        assert ArrangementType.ROW.value == "row"
        assert ArrangementType.COLUMN.value == "column"
        assert ArrangementType.TILE.value == "tile"
        assert ArrangementType.GROUP.value == "group"

    def test_enum_members(self):
        """Test all expected enum members exist"""
        expected_members = {"ROW", "COLUMN", "TILE", "GROUP"}
        actual_members = {member.name for member in ArrangementType}
        assert actual_members == expected_members

class TestGridArrangementManager:
    """Test the GridArrangementManager class"""

    def test_init_valid_dimensions(self):
        """Test initialization with valid dimensions"""
        manager = GridArrangementManager(5, 8)
        assert manager.total_rows == 5
        assert manager.total_cols == 8
        assert manager.get_arranged_tiles() == []
        assert manager.get_arranged_count() == 0

    def test_init_invalid_dimensions(self):
        """Test initialization with invalid dimensions"""
        with pytest.raises(ValueError, match="Invalid grid dimensions"):
            GridArrangementManager(0, 5)

        with pytest.raises(ValueError, match="Invalid grid dimensions"):
            GridArrangementManager(5, 0)

        with pytest.raises(ValueError, match="Invalid grid dimensions"):
            GridArrangementManager(-1, 5)

        with pytest.raises(ValueError, match="Invalid grid dimensions"):
            GridArrangementManager(5, -1)

    def test_add_tile_valid(self):
        """Test adding valid tiles"""
        manager = GridArrangementManager(3, 3)

        # Mock signals to test emissions
        manager.tile_added = Mock()
        manager.arrangement_changed = Mock()

        pos = TilePosition(1, 1)
        result = manager.add_tile(pos)

        assert result is True
        assert manager.get_arranged_count() == 1
        assert pos in manager.get_arranged_tiles()
        assert manager.is_tile_arranged(pos)

        # Check signals were emitted
        manager.tile_added.emit.assert_called_once_with(pos)
        manager.arrangement_changed.emit.assert_called_once()

    def test_add_tile_invalid_position(self):
        """Test adding tiles outside grid bounds"""
        manager = GridArrangementManager(3, 3)

        # Test positions outside bounds
        invalid_positions = [
            TilePosition(-1, 0),  # Negative row
            TilePosition(0, -1),  # Negative col
            TilePosition(3, 0),  # Row too large
            TilePosition(0, 3),  # Col too large
            TilePosition(5, 5),  # Both too large
        ]

        for pos in invalid_positions:
            result = manager.add_tile(pos)
            assert result is False
            assert manager.get_arranged_count() == 0

    def test_add_tile_duplicate(self):
        """Test adding duplicate tiles"""
        manager = GridArrangementManager(3, 3)
        pos = TilePosition(1, 1)

        # Add tile first time
        result1 = manager.add_tile(pos)
        assert result1 is True
        assert manager.get_arranged_count() == 1

        # Try to add same tile again
        result2 = manager.add_tile(pos)
        assert result2 is False
        assert manager.get_arranged_count() == 1  # Should not change

    def test_remove_tile_valid(self):
        """Test removing valid tiles"""
        manager = GridArrangementManager(3, 3)
        pos = TilePosition(1, 1)

        # Add tile first
        manager.add_tile(pos)
        assert manager.get_arranged_count() == 1

        # Mock signals
        manager.tile_removed = Mock()
        manager.arrangement_changed = Mock()

        # Remove tile
        result = manager.remove_tile(pos)
        assert result is True
        assert manager.get_arranged_count() == 0
        assert not manager.is_tile_arranged(pos)

        # Check signals were emitted
        manager.tile_removed.emit.assert_called_once_with(pos)
        manager.arrangement_changed.emit.assert_called_once()

    def test_remove_tile_not_arranged(self):
        """Test removing tiles that aren't arranged"""
        manager = GridArrangementManager(3, 3)
        pos = TilePosition(1, 1)

        result = manager.remove_tile(pos)
        assert result is False
        assert manager.get_arranged_count() == 0

    def test_add_row_valid(self):
        """Test adding valid rows"""
        manager = GridArrangementManager(3, 3)

        # Mock signals
        manager.arrangement_changed = Mock()

        result = manager.add_row(1)
        assert result is True
        assert manager.get_arranged_count() == 3  # 3 tiles in row

        # Check all tiles in row are arranged
        for col in range(3):
            assert manager.is_tile_arranged(TilePosition(1, col))

        manager.arrangement_changed.emit.assert_called_once()

    def test_add_row_invalid_index(self):
        """Test adding rows with invalid indices"""
        manager = GridArrangementManager(3, 3)

        # Test invalid row indices
        assert manager.add_row(-1) is False
        assert manager.add_row(3) is False
        assert manager.add_row(10) is False

        assert manager.get_arranged_count() == 0

    def test_add_row_with_conflicting_tiles(self):
        """Test adding row when some tiles are already arranged"""
        manager = GridArrangementManager(3, 3)

        # Add a single tile in the row
        manager.add_tile(TilePosition(1, 1))

        # Try to add the whole row - should succeed, adding the other tiles
        result = manager.add_row(1)
        assert result is True
        assert manager.get_arranged_count() == 3  # All tiles in the row

    def test_add_column_valid(self):
        """Test adding valid columns"""
        manager = GridArrangementManager(3, 3)

        # Mock signals
        manager.arrangement_changed = Mock()

        result = manager.add_column(1)
        assert result is True
        assert manager.get_arranged_count() == 3  # 3 tiles in column

        # Check all tiles in column are arranged
        for row in range(3):
            assert manager.is_tile_arranged(TilePosition(row, 1))

        manager.arrangement_changed.emit.assert_called_once()

    def test_add_column_invalid_index(self):
        """Test adding columns with invalid indices"""
        manager = GridArrangementManager(3, 3)

        # Test invalid column indices
        assert manager.add_column(-1) is False
        assert manager.add_column(3) is False
        assert manager.add_column(10) is False

        assert manager.get_arranged_count() == 0

    def test_add_column_with_conflicting_tiles(self):
        """Test adding column when some tiles are already arranged"""
        manager = GridArrangementManager(3, 3)

        # Add a single tile in the column
        manager.add_tile(TilePosition(1, 1))

        # Try to add the whole column - should succeed, adding the other tiles
        result = manager.add_column(1)
        assert result is True
        assert manager.get_arranged_count() == 3  # All tiles in the column

    def test_add_group_valid(self):
        """Test adding valid groups"""
        manager = GridArrangementManager(3, 3)

        # Create a group
        tiles = [TilePosition(0, 0), TilePosition(0, 1)]
        group = TileGroup("test_group", tiles, 2, 1)

        # Mock signals
        manager.group_added = Mock()
        manager.arrangement_changed = Mock()

        result = manager.add_group(group)
        assert result is True
        assert manager.get_arranged_count() == 2

        # Check all tiles in group are arranged
        for tile in tiles:
            assert manager.is_tile_arranged(tile)
            assert manager.get_tile_group(tile) == "test_group"

        # Check group is stored
        assert "test_group" in manager.get_groups()
        assert manager.get_groups()["test_group"] == group

        # Check signals were emitted
        manager.group_added.emit.assert_called_once_with("test_group")
        manager.arrangement_changed.emit.assert_called_once()

    def test_add_group_with_conflicting_tiles(self):
        """Test adding group when some tiles are already arranged"""
        manager = GridArrangementManager(3, 3)

        # Add a single tile
        manager.add_tile(TilePosition(0, 0))

        # Try to add group with overlapping tile
        tiles = [TilePosition(0, 0), TilePosition(0, 1)]
        group = TileGroup("test_group", tiles, 2, 1)

        result = manager.add_group(group)
        assert result is False
        assert manager.get_arranged_count() == 1  # Only the single tile
        assert "test_group" not in manager.get_groups()

    def test_remove_group_valid(self):
        """Test removing valid groups"""
        manager = GridArrangementManager(3, 3)

        # Add a group
        tiles = [TilePosition(0, 0), TilePosition(0, 1)]
        group = TileGroup("test_group", tiles, 2, 1)
        manager.add_group(group)

        # Mock signals
        manager.group_removed = Mock()
        manager.arrangement_changed = Mock()

        result = manager.remove_group("test_group")
        assert result is True
        assert manager.get_arranged_count() == 0

        # Check all tiles are no longer arranged
        for tile in tiles:
            assert not manager.is_tile_arranged(tile)
            assert manager.get_tile_group(tile) is None

        # Check group is removed
        assert "test_group" not in manager.get_groups()

        # Check signals were emitted
        manager.group_removed.emit.assert_called_once_with("test_group")
        manager.arrangement_changed.emit.assert_called_once()

    def test_remove_group_nonexistent(self):
        """Test removing non-existent groups"""
        manager = GridArrangementManager(3, 3)

        result = manager.remove_group("nonexistent")
        assert result is False
        assert manager.get_arranged_count() == 0

    def test_remove_tile_in_group(self):
        """Test removing tile that's part of a group removes entire group"""
        manager = GridArrangementManager(3, 3)

        # Add a group
        tiles = [TilePosition(0, 0), TilePosition(0, 1)]
        group = TileGroup("test_group", tiles, 2, 1)
        manager.add_group(group)

        # Try to remove single tile from group
        result = manager.remove_tile(TilePosition(0, 0))
        assert result is True
        assert manager.get_arranged_count() == 0  # Entire group removed

        # Check all tiles are no longer arranged
        for tile in tiles:
            assert not manager.is_tile_arranged(tile)

    def test_create_group_from_selection_valid(self):
        """Test creating group from tile selection"""
        manager = GridArrangementManager(3, 3)

        # Create selection of tiles
        tiles = [TilePosition(0, 0), TilePosition(0, 1), TilePosition(1, 0)]

        group = manager.create_group_from_selection(tiles, "new_group", "Test Group")

        assert group is not None
        assert group.id == "new_group"
        assert group.name == "Test Group"
        assert group.tiles == tiles
        assert group.width == 2  # max_col - min_col + 1 = 1 - 0 + 1 = 2
        assert group.height == 2  # max_row - min_row + 1 = 1 - 0 + 1 = 2

        # Check group is added to manager
        assert manager.get_arranged_count() == 3
        assert "new_group" in manager.get_groups()

    def test_create_group_from_selection_empty(self):
        """Test creating group from empty selection"""
        manager = GridArrangementManager(3, 3)

        group = manager.create_group_from_selection([], "empty_group")
        assert group is None
        assert manager.get_arranged_count() == 0

    def test_create_group_from_selection_with_conflicts(self):
        """Test creating group when some tiles are already arranged"""
        manager = GridArrangementManager(3, 3)

        # Add a single tile
        manager.add_tile(TilePosition(0, 0))

        # Try to create group with overlapping tile
        tiles = [TilePosition(0, 0), TilePosition(0, 1)]
        group = manager.create_group_from_selection(tiles, "conflict_group")

        assert group is None
        assert manager.get_arranged_count() == 1  # Only the single tile

    def test_clear_arrangement(self):
        """Test clearing all arrangements"""
        manager = GridArrangementManager(3, 3)

        # Add various arrangements
        manager.add_tile(TilePosition(0, 0))
        manager.add_row(1)
        manager.add_column(2)

        tiles = [TilePosition(2, 0), TilePosition(2, 1)]
        group = TileGroup("test_group", tiles, 2, 1)
        manager.add_group(group)

        assert manager.get_arranged_count() > 0

        # Mock signals
        manager.arrangement_cleared = Mock()
        manager.arrangement_changed = Mock()

        manager.clear()

        assert manager.get_arranged_count() == 0
        assert manager.get_arranged_tiles() == []
        assert manager.get_groups() == {}
        assert manager.get_arrangement_order() == []

        # Check signals were emitted
        manager.arrangement_cleared.emit.assert_called_once()
        manager.arrangement_changed.emit.assert_called_once()

    def test_arrangement_order_tracking(self):
        """Test that arrangement order is tracked correctly"""
        manager = GridArrangementManager(3, 3)

        # Add arrangements in specific order - now overlaps should work!
        manager.add_tile(TilePosition(0, 0))
        manager.add_row(1)
        manager.add_column(2)

        tiles = [TilePosition(2, 0), TilePosition(2, 1)]
        group = TileGroup("test_group", tiles, 2, 1)
        manager.add_group(group)

        order = manager.get_arrangement_order()

        # Check order is correct
        assert len(order) == 4
        assert order[0] == (ArrangementType.TILE, "0,0")
        assert order[1] == (ArrangementType.ROW, "1")
        assert order[2] == (ArrangementType.COLUMN, "2")
        assert order[3] == (ArrangementType.GROUP, "test_group")

    def test_is_row_fully_arranged(self):
        """Test checking if entire row is arranged"""
        manager = GridArrangementManager(3, 3)

        # Initially no rows are arranged
        assert not manager.is_row_fully_arranged(0)
        assert not manager.is_row_fully_arranged(1)
        assert not manager.is_row_fully_arranged(2)

        # Add partial row
        manager.add_tile(TilePosition(0, 0))
        manager.add_tile(TilePosition(0, 1))
        assert not manager.is_row_fully_arranged(0)  # Missing one tile

        # Complete the row
        manager.add_tile(TilePosition(0, 2))
        assert manager.is_row_fully_arranged(0)

        # Add full row using add_row
        manager.add_row(1)
        assert manager.is_row_fully_arranged(1)

    def test_is_column_fully_arranged(self):
        """Test checking if entire column is arranged"""
        manager = GridArrangementManager(3, 3)

        # Initially no columns are arranged
        assert not manager.is_column_fully_arranged(0)
        assert not manager.is_column_fully_arranged(1)
        assert not manager.is_column_fully_arranged(2)

        # Add partial column
        manager.add_tile(TilePosition(0, 0))
        manager.add_tile(TilePosition(1, 0))
        assert not manager.is_column_fully_arranged(0)  # Missing one tile

        # Complete the column
        manager.add_tile(TilePosition(2, 0))
        assert manager.is_column_fully_arranged(0)

        # Add full column using add_column
        manager.add_column(1)
        assert manager.is_column_fully_arranged(1)

    def test_get_row_tiles(self):
        """Test getting all tiles in a row"""
        manager = GridArrangementManager(3, 4)

        row_tiles = manager.get_row_tiles(1)

        assert len(row_tiles) == 4
        expected_tiles = [
            TilePosition(1, 0),
            TilePosition(1, 1),
            TilePosition(1, 2),
            TilePosition(1, 3),
        ]
        assert row_tiles == expected_tiles

    def test_get_column_tiles(self):
        """Test getting all tiles in a column"""
        manager = GridArrangementManager(4, 3)

        col_tiles = manager.get_column_tiles(1)

        assert len(col_tiles) == 4
        expected_tiles = [
            TilePosition(0, 1),
            TilePosition(1, 1),
            TilePosition(2, 1),
            TilePosition(3, 1),
        ]
        assert col_tiles == expected_tiles

    def test_reorder_arrangement_valid(self):
        """Test reordering arrangement"""
        manager = GridArrangementManager(3, 3)

        # Add arrangements
        manager.add_tile(TilePosition(0, 0))
        manager.add_row(1)
        manager.add_column(2)

        original_order = manager.get_arrangement_order()

        # Reorder
        new_order = [original_order[2], original_order[0], original_order[1]]
        manager.reorder_arrangement(new_order)

        assert manager.get_arrangement_order() == new_order

    def test_reorder_arrangement_invalid(self):
        """Test reordering with invalid order"""
        manager = GridArrangementManager(3, 3)

        # Add arrangements
        manager.add_tile(TilePosition(0, 0))
        manager.add_row(1)

        original_order = manager.get_arrangement_order()

        # Try to reorder with different items
        invalid_order = [(ArrangementType.TILE, "1,1"), (ArrangementType.ROW, "2")]

        with pytest.raises(
            ValueError, match="New order must contain all current arrangement items"
        ):
            manager.reorder_arrangement(invalid_order)

        # Original order should be unchanged
        assert manager.get_arrangement_order() == original_order

    def test_row_column_overlap(self):
        """Test that row and column additions handle overlaps correctly"""
        manager = GridArrangementManager(3, 3)

        # Add row 1
        assert manager.add_row(1) is True
        assert manager.get_arranged_count() == 3

        # Add column 1 - should succeed, with overlap at (1,1)
        assert manager.add_column(1) is True
        assert (
            manager.get_arranged_count() == 5
        )  # 3 from row + 2 new from column (excluding overlap)

        # Verify specific tiles
        assert manager.is_tile_arranged(TilePosition(1, 0))  # From row
        assert manager.is_tile_arranged(TilePosition(1, 1))  # From row (overlap point)
        assert manager.is_tile_arranged(TilePosition(1, 2))  # From row
        assert manager.is_tile_arranged(TilePosition(0, 1))  # From column
        assert manager.is_tile_arranged(TilePosition(2, 1))  # From column

        # Check that both operations are tracked
        order = manager.get_arrangement_order()
        assert len(order) == 2
        assert order[0] == (ArrangementType.ROW, "1")
        assert order[1] == (ArrangementType.COLUMN, "1")