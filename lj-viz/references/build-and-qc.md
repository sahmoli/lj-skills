# Build and QC contract

## 1. Choose an effort profile

- **quick** — style/placement repair of an existing figure with no change to claim, data, estimand,
  encoding or scales. Use `assets/quick-manifest.example.yaml`, compare to the baseline, and stop if the fix
  would require scientific redesign.
- **full** — new figure or material redesign. Establish the figure, reference, visual, and data contracts
  that the change needs, then render and inspect the affected output.
- **revision** — a bounded response to reviewer/editor feedback. Record baseline artifact, exact request,
  allowed changes and preserved invariants; report the visual diff and any scientific consequence.

Profile is orthogonal to `design | build | audit`: it controls effort and required evidence, not whether code
is executed.

## 2. Workspace and dependency check

Inspect existing scripts, data, environment files, and output conventions before generating code. Reuse the
project's language and dependency manager. Do not install plotting packages silently. State missing optional
packages and either use a simpler available route or stop with a precise requirement.

New builds default to:

```text
outputs/figures/<figure-id>/
  figure-manifest.yaml
  visual-vocabulary.yaml        # for a figure set or recurring entities
  assets/                       # copied, provenance-recorded vectors
  <figure-id>.R | <figure-id>.py
  <figure-id>.pdf
  <figure-id>.svg
  <figure-id>.png
  preflight.txt
```

Do not overwrite existing artifacts without explicit authorisation. When editing an established pipeline,
preserve its paths instead of creating this directory merely for conformity.

Use the shared publication theme when it suits the project's visual system, or record an equivalent project
theme and its provenance. Do not assume the skill repository is on Python's module path or R's working
directory. Current journal requirements and readable final size override a generic style default.

For a figure set, copy `assets/visual-vocabulary.example.yaml` once at paper scope. When taxa recur, select
only vetted vectors from `assets/silhouettes/registry.yaml`, copy the SVG into the project directory, and
retain registry ID, taxon match, licence, creator and SHA-256. Validate the canonical registry after any
addition:

```bash
python3 /path/to/lj-viz/scripts/validate_silhouette_registry.py \
  /path/to/lj-viz/assets/silhouettes/registry.yaml
```

If the current plotting stack cannot place SVG, use `scripts/render_silhouette.py` to make a transparent
PNG derivative at the declared physical width and DPI. Keep and cite the SVG as canonical; do not treat the
derivative as a new source asset.

For full Python composites, use `canvas_grid(...)`, then write its returned layout with
`write_layout_contract(...)`. This fixes exact axes boxes and gutters before marks are drawn. Use
`nature_grid(...)` for quick/simple plots whose final geometry will be measured after export. R uses
`nature_canvas_positions()` and `nature_canvas_grob()` for the same canvas-first contract. The ggplot2 theme
remains a safe single-plot floor, not a compound-layout engine.

## 3. Manifest lifecycle

Copy `assets/figure-manifest.example.yaml`, replace every placeholder, and validate before rendering:

```bash
python3 /path/to/lj-viz/scripts/validate_manifest.py figure-manifest.yaml
```

After the command succeeds, set `build.status: success`, list actual artifacts, and mark only QC checks that
were performed. Relative paths resolve from the manifest directory unless `project_root` or the explicit
`--project-root` override says otherwise; current shell working directory is irrelevant. A non-zero command
or missing/stale output sets `build.status: failed`; the validator verifies
that every artifact named by a successful build exists, is non-empty, and is not older than local code/data.

For quick repair:

```bash
python3 /path/to/lj-viz/scripts/validate_quick_manifest.py quick-manifest.yaml
```

Query the audited corpus before locking a full Reference Board, then validate exact hits:

```bash
python3 /path/to/lj-viz/scripts/query_reference_board.py --query "gradient uncertainty small multiples"
python3 /path/to/lj-viz/scripts/query_reference_board.py --check-manifest figure-manifest.yaml
```

Audit the declared semantic palette before rendering:

```bash
python3 /path/to/lj-viz/scripts/audit_palette.py figure-manifest.yaml
```

This checks exact sRGB contrast and declared critical comparison pairs under protanopia, deuteranopia and
tritanopia simulation. It does not prove that a rendered figure is accessible or that colour carries the
intended hierarchy. `--builtin` regression-tests the shipped namespaces.

## 4. Output strategy

- Prefer editable vector PDF/SVG for plots and schematics.
- Embed high-resolution raster imagery inside vector assembly when needed.
- Produce PNG for rapid visual review.
- Produce TIFF only when the current venue contract requests it.
- Set physical dimensions at export, not by later scaling in a manuscript editor.
- Preserve editable text and embed fonts where the format supports it.

The theme assets are the one canonical Nature-level visual system, not universal journal skins.
`lj-journal` supplies live export fields when a venue requires a technical override; it must not fork the
palette, spacing, hierarchy, legend or icon language.

## 5. Deterministic preflight

Run:

```bash
python3 /path/to/lj-viz/scripts/preflight_figure.py figure.pdf --manifest figure-manifest.yaml
```

