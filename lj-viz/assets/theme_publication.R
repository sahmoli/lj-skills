# Corpus-grounded ggplot2 craft system for lj-viz.
# Neutrals/spacing are stable. Colour comes from one paper-level semantic
# namespace; these are ecology defaults, not publisher branding.

nature_neutrals <- c(
  paper = "#FFFFFF", ink = "#202124", ink_muted = "#666A70",
  hairline = "#B7BBC1", context = "#D9DDE2", context_soft = "#F0F1F3",
  missing = "#8B9098"
)

nature_palette_profiles <- list(
  evidence = c(focal = "#4477AA", comparison = "#CCBB44", positive = "#228833", negative = "#AA3377"),
  surrogacy = c(umbrella = "#D86B63", keystone = "#4D79B9", flagship = "#E0A63A"),
  portfolio = c(pair = "#2C7F8E", singleton = "#D98570"),
  period = c(before = "#D64D52", after = "#57A9D8"),
  taxonomic = c(
    taxon_1 = "#30338C", taxon_2 = "#4B92C3", taxon_3 = "#8BD0E2",
    taxon_4 = "#5A1A6C", taxon_5 = "#9A65A6", taxon_6 = "#A86618",
    taxon_7 = "#E2B85E", taxon_8 = "#087C5C", taxon_9 = "#34A85A", taxon_10 = "#A8D35F"
  )
)

semantic_palette <- function(namespace = "evidence", overrides = NULL) {
  if (!namespace %in% names(nature_palette_profiles)) {
    stop(sprintf("unknown palette namespace: %s", namespace))
  }
  profile <- nature_palette_profiles[[namespace]]
  if (!is.null(overrides)) {
    unknown <- setdiff(names(overrides), names(profile))
    if (length(unknown) > 0) {
      stop(sprintf("overrides introduce undeclared semantic tokens: %s", paste(unknown, collapse = ", ")))
    }
    profile[names(overrides)] <- overrides
  }
  c(nature_neutrals, profile)
}

# Compatibility aliases for existing scripts.
nature_colours <- c(
  nature_neutrals,
  signal = nature_palette_profiles$evidence[["focal"]],
  signal_soft = "#C8DDE9",
  accent = nature_palette_profiles$evidence[["comparison"]],
  accent_soft = "#EED8C9",
  positive = nature_palette_profiles$evidence[["positive"]],
  negative = nature_palette_profiles$evidence[["negative"]]
)
nature_categorical <- unname(nature_palette_profiles$taxonomic)
nature_spacing_mm <- c(hair = 1.5, compact = 2.5, standard = 4, generous = 6, section = 9)

nature_mark_style <- function(evidence_role, semantic_role = NULL, palette = semantic_palette()) {
  if (evidence_role == "context") {
    return(list(colour = nature_neutrals[["context"]], linewidth = 0.5 * 0.3528, alpha = 0.7))
  }
  if (evidence_role == "reference") {
    return(list(colour = nature_neutrals[["ink_muted"]], linewidth = 0.5 * 0.3528,
                alpha = 0.9, linetype = "dashed"))
  }
  if (!evidence_role %in% c("focal", "comparison", "support")) {
    stop("evidence_role must be focal, comparison, support, context, or reference")
  }
  if (is.null(semantic_role) || !semantic_role %in% names(palette)) {
    stop("semantic_role must name a colour in the selected paper palette")
  }
  weights <- list(
    focal = list(linewidth = 0.9 * 0.3528, alpha = 1),
    comparison = list(linewidth = 0.75 * 0.3528, alpha = 0.9),
    support = list(linewidth = 0.5 * 0.3528, alpha = 0.55)
  )
  c(list(colour = unname(palette[[semantic_role]])), weights[[evidence_role]])
}

nature_canvas_positions <- function(nrows, ncols, width_mm, height_mm,
                                    outer_mm = nature_spacing_mm[["standard"]],
                                    panel_mm = nature_spacing_mm[["standard"]],
                                    width_ratios = rep(1, ncols),
                                    height_ratios = rep(1, nrows)) {
  allowed <- unname(nature_spacing_mm)
  if (!outer_mm %in% allowed || !panel_mm %in% allowed) stop("spacing must use shared mm tokens")
  available_w <- width_mm - 2 * outer_mm - (ncols - 1) * panel_mm
  available_h <- height_mm - 2 * outer_mm - (nrows - 1) * panel_mm
  if (available_w <= 0 || available_h <= 0) stop("spacing leaves no positive panel area")
  widths <- available_w * width_ratios / sum(width_ratios)
  heights <- available_h * height_ratios / sum(height_ratios)
  result <- list(); top <- height_mm - outer_mm; index <- 1
  for (row in seq_len(nrows)) {
    bottom <- top - heights[[row]]; left <- outer_mm
    for (col in seq_len(ncols)) {
      result[[index]] <- data.frame(
        id = sprintf("r%dc%d", row, col),
        x = left / width_mm, y = bottom / height_mm,
        width = widths[[col]] / width_mm, height = heights[[row]] / height_mm
      )
      left <- left + widths[[col]] + panel_mm; index <- index + 1
    }
    top <- bottom - panel_mm
  }
  do.call(rbind, result)
}

