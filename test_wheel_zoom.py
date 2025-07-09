#!/usr/bin/env python3
"""
Test script for mouse wheel zoom functionality
This helps verify both zoom directions work correctly
"""

def test_zoom_logic():
    """Test the zoom level logic without GUI"""
    print("Testing zoom level progression logic...")

    zoom_levels = [1, 2, 4, 8, 16, 32, 64]

    def get_next_zoom(current_zoom, zoom_in=True):
        """Simulate the zoom logic from the wheelEvent"""
        # Find current zoom level index
        current_index = 0
        for i, level in enumerate(zoom_levels):
            if level <= current_zoom:
                current_index = i
            else:
                break

        # Calculate new zoom level
        if zoom_in:
            # Zoom in - move to next higher level
            new_index = min(current_index + 1, len(zoom_levels) - 1)
        else:
            # Zoom out - move to next lower level
            new_index = max(current_index - 1, 0)

        return zoom_levels[new_index]

    # Test zoom in progression
    print("\n=== Testing Zoom IN (wheel up) ===")
    current = 1
    for _i in range(8):
        next_zoom = get_next_zoom(current, zoom_in=True)
        print(f"  {current}x -> {next_zoom}x")
        if next_zoom == current:
            print(f"  (Reached maximum at {current}x)")
            break
        current = next_zoom

    # Test zoom out progression
    print("\n=== Testing Zoom OUT (wheel down) ===")
    current = 64
    for _i in range(8):
        next_zoom = get_next_zoom(current, zoom_in=False)
        print(f"  {current}x -> {next_zoom}x")
        if next_zoom == current:
            print(f"  (Reached minimum at {current}x)")
            break
        current = next_zoom

    # Test from middle values
    print("\n=== Testing from middle values ===")
    test_values = [1, 2, 4, 8, 16, 32, 64]
    for val in test_values:
        zoom_in = get_next_zoom(val, zoom_in=True)
        zoom_out = get_next_zoom(val, zoom_in=False)
        print(f"  From {val}x: IN -> {zoom_in}x, OUT -> {zoom_out}x")

def simulate_wheel_events():
    """Simulate a series of wheel events"""
    print("\n=== Simulating Wheel Events ===")

    # Simulate starting at 4x (default)
    current_zoom = 4
    events = [
        (120, "Wheel UP (zoom in)"),
        (120, "Wheel UP (zoom in)"),
        (120, "Wheel UP (zoom in)"),
        (-120, "Wheel DOWN (zoom out)"),
        (-120, "Wheel DOWN (zoom out)"),
        (-120, "Wheel DOWN (zoom out)"),
        (-120, "Wheel DOWN (zoom out)"),
        (-120, "Wheel DOWN (zoom out)"),
    ]

    zoom_levels = [1, 2, 4, 8, 16, 32, 64]

    for delta, description in events:
        # Find current index
        current_index = 0
        for i, level in enumerate(zoom_levels):
            if level <= current_zoom:
                current_index = i
            else:
                break

        # Calculate new zoom
        if delta > 0:
            new_index = min(current_index + 1, len(zoom_levels) - 1)
        else:
            new_index = max(current_index - 1, 0)

        new_zoom = zoom_levels[new_index]

        print(f"  {description}: {current_zoom}x -> {new_zoom}x (delta: {delta})")
        current_zoom = new_zoom

if __name__ == "__main__":
    print("=== Mouse Wheel Zoom Logic Test ===")
    test_zoom_logic()
    simulate_wheel_events()
    print("\n✓ If you see smooth progressions in both directions, the logic is working!")
    print("✓ Load kirby_visual_friendly_ultrathink.png in the editor to test with real mouse wheel.")
