"""Corpus-grounded Matplotlib craft system for lj-viz.

The stable layer is neutral scaffolding, typography, spacing, and line weights.
Colour is selected from a semantic namespace for the paper; there is no
official or universal "Nature palette". Exact upload requirements remain
dated facts owned by lj-journal.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
from typing import Iterator, Mapping, Sequence

import matplotlib as mpl
from matplotlib.offsetbox import AnnotationBbox, HPacker, OffsetImage, TextArea

MM_PER_INCH = 25.4

NEUTRALS = {
    "paper": "#FFFFFF",
    "ink": "#202124",
    "ink_muted": "#666A70",
    "hairline": "#B7BBC1",
    "context": "#D9DDE2",
    "context_soft": "#F0F1F3",
    "missing": "#8B9098",
}

# Ecology defaults distilled from the audited corpus and Juan's two papers,
# not publisher branding. Select one namespace and keep its meanings fixed
# across the manuscript. Do not cycle through profiles panel by panel.
PALETTE_PROFILES: dict[str, dict[str, str]] = {
    "evidence": {
        "focal": "#4477AA", "comparison": "#CCBB44",
        "positive": "#228833", "negative": "#AA3377",
    },
    "surrogacy": {
        "umbrella": "#D86B63", "keystone": "#4D79B9", "flagship": "#E0A63A",
    },
    # Juan's mint/salmon language, shifted toward blue-teal and separated in
    # luminance so it remains legible under red-green colour-vision variants.
    "portfolio": {"pair": "#2C7F8E", "singleton": "#D98570"},
    "period": {"before": "#D64D52", "after": "#57A9D8"},
    "taxonomic": {
        "taxon_1": "#30338C", "taxon_2": "#4B92C3", "taxon_3": "#8BD0E2",
        "taxon_4": "#5A1A6C", "taxon_5": "#9A65A6", "taxon_6": "#A86618",
        "taxon_7": "#E2B85E", "taxon_8": "#087C5C", "taxon_9": "#34A85A",
        "taxon_10": "#A8D35F",
    },
}

# Only pairs that are intended to be decoded against each other belong here.
# A ten-taxon palette is never promised to be pairwise CVD-safe: taxonomic
# figures must declare the critical comparisons and retain labels/position.
PALETTE_CRITICAL_PAIRS: dict[str, tuple[tuple[str, str], ...]] = {
    "evidence": (("focal", "comparison"), ("positive", "negative")),
    "surrogacy": (("umbrella", "keystone"), ("umbrella", "flagship"), ("keystone", "flagship")),
    "portfolio": (("pair", "singleton"),),
    "period": (("before", "after"),),
    "taxonomic": (),
}

# Compatibility aliases for existing scripts. New work should use NEUTRALS
# plus semantic_palette(namespace).
NATURE_ROLES = {
    **NEUTRALS,
    "signal": PALETTE_PROFILES["evidence"]["focal"],
    "signal_soft": "#C8DDE9",
    "accent": PALETTE_PROFILES["evidence"]["comparison"],
    "accent_soft": "#EED8C9",
    "positive": PALETTE_PROFILES["evidence"]["positive"],
    "negative": PALETTE_PROFILES["evidence"]["negative"],
}
NATURE_CATEGORICAL = tuple(PALETTE_PROFILES["taxonomic"].values())

SPACING_MM = {
    "hair": 1.5,
    "compact": 2.5,
    "standard": 4.0,
    "generous": 6.0,
    "section": 9.0,
}


def semantic_palette(namespace: str, overrides: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return one named semantic namespace plus stable neutral tokens."""
    if namespace not in PALETTE_PROFILES:
        allowed = ", ".join(sorted(PALETTE_PROFILES))
        raise ValueError(f"unknown palette namespace {namespace!r}; choose one of: {allowed}")
    palette = {**NEUTRALS, **PALETTE_PROFILES[namespace]}
    if overrides:
        unknown = set(overrides) - set(PALETTE_PROFILES[namespace])
        if unknown:
            raise ValueError(f"overrides introduce undeclared semantic tokens: {sorted(unknown)}")
        palette.update(overrides)
    return palette


def mm_to_inches(value_mm: float) -> float:
    return value_mm / MM_PER_INCH


def figure_size(width_mm: float = 183, height_mm: float = 110) -> tuple[float, float]:
    """Return an exact physical Matplotlib figure size in inches."""
    return mm_to_inches(width_mm), mm_to_inches(height_mm)


