#!/usr/bin/env python3
"""
ROM Offset Mismatch Diagnostic Tool

This script helps diagnose why ROM offsets from Lua scripts don't match
SpritePal's manual offset slider results. It tests the most common causes:

1. SMC header offset issues (+512 bytes)
2. Coordinate system mismatches (CPU vs ROM file addressing)
3. Banking calculation differences
4. HAL compression alignment issues

Usage:
    python diagnose_offset_mismatch.py --rom ROM_FILE --lua-offset 0x240000
"""

import argparse
import sys
from pathlib import Path

from core.sprite_finder import SpriteFinder
from utils.logging_config import get_logger

logger = get_logger(__name__)


class OffsetMismatchDiagnostic:
    """Diagnoses ROM offset mismatches between Lua scripts and SpritePal."""
    
    def __init__(self, rom_path: str):
        self.rom_path = rom_path
        self.sprite_finder = SpriteFinder()
        
        # Get ROM file info
        self.rom_file = Path(rom_path)
        if not self.rom_file.exists():
            raise FileNotFoundError(f"ROM file not found: {rom_path}")
            
        self.rom_size = self.rom_file.stat().st_size
        self.has_smc_header = self._detect_smc_header()
        
    def _detect_smc_header(self) -> bool:
        """Detect if ROM file has SMC header (512 bytes)."""
        # SMC files have size that is 512 bytes more than power-of-2
        return (self.rom_size % 1024) == 512
        
    def diagnose_lua_offset(self, lua_offset: int) -> dict:
        """
        Comprehensive diagnosis of why a Lua-reported offset might not work.
        
        Args:
            lua_offset: ROM offset reported by Lua script
            
        Returns:
            Diagnostic results with recommendations
        """
        print(f"\n=== ROM OFFSET DIAGNOSTIC ===")
        print(f"ROM File: {self.rom_path}")
        print(f"ROM Size: {self.rom_size:,} bytes (0x{self.rom_size:X})")
        print(f"SMC Header: {'YES' if self.has_smc_header else 'NO'}")
        print(f"Lua Offset: 0x{lua_offset:06X}")
        
        results = {
            "rom_info": {
                "path": self.rom_path,
                "size": self.rom_size,
                "has_smc_header": self.has_smc_header
            },
            "lua_offset": lua_offset,
            "tests": {}
        }
        
        # Test 1: Exact offset as reported by Lua
        print(f"\n--- Test 1: Direct Lua Offset ---")
        exact_result = self._test_offset(lua_offset, "Direct Lua offset")
        results["tests"]["direct"] = exact_result
        
        # Test 2: Offset adjusted for SMC header
        if self.has_smc_header:
            adjusted_offset = lua_offset + 512
            print(f"\n--- Test 2: SMC Header Adjusted (+512 bytes) ---")
            adjusted_result = self._test_offset(adjusted_offset, "SMC header adjusted")
            results["tests"]["smc_adjusted"] = adjusted_result
        else:
            print(f"\n--- Test 2: SMC Header Adjustment (Skipped - No Header) ---")
            results["tests"]["smc_adjusted"] = None
            
        # Test 3: Test nearby offsets (alignment issues)
        print(f"\n--- Test 3: Nearby Alignment Offsets ---")
        alignment_results = self._test_alignment_offsets(lua_offset)
        results["tests"]["alignment"] = alignment_results
        
        # Test 4: Banking recalculation test
        print(f"\n--- Test 4: Banking Recalculation ---")
        banking_results = self._test_banking_variants(lua_offset)
        results["tests"]["banking"] = banking_results
        
        # Generate recommendations
        recommendations = self._generate_recommendations(results)
        results["recommendations"] = recommendations
        
        self._print_summary(results)
        return results
        
    def _test_offset(self, offset: int, description: str) -> dict:
        """Test if a specific offset contains valid sprite data."""
        try:
            sprite_info = self.sprite_finder.check_offset_for_sprite(self.rom_path, offset)
            
            if sprite_info:
                confidence = sprite_info.get("quality", 0.0)
                tile_count = sprite_info.get("tile_count", 0)
                print(f"✓ FOUND SPRITE at 0x{offset:06X}: confidence={confidence:.3f}, tiles={tile_count}")
                
                return {
                    "offset": offset,
                    "found_sprite": True,
                    "confidence": confidence,
                    "tile_count": tile_count,
                    "description": description
                }
            else:
                print(f"✗ No sprite at 0x{offset:06X}")
                return {
                    "offset": offset,
                    "found_sprite": False,
                    "description": description
                }
                
        except Exception as e:
            print(f"✗ Error testing 0x{offset:06X}: {e}")
            return {
                "offset": offset,
                "found_sprite": False,
                "error": str(e),
                "description": description
            }
            
    def _test_alignment_offsets(self, base_offset: int) -> list:
        """Test common alignment boundaries around the base offset."""
        alignments = [0x10, 0x20, 0x40, 0x80, 0x100, 0x200]
        results = []
        
        for alignment in alignments:
            # Test aligned down
            aligned_offset = (base_offset // alignment) * alignment
            if aligned_offset != base_offset:
                result = self._test_offset(aligned_offset, f"Aligned to 0x{alignment:X} boundary")
                if result["found_sprite"]:
                    results.append(result)
                    
            # Test aligned up  
            aligned_offset = ((base_offset + alignment - 1) // alignment) * alignment
            if aligned_offset != base_offset and aligned_offset - base_offset <= alignment:
                result = self._test_offset(aligned_offset, f"Aligned up to 0x{alignment:X} boundary")
                if result["found_sprite"]:
                    results.append(result)
                    
        return results
        
    def _test_banking_variants(self, lua_offset: int) -> list:
        """Test different banking calculation variants."""
        results = []
        
        # Common banking base differences
        banking_variants = [
            ("LoROM variant", -0x8000),
            ("HiROM variant", 0x8000),
            ("Alternative banking", 0x10000),
        ]
        
        for variant_name, adjustment in banking_variants:
            adjusted_offset = lua_offset + adjustment
            if 0 <= adjusted_offset < self.rom_size:
                result = self._test_offset(adjusted_offset, variant_name)
                if result["found_sprite"]:
                    results.append(result)
                    
        return results
        
    def _generate_recommendations(self, results: dict) -> list:
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Check if direct offset worked
        if results["tests"]["direct"]["found_sprite"]:
            recommendations.append({
                "priority": "HIGH",
                "issue": "Lua offset works correctly",
                "action": "No adjustment needed - check SpritePal configuration",
                "confidence": results["tests"]["direct"]["confidence"]
            })
            return recommendations
            
        # Check if SMC adjustment worked
        if results["tests"]["smc_adjusted"] and results["tests"]["smc_adjusted"]["found_sprite"]:
            recommendations.append({
                "priority": "HIGH", 
                "issue": "SMC header offset mismatch",
                "action": "Add 512 bytes (0x200) to all Lua offsets, or fix Lua script to detect SMC headers",
                "confidence": results["tests"]["smc_adjusted"]["confidence"]
            })
            
        # Check alignment results
        alignment_found = [r for r in results["tests"]["alignment"] if r["found_sprite"]]
        if alignment_found:
            best_alignment = max(alignment_found, key=lambda x: x.get("confidence", 0))
            offset_diff = best_alignment["offset"] - results["lua_offset"]
            recommendations.append({
                "priority": "MEDIUM",
                "issue": f"Offset alignment issue (difference: {offset_diff:+d} bytes)",
                "action": f"Use aligned offset 0x{best_alignment['offset']:06X} instead of 0x{results['lua_offset']:06X}",
                "confidence": best_alignment["confidence"]
            })
            
        # Check banking results
        banking_found = [r for r in results["tests"]["banking"] if r["found_sprite"]]
        if banking_found:
            best_banking = max(banking_found, key=lambda x: x.get("confidence", 0))
            recommendations.append({
                "priority": "MEDIUM",
                "issue": "Banking calculation mismatch",
                "action": f"Review banking calculation - try offset 0x{best_banking['offset']:06X}",
                "confidence": best_banking["confidence"]
            })
            
        # If no solutions found
        if not recommendations:
            recommendations.append({
                "priority": "HIGH",
                "issue": "No valid sprite found at any tested offset",
                "action": "Verify Lua script is correctly capturing ROM offsets, or ROM uses different compression format",
                "confidence": 0.0
            })
            
        return recommendations
        
    def _print_summary(self, results: dict):
        """Print diagnostic summary with recommendations."""
        print(f"\n{'='*50}")
        print("DIAGNOSTIC SUMMARY")
        print(f"{'='*50}")
        
        print(f"\nRECOMMENDations:")
        for i, rec in enumerate(results["recommendations"], 1):
            print(f"{i}. [{rec['priority']}] {rec['issue']}")
            print(f"   Action: {rec['action']}")
            if rec['confidence'] > 0:
                print(f"   Confidence: {rec['confidence']:.3f}")
            print()
            
    def batch_test_lua_offsets(self, offsets: list[int]) -> dict:
        """Test multiple Lua offsets and identify patterns."""
        print(f"\n=== BATCH OFFSET TESTING ===")
        print(f"Testing {len(offsets)} offsets...")
        
        results = {
            "total_offsets": len(offsets),
            "direct_matches": 0,
            "smc_adjusted_matches": 0,
            "alignment_matches": 0,
            "no_matches": 0,
            "details": []
        }
        
        for offset in offsets:
            offset_results = self.diagnose_lua_offset(offset)
            
            if offset_results["tests"]["direct"]["found_sprite"]:
                results["direct_matches"] += 1
            elif (offset_results["tests"]["smc_adjusted"] and 
                  offset_results["tests"]["smc_adjusted"]["found_sprite"]):
                results["smc_adjusted_matches"] += 1
            elif offset_results["tests"]["alignment"]:
                results["alignment_matches"] += 1
            else:
                results["no_matches"] += 1
                
            results["details"].append(offset_results)
            
        self._print_batch_summary(results)
        return results
        
    def _print_batch_summary(self, results: dict):
        """Print batch testing summary."""
        total = results["total_offsets"]
        print(f"\n{'='*50}")
        print("BATCH TEST SUMMARY")
        print(f"{'='*50}")
        print(f"Total offsets tested: {total}")
        print(f"Direct matches: {results['direct_matches']} ({results['direct_matches']/total:.1%})")
        print(f"SMC adjusted matches: {results['smc_adjusted_matches']} ({results['smc_adjusted_matches']/total:.1%})")
        print(f"Alignment matches: {results['alignment_matches']} ({results['alignment_matches']/total:.1%})")
        print(f"No matches: {results['no_matches']} ({results['no_matches']/total:.1%})")
        
        if results["smc_adjusted_matches"] > results["direct_matches"]:
            print(f"\n🎯 CONCLUSION: SMC header issue detected!")
            print(f"   Add 512 bytes (0x200) to Lua offsets for this ROM.")
        elif results["direct_matches"] > 0:
            print(f"\n✅ CONCLUSION: Lua offsets work correctly.")
        else:
            print(f"\n⚠️  CONCLUSION: Systematic issue detected - needs investigation.")


def main():
    """Main diagnostic routine."""
    parser = argparse.ArgumentParser(description="Diagnose ROM offset mismatches")
    parser.add_argument("--rom", required=True, help="Path to ROM file")
    parser.add_argument("--lua-offset", type=lambda x: int(x, 0), 
                       help="Single offset from Lua script (hex or decimal)")
    parser.add_argument("--lua-offsets", nargs="+", type=lambda x: int(x, 0),
                       help="Multiple offsets from Lua script")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        
    try:
        diagnostic = OffsetMismatchDiagnostic(args.rom)
        
        if args.lua_offset:
            diagnostic.diagnose_lua_offset(args.lua_offset)
        elif args.lua_offsets:
            diagnostic.batch_test_lua_offsets(args.lua_offsets)
        else:
            print("Please specify either --lua-offset or --lua-offsets")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Diagnostic failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()