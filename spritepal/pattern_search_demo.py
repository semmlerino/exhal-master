#!/usr/bin/env python3
"""
Pattern Search Demo for SpritePal Advanced Search Dialog

This script demonstrates the pattern search functionality implemented
in the AdvancedSearchDialog, showing various search patterns and operations.
"""

def demo_hex_patterns():
    """Examples of hex patterns that can be searched."""
    patterns = [
        # Basic hex patterns
        "00 01 02 FF",           # Exact bytes
        "10 ?? ?? 30",           # Wildcards
        "FF 00 ?? ?? ?? 00 FF",  # Mixed exact and wildcards

        # SNES specific patterns
        "78 DA",                 # zlib compression header
        "1F 8B",                 # gzip header
        "50 4B",                 # ZIP file header

        # Sprite-related patterns
        "20 ?? ?? 20",           # Possible sprite dimensions
        "10 ?? 10 ??",           # Common tile arrangements
    ]

    print("Hex Pattern Examples:")
    for pattern in patterns:
        print(f"  • {pattern}")
    print()

def demo_regex_patterns():
    """Examples of regex patterns for ROM analysis."""
    patterns = [
        # Text patterns
        r"SNES",                    # Find "SNES" text
        r"[A-Z]{4,}",              # 4+ uppercase letters
        r"Nintendo",                # Company name

        # Binary patterns
        r"\x00\x01.{2}\xFF",       # Bytes with gap
        r"[\x20-\x7F]{4,}",        # Printable ASCII strings
        r"\x78\xDA.{10,}",         # zlib compressed data

        # Complex patterns
        r"(\x00{4,}|\xFF{4,})",    # Long runs of 0x00 or 0xFF
        r"\x10\x20.{0,5}\x30\x40", # Pattern with variable gap
    ]

    print("Regex Pattern Examples:")
    for pattern in patterns:
        print(f"  • {pattern}")
    print()

def demo_multiple_patterns():
    """Examples of multiple pattern operations."""

    print("Multiple Pattern Operations:")
    print("  OR Operation (find any pattern):")
    print("    FF 00 FF 00")
    print("    00 FF 00 FF")
    print("    → Finds locations with either pattern")
    print()

    print("  AND Operation (find all patterns nearby):")
    print("    78 DA")      # zlib header
    print("    ?? ?? 00 ??") # followed by some pattern
    print("    → Finds locations where both patterns exist within 256 bytes")
    print()

def demo_search_options():
    """Demonstrate search options and their effects."""

    print("Search Options:")
    print("  • Case Sensitive: For regex patterns only")
    print("  • Alignment Required: Forces matches at 16-byte boundaries")
    print("  • Context Size: Number of bytes to show around matches (0-256)")
    print("  • Max Results: Limit number of matches (1-10000)")
    print("  • Multiple Patterns: OR/AND operations for multiple patterns")
    print()

def demo_performance_features():
    """Show performance optimization features."""

    print("Performance Features:")
    print("  • Memory-mapped file I/O for large ROMs")
    print("  • Chunked processing with progress updates")
    print("  • Early termination on cancellation")
    print("  • Efficient pattern matching algorithms")
    print("  • Context data compression for results")
    print()

def demo_use_cases():
    """Real-world use cases for pattern search."""

    print("Use Cases:")
    print("  1. Finding compressed sprite data:")
    print("     Hex: 78 DA ?? ?? (zlib header)")
    print()
    print("  2. Locating text strings:")
    print("     Regex: [A-Za-z ]{8,} (readable text)")
    print()
    print("  3. Finding sprite headers:")
    print("     Hex: 20 20 ?? ?? (32x32 sprite dimensions)")
    print()
    print("  4. Locating palettes:")
    print("     Hex: ?? ?? 00 7C (common SNES palette pattern)")
    print()
    print("  5. Finding multiple related patterns:")
    print("     AND Operation:")
    print("       78 DA     (compression header)")
    print("       ?? ?? 20  (size marker)")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("SpritePal Pattern Search Demonstration")
    print("=" * 60)
    print()

    demo_hex_patterns()
    demo_regex_patterns()
    demo_multiple_patterns()
    demo_search_options()
    demo_performance_features()
    demo_use_cases()

    print("=" * 60)
    print("To use pattern search:")
    print("1. Open SpritePal")
    print("2. Go to Tools > Advanced Search")
    print("3. Select the 'Pattern Search' tab")
    print("4. Choose Hex or Regex pattern type")
    print("5. Enter your pattern(s)")
    print("6. Configure options as needed")
    print("7. Click 'Search'")
    print("=" * 60)
