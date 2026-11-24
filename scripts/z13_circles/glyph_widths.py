"""Width and height of each glyph on one text line of a scan (ink = pixels darker than a threshold).

Used to compare image resolution: how many pixels wide Z13's circled glyphs are on a given image.
Glyphs are separated by blank columns within the row band, so touching glyphs count as one.

    python scripts/z13_circles/glyph_widths.py Zodiac-name.gif --band 160 205

On the Wikimedia Commons file Zodiac-name.gif (640x829, sha256 13996b1f...ec115; see
results/z13_circles/IMAGES.md) this finds the 13 Z13 glyphs; the circled ones (positions 5, 7, 9) are
21, 20 and 19 px wide. Position 4 (crossed circle with a tail) is 29 px wide.
"""
import argparse
import json

import numpy as np
from PIL import Image


def glyph_boxes(ink):
    """Column runs of ink in a boolean row band -> list of dicts (x0, x1, width, height)."""
    cols = ink.any(axis=0)
    boxes, start = [], None
    for x, on in enumerate(list(cols) + [False]):
        if on and start is None:
            start = x
        elif not on and start is not None:
            rows = np.where(ink[:, start:x].any(axis=1))[0]
            boxes.append({"x0": start, "x1": x - 1, "width": x - start,
                          "height": int(rows.max() - rows.min() + 1)})
            start = None
    return boxes


def measure(path, y0, y1, threshold=128):
    gray = np.asarray(Image.open(path).convert("L"))
    return glyph_boxes(gray[y0:y1] < threshold)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("image")
    ap.add_argument("--band", nargs=2, type=int, required=True, metavar=("Y0", "Y1"),
                    help="row band holding the cipher line (Y1 exclusive)")
    ap.add_argument("--threshold", type=int, default=128)
    args = ap.parse_args()
    boxes = measure(args.image, args.band[0], args.band[1], args.threshold)
    for i, b in enumerate(boxes, 1):
        b["position"] = i
    print(json.dumps(boxes, indent=1))


if __name__ == "__main__":
    main()
