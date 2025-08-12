"""
Global accessibility styles for SpritePal application.
Provides consistent focus indicators, keyboard navigation hints, and WCAG 2.1 compliance.
"""

from PySide6.QtWidgets import QApplication


def apply_global_accessibility_styles() -> None:
    """Apply global accessibility styles to the application."""
    app = QApplication.instance()
    if not app:
        return
    
    # Global accessibility stylesheet with focus indicators and high contrast
    global_style = """
    /* ===== FOCUS INDICATORS ===== */
    /* All focusable widgets get a clear focus outline */
    QWidget:focus {
        outline: 2px solid #0078d4;
        outline-offset: 1px;
    }
    
    /* Text input fields */
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
        border: 2px solid #0078d4;
        background-color: #f0f8ff;
    }
    
    /* Buttons */
    QPushButton:focus {
        border: 2px solid #0078d4;
        padding: 3px;
        background-color: #e6f2ff;
    }
    
    QPushButton:default {
        font-weight: bold;
        border-width: 2px;
    }
    
    /* Dropdowns and spinners */
    QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
        border: 2px solid #0078d4;
        background-color: #f0f8ff;
    }
    
    /* Sliders */
    QSlider:focus {
        border: 1px solid #0078d4;
        background-color: #f0f8ff;
    }
    
    /* Checkboxes and radio buttons */
    QCheckBox:focus, QRadioButton:focus {
        color: #0078d4;
        font-weight: bold;
    }
    
    QCheckBox:focus::indicator, QRadioButton:focus::indicator {
        border: 2px solid #0078d4;
    }
    
    /* Tab widgets */
    QTabBar::tab:focus {
        border: 2px solid #0078d4;
        background-color: #e6f2ff;
    }
    
    QTabBar::tab:selected {
        font-weight: bold;
        background-color: #ffffff;
    }
    
    /* List widgets */
    QListWidget:focus, QTreeWidget:focus, QTableWidget:focus {
        border: 2px solid #0078d4;
    }
    
    QListWidget::item:focus, QTreeWidget::item:focus, QTableWidget::item:focus {
        background-color: #0078d4;
        color: white;
    }
    
    /* ===== HIGH CONTRAST ===== */
    /* Tooltips with high contrast */
    QToolTip {
        background-color: #ffffcc;
        color: #000000;
        border: 2px solid #000000;
        padding: 5px;
        font-size: 10pt;
    }
    
    /* Status bar messages */
    QStatusBar {
        font-size: 10pt;
        color: #000000;
        background-color: #f0f0f0;
    }
    
    /* ===== KEYBOARD NAVIGATION HINTS ===== */
    /* Menu bar items */
    QMenuBar::item:selected {
        background-color: #0078d4;
        color: white;
    }
    
    QMenuBar::item:focus {
        border: 2px solid #0078d4;
    }
    
    /* Menu items */
    QMenu::item:selected {
        background-color: #0078d4;
        color: white;
    }
    
    QMenu::item:focus {
        background-color: #0078d4;
        color: white;
        font-weight: bold;
    }
    
    /* Toolbar buttons */
    QToolButton:focus {
        border: 2px solid #0078d4;
        background-color: #e6f2ff;
    }
    
    /* ===== DISABLED STATES ===== */
    /* Clear visual distinction for disabled items */
    QWidget:disabled {
        color: #808080;
        background-color: #f0f0f0;
    }
    
    QPushButton:disabled {
        color: #808080;
        background-color: #e0e0e0;
        border: 1px solid #c0c0c0;
    }
    
    QLineEdit:disabled, QTextEdit:disabled {
        color: #808080;
        background-color: #f5f5f5;
        border: 1px solid #d0d0d0;
    }
    
    /* ===== GROUP BOXES ===== */
    /* Make group boxes more visible */
    QGroupBox {
        font-weight: bold;
        border: 2px solid #d0d0d0;
        border-radius: 5px;
        margin-top: 10px;
        padding-top: 10px;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px 0 5px;
        background-color: white;
    }
    
    QGroupBox:focus {
        border: 2px solid #0078d4;
    }
    
    /* ===== SCROLL BARS ===== */
    /* Larger scroll bars for better accessibility */
    QScrollBar:vertical {
        width: 16px;
    }
    
    QScrollBar:horizontal {
        height: 16px;
    }
    
    QScrollBar::handle {
        background-color: #808080;
        border-radius: 3px;
    }
    
    QScrollBar::handle:hover {
        background-color: #606060;
    }
    
    QScrollBar::handle:focus {
        background-color: #0078d4;
    }
    
    /* ===== SPLITTERS ===== */
    /* More visible splitter handles */
    QSplitter::handle {
        background-color: #d0d0d0;
    }
    
    QSplitter::handle:hover {
        background-color: #a0a0a0;
    }
    
    QSplitter::handle:focus {
        background-color: #0078d4;
    }
    
    /* ===== ERROR STATES ===== */
    /* Clear error indication */
    QLineEdit[hasError="true"], QTextEdit[hasError="true"] {
        border: 2px solid #ff0000;
        background-color: #fff0f0;
    }
    
    /* ===== SELECTION COLORS ===== */
    /* High contrast selection */
    QWidget::selection {
        background-color: #0078d4;
        color: white;
    }
    
    /* ===== DIALOG BUTTONS ===== */
    /* Standard dialog buttons */
    QDialogButtonBox QPushButton {
        min-width: 80px;
        min-height: 25px;
    }
    
    QDialogButtonBox QPushButton:default {
        background-color: #0078d4;
        color: white;
        font-weight: bold;
    }
    
    QDialogButtonBox QPushButton:default:focus {
        background-color: #005a9e;
        border: 2px solid #003d6b;
    }
    """
    
    # Apply the stylesheet
    current_style = app.styleSheet()
    app.setStyleSheet(current_style + global_style)
    
    # Set application-wide attributes for better accessibility
    app.setEffectEnabled(app.UI_AnimateCombo, False)  # Disable animations that can be distracting
    app.setEffectEnabled(app.UI_AnimateTooltip, False)
    
    # Ensure high DPI support for better readability
    app.setAttribute(app.AA_UseHighDpiPixmaps, True)
    app.setAttribute(app.AA_EnableHighDpiScaling, True)


def configure_accessibility_settings() -> None:
    """Configure application-wide accessibility settings."""
    app = QApplication.instance()
    if not app:
        return
    
    # Set default font size for better readability
    from PySide6.QtGui import QFont
    
    font = app.font()
    if font.pointSize() < 10:
        font.setPointSize(10)
        app.setFont(font)
    
    # Ensure keyboard navigation is enabled
    app.setNavigationMode(app.NavigationModeKeypadTabOrder)
    
    # Set double-click interval for users with motor impairments
    app.setDoubleClickInterval(600)  # 600ms instead of default 400ms
    
    # Enable tooltips by default
    from PySide6.QtCore import Qt
    app.setAttribute(Qt.AA_DisableWindowContextHelpButton, False)


def initialize_accessibility() -> None:
    """Initialize all accessibility features for the application."""
    apply_global_accessibility_styles()
    configure_accessibility_settings()
    
    # Import and apply any additional accessibility helpers
    from ui.utils.accessibility import apply_global_accessibility_styles as apply_utils_styles
    apply_utils_styles()