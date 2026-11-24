#!/usr/bin/env python3
"""Validate an lj-viz figure manifest and its conditional scientific guardrails."""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required to validate figure-manifest.yaml") from exc

COMMON_REQUIRED = (
    "figure_id", "workflow", "claim", "reader_task", "alternative_explanation", "medium",
    "reference_board", "visual_design", "visual_vocabulary", "provenance", "output", "build", "qc",
)
QUANTITATIVE_REQUIRED = (
    "analysis_unit", "repeating_unit", "estimand", "comparison", "panels", "uncertainty", "encoding",
    "presentation", "spatial",
)
CONCEPTUAL_REQUIRED = ("semantic_model", "representation")
FIGURE_FAMILIES = {"quantitative", "conceptual", "mixed"}
SEMANTIC_STATUSES = {"direct", "synthesized", "hypothesis", "design-only"}
NODE_ROLES = {
    "baseline", "insertion-point", "driver", "trigger", "mechanism", "mediator", "state", "outcome",
    "feedback", "failure", "safeguard", "context", "asset",
}
EDGE_RELATIONS = {
    "activates", "inhibits", "transforms", "transports", "amplifies", "feeds-back", "restores",
    "associates", "other",
}
EDGE_SIGNS = {"positive", "negative", "neutral", "unknown"}
TOPOLOGY_TYPES = {"linear", "branched", "convergent", "feedback", "parallel", "nested", "hybrid"}

HEX_COLOUR = re.compile(r"^#[0-9A-Fa-f]{6}$")
BUILTIN_NAMESPACES = {"evidence", "surrogacy", "portfolio", "period", "taxonomic"}
NEUTRAL_TOKENS = {"ink": "#202124", "context": "#D9DDE2", "missing": "#8B9098"}

def missing(value: object) -> bool:
    return value is None or value == "" or value == [] or value == {}

