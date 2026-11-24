"""Create deliberately defective technical-QC artifacts for preflight tests."""
from pathlib import Path
import sys

import fitz
from PIL import Image

target = Path(sys.argv[1])
if target.suffix.lower() == ".pdf":
    doc = fitz.open()
    page = doc.new_page(width=252.28, height=198.43)  # 89 x 70 mm
    page.insert_text((20, 30), "too small", fontsize=3, fontname="helv")
    doc.save(target)
elif target.suffix.lower() == ".png":
    Image.new("RGB", (80, 60), "white").save(target, dpi=(20, 20))
else:
    raise SystemExit("expected .pdf or .png")
