# SpritePal Development Script for Windows PowerShell
# Usage: .\dev.ps1 <command>

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "SpritePal Development Commands (Windows)" -ForegroundColor Green
    Write-Host "=======================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Environment Setup:" -ForegroundColor Yellow
    Write-Host "  install         Install production dependencies"
    Write-Host "  install-dev     Install development dependencies"
    Write-Host "  setup           Complete development environment setup"
    Write-Host ""
    Write-Host "Testing:" -ForegroundColor Yellow
    Write-Host "  test            Run all tests with coverage"
    Write-Host "  test-unit       Run unit tests only (fast)"
    Write-Host "  test-gui        Run GUI tests"
    Write-Host "  test-all        Run all tests including GUI"
    Write-Host ""
    Write-Host "Code Quality:" -ForegroundColor Yellow
    Write-Host "  lint            Run linting checks"
    Write-Host "  lint-fix        Fix linting issues automatically"
    Write-Host "  format          Format code"
    Write-Host "  type-check      Run type checking"
    Write-Host "  security        Run security scans"
    Write-Host "  all-checks      Run all quality checks"
    Write-Host ""
    Write-Host "Application:" -ForegroundColor Yellow
    Write-Host "  run             Launch SpritePal application"
    Write-Host "  run-debug       Launch with debug logging"
    Write-Host ""
    Write-Host "Building:" -ForegroundColor Yellow
    Write-Host "  build           Build distribution packages"
    Write-Host "  clean           Clean generated files"
    Write-Host ""
    Write-Host "Utilities:" -ForegroundColor Yellow
    Write-Host "  coverage        Generate coverage report"
    Write-Host "  pre-commit      Run pre-commit hooks"
    Write-Host "  verify-setup    Verify environment setup"
    Write-Host "  quick           Quick dev cycle (format, lint, test)"
    Write-Host "  full            Full dev cycle with all checks"
}

function Install-Dependencies {
    Write-Host "Installing production dependencies..." -ForegroundColor Blue
    pip install -r requirements.txt
}

function Install-DevDependencies {
    Write-Host "Installing development dependencies..." -ForegroundColor Blue
    pip install -r dev-requirements.txt
    pre-commit install
}

function Setup-Environment {
    Install-DevDependencies
    Write-Host "Development environment setup complete!" -ForegroundColor Green
    Write-Host "Run '.\dev.ps1 test' to verify everything works" -ForegroundColor Green
}

function Clean-Files {
    Write-Host "Cleaning generated files and caches..." -ForegroundColor Blue
    Get-ChildItem -Recurse -Name "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Name "__pycache__" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Name ".pytest_cache" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Name ".mypy_cache" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Name ".ruff_cache" -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "htmlcov" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "dist" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "*.egg-info" -ErrorAction SilentlyContinue
    Remove-Item -Force ".coverage" -ErrorAction SilentlyContinue
    Remove-Item -Force "coverage.xml" -ErrorAction SilentlyContinue
}

function Run-Tests {
    Write-Host "Running tests with coverage..." -ForegroundColor Blue
    pytest spritepal/tests/ -v --cov=spritepal --cov-report=html --cov-report=term -m "not gui"
}

function Run-UnitTests {
    Write-Host "Running unit tests..." -ForegroundColor Blue
    pytest spritepal/tests/ -v -m "unit" --tb=short
}

function Run-GuiTests {
    Write-Host "Running GUI tests..." -ForegroundColor Blue
    $env:QT_QPA_PLATFORM = "offscreen"
    pytest spritepal/tests/ -v -m "gui" --tb=short
}

function Run-AllTests {
    Write-Host "Running all tests..." -ForegroundColor Blue
    pytest spritepal/tests/ -v --cov=spritepal --cov-report=html --tb=short
}

function Run-Linting {
    Write-Host "Running linting checks..." -ForegroundColor Blue
    ruff check spritepal/
}

function Fix-Linting {
    Write-Host "Fixing linting issues..." -ForegroundColor Blue
    ruff check spritepal/ --fix
}

function Format-Code {
    Write-Host "Formatting code..." -ForegroundColor Blue
    ruff format spritepal/
}

function Run-TypeCheck {
    Write-Host "Running type checking..." -ForegroundColor Blue
    mypy spritepal/
}

function Run-Security {
    Write-Host "Running security scans..." -ForegroundColor Blue
    bandit -r spritepal/ -f screen
    safety check
}

function Run-AllChecks {
    Write-Host "Running all quality checks..." -ForegroundColor Blue
    Run-Linting
    Run-TypeCheck
    Run-Security
    Run-UnitTests
}

function Run-Application {
    Write-Host "Launching SpritePal..." -ForegroundColor Blue
    Set-Location spritepal
    python launch_spritepal.py
    Set-Location ..
}

function Run-ApplicationDebug {
    Write-Host "Launching SpritePal with debug logging..." -ForegroundColor Blue
    $env:PYTHONPATH = ".."
    Set-Location spritepal
    python launch_spritepal.py --debug
    Set-Location ..
}

function Build-Package {
    Write-Host "Building distribution packages..." -ForegroundColor Blue
    Clean-Files
    python -m build
}

function Generate-Coverage {
    Write-Host "Generating coverage report..." -ForegroundColor Blue
    pytest spritepal/tests/ --cov=spritepal --cov-report=html --cov-report=term
    Write-Host "Coverage report generated in htmlcov/" -ForegroundColor Green
}

function Run-PreCommit {
    Write-Host "Running pre-commit hooks..." -ForegroundColor Blue
    pre-commit run --all-files
}

function Verify-Setup {
    Write-Host "Verifying development environment setup..." -ForegroundColor Blue
    Write-Host "Python version:" -ForegroundColor Yellow
    python --version
    
    Write-Host "Verifying dependencies..." -ForegroundColor Yellow
    python -c "import PyQt6; print('PyQt6:', PyQt6.QtCore.PYQT_VERSION_STR)"
    python -c "import PIL; print('Pillow:', PIL.__version__)"
    python -c "import numpy; print('NumPy:', numpy.__version__)"
    
    Write-Host "Verifying tools..." -ForegroundColor Yellow
    ruff --version
    mypy --version
    pytest --version
    
    Write-Host "Environment verification complete!" -ForegroundColor Green
}

function Quick-Cycle {
    Write-Host "Running quick development cycle..." -ForegroundColor Blue
    Format-Code
    Fix-Linting
    Run-UnitTests
}

function Full-Cycle {
    Write-Host "Running full development cycle..." -ForegroundColor Blue
    Clean-Files
    Format-Code
    Run-Linting
    Run-TypeCheck
    Run-Security
    Run-Tests
    Generate-Coverage
}

# Command routing
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "install" { Install-Dependencies }
    "install-dev" { Install-DevDependencies }
    "setup" { Setup-Environment }
    "clean" { Clean-Files }
    "test" { Run-Tests }
    "test-unit" { Run-UnitTests }
    "test-gui" { Run-GuiTests }
    "test-all" { Run-AllTests }
    "lint" { Run-Linting }
    "lint-fix" { Fix-Linting }
    "format" { Format-Code }
    "type-check" { Run-TypeCheck }
    "security" { Run-Security }
    "all-checks" { Run-AllChecks }
    "run" { Run-Application }
    "run-debug" { Run-ApplicationDebug }
    "build" { Build-Package }
    "coverage" { Generate-Coverage }
    "pre-commit" { Run-PreCommit }
    "verify-setup" { Verify-Setup }
    "quick" { Quick-Cycle }
    "full" { Full-Cycle }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host "Run '.\dev.ps1 help' for available commands" -ForegroundColor Yellow
    }
}