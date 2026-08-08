#!/usr/bin/env python3
"""
Renders a yearly contribution-activity card in the same animation style as
GitHub's own contribution graph widgets: a clip-path "wipe" reveal on the
chart line, a sweeping highlight bar, staggered number fade-ins, and a
palette that switches with the viewer's light/dark preference via
`prefers-color-scheme` -- all inside the SVG's own <style>, no JS.

Usage:
    GITHUB_TOKEN=... python generate_activity.py <username> <output-svg>
    python generate_activity.py <username> <output-svg> --demo
"""
import argparse
import datetime
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from theme import FONT_MONO  # noqa: E402

API = "https://api.github.com"
W, H = 620, 148

# Light-mode-first palette (GitHub renders README images against whatever
# scheme the *viewer* has selected, so pick sensible defaults for light and
# let the media query override for dark).
LIGHT = {"dim": "#6e7681", "mid": "#8c959f", "strong": "#1f2328", "line": "#1f2328", "wash": "#6e7681"}
DARK = {"dim": "#c9d1d9", "mid": "#8b949e", "strong": "#f0f6fc", "line": "#c9d1d9", "wash": "#c9d1d9"}


def gh_graphql(query: str, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{API}/graphql", json={"query": query}, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def fetch_live(username: str, token: str) -> dict:
    q = f"""
    query {{
      user(login: "{username}") {{
        contributionsCollection {{
          contributionCalendar {{
            totalContributions
            weeks {{ contributionDays {{ contributionCount, date }} }}
          }}
        }}
      }}
    }}
    """
    data = gh_graphql(q, token)
    cal = data["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    weekly_totals = [sum(d["contributionCount"] for d in wk["contributionDays"]) for wk in weeks]
    active_days = sum(
        1 for wk in weeks for d in wk["contributionDays"] if d["contributionCount"] > 0
    )
    return {
        "total": cal["totalContributions"],
        "active_days": active_days,
        "best_week": max(weekly_totals) if weekly_totals else 0,
        "weekly": weekly_totals,
    }


def demo_data() -> dict:
    import random

    random.seed(11)
    weekly = [random.randint(0, 12) for _ in range(52)]
    for i in (24, 25, 26):
        weekly[i] = random.randint(20, 32)  # a visible "busy month" bump
    return {
        "total": sum(weekly),
        "active_days": sum(1 for w in weekly if w > 0) * 3,  # rough stand-in for demo only
        "best_week": max(weekly),
        "weekly": weekly,
    }


def area_and_line(weekly: list[int], x0: float, y0: float, w: float, h: float):
    n = len(weekly)
    if n < 2:
        weekly = weekly + [0]
        n = 2
    lo, hi = 0, max(weekly) or 1
    step = w / (n - 1)

    pts = []
    for i, v in enumerate(weekly):
        px = x0 + i * step
        py = y0 + h - ((v - lo) / (hi - lo)) * h
        pts.append((px, py))

    line_d = "M " + "L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    area_d = line_d + f" L {pts[-1][0]:.1f} {y0 + h:.1f} L {pts[0][0]:.1f} {y0 + h:.1f} Z"
    return line_d, area_d, pts[-1]


def build_svg(d: dict, username: str) -> str:
    chart_x, chart_y, chart_w, chart_h = 0, 84, W, 56
    line_d, area_d, (end_x, end_y) = area_and_line(d["weekly"], chart_x, chart_y, chart_w, chart_h)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"
     fill="none" font-family="{FONT_MONO}" role="img" aria-label="contribution activity for {username}">
  <style>
    .dim    {{ fill: {LIGHT['dim']}; }}
    .mid    {{ fill: {LIGHT['mid']}; }}
    .strong {{ fill: {LIGHT['strong']}; }}
    .line   {{ stroke: {LIGHT['line']}; }}
    .wash   {{ fill: {LIGHT['wash']}; opacity: 0.13; }}
    .sweep  {{ fill: {LIGHT['line']}; }}
    @media (prefers-color-scheme: dark) {{
      .dim    {{ fill: {DARK['dim']}; }}
      .mid    {{ fill: {DARK['mid']}; }}
      .strong {{ fill: {DARK['strong']}; }}
      .line   {{ stroke: {DARK['line']}; }}
      .wash   {{ fill: {DARK['wash']}; opacity: 0.16; }}
      .sweep  {{ fill: {DARK['line']}; }}
    }}
  </style>

  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="0.10s" dur="0.45s" fill="freeze"/>
    <text x="0" y="50" class="strong" font-size="52" font-weight="600">{d['total']}</text>
    <text x="0" y="72" class="mid" font-size="12">contributions in the last year</text>
  </g>

  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="0.30s" dur="0.45s" fill="freeze"/>
    <text x="{W}" y="30" class="strong" font-size="19" text-anchor="end" font-weight="600">{d['active_days']}</text>
    <text x="{W}" y="47" class="mid" font-size="11" text-anchor="end">active days</text>
  </g>

  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="0.42s" dur="0.45s" fill="freeze"/>
    <text x="{W}" y="70" class="strong" font-size="19" text-anchor="end" font-weight="600">{d['best_week']}</text>
    <text x="{W}" y="87" class="mid" font-size="11" text-anchor="end">best week</text>
  </g>

  <clipPath id="reveal">
    <rect x="0" y="{chart_y}" height="{chart_h}" width="0">
      <animate attributeName="width" from="0" to="{W}" begin="0.50s" dur="1.3s" fill="freeze"/>
    </rect>
  </clipPath>

  <g clip-path="url(#reveal)">
    <path d="{area_d}" class="wash"/>
    <path d="{line_d}" class="line" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
  </g>

  <rect y="{chart_y}" width="2" height="{chart_h}" class="sweep" opacity="0">
    <animate attributeName="x" from="0" to="{W}" begin="0.50s" dur="1.3s" fill="freeze"/>
    <set attributeName="opacity" to="0.55" begin="0.50s"/>
    <set attributeName="opacity" to="0" begin="1.80s"/>
  </rect>

  <circle cx="{end_x:.1f}" cy="{end_y:.1f}" r="4.5" class="strong" stroke="currentColor" stroke-width="2" opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="1.80s" dur="0.35s" fill="freeze"/>
  </circle>
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
