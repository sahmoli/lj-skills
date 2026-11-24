#!/usr/bin/env python3
"""Synthetic centred-effect build fixture for lj-viz."""
import sys
import importlib.util
from pathlib import Path
import matplotlib.pyplot as plt

theme_path = Path(__file__).resolve().parents[2] / "lj-viz" / "assets" / "theme_publication.py"
spec = importlib.util.spec_from_file_location("ljviz_theme", theme_path)
theme = importlib.util.module_from_spec(spec)
spec.loader.exec_module(theme)

out = sys.argv[1]
estimate = [-0.28, -0.06, 0.19]
lo = [-0.42, -0.18, 0.04]
hi = [-0.12, 0.07, 0.34]
y = [0, 1, 2]
with theme.publication_theme():
    fig, ax = plt.subplots(figsize=theme.figure_size(89, 70))
    ax.errorbar(estimate, y, xerr=[[a-b for a, b in zip(estimate, lo)], [a-b for a, b in zip(hi, estimate)]],
                fmt="o", color=theme.NATURE_ROLES["signal"],
                ecolor=theme.NATURE_ROLES["hairline"], capsize=2)
    ax.axvline(0, color=theme.NATURE_ROLES["hairline"], linewidth=0.7, linestyle="--")
    ax.set(yticks=y, yticklabels=["Treatment", "Climate", "Interaction"], xlabel="Effect (95% CI)")
    fig.savefig(out, bbox_inches=None)
    plt.close(fig)
