@echo off
REM Compile HAL compression tools for Windows
REM Requires MinGW-w64 or similar GCC for Windows

echo Compiling HAL compression tools for Windows...

REM Navigate to source directory
cd ..\archive\obsolete_test_images\ultrathink

REM Compile exhal
echo Compiling exhal.exe...
gcc -O2 -o exhal.exe exhal.c compress.c
if %errorlevel% neq 0 (
    echo Failed to compile exhal.exe
    exit /b 1
)

REM Compile inhal
echo Compiling inhal.exe...
gcc -O2 -o inhal.exe inhal.c compress.c
if %errorlevel% neq 0 (
    echo Failed to compile inhal.exe
    exit /b 1
)

REM Copy to spritepal tools directory
echo Copying executables...
if not exist "..\..\..\..\spritepal\tools" mkdir "..\..\..\..\spritepal\tools"
copy exhal.exe ..\..\..\..\spritepal\tools\
copy inhal.exe ..\..\..\..\spritepal\tools\

echo Done! HAL tools compiled and copied to spritepal\tools\