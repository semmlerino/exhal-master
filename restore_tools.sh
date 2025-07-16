#!/bin/bash
# Restore useful tools based on documentation references

echo "Restoring useful tools from archive/obsolete directories..."

# Core palette extraction tools
echo "Restoring palette extraction tools..."
cp obsolete_cleanup_2025_07_15/mss_palette_extractor.py .
cp obsolete_cleanup_2025_07_15/analyze_palettes.py .
cp obsolete_cleanup_2025_07_15/extract_palette_for_editor.py .

# VRAM/OAM analysis tools
echo "Restoring VRAM/OAM analysis tools..."
cp obsolete_cleanup_2025_07_15/analyze_oam_dumps.py .
cp obsolete_cleanup_2025_07_15/rom_analyzer.py .

# Sprite extraction utilities
echo "Restoring sprite extraction utilities..."
cp obsolete_cleanup_2025_07_15/extract_4bpp_section.py .
cp obsolete_cleanup_2025_07_15/create_grayscale_with_palette.py .

# Additional useful tools from archive
echo "Restoring additional archive tools..."
cp archive/analysis/create_character_sheet.py .
cp archive/analysis/parse_synchronized_data.py .
cp archive/analysis/extract_mss_palettes.py .

# Demo/workflow scripts that are useful as references
echo "Restoring demo/workflow scripts..."
mkdir -p restored_demos
cp archive/experimental/demo_edit_and_reinsert.py restored_demos/
cp archive/experimental/demo_unified_workflow.py restored_demos/
cp archive/experimental/demo_all_characters.py restored_demos/

echo "Tools restored successfully!"
echo ""
echo "Key tools now available:"
echo "  - mss_palette_extractor.py: Extract palettes from Mesen-S savestates"
echo "  - analyze_oam_dumps.py: Analyze OAM data for sprite-palette mappings"
echo "  - rom_analyzer.py: Analyze ROM structure and find sprite data"
echo "  - extract_4bpp_section.py: Extract focused sprite sections"
echo "  - create_character_sheet.py: Create organized sprite sheets"
echo ""
echo "Demo scripts in restored_demos/ for reference"