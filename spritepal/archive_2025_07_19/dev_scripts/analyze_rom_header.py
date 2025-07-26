#!/usr/bin/env python3
"""Analyze ROM header to debug recognition issues."""

import os
import struct


def analyze_rom_header(rom_path):
    """Analyze ROM header at both possible offsets."""

    if not os.path.exists(rom_path):
        print(f"Error: ROM file not found at {rom_path}")
        return

    with open(rom_path, "rb") as f:
        # Get file size
        f.seek(0, 2)  # Seek to end
        file_size = f.tell()
        f.seek(0)  # Back to start

        # Check for SMC header
        has_smc_header = (file_size % 1024) == 512
        print(f"\nFile size: {file_size} bytes")
        print(f"SMC header present: {has_smc_header}")

        if has_smc_header:
            print("File appears to have a 512-byte SMC header")

        # Try both header offsets
        offsets = [0x7FC0, 0xFFC0]

        for offset in offsets:
            print(f"\n{'='*60}")
            print(f"Reading header at offset 0x{offset:04X}")

            try:
                # Seek to header offset
                f.seek(offset)
                header_data = f.read(32)

                if len(header_data) < 32:
                    print(f"Not enough data at offset 0x{offset:04X}")
                    continue

                # Extract title (bytes 0-21)
                title_bytes = header_data[0:21]
                title_str = title_bytes.decode("ascii", errors="replace")

                print("\nTitle (21 bytes):")
                print(f"  Raw bytes: {title_bytes.hex()}")
                print(f"  Decoded: '{title_str}'")
                print(f"  Stripped: '{title_str.strip()}'")

                # Also show individual bytes for debugging
                print("  Byte-by-byte:")
                for i, b in enumerate(title_bytes):
                    char = chr(b) if 32 <= b <= 126 else "."
                    print(f"    [{i:2d}] 0x{b:02X} ({b:3d}) '{char}'")

                # Extract checksum (bytes 30-31, little-endian 16-bit)
                if len(header_data) >= 32:
                    checksum = struct.unpack("<H", header_data[30:32])[0]
                    print("\nChecksum:")
                    print(f"  Offset 30-31: 0x{checksum:04X}")

                    # Also try complement checksum at bytes 28-29
                    complement = struct.unpack("<H", header_data[28:30])[0]
                    print(f"  Complement (28-29): 0x{complement:04X}")

                    # Verify checksum + complement = 0xFFFF
                    if (checksum + complement) & 0xFFFF == 0xFFFF:
                        print("  Checksum verified (sum = 0xFFFF)")
                    else:
                        print(
                            f"  Warning: Checksum + complement = 0x{(checksum + complement) & 0xFFFF:04X}"
                        )

            except Exception as e:
                print(f"Error reading at offset 0x{offset:04X}: {e}")

        # If SMC header is present, also try reading with 512-byte offset
        if has_smc_header:
            print(f"\n{'='*60}")
            print("Trying offsets with SMC header adjustment (+512 bytes):")

            for offset in offsets:
                adjusted_offset = offset + 512
                print(f"\nReading at adjusted offset 0x{adjusted_offset:04X}")

                try:
                    f.seek(adjusted_offset)
                    header_data = f.read(32)

                    if len(header_data) < 32:
                        print(f"Not enough data at offset 0x{adjusted_offset:04X}")
                        continue

                    # Extract title
                    title_bytes = header_data[0:21]
                    title_str = title_bytes.decode("ascii", errors="replace")

                    print(f"  Title: '{title_str.strip()}'")

                    # Extract checksum
                    if len(header_data) >= 32:
                        checksum = struct.unpack("<H", header_data[30:32])[0]
                        print(f"  Checksum: 0x{checksum:04X}")

                except Exception as e:
                    print(f"Error reading at adjusted offset: {e}")

    print(f"\n{'='*60}")
    print("\nExpected values from sprite_locations.json:")
    print("  Title: 'KIRBY SUPER STAR'")
    print("  Checksum: 0x8A5C")


if __name__ == "__main__":
    rom_path = "Kirby Super Star (USA).sfc"
    print(f"Analyzing ROM: {rom_path}")
    analyze_rom_header(rom_path)
