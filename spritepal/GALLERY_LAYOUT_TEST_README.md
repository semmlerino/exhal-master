# Sprite Gallery Layout Test

This directory contains a comprehensive test script to verify that the sprite gallery tab layout fix is working correctly.

## What This Test Verifies

The layout fix addressed an issue where unwanted `addStretch()` calls were causing excessive empty space in the sprite gallery. This test script verifies:

1. **Content Positioning**: Gallery content stays compact at the top without excessive empty space
2. **Scrolling Behavior**: Proper scrolling when many sprites are present  
3. **Window Resizing**: Layout adapts correctly to window size changes
4. **Maximize/Restore**: Layout behaves properly in maximized and restored states
5. **Column Adaptation**: Number of columns adjusts based on available width

## Files

- `test_gallery_layout_fix.py` - Main test script with comprehensive layout tests
- `run_gallery_layout_test.sh` - Bash script to run tests with proper environment setup
- `GALLERY_LAYOUT_TEST_README.md` - This documentation file

## Prerequisites

1. **Python 3** with PySide6 installed:
   ```bash
   pip install PySide6
   ```

2. **Virtual Environment** (recommended):
   ```bash
   # From the spritepal directory
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install PySide6
   ```

3. **Display Environment**:
   - On desktop systems: Normal display should work
   - On headless systems: Install `xvfb` for virtual display
   ```bash
   # Ubuntu/Debian
   sudo apt-get install xvfb
   
   # Then run with:
   xvfb-run -a python test_gallery_layout_fix.py
   ```

## Running the Tests

### Method 1: Using the Runner Script (Recommended)
```bash
./run_gallery_layout_test.sh
```

The runner script will:
- Check for required dependencies
- Activate virtual environment if available  
- Set up display environment if needed
- Run the test with proper error handling

### Method 2: Direct Python Execution
```bash
# With virtual environment activated
python test_gallery_layout_fix.py

# Or with xvfb on headless systems
xvfb-run -a python test_gallery_layout_fix.py
```

## Test Interface

The test launches a GUI window with:

### Left Panel: Sprite Gallery
- The actual sprite gallery tab being tested
- Shows mock sprites to test layout behavior
- Interactive - you can resize, scroll, etc.

### Right Panel: Test Controls
- **Individual Test Buttons**: Run specific layout tests
  - "Test: Few Sprites (No Stretch)" - Tests compact layout with few items
  - "Test: Many Sprites (Scrolling)" - Tests scrolling with many items  
  - "Test: Window Resize Behavior" - Tests column adaptation during resize
  - "Test: Maximize/Restore Layout" - Tests layout during window state changes

- **Run All Tests**: Executes complete test suite automatically

- **Test Results**: Shows detailed results of each test
- **Live Measurements**: Real-time layout measurements and analysis

## Expected Test Results

### ✅ Passing Tests Should Show:
- **Few Sprites Layout**: Content height ratio ≤ 2.0 (minimal waste)
- **Content Positioning**: First sprite positioned at y ≤ 50px (near top)
- **Scrolling Enabled**: Vertical scrollbar appears with many sprites
- **Scrolling Functionality**: Scrollbar actually moves content
- **Resize Column Adaptation**: More columns when window is wider
- **Resize Column Reduction**: Fewer columns when window is narrower  
- **Maximized Layout**: More columns when maximized
- **Maximized Content Position**: Content stays at top when maximized

### ❌ Failing Tests Indicate:
- **Height Ratio > 2.0**: Excessive empty space (layout fix not working)
- **Content Not At Top**: Content positioned too far down
- **No Scrolling**: Scrollbar not appearing with many sprites
- **Poor Column Adaptation**: Columns not adjusting to window width

## Understanding the Results

### Live Measurements Panel
The bottom panel shows real-time measurements including:

```
GALLERY WIDGET MEASUREMENTS
==============================
Gallery Size: 800 x 600           # Overall widget size
Container Size: 780 x 400          # Content container size  
Viewport Size: 778 x 598           # Visible scroll area
V-Scrollbar: visible=false, max=0  # Scrollbar state
Sprite Count: 6                    # Number of sprites loaded
Columns: 3                         # Current column count
Expected Content Height: 200       # Calculated needed height
Actual Container Height: 400       # Actual container height
Height Ratio: 2.00                 # Efficiency ratio
Height Analysis: ✓ Good            # Analysis result
```

### Key Metrics:
- **Height Ratio**: Actual height ÷ Expected height
  - ≤ 1.5: ✓ Good (minimal waste)
  - ≤ 2.0: ⚠ Acceptable (some waste)  
  - > 2.0: ✗ Poor (excessive waste)
- **Content At Top**: ✓ if first sprite y ≤ 50px

## Troubleshooting

### Common Issues:

1. **"PySide6 not available"**
   ```bash
   pip install PySide6
   ```

2. **"Fatal Python error: Aborted"**
   - Ensure you're using the test script (which handles Qt properly)
   - Try with xvfb on headless systems
   - Check virtual environment is activated

3. **Test window doesn't appear**
   - On WSL/headless: Install and use xvfb
   - On remote systems: Ensure X11 forwarding is enabled

4. **Tests fail unexpectedly**
   - Check console output for detailed error messages
   - Verify the sprite gallery components are working normally
   - Try running individual tests instead of the full suite

### WSL-Specific Setup:
```bash
# Install X11 server (e.g., VcXsrv on Windows)
# Then:
export DISPLAY=:0
python test_gallery_layout_fix.py

# Or use xvfb:
sudo apt-get install xvfb
xvfb-run -a python test_gallery_layout_fix.py
```

## Interpreting Results

### All Tests Pass ✅
The gallery layout fix is working correctly:
- No excessive empty space with few sprites
- Proper scrolling behavior with many sprites
- Responsive layout that adapts to window changes
- Content consistently positioned at the top

### Some Tests Fail ❌  
Review the specific failures:
- **Height ratio failures**: May indicate the `addStretch()` fix wasn't applied properly
- **Positioning failures**: Content container may have incorrect alignment
- **Scrolling failures**: Scroll area configuration issues
- **Resize failures**: Column calculation or layout update problems

## Test Coverage

This test script covers the core layout behaviors that were problematic before the fix:

1. **Empty Space Prevention**: Verifies container doesn't grow unnecessarily
2. **Content Positioning**: Ensures content stays at top of container
3. **Responsive Design**: Confirms layout adapts to different window sizes
4. **Scrolling Integration**: Tests that scrolling works when needed
5. **State Consistency**: Verifies layout is consistent across window state changes

The test uses mock sprites and a mock ROM extractor to focus purely on layout behavior without requiring actual ROM files or complex sprite extraction logic.