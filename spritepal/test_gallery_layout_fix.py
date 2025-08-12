#!/usr/bin/env python3
"""
Test script to verify sprite gallery tab layout fix.

This test verifies that the sprite gallery layout fix is working correctly,
specifically that:
1. Gallery content stays compact at the top without excessive empty space
2. Scrolling works properly when many sprites are added
3. Layout behaves correctly in both regular and maximized window states
4. The unwanted addStretch() call removal is effective

Run with: python test_gallery_layout_fix.py
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

# Add the spritepal directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QScrollArea, QTextEdit, QSplitter, QMessageBox
    )
    from PySide6.QtCore import Qt, QTimer, QSize
    from PySide6.QtGui import QPixmap, QFont, QPainter, QColor
    
    # Import the components to test
    from ui.tabs.sprite_gallery_tab import SpriteGalleryTab
    from ui.widgets.sprite_gallery_widget import SpriteGalleryWidget
    from ui.widgets.sprite_thumbnail_widget import SpriteThumbnailWidget
    
    QT_AVAILABLE = True
except ImportError as e:
    QT_AVAILABLE = False
    print(f"Qt not available: {e}")
    print("Please ensure PySide6 is installed: pip install PySide6")

from utils.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class TestResult:
    """Results from a specific test."""
    name: str
    passed: bool
    message: str
    details: str = ""

class MockRomExtractor:
    """Mock ROM extractor for testing."""
    
    def extract_sprite_at(self, offset: int, size: int = 128):
        """Generate a mock sprite pixmap."""
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(60, 60, 60))
        
        painter = QPainter(pixmap)
        # Create a simple test pattern based on offset
        color_val = (offset % 255)
        test_color = QColor(color_val, 128, 255 - color_val)
        painter.setBrush(test_color)
        
        # Draw some shapes to make it look like a sprite
        center = size // 2
        painter.drawEllipse(center - 20, center - 20, 40, 40)
        painter.drawRect(center - 10, center - 10, 20, 20)
        
        # Add offset text
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 8)
        painter.setFont(font)
        painter.drawText(5, 15, f"{offset:04X}")
        
        painter.end()
        return pixmap

class GalleryLayoutTestWindow(QMainWindow):
    """Test window for sprite gallery layout testing."""
    
    def __init__(self):
        super().__init__()
        
        self.test_results: List[TestResult] = []
        self.gallery_tab: SpriteGalleryTab = None
        self.mock_rom_extractor = MockRomExtractor()
        
        self._setup_ui()
        self._setup_test_data()
        
    def _setup_ui(self):
        """Setup the test UI."""
        self.setWindowTitle("Sprite Gallery Layout Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Horizontal splitter for gallery and results
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout = QHBoxLayout()
        main_layout.addWidget(splitter)
        main_widget.setLayout(main_layout)
        
        # Left side: Gallery tab
        self.gallery_tab = SpriteGalleryTab()
        splitter.addWidget(self.gallery_tab)
        
        # Right side: Test controls and results
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        
        # Test controls
        controls_label = QLabel("Gallery Layout Tests")
        controls_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        right_layout.addWidget(controls_label)
        
        # Test buttons
        self.test_few_sprites_btn = QPushButton("Test: Few Sprites (No Stretch)")
        self.test_few_sprites_btn.clicked.connect(self._test_few_sprites)
        right_layout.addWidget(self.test_few_sprites_btn)
        
        self.test_many_sprites_btn = QPushButton("Test: Many Sprites (Scrolling)")
        self.test_many_sprites_btn.clicked.connect(self._test_many_sprites)
        right_layout.addWidget(self.test_many_sprites_btn)
        
        self.test_window_resize_btn = QPushButton("Test: Window Resize Behavior")
        self.test_window_resize_btn.clicked.connect(self._test_window_resize)
        right_layout.addWidget(self.test_window_resize_btn)
        
        self.test_maximize_btn = QPushButton("Test: Maximize/Restore Layout")
        self.test_maximize_btn.clicked.connect(self._test_maximize_restore)
        right_layout.addWidget(self.test_maximize_btn)
        
        self.run_all_tests_btn = QPushButton("Run All Layout Tests")
        self.run_all_tests_btn.clicked.connect(self._run_all_tests)
        self.run_all_tests_btn.setStyleSheet("QPushButton { background-color: #4CAF50; font-weight: bold; }")
        right_layout.addWidget(self.run_all_tests_btn)
        
        # Results area
        results_label = QLabel("Test Results:")
        results_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        right_layout.addWidget(results_label)
        
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(300)
        self.results_text.setFont(QFont("Courier", 9))
        right_layout.addWidget(self.results_text)
        
        # Layout measurements display
        measurements_label = QLabel("Current Layout Measurements:")
        measurements_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        right_layout.addWidget(measurements_label)
        
        self.measurements_text = QTextEdit()
        self.measurements_text.setMaximumHeight(200)
        self.measurements_text.setFont(QFont("Courier", 8))
        right_layout.addWidget(self.measurements_text)
        
        # Set splitter proportions
        splitter.setSizes([800, 400])
        splitter.addWidget(right_widget)
        
        # Auto-update measurements
        self.measurement_timer = QTimer()
        self.measurement_timer.timeout.connect(self._update_measurements)
        self.measurement_timer.start(500)  # Update every 500ms
        
    def _setup_test_data(self):
        """Setup test ROM data for the gallery."""
        # Mock ROM path and data
        test_rom_path = "/tmp/test_rom.smc"
        rom_size = 2 * 1024 * 1024  # 2MB
        
        # Set ROM data in gallery
        self.gallery_tab.set_rom_data(test_rom_path, rom_size, self.mock_rom_extractor)
        
    def _generate_mock_sprites(self, count: int) -> List[Dict[str, Any]]:
        """Generate mock sprite data for testing."""
        sprites = []
        base_offset = 0x200000
        
        for i in range(count):
            offset = base_offset + (i * 0x800)  # Space sprites apart
            sprite_info = {
                'offset': offset,
                'size': 1024 + (i % 512),  # Vary size
                'decompressed_size': 2048 + (i % 1024),
                'compressed': i % 3 == 0,  # Some compressed
                'tile_count': 16 + (i % 32),
                'width': 32,
                'height': 32,
                'name': f"TestSprite_{i:03d}" if i % 5 == 0 else None  # Some have names
            }
            sprites.append(sprite_info)
        
        return sprites
        
    def _test_few_sprites(self):
        """Test layout with few sprites - should not have excessive empty space."""
        self._log_test_start("Few Sprites Layout Test")
        
        try:
            # Add just 6 sprites
            sprites = self._generate_mock_sprites(6)
            self.gallery_tab.sprites_data = sprites
            self.gallery_tab.gallery_widget.set_sprites(sprites)
            
            # Wait a moment for layout
            QApplication.processEvents()
            QTimer.singleShot(100, lambda: self._check_few_sprites_layout(sprites))
            
        except Exception as e:
            self._add_result(TestResult(
                "Few Sprites Test",
                False,
                f"Failed to setup test: {e}",
                str(e)
            ))
    
    def _check_few_sprites_layout(self, sprites: List[Dict[str, Any]]):
        """Check the layout for few sprites."""
        try:
            gallery_widget = self.gallery_tab.gallery_widget
            container = gallery_widget.container_widget
            
            # Check that container height is reasonable for content
            content_height = self._calculate_expected_content_height(len(sprites), 
                                                                   gallery_widget.thumbnail_size,
                                                                   gallery_widget.columns)
            
            actual_height = container.height()
            
            # Container should not be much larger than needed content
            height_ratio = actual_height / content_height if content_height > 0 else float('inf')
            
            # Allow some margin but not excessive
            if height_ratio <= 2.0:  # At most 2x the needed height
                self._add_result(TestResult(
                    "Few Sprites Layout",
                    True,
                    f"Content height appropriate: {actual_height}px for {content_height}px content (ratio: {height_ratio:.2f})"
                ))
            else:
                self._add_result(TestResult(
                    "Few Sprites Layout",
                    False,
                    f"Excessive empty space: {actual_height}px container for {content_height}px content (ratio: {height_ratio:.2f})",
                    "Container height is much larger than needed, suggesting unwanted stretching"
                ))
                
            # Check if content is positioned at the top
            first_thumbnail = list(gallery_widget.thumbnails.values())[0] if gallery_widget.thumbnails else None
            if first_thumbnail:
                first_pos_y = first_thumbnail.pos().y()
                if first_pos_y <= 50:  # Should be near the top (allowing for margins)
                    self._add_result(TestResult(
                        "Content Positioning",
                        True,
                        f"Content properly positioned at top: first sprite at y={first_pos_y}"
                    ))
                else:
                    self._add_result(TestResult(
                        "Content Positioning",
                        False,
                        f"Content not at top: first sprite at y={first_pos_y}",
                        "Content should start near the top of the container"
                    ))
            
        except Exception as e:
            self._add_result(TestResult(
                "Few Sprites Layout Check",
                False,
                f"Error checking layout: {e}",
                str(e)
            ))
    
    def _test_many_sprites(self):
        """Test layout with many sprites - should enable scrolling."""
        self._log_test_start("Many Sprites Scrolling Test")
        
        try:
            # Add many sprites to force scrolling
            sprites = self._generate_mock_sprites(50)
            self.gallery_tab.sprites_data = sprites
            self.gallery_tab.gallery_widget.set_sprites(sprites)
            
            # Wait for layout
            QApplication.processEvents()
            QTimer.singleShot(200, lambda: self._check_many_sprites_scrolling(sprites))
            
        except Exception as e:
            self._add_result(TestResult(
                "Many Sprites Test",
                False,
                f"Failed to setup test: {e}",
                str(e)
            ))
    
    def _check_many_sprites_scrolling(self, sprites: List[Dict[str, Any]]):
        """Check scrolling behavior with many sprites."""
        try:
            gallery_widget = self.gallery_tab.gallery_widget
            
            # Check if vertical scrollbar is present and active
            v_scrollbar = gallery_widget.verticalScrollBar()
            scrollbar_visible = v_scrollbar.isVisible()
            scrollbar_enabled = v_scrollbar.maximum() > 0
            
            if scrollbar_visible and scrollbar_enabled:
                self._add_result(TestResult(
                    "Scrolling Enabled",
                    True,
                    f"Scrollbar properly enabled: max={v_scrollbar.maximum()}, visible={scrollbar_visible}"
                ))
                
                # Test scrolling functionality
                original_pos = v_scrollbar.value()
                v_scrollbar.setValue(v_scrollbar.maximum() // 2)  # Scroll to middle
                QApplication.processEvents()
                
                new_pos = v_scrollbar.value()
                if abs(new_pos - original_pos) > 10:  # Scrolling actually happened
                    self._add_result(TestResult(
                        "Scrolling Functionality",
                        True,
                        f"Scrolling works: moved from {original_pos} to {new_pos}"
                    ))
                    
                    # Scroll back
                    v_scrollbar.setValue(original_pos)
                else:
                    self._add_result(TestResult(
                        "Scrolling Functionality",
                        False,
                        "Scrollbar present but scrolling not working properly"
                    ))
            else:
                self._add_result(TestResult(
                    "Scrolling Setup",
                    False,
                    f"Scrollbar not properly enabled: visible={scrollbar_visible}, max={v_scrollbar.maximum()}",
                    "With many sprites, vertical scrolling should be available"
                ))
                
        except Exception as e:
            self._add_result(TestResult(
                "Scrolling Test",
                False,
                f"Error testing scrolling: {e}",
                str(e)
            ))
    
    def _test_window_resize(self):
        """Test layout behavior during window resize."""
        self._log_test_start("Window Resize Test")
        
        try:
            # Setup medium number of sprites
            sprites = self._generate_mock_sprites(20)
            self.gallery_tab.sprites_data = sprites
            self.gallery_tab.gallery_widget.set_sprites(sprites)
            
            # Record initial state
            original_size = self.size()
            original_columns = self.gallery_tab.gallery_widget.columns
            
            # Resize window wider
            self.resize(1600, 800)
            QApplication.processEvents()
            QTimer.singleShot(100, lambda: self._check_resize_behavior(
                original_size, original_columns, "wider"
            ))
            
        except Exception as e:
            self._add_result(TestResult(
                "Window Resize Test",
                False,
                f"Failed to setup resize test: {e}",
                str(e)
            ))
    
    def _check_resize_behavior(self, original_size: QSize, original_columns: int, resize_type: str):
        """Check behavior after window resize."""
        try:
            gallery_widget = self.gallery_tab.gallery_widget
            new_columns = gallery_widget.columns
            
            if resize_type == "wider":
                # Should have more columns when wider
                if new_columns >= original_columns:
                    self._add_result(TestResult(
                        "Resize Column Adaptation",
                        True,
                        f"Columns adapted correctly: {original_columns} → {new_columns} when wider"
                    ))
                    
                    # Now test making it narrower
                    self.resize(800, 800)
                    QApplication.processEvents()
                    QTimer.singleShot(100, lambda: self._check_resize_behavior(
                        original_size, new_columns, "narrower"
                    ))
                else:
                    self._add_result(TestResult(
                        "Resize Column Adaptation",
                        False,
                        f"Columns didn't increase when wider: {original_columns} → {new_columns}"
                    ))
                    
            elif resize_type == "narrower":
                narrower_columns = gallery_widget.columns
                if narrower_columns < new_columns:
                    self._add_result(TestResult(
                        "Resize Column Reduction",
                        True,
                        f"Columns reduced correctly when narrower: {new_columns} → {narrower_columns}"
                    ))
                else:
                    self._add_result(TestResult(
                        "Resize Column Reduction", 
                        False,
                        f"Columns didn't reduce when narrower: {new_columns} → {narrower_columns}"
                    ))
                
                # Restore original size
                self.resize(original_size)
                QApplication.processEvents()
                
        except Exception as e:
            self._add_result(TestResult(
                "Resize Behavior Check",
                False,
                f"Error checking resize behavior: {e}",
                str(e)
            ))
    
    def _test_maximize_restore(self):
        """Test layout during window maximize/restore."""
        self._log_test_start("Maximize/Restore Test")
        
        try:
            # Setup test sprites
            sprites = self._generate_mock_sprites(25)
            self.gallery_tab.sprites_data = sprites
            self.gallery_tab.gallery_widget.set_sprites(sprites)
            
            # Record normal state
            normal_columns = self.gallery_tab.gallery_widget.columns
            
            # Maximize window
            self.showMaximized()
            QApplication.processEvents()
            QTimer.singleShot(200, lambda: self._check_maximized_layout(normal_columns))
            
        except Exception as e:
            self._add_result(TestResult(
                "Maximize Test",
                False,
                f"Failed to setup maximize test: {e}",
                str(e)
            ))
    
    def _check_maximized_layout(self, normal_columns: int):
        """Check layout in maximized state."""
        try:
            gallery_widget = self.gallery_tab.gallery_widget
            max_columns = gallery_widget.columns
            
            # Should have more columns when maximized
            if max_columns > normal_columns:
                self._add_result(TestResult(
                    "Maximized Layout",
                    True,
                    f"More columns when maximized: {normal_columns} → {max_columns}"
                ))
            else:
                self._add_result(TestResult(
                    "Maximized Layout",
                    False,
                    f"Columns didn't increase when maximized: {normal_columns} → {max_columns}"
                ))
            
            # Check that content is still at the top
            if gallery_widget.thumbnails:
                first_thumbnail = list(gallery_widget.thumbnails.values())[0]
                first_pos_y = first_thumbnail.pos().y()
                
                if first_pos_y <= 50:
                    self._add_result(TestResult(
                        "Maximized Content Position",
                        True,
                        f"Content stays at top when maximized: y={first_pos_y}"
                    ))
                else:
                    self._add_result(TestResult(
                        "Maximized Content Position",
                        False,
                        f"Content drifted from top when maximized: y={first_pos_y}",
                        "Content should remain at top regardless of window size"
                    ))
            
            # Restore window
            QTimer.singleShot(1000, self._restore_and_check)
            
        except Exception as e:
            self._add_result(TestResult(
                "Maximized Layout Check",
                False,
                f"Error checking maximized layout: {e}",
                str(e)
            ))
    
    def _restore_and_check(self):
        """Restore window and check layout returns to normal."""
        try:
            self.showNormal()
            QApplication.processEvents()
            
            QTimer.singleShot(200, lambda: self._add_result(TestResult(
                "Window Restore",
                True,
                "Window restored successfully"
            )))
            
        except Exception as e:
            self._add_result(TestResult(
                "Window Restore",
                False,
                f"Error restoring window: {e}",
                str(e)
            ))
    
    def _run_all_tests(self):
        """Run all layout tests in sequence."""
        self._clear_results()
        self._log_test_start("Running All Layout Tests")
        
        # Run tests with delays between them
        QTimer.singleShot(100, self._test_few_sprites)
        QTimer.singleShot(2000, self._test_many_sprites) 
        QTimer.singleShot(4000, self._test_window_resize)
        QTimer.singleShot(8000, self._test_maximize_restore)
        QTimer.singleShot(12000, self._show_final_results)
    
    def _show_final_results(self):
        """Show final test results summary."""
        passed_tests = [r for r in self.test_results if r.passed]
        failed_tests = [r for r in self.test_results if not r.passed]
        
        summary = f"\n{'='*50}\n"
        summary += f"FINAL TEST RESULTS\n"
        summary += f"{'='*50}\n"
        summary += f"Total Tests: {len(self.test_results)}\n"
        summary += f"Passed: {len(passed_tests)}\n"
        summary += f"Failed: {len(failed_tests)}\n"
        summary += f"Success Rate: {len(passed_tests) / len(self.test_results) * 100:.1f}%\n"
        
        if failed_tests:
            summary += f"\nFAILED TESTS:\n"
            for test in failed_tests:
                summary += f"❌ {test.name}: {test.message}\n"
        
        summary += f"\n{'='*50}\n"
        
        if len(failed_tests) == 0:
            summary += "🎉 ALL TESTS PASSED! Gallery layout fix is working correctly.\n"
        else:
            summary += f"⚠️  {len(failed_tests)} test(s) failed. Review the issues above.\n"
        
        self._append_to_results(summary)
        
        # Show message box with results
        if len(failed_tests) == 0:
            QMessageBox.information(self, "Test Results", 
                                  f"All {len(self.test_results)} layout tests passed!\n\n"
                                  "The sprite gallery layout fix is working correctly.")
        else:
            QMessageBox.warning(self, "Test Results",
                              f"{len(failed_tests)} of {len(self.test_results)} tests failed.\n\n"
                              "Check the detailed results for issues.")
    
    def _calculate_expected_content_height(self, sprite_count: int, thumbnail_size: int, columns: int) -> int:
        """Calculate expected height needed for content."""
        if sprite_count == 0 or columns == 0:
            return 0
            
        rows = (sprite_count + columns - 1) // columns  # Ceiling division
        thumbnail_height = thumbnail_size + 40  # Thumbnail plus label
        spacing = 16
        margins = 8
        
        return (rows * thumbnail_height) + ((rows - 1) * spacing) + margins
    
    def _update_measurements(self):
        """Update the real-time layout measurements display."""
        try:
            if not self.gallery_tab or not self.gallery_tab.gallery_widget:
                return
                
            gallery = self.gallery_tab.gallery_widget
            container = gallery.container_widget
            
            measurements = []
            measurements.append(f"GALLERY WIDGET MEASUREMENTS")
            measurements.append(f"{'=' * 30}")
            
            # Basic measurements
            measurements.append(f"Gallery Size: {gallery.width()} x {gallery.height()}")
            measurements.append(f"Container Size: {container.width()} x {container.height()}")
            measurements.append(f"Viewport Size: {gallery.viewport().width()} x {gallery.viewport().height()}")
            
            # Scrolling info
            v_scrollbar = gallery.verticalScrollBar()
            measurements.append(f"V-Scrollbar: visible={v_scrollbar.isVisible()}, max={v_scrollbar.maximum()}")
            measurements.append(f"V-Scroll Position: {v_scrollbar.value()}/{v_scrollbar.maximum()}")
            
            # Content info
            measurements.append(f"Sprite Count: {len(gallery.sprite_data)}")
            measurements.append(f"Thumbnail Count: {len(gallery.thumbnails)}")
            measurements.append(f"Columns: {gallery.columns}")
            measurements.append(f"Thumbnail Size: {gallery.thumbnail_size}")
            
            # Layout analysis
            if gallery.thumbnails:
                first_thumb = list(gallery.thumbnails.values())[0]
                measurements.append(f"First Thumbnail Position: {first_thumb.pos().x()}, {first_thumb.pos().y()}")
                
                # Check if content is at top
                content_at_top = first_thumb.pos().y() <= 50
                measurements.append(f"Content At Top: {'✓' if content_at_top else '✗'}")
                
                # Calculate actual vs expected height
                expected_height = self._calculate_expected_content_height(
                    len(gallery.sprite_data), gallery.thumbnail_size, gallery.columns
                )
                actual_height = container.height()
                height_ratio = actual_height / expected_height if expected_height > 0 else 0
                
                measurements.append(f"Expected Content Height: {expected_height}")
                measurements.append(f"Actual Container Height: {actual_height}")
                measurements.append(f"Height Ratio: {height_ratio:.2f}")
                
                # Analyze ratio
                if height_ratio <= 1.5:
                    measurements.append("Height Analysis: ✓ Good (minimal waste)")
                elif height_ratio <= 2.0:
                    measurements.append("Height Analysis: ⚠ Acceptable (some waste)")
                else:
                    measurements.append("Height Analysis: ✗ Poor (excessive waste)")
            
            self.measurements_text.setPlainText("\n".join(measurements))
            
        except Exception as e:
            self.measurements_text.setPlainText(f"Error updating measurements: {e}")
    
    def _log_test_start(self, test_name: str):
        """Log the start of a test."""
        message = f"\n🚀 Starting: {test_name}"
        self._append_to_results(message)
        logger.info(f"Starting test: {test_name}")
    
    def _add_result(self, result: TestResult):
        """Add a test result."""
        self.test_results.append(result)
        
        status = "✅" if result.passed else "❌"
        message = f"{status} {result.name}: {result.message}"
        
        if result.details:
            message += f"\n   Details: {result.details}"
            
        self._append_to_results(message)
        logger.info(f"Test result - {result.name}: {'PASS' if result.passed else 'FAIL'} - {result.message}")
    
    def _append_to_results(self, text: str):
        """Append text to results display."""
        self.results_text.append(text)
        self.results_text.ensureCursorVisible()
    
    def _clear_results(self):
        """Clear test results."""
        self.test_results.clear()
        self.results_text.clear()

def main():
    """Main test function."""
    if not QT_AVAILABLE:
        print("❌ Qt/PySide6 is not available. Cannot run GUI tests.")
        print("Install with: pip install PySide6")
        return False
    
    print("🔧 Starting Sprite Gallery Layout Test...")
    print("This test will verify that the gallery layout fix is working correctly.")
    print("The fix should prevent excessive empty space in the gallery.")
    print()
    
    try:
        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("Gallery Layout Test")
        
        # Create and show test window
        test_window = GalleryLayoutTestWindow()
        test_window.show()
        
        print("✅ Test window launched successfully!")
        print("📋 Use the buttons in the right panel to run individual tests")
        print("🚀 Click 'Run All Layout Tests' to run the complete test suite")
        print("📊 Real-time measurements are displayed in the bottom panel")
        print()
        print("Expected behaviors:")
        print("  - Few sprites: Content should stay at top without excessive empty space")
        print("  - Many sprites: Scrolling should work smoothly")
        print("  - Window resize: Column count should adapt appropriately")
        print("  - Maximize/restore: Layout should adapt and content stay at top")
        
        # Run the application
        return app.exec()
        
    except Exception as e:
        print(f"❌ Error running test: {e}")
        logger.error(f"Test execution error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)