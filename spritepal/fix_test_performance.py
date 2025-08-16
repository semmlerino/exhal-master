#!/usr/bin/env python3
"""
Fix test performance by adding no_manager_setup marker to tests that don't need managers.

The autouse setup_managers fixture is taking 0.35s per test setup and 0.15s teardown.
Tests that don't need managers should be marked with no_manager_setup to skip this overhead.
"""

import re
from pathlib import Path

def needs_managers(content: str) -> bool:
    """Determine if test file needs managers based on content."""
    # Patterns indicating manager usage
    manager_patterns = [
        r'ExtractionManager',
        r'InjectionManager', 
        r'SessionManager',
        r'ExtractorManager',
        r'rom_extraction_panel',
        r'manual_offset_dialog',
        r'managers_initialized',
        r'session_managers',
        r'fast_managers',
        r'from core\.managers',
        r'initialize_managers',
        r'cleanup_managers',
    ]
    
    # Check if any manager pattern exists
    for pattern in manager_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return True
    
    # Patterns indicating simple unit tests that don't need managers
    simple_test_indicators = [
        r'test.*exception',
        r'test.*constant',
        r'test.*util',
        r'test.*helper',
        r'test.*data_structure',
        r'test.*algorithm',
    ]
    
    filename_lower = str(Path(content).name).lower() if len(content) < 100 else ""
    for pattern in simple_test_indicators:
        if re.search(pattern, filename_lower, re.IGNORECASE):
            return False
    
    # Default to needing managers if uncertain
    return True

def add_no_manager_marker(file_path: Path) -> bool:
    """Add no_manager_setup marker to test file if it doesn't need managers."""
    content = file_path.read_text()
    
    # Skip if already has the marker
    if 'no_manager_setup' in content:
        return False
    
    # Check if file needs managers
    if needs_managers(content):
        return False
    
    # Find existing pytestmark
    pytestmark_match = re.search(r'^pytestmark\s*=\s*\[(.*?)\]', content, re.MULTILINE | re.DOTALL)
    
    if pytestmark_match:
        # Add to existing pytestmark
        start, end = pytestmark_match.span()
        markers = pytestmark_match.group(1)
        
        # Parse existing markers properly
        if markers.strip():
            new_markers = markers.rstrip() + ',\n    pytest.mark.no_manager_setup,\n'
        else:
            new_markers = '\n    pytest.mark.no_manager_setup,\n'
        
        new_content = content[:start] + f'pytestmark = [{new_markers}]' + content[end:]
    else:
        # Add new pytestmark after imports
        import_end = 0
        for match in re.finditer(r'^(from|import)\s+', content, re.MULTILINE):
            import_end = max(import_end, match.end())
        
        # Find the next line after imports
        next_line = content.find('\n', import_end)
        if next_line == -1:
            next_line = len(content)
        
        # Insert pytestmark
        new_content = (content[:next_line] + 
                      '\n\npytestmark = [pytest.mark.no_manager_setup]\n' + 
                      content[next_line:])
    
    file_path.write_text(new_content)
    return True

def main():
    """Fix test performance by marking tests that don't need managers."""
    test_dir = Path('tests')
    
    # Files that definitely don't need managers
    simple_test_files = [
        'test_constants.py',
        'test_exceptions.py',
        'test_utils.py',
        'test_data_structures.py',
        'test_algorithms.py',
        'test_compression.py',
        'test_memory_utils.py',
        'test_color_conversion.py',
    ]
    
    updated_files = []
    
    # First, handle known simple test files
    for filename in simple_test_files:
        for test_file in test_dir.rglob(filename):
            if test_file.is_file() and add_no_manager_marker(test_file):
                updated_files.append(test_file)
                print(f"Added no_manager_setup marker to: {test_file}")
    
    # Now scan other test files and analyze them
    for test_file in test_dir.rglob('test_*.py'):
        if test_file.is_file() and test_file.name not in simple_test_files:
            content = test_file.read_text()
            
            # Very conservative - only mark files that clearly don't use Qt/managers
            if ('QWidget' not in content and 
                'QDialog' not in content and
                'qtbot' not in content and
                'Manager' not in content and
                'manager' not in content and
                'panel' not in content and
                'dialog' not in content):
                
                if add_no_manager_marker(test_file):
                    updated_files.append(test_file)
                    print(f"Added no_manager_setup marker to: {test_file}")
    
    print(f"\nUpdated {len(updated_files)} test files")
    print("\nFiles updated:")
    for f in sorted(updated_files):
        print(f"  - {f}")

if __name__ == '__main__':
    main()