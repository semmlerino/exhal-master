#!/usr/bin/env python3
"""
ROM Offset Validation: Lua Script vs SpritePal Manual Offset

This script compares ROM offsets discovered by Mesen2 Lua scripts
with SpritePal's sprite validation to verify accuracy.

The validation tests whether:
1. ROM offsets found by Lua DMA monitoring contain valid sprite data
2. SpritePal's manual offset slider correctly identifies the same sprites
3. Both systems produce consistent results for sprite detection

Usage:
    python validate_lua_vs_spritepal_offsets.py --rom ROM_FILE --lua-json LUA_OUTPUT.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.sprite_finder import SpriteFinder
from utils.logging_config import get_logger

logger = get_logger(__name__)


class LuaSpritePalValidator:
    """Validates ROM offsets found by Lua scripts against SpritePal sprite detection."""
    
    def __init__(self, rom_path: str):
        """
        Initialize validator.
        
        Args:
            rom_path: Path to ROM file
        """
        self.rom_path = rom_path
        self.sprite_finder = SpriteFinder()
        self.results = {
            "rom_file": rom_path,
            "lua_offsets": [],
            "spritepal_validation": [],
            "matches": [],
            "discrepancies": [],
            "summary": {}
        }
        
    def load_lua_results(self, lua_json_path: str) -> List[int]:
        """
        Load ROM offsets from Lua script JSON output.
        
        Args:
            lua_json_path: Path to JSON file from Lua script
            
        Returns:
            List of ROM offsets found by Lua script
        """
        logger.info(f"Loading Lua results from: {lua_json_path}")
        
        try:
            with open(lua_json_path, 'r') as f:
                data = json.load(f)
                
            # Handle different JSON formats from the two Lua scripts
            offsets = []
            
            if 'rom_offsets' in data:
                # Standard format with rom_offsets array
                for entry in data['rom_offsets']:
                    if isinstance(entry, dict):
                        offset = entry.get('offset', 0)
                    else:
                        offset = entry
                    offsets.append(offset)
                    
            elif 'unique_rom_offsets' in data:
                # Alternative format from precise script
                for offset_key, info in data['unique_rom_offsets'].items():
                    # Type-safe offset parsing with validation
                    try:
                        if isinstance(offset_key, str):
                            if offset_key.startswith('0x'):
                                offset = int(offset_key, 16)
                            else:
                                offset = int(offset_key, 10)  # Explicit base 10
                        elif isinstance(offset_key, (int, float)):
                            offset = int(offset_key)  # Convert float to int safely
                        else:
                            logger.warning(f"Unknown offset format: {offset_key} (type: {type(offset_key)})")
                            continue
                        
                        # Validate offset is within reasonable ROM range
                        if not (0 <= offset <= 0x800000):  # 8MB max ROM size
                            logger.warning(f"Offset out of range: 0x{offset:X}")
                            continue
                            
                        offsets.append(offset)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to parse offset '{offset_key}': {e}")
                        continue
                    
            # Sort offsets for consistent processing
            offsets.sort()
            self.results["lua_offsets"] = offsets
            
            logger.info(f"Loaded {len(offsets)} ROM offsets from Lua results")
            return offsets
            
        except Exception as e:
            logger.error(f"Failed to load Lua results: {e}")
            return []
            
    def validate_offsets_with_spritepal(self, offsets: List[int]) -> List[Dict[str, Any]]:
        """
        Validate each ROM offset using SpritePal's sprite detection.
        
        Args:
            offsets: List of ROM offsets to validate
            
        Returns:
            List of validation results for each offset
        """
        logger.info(f"Validating {len(offsets)} ROM offsets with SpritePal")
        
        validation_results = []
        
        for i, offset in enumerate(offsets):
            logger.debug(f"Validating offset {i+1}/{len(offsets)}: 0x{offset:06X}")
            
            try:
                # Use SpriteFinder to check if this offset contains valid sprite data
                sprite_info = self.sprite_finder.check_offset_for_sprite(
                    self.rom_path, offset
                )
                
                result = {
                    "offset": offset,
                    "offset_hex": f"0x{offset:06X}",
                    "valid_sprite": sprite_info is not None,
                    "sprite_info": sprite_info,
                    "confidence": sprite_info.get("quality", 0.0) if sprite_info else 0.0,
                    "tile_count": sprite_info.get("tile_count", 0) if sprite_info else 0,
                    "decompressed_size": sprite_info.get("decompressed_size", 0) if sprite_info else 0
                }
                
                if sprite_info:
                    logger.info(f"✓ Valid sprite at 0x{offset:06X}: "
                              f"confidence={result['confidence']:.3f}, "
                              f"tiles={result['tile_count']}")
                else:
                    logger.debug(f"✗ No valid sprite at 0x{offset:06X}")
                    
                validation_results.append(result)
                
            except Exception as e:
                logger.warning(f"Error validating offset 0x{offset:06X}: {e}")
                result = {
                    "offset": offset,
                    "offset_hex": f"0x{offset:06X}",
                    "valid_sprite": False,
                    "error": str(e)
                }
                validation_results.append(result)
                
        self.results["spritepal_validation"] = validation_results
        return validation_results
        
    def analyze_results(self, lua_offsets: List[int], 
                       validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze validation results and identify matches/discrepancies.
        
        Args:
            lua_offsets: Original offsets from Lua script
            validation_results: SpritePal validation results
            
        Returns:
            Analysis summary
        """
        logger.info("Analyzing validation results")
        
        # Categorize results
        valid_sprites = [r for r in validation_results if r["valid_sprite"]]
        invalid_offsets = [r for r in validation_results if not r["valid_sprite"]]
        
        # Calculate statistics
        total_offsets = len(lua_offsets)
        valid_count = len(valid_sprites)
        invalid_count = len(invalid_offsets)
        accuracy_rate = valid_count / total_offsets if total_offsets > 0 else 0.0
        
        # Find high-confidence sprites
        high_confidence = [r for r in valid_sprites if r["confidence"] >= 0.7]
        medium_confidence = [r for r in valid_sprites if 0.4 <= r["confidence"] < 0.7]
        low_confidence = [r for r in valid_sprites if r["confidence"] < 0.4]
        
        summary = {
            "total_lua_offsets": total_offsets,
            "valid_sprites_found": valid_count,
            "invalid_offsets": invalid_count,
            "accuracy_rate": accuracy_rate,
            "high_confidence_sprites": len(high_confidence),
            "medium_confidence_sprites": len(medium_confidence),
            "low_confidence_sprites": len(low_confidence),
            "confidence_breakdown": {
                "high": [r["offset_hex"] for r in high_confidence],
                "medium": [r["offset_hex"] for r in medium_confidence],
                "low": [r["offset_hex"] for r in low_confidence]
            }
        }
        
        self.results["summary"] = summary
        self.results["matches"] = valid_sprites
        self.results["discrepancies"] = invalid_offsets
        
        return summary
        
    def generate_report(self, output_path: Optional[str] = None) -> str:
        """
        Generate a detailed validation report.
        
        Args:
            output_path: Optional path to save report
            
        Returns:
            Report text
        """
        summary = self.results["summary"]
        
        report = f"""
=== Lua Script vs SpritePal Validation Report ===

ROM File: {self.results["rom_file"]}
Analysis Date: {Path(__file__).stat().st_mtime}

SUMMARY STATISTICS:
- Total Lua Offsets: {summary["total_lua_offsets"]}
- Valid Sprites Found: {summary["valid_sprites_found"]}
- Invalid Offsets: {summary["invalid_offsets"]}
- Accuracy Rate: {summary["accuracy_rate"]:.1%}

CONFIDENCE BREAKDOWN:
- High Confidence (≥0.7): {summary["high_confidence_sprites"]} sprites
- Medium Confidence (0.4-0.7): {summary["medium_confidence_sprites"]} sprites  
- Low Confidence (<0.4): {summary["low_confidence_sprites"]} sprites

HIGH CONFIDENCE SPRITES:
"""
        
        for offset_hex in summary["confidence_breakdown"]["high"]:
            match = next(r for r in self.results["matches"] if r["offset_hex"] == offset_hex)
            report += f"  {offset_hex}: confidence={match['confidence']:.3f}, tiles={match['tile_count']}\n"
            
        report += f"\nMEDIUM CONFIDENCE SPRITES:\n"
        for offset_hex in summary["confidence_breakdown"]["medium"]:
            match = next(r for r in self.results["matches"] if r["offset_hex"] == offset_hex)
            report += f"  {offset_hex}: confidence={match['confidence']:.3f}, tiles={match['tile_count']}\n"
            
        report += f"\nINVALID OFFSETS (No valid sprite data found):\n"
        for discrepancy in self.results["discrepancies"][:20]:  # Show first 20
            report += f"  {discrepancy['offset_hex']}\n"
            
        if len(self.results["discrepancies"]) > 20:
            report += f"  ... and {len(self.results['discrepancies']) - 20} more\n"
            
        report += f"""
ANALYSIS:
The Lua script accuracy of {summary["accuracy_rate"]:.1%} indicates:
"""
        
        if summary["accuracy_rate"] >= 0.8:
            report += "- EXCELLENT: Lua script very accurately identifies sprite locations\n"
        elif summary["accuracy_rate"] >= 0.6:
            report += "- GOOD: Lua script identifies most sprite locations correctly\n"
        elif summary["accuracy_rate"] >= 0.4:
            report += "- FAIR: Lua script has moderate accuracy, some false positives\n"
        else:
            report += "- POOR: Lua script has many false positives or detection issues\n"
            
        report += f"- High confidence matches: {summary['high_confidence_sprites']}/{summary['total_lua_offsets']} ({summary['high_confidence_sprites']/summary['total_lua_offsets']:.1%})\n"
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
            logger.info(f"Report saved to: {output_path}")
            
        return report
        
    def save_detailed_results(self, output_path: str) -> None:
        """
        Save detailed JSON results for further analysis.
        
        Args:
            output_path: Path to save JSON results
        """
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Detailed results saved to: {output_path}")


