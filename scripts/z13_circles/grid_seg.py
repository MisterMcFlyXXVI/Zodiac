"""Grid segmentation for the I1b look-alike check (cut-point search near equal pitch)."""
import numpy as np
from PIL import Image

def cuts(proj, lo, hi, n, win_frac=0.35):
    """n+1 boundaries: lo, n-1 interior cuts at projection minima near equal spacing, hi."""
    p = (hi - lo) / n
    out = [lo]
    for k in range(1, n):
        c = lo + k * p
        a, b = int(c - win_frac * p), int(c + win_frac * p) + 1
        w = proj[a:b]
        # smallest value; ties -> closest to centre
        idx = np.flatnonzero(w == w.min())
        j = idx[np.argmin(np.abs(idx + a - c))] + a
        out.append(j)
    out.append(hi)
    return out

def clean_bbox(m, min_area=12):
    """bbox of ink components with >= min_area pixels (4-connected, iterative flood)."""
    h, w = m.shape
    lab = np.zeros((h, w), int); n = 0; keep = np.zeros((h, w), bool)
    for y, x in zip(*np.nonzero(m)):
        if lab[y, x]: continue
        n += 1; st = [(y, x)]; lab[y, x] = n; pts = []
        while st:
            cy, cx = st.pop(); pts.append((cy, cx))
            for dy, dx in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                ny, nx = cy+dy, cx+dx
                if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and not lab[ny, nx]:
                    lab[ny, nx] = n; st.append((ny, nx))
        if len(pts) >= min_area:
            for q in pts: keep[q] = True
    if not keep.any(): return None
    ys, xs = np.nonzero(keep)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1

def segment(mask, roi, nrows, ncols):
    """roi=(x0,y0,x1,y1) generous box around grid. Returns list of rows of boxes (x0,y0,x1,y1) in page px."""
    x0, y0, x1, y1 = roi
    sub = mask[y0:y1, x0:x1]
    ys, xs = np.nonzero(sub)
    # tight extent from robust percentiles of ink projections
    rp = sub.sum(1); cp = sub.sum(0)
    ry = np.flatnonzero(rp >= 3); cx = np.flatnonzero(cp >= 2)
    Y0, Y1, X0, X1 = ry.min(), ry.max() + 1, cx.min(), cx.max() + 1
    rc = cuts(rp, Y0, Y1, nrows)
    grid = []
    for r in range(nrows):
        a, b = rc[r], rc[r + 1]
        cp2 = sub[a:b].sum(0)
        cc = cuts(cp2, X0, X1, ncols)
        row = []
        for c in range(ncols):
            cell = sub[a:b, cc[c]:cc[c + 1]]
            bb = clean_bbox(cell)
            if bb is None: row.append(None); continue
            row.append([x0 + cc[c] + bb[0], y0 + a + bb[1], x0 + cc[c] + bb[2], y0 + a + bb[3]])
        grid.append(row)
    return grid, (X0 + x0, Y0 + y0, X1 + x0, Y1 + y0)
