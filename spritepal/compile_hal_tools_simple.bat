@echo off
echo Attempting to compile HAL tools for Windows...
echo.

REM Try different compilers
set COMPILER=
set FOUND=0

REM Check for gcc in common locations
if exist "C:\mingw64\bin\gcc.exe" (
    set COMPILER=C:\mingw64\bin\gcc.exe
    set FOUND=1
    echo Found GCC at C:\mingw64\bin\gcc.exe
) else if exist "C:\msys64\mingw64\bin\gcc.exe" (
    set COMPILER=C:\msys64\mingw64\bin\gcc.exe
    set FOUND=1
    echo Found GCC at C:\msys64\mingw64\bin\gcc.exe
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
    echo 2. Extract to C:\mingw64
    echo 3. Run this script again
    pause
    exit /b 1
)

REM Create tools directory
if not exist "tools" mkdir "tools"

REM Compile tools
echo.
echo Compiling exhal.exe...
%COMPILER% -O2 -o tools\exhal.exe ..\archive\obsolete_test_images\ultrathink\exhal.c ..\archive\obsolete_test_images\ultrathink\compress.c
if %errorlevel% neq 0 (
    echo Failed to compile exhal.exe
    pause
    exit /b 1
)

echo Compiling inhal.exe...
%COMPILER% -O2 -o tools\inhal.exe ..\archive\obsolete_test_images\ultrathink\inhal.c ..\archive\obsolete_test_images\ultrathink\compress.c
if %errorlevel% neq 0 (
    echo Failed to compile inhal.exe
    pause
    exit /b 1
)

echo.
echo Success! HAL tools compiled to tools\ directory
pause
