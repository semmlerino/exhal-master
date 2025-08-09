"""
Base mock dialog infrastructure for testing.

This module provides lightweight mock dialogs that prevent blocking operations
while maintaining realistic Qt signal behavior.
"""

from typing import Any, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QDialog


class MockDialogBase(QObject):
    """
    Base class for all mock dialogs.

    Provides:
    - Non-blocking exec() method
    - Real Qt signals
    - Configurable return values
    - Automatic cleanup
    """

    # Standard dialog signals
    accepted = pyqtSignal()
    rejected = pyqtSignal()
    finished = pyqtSignal(int)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.result_value = QDialog.DialogCode.Accepted
        self._exec_called = False
        self._show_called = False

    def exec(self) -> int:
        """Non-blocking exec replacement."""
        self._exec_called = True
        # Emit finished signal asynchronously
        QTimer.singleShot(0, lambda: self.finished.emit(self.result_value))
        return self.result_value

    def show(self) -> None:
        """Non-blocking show method."""
        self._show_called = True

    def accept(self) -> None:
        """Accept the dialog."""
        self.result_value = QDialog.DialogCode.Accepted
        self.accepted.emit()
        self.finished.emit(self.result_value)

    def reject(self) -> None:
        """Reject the dialog."""
        self.result_value = QDialog.DialogCode.Rejected
        self.rejected.emit()
        self.finished.emit(self.result_value)

    def close(self) -> bool:
        """Close the dialog."""
        return True

    def deleteLater(self) -> None:
        """Schedule deletion."""
        pass


class MockMessageBox(MockDialogBase):
    """Mock QMessageBox for testing."""

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.text = ""
        self.informative_text = ""
        self.detailed_text = ""
        self.icon = None
        self.standard_buttons = None

    @staticmethod
    def information(parent: Any, title: str, text: str) -> int:
        """Mock information dialog."""
        return QDialog.DialogCode.Accepted

    @staticmethod
    def warning(parent: Any, title: str, text: str) -> int:
        """Mock warning dialog."""
        return QDialog.DialogCode.Accepted

    @staticmethod
    def critical(parent: Any, title: str, text: str) -> int:
        """Mock critical dialog."""
        return QDialog.DialogCode.Accepted

    @staticmethod
    def question(parent: Any, title: str, text: str,
                 buttons: Any = None, defaultButton: Any = None) -> int:
        """Mock question dialog."""
        return QDialog.DialogCode.Accepted


class MockFileDialog(MockDialogBase):
    """Mock QFileDialog for testing."""

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.selected_files = []
        self.selected_directory = ""

    @staticmethod
    def getOpenFileName(parent: Any, caption: str = "",
                        directory: str = "", filter: str = "") -> tuple[str, str]:
        """Mock file open dialog."""
        return "/test/file.txt", "All Files (*)"

    @staticmethod
    def getSaveFileName(parent: Any, caption: str = "",
                       directory: str = "", filter: str = "") -> tuple[str, str]:
        """Mock file save dialog."""
        return "/test/output.txt", "All Files (*)"

    @staticmethod
    def getExistingDirectory(parent: Any, caption: str = "",
                           directory: str = "") -> str:
        """Mock directory selection dialog."""
        return "/test/directory"


class MockInputDialog(MockDialogBase):
    """Mock QInputDialog for testing."""

    @staticmethod
    def getText(parent: Any, title: str, label: str,
                text: str = "") -> tuple[str, bool]:
        """Mock text input dialog."""
        return "test_input", True

    @staticmethod
    def getInt(parent: Any, title: str, label: str,
               value: int = 0, min: int = -2147483647,
               max: int = 2147483647, step: int = 1) -> tuple[int, bool]:
        """Mock integer input dialog."""
        return 42, True

    @staticmethod
    def getDouble(parent: Any, title: str, label: str,
                  value: float = 0.0, min: float = -2147483647.0,
                  max: float = 2147483647.0, decimals: int = 1) -> tuple[float, bool]:
        """Mock double input dialog."""
        return 3.14, True


class MockProgressDialog(MockDialogBase):
    """Mock QProgressDialog for testing."""

    # Progress dialog specific signals
    canceled = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.value = 0
        self.minimum = 0
        self.maximum = 100
        self.label_text = ""
        self._was_canceled = False

    def setValue(self, value: int) -> None:
        """Set progress value."""
        self.value = value

    def setLabelText(self, text: str) -> None:
        """Set label text."""
        self.label_text = text

    def wasCanceled(self) -> bool:
        """Check if canceled."""
        return self._was_canceled

    def cancel(self) -> None:
        """Cancel the dialog."""
        self._was_canceled = True
        self.canceled.emit()


def create_mock_dialog(dialog_type: str, **kwargs) -> MockDialogBase:
    """
    Factory function to create mock dialogs.

    Args:
        dialog_type: Type of dialog ('message', 'file', 'input', 'progress')
        **kwargs: Additional arguments for dialog creation

    Returns:
        Mock dialog instance
    """
    dialog_map = {
        'message': MockMessageBox,
        'file': MockFileDialog,
        'input': MockInputDialog,
        'progress': MockProgressDialog,
    }

    dialog_class = dialog_map.get(dialog_type, MockDialogBase)
    return dialog_class(**kwargs)


# Convenience function for patching
def patch_all_dialogs(monkeypatch):
    """
    Patch all Qt dialogs with mocks.

    Args:
        monkeypatch: pytest monkeypatch fixture
    """
    import PyQt6.QtWidgets as widgets

    monkeypatch.setattr(widgets, 'QMessageBox', MockMessageBox)
    monkeypatch.setattr(widgets, 'QFileDialog', MockFileDialog)
    monkeypatch.setattr(widgets, 'QInputDialog', MockInputDialog)
    monkeypatch.setattr(widgets, 'QProgressDialog', MockProgressDialog)
