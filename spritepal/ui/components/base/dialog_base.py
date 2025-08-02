"""
Base dialog class for SpritePal that enforces proper initialization patterns.

This class ensures that instance variables are declared before setup methods are called,
preventing the common bug where widgets created in setup methods are overwritten by
late instance variable declarations.
"""

from typing import Any, ClassVar

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QWidget
from utils.logging_config import get_logger

logger = get_logger(__name__)


class InitializationOrderError(Exception):
    """Raised when initialization order requirements are violated."""


class DialogBaseMeta(type(QDialog)):
    """Metaclass to enforce initialization order in dialogs."""

    def __new__(mcs, name: str, bases: tuple, namespace: dict) -> type:
        # Create the class
        cls = super().__new__(mcs, name, bases, namespace)

        # For DialogBase itself, don't add checks
        if name == "DialogBase":
            return cls

        # Wrap __init__ to add initialization checks
        original_init = cls.__init__

        def checked_init(self, *args, **kwargs):
            # Track initialization state
            self._initialization_phase = "pre_init"
            self._declared_variables: set[str] = set()
            self._setup_called = False

            # Call original init
            original_init(self, *args, **kwargs)

            # Verify initialization completed properly
            if hasattr(self, "_setup_ui") and not self._setup_called:
                raise InitializationOrderError(
                    f"{cls.__name__} has _setup_ui method but didn't call super().__init__()"
                )

        cls.__init__ = checked_init
        return cls


