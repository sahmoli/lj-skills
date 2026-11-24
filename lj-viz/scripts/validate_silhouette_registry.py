#!/usr/bin/env python3
"""Validate curated species silhouettes, taxonomic disclosure, licence, and hashes."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from urllib.parse import urlparse

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required to validate the silhouette registry") from exc


MATCH_LEVELS = {"exact", "synonym", "genus", "relative"}


def missing(value: object) -> bool:
    return value is None or value == "" or value == [] or value == {}


def load_registry(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("registry root must be a mapping")
    return data


def validate(data: dict, registry_path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    source = data.get("source") or {}
    if source.get("provider") != "PhyloPic":
        errors.append("source.provider must be PhyloPic for this registry")
    for key in ("homepage", "api_documentation", "image_usage"):
        if missing(source.get(key)):
            errors.append(f"source.{key} is required")

    assets = data.get("assets")
    if not isinstance(assets, dict) or not assets:
        errors.append("assets must be a non-empty mapping")
        return errors, warnings

    for asset_id, asset in assets.items():
        prefix = f"assets.{asset_id}"
        if not isinstance(asset, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        for key in ("intended_taxon", "depicted_taxon", "match_level", "file", "sha256", "source", "license", "creator"):
            if missing(asset.get(key)):
                errors.append(f"{prefix}.{key} is required")

        match_level = asset.get("match_level")
        if match_level not in MATCH_LEVELS:
            errors.append(f"{prefix}.match_level must be exact, synonym, genus, or relative")
        intended = str(asset.get("intended_taxon", "")).strip().casefold()
        depicted = str(asset.get("depicted_taxon", "")).strip().casefold()
        if match_level == "exact" and intended != depicted:
            errors.append(f"{prefix}: exact match requires intended_taxon = depicted_taxon")
        if match_level in {"genus", "relative"}:
            if asset.get("approximation_disclosed") is not True:
                errors.append(f"{prefix}: non-exact silhouette requires approximation_disclosed: true")
            if missing(asset.get("fallback_reason")) or str(asset.get("fallback_reason")).lower() == "not-applicable":
                errors.append(f"{prefix}: non-exact silhouette requires fallback_reason")

        licence = asset.get("license") or {}
        for key in ("id", "url", "commercial_use", "attribution_required"):
            if key not in licence or missing(licence.get(key)):
                errors.append(f"{prefix}.license.{key} is required")
        if licence.get("commercial_use") is not True:
            errors.append(f"{prefix}: curated publication assets must permit commercial reuse")
        if licence.get("attribution_required") is True and missing(asset.get("recommended_credit")):
            errors.append(f"{prefix}: attribution-required asset needs recommended_credit")

        source_data = asset.get("source") or {}
        for key in ("image_uuid", "node_uuid", "image_api", "source_url", "vector_url"):
            if missing(source_data.get(key)):
                errors.append(f"{prefix}.source.{key} is required")
        for key in ("image_api", "source_url", "vector_url"):
            value = source_data.get(key)
            if value and not urlparse(str(value)).netloc.endswith("phylopic.org"):
                errors.append(f"{prefix}.source.{key} must use an official phylopic.org host")

        file_value = asset.get("file")
        if file_value:
            file_path = registry_path.parent / str(file_value)
            if file_path.suffix.lower() != ".svg":
                errors.append(f"{prefix}.file must be an SVG")
            if not file_path.exists() or file_path.stat().st_size == 0:
                errors.append(f"{prefix}.file is missing or empty: {file_value}")
            else:
                digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
                if digest != str(asset.get("sha256", "")).lower():
                    errors.append(f"{prefix}.sha256 does not match {file_value}")

        if asset.get("modified") is True:
            note = asset.get("modification_note")
            if missing(note) or str(note).lower() == "not-applicable":
                errors.append(f"{prefix}: modified asset requires modification_note")
        elif asset.get("modified") is not False:
            warnings.append(f"{prefix}.modified should be explicit true or false")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("registry", type=Path)
    args = parser.parse_args()
    try:
        data = load_registry(args.registry)
        errors, warnings = validate(data, args.registry)
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 2
    for item in warnings:
        print(f"WARN: {item}")
    for item in errors:
        print(f"FAIL: {item}")
    if errors:
        print(f"RESULT: FAIL ({len(errors)} errors, {len(warnings)} warnings)")
        return 1
    print(f"RESULT: PASS ({len(warnings)} warnings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
