@echo off
echo Compiling with Tiny C Compiler...

set TCC_PATH=C:\tcc\tcc.exe
if not exist "%TCC_PATH%" (
    echo TCC not found at C:\tcc\tcc.exe
    echo Please download from: http://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27-win64-bin.zip
    echo Extract to C:\tcc\
    pause
    exit /b 1
)

if not exist "tools" mkdir "tools"

echo Compiling exhal.exe...
"%TCC_PATH%" -o tools\exhal.exe ..\archive\obsolete_test_images\ultrathink\exhal.c ..\archive\obsolete_test_images\ultrathink\compress.c

echo Compiling inhal.exe...
"%TCC_PATH%" -o tools\inhal.exe ..\archive\obsolete_test_images\ultrathink\inhal.c ..\archive\obsolete_test_images\ultrathink\compress.c

echo Done!
pause
