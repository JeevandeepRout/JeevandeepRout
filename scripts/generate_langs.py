#!/usr/bin/env python3
"""
Two-column "top languages" card: left ranked by bytes of code across all
repos, right ranked by number of repos per primary language. Same
clip-path wipe + sweeping highlight animation as the other cards.

Usage:
    GITHUB_TOKEN=... python generate_langs.py <username> <output-svg>
    python generate_langs.py <username> <output-svg> --demo
"""
import argparse
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from theme import FONT_MONO  # noqa: E402

API = "https://api.github.com"
W, H = 620, 142
ROW_H = 22
BAR_H = 7
BAR_MAX_W = 152.0
RADIUS = 3
TOP_N = 5

LIGHT = {"dim": "#6e7681", "label": "#424a53", "muted": "#8c959f"}
DARK = {"dim": "#c9d1d9", "label": "#f0f6fc", "muted": "#8b949e"}


def gh_get(path: str, token: str | None, params=None):
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(f"{API}{path}", headers=headers, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def fetch_live(username: str, token: str) -> dict:
    repos = gh_get(f"/users/{username}/repos", token, params={"per_page": 100, "type": "owner"})
    repos = [r for r in repos if not r.get("fork")]

    by_repos: dict[str, int] = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            by_repos[lang] = by_repos.get(lang, 0) + 1

    by_bytes: dict[str, int] = {}
    for r in repos:
        try:
            langs = gh_get(f"/repos/{username}/{r['name']}/languages", token)
        except Exception:
            continue
        for lang, n in langs.items():
            by_bytes[lang] = by_bytes.get(lang, 0) + n

    return {"by_bytes": by_bytes, "by_repos": by_repos}


def demo_data() -> dict:
    return {
        "by_bytes": {"Python": 210_000, "TypeScript": 162_000, "Rust": 43_000, "Liquid": 33_000, "JavaScript": 24_000},
        "by_repos": {"Python": 6, "TypeScript": 3, "Liquid": 1, "Rust": 1},
    }


def rounded_bar(x0: float, y0: float, width: float, height: float, radius: float) -> str:
    radius = min(radius, width / 2) if width > 0 else 0
    x_end = x0 + width
    x_flat = x_end - radius
    return (
        f"M{x0:.1f} {y0:.1f}H{x_flat:.1f}"
        f"Q{x_end:.1f} {y0:.1f} {x_end:.1f} {y0 + radius:.1f}"
        f"V{y0 + height - radius:.1f}"
        f"Q{x_end:.1f} {y0 + height:.1f} {x_flat:.1f} {y0 + height:.1f}"
        f"H{x0:.1f}Z"
    )


def column(entries: list[tuple[str, float]], label: str, col_x: float, delay0: float, clip_id: str) -> str:
    top = sorted(entries, key=lambda kv: kv[1], reverse=True)[:TOP_N]
    total = sum(v for _, v in entries) or 1
    max_v = top[0][1] if top else 1
    bar_x = col_x + 82
    val_x = col_x + 272
    parts = [
        f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{delay0:.2f}s" '
        f'dur="0.45s" fill="freeze"/>'
        f'<text x="{col_x}" y="12" class="m-f" font-size="9" letter-spacing="1.3">{label}</text></g>'
    ]
    parts.append(
        f'<clipPath id="{clip_id}"><rect x="{bar_x}" y="20" height="{H - 32}" width="0">'
        f'<animate attributeName="width" from="0" to="{BAR_MAX_W}" begin="{delay0 + 0.14:.2f}s" '
        f'dur="0.95s" fill="freeze"/></rect></clipPath>'
    )
    for i, (name, value) in enumerate(top):
        row_y = 34 + i * ROW_H
        bar_y = row_y - 8
        pct = round(100 * value / total)
        bar_w = BAR_MAX_W * (value / max_v)
        d = rounded_bar(bar_x, bar_y, bar_w, BAR_H, RADIUS)
        row_delay = delay0 + 0.10 + i * 0.05
        parts.append(
            f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{row_delay:.2f}s" '
            f'dur="0.45s" fill="freeze"/>'
            f'<text x="{col_x}" y="{row_y}" class="e-f" font-size="11">{name.lower()}</text>'
            f'<text x="{val_x}" y="{row_y}" class="m-f" font-size="11" text-anchor="end">{pct}%</text></g>'
            f'<g clip-path="url(#{clip_id})"><path d="{d}" class="d-f"/></g>'
        )
    sweep_delay = delay0 + 0.14
    sweep_end = sweep_delay + 0.95
    parts.append(
        f'<rect y="20" width="2" height="{H - 32}" class="d-f" opacity="0">'
        f'<animate attributeName="x" from="{bar_x}" to="{bar_x + BAR_MAX_W}" begin="{sweep_delay:.2f}s" '
        f'dur="0.95s" fill="freeze"/>'
        f'<set attributeName="opacity" to="0.55" begin="{sweep_delay:.2f}s"/>'
        f'<set attributeName="opacity" to="0" begin="{sweep_end:.2f}s"/></rect>'
    )
    return "".join(parts)


def build_svg(d: dict, username: str) -> str:
    col1 = column(list(d["by_bytes"].items()), "BY BYTES", 34, 0.10, "rl0")
    col2 = column(list(d["by_repos"].items()), "BY REPOS", 342, 0.20, "rl1")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none"
     font-family="{FONT_MONO}" role="img" aria-label="top languages for {username}">
  <style>
    .d-f {{ fill: {LIGHT['dim']}; }}
    .e-f {{ fill: {LIGHT['label']}; }}
    .m-f {{ fill: {LIGHT['muted']}; }}
    @media (prefers-color-scheme: dark) {{
      .d-f {{ fill: {DARK['dim']}; }}
      .e-f {{ fill: {DARK['label']}; }}
      .m-f {{ fill: {DARK['muted']}; }}
    }}
  </style>
  {col1}
  {col2}
</svg>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("username")
    ap.add_argument("output")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if args.demo or not token:
        data = demo_data()
    else:
        try:
            data = fetch_live(args.username, token)
        except Exception as e:
            print(f"warning: live fetch failed ({e}), falling back to demo data", file=sys.stderr)
            data = demo_data()

    svg = build_svg(data, args.username)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(svg, encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
