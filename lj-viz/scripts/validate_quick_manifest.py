#!/usr/bin/env python3
"""Validate the lightweight, no-scientific-redesign lj-viz repair contract."""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from validate_manifest import load_manifest, manifest_project_root, missing, resolve_path

QUICK_ALLOWED_CHANGES = {
    "typography", "spacing", "label-placement", "legend-position",
    "annotation-placement", "line-weight", "symbol-size", "export-format",
}
PROTECTED_INVARIANTS = {"claim", "data", "estimand", "encoding", "scales"}


def existing_nonempty(value: object, root: Path) -> Path | None:
    path = resolve_path(value, root)
    return path if path is not None and path.exists() and path.stat().st_size > 0 else None


def read_report(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def validate_quick(data: dict, root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    required = ("figure_id", "workflow", "reader_task", "medium", "provenance", "output", "build", "qc")
    for key in required:
        if missing(data.get(key)):
            errors.append(f"missing required field: {key}")
    workflow = data.get("workflow") or {}
    if workflow.get("profile") != "quick":
        errors.append("workflow.profile must be quick")
    for key in ("task", "baseline_artifact", "preserve", "allowed_changes"):
        if missing(workflow.get(key)):
            errors.append(f"workflow.{key} is required")
    preserve = {str(item) for item in workflow.get("preserve") or []}
    for invariant in PROTECTED_INVARIANTS:
        if invariant not in preserve:
            errors.append(f"workflow.preserve must include {invariant}")
    allowed_changes = {str(item) for item in workflow.get("allowed_changes") or []}
    forbidden = allowed_changes & PROTECTED_INVARIANTS
    unknown_changes = allowed_changes - QUICK_ALLOWED_CHANGES
    if forbidden:
        errors.append(f"workflow.allowed_changes cannot modify protected invariants: {sorted(forbidden)}")
    if unknown_changes:
        errors.append(f"workflow.allowed_changes contains undeclared quick repairs: {sorted(unknown_changes)}")
    baseline = resolve_path(workflow.get("baseline_artifact"), root)
    baseline_missing = baseline is None or not baseline.exists() or baseline.stat().st_size == 0
    output = data.get("output") or {}
    for key in ("width_mm", "height_mm"):
        value = output.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            errors.append(f"output.{key} must be a positive number")
    if missing(output.get("formats")):
        errors.append("output.formats is required")
    provenance = data.get("provenance") or {}
    for key in ("code", "command"):
        if missing(provenance.get(key)):
            errors.append(f"provenance.{key} is required")
    build = data.get("build") or {}
    if build.get("status") not in {"planned", "success", "failed"}:
        errors.append("build.status must be planned, success, or failed")
    if baseline_missing:
        message = f"workflow.baseline_artifact is missing or empty: {workflow.get('baseline_artifact')}"
        if build.get("status") == "planned":
            warnings.append(message)
        else:
            errors.append(message)
    artifact_paths: list[Path] = []
    if build.get("status") == "success":
        if missing(build.get("artifacts")):
            errors.append("a successful build must list build.artifacts")
        for item in build.get("artifacts") or []:
            value = item.get("path") if isinstance(item, dict) else item
            path = existing_nonempty(value, root)
            if path is None:
                errors.append(f"successful build artifact is missing or empty: {value}")
            else:
                artifact_paths.append(path)
        code_path = existing_nonempty(provenance.get("code"), root)
        if code_path is None:
            errors.append(f"successful build code source is missing or empty: {provenance.get('code')}")
        else:
            newest_source = max(code_path.stat().st_mtime, baseline.stat().st_mtime) if baseline else code_path.stat().st_mtime
            for artifact in artifact_paths:
                if artifact.stat().st_mtime < newest_source:
                    errors.append(f"successful build artifact is stale relative to code/baseline: {artifact}")
    qc = data.get("qc") or {}
    technical = qc.get("technical_preflight") or {}
    if missing(technical):
        errors.append("qc.technical_preflight is required")
    elif technical.get("status") not in {"pending", "pass", "fail"}:
        errors.append("qc.technical_preflight.status must be pending, pass, or fail")
    elif technical.get("status") in {"pass", "fail"}:
        report = existing_nonempty(technical.get("report"), root)
        if report is None:
            errors.append(f"technical preflight report is missing or empty: {technical.get('report')}")
        elif technical.get("status") == "pass":
            if "RESULT: PASS" not in read_report(report):
                errors.append("technical preflight report does not contain RESULT: PASS")
            if artifact_paths and report.stat().st_mtime < max(path.stat().st_mtime for path in artifact_paths):
                errors.append("technical preflight report is stale relative to the declared artifacts")
    if qc.get("visual_craft_verdict") not in {"pending", "ship", "revise", "reject"}:
        errors.append("qc.visual_craft_verdict must be pending, ship, revise, or reject")
    if qc.get("visual_craft_verdict") == "ship":
        if build.get("status") != "success":
            errors.append("quick SHIP requires build.status: success")
        if technical.get("status") != "pass":
            errors.append("quick SHIP requires qc.technical_preflight.status: pass")
        if qc.get("baseline_diff_reviewed") is not True:
            errors.append("quick SHIP requires qc.baseline_diff_reviewed: true")
        diff_report = existing_nonempty(qc.get("baseline_diff_report"), root)
        if diff_report is None:
            errors.append("quick SHIP requires an existing qc.baseline_diff_report")
        else:
            diff_text = read_report(diff_report)
            if not all(marker in diff_text for marker in (
                "FACT: mean_absolute_error=", "FACT: changed_pixel_fraction=", "RESULT:",
            )):
                errors.append("quick SHIP baseline diff report is not a compare_render report")
            if artifact_paths and diff_report.stat().st_mtime < max(path.stat().st_mtime for path in artifact_paths):
                errors.append("quick SHIP baseline diff report is stale relative to the declared artifacts")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args()
    try:
        data = load_manifest(args.manifest)
        root = manifest_project_root(args.manifest.resolve(), data, args.project_root)
        errors, warnings = validate_quick(data, root)
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 2
    for warning in warnings:
        print(f"WARN: {warning}")
    for error in errors:
        print(f"FAIL: {error}")
    print(f"RESULT: {'FAIL' if errors else 'PASS'} ({len(errors)} errors, {len(warnings)} warnings)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
