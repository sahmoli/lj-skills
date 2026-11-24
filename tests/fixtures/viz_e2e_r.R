# Synthetic gradient build fixture for lj-viz.
args <- commandArgs(trailingOnly = TRUE)
out <- args[[1]]
library(ggplot2)
full_args <- commandArgs(trailingOnly = FALSE)
script_arg <- sub("^--file=", "", full_args[grep("^--file=", full_args)])
source(file.path(dirname(normalizePath(script_arg)),
                 "..", "..", "lj-viz", "assets", "theme_publication.R"))
d <- expand.grid(year = 1:10, treatment = c("Control", "Treatment"))
d$estimate <- 0.2 * d$year + ifelse(d$treatment == "Treatment", 0.6, 0)
d$lo <- d$estimate - 0.2
d$hi <- d$estimate + 0.2
p <- ggplot(d, aes(year, estimate, colour = treatment, fill = treatment)) +
  geom_ribbon(aes(ymin = lo, ymax = hi), alpha = 0.15, colour = NA) +
  geom_line(linewidth = 0.34) +
  scale_colour_manual(values = c(Control = nature_colours[["ink_muted"]], Treatment = nature_colours[["signal"]])) +
  scale_fill_manual(values = c(Control = nature_colours[["context"]], Treatment = nature_colours[["signal_soft"]])) +
  theme_publication(base_family = "Helvetica") +
  labs(x = "Year", y = "Estimated response", colour = NULL, fill = NULL)
# Use the base PDF device in the fixture: Cairo is an optional system dependency
# and this test verifies lj-viz's build/preflight contract, not a specific renderer.
ggsave(out, p, width = 89, height = 70, units = "mm", device = grDevices::pdf)
