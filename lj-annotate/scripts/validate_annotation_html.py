#!/usr/bin/env python3
"""Static validation for canonical lj-annotate HTML artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_annotation_html import (  # noqa: E402
    PacketError,
    RENDERER_VERSION,
    build_html,
    packet_sha256,
    validate_packet,
)


CSP_PARTS = [
    "default-src 'none'", "connect-src 'none'", "img-src 'none'",
    "media-src 'none'", "font-src 'none'", "form-action 'none'",
    "base-uri 'none'", "frame-src 'none'", "object-src 'none'",
]
NETWORK_CODE = ["fetch(", "xmlhttprequest", "websocket(", "sendbeacon("]
CORE_TOKENS = [
    "100dvh", "localStorage", "human_reviewed", "changed_from_ai",
    "ArrowRight", "ArrowLeft", "__ljAnnotateQA", "capacityOverflow",
    "candidate-card", "field-group", "highlight_terms", "packet_sha256",
    '.choice[aria-pressed="true"]', "selectedHaveCheck",
    "请先确认全部记录。",
]


def embedded_packet(text: str) -> dict:
    match = re.search(r'<script id="packet" type="application/json">(.*?)</script>', text, re.DOTALL)
    if not match:
        raise PacketError("embedded packet missing")
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise PacketError(f"embedded packet JSON invalid: {error}") from error
    if not isinstance(value, dict):
        raise PacketError("embedded packet must be an object")
    return value


def validate_html(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    failures: list[str] = []
    try:
        packet = embedded_packet(text)
        validate_packet(packet)
    except PacketError as error:
        failures.append(f"packet invalid: {error}")
        return failures

    low = text.lower()
    for part in CSP_PARTS:
        if part not in low:
            failures.append("CSP missing: " + part)
    if re.search(r'<(?:script|img|link|iframe)[^>]+(?:src|href)\s*=\s*["\']https?://', text, re.I):
        failures.append("external resource reference present")
    for token in NETWORK_CODE:
        if token in low:
            failures.append("network-capable code present: " + token)
    for required in CORE_TOKENS:
        if required not in text:
            failures.append("executable interaction contract missing: " + required)
    if "innerHTML" in text or "insertAdjacentHTML" in text:
        failures.append("unsafe HTML injection API present")
    if packet.get("mode") == "blind_coding":
        packet_keys = {str(key).lower() for key in packet.get("records", [{}])[0]}
        leaked = sorted(packet_keys & {"ai_draft", "ai_notes", "ai_answer", "prior_answer"})
        if leaked:
            failures.append("blind embedded packet contains AI/prior fields: " + ", ".join(leaked))

    version_match = re.search(r'<meta name="lj-annotate-renderer" content="([^"]+)">', text)
    if not version_match or version_match.group(1) != RENDERER_VERSION:
        failures.append("renderer version metadata mismatch")
    hash_match = re.search(r'<meta name="lj-annotate-packet-sha256" content="([0-9a-f]{64})">', text)
    if not hash_match or hash_match.group(1) != packet_sha256(packet):
        failures.append("embedded packet SHA-256 metadata mismatch")

    # Packet v2 is a closed renderer contract: project code may adapt data but
    # may not post-process HTML/CSS/JS. This turns missing hierarchy/highlights
    # and selection-state regressions into build failures.
    if packet.get("schema_version") == "lj.annotate.packet.2" and text != build_html(packet):
        failures.append("packet v2 artifact differs from the canonical renderer")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path)
    args = parser.parse_args()
    failures = validate_html(args.html)
    print(json.dumps({"status": "PASS" if not failures else "FAIL", "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
