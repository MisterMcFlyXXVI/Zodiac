#!/bin/bash
# usage: fbi_ocr_page.sh PDF PAGE  -> OCR text of one page on stdout (150 dpi, tesseract).
# Nothing is written to disk except a temp image, which is deleted. The text is never stored by
# the pipeline: scripts/fbi_file_index.py keeps only page tags.
set -e
pdf=$1; p=$2
t=$(mktemp -d)
trap 'rm -rf "$t"' EXIT
pdftoppm -r 150 -gray -f "$p" -l "$p" -png -singlefile "$pdf" "$t/pg"
OMP_THREAD_LIMIT=1 tesseract "$t/pg.png" stdout --psm 3 2>/dev/null
