# Ecology implementation exemplars

Reuse the evidence architecture and guardrails, never the published data or decorative styling. All snippets
assume the Figure Contract has already defined columns, repeating units, estimand, and uncertainty.

Before running a snippet, copy the corresponding theme asset from `lj-viz/assets/` beside the plotting script,
set the working directory to the project root, and create the manifest/output directory declared by the build
contract. The bare `import`/`source()` below is intentionally local and must not depend on an installed skill path.
Select the Reference Board first. These snippets implement marks; they do not choose composition or taste.

## 1. Effect estimates against a null — Python

Use for intervention/model coefficients. A zero baseline is a scientific reference, not a bar baseline.

```python
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from theme_publication import apply_publication_theme, semantic_palette

apply_publication_theme()
colours = semantic_palette("evidence")
df = pd.read_csv("data/effects.csv")  # term, estimate, lo, hi
fig, ax = plt.subplots(figsize=(89 / 25.4, 62 / 25.4))
y = range(len(df))
ax.errorbar(df["estimate"], y, xerr=[df["estimate"]-df["lo"], df["hi"]-df["estimate"]],
            fmt="o", color=colours["focal"], ecolor=colours["hairline"], capsize=2)
ax.axvline(0, color=colours["hairline"], lw=0.6, ls="--")
ax.set(yticks=list(y), yticklabels=df["term"], xlabel="Effect (95% CI)")
fig.savefig("outputs/figures/fig-effect/fig-effect.pdf")
fig.savefig("outputs/figures/fig-effect/fig-effect.png", dpi=450)
```

## 2. Repeated gradient trajectories — R

Use aligned facets when the scientific task is comparing trajectory shape. The ribbon must be defined in
the manifest (for example 95% model CI), not described merely as “uncertainty”.

```r
library(ggplot2)
source("theme_publication.R")
d <- read.csv("data/trajectories.csv") # x, estimate, lo, hi, attribute, group
pal <- semantic_palette("evidence")
p <- ggplot(d, aes(x, estimate, colour = group, fill = group)) +
  geom_ribbon(aes(ymin = lo, ymax = hi), alpha = 0.16, colour = NA) +
  geom_line(linewidth = 0.34) + # ggplot2 linewidth is mm; 0.34 mm is about 0.96 pt
  facet_wrap(~attribute, scales = "fixed") +
  scale_colour_manual(values = c(Control = pal[["ink_muted"]], Treatment = pal[["focal"]])) +
  scale_fill_manual(values = c(Control = pal[["context"]], Treatment = pal[["focal"]])) +
  labs(x = "Gradient", y = "Estimated response", colour = NULL, fill = NULL) +
  theme_publication()
ggsave("outputs/figures/fig-gradient/fig-gradient.pdf", p, width = 183, height = 105, units = "mm")
ggsave("outputs/figures/fig-gradient/fig-gradient.png", p, width = 183, height = 105, units = "mm", dpi = 450)
```

## 3. Before/after distributions — R

Use raw points or distribution summaries when independent units are available. Pair lines only when the
same independent unit is observed twice; never imply pairing from aggregated samples.

```r
library(ggplot2)
source("theme_publication.R")
d <- read.csv("data/before-after.csv") # period, response, independent_id
pal <- semantic_palette("period")
p <- ggplot(d, aes(period, response, colour = period)) +
  geom_boxplot(width = 0.45, outlier.shape = NA, linewidth = 0.3) +
  geom_jitter(width = 0.08, alpha = 0.45, size = 0.7) +
  scale_colour_manual(values = c(Before = pal[["before"]], After = pal[["after"]])) +
  labs(x = NULL, y = "Response (unit)", colour = NULL) + theme_publication() +
  theme(legend.position = "none")
ggsave("outputs/figures/fig-before-after/fig-before-after.pdf", p, width = 89, height = 70, units = "mm")
```

## 4. Global area/density map without Web Mercator — R

Use Equal Earth for global area comparison. Aggregate sensitive records before plotting; do not jitter
coordinates. A grid is illustrative—the privacy/resolution rule must come from governance and ecology.

