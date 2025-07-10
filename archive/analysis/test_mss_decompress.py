#!/usr/bin/env python3
"""Test MSS decompression specifically"""

import zlib

# Read the MSS file
with open("Kirby Super Star (USA)_2.mss", "rb") as f:
    data = f.read()

print(f"File size: {len(data)} bytes")
print(f"Header: {data[:32].hex()}")

# Find zlib header (78 01, 78 9C, 78 DA)
for i in range(len(data) - 1):
    if data[i] == 0x78 and data[i+1] in [0x01, 0x9C, 0xDA]:
        print(f"\nFound zlib header at offset 0x{i:X}: {data[i:i+2].hex()}")

        # Try to decompress from this point
        try:
            decompressed = zlib.decompress(data[i:])
            print(f"  Successfully decompressed! Size: {len(decompressed)} bytes")

            # Save the decompressed data
            with open("mss_decompressed.bin", "wb") as f:
                f.write(decompressed)

            # Look for SNES memory structures
            print("\n  Looking for SNES structures:")

            # Check for VRAM (64KB)
            if len(decompressed) >= 65536:
                print("    Possible VRAM at start (64KB)")

            # Check for WRAM (128KB)
            if len(decompressed) >= 131072:
                print("    Possible WRAM present (128KB)")

            # Examine structure
            print("\n  First 256 bytes of decompressed data:")
            for j in range(0, min(256, len(decompressed)), 16):
                hex_str = " ".join(f"{b:02x}" for b in decompressed[j:j+16])
                ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in decompressed[j:j+16])
                print(f"    {j:04X}: {hex_str:<48} {ascii_str}")

            break

        except Exception as e:
            print(f"  Decompression failed: {e}")
