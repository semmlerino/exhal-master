@echo off
REM Compile HAL tools with static linking to avoid DLL dependencies

echo Compiling HAL tools with static linking...

REM Try to find gcc
set GCC=gcc
where gcc >nul 2>&1
if %errorlevel% neq 0 (
    if exist "C:\mingw64\bin\gcc.exe" set GCC=C:\mingw64\bin\gcc.exe
    if exist "C:\MinGW\bin\gcc.exe" set GCC=C:\MinGW\bin\gcc.exe
    if exist "C:\msys64\mingw64\bin\gcc.exe" set GCC=C:\msys64\mingw64\bin\gcc.exe
)

REM Create tools directory
if not exist tools mkdir tools

REM Navigate to source directory
cd ..\archive\obsolete_test_images\ultrathink

REM Compile with static linking
echo.
echo Compiling exhal.exe (static)...
%GCC% -O2 -static -static-libgcc -o ..\..\..\..\spritepal\tools\exhal.exe exhal.c compress.c
if %errorlevel% neq 0 (
    echo Failed to compile exhal.exe
    pause
    exit /b 1
)

echo Compiling inhal.exe (static)...
%GCC% -O2 -static -static-libgcc -o ..\..\..\..\spritepal\tools\inhal.exe inhal.c compress.c
if %errorlevel% neq 0 (
    echo Failed to compile inhal.exe
    pause
    exit /b 1
)

cd ..\..\..\..\spritepal

echo.
echo Success! Static HAL tools compiled to tools\ directory
echo These executables have no DLL dependencies.
pause