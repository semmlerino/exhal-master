"""
Row arrangement state management
"""

from PyQt6.QtCore import QObject, pyqtSignal


class ArrangementManager(QObject):
    """Manages the state of arranged sprite rows"""

    # Signals
    arrangement_changed = pyqtSignal()  # Emitted when arrangement changes
    row_added = pyqtSignal(int)  # Emitted when a row is added
    row_removed = pyqtSignal(int)  # Emitted when a row is removed
    arrangement_cleared = pyqtSignal()  # Emitted when arrangement is cleared

    def __init__(self):
        super().__init__()
        self._arranged_rows: list[int] = []

    def add_row(self, row_index: int) -> bool:
        """Add a row to the arrangement

        Args:
            row_index: Index of the row to add

        Returns:
            True if row was added, False if already present
        """
        if row_index not in self._arranged_rows:
            self._arranged_rows.append(row_index)
            self.row_added.emit(row_index)
            self.arrangement_changed.emit()
            return True
        return False

    def remove_row(self, row_index: int) -> bool:
        """Remove a row from the arrangement

        Args:
            row_index: Index of the row to remove

        Returns:
            True if row was removed, False if not present
        """
        if row_index in self._arranged_rows:
            self._arranged_rows.remove(row_index)
            self.row_removed.emit(row_index)
            self.arrangement_changed.emit()
            return True
        return False

    def add_multiple_rows(self, row_indices: list[int]) -> int:
        """Add multiple rows to the arrangement

        Args:
            row_indices: List of row indices to add

        Returns:
            Number of rows actually added
        """
        added_count = 0
        for row_index in row_indices:
            if row_index not in self._arranged_rows:
                self._arranged_rows.append(row_index)
                added_count += 1

        if added_count > 0:
            self.arrangement_changed.emit()

        return added_count

    def remove_multiple_rows(self, row_indices: list[int]) -> int:
        """Remove multiple rows from the arrangement

        Args:
            row_indices: List of row indices to remove

        Returns:
            Number of rows actually removed
        """
        removed_count = 0
        for row_index in row_indices:
            if row_index in self._arranged_rows:
                self._arranged_rows.remove(row_index)
                removed_count += 1

        if removed_count > 0:
            self.arrangement_changed.emit()

        return removed_count

    def reorder_rows(self, new_order: list[int]) -> None:
        """Set a new order for the arranged rows

        Args:
            new_order: New list of row indices in desired order
        """
        self._arranged_rows = new_order.copy()
        self.arrangement_changed.emit()

    def clear(self) -> None:
        """Clear all arranged rows"""
        self._arranged_rows.clear()
        self.arrangement_cleared.emit()
        self.arrangement_changed.emit()

    def get_arranged_indices(self) -> list[int]:
        """Get the current list of arranged row indices

        Returns:
            Copy of the arranged rows list
        """
        return self._arranged_rows.copy()

    def get_arranged_count(self) -> int:
        """Get the number of arranged rows

        Returns:
            Number of rows in arrangement
        """
        return len(self._arranged_rows)

    def is_row_arranged(self, row_index: int) -> bool:
        """Check if a row is in the arrangement

        Args:
            row_index: Index of the row to check

        Returns:
            True if row is arranged, False otherwise
        """
        return row_index in self._arranged_rows