def main():
    """Main validation routine."""
    parser = argparse.ArgumentParser(
        description="Validate ROM offsets from Lua scripts against SpritePal"
    )
    parser.add_argument("--rom", required=True, help="Path to ROM file")
    parser.add_argument("--lua-json", required=True, help="Path to Lua script JSON output")
    parser.add_argument("--output-dir", default="validation_results", help="Output directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Validate inputs
    rom_path = Path(args.rom)
    if not rom_path.exists():
        logger.error(f"ROM file not found: {rom_path}")
        sys.exit(1)
        
    lua_json_path = Path(args.lua_json)
    if not lua_json_path.exists():
        logger.error(f"Lua JSON file not found: {lua_json_path}")
        sys.exit(1)
        
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    logger.info("=== ROM Offset Validation: Lua Script vs SpritePal ===")
    logger.info(f"ROM: {rom_path}")
    logger.info(f"Lua JSON: {lua_json_path}")
    
    # Initialize validator
    validator = LuaSpritePalValidator(str(rom_path))
    
    # Load Lua results
    lua_offsets = validator.load_lua_results(str(lua_json_path))
    if not lua_offsets:
        logger.error("No valid offsets loaded from Lua results")
        sys.exit(1)
        
    # Validate with SpritePal
    validation_results = validator.validate_offsets_with_spritepal(lua_offsets)
    
    # Analyze results
    summary = validator.analyze_results(lua_offsets, validation_results)
    
    # Generate outputs
    report_path = output_dir / f"validation_report_{lua_json_path.stem}.txt"
    results_path = output_dir / f"detailed_results_{lua_json_path.stem}.json"
    
    report = validator.generate_report(str(report_path))
    validator.save_detailed_results(str(results_path))
    
    # Print summary to console
    print("\n" + "="*60)
    print("VALIDATION COMPLETE")
    print("="*60)
    print(f"Total Offsets Tested: {summary['total_lua_offsets']}")
    print(f"Valid Sprites Found: {summary['valid_sprites_found']}")
    print(f"Accuracy Rate: {summary['accuracy_rate']:.1%}")
    print(f"High Confidence: {summary['high_confidence_sprites']} sprites")
    print(f"Report: {report_path}")
    print(f"Details: {results_path}")
    print("="*60)


if __name__ == "__main__":
    main()