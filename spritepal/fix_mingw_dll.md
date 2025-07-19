# Fixing MinGW DLL Issues

## Quick Fix: Static Compilation
Run this to compile without DLL dependencies:
```batch
compile_hal_static.bat
```

## Alternative Fixes:

### Option 1: Copy Missing DLLs
Find and copy these DLLs to your tools folder:
- libisl-15.dll
- libgcc_s_seh-1.dll
- libwinpthread-1.dll

They're usually in:
- C:\mingw64\bin\
- C:\MinGW\bin\

### Option 2: Use MSYS2 Environment
If you installed via MSYS2, run compilation from MSYS2 terminal:
1. Open "MSYS2 MinGW 64-bit" from Start Menu
2. Navigate to project: `cd /c/CustomScripts/KirbyMax/workshop/exhal-master/spritepal`
3. Run: `python compile_hal_tools.py`

### Option 3: Download Visual Studio Build Tools
Use Microsoft's compiler which doesn't have DLL issues:
1. Download: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
2. Install "Desktop development with C++"
3. Open "Developer Command Prompt"
4. Run: `python compile_hal_tools.py`

### Option 4: Use TCC (Tiny C Compiler)
Simplest solution - no DLLs needed:
1. Download: http://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27-win64-bin.zip
2. Extract to C:\tcc\
3. Run: `compile_with_tcc.bat`