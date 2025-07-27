"""
Theme constants and styling foundations for SpritePal UI
"""


# Color Palette
COLORS = {
    # Primary action colors (reverted to original)
    "primary": "#c7672a",           # Orange - Arrange Rows button
    "primary_hover": "#a85521",
    "primary_pressed": "#86441a",

    "secondary": "#2a67c7",         # Blue - Grid Arrange button
    "secondary_hover": "#2155a8",
    "secondary_pressed": "#1a4486",

    "accent": "#744da9",            # Purple - Inject button
    "accent_hover": "#5b3d85",
    "accent_pressed": "#472d68",

    # Additional action colors
    "extract": "#0078d4",           # Blue - Extract button
    "extract_hover": "#106ebe",
    "extract_pressed": "#005a9e",

    "editor": "#107c41",            # Green - Open Editor button
    "editor_hover": "#0e6332",
    "editor_pressed": "#0c5228",

    # Status colors
    "success": "#28a745",
    "warning": "#ffc107",
    "danger": "#dc3545",
    "info": "#17a2b8",

    # Neutral colors
    "white": "#ffffff",
    "light_gray": "#f8f9fa",
    "gray": "#6c757d",
    "dark_gray": "#495057",
    "disabled": "#555555",
    "disabled_text": "#999999",
    "black": "#000000",

    # Background colors
    "background": "#ffffff",
    "panel_background": "#f5f5f5",
    "input_background": "#ffffff",

    # Border colors
    "border": "#dee2e6",
    "border_focus": "#80bdff",
    "border_error": "#dc3545",
}

# Typography
FONTS = {
    "default_family": "Arial, sans-serif",
    "monospace_family": "Consolas, Monaco, monospace",

    "small_size": "11px",
    "default_size": "12px",
    "medium_size": "14px",
    "large_size": "16px",

    "normal_weight": "normal",
    "bold_weight": "bold",
}

# Layout Dimensions
DIMENSIONS = {
    # Spacing
    "spacing_xs": 4,
    "spacing_sm": 6,
    "spacing_md": 10,
    "spacing_lg": 16,
    "spacing_xl": 20,

    # Component heights
    "button_height": 35,
    "input_height": 32,
    "combo_height": 32,

    # Component widths
    "button_min_width": 100,
    "button_max_width": 150,
    "combo_min_width": 200,
    "label_min_width": 120,

    # Border radius
    "border_radius": 4,
    "border_radius_small": 2,
    "border_radius_large": 8,

    # Border widths
    "border_width": 1,
    "border_width_thick": 2,
}

def get_theme_style() -> str:
    """
    Get base theme styles that should be applied globally

    Returns:
        CSS string with global theme styles
    """
    return f"""
    QWidget {{
        font-family: {FONTS['default_family']};
        font-size: {FONTS['default_size']};
        color: {COLORS['black']};
        background-color: {COLORS['background']};
    }}

    QGroupBox {{
        font-weight: {FONTS['bold_weight']};
        border: {DIMENSIONS['border_width']}px solid {COLORS['border']};
        border-radius: {DIMENSIONS['border_radius']}px;
        margin-top: {DIMENSIONS['spacing_sm']}px;
        padding-top: {DIMENSIONS['spacing_md']}px;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: {DIMENSIONS['spacing_md']}px;
        padding: 0 {DIMENSIONS['spacing_sm']}px 0 {DIMENSIONS['spacing_sm']}px;
    }}

    QLabel {{
        color: {COLORS['black']};
        font-size: {FONTS['default_size']};
    }}

    QStatusBar {{
        background-color: {COLORS['light_gray']};
        border-top: {DIMENSIONS['border_width']}px solid {COLORS['border']};
    }}
    """

def get_disabled_state_style() -> str:
    """Get CSS for disabled widget states"""
    return f"""
    :disabled {{
        background-color: {COLORS['disabled']};
        color: {COLORS['disabled_text']};
        border-color: {COLORS['disabled']};
    }}
    """