nature_canvas_grob <- function(grobs, positions) {
  if (length(grobs) != nrow(positions)) stop("one position is required per grob")
  children <- lapply(seq_along(grobs), function(index) {
    row <- positions[index, ]
    grid::grobTree(grobs[[index]], vp = grid::viewport(
      x = row$x, y = row$y, width = row$width, height = row$height,
      just = c("left", "bottom")
    ))
  })
  do.call(grid::grobTree, children)
}

compound_icon_label_grob <- function(icon_grob, label, icon_side = "left", gap_mm = 1.5,
                                     fontsize = 6, colour = nature_neutrals[["ink"]]) {
  if (!icon_side %in% c("left", "right")) stop("icon_side must be left or right")
  if (!gap_mm %in% unname(nature_spacing_mm)) stop("gap_mm must use a shared spacing token")
  text <- grid::textGrob(label, gp = grid::gpar(fontsize = fontsize, col = colour), just = "left")
  spacer <- grid::nullGrob()
  grobs <- if (icon_side == "left") list(icon_grob, spacer, text) else list(text, spacer, icon_grob)
  widths <- if (icon_side == "left") {
    grid::unit.c(grid::grobWidth(icon_grob), grid::unit(gap_mm, "mm"), grid::grobWidth(text))
  } else {
    grid::unit.c(grid::grobWidth(text), grid::unit(gap_mm, "mm"), grid::grobWidth(icon_grob))
  }
  gtable::gtable_row("icon-label", grobs, widths = widths)
}

pick_nature_family <- function(candidates = c("Arial", "Helvetica", "Liberation Sans", "DejaVu Sans")) {
  if (requireNamespace("systemfonts", quietly = TRUE)) {
    for (candidate in candidates) {
      match <- tryCatch(systemfonts::match_font(candidate), error = function(e) NULL)
      if (!is.null(match) && nzchar(match$path)) return(candidate)
    }
  }
  "sans"
}

theme_publication <- function(base_size = 7, base_family = pick_nature_family(), grid = "none") {
  stopifnot(base_size >= 5, base_size <= 7, grid %in% c("none", "y"))
  grid_y <- if (grid == "y") {
    ggplot2::element_line(colour = nature_neutrals[["context_soft"]], linewidth = 0.25 * 0.3528)
  } else {
    ggplot2::element_blank()
  }

  ggplot2::theme_classic(base_size = base_size, base_family = base_family) +
    ggplot2::theme(
      text = ggplot2::element_text(colour = nature_neutrals[["ink"]]),
      axis.line = ggplot2::element_line(colour = nature_neutrals[["ink"]], linewidth = 0.5 * 0.3528),
      axis.ticks = ggplot2::element_line(colour = nature_neutrals[["ink"]], linewidth = 0.5 * 0.3528),
      axis.ticks.length = grid::unit(2.3, "pt"),
      axis.title.x = ggplot2::element_text(margin = ggplot2::margin(t = 2.5)),
      axis.title.y = ggplot2::element_text(margin = ggplot2::margin(r = 2.5)),
      axis.text = ggplot2::element_text(size = base_size - 1),
      panel.grid.major.y = grid_y,
      panel.grid.major.x = ggplot2::element_blank(),
      panel.grid.minor = ggplot2::element_blank(),
      panel.spacing = grid::unit(nature_spacing_mm[["standard"]], "mm"),
      plot.margin = ggplot2::margin(4, 4, 4, 4, unit = "mm"),
      plot.title = ggplot2::element_blank(),
      plot.subtitle = ggplot2::element_blank(),
      strip.background = ggplot2::element_blank(),
      strip.text = ggplot2::element_text(face = "plain", margin = ggplot2::margin(b = 1.5)),
      legend.position = "top",
      legend.justification = "left",
      legend.box.just = "left",
      legend.key = ggplot2::element_blank(),
      legend.key.width = grid::unit(4, "mm"),
      legend.key.height = grid::unit(3, "mm"),
      legend.spacing.x = grid::unit(1.5, "mm"),
      legend.margin = ggplot2::margin(0, 0, 1.5, 0),
      legend.title = ggplot2::element_blank()
    )
}

scale_colour_nature <- function(namespace = "evidence", values = NULL, ...) {
  if (is.null(values)) values <- nature_palette_profiles[[namespace]]
  ggplot2::scale_colour_manual(values = values, ...)
}

scale_fill_nature <- function(namespace = "evidence", values = NULL, ...) {
  if (is.null(values)) values <- nature_palette_profiles[[namespace]]
  ggplot2::scale_fill_manual(values = values, ...)
}
