#!/usr/bin/env python3
"""Extract VRAM data from MSS savestates to find sprite patterns."""

import zlib
from pathlib import Path


def extract_vram_from_mss(mss_path: str) -> bytes:
    """Extract VRAM data from MSS savestate file."""
    print(f"Reading MSS file: {mss_path}")

    mss_path_obj = Path(mss_path)
    with mss_path_obj.open("rb") as f:
        data = f.read()

    # Verify MSS signature
    if data[:3] != b"MSS":
        print("Error: Not a valid MSS savestate file")
        return b""

    # Decompress data (starts at offset 0x23)
    try:
        decompressed = zlib.decompress(data[0x23:])
        print(f"Decompressed size: {len(decompressed)} bytes")
    except Exception as e:
        print(f"Failed to decompress: {e}")
        return b""

    # Extract VRAM (64KB at offset 0x00000)
    vram_offset = 0x00000
    vram_size = 0x10000  # 64KB

    if len(decompressed) < vram_offset + vram_size:
        print("Warning: Decompressed data too small for VRAM extraction")
        return b""

    vram_data = decompressed[vram_offset:vram_offset + vram_size]
    print(f"Extracted VRAM: {len(vram_data)} bytes")

    return vram_data

def analyze_sprite_area(vram_data: bytes):
    """Analyze sprite area in VRAM."""
    # Sprites are typically at 0x4000 or 0x6000 in VRAM
    sprite_offsets = [0x4000, 0x6000, 0x8000, 0xC000]

    for offset in sprite_offsets:
        print(f"\nAnalyzing VRAM offset 0x{offset:04X}:")

        # Extract a sample of sprite data
        sample_size = 0x100  # 256 bytes
        if offset + sample_size <= len(vram_data):
            sprite_sample = vram_data[offset:offset + sample_size]

            # Check for non-zero data
            non_zero_bytes = sum(1 for b in sprite_sample if b != 0)
            print(f"  Non-zero bytes: {non_zero_bytes}/{sample_size}")

            # Show first 32 bytes as hex
            print(f"  First 32 bytes: {sprite_sample[:32].hex()}")

def save_vram_dump(vram_data: bytes, output_path: str):
    """Save VRAM data to file."""
    output_path_obj = Path(output_path)
    with output_path_obj.open("wb") as f:
        f.write(vram_data)
    print(f"\nSaved VRAM dump to: {output_path}")

def main():
    # Find MSS files
    mss_files = list(Path("..").glob("*.mss"))

    if not mss_files:
        print("No MSS files found in parent directory")
        return

    for mss_file in mss_files:
        print(f"\n{'='*60}")
        print(f"Processing: {mss_file.name}")
        print("="*60)

        vram_data = extract_vram_from_mss(str(mss_file))

        if vram_data:
            # Analyze sprite areas
            analyze_sprite_area(vram_data)

            # Save VRAM dump
            output_name = f"vram_{mss_file.stem}_VRAM.dmp"
            save_vram_dump(vram_data, output_name)

            # Extract specific sprite regions for analysis
            for offset in [0x4000, 0x6000, 0x8000, 0xC000]:
                if offset + 0x2000 <= len(vram_data):
                    region_data = vram_data[offset:offset + 0x2000]
                    region_name = f"vram_{mss_file.stem}_VRAM.dmp_{offset:04X}.bin"
                    region_path = Path(region_name)
                    with region_path.open("wb") as f:
                        f.write(region_data)
                    print(f"Saved sprite region 0x{offset:04X} to {region_name}")

if __name__ == "__main__":
    main()