def nature_grid(
    fig,
    nrows: int,
    ncols: int,
    *,
    width_mm: float,
    height_mm: float,
    outer_mm: float = SPACING_MM["standard"],
    panel_mm: float = SPACING_MM["standard"],
    width_ratios: Sequence[float] | None = None,
    height_ratios: Sequence[float] | None = None,
):
    """Create a GridSpec whose physical gutters come from the Beauty Contract."""
    allowed = set(SPACING_MM.values())
    if outer_mm not in allowed or panel_mm not in allowed:
        raise ValueError("outer_mm and panel_mm must use a shared SPACING_MM token")
    if width_mm <= 2 * outer_mm or height_mm <= 2 * outer_mm:
        raise ValueError("spacing leaves no positive panel area")
    fig.set_layout_engine("constrained")
    engine = fig.get_layout_engine()
    engine.set(
        w_pad=mm_to_inches(panel_mm / 2),
        h_pad=mm_to_inches(panel_mm / 2),
        wspace=panel_mm / width_mm,
        hspace=panel_mm / height_mm,
        rect=(
            outer_mm / width_mm,
            outer_mm / height_mm,
            1 - 2 * outer_mm / width_mm,
            1 - 2 * outer_mm / height_mm,
        ),
    )
    return fig.add_gridspec(
        nrows, ncols, width_ratios=width_ratios, height_ratios=height_ratios,
    )


def canvas_grid(
    fig,
    nrows: int,
    ncols: int,
    *,
    width_mm: float,
    height_mm: float,
    outer_mm: float = SPACING_MM["standard"],
    panel_mm: float = SPACING_MM["standard"],
    width_ratios: Sequence[float] | None = None,
    height_ratios: Sequence[float] | None = None,
):
    """Create exact canvas-first axes and a serialisable millimetre layout.

    Use this for full multi-panel composition. ``nature_grid`` remains useful
    for quick/simple plots whose rendered geometry is checked afterwards.
    """
    allowed = set(SPACING_MM.values())
    if outer_mm not in allowed or panel_mm not in allowed:
        raise ValueError("outer_mm and panel_mm must use a shared SPACING_MM token")
    if nrows < 1 or ncols < 1:
        raise ValueError("nrows and ncols must be positive")
    available_w = width_mm - 2 * outer_mm - (ncols - 1) * panel_mm
    available_h = height_mm - 2 * outer_mm - (nrows - 1) * panel_mm
    if available_w <= 0 or available_h <= 0:
        raise ValueError("spacing leaves no positive panel area")
    wr = list(width_ratios or [1] * ncols)
    hr = list(height_ratios or [1] * nrows)
    if len(wr) != ncols or len(hr) != nrows or min(wr + hr) <= 0:
        raise ValueError("ratio counts must match the grid and remain positive")
    widths = [available_w * value / sum(wr) for value in wr]
    heights = [available_h * value / sum(hr) for value in hr]
    fig.set_layout_engine("none")
    axes: list[list[object]] = []
    panels: list[dict[str, float | str]] = []
    top = height_mm - outer_mm
    for row, panel_h in enumerate(heights):
        bottom = top - panel_h
        left = outer_mm
        row_axes = []
        for col, panel_w in enumerate(widths):
            axis = fig.add_axes([
                left / width_mm, bottom / height_mm,
                panel_w / width_mm, panel_h / height_mm,
            ])
            row_axes.append(axis)
            panels.append({
                "id": f"r{row + 1}c{col + 1}",
                "left_mm": round(left, 6), "bottom_mm": round(bottom, 6),
                "width_mm": round(panel_w, 6), "height_mm": round(panel_h, 6),
            })
            left += panel_w + panel_mm
        axes.append(row_axes)
        top = bottom - panel_mm
    return axes, {
        "canvas": {"width_mm": width_mm, "height_mm": height_mm},
        "outer_mm": outer_mm, "panel_mm": panel_mm, "panels": panels,
    }


def write_layout_contract(layout: Mapping[str, object], path: str | Path) -> None:
    """Write the renderer-produced geometry sidecar used by craft QC."""
    Path(path).write_text(json.dumps(layout, indent=2) + "\n", encoding="utf-8")


def mark_style(
    palette: Mapping[str, str],
    *,
    evidence_role: str,
    semantic_role: str | None = None,
) -> dict[str, object]:
    """Return transparent style tokens without hiding plotting semantics."""
    if evidence_role == "context":
        return {"color": NEUTRALS["context"], "linewidth": 0.5, "alpha": 0.7, "zorder": 1}
    if evidence_role == "reference":
        return {"color": NEUTRALS["ink_muted"], "linewidth": 0.5, "alpha": 0.9,
                "linestyle": (0, (3, 2)), "zorder": 2}
    if evidence_role not in {"focal", "comparison", "support"}:
        raise ValueError("evidence_role must be focal, comparison, support, context, or reference")
    if semantic_role is None or semantic_role not in palette:
        raise ValueError("semantic_role must name a colour in the selected paper palette")
    weights = {
        "focal": {"linewidth": 0.9, "alpha": 1.0, "zorder": 4},
        "comparison": {"linewidth": 0.75, "alpha": 0.9, "zorder": 3},
        "support": {"linewidth": 0.5, "alpha": 0.55, "zorder": 2},
    }
    return {"color": palette[semantic_role], **weights[evidence_role]}


