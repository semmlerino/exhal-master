#!/usr/bin/env python3
"""
Generate mock sprite thumbnails for the gallery.
This creates colored pattern images to simulate actual sprites.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap, QPen, QBrush
import random

def generate_mock_sprite_thumbnail(sprite_info: dict, size: int = 256) -> QPixmap:
    """
    Generate a mock sprite thumbnail based on sprite info.
    
    Args:
        sprite_info: Dictionary with sprite metadata
        size: Size of the thumbnail in pixels
        
    Returns:
        QPixmap with a generated sprite pattern
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(30, 30, 30))
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Get sprite characteristics
    name = sprite_info.get('name', 'Unknown')
    offset = sprite_info.get('offset', 0)
    sprite_width = sprite_info.get('width', 128)
    sprite_height = sprite_info.get('height', 128)
    palette_index = sprite_info.get('palette_index', 0)
    
    # Generate colors based on palette index
    base_hue = (palette_index * 45) % 360
    colors = [
        QColor.fromHsv(base_hue, 180, 200),        # Primary color
        QColor.fromHsv((base_hue + 30) % 360, 150, 150),  # Secondary
        QColor.fromHsv((base_hue - 30) % 360, 120, 100),  # Shadow
        QColor.fromHsv(base_hue, 50, 250),         # Highlight
    ]
    
    # Determine sprite type from name
    is_character = any(x in name.lower() for x in ['kirby', 'dee', 'knight', 'dedede'])
    is_enemy = any(x in name.lower() for x in ['enemy', 'waddle', 'kracko', 'whispy'])
    is_item = any(x in name.lower() for x in ['item', 'cherry', 'cake', '1up'])
    is_block = any(x in name.lower() for x in ['block', 'star', 'stone', 'ice'])
    
    # Draw different patterns based on type
    if is_character:
        # Draw a circular character sprite
        center_x = size // 2
        center_y = size // 2
        radius = min(sprite_width, sprite_height) // 2
        
        # Body
        painter.setBrush(QBrush(colors[0]))
        painter.setPen(QPen(colors[2], 2))
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
        
        # Eyes
        eye_size = radius // 4
        eye_y = center_y - radius // 3
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawEllipse(center_x - radius // 2, eye_y, eye_size, eye_size)
        painter.drawEllipse(center_x + radius // 4, eye_y, eye_size, eye_size)
        
        # Pupils
        painter.setBrush(QBrush(Qt.GlobalColor.black))
        painter.drawEllipse(center_x - radius // 2 + 2, eye_y + 2, eye_size // 2, eye_size // 2)
        painter.drawEllipse(center_x + radius // 4 + 2, eye_y + 2, eye_size // 2, eye_size // 2)
        
    elif is_enemy:
        # Draw a square enemy sprite
        margin = (size - min(sprite_width, sprite_height)) // 2
        rect_size = min(sprite_width, sprite_height)
        
        painter.setBrush(QBrush(colors[1]))
        painter.setPen(QPen(colors[2], 3))
        painter.drawRect(margin, margin, rect_size, rect_size)
        
        # Add pattern
        painter.setPen(QPen(colors[3], 2))
        for i in range(margin + 10, margin + rect_size - 10, 20):
            painter.drawLine(i, margin + 10, i, margin + rect_size - 10)
            
    elif is_item:
        # Draw a star/diamond item
        center_x = size // 2
        center_y = size // 2
        radius = min(sprite_width, sprite_height) // 3
        
        painter.setBrush(QBrush(colors[3]))
        painter.setPen(QPen(colors[0], 2))
        
        # Draw star shape
        points = []
        for i in range(8):
            angle = i * 45
            if i % 2 == 0:
                r = radius
            else:
                r = radius // 2
            import math
            x = center_x + r * math.cos(math.radians(angle))
            y = center_y + r * math.sin(math.radians(angle))
            points.append((x, y))
        
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QPolygonF
        polygon = QPolygonF([QPointF(x, y) for x, y in points])
        painter.drawPolygon(polygon)
        
    elif is_block:
        # Draw a tiled block pattern
        tile_size = 32
        painter.setPen(QPen(colors[2], 1))
        
        for x in range(0, size, tile_size):
            for y in range(0, size, tile_size):
                if (x // tile_size + y // tile_size) % 2 == 0:
                    painter.setBrush(QBrush(colors[0]))
                else:
                    painter.setBrush(QBrush(colors[1]))
                painter.drawRect(x, y, tile_size, tile_size)
    else:
        # Default pattern for unknown sprites
        # Draw a grid of colored pixels
        pixel_size = 16
        random.seed(offset)  # Use offset for consistent randomization
        
        for x in range(0, size, pixel_size):
            for y in range(0, size, pixel_size):
                color_index = random.randint(0, len(colors) - 1)
                painter.fillRect(x, y, pixel_size, pixel_size, colors[color_index])
    
    # Add border
    painter.setPen(QPen(QColor(100, 100, 100), 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(1, 1, size - 2, size - 2)
    
    # Add name label at bottom
    painter.setPen(QPen(Qt.GlobalColor.white))
    from PySide6.QtGui import QFont
    painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
    painter.drawText(5, size - 5, name[:20])  # Truncate long names
    
    painter.end()
    
    return pixmap

def populate_gallery_with_mock_thumbnails(gallery_widget, sprite_data: list):
    """
    Populate a gallery widget with mock thumbnails.
    
    Args:
        gallery_widget: SpriteGalleryWidget instance
        sprite_data: List of sprite info dictionaries
    """
    for sprite_info in sprite_data:
        offset = sprite_info.get('offset', 0)
        if isinstance(offset, str):
            offset = int(offset, 16) if offset.startswith('0x') else int(offset)
        
        # Generate mock thumbnail
        thumbnail_size = gallery_widget.thumbnail_size
        pixmap = generate_mock_sprite_thumbnail(sprite_info, thumbnail_size)
        
        # Find the thumbnail widget and set its pixmap
        if offset in gallery_widget.thumbnails:
            thumbnail_widget = gallery_widget.thumbnails[offset]
            thumbnail_widget.set_sprite_data(pixmap, sprite_info)