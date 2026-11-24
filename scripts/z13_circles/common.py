"""Shared paths, sealed-hash check and page-argument helpers for the Z13 circles run scripts."""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CIPHER_DIR = os.path.join(ROOT, "data", "ciphers") + os.sep
RESULTS = os.path.join(ROOT, "results", "z13_circles")
PAGE_FLAGS = ("p171", "p176", "p180", "p196")   # FBI Vault Part 09 pages (Z408 x3, Z340), 150 ppi renders

if HERE not in sys.path:
    sys.path.insert(0, HERE)


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def sealed():
    """{file name: sha256} from SEALED.sha256 (the hashes pre-registered on the fork before any real image)."""
    with open(os.path.join(HERE, "SEALED.sha256")) as fh:
        return {line.split()[1]: line.split()[0] for line in fh if line.strip()}


def check_sealed(*names):
    want = sealed()
    for n in names:
        got = sha256(os.path.join(HERE, n))
        assert got == want[n], "%s differs from its sealed hash (%s != %s)" % (n, got, want[n])


def add_page_args(ap):
    for f in PAGE_FLAGS:
        ap.add_argument("--" + f, required=True, help="PNG of FBI Part 09 page %s at 150 ppi (pdftoppm -r 150)" % f[1:])


def page_map(args):
    """{'P09-171': path, ...} in the names the run scripts use."""
    return {"P09-" + f[1:]: getattr(args, f) for f in PAGE_FLAGS}
