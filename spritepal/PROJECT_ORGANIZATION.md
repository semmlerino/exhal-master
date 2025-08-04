# SpritePal Project Organization

This document describes the current organization of the SpritePal project after the major cleanup and reorganization performed on 2025-08-03.

## Root Directory Structure

### Core Application Files
- `launch_spritepal.py` - Main application entry point
- `CLAUDE.md` - AI assistant instructions for code development
- `.spritepal_settings.json` - User settings (persistent across sessions)

### ROM Files (Development)
- `Kirby Super Star (USA).sfc` - Test ROM file for development
- `Kirby's Fun Pak (Europe).sfc` - Alternative region ROM for testing
- `test_rom.sfc` - Minimal test ROM for automated testing

### Configuration Files
- `basedpyrightconfig.json` - Type checker configuration
- `conftest.py` - pytest configuration for the entire project
- `pytest.ini` - pytest settings and markers

### Package Management
- `package.json` / `package-lock.json` - Node.js dependencies (if any)
- `install_test_deps.sh` - System dependency installation script

## Major Directories

### `/archive/` and `/archive_2025_07_19/`
**Purpose**: Historical preservation of old code, tests, and development artifacts

**Contents**:
- Old debug scripts that are no longer needed
- Obsolete test files from earlier development phases
- Legacy integration tests that have been superseded
- Generated files from development iterations
- Screenshots and documentation from earlier versions

**Maintenance**: These directories should generally not be modified unless doing archaeological code research

### `/config/`
**Purpose**: Application configuration files and templates

**Subdirectories**:
- `test_profiles/` - Test-specific configuration files for different testing scenarios
- Root level contains default application configuration (palettes, sprite locations)

### `/core/`
**Purpose**: Business logic and core application functionality

**Key Components**:
- Extraction and injection engines
- ROM/VRAM processing logic
- Manager classes (business logic coordination)
- Worker classes (threading coordination)
- Protocol definitions for type safety

### `/docs/`
**Purpose**: Documentation for the project

**Subdirectories**:
- `archived/` - Historical documentation that's no longer current
- `development/` - Development notes, implementation guides, and technical documentation created during feature development

**Key Files**:
- Architecture documentation
- Development guides and best practices
- Feature implementation notes

### `/scripts/`
**Purpose**: Development tools and utilities

**Subdirectories**:
- `analysis/` - VRAM analysis tools, ROM exploration scripts, sprite finding utilities
- `test_runners/` - Specialized test execution scripts with virtual display support
- Root level contains code quality tools (type checking analysis, import analysis, etc.)

### `/test_output/`
**Purpose**: Generated files from tests and development

**Subdirectories**:
- `images/` - PNG and JPEG files generated during testing
- `metadata/` - Palette and sprite metadata files
- `sprites/` - Raw sprite data files and VRAM dumps

**Root Files**: Log files, analysis reports, test results

### `/tests/`
**Purpose**: Test suite for the application

**Organization**:
- Unit tests for core functionality
- Integration tests for UI components
- Mock-based tests for headless environments
- Fixtures and test helpers in subdirectories

### `/tools/`
**Purpose**: External binary tools for HAL compression

**Contents**: Pre-compiled exhal/inhal tools for Windows and Linux

### `/ui/`
**Purpose**: User interface components

**Organization**:
- `common/` - Shared UI utilities and widgets
- `components/` - Reusable UI components organized by type
- `dialogs/` - Application dialogs and their supporting code
- `managers/` - UI coordination and management classes
- Root level contains main windows and primary UI panels

### `/utils/`
**Purpose**: Utility functions and shared code

**Contents**: Constants, validation, image processing, settings management, caching

## File Type Organization

### Python Scripts
- **Application code**: Organized in appropriate module directories
- **Development scripts**: Moved to `/scripts/analysis/` or `/scripts/test_runners/`
- **Archive scripts**: Preserved in `/archive/` directories

### Generated Files
- **Test outputs**: Organized in `/test_output/` with subdirectories by type
- **User-generated**: Remain in root or user-specified locations
- **Development artifacts**: Archived or moved to appropriate analysis directories

### Documentation
- **User documentation**: Remains in `/docs/` root
- **Development documentation**: Organized in `/docs/development/`
- **Historical documentation**: Preserved in `/docs/archived/`

### Configuration Files
- **User settings**: Remain in root directory (`.spritepal_settings.json`)
- **Test configurations**: Organized in `/config/test_profiles/`
- **Development configurations**: Remain in root (`pytest.ini`, `basedpyrightconfig.json`)

## Benefits of This Organization

### For Development
- **Clear separation** between production code and development tools
- **Easy location** of analysis scripts and test utilities
- **Preserved history** in archive directories for reference

### For Testing
- **Organized test outputs** make it easy to examine results
- **Specialized test runners** handle different execution environments
- **Clean separation** between test code and test outputs

### For Maintenance
- **Logical grouping** makes it easier to find related files
- **Documentation organization** supports both users and developers
- **Clear file purposes** reduce confusion about what can be safely removed

## Cleanup Guidelines

### Safe to Clean
- `/test_output/` contents (regenerated during testing)
- `/htmlcov/` (test coverage reports, regenerated)
- Temporary files and logs

### Preserve
- `/archive/` directories (historical reference)
- User configuration files in root
- Documentation in `/docs/`
- All source code directories

### Regular Maintenance
- Periodically clean test output directories
- Archive old development documentation when it becomes obsolete
- Update this organization document when major structural changes are made

## Migration Notes

This organization was implemented on 2025-08-03 to address:
- Cluttered root directory with development scripts
- Scattered test outputs and generated files
- Mixed development and production configuration files
- Unclear purpose of various scripts and utilities

The reorganization maintains full functionality while improving project clarity and maintainability.