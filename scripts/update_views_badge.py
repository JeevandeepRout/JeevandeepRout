#!/usr/bin/env python3
"""Fetch the current profile view count and render it as a local SVG badge."""
import re
import sys
import urllib.request
from pathlib import Path

USERNAME = "JeevandeepRout"
SOURCE = f"https://komarev.com/ghpvc/?username={USERNAME}&style=flat-square"
OUT = Path("assets/profile-views.svg")

LABEL = "Profile views"
LABEL_BG = "#5b5b5b"
VALUE_BG = "#316feb"


def fetch_count() -> int:
    req = urllib.request.Request(SOURCE, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        svg = resp.read().decode("utf-8", "replace")
    # The badge contains <text> nodes for the label and the number (often twice,
    # for the shadow). Take the last purely numeric one.
    for text in reversed(re.findall(r"<text[^>]*>([^<]+)</text>", svg)):
        cleaned = text.strip().replace(",", "")
        if cleaned.isdigit():
            return int(cleaned)
    raise ValueError("Could not find a view count in the badge response")


def render(count: int) -> str:
    value = f"{count:,}"
    label_w = round(len(LABEL) * 6.4 + 12)
    value_w = round(len(value) * 7.0 + 12)
    total = label_w + value_w
    lx = label_w / 2
    vx = label_w + value_w / 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="20" role="img" aria-label="{LABEL}: {value}">
  <title>{LABEL}: {value}</title>
  <clipPath id="r"><rect width="{total}" height="20" rx="3"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_w}" height="20" fill="{LABEL_BG}"/>
    <rect x="{label_w}" width="{value_w}" height="20" fill="{VALUE_BG}"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{lx}" y="14">{LABEL}</text>
    <text x="{vx}" y="14" font-weight="bold">{value}</text>
  </g>
</svg>
"""


def main() -> int:
    try:
        count = fetch_count()
    except Exception as exc:  # keep the old badge if the service is down
        print(f"Fetch failed, keeping existing badge: {exc}", file=sys.stderr)
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(count), encoding="utf-8")
    print(f"Wrote {OUT} with count {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
