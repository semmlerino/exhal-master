"""
Base dialog class for SpritePal that enforces proper initialization patterns.

This class ensures that instance variables are declared before setup methods are called,
preventing the common bug where widgets created in setup methods are overwritten by
late instance variable declarations.
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, List, Type

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QWidget

from spritepal.utils.logging_config import get_logger

logger = get_logger(__name__)


class InitializationOrderError(Exception):
    """Raised when initialization order requirements are violated."""


class DialogBaseMeta(type(QDialog)):
    """Metaclass to enforce initialization order in dialogs."""
    
    def __new__(mcs, name: str, bases: tuple, namespace: dict) -> Type:
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
    _WIDGET_ATTRIBUTES: ClassVar[List[str]] = [
        "rom_map", "offset_widget", "scan_controls", "import_export",
        "status_panel", "preview_widget", "mode_selector", "status_label",
        "dumps_dir_edit", "cache_enabled_check", "source_list", "arranged_list",
        "available_rows_widget", "arranged_rows_widget"
    ]
    
    def __init__(self, parent: QWidget | None = None):
        """
        Initialize the dialog base.
        
        Args:
            parent: Parent widget (optional)
        """
        # Initialize tracking before calling Qt's init
        self._initialization_phase = "during_init"
        self._declared_variables: set[str] = set()
        self._setup_called = False
        
        # Record all instance variables declared before super().__init__()
        for attr_name in dir(self):
            if not attr_name.startswith("_") and hasattr(self, attr_name):
                self._declared_variables.add(attr_name)
        
        # Call Qt's init
        super().__init__(parent)
        
        # Set standard dialog properties
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        
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
    
    @abstractmethod
    def _setup_ui(self) -> None:
        """
        Set up the dialog UI.
        
        Subclasses MUST implement this method to create their UI.
        This is called automatically by __init__ after instance variables
        are declared but before the dialog is shown.
        """
        raise NotImplementedError("Subclasses must implement _setup_ui()")
    
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