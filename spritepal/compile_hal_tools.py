#!/usr/bin/env python3
"""
Cross-platform HAL tools compilation script.
Compiles exhal/inhal for the current platform.
"""

import os
import platform
import subprocess
import shutil
from pathlib import Path


def compile_hal_tools():
    """Compile HAL compression tools for the current platform"""
    
    # Determine platform
    system = platform.system()
    print(f"Detected platform: {system}")
    
    # Source directory
    src_dir = Path("../archive/obsolete_test_images/ultrathink")
    if not src_dir.exists():
        print(f"Error: Source directory not found: {src_dir}")
        return False
    
    # Output directory
    tools_dir = Path("tools")
    tools_dir.mkdir(exist_ok=True)
    
    # Platform-specific compilation
    if system == "Windows":
        # Windows compilation
        exe_suffix = ".exe"
        
        # Try different compilers
        compilers = ["gcc", "cl", "clang", "mingw32-gcc", "x86_64-w64-mingw32-gcc"]
        compiler = None
        
        # Also check common MinGW installation paths
        mingw_paths = [
            r"C:\MinGW\bin\gcc.exe",
            r"C:\mingw64\bin\gcc.exe",
            r"C:\msys64\mingw64\bin\gcc.exe",
            r"C:\Program Files\mingw-w64\x86_64-8.1.0-posix-seh-rt_v6-rev0\mingw64\bin\gcc.exe"
        ]
        
        for cc in compilers:
            try:
                subprocess.run([cc, "--version"], capture_output=True, check=True)
                compiler = cc
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        # If not found in PATH, check common locations
        if not compiler:
            for gcc_path in mingw_paths:
                if os.path.exists(gcc_path):
                    compiler = gcc_path
                    break
        
        if not compiler:
            print("Error: No C compiler found.")
            print("\nTo install a compiler on Windows, choose one of these options:")
            print("\n1. MinGW-w64 (Recommended):")
            print("   - Download from: https://github.com/msys2/msys2-installer/releases")
            print("   - Install MSYS2, then run: pacman -S mingw-w64-x86_64-gcc")
            print("   - Add to PATH: C:\\msys64\\mingw64\\bin")
            print("\n2. Visual Studio Build Tools:")
            print("   - Download from: https://visualstudio.microsoft.com/downloads/")
            print("   - Select 'Build Tools for Visual Studio'")
            print("   - Install 'Desktop development with C++'")
            print("\n3. Pre-compiled binaries:")
            print("   - Check if pre-compiled Windows binaries are available")
            print("   - in the project releases or ask the maintainer")
            return False
        
        print(f"Using compiler: {compiler}")
        
        # Compile commands
        if compiler == "cl":
            # MSVC
            compile_cmds = [
                [compiler, "/O2", f"{src_dir}/exhal.c", f"{src_dir}/compress.c", "/Fe:exhal.exe"],
                [compiler, "/O2", f"{src_dir}/inhal.c", f"{src_dir}/compress.c", "/Fe:inhal.exe"]
            ]
        else:
            # GCC/Clang
            compile_cmds = [
                [compiler, "-O2", "-o", "exhal.exe", f"{src_dir}/exhal.c", f"{src_dir}/compress.c"],
                [compiler, "-O2", "-o", "inhal.exe", f"{src_dir}/inhal.c", f"{src_dir}/compress.c"]
            ]
    
    else:
        # Linux/macOS compilation
        exe_suffix = ""
        compiler = "gcc"
        
        # Check for compiler
        try:
            subprocess.run([compiler, "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"Error: {compiler} not found. Please install build-essential.")
            return False
        
        compile_cmds = [
            [compiler, "-O2", "-o", "exhal", f"{src_dir}/exhal.c", f"{src_dir}/compress.c"],
            [compiler, "-O2", "-o", "inhal", f"{src_dir}/inhal.c", f"{src_dir}/compress.c"]
        ]
    
    # Compile tools
    for cmd in compile_cmds:
        tool_name = "exhal" if "exhal" in str(cmd) else "inhal"
        print(f"Compiling {tool_name}{exe_suffix}...")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"  Success!")
            
            # Move to tools directory
            src_file = f"{tool_name}{exe_suffix}"
            dst_file = tools_dir / src_file
            
            if os.path.exists(src_file):
                shutil.move(src_file, dst_file)
                if system != "Windows":
                    # Make executable on Unix
                    os.chmod(dst_file, 0o755)
            
        except subprocess.CalledProcessError as e:
            print(f"  Failed: {e.stderr}")
            return False
    
    print(f"\nHAL tools compiled successfully!")
    print(f"Binaries saved to: {tools_dir.absolute()}")
    
    # Create platform marker file
    platform_file = tools_dir / f".platform_{system.lower()}"
    platform_file.touch()
    
    return True


if __name__ == "__main__":
    compile_hal_tools()