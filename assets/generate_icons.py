"""
Generate PNG and ICO icon assets from ravnapp.jpeg.
Run once: python assets/generate_icons.py
"""

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parent.parent
OUT  = Path(__file__).parent
SRC  = OUT / "ravnapp.jpeg"


def tight_crop(img: Image.Image, padding: float = 0.08) -> Image.Image:
    """
    Crop tightly around non-background content using only Pillow.
    Samples the four corners to detect background color, converts to
    grayscale difference map, then finds the bounding box of foreground.
    """
    from PIL import ImageChops, ImageFilter

    rgba = img.convert("RGBA")
    w, h = rgba.size

    # Sample background from corners (average the 4 corner pixel values)
    corners = [
        rgba.getpixel((0, 0)),
        rgba.getpixel((w - 1, 0)),
        rgba.getpixel((0, h - 1)),
        rgba.getpixel((w - 1, h - 1)),
    ]
    bg_r = int(sum(c[0] for c in corners) / 4)
    bg_g = int(sum(c[1] for c in corners) / 4)
    bg_b = int(sum(c[2] for c in corners) / 4)

    # Create a solid background-color image and diff against original
    bg_img = Image.new("RGBA", (w, h), (bg_r, bg_g, bg_b, 255))
    diff = ImageChops.difference(rgba.convert("RGB"), bg_img.convert("RGB"))

    # Convert diff to grayscale and threshold to get content mask
    gray = diff.convert("L")
    threshold = gray.point(lambda p: 255 if p > 25 else 0)
    # Dilate slightly to connect nearby content
    threshold = threshold.filter(ImageFilter.MaxFilter(size=5))

    bbox = threshold.getbbox()
    if bbox is None:
        # Fallback: simple square center-crop
        side = min(w, h)
        return img.crop(((w - side) // 2, (h - side) // 2,
                          (w + side) // 2, (h + side) // 2))

    left, top, right, bottom = bbox
    cw = right - left
    ch = bottom - top

    # Add padding proportional to content size
    pad_x = int(cw * padding)
    pad_y = int(ch * padding)
    left   = max(0, left   - pad_x)
    top    = max(0, top    - pad_y)
    right  = min(w, right  + pad_x)
    bottom = min(h, bottom + pad_y)

    cropped = img.crop((left, top, right, bottom))

    # Square-pad the shorter dimension with background color
    cw, ch = cropped.size
    side = max(cw, ch)
    result = Image.new("RGBA", (side, side), (bg_r, bg_g, bg_b, 255))
    result.paste(cropped, ((side - cw) // 2, (side - ch) // 2))
    return result


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(f"Source not found: {SRC}")

    img = Image.open(SRC).convert("RGBA")
    img = tight_crop(img, padding=0.08)  # sıkı kırp, içerik ekrana dolsun

    # --- PNG variants ---
    for size in (256, 128, 64, 32, 16):
        resized = img.resize((size, size), Image.LANCZOS)
        dest = OUT / f"ravn-icon-{size}.png"
        resized.save(dest, "PNG")
        print(f"Saved {dest}")

    # --- ICO (multi-size, Windows title bar + taskbar) ---
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_images = [img.resize(s, Image.LANCZOS) for s in ico_sizes]
    ico_path = OUT / "ravn.ico"
    ico_images[0].save(
        ico_path,
        format="ICO",
        sizes=ico_sizes,
        append_images=ico_images[1:],
    )
    print(f"Saved {ico_path}")

    print("Done.")


if __name__ == "__main__":
    main()
