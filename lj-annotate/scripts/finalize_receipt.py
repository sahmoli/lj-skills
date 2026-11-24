#!/usr/bin/env python3
"""Mark an lj-annotate build receipt as browser-validated."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: finalize_receipt.py RECEIPT.json", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("status") != "STATIC_VALIDATION_PASS_BROWSER_VALIDATION_PENDING":
        print("FAIL: receipt is not pending browser validation", file=sys.stderr)
        return 1
    receipt["status"] = "BROWSER_VALIDATION_PASS"
    receipt["browser_validation"] = {
        "runner": "Playwright Chromium",
        "desktop_viewport": "1440x900",
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: finalized {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