```r
library(sf)
library(ggplot2)
source("theme_publication.R")
records <- st_read("data/restricted-occurrences.gpkg", quiet = TRUE)
world <- st_read("data/world.gpkg", quiet = TRUE)
target <- "EPSG:8857" # Equal Earth; suitable for global area comparison
records <- st_transform(records, target)
world <- st_transform(world, target)
grid <- st_make_grid(world, cellsize = 100000, square = TRUE)
counts <- lengths(st_intersects(grid, records))
cells <- st_sf(count = counts, geometry = grid[counts > 0])
p <- ggplot() + geom_sf(data = world, fill = nature_colours[["context_soft"]],
                        colour = nature_colours[["hairline"]], linewidth = 0.15) +
  geom_sf(data = cells, aes(fill = count), colour = NA) +
  scale_fill_viridis_c(trans = "sqrt", name = "Records\nper governed cell") +
  coord_sf(datum = NA) + theme_publication() +
  theme(axis.line = element_blank(), axis.ticks = element_blank(), axis.text = element_blank(),
        axis.title = element_blank())
ggsave("outputs/figures/fig-map/fig-map.pdf", p, width = 183, height = 95, units = "mm")
```

## 5. Scenario trade-off small multiples — Python

Use common axes and stable scenario semantics. Do not connect unordered categories as if they were time.

```python
import pandas as pd
import matplotlib.pyplot as plt
from theme_publication import apply_publication_theme, semantic_palette

apply_publication_theme()
df = pd.read_csv("data/scenarios.csv")  # scenario, pressure, biodiversity, region
regions = list(dict.fromkeys(df["region"]))
scenario_colours = semantic_palette("evidence")
# This mapping is part of the paper contract; replace keys/roles deliberately.
scenario_role = {"baseline": "comparison", "restoration": "positive", "pressure": "negative"}
fig, axes = plt.subplots(1, len(regions), sharex=True, sharey=True,
                         figsize=(183 / 25.4, 58 / 25.4))
for ax, region in zip(axes, regions):
    part = df[df["region"] == region]
    for scenario, group in part.groupby("scenario", sort=False):
        ax.scatter(group["pressure"], group["biodiversity"], label=scenario,
                   color=scenario_colours[scenario_role[scenario]], s=14)
    ax.set_title(region)
    ax.axhline(0, color="0.75", lw=0.6)
axes[0].set_ylabel("Biodiversity change")
for ax in axes: ax.set_xlabel("Pressure / cost")
axes[-1].legend(frameon=False, title=None)
fig.savefig("outputs/figures/fig-tradeoff/fig-tradeoff.pdf")
```

## 6. Observed-versus-predicted validation — Python

Use a 1:1 line to make calibration the task. Equal aspect/limits matter; a regression line alone can hide
bias. Repeated cross-validation folds are not automatically independent biological `n`.

```python
import pandas as pd
import matplotlib.pyplot as plt
from theme_publication import apply_publication_theme, semantic_palette

apply_publication_theme()
colours = semantic_palette("evidence")
d = pd.read_csv("data/validation.csv")  # observed, predicted, split
lo = min(d["observed"].min(), d["predicted"].min())
hi = max(d["observed"].max(), d["predicted"].max())
fig, ax = plt.subplots(figsize=(70 / 25.4, 70 / 25.4))
ax.scatter(d["observed"], d["predicted"], s=10, alpha=0.55, color=colours["focal"])
ax.plot([lo, hi], [lo, hi], color=colours["hairline"], lw=0.7, ls="--")
ax.set(xlim=(lo, hi), ylim=(lo, hi), xlabel="Observed", ylabel="Predicted", aspect="equal")
fig.savefig("outputs/figures/fig-validation/fig-validation.pdf")
```

## 7. Coverage routes for common ecology plots

These are decision routes, not extra universal templates:

- **NMDS/ordination** — show site scores and declared grouping/gradient; expose stress, distance choice, and
  fitted-variable status in caption/manifest. Ellipses need a defined target and level; do not treat visual
  separation as a test.
- **Rarefaction/coverage** — put sample coverage or effort on the comparison axis when richness is the target;
  distinguish interpolation from extrapolation and define the interval-generating procedure.
- **Small-n independent units** — show every independent unit and any pairing; do not multiply `n` by technical
  replicates or use jitter that visually hides duplicated values.
- **Effort-aware time series** — map/raw effort belongs beside or behind the estimated trend when observation
  opportunity changes. A smooth line is not a substitute for effort correction, change-point justification, or
  uncertainty about the time-varying estimate.
