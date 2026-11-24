# Species silhouettes and paper-level visual vocabulary

Use this reference when organisms recur across panels or figures, or when a broad-audience mechanism,
food-web, sampling, movement or conservation diagram benefits from rapid taxon recognition. It is not
specific to surrogate-species studies. A snow-leopard paper, community comparison, trophic mechanism or
monitoring workflow may all use the same contract.

## Evidence boundary

Nature's official guidance allows icons only when they clarify a real system or process and warns against
superfluous or ambiguous icons. It does **not** require species silhouettes. The recommendation below is a
corpus-grounded craft rule: many broad-audience ecology figures use a restrained silhouette plus a text
label as a redundant identity channel. The silhouette must help decoding; it is not decoration.

PhyloPic is the preferred first source because it exposes taxon links, vector files, contributor and a
per-image Creative Commons licence through its official API. Licences vary by image. Never assume that
"from PhyloPic" means CC0: older CC BY, BY-SA and non-commercial images remain in the collection.

Official sources:

- <https://www.phylopic.org/>
- <https://www.phylopic.org/articles/image-usage>
- <https://api-docs.phylopic.org/v2/index.html>

## One paper, one visual language

Create `visual-vocabulary.yaml` at paper scope from `assets/visual-vocabulary.example.yaml` before drawing
the second figure. Treat semantic channels as namespaces:

- **entity identity** — scientific/common label plus a fixed silhouette or symbol;
- **analytical role** — one named semantic colour namespace such as treatment, period, portfolio or index;
- **condition or intervention** — marker, line type, boundary or texture when needed;
- **quantity** — position, length, area or colour value with named units and scale.

The rule is not "every species always gets a colour". If colour encodes treatment or evidence role, keep
species silhouettes neutral ink and use the same silhouette + label for identity. If colour itself encodes
taxon identity, that mapping must remain fixed across the complete paper. One visual channel should not
quietly change semantic jobs between figures.

For every recurring entity lock its label, scientific name, registry ID, orientation, fill/stroke logic and
optical treatment. A silhouette's displayed area must not imply abundance, body size or effect magnitude
unless that quantitative encoding is explicit. Keep a text label whenever a non-specialist could confuse
the outline.

The dominant craft grammar in the audited figures and Juan's two papers is **small and repeated**, not a
single large animal mascot. Place silhouettes above aligned categories, beside rows, at direct labels, or in
a compact process diagram. Start at 5–9 mm optical height at final size, then adjust only for recognisability.
Align feet/baselines for terrestrial mammals and visual centrelines for birds/fish; normalize visible ink,
not merely the SVG bounding box, so a long tail or horn does not make one category look quantitatively larger.

For first-pass reliability, alpha-crop transparent padding before measuring, then treat the visible silhouette
and its text label as one compound unit with a 1.5 mm gap. Do not place them with independent `x/y` anchors.
Test the compound at final size, grayscale, and the smallest intended output. If an exact asset is not
recognisable by outline at 9 mm, use text plus a neutral symbol or a broader disclosed taxon icon; do not keep
enlarging it until it becomes a mascot. When several species form a row, align visible feet/centrelines and
equalise optical ink height before distributing horizontal space.

## Taxonomic fallback hierarchy

Use this order and stop at the first defensible asset:

1. exact accepted species;
2. an exact taxonomic synonym mapped to the accepted species;
3. genus-level or generic guild silhouette, labelled at that broader level;
4. a near relative only as an explicitly disclosed schematic approximation;
5. neutral geometric symbol + text when the approximation would mislead.

A similar species may never be labelled as the focal species. For any non-exact asset, record both
`intended_taxon` and `depicted_taxon`, set `match_level`, set `approximation_disclosed: true`, and state a
`fallback_reason` in the registry and caption/legend when relevant. Do not use a substitute where diagnostic
morphology, body form, size or phylogenetic identity is part of the evidence.

## Curated assets, not a mirror

`assets/silhouettes/registry.yaml` is a small approved library, not a local mirror of PhyloPic. Add an asset
only when a real figure needs it. Prefer an exact CC0 or commercially reusable CC BY vector; do not bundle
NC material for journal publication without explicit rights review. Preserve the downloaded SVG unchanged,
record its SHA-256 hash, image/node UUID, exact licence URL, creator and verification date.

If the art is cropped, simplified, flipped or otherwise edited, keep the source file separately, mark
`modified: true`, describe the change, and follow the image's licence/attribution requirements. Copy approved
assets into a project's figure directory rather than editing the canonical registry file in place.

Run the registry check after adding or replacing an asset:

```bash
python3 scripts/validate_silhouette_registry.py assets/silhouettes/registry.yaml
```

Keep SVG as the canonical publication asset. When a plotting library cannot place SVG directly, generate a
transparent, final-size PNG derivative with the already-supported PyMuPDF route; record the command and the
source SVG hash in figure provenance:

```bash
python3 scripts/render_silhouette.py \
  assets/silhouettes/panthera-uncia__phylopic-cb44ff49.svg \
  /path/to/figure/assets/snow-leopard.png --width-mm 18 --dpi 600
```

This derivative is for programmatic placement or preview. Prefer the original SVG in the final vector
assembly whenever the chosen toolchain supports it. Do not silently install an SVG package merely to place
the icon.

The bundled snow-leopard asset is an exact `Panthera uncia` vector by Margot Michaud from PhyloPic, released
under CC0 1.0. Credit is not legally required, but the registry retains a recommended credit for scientific
provenance.
