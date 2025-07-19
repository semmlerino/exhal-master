#!/usr/bin/env python3
"""
Alternative solution: Use pre-compiled HAL tools if compilation fails.
This script attempts to use the Linux binaries with WSL on Windows.
"""

import os
import platform
import shutil
import subprocess
from pathlib import Path


def setup_wsl_wrapper():
    """Create wrapper scripts to run Linux binaries through WSL on Windows"""
    
    if platform.system() != "Windows":
        print("This script is only needed on Windows.")
        return False
    
    # Check if WSL is available
    try:
        result = subprocess.run(["wsl", "--version"], capture_output=True, check=True)
        print("WSL detected!")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("WSL not found. Please install WSL to use Linux binaries on Windows.")
        print("Run in PowerShell as Administrator: wsl --install")
        return False
    
    # Create tools directory
    tools_dir = Path("tools")
    tools_dir.mkdir(exist_ok=True)
    
    # Copy Linux binaries
    linux_exhal = Path("../archive/obsolete_test_images/ultrathink/exhal")
    linux_inhal = Path("../archive/obsolete_test_images/ultrathink/inhal")
    
    if not linux_exhal.exists() or not linux_inhal.exists():
        print("Linux binaries not found in archive directory.")
        return False
    
    # Copy binaries to tools directory with .linux suffix
    shutil.copy2(linux_exhal, tools_dir / "exhal.linux")
    shutil.copy2(linux_inhal, tools_dir / "inhal.linux")
    
    # Create Windows wrapper scripts
    exhal_wrapper = '''@echo off
wsl bash -c "cd '$(wslpath -a '%cd%')' && ./tools/exhal.linux %*"
'''
    
    inhal_wrapper = '''@echo off
wsl bash -c "cd '$(wslpath -a '%cd%')' && ./tools/inhal.linux %*"
'''
    
    # Write wrapper scripts
    with open(tools_dir / "exhal.exe.bat", "w") as f:
        f.write(exhal_wrapper)
    
    with open(tools_dir / "inhal.exe.bat", "w") as f:
        f.write(inhal_wrapper)
    
    # Alternative: Create Python wrappers that properly handle paths
    exhal_py_wrapper = '''#!/usr/bin/env python3
import sys
import subprocess
import os

# Convert Windows paths to WSL paths
args = []
for arg in sys.argv[1:]:
    if os.path.exists(arg) and os.path.isabs(arg):
        # Convert absolute Windows path to WSL path
        result = subprocess.run(["wsl", "wslpath", "-a", arg], capture_output=True, text=True)
        if result.returncode == 0:
            args.append(result.stdout.strip())
        else:
            args.append(arg)
    else:
        args.append(arg)

# Run Linux binary through WSL
cmd = ["wsl", "./tools/exhal.linux"] + args
subprocess.run(cmd)
'''
    
    inhal_py_wrapper = '''#!/usr/bin/env python3
import sys
import subprocess
import os

# Convert Windows paths to WSL paths
args = []
for arg in sys.argv[1:]:
    if os.path.exists(arg) and os.path.isabs(arg):
        # Convert absolute Windows path to WSL path
        result = subprocess.run(["wsl", "wslpath", "-a", arg], capture_output=True, text=True)
        if result.returncode == 0:
            args.append(result.stdout.strip())
        else:
            args.append(arg)
    else:
        args.append(arg)

# Run Linux binary through WSL
cmd = ["wsl", "./tools/inhal.linux"] + args
subprocess.run(cmd)
'''
    
    # Write Python wrappers
    with open(tools_dir / "exhal.py", "w") as f:
        f.write(exhal_py_wrapper)
    
    with open(tools_dir / "inhal.py", "w") as f:
        f.write(inhal_py_wrapper)
    
    print("\nWSL wrapper scripts created successfully!")
    print("The Linux binaries will be run through WSL.")
    print("\nNote: WSL must be installed and running for this to work.")
    
    return True


def provide_manual_instructions():
    """Provide instructions for manual tool acquisition"""
    
    print("\nManual options for getting HAL tools on Windows:")
    print("\n1. Install a C compiler (recommended):")
    print("   - MSYS2: https://www.msys2.org/")
    print("   - After installing, run: pacman -S mingw-w64-x86_64-gcc")
    print("   - Then run: python compile_hal_tools.py")
    
    print("\n2. Use WSL (Windows Subsystem for Linux):")
    print("   - Install WSL: wsl --install (in PowerShell as Admin)")
    print("   - Run this script again after WSL is installed")
    
    print("\n3. Request pre-compiled Windows binaries:")
    print("   - Ask the project maintainer for Windows .exe files")
    print("   - Place exhal.exe and inhal.exe in the tools/ directory")
    
    print("\n4. Cross-compile from Linux:")
    print("   - On a Linux machine: x86_64-w64-mingw32-gcc -o exhal.exe exhal.c compress.c")
    print("   - Copy the resulting .exe files to Windows")


if __name__ == "__main__":
    if platform.system() == "Windows":
        if not setup_wsl_wrapper():
            provide_manual_instructions()
    else:
        print("This script is only for Windows. On Linux/macOS, run compile_hal_tools.py")