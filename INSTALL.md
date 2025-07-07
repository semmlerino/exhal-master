# Installation Guide

This guide covers the installation of all components in the exhal-master project, including the HAL compression tools, SuperFamiconv, and the Kirby Super Star Sprite Editor.

## System Requirements

### Operating Systems
- **Linux** (native support)
- **macOS** (native support)
- **Windows** (through WSL - Windows Subsystem for Linux recommended)

### Core Requirements
- **C Compiler**: GCC 4.8+ or compatible C99 compiler
- **Make**: GNU Make 3.81+
- **Python**: 3.6 or higher
- **Git**: For cloning the repository

## Quick Install

### 1. Clone the Repository
```bash
git clone https://github.com/devinacker/exhal.git
cd exhal-master
```

### 2. Build C/C++ Tools
```bash
# Build HAL compression tools (exhal, inhal, sniff)
make

# Build SuperFamiconv (optional, for advanced graphics conversion)
cd SuperFamiconv
make
cd ..
```

### 3. Install Python Dependencies
```bash
# Install Python packages
pip install -r requirements.txt
```

## Detailed Installation

### HAL Compression Tools

The main C tools for HAL compression/decompression:

1. **Build the tools:**
   ```bash
   make clean
   make
   ```

2. **Verify installation:**
   ```bash
   ./exhal    # Should show usage information
   ./inhal    # Should show usage information
   ```

3. **Optional: Install system-wide (Linux/macOS):**
   ```bash
   sudo cp exhal inhal /usr/local/bin/
   ```

### SuperFamiconv (Optional)

Advanced SNES graphics conversion tool:

1. **Navigate to directory:**
   ```bash
   cd SuperFamiconv
   ```

2. **Build:**
   ```bash
   make
   ```

3. **Return to main directory:**
   ```bash
   cd ..
   ```

### Python Sprite Editor

GUI and command-line tools for sprite editing:

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify installation:**
   ```bash
   python -c "import PyQt6; import PIL; import numpy; print('All dependencies installed!')"
   ```

## Dependencies Reference

### C/C++ Dependencies
- **Compiler**: GCC or compatible C99 compiler
- **Standard libraries**: stdio.h, stdlib.h, string.h
- **No external libraries required**

### Python Dependencies
- **PyQt6** (>= 6.0.0) - GUI framework
- **Pillow** (>= 9.0.0) - Image processing
- **numpy** (>= 1.20.0) - Array operations
- **pytest** (>= 7.0.0) - Optional, for running tests

### Platform-Specific Notes

#### Windows (WSL)
1. Install WSL2: `wsl --install`
2. Install Ubuntu or preferred Linux distribution
3. Follow Linux installation steps within WSL

#### macOS
- Install Xcode Command Line Tools: `xcode-select --install`
- Use Homebrew for package management if needed

#### Linux
- Ubuntu/Debian: `sudo apt-get install build-essential python3-pip`
- Fedora/RHEL: `sudo dnf install gcc make python3-pip`
- Arch: `sudo pacman -S base-devel python-pip`

## Quick Start After Installation

### Extract sprites from ROM:
```bash
# Extract compressed data
./exhal rom.sfc 0x1A0000 sprites.bin

# Convert to PNG
python -m sprite_editor.snes_tiles_to_png sprites.bin sprites.png
```

### Launch GUI Editor:
```bash
python run_sprite_editor.py
```

### Run sprite workflow:
```bash
python -m sprite_editor.sprite_workflow extract
```

## Troubleshooting

### Common Issues

1. **"command not found" errors**
   - Ensure you're in the correct directory
   - Check that executables have execute permissions: `chmod +x exhal inhal`

2. **Python module import errors**
   - Verify Python version: `python --version` (should be 3.6+)
   - Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`

3. **Build errors**
   - Check compiler installation: `gcc --version`
   - Clean and rebuild: `make clean && make`

4. **PyQt6 installation issues**
   - On some systems, you may need: `pip install PyQt6 --user`
   - For display issues on WSL, install an X server (VcXsrv or similar)

### Getting Help

- Check the README files in each directory
- Review the example scripts in the `sprite_editor` directory
- For bugs or feature requests, visit the project repository

## Testing Installation

Run the test suite to verify everything is working:

```bash
# Test Python components
pytest sprite_editor/tests/

# Test compression tools
./exhal test_files/compressed.bin 0x0 test_output.bin
```

## Next Steps

- Read `README.md` for project overview
- Check `sprite_editor/README.md` for sprite editing details
- See `SPRITE_EDITING_GUIDE.md` for usage tutorials
- Review example scripts for common workflows