For a multipage manuscript PDF, `audit_layout.py` requires an explicit page selection; an unselected
multipage file is never reported as checked. SVG physical dimensions are compared to the manifest rather
than inferred from `viewBox` alone.

The PDF preflight imports `audit_layout.py` and fails on material text/text overlap, text/small-icon overlap,
or text extending outside the page. It warns on less than 1.5 mm text–icon clearance and labels within
the declared edge clearance (1.5 mm in the default contract). Run it on the final PDF, not only the PNG preview. These geometric checks cannot
see whether text overlaps a vector data point or whether an icon is semantically recognisable; pixel review
still owns those decisions.

The scripts can verify manifest and Beauty Contract completeness, conditional bar baselines, uncertainty definitions, EPSG:3857
misuse, arbitrary jitter, artifact existence, physical PDF size, small PDF text, embedded-raster effective
DPI, vector strokes outside 0.25–1 pt, some font-embedding signals, SVG dimensions/text nodes, raster pixel/DPI metadata, plus coarse rendered
facts for edge crowding, visual density and material saturated-colour clusters.

They cannot establish that the claim is scientifically valid, samples are independent, intervals were
computed correctly, colour meaning is appropriate, or panels form a valid evidence chain. Those require
source inspection and pixel review.

## 6. Review pack, pixel review and visual regression

Generate a standard review pack from the final PDF:

```bash
python3 /path/to/lj-viz/scripts/render_review_sheet.py figure.pdf review/ --layout layout-contract.json
python3 /path/to/lj-viz/scripts/craft_metrics.py figure.pdf --layout layout-contract.json --json-out craft.json
```

The review pack can include whole-composition and detail views, grayscale, relevant CVD simulations, and a
print-size view. `craft_metrics.py` verifies safe geometry and reports font/stroke tiers; it explicitly
does not certify hierarchy, density, optical balance, legend economy or icon recognition.

Alternatively render the final artifact, not an earlier preview:

```bash
pdftoppm -singlefile -png -r 180 figure.pdf /tmp/figure-final
```

Inspect at approximately its final physical width. Check hierarchy, text, symbols, overlaps, clipping,
legend decoding, panel order, colour/greyscale distinction, map privacy, and whether the claimed effect is
visually findable within two seconds. Check repeated gutters against the declared millimetre scale; verify
that panel area is earned by evidence, context/support marks do not dominate, and titles have not become
dashboard headlines. Remove redundant legends; inspect every semantic icon for purpose, optical size, style
consistency and provenance. Prefer small repeated silhouette grammar to a large mascot.

Generate an accessibility contact sheet:

```bash
python3 /path/to/lj-viz/scripts/render_cvd_preview.py figure.png figure-cvd.png
```

For a previously human-approved template, run a tolerance-based regression and inspect the diff:

```bash
python3 /path/to/lj-viz/scripts/compare_render.py approved.png figure.png --diff figure-diff.png
```

A snapshot `PASS` means only “within the declared pixel tolerance”; it does not prove the baseline is good.
Never update a baseline merely to make a test green. For a paper set, compare figures side by side against
`visual-vocabulary.yaml`: entity, colour meaning, symbol, order, units and terminology drift is a ship defect.
Re-run after every material code change.

For a new layout where labels, icons, or colour might conceal a defect, use a stress render before the
production render:

1. **stress render** — monochrome, longest labels/statistics, real icon assets, final canvas and gutters;
2. **production render** — data and colour after the stress render has no clipping or placement failure.

After production export, use the geometry audit and the declared label strategy when those risks are present.
This converts deterministic failures into code before the artifact is shown to the user.
When a manifest is present, small embedded images are checked as icons only when
`visual_design.icons.mode: semantic`; this prevents ordinary microscopy or photograph panels from being
misclassified. Standalone audits use a conservative size heuristic because they lack that semantic context.
The review sheet must include narrow panel-boundary strips: isolated panel crops can conceal labels that
cross a gutter. When a layout sidecar is available, compare the actual rendered text envelope with every
non-owner panel rectangle; sidecar-to-sidecar geometry alone is insufficient.

## 7. Repair loop and stop rule

Repair the smallest code/configuration source of each red gate, regenerate, re-run preflight, and inspect
again. If the same defect remains or a metric worsens after consecutive attempts, revise the panel
architecture, legend mode, label policy, or canvas contract; do not call it ship. Continue while a
verifiable repair remains. Stop successfully when:

- the build command succeeds and outputs are current;
- manifest and deterministic checks have no FAIL, recorded only as `technical PASS`; the named report must
  exist, contain PASS and be newer than the artifact it certifies;
- a new or materially reworked layout has a real stress artifact; quick/revision work compares an available
  baseline when the changed property makes that comparison informative;
- actual pixels have no red issue among the faithfulness, readability, hierarchy, spacing, colour, legend,
  or icon properties affected by the work;
- a separate visual-craft verdict is `ship` only when the requested artifact and comparison scope call for
  a ship decision;
- remaining unknowns are listed as `⚠待核` with the evidence needed to resolve them.

Stop only when the Beauty Contract is visibly met. Then avoid unbounded taste iteration: additional polish
must fix a named reader task or craft defect.
