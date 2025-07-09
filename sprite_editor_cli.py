#!/usr/bin/env python3
"""
Command-line interface for Kirby Super Star sprite editing
Provides an interactive menu-driven interface without GUI dependencies
"""

import os

from sprite_edit_workflow import SpriteEditWorkflow
from sprite_sheet_editor import SpriteSheetEditor


class SpriteEditorCLI:
    """Interactive command-line sprite editor"""

    def __init__(self):
        self.workflow = None
        self.sheet_editor = None
        self.current_workspace = None

    def print_header(self):
        """Print application header"""
        print("\n" + "=" * 60)
        print("    Kirby Super Star Sprite Editor - Interactive CLI")
        print("=" * 60)

    def print_menu(self):
        """Print main menu"""
        print("\nMain Menu:")
        print("1. Extract Sprites")
        print("2. Validate Edited Sprites")
        print("3. Reinsert Sprites")
        print("4. Quick Actions")
        print("5. Visual Tools")
        print("6. Help")
        print("0. Exit")
        print()

    def get_choice(self, prompt="Select option: ", valid_choices=None):
        """Get user choice with validation"""
        while True:
            choice = input(prompt).strip()
            if valid_choices and choice not in valid_choices:
                print("Invalid choice. Please try again.")
            else:
                return choice

    def extract_menu(self):
        """Extraction submenu"""
        print("\n--- Extract Sprites ---")
        print("1. Extract as individual tiles")
        print("2. Extract as sprite sheet")
        print("3. Quick extract Kirby sprites")
        print("4. Quick extract enemy sprites")
        print("0. Back to main menu")

        choice = self.get_choice("Select extraction type: ", ["0", "1", "2", "3", "4"])

        if choice == "0":
            return
        if choice == "3":
            self.quick_extract_kirby()
        elif choice == "4":
            self.quick_extract_enemies()
        else:
            # Get common inputs
            vram_file = input("VRAM dump file: ").strip()
            if not os.path.exists(vram_file):
                print(f"Error: File not found: {vram_file}")
                return

            cgram_file = input("CGRAM dump file: ").strip()
            if not os.path.exists(cgram_file):
                print(f"Error: File not found: {cgram_file}")
                return

            mappings_file = input("Palette mappings file (optional, press Enter to skip): ").strip()
            if not mappings_file:
                mappings_file = None

            offset_str = input("Offset (hex, default 0xC000): ").strip()
            offset = int(offset_str, 16) if offset_str else 0xC000

            size_str = input("Size (hex, default 0x1000): ").strip()
            size = int(size_str, 16) if size_str else 0x1000

            if choice == "1":
                # Individual tiles
                output_dir = input("Output directory: ").strip()
                if not output_dir:
                    output_dir = "extracted_sprites"

                os.makedirs(output_dir, exist_ok=True)

                print(f"\nExtracting tiles to {output_dir}...")
                self.workflow = SpriteEditWorkflow(mappings_file)

                try:
                    metadata = self.workflow.extract_for_editing(
                        vram_file, cgram_file, offset, size, output_dir
                    )
                    print(f"✓ Successfully extracted {len(metadata['tile_palette_mappings'])} tiles")
                    self.current_workspace = output_dir
                except Exception as e:
                    print(f"✗ Extraction failed: {e}")

            else:
                # Sprite sheet
                output_file = input("Output PNG file: ").strip()
                if not output_file:
                    output_file = "sprite_sheet.png"

                create_guide = input("Create editing guide? (y/n): ").lower() == "y"

                print(f"\nExtracting sprite sheet to {output_file}...")
                self.sheet_editor = SpriteSheetEditor(mappings_file)

                try:
                    metadata = self.sheet_editor.extract_sheet_for_editing(
                        vram_file, cgram_file, offset, size, output_file
                    )

                    if create_guide:
                        self.sheet_editor.create_editing_guide(output_file)

                    print("✓ Successfully extracted sprite sheet")
                except Exception as e:
                    print(f"✗ Extraction failed: {e}")

    def validate_menu(self):
        """Validation submenu"""
        print("\n--- Validate Sprites ---")
        print("1. Validate tile folder")
        print("2. Validate sprite sheet PNG")
        print("0. Back to main menu")

        choice = self.get_choice("Select validation type: ", ["0", "1", "2"])

        if choice == "0":
            return

        if choice == "1":
            # Validate folder
            input_dir = input("Folder with edited tiles: ").strip()
            if not input_dir and self.current_workspace:
                input_dir = self.current_workspace
                print(f"Using current workspace: {input_dir}")

            if not os.path.isdir(input_dir):
                print(f"Error: Directory not found: {input_dir}")
                return

            print(f"\nValidating tiles in {input_dir}...")
            self.workflow = SpriteEditWorkflow()

            try:
                results = self.workflow.validate_edited_sprites(input_dir)
                print(f"\n✓ Valid tiles: {len(results['valid_tiles'])}")
                print(f"✗ Invalid tiles: {len(results['invalid_tiles'])}")
                print(f"⚠ Warnings: {len(results['warnings'])}")

                if results["invalid_tiles"]:
                    print("\nInvalid tiles:")
                    for invalid in results["invalid_tiles"][:5]:
                        print(f"  - {invalid['tile']}: {invalid['error']}")
                    if len(results["invalid_tiles"]) > 5:
                        print(f"  ... and {len(results['invalid_tiles']) - 5} more")

            except Exception as e:
                print(f"✗ Validation failed: {e}")

        else:
            # Validate sheet
            input_file = input("Sprite sheet PNG file: ").strip()
            if not os.path.exists(input_file):
                print(f"Error: File not found: {input_file}")
                return

            print(f"\nValidating sprite sheet {input_file}...")
            self.sheet_editor = SpriteSheetEditor()

            try:
                results = self.sheet_editor.validate_edited_sheet(input_file)
                if results["valid"]:
                    print("✓ Validation passed!")
                else:
                    print("✗ Validation failed!")
                    print(f"Errors: {len(results['errors'])}")
                    for error in results["errors"][:5]:
                        print(f"  - {error}")
            except Exception as e:
                print(f"✗ Validation failed: {e}")

    def reinsert_menu(self):
        """Reinsertion submenu"""
        print("\n--- Reinsert Sprites ---")
        print("1. Reinsert from tile folder")
        print("2. Reinsert from sprite sheet")
        print("0. Back to main menu")

        choice = self.get_choice("Select reinsertion type: ", ["0", "1", "2"])

        if choice == "0":
            return

        create_backup = input("Create backup? (y/n): ").lower() == "y"

        if choice == "1":
            # Reinsert tiles
            input_dir = input("Folder with edited tiles: ").strip()
            if not input_dir and self.current_workspace:
                input_dir = self.current_workspace
                print(f"Using current workspace: {input_dir}")

            if not os.path.isdir(input_dir):
                print(f"Error: Directory not found: {input_dir}")
                return

            output_vram = input("Output VRAM file (press Enter for auto): ").strip() or None

            print(f"\nReinserting sprites from {input_dir}...")
            self.workflow = SpriteEditWorkflow()

            try:
                result = self.workflow.reinsert_sprites(input_dir, output_vram, create_backup)
                if result:
                    print(f"✓ Successfully reinserted sprites to: {result}")
                else:
                    print("✗ Reinsertion cancelled or failed")
            except Exception as e:
                print(f"✗ Reinsertion failed: {e}")

        else:
            # Reinsert sheet
            input_file = input("Edited sprite sheet PNG: ").strip()
            if not os.path.exists(input_file):
                print(f"Error: File not found: {input_file}")
                return

            output_vram = input("Output VRAM file (press Enter for auto): ").strip() or None

            print(f"\nReinserting sprite sheet {input_file}...")
            self.sheet_editor = SpriteSheetEditor()

            try:
                result = self.sheet_editor.reinsert_sheet(input_file, output_vram)
                if result:
                    print(f"✓ Successfully reinserted sprites to: {result}")
                else:
                    print("✗ Reinsertion cancelled or failed")
            except Exception as e:
                print(f"✗ Reinsertion failed: {e}")

    def quick_actions_menu(self):
        """Quick actions submenu"""
        print("\n--- Quick Actions ---")
        print("1. Extract and validate Kirby sprites")
        print("2. Extract full sprite sheet with guide")
        print("3. Batch validate all workspaces")
        print("0. Back to main menu")

        choice = self.get_choice("Select quick action: ", ["0", "1", "2", "3"])

        if choice == "1":
            self.quick_extract_and_validate_kirby()
        elif choice == "2":
            self.quick_extract_full_sheet()
        elif choice == "3":
            self.batch_validate_workspaces()

    def quick_extract_kirby(self):
        """Quick extract Kirby sprites"""
        print("\nQuick extracting Kirby sprites...")

        # Look for common dump files
        vram_candidates = ["Cave.SnesVideoRam.dmp", "VRAM.dmp", "sync3_vram.dmp"]
        cgram_candidates = ["Cave.SnesCgRam.dmp", "CGRAM.dmp", "sync3_cgram.dmp"]

        vram_file = None
        cgram_file = None

        for vf in vram_candidates:
            if os.path.exists(vf):
                vram_file = vf
                break

        for cf in cgram_candidates:
            if os.path.exists(cf):
                cgram_file = cf
                break

        if not vram_file or not cgram_file:
            print("Error: Could not find VRAM and CGRAM dumps")
            print("Please ensure dump files are in the current directory")
            return

        print(f"Using VRAM: {vram_file}")
        print(f"Using CGRAM: {cgram_file}")

        # Look for palette mappings
        mappings_file = "final_palette_mapping.json" if os.path.exists("final_palette_mapping.json") else None
        if mappings_file:
            print(f"Using palette mappings: {mappings_file}")

        output_dir = "kirby_sprites"
        os.makedirs(output_dir, exist_ok=True)

        self.workflow = SpriteEditWorkflow(mappings_file)

        try:
            metadata = self.workflow.extract_for_editing(
                vram_file, cgram_file, 0xC000, 0x400, output_dir
            )
            print(f"✓ Successfully extracted {len(metadata['tile_palette_mappings'])} Kirby tiles to {output_dir}")
            self.current_workspace = output_dir
        except Exception as e:
            print(f"✗ Extraction failed: {e}")

    def quick_extract_enemies(self):
        """Quick extract enemy sprites"""
        print("\nQuick extracting enemy sprites...")

        # Similar to Kirby but different region
        vram_candidates = ["Cave.SnesVideoRam.dmp", "VRAM.dmp", "sync3_vram.dmp"]
        cgram_candidates = ["Cave.SnesCgRam.dmp", "CGRAM.dmp", "sync3_cgram.dmp"]

        vram_file = None
        cgram_file = None

        for vf in vram_candidates:
            if os.path.exists(vf):
                vram_file = vf
                break

        for cf in cgram_candidates:
            if os.path.exists(cf):
                cgram_file = cf
                break

        if not vram_file or not cgram_file:
            print("Error: Could not find VRAM and CGRAM dumps")
            return

        print(f"Using VRAM: {vram_file}")
        print(f"Using CGRAM: {cgram_file}")

        mappings_file = "final_palette_mapping.json" if os.path.exists("final_palette_mapping.json") else None

        output_dir = "enemy_sprites"
        os.makedirs(output_dir, exist_ok=True)

        self.workflow = SpriteEditWorkflow(mappings_file)

        try:
            metadata = self.workflow.extract_for_editing(
                vram_file, cgram_file, 0xC800, 0x800, output_dir
            )
            print(f"✓ Successfully extracted {len(metadata['tile_palette_mappings'])} enemy tiles to {output_dir}")
        except Exception as e:
            print(f"✗ Extraction failed: {e}")

    def quick_extract_and_validate_kirby(self):
        """Extract and validate Kirby sprites in one go"""
        self.quick_extract_kirby()

        if self.current_workspace:
            print("\nAutomatically validating extracted sprites...")
            self.workflow = SpriteEditWorkflow()

            try:
                results = self.workflow.validate_edited_sprites(self.current_workspace)
                print(f"✓ All {len(results['valid_tiles'])} tiles are valid!")
            except Exception as e:
                print(f"✗ Validation failed: {e}")

    def quick_extract_full_sheet(self):
        """Quick extract full sprite sheet with guide"""
        print("\nQuick extracting full sprite sheet...")

        # Find dump files
        vram_candidates = ["Cave.SnesVideoRam.dmp", "VRAM.dmp", "sync3_vram.dmp"]
        cgram_candidates = ["Cave.SnesCgRam.dmp", "CGRAM.dmp", "sync3_cgram.dmp"]

        vram_file = None
        cgram_file = None

        for vf in vram_candidates:
            if os.path.exists(vf):
                vram_file = vf
                break

        for cf in cgram_candidates:
            if os.path.exists(cf):
                cgram_file = cf
                break

        if not vram_file or not cgram_file:
            print("Error: Could not find VRAM and CGRAM dumps")
            return

        mappings_file = "final_palette_mapping.json" if os.path.exists("final_palette_mapping.json") else None

        output_file = "full_sprite_sheet.png"

        self.sheet_editor = SpriteSheetEditor(mappings_file)

        try:
            self.sheet_editor.extract_sheet_for_editing(
                vram_file, cgram_file, 0xC000, 0x4000, output_file
            )
            self.sheet_editor.create_editing_guide(output_file)
            print("✓ Successfully extracted full sprite sheet")
            print(f"  Sheet: {output_file}")
            print(f"  Guide: {output_file.replace('.png', '_editing_guide.png')}")
        except Exception as e:
            print(f"✗ Extraction failed: {e}")

    def batch_validate_workspaces(self):
        """Validate all workspace directories"""
        print("\nScanning for workspace directories...")

        workspaces = []
        for item in os.listdir("."):
            if os.path.isdir(item):
                metadata_file = os.path.join(item, "extraction_metadata.json")
                if os.path.exists(metadata_file):
                    workspaces.append(item)

        if not workspaces:
            print("No workspace directories found")
            return

        print(f"Found {len(workspaces)} workspace(s):")
        for ws in workspaces:
            print(f"  - {ws}")

        proceed = input("\nValidate all? (y/n): ").lower() == "y"
        if not proceed:
            return

        self.workflow = SpriteEditWorkflow()

        for ws in workspaces:
            print(f"\nValidating {ws}...")
            try:
                results = self.workflow.validate_edited_sprites(ws)
                valid = len(results["valid_tiles"])
                invalid = len(results["invalid_tiles"])
                print(f"  ✓ Valid: {valid}, ✗ Invalid: {invalid}")
            except Exception as e:
                print(f"  ✗ Error: {e}")

    def visual_tools_menu(self):
        """Visual tools submenu"""
        print("\n--- Visual Tools ---")
        print("1. Create palette reference")
        print("2. Generate coverage map")
        print("3. Create workflow diagram")
        print("0. Back to main menu")

        choice = self.get_choice("Select visual tool: ", ["0", "1", "2", "3"])

        if choice == "1":
            print("Creating palette reference...")
            # TODO: Implement palette reference
            print("Palette reference generation not yet implemented in CLI")
        elif choice == "2":
            print("Generating coverage map...")
            # TODO: Implement coverage map
            print("Coverage map generation not yet implemented in CLI")
        elif choice == "3":
            self.create_workflow_diagram()

    def create_workflow_diagram(self):
        """Create a simple workflow diagram"""
        print("\nSprite Editing Workflow:")
        print("=" * 50)
        print()
        print("1. EXTRACT")
        print("   VRAM + CGRAM → Individual Tiles or Sprite Sheet")
        print("        ↓")
        print("2. EDIT")
        print("   Use image editor (keep indexed colors!)")
        print("        ↓")
        print("3. VALIDATE")
        print("   Check SNES constraints")
        print("        ↓")
        print("4. REINSERT")
        print("   Create modified VRAM dump")
        print("        ↓")
        print("5. TEST")
        print("   Load in emulator")
        print()
        print("=" * 50)

    def show_help(self):
        """Show help information"""
        print("\n--- Help ---")
        print()
        print("QUICK START:")
        print("1. Place VRAM and CGRAM dumps in current directory")
        print("2. Use 'Extract Sprites' to extract tiles or sheets")
        print("3. Edit extracted sprites in your image editor")
        print("4. Use 'Validate' to check constraints")
        print("5. Use 'Reinsert' to create modified VRAM")
        print()
        print("FILE FORMATS:")
        print("- VRAM dumps: Usually .dmp or .bin, 64KB")
        print("- CGRAM dumps: Usually .dmp or .bin, 512 bytes")
        print("- Palette mappings: JSON file with tile→palette data")
        print()
        print("COMMON OFFSETS:")
        print("- 0xC000: Start of sprite area (Kirby)")
        print("- 0xC800: Enemy sprites")
        print("- 0xD000: Effects/projectiles")
        print()
        print("CONSTRAINTS:")
        print("- 8×8 pixel tiles")
        print("- Max 15 colors + transparent per tile")
        print("- Must use existing palette colors")
        print("- Color 0 is always transparent")
        print()
        input("Press Enter to continue...")

    def run(self):
        """Main application loop"""
        self.print_header()

        while True:
            self.print_menu()
            choice = self.get_choice("Select option: ", ["0", "1", "2", "3", "4", "5", "6"])

            if choice == "0":
                print("\nThank you for using Kirby Super Star Sprite Editor!")
                break
            if choice == "1":
                self.extract_menu()
            elif choice == "2":
                self.validate_menu()
            elif choice == "3":
                self.reinsert_menu()
            elif choice == "4":
                self.quick_actions_menu()
            elif choice == "5":
                self.visual_tools_menu()
            elif choice == "6":
                self.show_help()


def main():
    """Main entry point"""
    try:
        cli = SpriteEditorCLI()
        cli.run()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