class DialogBase(QDialog, metaclass=DialogBaseMeta):
    """
    Base class for all SpritePal dialogs with enforced initialization patterns.

    Subclasses MUST follow this pattern:

    ```python
    class MyDialog(DialogBase):
        def __init__(self, parent: QWidget | None = None):
            # Step 1: Declare instance variables
            self.my_widget: QWidget | None = None
            self.my_data: list[str] = []

            # Step 2: Call parent init (this calls _setup_ui)
            super().__init__(parent)

        def _setup_ui(self):
            # Step 3: Create widgets (safe - variables already declared)
            self.my_widget = QWidget()
    ```
    """

    # Class-level registry of known widget attributes to check
    _WIDGET_ATTRIBUTES: ClassVar[list[str]] = [
        "rom_map", "offset_widget", "scan_controls", "import_export",
        "status_panel", "preview_widget", "mode_selector", "status_label",
        "dumps_dir_edit", "cache_enabled_check", "source_list", "arranged_list",
        "available_list"
    ]

    def __init__(
        self,
        parent: QWidget | None = None,
        title: str | None = None,
        modal: bool = True,
        min_size: tuple[int | None, int | None] | None = None,
        size: tuple[int, int] | None = None,
        with_status_bar: bool = False,
        with_button_box: bool = True,
        default_tab: int | None = None,
        orientation: Any = None,  # For splitter dialogs
        splitter_handle_width: int = 8,  # For splitter dialogs
        **kwargs  # Accept any additional keyword arguments
    ):
        """
        Initialize the dialog base.

        Args:
            parent: Parent widget (optional)
            title: Window title (optional)
            modal: Whether dialog should be modal (default: True)
            min_size: Minimum size as (width, height) tuple, None for no limit
            size: Fixed size as (width, height) tuple (optional)
            with_status_bar: Whether to add a status bar
            with_button_box: Whether to add a standard button box (default: True)
            default_tab: Default tab index for tabbed dialogs (optional)
            orientation: Splitter orientation for splitter dialogs (optional)
            splitter_handle_width: Handle width for splitter dialogs (default: 8)
            **kwargs: Additional keyword arguments (ignored, for compatibility)
        """
        # Initialize tracking before calling Qt's init
        self._initialization_phase = "during_init"
        self._declared_variables: set[str] = set()
        self._setup_called = False

        # Store configuration for subclasses
        self._default_tab = default_tab
        self._orientation = orientation
        self._splitter_handle_width = splitter_handle_width

        # Record all instance variables declared before super().__init__()
        try:
            for attr_name in dir(self):
                if not attr_name.startswith("_") and hasattr(self, attr_name):
                    self._declared_variables.add(attr_name)
        except RuntimeError:
            # Can't access attributes before Qt init, that's ok
            pass

        # Call Qt's init
        super().__init__(parent)

        # Set standard dialog properties
        if modal:
            self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # Apply optional settings
        if title:
            self.setWindowTitle(title)

        if min_size:
            width, height = min_size
            if width is not None:
                self.setMinimumWidth(width)
            if height is not None:
                self.setMinimumHeight(height)

        if size:
            width, height = size
            self.resize(width, height)

        if with_status_bar:
            from PyQt6.QtWidgets import QStatusBar
            self.status_bar = QStatusBar(self)
            self.setStatusBar = lambda: self.status_bar  # Mock for dialogs
        else:
            self.status_bar = None

        # Create main layout for dialogs that need it
        from PyQt6.QtWidgets import QDialogButtonBox, QTabWidget, QVBoxLayout, QWidget
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)

        # Create content widget
        self.content_widget = QWidget()
        self.main_layout.addWidget(self.content_widget)

        # Create button box if requested
        if with_button_box:
            self.button_box = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
            self.button_box.accepted.connect(self.accept)
            self.button_box.rejected.connect(self.reject)
            self.main_layout.addWidget(self.button_box)
        else:
            self.button_box = None

        # For tabbed dialogs, create tab widget
        self._tab_widget: QTabWidget | None = None
        self.tab_widget = self._tab_widget  # Public alias for tests

        # For splitter dialogs
        self.main_splitter = None  # Will be set by add_horizontal_splitter

        # If orientation is specified, create a splitter automatically
        if orientation is not None:
            from PyQt6.QtWidgets import QSplitter
            self.main_splitter = QSplitter(orientation)
            self.main_splitter.setHandleWidth(self._splitter_handle_width)
            self.main_layout.addWidget(self.main_splitter)

        # Call setup method if it exists
        if hasattr(self, "_setup_ui"):
            self._initialization_phase = "setup"
            self._setup_ui()
            self._setup_called = True

        # Verify no widget attributes were overwritten
        self._verify_initialization()
        self._initialization_phase = "complete"

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Override setattr to catch initialization order bugs.

        This detects when instance variables are assigned None after setup methods,
        which would overwrite already-created widgets.
        """
        # Allow private attributes and initialization tracking
        if name.startswith("_"):
            super().__setattr__(name, value)
            return

        # During initialization phase, track what's happening
        if hasattr(self, "_initialization_phase"):
            phase = self._initialization_phase

            # Check for suspicious patterns
            if (phase == "setup" and
                value is None and
                name in self._WIDGET_ATTRIBUTES):
                logger.warning(
                    f"{self.__class__.__name__}: Assigning None to '{name}' "
                    f"during setup phase - possible initialization order bug!"
                )

            # After setup, check for late assignments
            elif (phase == "complete" and
                  value is None and
                  name not in self._declared_variables and
                  name in self._WIDGET_ATTRIBUTES):
                raise InitializationOrderError(
                    f"{self.__class__.__name__}: Cannot assign None to '{name}' "
                    f"after setup - this would overwrite an existing widget! "
                    f"Declare '{name}' before calling super().__init__()"
                )

        super().__setattr__(name, value)

    def _verify_initialization(self) -> None:
        """Verify that initialization followed the correct pattern."""
        # Check for common widget attributes that should not be None
        for attr_name in self._WIDGET_ATTRIBUTES:
            if hasattr(self, attr_name):
                value = getattr(self, attr_name)
                if value is None and attr_name not in self._declared_variables:
                    logger.warning(
                        f"{self.__class__.__name__}: Widget attribute '{attr_name}' "
                        f"is None after initialization - was it properly created?"
                    )

    def _setup_ui(self) -> None:
        """
        Set up the dialog UI.

        Subclasses MAY implement this method to create their UI.
        This is called automatically by __init__ after instance variables
        are declared but before the dialog is shown.

        If not implemented, subclasses should set up their UI in __init__.
        """
        # Optional method - subclasses can implement if needed

    def set_content_layout(self, layout: Any) -> None:
        """
        Set the content layout for the dialog.

        Args:
            layout: The layout to set as the dialog's content
        """
        if hasattr(layout, "setContentsMargins"):
            layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addLayout(layout)

    def add_tab(self, widget: QWidget, label: str) -> None:
        """
        Add a tab to the dialog (for tabbed dialogs).

        Args:
            widget: The widget to add as a tab
            label: The tab label
        """
        if not self._tab_widget:
            from PyQt6.QtWidgets import QTabWidget
            self._tab_widget = QTabWidget()
            self.tab_widget = self._tab_widget  # Update public alias
            self.main_layout.addWidget(self._tab_widget)

        self._tab_widget.addTab(widget, label)

        # Set default tab if specified
        if hasattr(self, "_default_tab") and self._default_tab is not None:
            self._tab_widget.setCurrentIndex(self._default_tab)

    def add_horizontal_splitter(self, handle_width: int | None = None) -> Any:
        """
        Add a horizontal splitter to the dialog (for splitter dialogs).

        Args:
            handle_width: Width of the splitter handle (uses default if not specified)

        Returns:
            The created splitter widget
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QSplitter

        if handle_width is None:
            handle_width = self._splitter_handle_width

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(handle_width)

        # If main_splitter already exists, add to it instead of main_layout
        if self.main_splitter is not None:
            self.main_splitter.addWidget(splitter)
        else:
            self.main_layout.addWidget(splitter)
            self.main_splitter = splitter

        return splitter

    def add_panel(self, widget: QWidget, stretch_factor: int = 1) -> None:
        """
        Add a panel to the dialog.

        Args:
            widget: The widget to add
            stretch_factor: Stretch factor for the widget
        """
        if self.main_splitter:
            # Add to splitter if it exists
            self.main_splitter.addWidget(widget)
            # Set stretch factor
            self.main_splitter.setStretchFactor(self.main_splitter.count() - 1, stretch_factor)
        else:
            # Otherwise add to main layout
            self.main_layout.addWidget(widget, stretch_factor)

    def add_button(self, text: str, callback: Any = None) -> Any:
        """
        Add a button to the dialog.

        Args:
            text: Button text
            callback: Optional callback function

        Returns:
            The created button
        """
        from PyQt6.QtWidgets import QPushButton

        button = QPushButton(text)
        if callback:
            button.clicked.connect(callback)
        return button

    def update_status(self, message: str) -> None:
        """
        Update the status bar message (for dialogs with status bars).

        Args:
            message: Status message to display
        """
        if hasattr(self, "status_bar") and self.status_bar:
            self.status_bar.showMessage(message)

    def set_current_tab(self, index: int) -> None:
        """
        Set the current tab for tabbed dialogs.

        Args:
            index: Tab index to switch to
        """
        if self._tab_widget:
            self._tab_widget.setCurrentIndex(index)

    def get_current_tab_index(self) -> int:
        """
        Get the current tab index for tabbed dialogs.

        Returns:
            Current tab index, or -1 if no tabs exist
        """
        if self._tab_widget:
            return self._tab_widget.currentIndex()
        return -1

    def show_error(self, title: str, message: str) -> None:
        """
        Show an error message dialog.

        Args:
            title: Error dialog title
            message: Error message to display
        """
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(self, title, message)

    def show_info(self, title: str, message: str) -> None:
        """
        Show an information message dialog.

        Args:
            title: Info dialog title
            message: Info message to display
        """
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, title, message)

    def show_warning(self, title: str, message: str) -> None:
        """
        Show a warning message dialog.

        Args:
            title: Warning dialog title
            message: Warning message to display
        """
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, title, message)

    def confirm_action(self, title: str, message: str) -> bool:
        """
        Show a confirmation dialog.

        Args:
            title: Confirmation dialog title
            message: Confirmation message

        Returns:
            True if user confirmed, False otherwise
        """
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, title, message)
        return reply == QMessageBox.StandardButton.Yes
