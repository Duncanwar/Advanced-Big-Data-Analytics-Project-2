#!/usr/bin/env bash
# Build the report from report/report.md:
set -euo pipefail
cd "$(dirname "$0")"
OUT=Project2_Report
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
pandoc report.md -o "$OUT.docx" --resource-path=. --toc --toc-depth=2 --reference-doc=reference.docx
pandoc report.md -s --self-contained --resource-path=. --css print.css --toc --toc-depth=2 \
  --metadata pagetitle="Project 2 Report" -o report.html
"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$PWD/$OUT.pdf" "file://$PWD/report.html" 2>/dev/null
ls -la "$OUT.docx" "$OUT.pdf"
