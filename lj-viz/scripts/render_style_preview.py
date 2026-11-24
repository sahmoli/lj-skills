#!/usr/bin/env python3
"""Render a deliberately weak baseline and a corpus-grounded craft preview.

The data are deterministic and synthetic. The preview tests visual grammar,
not a scientific result and not compliance with a publisher specification.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import fitz
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
THEME_PATH = ROOT / "assets" / "theme_publication.py"
SILHOUETTE_PATH = ROOT / "assets" / "silhouettes" / "panthera-uncia__phylopic-cb44ff49.svg"


def load_theme():
    spec = importlib.util.spec_from_file_location("ljviz_theme", THEME_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load theme_publication.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def silhouette_rgba(path: Path, width_px: int = 1200) -> np.ndarray:
    document = fitz.open(path)
    page = document[0]
    scale = width_px / page.rect.width
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=True)
    image = Image.frombytes("RGBA", (pixmap.width, pixmap.height), pixmap.samples)
    document.close()
    alpha = np.asarray(image)[:, :, 3]
    rows, cols = np.where(alpha > 4)
    if len(rows):
        image = image.crop((cols.min(), rows.min(), cols.max() + 1, rows.max() + 1))
    return np.asarray(image)


def old_preview(path: Path, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite {path}; pass --force")
    rng = np.random.default_rng(2)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), facecolor="#F4F7FA")
    fig.suptitle("Why a paired-species portfolio can improve conservation outcomes", fontsize=22, weight="bold")
    colours = ["#0B7285", "#F08C00", "#2F9E44"]
    for index, ax in enumerate(axes):
        x = np.arange(10)
        ax.plot(x, rng.normal(index, 0.3, 10).cumsum(), lw=3, color=colours[index])
        ax.set_title(("Evidence overview", "Mechanism", "Implication")[index], fontsize=15, weight="bold")
        ax.grid(True, color="white", linewidth=2)
        ax.set_facecolor("#E9EEF3")
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def craft_preview(path: Path, *, force: bool, stress: bool = False) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite {path}; pass --force")
    theme = load_theme()
    portfolio = theme.semantic_palette("portfolio")
    pair_colour = portfolio["ink"] if stress else portfolio["pair"]
    singleton_colour = portfolio["ink_muted"] if stress else portfolio["singleton"]
    pair_context = portfolio["context"] if stress else pair_colour
    singleton_context = portfolio["context"] if stress else singleton_colour
    context_alpha = 0.55 if stress else 0.24
    silhouette = silhouette_rgba(SILHOUETTE_PATH)
    rng = np.random.default_rng(11)

    width_mm, height_mm = 183, 96
    with theme.publication_theme("portfolio"):
        fig = plt.figure(figsize=theme.figure_size(width_mm, height_mm))
        axes, layout = theme.canvas_grid(
            fig, 1, 3, width_mm=width_mm, height_mm=height_mm,
            outer_mm=9, panel_mm=4, width_ratios=[1.35, 0.92, 1.05],
        )
        ax_a, ax_b, ax_c = axes[0]
        for panel, panel_id in zip(layout["panels"], ("a", "b", "c")):
            panel["id"] = panel_id

        # a — dense trajectories with stable pair/singleton colour language.
        alpha = np.linspace(0, 1.5, 60)
        pair_curves = []
        single_curves = []
        for index in range(10):
            # Leave a genuine, declared annotation band above rank 2.5; the
            # compound silhouette-label must not mask a trajectory.
            pair = 2.7 + index * 0.20 + 2.05 * alpha + rng.normal(0, 0.035, len(alpha))
            single = 10.0 + index * 0.25 - 2.5 * alpha + rng.normal(0, 0.035, len(alpha))
            pair_curves.append(pair)
            single_curves.append(single)
            ax_a.plot(alpha, pair, color=pair_context, alpha=context_alpha, lw=0.55, ls="-")
            ax_a.plot(alpha, single, color=singleton_context, alpha=context_alpha, lw=0.55, ls=(0, (3, 2)))
        pair_mid = np.mean(pair_curves, axis=0)
        single_mid = np.mean(single_curves, axis=0)
        ax_a.plot(alpha, pair_mid, color=pair_colour, lw=0.9, ls="-")
        ax_a.plot(alpha, single_mid, color=singleton_colour, lw=0.9, ls=(0, (3, 2)))
        ax_a.axvline(0.82, color=portfolio["hairline"], lw=0.5, ls=(0, (2, 2)))
        ax_a.text(0.82, 2.5, "α*", ha="center", va="bottom", fontsize=6)
        ax_a.set(xlabel="Cost-scaling exponent, α", ylabel="Portfolio rank", xlim=(0, 1.5), ylim=(1, 14))
        ax_a.yaxis.set_label_coords(-0.07, 0.5)
        ax_a.invert_yaxis()
        theme.add_icon_label(
            ax_a, silhouette, "Snow leopard", (0.04, 0.955),
            zoom=0.032, gap_mm=1.5, fontsize=6, box_alignment=(0, 0.5),
        )
        theme.add_panel_label(ax_a, "a", x=-0.08, y=1.02)

        # b — compact comparison using the same paper-level colour namespace.
        rows = np.array([4, 3, 2, 1, 0])
        labels = ["Snow leopard", "Kiang", "Pallas's cat", "Blue sheep", "Gazelle"]
        values = {
            "pair": [0.86, 0.76, 0.71, 0.80, 0.66],
            "singleton": [0.58, 0.51, 0.47, 0.61, 0.43],
        }
        for row, pair_value, singleton_value, label in zip(
            rows, values["pair"], values["singleton"], labels,
        ):
            ax_b.hlines(row, singleton_value, pair_value, color=portfolio["context"], lw=0.5, zorder=1)
            ax_b.text(0.02, row, label, ha="left", va="center", fontsize=6, color=portfolio["ink"])
        for role, estimates in values.items():
            y = rows
            if role == "pair":
                ax_b.scatter(estimates, y, s=18, color=pair_colour, edgecolor="white",
                             linewidth=0.35, zorder=3)
            else:
                ax_b.scatter(estimates, y, s=18, facecolor="white", edgecolor=singleton_colour,
                             linewidth=0.65, zorder=3)
        ax_b.set(xlabel="Composite effectiveness", xlim=(0, 1), yticks=[], ylim=(-0.42, 4.42))
        legend_handles = [
            Line2D([0], [0], color=pair_colour, lw=0.75, ls="-", marker="o",
                   markersize=3.3, markerfacecolor=pair_colour, markeredgewidth=0.35),
            Line2D([0], [0], color=singleton_colour, lw=0.75, ls=(0, (3, 2)), marker="o",
                   markersize=3.3, markerfacecolor="white", markeredgecolor=singleton_colour,
                   markeredgewidth=0.65),
        ]
        legend = fig.legend(legend_handles, ["Pair", "Singleton"],
                            loc="upper center", bbox_to_anchor=(0.5, 0.98), ncol=2,
                            handletextpad=0.2, columnspacing=0.8)
        theme.style_legend(legend)
        theme.add_panel_label(ax_b, "b", x=-0.08, y=1.02)

        # c — relationship test; colour remains the same paper-level namespace.
        x_pair = rng.uniform(0.08, 0.92, 24)
        x_single = rng.uniform(0.08, 0.92, 18)
        y_pair = 0.24 + 0.58 * x_pair + rng.normal(0, 0.085, len(x_pair))
        y_single = 0.33 + 0.22 * x_single + rng.normal(0, 0.085, len(x_single))
        ax_c.scatter(x_pair, y_pair, s=11, color=pair_colour, alpha=0.72,
                     edgecolor="white", linewidth=0.3)
        ax_c.scatter(x_single, y_single, s=10, facecolor="white", edgecolor=singleton_colour,
                     linewidth=0.65)
        for x, y, colour, line_style in (
            (x_pair, y_pair, pair_colour, "-"),
            (x_single, y_single, singleton_colour, (0, (3, 2))),
        ):
            slope, intercept = np.polyfit(x, y, 1)
            xx = np.array([0.08, 0.92])
            ax_c.plot(xx, intercept + slope * xx, color=colour, lw=0.75, ls=line_style)
        ax_c.set(xlabel="Habitat complementarity", ylabel="Umbrella gain", xlim=(0, 1), ylim=(0.12, 0.96))
        theme.add_panel_label(ax_c, "c", x=-0.08, y=1.02)

        fig.savefig(path, dpi=300, facecolor="white", bbox_inches=None)
        if not stress:
            fig.savefig(path.with_suffix(".pdf"), facecolor="white", bbox_inches=None)
            fig.savefig(path.with_suffix(".svg"), facecolor="white", bbox_inches=None)
            theme.write_layout_contract(layout, path.with_name("layout-contract.json"))
        plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    old_path = args.output_dir / "lj-viz-before.png"
    stress_path = args.output_dir / "lj-viz-stress.png"
    new_path = args.output_dir / "lj-viz-corpus-craft.png"
    old_preview(old_path, force=args.force)
    craft_preview(stress_path, force=args.force, stress=True)
    craft_preview(new_path, force=args.force)
    print(old_path)
    print(stress_path)
    print(new_path)
    print(new_path.with_suffix(".pdf"))
    print(new_path.with_suffix(".svg"))
    print(new_path.with_name("layout-contract.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
