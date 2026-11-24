#!/usr/bin/env python3
"""Build a canonical, dependency-free offline annotation workbench.

Packet v1 remains readable for frozen projects. Packet v2 is the public,
cross-research contract: project adapters describe scientific structure and
evidence; this renderer owns all HTML, interaction, provenance, and layout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


RENDERER_VERSION = "2.0.1"
PACKET_SCHEMAS = {"lj.annotate.packet.1", "lj.annotate.packet.2"}
RETURN_SCHEMAS = {"lj.annotate.return.1", "lj.annotate.return.2"}
MODES = {"assisted_review", "blind_coding"}
SECTION_ROLES = {
    "upstream_scope": 0,
    "peer_classification": 1,
    "downstream_outcome": 2,
    "input_quality": 3,
}
SECTION_TONES = {"target", "classification", "outcome", "quality", "neutral"}
HIGHLIGHT_TONES = {"target", "classification", "outcome"}
FORBIDDEN_BLIND_KEYS = {
    "ai", "ai_draft", "ai_answer", "ai_reason", "ai_confidence", "ai_notes",
    "ai_provenance", "prior_answer", "prior_answers", "human_prior_answer",
    "legacy_label", "outcome", "weight", "weights", "pi", "stratum",
    "sampling_stratum", "screen_flag",
}
RECORD_REQUIRED = {"record_key", "primary_text"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHORTCUT_RE = re.compile(r"^[a-z0-9]$")


class PacketError(ValueError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_packet_json(packet: dict[str, Any]) -> str:
    return json.dumps(packet, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def packet_sha256(packet: dict[str, Any]) -> str:
    return sha256_bytes(canonical_packet_json(packet).encode("utf-8"))


def nested_keys(value: Any) -> set[str]:
    out: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            out.add(str(key).lower())
            out.update(nested_keys(child))
    elif isinstance(value, list):
        for child in value:
            out.update(nested_keys(child))
    return out


def require_sha256(value: Any, label: str) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise PacketError(f"{label} must be a lowercase SHA-256 hex digest")


def validate_structural_rules(
    packet: dict[str, Any], option_values: dict[str, set[str]], field_section_rank: dict[str, int]
) -> None:
    rules = packet.get("structural_rules", [])
    if not isinstance(rules, list):
        raise PacketError("structural_rules must be a list")
    edges: dict[str, set[str]] = {key: set() for key in option_values}
    target_values: dict[str, set[str]] = {}
    structural_reachable: dict[tuple[str, str], int] = {}
    for rule in rules:
        when = rule.get("when", {}) if isinstance(rule, dict) else {}
        source = when.get("field")
        if source not in option_values or when.get("equals") not in option_values[source]:
            raise PacketError("structural rule condition is invalid")
        assignments = rule.get("set", {})
        locks = rule.get("lock", [])
        if not isinstance(assignments, dict) or not isinstance(locks, list):
            raise PacketError("structural rule set/lock is invalid")
        if set(assignments) != set(locks):
            raise PacketError("every structural assignment must be locked, and every lock must be assigned")
        for target, value in assignments.items():
            if target not in option_values or value not in option_values[target]:
                raise PacketError("structural rule assignment is invalid")
            if source == target:
                raise PacketError("structural rule cannot assign its own condition field")
            if field_section_rank and field_section_rank[source] > field_section_rank[target]:
                raise PacketError("structural rule cannot make a downstream field control an upstream field")
            edges[source].add(target)
            target_values.setdefault(target, set()).add(value)
            structural_reachable[(target, value)] = structural_reachable.get((target, value), 0) + 1
    if any(len(values) > 1 for values in target_values.values()):
        raise PacketError("multiple structural rules may not assign conflicting values to one field")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise PacketError("structural rule dependency cycle")
        if node in visited:
            return
        visiting.add(node)
        for child in edges[node]:
            visit(child)
        visiting.remove(node)
        visited.add(node)

    for field in edges:
        visit(field)

    for field in packet["fields"]:
        for option in field["options"]:
            if option.get("structural_only") and not structural_reachable.get((field["key"], option["value"])):
                raise PacketError("every structural-only value must be reachable from a structural rule")


def validate_packet(packet: dict[str, Any]) -> None:
    schema = packet.get("schema_version")
    if schema not in PACKET_SCHEMAS:
        raise PacketError("schema_version must be lj.annotate.packet.1 or lj.annotate.packet.2")
    is_v2 = schema == "lj.annotate.packet.2"
    mode = packet.get("mode")
    if mode not in MODES:
        raise PacketError("mode must be assisted_review or blind_coding")
    if not isinstance(packet.get("packet_id"), str) or not packet["packet_id"].strip():
        raise PacketError("packet_id must be non-empty text")
    records = packet.get("records")
    fields = packet.get("fields")
    if not isinstance(records, list) or not records:
        raise PacketError("records must be a non-empty list")
    if not isinstance(fields, list) or not fields:
        raise PacketError("fields must be a non-empty list")

    if is_v2:
        if not isinstance(packet.get("task_version"), str) or not packet["task_version"].strip():
            raise PacketError("packet v2 requires task_version")
        return_schema = packet.get("return_schema_version", "lj.annotate.return.2")
        if return_schema not in RETURN_SCHEMAS:
            raise PacketError("return_schema_version is invalid")
        provenance = packet.get("provenance")
        if not isinstance(provenance, dict):
            raise PacketError("packet v2 requires provenance")
        for key in ["task_spec_sha256", "codebook_sha256", "source_manifest_sha256"]:
            require_sha256(provenance.get(key), "provenance." + key)
        if mode == "assisted_review":
            ai = provenance.get("ai")
            if not isinstance(ai, dict) or not str(ai.get("system", "")).strip() or not str(ai.get("model", "")).strip():
                raise PacketError("assisted packet v2 requires provenance.ai system and model")
            require_sha256(ai.get("prompt_sha256"), "provenance.ai.prompt_sha256")
            require_sha256(ai.get("draft_manifest_sha256"), "provenance.ai.draft_manifest_sha256")

    field_keys: list[str] = []
    shortcut_keys: set[str] = set()
    option_values: dict[str, set[str]] = {}
    for number, field in enumerate(fields, 1):
        if not isinstance(field, dict):
            raise PacketError(f"field {number} must be an object")
        key = field.get("key")
        if not isinstance(key, str) or not key or key in field_keys:
            raise PacketError("field keys must be unique non-empty text")
        field_keys.append(key)
        options = field.get("options")
        if not isinstance(options, list) or len(options) < 2:
            raise PacketError(f"field {key} needs at least two options")
        values: set[str] = set()
        for option in options:
            value = option.get("value") if isinstance(option, dict) else None
            label = option.get("label") if isinstance(option, dict) else None
            shortcut = option.get("key") if isinstance(option, dict) else None
            if not isinstance(value, str) or not value or value in values:
                raise PacketError(f"field {key} option values must be unique text")
            if not isinstance(label, str) or not label:
                raise PacketError(f"field {key} option {value} needs a label")
            if shortcut is not None:
                shortcut = str(shortcut).lower()
                if not SHORTCUT_RE.fullmatch(shortcut) or shortcut in shortcut_keys:
                    raise PacketError("option shortcuts must be globally unique lowercase letters or digits")
                shortcut_keys.add(shortcut)
            values.add(value)
        option_values[key] = values

    field_section_rank: dict[str, int] = {}
    if is_v2:
        sections = packet.get("sections")
        if not isinstance(sections, list) or not sections:
            raise PacketError("packet v2 requires at least one scientific section")
        section_keys: set[str] = set()
        section_field_order: list[str] = []
        last_rank = -1
        for section in sections:
            if not isinstance(section, dict):
                raise PacketError("section must be an object")
            key = section.get("key")
            role = section.get("role")
            tone = section.get("tone", "neutral")
            refs = section.get("fields")
            if not isinstance(key, str) or not key or key in section_keys:
                raise PacketError("section keys must be unique non-empty text")
            if role not in SECTION_ROLES or SECTION_ROLES[role] < last_rank:
                raise PacketError("section roles must follow scientific order")
            if tone not in SECTION_TONES:
                raise PacketError("section tone is invalid")
            if not isinstance(section.get("label"), str) or not section["label"].strip():
                raise PacketError("section label is required")
            if not isinstance(refs, list) or not refs or any(ref not in field_keys for ref in refs):
                raise PacketError("section fields must reference real fields")
            if len(refs) != len(set(refs)):
                raise PacketError("a section cannot repeat a field")
            section_keys.add(key)
            last_rank = SECTION_ROLES[role]
            section_field_order.extend(refs)
            for ref in refs:
                if ref in field_section_rank:
                    raise PacketError("every field must belong to exactly one section")
                field_section_rank[ref] = last_rank
        if section_field_order != field_keys:
            raise PacketError("sections must cover fields exactly once and preserve field order")

        layout = packet.get("layout")
        if not isinstance(layout, dict) or layout.get("profile") != "fixed_review":
            raise PacketError("packet v2 requires layout.profile=fixed_review")
        if layout.get("desktop_decision_overflow", "fail") not in {"fail", "internal_scroll"}:
            raise PacketError("desktop_decision_overflow must be fail or internal_scroll")
        min_px = layout.get("evidence_min_font_px", 11)
        max_px = layout.get("evidence_max_font_px", 34)
        max_fields = layout.get("max_fields", 12)
        if not isinstance(min_px, int) or not 11 <= min_px <= 18:
            raise PacketError("evidence_min_font_px must be an integer from 11 to 18")
        if not isinstance(max_px, int) or not min_px <= max_px <= 42:
            raise PacketError("evidence_max_font_px is invalid")
        if not isinstance(max_fields, int) or max_fields < 1 or len(fields) > max_fields:
            raise PacketError("field count exceeds declared layout.max_fields")
        if layout.get("secondary_mode", "auto") not in {"auto", "hidden", "always"}:
            raise PacketError("secondary_mode must be auto, hidden, or always")

    validate_structural_rules(packet, option_values, field_section_rank)

    highlighting = packet.get("highlighting", {})
    if not isinstance(highlighting, dict):
        raise PacketError("highlighting must be an object")
    groups = highlighting.get("groups", [])
    highlight_keys: set[str] = set()
    concept_terms: dict[str, str] = {}
    focal_highlight_keys: list[str] = []
    if highlighting.get("enabled"):
        if not isinstance(groups, list) or not 1 <= len(groups) <= 3:
            raise PacketError("enabled highlighting requires one to three groups")
        for index, group in enumerate(groups):
            if not isinstance(group, dict) or not isinstance(group.get("label"), str):
                raise PacketError("highlight group needs a label")
            key = group.get("key", f"highlight_{index}")
            if not isinstance(key, str) or not key or key in highlight_keys:
                raise PacketError("highlight group keys must be unique")
            terms = group.get("static_terms", group.get("terms", []))
            if not isinstance(terms, list) or any(not isinstance(term, str) or not term.strip() for term in terms):
                raise PacketError("highlight terms must be non-empty text")
            if is_v2 and group.get("tone", "classification") not in HIGHLIGHT_TONES:
                raise PacketError("highlight tone is invalid")
            if is_v2 and group.get("targets", "both") not in {"primary", "secondary", "both"}:
                raise PacketError("highlight targets must be primary, secondary, or both")
            if group.get("include_focal_aliases"):
                focal_highlight_keys.append(key)
            for term in terms:
                folded = term.casefold()
                owner = concept_terms.get(folded)
                if owner is not None and owner != key:
                    raise PacketError("one literal highlight term cannot belong to multiple concepts")
                concept_terms[folded] = key
            highlight_keys.add(key)
        if len(focal_highlight_keys) > 1:
            raise PacketError("focal aliases may feed only one highlight concept")
        if mode == "blind_coding":
            auth = highlighting.get("blind_authorization")
            if is_v2:
                if not isinstance(auth, dict):
                    raise PacketError("blind highlighting requires hash-bound authorization")
                require_sha256(auth.get("protocol_sha256"), "blind_authorization.protocol_sha256")
                if auth.get("task_neutral") is not True or auth.get("discloses_no_design_or_outcome") is not True:
                    raise PacketError("blind highlighting authorization must affirm neutrality and no disclosure")
            elif not highlighting.get("protocol_authorized"):
                raise PacketError("blind highlighting requires explicit protocol_authorized=true")

    seen: set[str] = set()
    for number, record in enumerate(records, 1):
        if not isinstance(record, dict) or not RECORD_REQUIRED <= set(record):
            raise PacketError(f"record {number} missing record_key or primary_text")
        key = record["record_key"]
        if not isinstance(key, str) or not key or key in seen:
            raise PacketError("record_key must be unique non-empty text")
        seen.add(key)
        if not isinstance(record["primary_text"], str) or not isinstance(record.get("secondary_text", ""), str):
            raise PacketError(f"record {number} evidence must be text")
        if mode == "assisted_review":
            draft = record.get("ai_draft")
            if not isinstance(draft, dict) or list(draft) != field_keys:
                raise PacketError("assisted review requires one ordered complete AI draft per record")
            for field_key, value in draft.items():
                if value not in option_values[field_key]:
                    raise PacketError(f"record {number} has invalid AI draft for {field_key}")
        if is_v2:
            bindings = record.get("bindings")
            if not isinstance(bindings, dict):
                raise PacketError("packet v2 records require bindings")
            require_sha256(bindings.get("evidence_sha256"), f"record {number} evidence_sha256")
            focal = record.get("focal_entity")
            if focal is not None:
                if not isinstance(focal, dict) or not str(focal.get("label", "")).strip():
                    raise PacketError("focal_entity requires a human-readable label")
                aliases = focal.get("aliases")
                if not isinstance(aliases, list) or not aliases or any(not isinstance(x, str) or not x.strip() for x in aliases):
                    raise PacketError("focal_entity aliases must be non-empty text")
                for concept in focal_highlight_keys:
                    for term in aliases:
                        folded = term.casefold()
                        owner = concept_terms.get(folded)
                        if owner is not None and owner != concept:
                            raise PacketError("one literal highlight term cannot belong to multiple concepts")
                        concept_terms[folded] = concept
            active = record.get("active_fields", field_keys)
            if not isinstance(active, list) or not active or len(active) != len(set(active)) or any(x not in field_keys for x in active):
                raise PacketError("active_fields must be a unique non-empty subset of fields")
            notes = record.get("initial_notes", {})
            if not isinstance(notes, dict) or any(k not in field_keys or not isinstance(v, str) for k, v in notes.items()):
                raise PacketError("initial_notes must map field keys to text")
            dynamic = record.get("highlight_terms", {})
            if not isinstance(dynamic, dict) or any(k not in highlight_keys for k in dynamic):
                raise PacketError("record highlight_terms references an unknown highlight group")
            for concept, terms in dynamic.items():
                if not isinstance(terms, list) or any(not isinstance(term, str) or not term.strip() for term in terms):
                    raise PacketError("record highlight terms must be non-empty text")
                for term in terms:
                    folded = term.casefold()
                    owner = concept_terms.get(folded)
                    if owner is not None and owner != concept:
                        raise PacketError("one literal highlight term cannot belong to multiple concepts")
                    concept_terms[folded] = concept

    if mode == "blind_coding" and nested_keys(records) & FORBIDDEN_BLIND_KEYS:
        leaked = sorted(nested_keys(records) & FORBIDDEN_BLIND_KEYS)
        raise PacketError("blind packet contains forbidden keys: " + ", ".join(leaked))

    structural_only = {
        field["key"]: {option["value"] for option in field["options"] if option.get("structural_only")}
        for field in fields
    }
    if mode == "assisted_review":
        for number, record in enumerate(records, 1):
            draft = record["ai_draft"]
            active_assignments: dict[str, str] = {}
            active_locks: set[str] = set()
            for rule in packet.get("structural_rules", []):
                if draft[rule["when"]["field"]] == rule["when"]["equals"]:
                    active_assignments.update(rule.get("set", {}))
                    active_locks.update(rule.get("lock", []))
            for field_key, values in structural_only.items():
                if draft[field_key] in values and (
                    field_key not in active_locks or active_assignments.get(field_key) != draft[field_key]
                ):
                    raise PacketError(f"record {number} uses structural-only value outside an active rule")


class HTMLTemplate(str):
    """Keep the historical module.HTML.replace('__PACKET__', data) ABI alive."""

    def replace(self, old: str, new: str, count: int = -1) -> str:  # type: ignore[override]
        text = str(self)
        if old == "__PACKET__":
            digest = sha256_bytes(new.encode("utf-8"))
            text = text.replace("__PACKET_SHA256__", digest)
        return text.replace(old, new, count)


def build_html(packet: dict[str, Any]) -> str:
    validate_packet(packet)
    return HTML.replace("__PACKET__", canonical_packet_json(packet))


def build_receipt(packet_path: Path, html_path: Path) -> dict[str, Any]:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    validate_packet(packet)
    validator = Path(__file__).with_name("validate_annotation_html.py")
    return {
        "status": "STATIC_VALIDATION_PASS_BROWSER_VALIDATION_PENDING",
        "renderer_version": RENDERER_VERSION,
        "schema_version": packet["schema_version"],
        "return_schema_version": packet.get("return_schema_version", "lj.annotate.return.1"),
        "mode": packet["mode"],
        "record_n": len(packet["records"]),
        "field_n": len(packet["fields"]),
        "section_n": len(packet.get("sections", [])),
        "highlight_group_n": len(packet.get("highlighting", {}).get("groups", [])),
        "human_confirmed_n_at_build": 0,
        "artifact_hashes": {
            "packet_file": sha256_file(packet_path),
            "packet_semantic": packet_sha256(packet),
            "html": sha256_file(html_path),
            "renderer": sha256_file(Path(__file__)),
            "validator": sha256_file(validator) if validator.exists() else None,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an offline one-screen annotation HTML")
    parser.add_argument("packet", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_html(packet), encoding="utf-8")
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(
            json.dumps(build_receipt(args.packet, args.output), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        f"PASS renderer={RENDERER_VERSION} schema={packet['schema_version']} "
        f"records={len(packet['records'])} mode={packet['mode']}: {args.output}"
    )
    return 0


HTML = HTMLTemplate(r'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; connect-src 'none'; img-src 'none'; media-src 'none'; object-src 'none'; frame-src 'none'; font-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; form-action 'none'; base-uri 'none'">
<meta name="lj-annotate-renderer" content="2.0.1"><meta name="lj-annotate-packet-sha256" content="__PACKET_SHA256__">
<title>Offline annotation</title><style>
:root{color-scheme:light;--canvas:#e9ede8;--paper:#fffef9;--ink:#17231d;--muted:#66736c;--line:#d5dbd4;--action:#173b2c;--action-soft:#dceae2;--neutral:#f4f5f2;--neutral-ink:#37423c;--target:#b9e3d8;--target-ink:#104d43;--classification:#f1d58f;--classification-ink:#5d4609;--outcome:#efc3ca;--outcome-ink:#742735;--quality:#d9e0e5;--quality-ink:#35444f;--radius:10px;--gap:9px;--evidence-min:11px;--evidence-max:34px}
*{box-sizing:border-box}
html,body{height:100%;overflow:hidden}
body{margin:0;background:var(--canvas);color:var(--ink);font:14px/1.4 ui-sans-serif,-apple-system,"SF Pro Text","PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.app{height:100dvh;padding:var(--gap);display:grid;grid-template-rows:auto minmax(0,1fr) auto;gap:var(--gap)}
header{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:5px 14px;align-items:center}
.mode{font:800 11px/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.04em;color:#18593d}
h1{font-size:18px;line-height:1.15;margin:2px 0 0}
.status{color:var(--muted);font-variant-numeric:tabular-nums;text-align:right}
.track{grid-column:1/-1;height:4px;border-radius:9px;background:#d1d7d1;overflow:hidden}
.track i{display:block;width:0;height:100%;background:#18593d}
.capacity-warning{display:none;grid-column:1/-1;padding:4px 8px;border-radius:6px;background:#ffe4df;color:#8a2e1f;font-weight:800}
.capacity-warning.visible{display:block}
.workspace{min-height:0;display:grid;grid-template-columns:minmax(0,1.12fr) minmax(520px,.88fr);gap:var(--gap)}
.evidence,.coding{min-height:0;background:var(--paper);border:1px solid var(--line);border-radius:var(--radius)}
.evidence{padding:12px 15px 10px;display:grid;grid-template-rows:auto auto minmax(0,1fr) auto;gap:7px}
.evidence.has-secondary{grid-template-rows:auto auto minmax(0,1fr) auto minmax(0,.45fr) auto}
.candidate-card{display:flex;align-items:baseline;gap:10px;min-height:47px;padding:9px 12px;border-radius:9px;background:var(--target);color:var(--target-ink);border:2px solid #69ad9d}
.candidate-card.hidden{display:none}
.candidate-label{font:900 25px/1.05 ui-sans-serif,-apple-system,"PingFang SC",sans-serif}
.candidate-subtitle{font:750 13px/1.1 ui-monospace,SFMono-Regular,monospace;opacity:.78}
.label{color:var(--muted);font:750 10px/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;text-transform:uppercase;letter-spacing:.08em}
.primary,.secondary{min-height:0;white-space:pre-wrap;overflow-wrap:anywhere}
.primary{display:block;overflow:hidden;font:600 var(--evidence-max)/1.34 Georgia,"Songti SC","Noto Serif SC",serif}
.secondary{display:none;overflow:auto;padding-top:7px;border-top:1px solid var(--line);color:#46524b;font-size:14px}
.evidence.has-secondary .secondary{display:block}
.secondary-label{display:none}
.evidence.has-secondary .secondary-label{display:block}
.legend{display:flex;gap:11px;flex-wrap:wrap;padding-top:3px;border-top:1px solid var(--line);color:var(--muted);font-size:10px}
.swatch{display:inline-block;width:9px;height:9px;margin-right:4px;border-radius:2px}
.hit-target,.swatch-target{background:var(--target);color:var(--target-ink)}
.hit-classification,.swatch-classification{background:var(--classification);color:var(--classification-ink)}
.hit-outcome,.swatch-outcome{background:var(--outcome);color:var(--outcome-ink)}
mark{padding:0 .08em;border-radius:2px;color:inherit}
.fit-warning{color:#8a3b20;font-weight:800}
.coding{padding:7px;display:flex;flex-direction:column;gap:5px;overflow:hidden;background:#f8f8f4}
.field-group{border:1px solid var(--line);border-radius:9px;background:var(--paper);overflow:hidden}
.group-title{padding:4px 8px 3px;font:850 10px/1.2 ui-monospace,SFMono-Regular,monospace;letter-spacing:.08em;color:#5c6862;background:#eef1ed;border-bottom:1px solid var(--line)}
.field-group[data-tone="target"] .group-title{background:var(--target);color:var(--target-ink)}
.field-group[data-tone="classification"] .group-title{background:#f7eac7;color:var(--classification-ink)}
.field-group[data-tone="outcome"] .group-title{background:#f6dfe3;color:var(--outcome-ink)}
.field-group[data-tone="quality"]{opacity:.82}
.field-group[data-tone="quality"] .group-title{background:#edf0f2;color:var(--quality-ink)}
.field{display:grid;grid-template-columns:minmax(142px,.95fr) minmax(300px,1.65fr);grid-template-rows:auto 20px;column-gap:7px;align-items:center;padding:3px 7px;border-bottom:1px solid #e7eae6}
.field:last-child{border-bottom:0}
.field.inactive-record-field{opacity:.42}
.field-copy{min-width:0}
.field-title{font-size:13px;font-weight:800}
.field-hint{color:var(--muted);font-size:9px;line-height:1.15}
.choices{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;gap:5px}
.choice{position:relative;min-height:34px;padding:5px 22px 5px 22px;border:1px solid #cbd1cc;border-radius:7px;background:var(--neutral);color:var(--neutral-ink);box-shadow:none;font:750 11px/1.15 inherit;cursor:pointer}
.choice::before{content:""}
.choice[aria-pressed="true"]{border-width:1px;box-shadow:inset 0 0 0 2px rgba(0,0,0,.18)}
.choice[aria-pressed="true"]::before{content:"✓";position:absolute;left:7px;top:50%;transform:translateY(-50%);font-weight:950}
.field-group[data-tone="target"] .choice[aria-pressed="true"]{background:var(--target);color:var(--target-ink);border-color:#4c9d8a}
.field-group[data-tone="classification"] .choice[aria-pressed="true"]{background:var(--classification);color:var(--classification-ink);border-color:#c59d35}
.field-group[data-tone="outcome"] .choice[aria-pressed="true"]{background:var(--outcome);color:var(--outcome-ink);border-color:#c46b7a}
.field-group[data-tone="quality"] .choice[aria-pressed="true"]{background:var(--quality);color:var(--quality-ink);border-color:#8699a5}
.field-group[data-tone="neutral"] .choice[aria-pressed="true"]{background:var(--action-soft);color:var(--action);border-color:#6d9581}
.choice:disabled{opacity:.48;cursor:not-allowed}
.choice .key{position:absolute;right:6px;top:50%;transform:translateY(-50%);font:700 9px/1 ui-monospace,monospace;opacity:.55}
.ai-badge{position:absolute;left:4px;top:2px;padding:1px 3px;border:1px solid #aeb6b0;border-radius:3px;background:#fff;color:#4e5953;font-size:6px;letter-spacing:.05em}
.choice[aria-pressed="true"] .ai-badge{left:auto;right:18px;background:rgba(255,255,255,.76)}
.note-slot{grid-column:2;min-height:20px}
.note{visibility:hidden;width:100%;height:20px;padding:2px 7px;border:1px solid #795514;border-radius:6px;background:#fffaf0;font:10px inherit}
.note.visible{visibility:visible}
.footer{display:grid;grid-template-columns:auto 1fr auto auto minmax(235px,330px);gap:7px;align-items:center}
.footer button{min-height:41px;padding:7px 11px;border:1px solid var(--line);border-radius:8px;background:var(--paper);color:var(--ink);font-weight:780;cursor:pointer}
.footer .confirm{background:var(--action);color:white;border-color:var(--action)}
.help{text-align:center;color:var(--muted);font-size:10px}
.footer button:focus-visible,.choice:focus-visible,.note:focus-visible{outline:3px solid #5ba4cb;outline-offset:2px}
@media(max-height:700px) and (min-width:861px){.app{padding:5px;gap:5px}
.evidence{padding:8px}
.field{padding:2px 6px;grid-template-rows:auto 18px}
.choice{min-height:31px}
.footer button{min-height:35px}
}
@media(max-width:860px){html,body{height:auto;min-height:100%;overflow:auto}
.app{height:auto;min-height:100dvh}
.workspace{grid-template-columns:1fr}
.evidence{height:62vh;min-height:500px;max-height:650px}
.primary{min-height:0;overflow-y:auto}
.coding{overflow:visible}
.footer{grid-template-columns:repeat(2,1fr)}
.help{grid-column:1/-1;order:-1}
.footer .confirm{grid-column:1/-1}
.field{grid-template-columns:1fr;grid-template-rows:auto auto 29px}
.note-slot{grid-column:1}
}

</style></head><body><main class="app"><header><div><div class="mode" id="mode"></div><h1 id="title"></h1></div><div class="status" id="status"></div><div class="track"><i id="bar"></i></div><div class="capacity-warning" id="capacityWarning">当前字段在桌面目标尺寸内无法完整容纳；此页面尚未通过发布门。</div></header><section class="workspace"><article class="evidence" id="evidence"><div class="candidate-card hidden" id="candidateCard"><span class="candidate-label" id="candidateLabel"></span><span class="candidate-subtitle" id="candidateSubtitle"></span></div><div class="label evidence-label" id="primaryLabel">主要证据（已完整显示）</div><div class="primary" id="primary"></div><div class="label secondary-label" id="secondaryLabel">保留原文</div><div class="secondary" id="secondary"></div><div class="legend" id="legend"></div></article><aside class="coding" id="coding"></aside></section><footer class="footer"><button id="prev">← 上一条</button><div class="help">Enter / → 确认并继续 · ← 返回 · 自动保存在本机</div><button id="partial">导出已审核</button><button id="full">导出全部</button><button class="confirm" id="confirm"></button></footer></main><script id="packet" type="application/json">__PACKET__</script><script>
(()=>{'use strict';const RENDERER='2.0.1',P=JSON.parse(document.getElementById('packet').textContent),packetHash=document.querySelector('meta[name="lj-annotate-packet-sha256"]').content,N=P.records.length,assisted=P.mode==='assisted_review',v2=P.schema_version==='lj.annotate.packet.2',layout=P.layout||{},returnSchema=P.return_schema_version||(v2?'lj.annotate.return.2':'lj.annotate.return.1'),store='lj-annotate-'+P.packet_id+'-'+P.schema_version+'-'+packetHash.slice(0,16),fields=P.fields,fieldBy=Object.fromEntries(fields.map(f=>[f.key,f])),optionBy=Object.fromEntries(fields.map(f=>[f.key,Object.fromEntries(f.options.map(o=>[o.value,o]))])),blank=()=>Object.fromEntries(fields.map(f=>[f.key,''])),sections=P.sections||[{key:'default',role:'peer_classification',label:'判断',tone:'neutral',fields:fields.map(f=>f.key)}],$=id=>document.getElementById(id);let S;try{S=JSON.parse(localStorage.getItem(store)||'{}')}catch(_){S={}}S.index=Math.max(0,Math.min(N-1,Number(S.index)||0));S.rows=S.rows||{};
function activeSet(r){return new Set(r.active_fields||fields.map(f=>f.key))}function initialNotes(r){return assisted?(r.initial_notes||r.ai_notes||{}):(r.initial_notes||{})}function fresh(r){return{answers:assisted?{...r.ai_draft}:blank(),notes:{...initialNotes(r)},human_reviewed:false,reviewed_at:''}}P.records.forEach(r=>{if(!S.rows[r.record_key]||!S.rows[r.record_key].answers)S.rows[r.record_key]=fresh(r)});function persist(){localStorage.setItem(store,JSON.stringify(S))}function rec(){return P.records[S.index]}function row(){return S.rows[rec().record_key]}
function structural(a){const locked=new Set,assigned={};for(const rule of(P.structural_rules||[])){if(a.answers[rule.when.field]===rule.when.equals){for(const[k,v]of Object.entries(rule.set||{})){a.answers[k]=v;assigned[k]=v;delete a.notes[k]}for(const k of(rule.lock||[]))locked.add(k)}}return{locked,assigned}}function noteNeeded(f,v){const o=optionBy[f]&&optionBy[f][v];return!!(o&&o.requires_note)}function validField(f,v,locked){const o=optionBy[f]&&optionBy[f][v];return!!o&&(!o.structural_only||locked.has(f))}function fieldsReadyFor(r,a){const active=activeSet(r),{locked}=structural(a);return fields.every(f=>!active.has(f.key)||(validField(f.key,a.answers[f.key],locked)&&(!noteNeeded(f.key,a.answers[f.key])||String(a.notes[f.key]||'').trim())))}function completeFor(r,a){return fieldsReadyFor(r,a)&&a.human_reviewed}function changedFields(r,a){const active=activeSet(r);return assisted?fields.filter(f=>active.has(f.key)&&a.answers[f.key]!==r.ai_draft[f.key]).map(f=>f.key):[]}function changed(r,a){return changedFields(r,a).length>0}
function highlightGroups(r,target){const configured=(P.highlighting&&P.highlighting.enabled)?P.highlighting.groups||[]:[];return configured.map((g,i)=>{const key=g.key||('highlight_'+i),terms=[...(g.static_terms||g.terms||[]),...((r.highlight_terms||{})[key]||[])];if(g.include_focal_aliases&&r.focal_entity)terms.push(...(r.focal_entity.aliases||[]));return{...g,key,tone:g.tone||['classification','target','outcome'][i]||'classification',terms}}).filter(g=>(g.targets||'both')==='both'||(g.targets||'both')===target)}function decorate(el,text,target){el.textContent='';const hits=[];highlightGroups(rec(),target).forEach((g,gi)=>{g.terms.forEach(term=>{let start=0,hay=text.toLocaleLowerCase(),needle=term.toLocaleLowerCase();while(needle&&(start=hay.indexOf(needle,start))>=0){hits.push({start,end:start+term.length,gi,tone:g.tone});start+=term.length}})});hits.sort((a,b)=>a.start-b.start||(b.end-b.start)-(a.end-a.start)||a.gi-b.gi);const kept=[];for(const h of hits)if(!kept.length||h.start>=kept[kept.length-1].end)kept.push(h);let last=0;for(const h of kept){el.append(document.createTextNode(text.slice(last,h.start)));const m=document.createElement('mark');m.className='hit-'+h.tone;m.dataset.highlightGroup=String(h.gi);m.textContent=text.slice(h.start,h.end);el.append(m);last=h.end}el.append(document.createTextNode(text.slice(last)))}
function build(){const host=$('coding');host.textContent='';sections.forEach(group=>{const box=document.createElement('section');box.className='field-group';box.dataset.group=group.key;box.dataset.role=group.role;box.dataset.tone=group.tone||'neutral';const heading=document.createElement('div');heading.className='group-title';heading.textContent=group.label;box.append(heading);group.fields.forEach(key=>{const f=fieldBy[key],section=document.createElement('section');section.className='field';section.dataset.field=f.key;const copy=document.createElement('div');copy.className='field-copy';const title=document.createElement('div');title.className='field-title';title.textContent=f.label;const hint=document.createElement('div');hint.className='field-hint';hint.textContent=f.hint||'';copy.append(title,hint);const choices=document.createElement('div');choices.className='choices';f.options.forEach(o=>{const b=document.createElement('button');b.className='choice';b.type='button';b.dataset.value=o.value;b.dataset.tone=o.tone||'';b.textContent=o.label;if(o.key){const k=document.createElement('span');k.className='key';k.textContent=o.key;b.append(k)}if(assisted&&rec().ai_draft[f.key]===o.value){b.dataset.aiDraft='true';const ai=document.createElement('span');ai.className='ai-badge';ai.textContent='AI';b.append(ai)}b.onclick=()=>choose(f.key,o.value);choices.append(b)});const slot=document.createElement('div');slot.className='note-slot';const input=document.createElement('input');input.className='note';input.maxLength=500;input.placeholder='请写一句简短原因';input.setAttribute('aria-label',f.label+' note');input.oninput=()=>{const a=row();a.notes[f.key]=input.value;a.human_reviewed=false;render()};slot.append(input);section.append(copy,choices,slot);box.append(section)});host.append(box)})}
function renderLegend(){const host=$('legend');host.textContent='';if(!(P.highlighting&&P.highlighting.enabled))return;(P.highlighting.groups||[]).forEach((g,i)=>{const span=document.createElement('span'),sw=document.createElement('i'),tone=g.tone||['classification','target','outcome'][i]||'classification';sw.className='swatch swatch-'+tone;span.append(sw,document.createTextNode(g.label));host.append(span)})}
function fitEvidence(){const p=$('primary'),lab=$('primaryLabel'),min=Number(layout.evidence_min_font_px||11),max=Number(layout.evidence_max_font_px||34);p.style.fontSize=max+'px';p.style.lineHeight='1.34';let n=max;while(p.scrollHeight>p.clientHeight&&n>min){n-=1;p.style.fontSize=n+'px'}const overflow=p.scrollHeight>p.clientHeight;p.style.overflowY=overflow?'auto':'hidden';lab.textContent=overflow?'主要证据（极长文本，框内滚动）':'主要证据（已完整显示）';lab.classList.toggle('fit-warning',overflow);checkCapacity()}
function checkCapacity(){const coding=$('coding'),desktop=innerWidth>Number(layout.narrow_breakpoint_px||860),overflow=desktop&&coding.scrollHeight>coding.clientHeight+1,policy=layout.desktop_decision_overflow||'fail';document.body.dataset.capacityOverflow=String(overflow);$('capacityWarning').classList.toggle('visible',overflow&&policy==='fail');coding.style.overflowY=overflow&&policy==='internal_scroll'?'auto':'hidden'}
function render(){const r=rec(),a=row(),active=activeSet(r),{locked}=structural(a),focal=r.focal_entity||null,showFocal=P.records.some(x=>x.focal_entity),secondaryMode=layout.secondary_mode||'auto',showSecondary=secondaryMode==='always'||(secondaryMode==='auto'&&P.records.some(x=>String(x.secondary_text||'').trim()));$('candidateCard').classList.toggle('hidden',!showFocal);$('candidateLabel').textContent=focal?focal.label:'无特定对象';$('candidateSubtitle').textContent=focal?(focal.subtitle||focal.key||''):'';$('evidence').classList.toggle('has-secondary',showSecondary);decorate($('primary'),String(r.primary_text||''),'primary');decorate($('secondary'),String(r.secondary_text||''),'secondary');document.querySelectorAll('.field').forEach(section=>{const f=section.dataset.field,v=a.answers[f],inactive=!active.has(f);section.classList.toggle('inactive-record-field',inactive);section.setAttribute('aria-disabled',String(inactive));section.querySelectorAll('.choice').forEach(b=>{b.setAttribute('aria-pressed',String(b.dataset.value===v));b.disabled=inactive||locked.has(f)||(optionBy[f][b.dataset.value].structural_only&&!locked.has(f))});const input=section.querySelector('.note');input.classList.toggle('visible',!inactive&&noteNeeded(f,v)&&!locked.has(f));input.value=a.notes[f]||'';input.disabled=inactive||locked.has(f)});const done=P.records.filter(x=>completeFor(x,S.rows[x.record_key])).length;$('status').textContent=(S.index+1)+' / '+N+' · 已审核 '+done+' · 自动保存';$('bar').style.width=(100*done/N)+'%';$('confirm').textContent=assisted?(changed(r,a)?'保存修改，下一条 →':'AI 判断正确，下一条 →'):'确认，下一条 →';$('confirm').disabled=!fieldsReadyFor(r,a);$('prev').disabled=S.index===0;persist();requestAnimationFrame(fitEvidence)}
function rebuild(){build();render()}function choose(field,value){const r=rec(),a=row();if(!activeSet(r).has(field))return;const before=structural(a);a.answers[field]=value;a.human_reviewed=false;if(!noteNeeded(field,value))delete a.notes[field];const after=structural(a);for(const[target,oldValue]of Object.entries(before.assigned)){if(!after.locked.has(target)&&a.answers[target]===oldValue){a.answers[target]='';delete a.notes[target]}}render();const input=document.querySelector('[data-field="'+CSS.escape(field)+'"] .note');if(input&&noteNeeded(field,value))input.focus()}function move(delta){S.index=Math.max(0,Math.min(N-1,S.index+delta));rebuild()}function confirm(){const r=rec(),a=row();if(!fieldsReadyFor(r,a))return;a.human_reviewed=true;a.reviewed_at=new Date().toISOString();let next=-1;for(let step=1;step<=N;step++){const i=(S.index+step)%N;if(!S.rows[P.records[i].record_key].human_reviewed){next=i;break}}if(next>=0)S.index=next;rebuild()}
function exportData(kind){const all=P.records.map(r=>{const a=S.rows[r.record_key],out={record_key:r.record_key,answers:{...a.answers},notes:{...a.notes},human_reviewed:!!a.human_reviewed,reviewed_at:a.reviewed_at||''};if(r.bindings)out.bindings={...r.bindings};if(r.active_fields)out.active_fields=[...r.active_fields];if(assisted){out.ai_draft={...r.ai_draft};out.changed_from_ai=changed(r,a);if(returnSchema==='lj.annotate.return.2'){out.changed_fields=changedFields(r,a);out.ai_initial_notes={...initialNotes(r)}}}return out}),records=kind==='partial'?all.filter((x,i)=>completeFor(P.records[i],S.rows[P.records[i].record_key])):all;if(kind==='full'&&P.records.some(r=>!completeFor(r,S.rows[r.record_key]))){alert('请先确认全部记录。');return}const payload={schema_version:returnSchema,packet_id:P.packet_id,task_version:P.task_version||'',packet_sha256:packetHash,renderer_version:RENDERER,provenance:P.provenance||{},mode:P.mode,export_kind:kind,exported_at:new Date().toISOString(),records},blob=new Blob([JSON.stringify(payload,null,2)+'\n'],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=P.return_filename||P.packet_id+'-'+kind+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),0)}
function rect(el){const r=el.getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom,right:r.right}}function qa(){const selected=[...document.querySelectorAll('.choice[aria-pressed="true"]')],unselected=[...document.querySelectorAll('.choice[aria-pressed="false"]:not(:disabled)')],p=$('primary');return{renderer:RENDERER,packetSha256:packetHash,viewport:{width:innerWidth,height:innerHeight},document:{scrollWidth:document.body.scrollWidth,scrollHeight:document.body.scrollHeight,horizontalOverflow:document.body.scrollWidth>innerWidth+1,verticalOverflow:document.body.scrollHeight>innerHeight+1},status:$('status').textContent,footer:rect(document.querySelector('.footer')),fieldRects:Object.fromEntries([...document.querySelectorAll('.field')].map(e=>[e.dataset.field,rect(e)])),fieldN:document.querySelectorAll('.field').length,sectionN:document.querySelectorAll('.field-group').length,highlightN:document.querySelectorAll('mark').length,focalVisible:!$('candidateCard').classList.contains('hidden'),selectedN:selected.length,selectedHaveCheck:selected.every(e=>getComputedStyle(e,'::before').content!=='none'&&getComputedStyle(e,'::before').content!=='""'),unselectedBackgrounds:[...new Set(unselected.map(e=>getComputedStyle(e).backgroundColor))],capacityOverflow:document.body.dataset.capacityOverflow==='true',evidence:{fontSize:getComputedStyle(p).fontSize,scrollHeight:p.scrollHeight,clientHeight:p.clientHeight,overflowY:getComputedStyle(p).overflowY},reviewed:P.records.filter(x=>completeFor(x,S.rows[x.record_key])).length,index:S.index}}window.__ljAnnotateQA={snapshot:qa,setIndex:i=>{S.index=Math.max(0,Math.min(N-1,Number(i)||0));rebuild();return qa()},clear:()=>{localStorage.removeItem(store);location.reload()},storageKey:store,packetSha256:packetHash};
document.addEventListener('keydown',e=>{if(e.repeat||e.metaKey||e.ctrlKey||e.altKey)return;if(e.target.tagName==='INPUT'){if(e.key==='Enter'){e.preventDefault();confirm()}return}if(e.key==='Enter'||e.key==='ArrowRight'){e.preventDefault();confirm();return}if(e.key==='ArrowLeft'){e.preventDefault();move(-1);return}const key=e.key.toLowerCase();for(const f of fields)for(const o of f.options)if(String(o.key||'').toLowerCase()===key){e.preventDefault();choose(f.key,o.value);return}});$('mode').textContent=assisted?'AI-ASSISTED · HUMAN CONFIRMATION REQUIRED':'BLIND CODING · NO PREFILL';$('title').textContent=P.title||'离线标注';document.title=P.title||'Offline annotation';$('prev').onclick=()=>move(-1);$('confirm').onclick=confirm;$('partial').onclick=()=>exportData('partial');$('full').onclick=()=>exportData('full');renderLegend();addEventListener('resize',()=>requestAnimationFrame(fitEvidence));rebuild()})();
</script></body></html>''')


if __name__ == "__main__":
    raise SystemExit(main())
