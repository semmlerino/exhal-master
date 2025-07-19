#!/usr/bin/env python3
"""
Download pre-compiled HAL tools for Windows.
This script compiles the tools using GitHub Actions or similar CI service.
"""

import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path


def download_mingw_portable():
    """Download portable MinGW-w64 and compile tools"""
    
    print("Downloading portable MinGW-w64...")
    
    # MinGW-w64 portable URL (no installation required)
    mingw_url = "https://github.com/niXman/mingw-builds-binaries/releases/download/13.2.0-rt_v11-rev1/x86_64-13.2.0-release-posix-seh-msvcrt-rt_v11-rev1.7z"
    
    print(f"Download URL: {mingw_url}")
    print("\nPlease download MinGW-w64 manually from:")
    print("https://github.com/niXman/mingw-builds-binaries/releases")
    print("\nChoose: x86_64-*-release-posix-seh-*.7z")
    print("Extract it to C:\\mingw64")
    print("Then run: C:\\mingw64\\bin\\gcc.exe --version to verify")
    
    return False


def create_simple_batch_compiler():
    """Create a simple batch file that tries to compile with any available compiler"""
    
    batch_content = '''@echo off
echo Attempting to compile HAL tools for Windows...
echo.

REM Try different compilers
set COMPILER=
set FOUND=0

REM Check for gcc in common locations
if exist "C:\\mingw64\\bin\\gcc.exe" (
    set COMPILER=C:\\mingw64\\bin\\gcc.exe
    set FOUND=1
    echo Found GCC at C:\\mingw64\\bin\\gcc.exe
) else if exist "C:\\msys64\\mingw64\\bin\\gcc.exe" (
    set COMPILER=C:\\msys64\\mingw64\\bin\\gcc.exe
    set FOUND=1
    echo Found GCC at C:\\msys64\\mingw64\\bin\\gcc.exe
) else (
    where gcc >nul 2>nul
    if %errorlevel%==0 (
        set COMPILER=gcc
        set FOUND=1
        echo Found GCC in PATH
    )
)

if %FOUND%==0 (
    echo No C compiler found!
    echo.
    echo Please install MinGW-w64 manually:
    echo 1. Download from: https://github.com/niXman/mingw-builds-binaries/releases
    echo 2. Extract to C:\\mingw64
    echo 3. Run this script again
    pause
    exit /b 1
)

REM Create tools directory
if not exist "tools" mkdir "tools"

REM Compile tools
echo.
echo Compiling exhal.exe...
%COMPILER% -O2 -o tools\\exhal.exe ..\\archive\\obsolete_test_images\\ultrathink\\exhal.c ..\\archive\\obsolete_test_images\\ultrathink\\compress.c
if %errorlevel% neq 0 (
    echo Failed to compile exhal.exe
    pause
    exit /b 1
)

echo Compiling inhal.exe...
%COMPILER% -O2 -o tools\\inhal.exe ..\\archive\\obsolete_test_images\\ultrathink\\inhal.c ..\\archive\\obsolete_test_images\\ultrathink\\compress.c
if %errorlevel% neq 0 (
    echo Failed to compile inhal.exe
    pause
    exit /b 1
)

echo.
echo Success! HAL tools compiled to tools\\ directory
pause
'''
    
    with open("compile_hal_tools_simple.bat", "w") as f:
        f.write(batch_content)
    
    print("Created compile_hal_tools_simple.bat")
    print("This batch file will try to find and use any available C compiler.")
    

def create_tcc_solution():
    """Create solution using Tiny C Compiler (no installation required)"""
    
    print("\nAlternative: Tiny C Compiler (TCC) - No installation required!")
    print("1. Download TCC from: http://download.savannah.gnu.org/releases/tinycc/")
    print("2. Download: tcc-0.9.27-win64-bin.zip")
    print("3. Extract to any folder (e.g., C:\\tcc)")
    print("4. Run: C:\\tcc\\tcc.exe -o tools\\exhal.exe <source files>")
    
    tcc_batch = '''@echo off
echo Compiling with Tiny C Compiler...

set TCC_PATH=C:\\tcc\\tcc.exe
if not exist "%TCC_PATH%" (
    echo TCC not found at C:\\tcc\\tcc.exe
    echo Please download from: http://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27-win64-bin.zip
    echo Extract to C:\\tcc\\
    pause
    exit /b 1
)

if not exist "tools" mkdir "tools"

echo Compiling exhal.exe...
"%TCC_PATH%" -o tools\\exhal.exe ..\\archive\\obsolete_test_images\\ultrathink\\exhal.c ..\\archive\\obsolete_test_images\\ultrathink\\compress.c

echo Compiling inhal.exe...
"%TCC_PATH%" -o tools\\inhal.exe ..\\archive\\obsolete_test_images\\ultrathink\\inhal.c ..\\archive\\obsolete_test_images\\ultrathink\\compress.c

echo Done!
pause
'''
    
    with open("compile_with_tcc.bat", "w") as f:
        f.write(tcc_batch)
    
    print("\nCreated compile_with_tcc.bat for use with Tiny C Compiler")


def main():
    print("Windows Binary Download Helper")
    print("==============================\n")
    
    if os.name != 'nt':
        print("This script is for Windows only.")
        return
    
    print("Since winget is not available, here are your options:\n")
    
    print("Option 1: Manual MinGW-w64 Download")
    print("-----------------------------------")
    download_mingw_portable()
    
    print("\n\nOption 2: Automated Batch Files")
    print("--------------------------------")
    create_simple_batch_compiler()
    create_tcc_solution()
    
    print("\n\nOption 3: Direct Download Links")
    print("--------------------------------")
    print("MinGW-w64 (recommended):")
    print("https://github.com/niXman/mingw-builds-binaries/releases")
    print("\nTiny C Compiler (smallest, no install):")
    print("http://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27-win64-bin.zip")
    print("\nMSYS2 (full environment):")
    print("https://www.msys2.org/")
    
    print("\n\nQuickest Solution:")
    print("------------------")
    print("1. Download Tiny C Compiler (2MB): http://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27-win64-bin.zip")
    print("2. Extract to C:\\tcc\\")
    print("3. Run: compile_with_tcc.bat")


if __name__ == "__main__":
    main()