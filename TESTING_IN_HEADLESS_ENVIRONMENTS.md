# Testing in Headless Environments (WSL/Docker/CI)

This project includes Qt-based GUI applications that require special configuration when running tests in headless environments like WSL, Docker containers, or CI/CD pipelines.

## Automatic Configuration

The project automatically detects headless environments and configures Qt appropriately. The detection happens in `conftest.py` and checks for:

- Missing DISPLAY environment variable
- CI environment variable
- WSL environment (detected via kernel version)
- Pre-configured QT_QPA_PLATFORM=offscreen

When a headless environment is detected, the following configurations are applied automatically:
- `QT_QPA_PLATFORM=offscreen` - Uses Qt's offscreen platform plugin
- `QT_QUICK_BACKEND=software` - Disables GPU acceleration
- `QT_LOGGING_RULES=*.debug=false` - Reduces Qt debug output

## Running Tests

### Standard Method (Automatic Detection)
```bash
python3 -m pytest
```

### Explicit Offscreen Mode
If automatic detection fails, you can explicitly set the platform:
```bash
QT_QPA_PLATFORM=offscreen python3 -m pytest
```

### Using the Helper Script
A convenience script is provided:
```bash
./run_tests_headless.sh
```

This script sets the required environment variables and passes all arguments to pytest.

## Troubleshooting

### Common Errors

1. **"Failed to create wl_display"** or **"Could not connect to display"**
   - This means Qt is trying to connect to a display server
   - Solution: The automatic detection should prevent this, but if it occurs, use explicit offscreen mode

2. **"No Qt platform plugin could be initialized"**
   - Qt cannot find a suitable platform plugin
   - Solution: Ensure PyQt6 is properly installed with: `pip install PyQt6`

3. **QPixmap-related crashes**
   - Some operations require a proper Qt platform
   - Solution: The offscreen platform handles this, but some advanced graphics operations may still fail

### Verifying Configuration

To verify Qt is using the offscreen platform, look for this message when running tests:
```
Detected headless environment - using Qt offscreen platform
```

### Docker Considerations

When running in Docker, ensure your Dockerfile includes:
```dockerfile
# Install Qt dependencies for offscreen rendering
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
    && rm -rf /var/lib/apt/lists/*
```

### CI/CD Configuration

For GitHub Actions or similar CI systems:
```yaml
- name: Run Tests
  run: |
    python -m pytest
  env:
    QT_QPA_PLATFORM: offscreen  # Optional, auto-detection should work
```

## Limitations

When running in offscreen mode:
- Window positioning and screen-related features may not work as expected
- Some advanced graphics operations might be limited
- Performance characteristics may differ from real display rendering

Despite these limitations, all core functionality and business logic can be thoroughly tested in headless environments.