"""
Base dialog classes for SpritePal UI architecture

Provides standard dialog foundations with consistent styling and behavior.
"""


from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget
)

from spritepal.ui.styles import get_dialog_button_box_style, get_splitter_style


class BaseDialog(QDialog):
    """
    Standard dialog foundation with consistent styling and behavior.

    Features:
    - Consistent modal setup and sizing
    - Integrated styling system
    - status bar support
    - Standardized button box handling
    - Window title and icon management
    """

    def __init__(
        self,
        parent=None,
        title: str = "Dialog",
        modal: bool = True,
        size: tuple[int, int | None] = None,
        min_size: tuple[int, int | None] = None,
        with_status_bar: bool = False,
        with_button_box: bool = True
    ):
        super().__init__(parent)

        # Store configuration
        self._with_status_bar = with_status_bar
        self._with_button_box = with_button_box

        # Set basic properties
        self.setWindowTitle(title)
        self.setModal(modal)

        # Set sizing
        if size:
            self.resize(*size)
        if min_size:
            if min_size[0] is not None:
                self.setMinimumWidth(min_size[0])
            if len(min_size) > 1 and min_size[1] is not None:
                self.setMinimumHeight(min_size[1])

        # Initialize UI components
        self.main_layout = QVBoxLayout(self)
        self.content_widget: QWidget | None = None
        self.status_bar: QStatusBar | None = None
        self.button_box: QDialogButtonBox | None = None

        self._setup_base_ui()

    def _setup_base_ui(self):
        """Set up the base dialog UI structure"""
        # Create content area (will be populated by subclasses)
        self.content_widget = QWidget()
        self.main_layout.addWidget(self.content_widget)

        # Add status bar if requested
        if self._with_status_bar:
            self.status_bar = QStatusBar()
            self.main_layout.addWidget(self.status_bar)

        # Add button box if requested
        if self._with_button_box:
            self.button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
            self.button_box.setStyleSheet(get_dialog_button_box_style())
            self.button_box.accepted.connect(self.accept)
            self.button_box.rejected.connect(self.reject)
            self.main_layout.addWidget(self.button_box)

    def set_content_layout(self, layout):
        """Set the layout for the content area"""
        if self.content_widget:
            self.content_widget.setLayout(layout)

    def add_button(self, text: str, role=QDialogButtonBox.ButtonRole.ActionRole, callback=None):
        """Add a custom button to the button box"""
        if not self.button_box:
            raise ValueError("Dialog was created without button box")

        button = self.button_box.addButton(text, role)
        if callback:
            _ = button.clicked.connect(callback)
        return button

    def update_status(self, message: str):
        """Update the status bar message"""
        if self.status_bar:
            self.status_bar.showMessage(message)

    def clear_status(self):
        """Clear the status bar message"""
        if self.status_bar:
            self.status_bar.clearMessage()


class SplitterDialog(BaseDialog):
    """
    Dialog with resizable splitter panels.

    Features:
    - Pre-configured styled splitters
    - Standard layout patterns for resizable panels
    - Automatic stretch factor handling
    - Consistent splitter styling
    """

    def __init__(
        self,
        parent=None,
        title: str = "Dialog",
        modal: bool = True,
        size: tuple[int, int | None] = None,
        min_size: tuple[int, int | None] = None,
        with_status_bar: bool = True,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        splitter_handle_width: int = 8
    ):
        self._orientation = orientation
        self._handle_width = splitter_handle_width

        super().__init__(
            parent=parent,
            title=title,
            modal=modal,
            size=size,
            min_size=min_size,
            with_status_bar=with_status_bar,
            with_button_box=True
        )

    def _setup_base_ui(self):
        """Set up splitter-based UI structure"""
        # Create main splitter
        self.main_splitter = QSplitter(self._orientation)
        self.main_splitter.setHandleWidth(self._handle_width)
        self.main_splitter.setStyleSheet(get_splitter_style(self._handle_width))

        self.main_layout.addWidget(self.main_splitter)

        # Add status bar if requested
        if self._with_status_bar:
            self.status_bar = QStatusBar()
            self.main_layout.addWidget(self.status_bar)

        # Add button box if requested
        if self._with_button_box:
            self.button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
            self.button_box.setStyleSheet(get_dialog_button_box_style())
            self.button_box.accepted.connect(self.accept)
            self.button_box.rejected.connect(self.reject)
            self.main_layout.addWidget(self.button_box)

    def add_panel(self, widget: QWidget, stretch_factor: int = 1) -> int:
        """Add a panel to the splitter"""
        self.main_splitter.addWidget(widget)
        index = self.main_splitter.count() - 1  # Get the index of the just-added widget
        self.main_splitter.setStretchFactor(index, stretch_factor)
        return index

    def add_vertical_splitter(self, handle_width: int = 8) -> QSplitter:
        """Add a nested vertical splitter as a panel"""
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(handle_width)
        splitter.setStyleSheet(get_splitter_style(handle_width))
        self.add_panel(splitter)
        return splitter

    def add_horizontal_splitter(self, handle_width: int = 8) -> QSplitter:
        """Add a nested horizontal splitter as a panel"""
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(handle_width)
        splitter.setStyleSheet(get_splitter_style(handle_width))
        self.add_panel(splitter)
        return splitter

    def set_panel_ratios(self, ratios: list[int]):
        """Set the size ratios for splitter panels"""
        if len(ratios) != self.main_splitter.count():
            raise ValueError(f"Expected {self.main_splitter.count()} ratios, got {len(ratios)}")

        for i, ratio in enumerate(ratios):
            self.main_splitter.setStretchFactor(i, ratio)


class TabbedDialog(BaseDialog):
    """
    Dialog with tabbed interface for multiple modes/views.

    Features:
    - Tab widget with consistent styling
    - Standard tab management utilities
    - Easy tab addition and configuration
    """

    def __init__(
        self,
        parent=None,
        title: str = "Dialog",
        modal: bool = True,
        size: tuple[int, int | None] = None,
        min_size: tuple[int, int | None] = None,
        with_status_bar: bool = False,
        default_tab: int = 0
    ):
        self._default_tab = default_tab

        super().__init__(
            parent=parent,
            title=title,
            modal=modal,
            size=size,
            min_size=min_size,
            with_status_bar=with_status_bar,
            with_button_box=True
        )

    def _setup_base_ui(self):
        """Set up tabbed UI structure"""
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # Add status bar if requested
        if self._with_status_bar:
            self.status_bar = QStatusBar()
            self.main_layout.addWidget(self.status_bar)

        # Add button box if requested
        if self._with_button_box:
            self.button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
            self.button_box.setStyleSheet(get_dialog_button_box_style())
            self.button_box.accepted.connect(self.accept)
            self.button_box.rejected.connect(self.reject)
            self.main_layout.addWidget(self.button_box)

    def add_tab(self, widget: QWidget, title: str) -> int:
        """Add a tab to the tab widget"""
        return self.tab_widget.addTab(widget, title)

    def set_current_tab(self, index: int):
        """Set the currently active tab"""
        self.tab_widget.setCurrentIndex(index)

    def get_current_tab_index(self) -> int:
        """Get the index of the currently active tab"""
        return self.tab_widget.currentIndex()

    def get_current_tab_widget(self) -> QWidget | None:
        """Get the widget of the currently active tab"""
        return self.tab_widget.currentWidget()

    def showEvent(self, a0):
        """Set default tab when dialog is shown"""
        super().showEvent(a0)
        if self._default_tab >= 0:
            self.set_current_tab(self._default_tab)
