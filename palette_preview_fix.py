def apply_palette_for_preview(base_image, palette, handle_transparency=True):
    """
    Apply a palette to an indexed image for preview purposes.

    Args:
        base_image: PIL Image in mode 'P'
        palette: List of RGB values (768 values)
        handle_transparency: If True, make index 0 transparent or use neutral color

    Returns:
        PIL Image with palette applied
    """
    if not isinstance(base_image, Image.Image) or base_image.mode != "P":
        raise ValueError("Image must be in indexed color mode")

    if handle_transparency:
        # Option 1: Convert to RGBA with transparency
        base_image.convert("RGBA")
        pixels = np.array(base_image)

        # Create alpha channel - 0 where index is 0, 255 elsewhere
        alpha = np.where(pixels == 0, 0, 255).astype(np.uint8)

        # Apply palette and convert to RGBA
        img_colored = base_image.copy()
        img_colored.putpalette(palette)
        color_array = np.array(img_colored.convert("RGBA"))

        # Set alpha channel
        color_array[:, :, 3] = alpha

        return Image.fromarray(color_array, "RGBA")
    # Option 2: Just apply palette directly
    img_copy = base_image.copy()
    img_copy.putpalette(palette)
    return img_copy
