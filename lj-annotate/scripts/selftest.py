#!/usr/bin/env python3
"""Synthetic positive, negative, compatibility, and anti-patch tests."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from build_annotation_html import PacketError, build_html, build_receipt, validate_packet
from validate_annotation_html import validate_html


HERE = Path(__file__).resolve().parent
REFERENCES = HERE.parent / "references"
V1 = json.loads((REFERENCES / "synthetic-packet.json").read_text(encoding="utf-8"))
V2 = json.loads((REFERENCES / "synthetic-packet-v2.json").read_text(encoding="utf-8"))


def must_fail(packet: dict, needle: str) -> None:
    try:
        validate_packet(packet)
    except PacketError as error:
        assert needle.lower() in str(error).lower(), (needle, str(error))
    else:
        raise AssertionError("negative packet unexpectedly passed: " + needle)


def main() -> int:
    for packet in [V1, V2]:
        validate_packet(packet)
        html = build_html(packet)
        assert "AI-ASSISTED" in html and "human_reviewed" in html and "100dvh" in html
        assert '.choice[aria-pressed="true"]{border-width:1px' in html
        assert "if(e.target.tagName==='INPUT'){if(e.key==='Enter')" in html
        assert "__PACKET__" not in html and "__PACKET_SHA256__" not in html
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            packet_path = directory / "packet.json"
            html_path = directory / "review.html"
            packet_path.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
            html_path.write_text(html, encoding="utf-8")
            assert not validate_html(html_path)
            if shutil.which("node"):
                scripts = html.split("<script>")
                assert len(scripts) == 2
                js = scripts[1].split("</script>", 1)[0]
                js_path = directory / "renderer.js"
                js_path.write_text(js, encoding="utf-8")
                result = subprocess.run(
                    ["node", "--check", str(js_path)], capture_output=True, text=True, check=False
                )
                assert result.returncode == 0, result.stdout + result.stderr
            receipt = build_receipt(packet_path, html_path)
            assert receipt["status"].endswith("BROWSER_VALIDATION_PENDING")
            assert receipt["artifact_hashes"]["packet_semantic"] in html

    # v1 stays readable for frozen evidence chains.
    bad = copy.deepcopy(V1)
    del bad["records"][0]["ai_draft"]["action"]
    must_fail(bad, "ordered complete AI draft")
    blind = copy.deepcopy(V1)
    blind["mode"] = "blind_coding"
    blind["highlighting"] = {"enabled": False}
    for record in blind["records"]:
        record.pop("ai_draft")
    validate_packet(blind)
    leaked = copy.deepcopy(blind)
    leaked["records"][0]["prior_answer"] = "yes"
    must_fail(leaked, "forbidden")
    leaked_notes = copy.deepcopy(blind)
    leaked_notes["records"][0]["ai_notes"] = {"scope": "AI rationale"}
    must_fail(leaked_notes, "ai_notes")
    highlighted = copy.deepcopy(blind)
    highlighted["highlighting"] = {
        "enabled": True, "groups": [{"label": "Target", "terms": ["target"]}]
    }
    must_fail(highlighted, "protocol_authorized")

    invalid_rule = copy.deepcopy(V2)
    invalid_rule["structural_rules"][0]["set"]["outcome"] = "not-a-value"
    must_fail(invalid_rule, "assignment")
    lock_without_set = copy.deepcopy(V2)
    lock_without_set["structural_rules"][0]["lock"].append("classification")
    must_fail(lock_without_set, "every structural assignment")
    downstream_control = copy.deepcopy(V2)
    downstream_control["structural_rules"] = [{
        "when": {"field": "quality", "equals": "no"},
        "set": {"scope": "no"}, "lock": ["scope"],
    }]
    downstream_control["fields"][2]["options"] = [o for o in downstream_control["fields"][2]["options"] if not o.get("structural_only")]
    downstream_control["records"][1]["ai_draft"]["outcome"] = "no"
    must_fail(downstream_control, "downstream")

    missing_section = copy.deepcopy(V2)
    missing_section["sections"].pop()
    must_fail(missing_section, "cover fields exactly once")
    reversed_roles = copy.deepcopy(V2)
    reversed_roles["sections"][0], reversed_roles["sections"][1] = (
        reversed_roles["sections"][1], reversed_roles["sections"][0]
    )
    must_fail(reversed_roles, "scientific order")
    over_capacity = copy.deepcopy(V2)
    over_capacity["layout"]["max_fields"] = 3
    must_fail(over_capacity, "exceeds declared")
    bad_hash = copy.deepcopy(V2)
    bad_hash["provenance"]["codebook_sha256"] = "not-a-hash"
    must_fail(bad_hash, "SHA-256")
    unknown_dynamic = copy.deepcopy(V2)
    unknown_dynamic["records"][0]["highlight_terms"]["unknown"] = ["term"]
    must_fail(unknown_dynamic, "unknown highlight group")
    duplicate_concept = copy.deepcopy(V2)
    duplicate_concept["records"][0]["highlight_terms"]["classification"] = ["species alpha"]
    must_fail(duplicate_concept, "multiple concepts")
    bad_active = copy.deepcopy(V2)
    bad_active["records"][0]["active_fields"] = ["unknown"]
    must_fail(bad_active, "active_fields")

    # Packet v2 pages are canonical: silent project-local HTML patches fail.
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "patched.html"
        path.write_text(build_html(V2).replace("AI-ASSISTED", "LOCALLY PATCHED"), encoding="utf-8")
        assert "canonical renderer" in " ".join(validate_html(path))

    print("PASS lj-annotate v1 compatibility + v2 contract regression tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