def load_manifest(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest root must be a mapping")
    return data

def resolve_path(value: object, project_root: Path | None) -> Path | None:
    if missing(value):
        return None
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path
    if project_root is None:
        return None
    return project_root / path


def manifest_project_root(
    manifest_path: Path,
    data: dict,
    override: Path | None = None,
) -> Path:
    """Resolve paths without depending on the caller's current directory."""
    if override is not None:
        return override.expanduser().resolve()
    declared = data.get("project_root")
    if not missing(declared):
        path = Path(str(declared)).expanduser()
        return (path if path.is_absolute() else manifest_path.parent / path).resolve()
    return manifest_path.parent.resolve()


def _ids(items: object, kind: str, errors: list[str]) -> set[str]:
    """Collect unique IDs from a manifest list while emitting actionable errors."""
    values: set[str] = set()
    if not isinstance(items, list) or not items:
        errors.append(f"semantic_model.{kind} must be a non-empty list")
        return values
    for index, item in enumerate(items, start=1):
        prefix = f"semantic_model.{kind}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        identifier = item.get("id")
        if missing(identifier):
            errors.append(f"{prefix}.id is required")
        elif str(identifier) in values:
            errors.append(f"duplicate {kind[:-1]} id: {identifier}")
        else:
            values.add(str(identifier))
    return values


def _semantic_reference(value: object, known: set[str]) -> str | None:
    """Return a normalized semantic element ID, or None for malformed references."""
    if isinstance(value, str):
        return value if value in known else None
    if isinstance(value, dict) and isinstance(value.get("id"), str):
        identifier = value["id"]
        return identifier if identifier in known else None
    return None


def _path_is_closed_cycle(path: object, edges: list[dict[str, object]]) -> bool:
    if not isinstance(path, list) or len(path) < 2 or not all(isinstance(item, str) for item in path):
        return False
    pairs = list(zip(path, path[1:])) + [(path[-1], path[0])]
    edge_pairs = {(str(edge.get("from")), str(edge.get("to"))) for edge in edges}
    return all(pair in edge_pairs for pair in pairs)


def validate_semantic_model(data: dict, errors: list[str]) -> dict[str, object]:
    """Validate the source-grounded causal/structural contract for conceptual figures."""
    model = data.get("semantic_model") or {}
    if not isinstance(model, dict):
        errors.append("semantic_model must be a mapping")
        return {}
    for key in ("thesis", "scope", "source_anchors", "nodes", "edges", "topology", "constraints"):
        if missing(model.get(key)):
            errors.append(f"semantic_model.{key} is required")
    anchors = model.get("source_anchors") or []
    anchor_ids = _ids(anchors, "source_anchors", errors)
    anchor_statuses = {
        str(anchor.get("id")): anchor.get("status")
        for anchor in anchors if isinstance(anchor, dict) and not missing(anchor.get("id"))
    }
    for index, anchor in enumerate(anchors if isinstance(anchors, list) else [], start=1):
        if not isinstance(anchor, dict):
            continue
        prefix = f"semantic_model.source_anchors[{index}]"
        for key in ("source", "locator", "supports", "status"):
            if missing(anchor.get(key)):
                errors.append(f"{prefix}.{key} is required")
        if anchor.get("status") not in SEMANTIC_STATUSES:
            errors.append(f"{prefix}.status must be one of {sorted(SEMANTIC_STATUSES)}")
        if not isinstance(anchor.get("supports"), list) or not anchor.get("supports"):
            errors.append(f"{prefix}.supports must be a non-empty list")

    nodes = model.get("nodes") or []
    node_ids = _ids(nodes, "nodes", errors)
    for index, node in enumerate(nodes if isinstance(nodes, list) else [], start=1):
        if not isinstance(node, dict):
            continue
        prefix = f"semantic_model.nodes[{index}]"
        for key in ("label", "role"):
            if missing(node.get(key)):
                errors.append(f"{prefix}.{key} is required")
        if node.get("role") not in NODE_ROLES:
            errors.append(f"{prefix}.role must be one of {sorted(NODE_ROLES)}")
        status = node.get("status", "direct")
        if status not in SEMANTIC_STATUSES:
            errors.append(f"{prefix}.status must be one of {sorted(SEMANTIC_STATUSES)}")
        evidence = node.get("evidence") or []
        if not isinstance(evidence, list):
            errors.append(f"{prefix}.evidence must be a list")
        elif not evidence and status != "hypothesis":
            errors.append(f"{prefix} requires evidence or status: hypothesis")
        for anchor_id in evidence:
            if str(anchor_id) not in anchor_ids:
                errors.append(f"{prefix}.evidence references unknown source anchor: {anchor_id}")
            elif anchor_statuses.get(str(anchor_id)) == "design-only":
                errors.append(f"{prefix}.evidence cannot use design-only source anchor: {anchor_id}")
        if status == "design-only" and node.get("role") not in {"context", "asset"}:
            errors.append(f"{prefix}: design-only nodes may only be context or asset")

    edges = model.get("edges") or []
    edge_ids = _ids(edges, "edges", errors)
    for index, edge in enumerate(edges if isinstance(edges, list) else [], start=1):
        if not isinstance(edge, dict):
            continue
        prefix = f"semantic_model.edges[{index}]"
        for key in ("from", "to", "relation", "sign"):
            if missing(edge.get(key)):
                errors.append(f"{prefix}.{key} is required")
        if str(edge.get("from")) not in node_ids:
            errors.append(f"{prefix}.from references unknown node: {edge.get('from')}")
        if str(edge.get("to")) not in node_ids:
            errors.append(f"{prefix}.to references unknown node: {edge.get('to')}")
        if edge.get("relation") not in EDGE_RELATIONS:
            errors.append(f"{prefix}.relation must be one of {sorted(EDGE_RELATIONS)}")
        if edge.get("sign") not in EDGE_SIGNS:
            errors.append(f"{prefix}.sign must be one of {sorted(EDGE_SIGNS)}")
        status = edge.get("status", "direct")
        if status not in SEMANTIC_STATUSES:
            errors.append(f"{prefix}.status must be one of {sorted(SEMANTIC_STATUSES)}")
        evidence = edge.get("evidence") or []
        if not isinstance(evidence, list):
            errors.append(f"{prefix}.evidence must be a list")
        elif not evidence and status != "hypothesis":
            errors.append(f"{prefix} requires evidence or status: hypothesis")
        for anchor_id in evidence:
            if str(anchor_id) not in anchor_ids:
                errors.append(f"{prefix}.evidence references unknown source anchor: {anchor_id}")
            elif anchor_statuses.get(str(anchor_id)) == "design-only":
                errors.append(f"{prefix}.evidence cannot use design-only source anchor: {anchor_id}")
        if status == "design-only":
            errors.append(f"{prefix}: design-only cannot be used for a causal edge")

    anchored_targets = node_ids | edge_ids | {"thesis", "scope"}
    for index, anchor in enumerate(anchors if isinstance(anchors, list) else [], start=1):
        if not isinstance(anchor, dict) or not isinstance(anchor.get("supports"), list):
            continue
        for target in anchor["supports"]:
            if str(target) not in anchored_targets:
                errors.append(
                    f"semantic_model.source_anchors[{index}].supports references unknown thesis/node/edge: {target}"
                )

    topology = model.get("topology") or {}
    if not isinstance(topology, dict):
        errors.append("semantic_model.topology must be a mapping")
        topology = {}
    elif topology.get("type") not in TOPOLOGY_TYPES:
        errors.append(f"semantic_model.topology.type must be one of {sorted(TOPOLOGY_TYPES)}")
    dominant_path = topology.get("dominant_path") or []
    if not isinstance(dominant_path, list) or len(dominant_path) < 2:
        errors.append("semantic_model.topology.dominant_path must name at least two nodes")
    else:
        for identifier in dominant_path:
            if str(identifier) not in node_ids:
                errors.append(f"semantic_model.topology.dominant_path references unknown node: {identifier}")
        edge_pairs = {(str(edge.get("from")), str(edge.get("to"))) for edge in edges if isinstance(edge, dict)}
        for source, target in zip(dominant_path, dominant_path[1:]):
            if (str(source), str(target)) not in edge_pairs:
                errors.append(f"semantic_model.topology.dominant_path is not connected: {source} -> {target}")
    loops = topology.get("feedback_loops") or []
    if not isinstance(loops, list):
        errors.append("semantic_model.topology.feedback_loops must be a list")
    else:
        for index, loop in enumerate(loops, start=1):
            if not _path_is_closed_cycle(loop, [edge for edge in edges if isinstance(edge, dict)]):
                errors.append(f"semantic_model.topology.feedback_loops[{index}] is not a closed directed cycle")
    if topology.get("type") == "feedback" and not loops:
        errors.append("feedback topology requires at least one real feedback loop")
    insertion_points = topology.get("insertion_points") or []
    if not isinstance(insertion_points, list) or not insertion_points:
        errors.append("semantic_model.topology.insertion_points must be a non-empty list")
    else:
        known_elements = node_ids | edge_ids
        for value in insertion_points:
            if _semantic_reference(value, known_elements) is None:
                errors.append(f"semantic_model.topology.insertion_points references unknown element: {value}")

    constraints = model.get("constraints") or {}
    if not isinstance(constraints, dict):
        errors.append("semantic_model.constraints must be a mapping")
        constraints = {}
    for key in ("must_show", "must_not_show", "locked_labels", "invariants", "redundant_encoding"):
        if missing(constraints.get(key)):
            errors.append(f"semantic_model.constraints.{key} is required")
    known_elements = node_ids | edge_ids
    shown = constraints.get("must_show") or []
    hidden = constraints.get("must_not_show") or []
    if not isinstance(shown, list) or not isinstance(hidden, list):
        errors.append("semantic_model.constraints.must_show and must_not_show must be lists")
    else:
        show_refs = {str(item) for item in shown}
        hide_refs = {str(item) for item in hidden}
        overlap = show_refs & hide_refs
        if overlap:
            errors.append(f"semantic_model.constraints conflict between must_show and must_not_show: {sorted(overlap)}")
        for value in shown:
            if _semantic_reference(value, known_elements) is None:
                errors.append(f"semantic_model.constraints.must_show references unknown element: {value}")
    locked_labels = constraints.get("locked_labels") or {}
    if not isinstance(locked_labels, dict) or not locked_labels:
        errors.append("semantic_model.constraints.locked_labels must be a non-empty mapping")
    else:
        node_by_id = {str(node.get("id")): node for node in nodes if isinstance(node, dict)}
        for identifier, label in locked_labels.items():
            if str(identifier) not in node_ids:
                errors.append(f"semantic_model.constraints.locked_labels references unknown node: {identifier}")
            elif not isinstance(label, str) or not label.strip():
                errors.append(f"semantic_model.constraints.locked_labels.{identifier} must be non-empty text")
            elif str(node_by_id[str(identifier)].get("label")) != label:
                errors.append(f"semantic_model.constraints.locked_labels.{identifier} must match the node label")
    for key in ("invariants", "redundant_encoding"):
        value = constraints.get(key)
        if not isinstance(value, list) or not value:
            errors.append(f"semantic_model.constraints.{key} must be a non-empty list")
    for value in constraints.get("invariants") or []:
        if _semantic_reference(value, known_elements) is None:
            errors.append(f"semantic_model.constraints.invariants references unknown element: {value}")
    return {
        "node_ids": node_ids,
        "edge_ids": edge_ids,
        "anchor_ids": anchor_ids,
    }


def validate_representation(data: dict, errors: list[str]) -> None:
    representation = data.get("representation") or {}
    if not isinstance(representation, dict):
        errors.append("representation must be a mapping")
        return
    if representation.get("canonical_editable") != "svg":
        errors.append("representation.canonical_editable must be svg in v1")
    if representation.get("ai_image_role") not in {"none", "draft", "asset"}:
        errors.append("representation.ai_image_role must be none, draft, or asset")
    if representation.get("ai_image_role") == "asset":
        assets = (data.get("provenance") or {}).get("ai_assets")
        if not isinstance(assets, list) or not assets:
            errors.append("provenance.ai_assets is required when AI imagery is a final asset")
        else:
            for index, asset in enumerate(assets, start=1):
                if not isinstance(asset, dict) or any(missing(asset.get(key)) for key in ("path", "model", "prompt", "role")):
                    errors.append(f"provenance.ai_assets[{index}] requires path, model, prompt, and role")


def _validate_quantitative_contract(data: dict, errors: list[str], warnings: list[str]) -> None:
    """Keep the existing data-figure contract intact for quantitative and mixed figures."""
    uncertainty = data.get("uncertainty") or {}
    applicable = uncertainty.get("applicable")
    if applicable is True:
        for key in ("target", "type", "level"):
            if missing(uncertainty.get(key)) or str(uncertainty.get(key)).lower() == "unknown":
                errors.append(f"uncertainty.{key} must be defined when uncertainty is applicable")
    elif applicable is False:
        if missing(uncertainty.get("reason")):
            errors.append("uncertainty.reason is required when uncertainty is not applicable")
    else:
        warnings.append("uncertainty.applicable is unknown; do not ship an inferential figure yet")
    panels = data.get("panels") or []
    if not isinstance(panels, list) or not panels:
        errors.append("panels must be a non-empty list")
    else:
        seen = set()
        for index, panel in enumerate(panels, start=1):
            if not isinstance(panel, dict):
                errors.append(f"panels[{index}] must be a mapping")
                continue
            label = panel.get("label")
            if missing(label):
                errors.append(f"panels[{index}].label is required")
            elif label in seen:
                errors.append(f"duplicate panel label: {label}")
            elif not re.fullmatch(r"[a-z](?:[a-z0-9′']*)", str(label)):
                errors.append(f"panel label must begin with a lowercase part label: {label}")
            seen.add(label)
            for key in ("role", "mark", "quantity_semantics", "axis_policy"):
                if missing(panel.get(key)):
                    errors.append(f"panels[{index}].{key} is required")
            mark = str(panel.get("mark", "")).lower()
            semantics = str(panel.get("quantity_semantics", "")).lower()
            axis_min = panel.get("axis_min")
            if mark in {"bar", "area"} and semantics == "absolute-magnitude" and panel.get("zero_is_meaningful") is True:
                if axis_min is None or float(axis_min) != 0.0:
                    errors.append(f"panel {label}: absolute magnitude encoded by {mark} must start at zero")
    spatial = data.get("spatial") or {}
    if spatial.get("is_map") is True:
        crs = str(spatial.get("crs", "unknown")).upper().replace(" ", "")
        purpose = str(spatial.get("purpose", "unknown")).lower()
        if crs in {"EPSG:3857", "3857"} and purpose in {"area", "density", "distance"}:
            errors.append("EPSG:3857 is not valid measurement geometry for area, density, or distance")
        sensitive = spatial.get("sensitive_locality") or {}
        method = str(sensitive.get("method", "none")).lower()
        if "jitter" in method or ("random" in method and "displace" in method):
            errors.append("arbitrary coordinate jitter is not an acceptable sensitive-locality method")
    encoding = data.get("encoding") or {}
    if encoding.get("colour_is_sole_carrier") is True and not encoding.get("redundant_channel"):
        warnings.append("colour is the sole carrier; add shape, line type, direct label, or another redundant channel")
    presentation = data.get("presentation") or {}
    for key in ("ordering", "axis_breaks", "unit_display", "abbreviations", "label_priority", "shared_scale"):
        if missing(presentation.get(key)):
            errors.append(f"presentation.{key} is required")
    abbreviations = presentation.get("abbreviations") or {}
    if isinstance(abbreviations, dict):
        if abbreviations.get("applicable") is True and missing(abbreviations.get("dictionary")):
            errors.append("presentation.abbreviations.dictionary is required when applicable")
        if abbreviations.get("applicable") is False and missing(abbreviations.get("reason")):
            errors.append("presentation.abbreviations.reason is required when not applicable")
    shared_scale = presentation.get("shared_scale") or {}
    if isinstance(shared_scale, dict):
        if shared_scale.get("comparable") not in {True, False, "not-applicable"}:
            errors.append("presentation.shared_scale.comparable must be true, false, or not-applicable")
        if shared_scale.get("comparable") is False and missing(shared_scale.get("disclosure")):
            errors.append("non-comparable panel scales require presentation.shared_scale.disclosure")


def _validate_mixed_bindings(data: dict, semantic: dict[str, object], errors: list[str]) -> None:
    bindings = data.get("mixed_bindings") or []
    if not isinstance(bindings, list) or not bindings:
        errors.append("mixed_bindings must be a non-empty list for mixed figures")
        return
    known_semantic = set(semantic.get("node_ids") or set()) | set(semantic.get("edge_ids") or set())
    panel_labels = {
        str(panel.get("label"))
        for panel in data.get("panels") or []
        if isinstance(panel, dict) and not missing(panel.get("label"))
    }
    for index, binding in enumerate(bindings, start=1):
        prefix = f"mixed_bindings[{index}]"
        if not isinstance(binding, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        for key in ("semantic_id", "panel_label", "evidence_role"):
            if missing(binding.get(key)):
                errors.append(f"{prefix}.{key} is required")
        if str(binding.get("semantic_id")) not in known_semantic:
            errors.append(f"{prefix}.semantic_id references unknown node or edge: {binding.get('semantic_id')}")
        if str(binding.get("panel_label")) not in panel_labels:
            errors.append(f"{prefix}.panel_label references unknown panel: {binding.get('panel_label')}")


def validate(data: dict, project_root: Path | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    figure_family = data.get("figure_family", "quantitative")
    if figure_family not in FIGURE_FAMILIES:
        errors.append(f"figure_family must be one of {sorted(FIGURE_FAMILIES)}")
        figure_family = "quantitative"
    quantitative = figure_family in {"quantitative", "mixed"}
    conceptual = figure_family in {"conceptual", "mixed"}
    required = COMMON_REQUIRED + (QUANTITATIVE_REQUIRED if quantitative else ()) + (CONCEPTUAL_REQUIRED if conceptual else ())
    for key in required:
        if key not in data or missing(data[key]):
            errors.append(f"missing required field: {key}")
    workflow = data.get("workflow") or {}
    profile = workflow.get("profile")
    if profile not in {"full", "revision"}:
        errors.append("workflow.profile must be full or revision; quick work uses validate_quick_manifest.py")
    if profile == "revision":
        for key in ("baseline_artifact", "reviewer_request", "allowed_changes", "preserve"):
            if missing(workflow.get(key)):
                errors.append(f"workflow.{key} is required for revision")
        baseline = resolve_path(workflow.get("baseline_artifact"), project_root)
        if project_root is not None and (baseline is None or not baseline.exists()):
            errors.append("workflow.baseline_artifact must exist for revision")
        preserve = {str(item) for item in workflow.get("preserve") or []}
        protected = {"claim"}
        if quantitative:
            protected |= {"data", "estimand", "encoding", "scales"}
        if conceptual:
            protected |= {"semantic_model", "source_anchors", "locked_labels"}
        for invariant in protected:
            if invariant not in preserve:
                errors.append(f"workflow.preserve must include {invariant} for revision")
        forbidden = {str(item) for item in workflow.get("allowed_changes") or []} & protected
        if forbidden:
            errors.append(f"workflow.allowed_changes cannot modify protected invariants: {sorted(forbidden)}")
    provenance = data.get("provenance") or {}
    provenance_fields = ("data", "code", "command", "transforms") if quantitative else ("code", "command", "transforms")
    for key in provenance_fields:
        if missing(provenance.get(key)):
            errors.append(f"provenance.{key} is required")
    output = data.get("output") or {}
    for key in ("width_mm", "height_mm", "formats"):
        if missing(output.get(key)):
            errors.append(f"output.{key} is required")
    for key in ("width_mm", "height_mm"):
        value = output.get(key)
        if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0):
            errors.append(f"output.{key} must be a positive number")
    build = data.get("build") or {}
    if build.get("status") not in {"planned", "success", "failed"}:
        errors.append("build.status must be planned, success, or failed")
    if build.get("status") == "success" and missing(build.get("artifacts")):
        errors.append("a successful build must list build.artifacts")
    artifact_paths: list[Path] = []
    if build.get("status") == "success" and not missing(build.get("artifacts")) and project_root is not None:
        for item in build.get("artifacts") or []:
            value = item.get("path") if isinstance(item, dict) else item
            path = resolve_path(value, project_root)
            if path is None or not path.exists() or path.stat().st_size == 0:
                errors.append(f"successful build artifact is missing or empty: {value}")
            else:
                artifact_paths.append(path)
        source_paths: list[Path] = []
        code_path = resolve_path(provenance.get("code"), project_root)
        if code_path is None or not code_path.exists():
            errors.append(f"successful build code source is missing: {provenance.get('code')}")
        else:
            source_paths.append(code_path)
        if quantitative:
            for item in provenance.get("data") or []:
                value = item.get("path") if isinstance(item, dict) else item
                path = resolve_path(value, project_root)
                if path is None or not path.exists():
                    errors.append(f"successful build data source is missing: {value}")
                else:
                    source_paths.append(path)
        if artifact_paths and source_paths:
            newest_source = max(path.stat().st_mtime for path in source_paths)
            for artifact in artifact_paths:
                if artifact.stat().st_mtime < newest_source:
                    errors.append(f"successful build artifact is stale relative to code/data: {artifact}")
    if conceptual:
        semantic_summary = validate_semantic_model(data, errors)
        validate_representation(data, errors)
        if "svg" not in {str(item).lower() for item in output.get("formats") or []}:
            errors.append("conceptual and mixed figures must declare svg in output.formats")
    else:
        semantic_summary = {"node_ids": set(), "edge_ids": set()}

    if quantitative:
        _validate_quantitative_contract(data, errors, warnings)
    if figure_family == "mixed":
        _validate_mixed_bindings(data, semantic_summary, errors)

    references = data.get("reference_board") or []
    if not isinstance(references, list) or not references:
        errors.append("reference_board must name at least one source or baseline for a full figure")
    else:
        for index, reference in enumerate(references, start=1):
            prefix = f"reference_board[{index}]"
            if not isinstance(reference, dict):
                errors.append(f"{prefix} must be a mapping")
                continue
            for key in ("source_id", "figure_id", "borrow", "avoid"):
                if missing(reference.get(key)):
                    errors.append(f"{prefix}.{key} is required")
            if reference.get("source_kind", "corpus") not in {"corpus", "local-pdf", "baseline"}:
                errors.append(f"{prefix}.source_kind must be corpus, local-pdf, or baseline")
    visual = data.get("visual_design") or {}
    for key in ("direction", "hierarchy", "palette", "spacing_mm", "typography", "scaffolding", "density_strategy", "legend_strategy", "placement", "icons"):
        if missing(visual.get(key)):
            errors.append(f"visual_design.{key} is required")
    direction = visual.get("direction")
    if direction and direction not in {"quiet-analytical", "spatial", "mechanism", "image-led"}:
        errors.append("visual_design.direction must be quiet-analytical, spatial, mechanism, or image-led")
    hierarchy = visual.get("hierarchy") or {}
    for key in ("hero_panel", "support_strategy", "area_earned_by"):
        if missing(hierarchy.get(key)):
            errors.append(f"visual_design.hierarchy.{key} is required")
    palette = visual.get("palette") or {}
    for key in ("ink", "context", "missing"):
        value = palette.get(key)
        if missing(value) or not HEX_COLOUR.fullmatch(str(value)):
            errors.append(f"visual_design.palette.{key} must be a six-digit hex colour")
        elif str(value).upper() != NEUTRAL_TOKENS[key]:
            errors.append(f"visual_design.palette.{key} must match the runtime neutral token {NEUTRAL_TOKENS[key]}")
    namespace = str(palette.get("namespace", ""))
    if missing(namespace):
        errors.append("visual_design.palette.namespace is required")
    elif namespace not in BUILTIN_NAMESPACES and not re.fullmatch(r"(?:paper-specific|sequential|diverging):[a-z0-9][a-z0-9-]*", namespace):
        errors.append(
            "visual_design.palette.namespace must be a runtime namespace or an explicit "
            "paper-specific:/sequential:/diverging: namespace"
        )
    semantic = palette.get("semantic") or {}
    if not isinstance(semantic, dict) or not semantic:
        errors.append("visual_design.palette.semantic must map scientific meanings to colours")
    else:
        colours_to_meanings: dict[str, list[str]] = {}
        for meaning, value in semantic.items():
            if missing(meaning) or not HEX_COLOUR.fullmatch(str(value)):
                errors.append(f"visual_design.palette.semantic.{meaning} must be a six-digit hex colour")
            else:
                colours_to_meanings.setdefault(str(value).upper(), []).append(str(meaning))
        for colour, meanings in colours_to_meanings.items():
            if len(meanings) > 1:
                errors.append(f"semantic colour collision {colour}: {', '.join(meanings)}")
        critical_pairs = palette.get("critical_pairs")
        ordered_namespace = namespace.startswith(("sequential:", "diverging:"))
        if len(semantic) > 1 and not ordered_namespace and not isinstance(critical_pairs, list):
            errors.append("visual_design.palette.critical_pairs must declare the role pairs readers compare")
        elif isinstance(critical_pairs, list):
            for index, pair in enumerate(critical_pairs):
                if not isinstance(pair, list) or len(pair) != 2:
                    errors.append(
                        f"visual_design.palette.critical_pairs[{index}] must contain exactly two roles"
                    )
                elif any(str(role) not in semantic for role in pair):
                    errors.append(
                        f"visual_design.palette.critical_pairs[{index}] references an undeclared semantic role"
                    )
    if palette.get("collision_check") is not True:
        errors.append("visual_design.palette.collision_check must be true; one hue cannot silently change meaning")
    accent_budget = palette.get("accent_budget")
    if not isinstance(accent_budget, int) or isinstance(accent_budget, bool) or accent_budget < 0 or accent_budget > 2:
        errors.append("visual_design.palette.accent_budget must be an integer from 0 to 2")
    category_count = palette.get("categorical_count")
    if not isinstance(category_count, int) or isinstance(category_count, bool) or category_count < 0:
        errors.append("visual_design.palette.categorical_count must be a non-negative integer")
    spacing = visual.get("spacing_mm") or {}
    spacing_tokens = (1.5, 2.5, 4.0, 6.0, 9.0)
    for key in ("outer", "panel", "within_panel", "label_offset"):
        value = spacing.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
            errors.append(f"visual_design.spacing_mm.{key} must be a positive number")
        elif not any(math.isclose(float(value), token, abs_tol=1e-6) for token in spacing_tokens):
            errors.append(
                f"visual_design.spacing_mm.{key} must use the Nature spacing tokens: 1.5, 2.5, 4, 6, or 9 mm"
            )
    typography = visual.get("typography") or {}
    if missing(typography.get("family")):
        errors.append("visual_design.typography.family is required")
    body_pt = typography.get("body_pt")
    if (
        not isinstance(body_pt, (int, float)) or isinstance(body_pt, bool)
        or not math.isfinite(body_pt) or body_pt <= 0
    ):
        errors.append("visual_design.typography.body_pt must be a positive final-size point value")
    panel_label_pt = typography.get("panel_label_pt")
    if (
        not isinstance(panel_label_pt, (int, float)) or isinstance(panel_label_pt, bool)
        or not math.isfinite(panel_label_pt) or panel_label_pt <= 0
    ):
        errors.append("visual_design.typography.panel_label_pt must be a positive final-size point value")
    if typography.get("coloured_text") is not False:
        errors.append("Nature-style figures use black/white text plus keys, not coloured text")
    if typography.get("panel_title_strategy") not in {"caption-only", "short-header", "axis-header"}:
        errors.append("visual_design.typography.panel_title_strategy must avoid dashboard-style panel headlines")
    scaffolding = visual.get("scaffolding") or {}
    stroke = scaffolding.get("stroke_pt")
    if not isinstance(stroke, (int, float)) or isinstance(stroke, bool) or stroke < 0.25 or stroke > 1:
        errors.append("visual_design.scaffolding.stroke_pt must be 0.25–1 pt at final size")
    for key in ("background_gridlines", "drop_shadows", "decorative_boxes"):
        if scaffolding.get(key) is not False:
            errors.append(f"Nature-style default requires visual_design.scaffolding.{key}: false")
    if scaffolding.get("corner_policy") != "square":
        errors.append("visual_design.scaffolding.corner_policy must be square; rounded UI cards are not the default")
    if visual.get("legend_strategy") not in {"direct-label", "shared-strip", "compact", "none"}:
        errors.append("visual_design.legend_strategy must be direct-label, shared-strip, compact, or none")
    placement = visual.get("placement") or {}
    for key in ("collision_check", "clip_check", "longest_label_stress_test"):
        if placement.get(key) is not True:
            errors.append(f"visual_design.placement.{key} must be true")
    for key in ("edge_clearance_mm", "label_icon_clearance_mm"):
        value = placement.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not any(
            math.isclose(float(value), token, abs_tol=1e-6) for token in spacing_tokens
        ):
            errors.append(
                f"visual_design.placement.{key} must use the Nature spacing tokens: 1.5, 2.5, 4, 6, or 9 mm"
            )
    ladder = placement.get("direct_label_ladder")
    allowed_ladder = ["outside-data", "margin-band", "leader-line", "compact-legend"]
    if ladder != allowed_ladder:
        errors.append(
            "visual_design.placement.direct_label_ladder must be "
            "[outside-data, margin-band, leader-line, compact-legend]"
        )
    icons = visual.get("icons") or {}
    if icons.get("mode") not in {"none", "semantic"}:
        errors.append("visual_design.icons.mode must be none or semantic; decorative icons are not allowed")
    if icons.get("mode") == "semantic":
        for key in ("purpose", "provenance"):
            if missing(icons.get(key)) or str(icons.get(key)).lower() in {"unknown", "not-applicable"}:
                errors.append(f"visual_design.icons.{key} is required for semantic icons")
    if icons.get("grammar") not in {"none", "repeated-small", "diagram-symbol"}:
        errors.append("visual_design.icons.grammar must be none, repeated-small, or diagram-symbol")
    if icons.get("mode") == "semantic" and icons.get("grammar") == "none":
        errors.append("semantic icons require a declared repeated-small or diagram-symbol grammar")
    silhouettes = icons.get("silhouettes") or []
    if not isinstance(silhouettes, list):
        errors.append("visual_design.icons.silhouettes must be a list")
    else:
        if silhouettes:
            optical_height = icons.get("optical_height_mm")
            if (
                not isinstance(optical_height, (int, float))
                or isinstance(optical_height, bool)
                or not 5 <= float(optical_height) <= 9
            ):
                errors.append(
                    "visual_design.icons.optical_height_mm must be 5–9 mm at final size when silhouettes are used"
                )
        for index, silhouette in enumerate(silhouettes, start=1):
            prefix = f"visual_design.icons.silhouettes[{index}]"
            if not isinstance(silhouette, dict):
                errors.append(f"{prefix} must be a mapping")
                continue
            for key in ("registry_id", "intended_taxon", "depicted_taxon", "match_level"):
                if missing(silhouette.get(key)):
                    errors.append(f"{prefix}.{key} is required")
            match_level = silhouette.get("match_level")
            if match_level not in {"exact", "synonym", "genus", "relative"}:
                errors.append(f"{prefix}.match_level must be exact, synonym, genus, or relative")
            intended = str(silhouette.get("intended_taxon", "")).casefold()
            depicted = str(silhouette.get("depicted_taxon", "")).casefold()
            if match_level == "exact" and intended != depicted:
                errors.append(f"{prefix}: exact match requires intended_taxon = depicted_taxon")
            if match_level in {"genus", "relative"} and silhouette.get("approximation_disclosed") is not True:
                errors.append(f"{prefix}: non-exact silhouette requires approximation_disclosed: true")
    vocabulary = data.get("visual_vocabulary") or {}
    applicable = vocabulary.get("applicable")
    if applicable is True:
        for key in ("scope", "path", "locked_channels"):
            if missing(vocabulary.get(key)):
                errors.append(f"visual_vocabulary.{key} is required when applicable")
        if vocabulary.get("scope") not in {"paper", "figure-set"}:
            errors.append("visual_vocabulary.scope must be paper or figure-set when applicable")
        vocabulary_path = resolve_path(vocabulary.get("path"), project_root)
        if project_root is not None and (vocabulary_path is None or not vocabulary_path.exists()):
            errors.append(f"visual_vocabulary.path does not exist: {vocabulary.get('path')}")
        elif vocabulary_path is not None:
            try:
                vocabulary_data = yaml.safe_load(vocabulary_path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as exc:
                errors.append(f"visual_vocabulary.path cannot be parsed: {exc}")
            else:
                if not isinstance(vocabulary_data, dict):
                    errors.append("visual_vocabulary.path must contain a YAML mapping")
                else:
                    vocabulary_palette = vocabulary_data.get("palette") or {}
                    if vocabulary_palette.get("namespace") != namespace:
                        errors.append(
                            "visual_vocabulary palette namespace does not match visual_design.palette.namespace"
                        )
                    vocabulary_roles = vocabulary_palette.get("semantic_roles") or {}
                    if vocabulary_roles != semantic:
                        errors.append(
                            "visual_vocabulary semantic colour roles do not match visual_design.palette.semantic"
                        )
                    vocabulary_neutrals = vocabulary_data.get("neutral_roles") or {}
                    for key, expected in NEUTRAL_TOKENS.items():
                        if str(vocabulary_neutrals.get(key, "")).upper() != expected:
                            errors.append(
                                f"visual_vocabulary neutral_roles.{key} must match the runtime token {expected}"
                            )
                    physical_type = vocabulary_data.get("typography_physical") or {}
                    manifest_type = visual.get("typography") or {}
                    for source_key, manifest_key in (
                        ("body_pt", "body_pt"), ("panel_label_pt", "panel_label_pt")
                    ):
                        if source_key in physical_type and physical_type.get(source_key) != manifest_type.get(manifest_key):
                            errors.append(
                                f"visual_vocabulary typography_physical.{source_key} does not match manifest typography"
                            )
    elif applicable is False:
        if missing(vocabulary.get("reason")):
            errors.append("visual_vocabulary.reason is required when not applicable")
    else:
        errors.append("visual_vocabulary.applicable must be true or false")
    qc = data.get("qc") or {}
    stress = qc.get("stress_render") or {}
    if stress.get("status") not in {"pending", "pass", "fail"}:
        errors.append("qc.stress_render.status must be pending, pass, or fail")
    elif stress.get("status") == "pass" and project_root is not None:
        stress_path = resolve_path(stress.get("artifact"), project_root)
        if stress_path is None or not stress_path.exists() or stress_path.stat().st_size == 0:
            errors.append(f"stress render artifact is missing or empty: {stress.get('artifact')}")
    technical = qc.get("technical_preflight") or {}
    if technical.get("status") not in {"pending", "pass", "fail"}:
        errors.append("qc.technical_preflight.status must be pending, pass, or fail")
    if missing(technical.get("report")):
        errors.append("qc.technical_preflight.report is required")
    elif technical.get("status") == "pass" and project_root is not None:
        report_path = resolve_path(technical.get("report"), project_root)
        if report_path is None or not report_path.exists() or report_path.stat().st_size == 0:
            errors.append(f"technical preflight report is missing or empty: {technical.get('report')}")
        else:
            try:
                report_text = report_path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                errors.append(f"technical preflight report cannot be read: {exc}")
            else:
                if "RESULT: PASS" not in report_text:
                    errors.append("technical preflight report does not contain RESULT: PASS")
            if artifact_paths and report_path.stat().st_mtime < max(path.stat().st_mtime for path in artifact_paths):
                errors.append("technical preflight report is stale relative to the declared artifacts")
    if qc.get("visual_craft_verdict") not in {"pending", "ship", "revise", "reject"}:
        errors.append("qc.visual_craft_verdict must be pending, ship, revise, or reject")
    if technical.get("status") == "pass" and qc.get("visual_craft_verdict") == "pending":
        warnings.append("technical PASS is not an aesthetic verdict; visual_craft_verdict remains pending")
    for key in ("final_size_reviewed", "colour_accessibility_reviewed", "claim_trace_reviewed", "visual_craft_reviewed"):
        if key not in qc:
            errors.append(f"qc.{key} is required")
        elif qc.get(key) is not True:
            warnings.append(f"qc.{key} is not complete")
    if qc.get("visual_craft_verdict") == "ship":
        if build.get("status") != "success":
            errors.append("visual_craft_verdict ship requires build.status: success")
        if technical.get("status") != "pass":
            errors.append("visual_craft_verdict ship requires technical_preflight.status: pass")
        if stress.get("status") != "pass":
            errors.append("visual_craft_verdict ship requires qc.stress_render.status: pass")
        if profile == "revision":
            if qc.get("revision_diff_reviewed") is not True:
                errors.append("revision SHIP requires qc.revision_diff_reviewed: true")
            diff_path = resolve_path(qc.get("revision_diff_report"), project_root)
            if project_root is not None and (diff_path is None or not diff_path.exists() or diff_path.stat().st_size == 0):
                errors.append("revision SHIP requires an existing qc.revision_diff_report")
            elif diff_path is not None:
                diff_text = diff_path.read_text(encoding="utf-8", errors="replace")
                if not all(marker in diff_text for marker in (
                    "FACT: mean_absolute_error=", "FACT: changed_pixel_fraction=", "RESULT:",
                )):
                    errors.append("revision SHIP diff report is not a compare_render report")
                if artifact_paths and diff_path.stat().st_mtime < max(path.stat().st_mtime for path in artifact_paths):
                    errors.append("revision SHIP diff report is stale relative to the declared artifacts")
        for key in ("final_size_reviewed", "colour_accessibility_reviewed", "claim_trace_reviewed", "visual_craft_reviewed"):
            if qc.get(key) is not True:
                errors.append(f"visual_craft_verdict ship requires qc.{key}: true")
    return errors, warnings

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args()
    try:
        data = load_manifest(args.manifest)
        root = manifest_project_root(args.manifest.resolve(), data, args.project_root)
        errors, warnings = validate(data, root)
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
