# Installing C Compiler on Windows

## Option 1: MinGW-w64 via winget (Recommended)
```powershell
winget install -e --id MSYS2.MSYS2
```

After installation, open MSYS2 terminal and run:
```bash
pacman -S mingw-w64-x86_64-gcc
```

Then add to PATH: `C:\msys64\mingw64\bin`

## Option 2: Standalone MinGW-w64
```powershell
winget install -e --id niXman.mingw-w64
```

## Option 3: LLVM/Clang
```powershell
winget install -e --id LLVM.LLVM
```

## Option 4: Visual Studio Build Tools
```powershell
winget install -e --id Microsoft.VisualStudio.2022.BuildTools
```

After installing any of these, run:
```bash
python compile_hal_tools.py
```