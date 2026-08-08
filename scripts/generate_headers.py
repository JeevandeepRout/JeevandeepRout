#!/usr/bin/env python3
"""
Minimal section headers: a bold label followed by a horizontal rule that
runs to the right edge. Matches the reference: 620x26, no bracket/cursor
decoration, adaptive light/dark via prefers-color-scheme. No embedded
font -- the system monospace stack it falls back to looks effectively
identical and keeps the file tiny.

Usage:
    python generate_headers.py <output-dir>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from theme import FONT_MONO  # noqa: E402

W, H = 620, 26
FONT_SIZE = 16
CHAR_W = FONT_SIZE * 0.6   # monospace advance estimate
GAP = 18                   # space between label text and the rule

LIGHT = {"label": "#424a53", "rule": "#d8dee4"}
DARK = {"label": "#f0f6fc", "rule": "#30363d"}

HEADERS = [
    {"file": "header-about.svg", "label": "about"},
    {"file": "header-stack.svg", "label": "stack"},
    {"file": "header-projects.svg", "label": "projects"},
    {"file": "header-stats.svg", "label": "stats"},
    {"file": "header-thoughts-things.svg", "label": "thoughts & things"},
]


def escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def build_header(label: str) -> str:
    text_w = len(label) * CHAR_W
    line_x1 = text_w + GAP
    safe_label = escape(label)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"
     fill="none" font-family="{FONT_MONO}" role="img" aria-label="{safe_label} section">
  <style>
    .label {{ fill: {LIGHT['label']}; }}
    .rule  {{ stroke: {LIGHT['rule']}; }}
    @media (prefers-color-scheme: dark) {{
      .label {{ fill: {DARK['label']}; }}
      .rule  {{ stroke: {DARK['rule']}; }}
    }}
  </style>
  <text x="0" y="18" class="label" font-size="{FONT_SIZE}" font-weight="600">{safe_label}</text>
  <line x1="{line_x1:.0f}" y1="12.5" x2="{W}" y2="12.5" class="rule" stroke-width="1"/>
</svg>"""


def main():
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("assets")
    out_dir.mkdir(parents=True, exist_ok=True)
    for h in HEADERS:
        svg = build_header(h["label"])
        (out_dir / h["file"]).write_text(svg, encoding="utf-8")
        print(f"wrote {out_dir / h['file']}")


if __name__ == "__main__":
    main()
