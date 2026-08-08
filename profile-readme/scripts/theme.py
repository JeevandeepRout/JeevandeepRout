"""
Shared visual theme for every generated SVG in this profile.
Keeping this in one place is what makes the portrait, headers and stat
cards all look like they belong to the same page.
"""

BG = "#0b0b0c"          # near-black background
INK_0 = "#f2f2f0"       # brightest foreground (headlines, peaks of a chart)
INK_1 = "#c7c7c2"       # primary text
INK_2 = "#8d8d88"       # secondary text / labels
INK_3 = "#4a4a47"       # hairlines, faint grid
INK_4 = "#2a2a28"       # near-invisible structure lines
ACCENT = "#f2f2f0"      # monochrome "accent" = brightest ink, used sparingly

FONT_MONO = (
    "ui-monospace, 'SFMono-Regular', 'JetBrains Mono', 'Fira Code', "
    "Menlo, Consolas, monospace"
)
FONT_SANS = (
    "-apple-system, 'Segoe UI', 'Inter', 'Helvetica Neue', Arial, sans-serif"
)

# Character ramp used for the portrait, ordered light -> dark.
# Kept ASCII-only and monospace-safe.
RAMP = " .:-=+*#%@"

SVG_HEADER = (
    '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
    'viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{label}">'
)