def nature_rc() -> dict[str, object]:
    """Return scoped, deliberately quiet publication defaults."""
    return {
        "figure.facecolor": NEUTRALS["paper"],
        "figure.edgecolor": NEUTRALS["paper"],
        "figure.dpi": 110,
        "figure.constrained_layout.use": True,
        "figure.constrained_layout.h_pad": mm_to_inches(SPACING_MM["compact"]),
        "figure.constrained_layout.w_pad": mm_to_inches(SPACING_MM["compact"]),
        "figure.constrained_layout.hspace": 0.08,
        "figure.constrained_layout.wspace": 0.10,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
        "font.size": 7,
        "text.color": NEUTRALS["ink"],
        "axes.labelsize": 7,
        "axes.titlesize": 7,
        "axes.titleweight": "normal",
        "axes.titlepad": 3,
        "axes.labelpad": 2.5,
        "axes.linewidth": 0.5,
        "axes.edgecolor": NEUTRALS["ink"],
        "axes.labelcolor": NEUTRALS["ink"],
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "axes.axisbelow": True,
        # Unspecified marks stay neutral. Scientific colours are explicit
        # semantic assignments, never an accidental categorical wheel.
        "axes.prop_cycle": mpl.cycler(color=[NEUTRALS["ink"]]),
        "xtick.labelsize": 6,
        "ytick.labelsize": 6,
        "xtick.color": NEUTRALS["ink"],
        "ytick.color": NEUTRALS["ink"],
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 2.3,
        "ytick.major.size": 2.3,
        "xtick.major.width": 0.5,
        "ytick.major.width": 0.5,
        "lines.linewidth": 0.75,
        "lines.markersize": 3.0,
        "lines.markeredgewidth": 0.4,
        "patch.linewidth": 0.5,
        "legend.fontsize": 6,
        "legend.frameon": False,
        "legend.handlelength": 1.3,
        "legend.handletextpad": 0.4,
        "legend.columnspacing": 0.8,
        "legend.labelspacing": 0.3,
        "legend.borderaxespad": 0.25,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "savefig.dpi": 450,
        "savefig.bbox": "standard",
        "savefig.pad_inches": 0.03,
        "savefig.transparent": False,
        "savefig.facecolor": NEUTRALS["paper"],
        "image.cmap": "viridis",
    }


def apply_publication_theme() -> None:
    mpl.rcParams.update(nature_rc())


@contextmanager
def publication_theme(namespace: str = "evidence") -> Iterator[dict[str, str]]:
    """Apply the visual system without leaking rcParams; yield selected palette."""
    with mpl.rc_context(nature_rc()):
        yield semantic_palette(namespace)


def add_panel_label(ax, label: str, *, x: float = -0.12, y: float = 1.04) -> None:
    """Add a Nature-style lowercase, bold, 8 pt panel label."""
    ax.text(
        x, y, label, transform=ax.transAxes, ha="left", va="bottom",
        fontsize=8, fontweight="bold", color=NEUTRALS["ink"], clip_on=False,
    )


def add_icon_label(
    ax,
    rgba,
    label: str,
    xy: tuple[float, float],
    *,
    zoom: float,
    icon_side: str = "left",
    gap_mm: float = SPACING_MM["hair"],
    fontsize: float = 6,
    xycoords=None,
    box_alignment: tuple[float, float] = (0, 0.5),
):
    """Place a silhouette and label as one collision-safe compound artist.

    Pass an alpha-cropped image so zoom tracks visible ink rather than a padded
    raster canvas. The shared spacing token becomes a real, renderer-controlled
    gap; callers should not anchor independent text and icon artists by eye.
    """
    if icon_side not in {"left", "right"}:
        raise ValueError("icon_side must be 'left' or 'right'")
    if gap_mm not in set(SPACING_MM.values()):
        raise ValueError("gap_mm must use a shared SPACING_MM token")
    icon = OffsetImage(rgba, zoom=zoom, interpolation="lanczos")
    text = TextArea(label, textprops={"fontsize": fontsize, "color": NEUTRALS["ink"]})
    children = [icon, text] if icon_side == "left" else [text, icon]
    packed = HPacker(children=children, align="center", pad=0, sep=gap_mm * 72 / MM_PER_INCH)
    artist = AnnotationBbox(
        packed, xy, xycoords=xycoords or ax.transAxes, frameon=False, pad=0,
        box_alignment=box_alignment,
    )
    ax.add_artist(artist)
    return artist


def quiet_support_axis(ax) -> None:
    """Make a supporting panel quieter without hiding its scale."""
    ax.spines["left"].set_color(NEUTRALS["hairline"])
    ax.spines["bottom"].set_color(NEUTRALS["hairline"])
    ax.tick_params(colors=NEUTRALS["ink_muted"])


def style_legend(legend) -> None:
    if legend is None:
        return
    legend.set_frame_on(False)
    for item in legend.get_texts():
        item.set_color(NEUTRALS["ink_muted"])
