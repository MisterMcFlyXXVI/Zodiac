"""Find glyph boxes on the cipher line of FBI Part 09 p210 from ink gaps (column projection), not by eye.
Writes candidate boxes; crops.json is written separately after the 13 boxes are checked."""
import sys, json, numpy as np
from PIL import Image
img = np.array(Image.open(sys.argv[1]).convert("L"))
y0, y1, x0, x1 = map(int, sys.argv[2:6])        # band around the cipher line
band = img[y0:y1, x0:x1] < 128                   # ink = dark
cols = band.sum(0)
spans, inside = [], False
for x, v in enumerate(cols):
    if v > 0 and not inside: start, inside = x, True
    if v == 0 and inside: spans.append((start, x)); inside = False
if inside: spans.append((start, len(cols)))
out = []
for a, b in spans:
    rows = np.where(band[:, a:b].any(1))[0]
    out.append([x0 + a, y0 + int(rows.min()), x0 + b, y0 + int(rows.max()) + 1])
print(json.dumps(out)); print(len(out), "spans; widths:", [b[2]-b[0] for b in out])
