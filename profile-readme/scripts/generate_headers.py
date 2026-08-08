#!/usr/bin/env python3
"""
Builds the section-title graphics used instead of plain "## About" style
markdown headers. Each one is a small, self-contained, looping SVG:
an index tag, the title, and a line that draws itself in.

Usage:
    python generate_headers.py <output-dir>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from theme import BG, INK_0, INK_1, INK_2, INK_3, FONT_MONO  # noqa: E402

W, H = 760, 64

HEADERS = [
    {"file": "header-about.svg", "index": "01", "title": "ABOUT", "tag": "whoami"},
    {"file": "header-stack.svg", "index": "02", "title": "STACK", "tag": "tools --list"},
    {"file": "header-projects.svg", "index": "03", "title": "PROJECTS", "tag": "ls ./featured"},
    {"file": "header-connect.svg", "index": "04", "title": "CONNECT", "tag": "cat ./contact"},
]


def build_header(index: str, title: str, tag: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}"
     width="{W}" height="{H}" role="img" aria-label="{title.lower()} section">
  <defs>
    <style>
      .bg    {{ fill: {BG}; }}
      .idx   {{ font-family: {FONT_MONO}; font-size: 15px; fill: {INK_3}; }}
      .title {{
        font-family: {FONT_MONO}; font-weight: 700; font-size: 30px;
        fill: {INK_0}; letter-spacing: 3px;
      }}
      .tag   {{ font-family: {FONT_MONO}; font-size: 13px; fill: {INK_2}; }}
      .bracket {{ font-family: {FONT_MONO}; font-size: 30px; fill: {INK_3}; }}
      .line  {{ stroke: {INK_3}; stroke-width: 1; }}
      .cursor {{
        fill: {INK_1};
        animation: blink 1.1s steps(1) infinite;
      }}
      @keyframes blink {{
        0%, 49%   {{ opacity: 1; }}
        50%, 100% {{ opacity: 0; }}
      }}
      .grow {{
        stroke-dasharray: 640;
        stroke-dashoffset: 640;
        animation: draw 1.6s ease-out forwards;
      }}
      @keyframes draw {{
        to {{ stroke-dashoffset: 0; }}
      }}
    </style>
  </defs>

  <rect class="bg" x="0" y="0" width="{W}" height="{H}"/>

  <text class="idx" x="0" y="16">{index}</text>
  <text class="bracket" x="0" y="46">&#8203;</text>
  <text class="title" x="0" y="46">
    <tspan fill="{INK_3}">&lt;</tspan>{title}<tspan fill="{INK_3}">/&gt;</tspan>
  </text>
  <rect class="cursor" x="{(len(title) + 3) * 21 - 3 + 8}" y="24" width="10" height="24"/>

  <text class="tag" x="{W - 8}" y="16" text-anchor="end">{tag}</text>

  <line class="line grow" x1="0" y1="58" x2="{W}" y2="58"/>
</svg>"""


def main():
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("assets")
    out_dir.mkdir(parents=True, exist_ok=True)
    for h in HEADERS:
        svg = build_header(h["index"], h["title"], h["tag"])
        (out_dir / h["file"]).write_text(svg, encoding="utf-8")
        print(f"wrote {out_dir / h['file']}")


if __name__ == "__main__":
    main()
