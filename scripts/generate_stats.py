#!/usr/bin/env python3
"""
Pulls a handful of numbers about a GitHub account from the REST/GraphQL
API and renders them as small animated SVG cards (bars count up, a spark
line traces itself). No external image services -- just data in, SVG out.

Usage:
    GITHUB_TOKEN=... python generate_stats.py <username> <output-dir>

If GITHUB_TOKEN is not set, or the API can't be reached, it falls back to
--demo data so the README still renders (useful for local previews and
for the very first commit before Actions has a token wired up).
"""
import argparse
import datetime
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from theme import BG, INK_0, INK_1, INK_2, INK_3, FONT_MONO  # noqa: E402

API = "https://api.github.com"
W, H = 760, 190


def gh_get(path: str, token: str | None, params=None):
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(f"{API}{path}", headers=headers, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def gh_graphql(query: str, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{API}/graphql", json={"query": query}, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def fetch_live(username: str, token: str) -> dict:
    user = gh_get(f"/users/{username}", token)
    repos = gh_get(f"/users/{username}/repos", token, params={"per_page": 100, "type": "owner"})

    stars = sum(r.get("stargazers_count", 0) for r in repos)
    forks = sum(r.get("forks_count", 0) for r in repos)
    langs: dict[str, int] = {}
    for r in repos:
        if r.get("language"):
            langs[r["language"]] = langs.get(r["language"], 0) + 1
    top_langs = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:5]

    contrib_weeks = []
    try:
        q = f"""
        query {{
          user(login: "{username}") {{
            contributionsCollection {{
              contributionCalendar {{
                totalContributions
                weeks {{ contributionDays {{ contributionCount }} }}
              }}
            }}
          }}
        }}
        """
        gdata = gh_graphql(q, token)
        cal = gdata["user"]["contributionsCollection"]["contributionCalendar"]
        total_contribs = cal["totalContributions"]
        for wk in cal["weeks"][-24:]:
            days = wk["contributionDays"]
            contrib_weeks.append(sum(d["contributionCount"] for d in days))
    except Exception:
        total_contribs = 0
        contrib_weeks = []

    return {
        "followers": user.get("followers", 0),
        "public_repos": user.get("public_repos", 0),
        "stars": stars,
        "forks": forks,
        "contributions": total_contribs,
        "top_langs": top_langs,
        "spark": contrib_weeks or [0],
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
    }


def demo_data() -> dict:
    import random

    random.seed(7)
    return {
        "followers": 128,
        "public_repos": 34,
        "stars": 512,
        "forks": 61,
        "contributions": 1867,
        "top_langs": [("Python", 14), ("TypeScript", 9), ("Rust", 5), ("Go", 3), ("Shell", 2)],
        "spark": [random.randint(2, 40) for _ in range(24)],
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
    }


def bar_row(label: str, value: int, max_value: int, y: int, delay: float) -> str:
    max_w = 250
    frac = 0 if max_value == 0 else value / max_value
    target_w = max(2, round(max_w * frac))
    return f"""
    <text class="lbl" x="0" y="{y}">{label}</text>
    <rect class="track" x="150" y="{y - 11}" width="{max_w}" height="10" rx="2"/>
    <rect class="bar" x="150" y="{y - 11}" width="{target_w}" height="10" rx="2"
          style="animation-delay:{delay}s"/>
    <text class="val" x="{150 + max_w + 12}" y="{y}">{value:,}</text>"""


def sparkline(points: list[int], x0: int, y0: int, w: int, h: int) -> str:
    if not points:
        points = [0]
    lo, hi = min(points), max(points)
    span = (hi - lo) or 1
    n = len(points)
    step = w / max(1, n - 1)
    coords = []
    for i, p in enumerate(points):
        px = x0 + i * step
        py = y0 + h - ((p - lo) / span) * h
        coords.append((px, py))
    path_d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    last_x, last_y = coords[-1]
    length = int(w * 1.6) + 40
    return f"""
    <path class="spark" d="{path_d}" style="stroke-dasharray:{length};stroke-dashoffset:{length};"/>
    <circle class="spark-dot" cx="{last_x:.1f}" cy="{last_y:.1f}" r="3"/>"""


def build_svg(d: dict, username: str) -> str:
    max_bar = max(d["followers"], d["public_repos"], d["stars"], d["forks"], 1)
    rows = [
        bar_row("followers", d["followers"], max_bar, 34, 0.0),
        bar_row("repos", d["public_repos"], max_bar, 58, 0.1),
        bar_row("stars", d["stars"], max_bar, 82, 0.2),
        bar_row("forks", d["forks"], max_bar, 106, 0.3),
    ]
    langs_line = "  ".join(f"{name} {count}" for name, count in d["top_langs"][:3]) or "n/a"
    spark = sparkline(d["spark"], 0, 0, 250, 40)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}"
     width="{W}" height="{H}" role="img" aria-label="live GitHub stats for {username}">
  <defs>
    <style>
      .bg     {{ fill: {BG}; }}
      .lbl    {{ font-family: {FONT_MONO}; font-size: 12px; fill: {INK_2}; }}
      .val    {{ font-family: {FONT_MONO}; font-size: 12px; fill: {INK_0}; }}
      .track  {{ fill: {INK_3}; opacity: 0.35; }}
      .bar    {{
        fill: {INK_0};
        transform-box: fill-box;
        transform-origin: left;
        transform: scaleX(0);
        animation: grow 1s ease-out forwards;
      }}
      @keyframes grow {{ to {{ transform: scaleX(1); }} }}
      .spark {{
        fill: none; stroke: {INK_1}; stroke-width: 1.6;
        animation: draw 2.2s ease-out forwards;
      }}
      @keyframes draw {{ to {{ stroke-dashoffset: 0; }} }}
      .spark-dot {{
        fill: {INK_0};
        animation: pulse 1.8s ease-in-out infinite;
      }}
      @keyframes pulse {{
        0%, 100% {{ r: 3; opacity: 1; }}
        50%      {{ r: 5; opacity: 0.5; }}
      }}
      .meta {{ font-family: {FONT_MONO}; font-size: 11px; fill: {INK_3}; }}
      .head {{ font-family: {FONT_MONO}; font-size: 12px; fill: {INK_2}; letter-spacing: 1px; }}
      .divider {{ stroke: {INK_3}; stroke-width: 1; opacity: 0.5; }}
    </style>
  </defs>

  <rect class="bg" x="0" y="0" width="{W}" height="{H}" rx="10"/>

  <g transform="translate(20, 26)">{''.join(rows)}</g>

  <line class="divider" x1="470" y1="14" x2="470" y2="{H - 14}"/>

  <g transform="translate(490, 24)">
    <text class="head" x="0" y="0">CONTRIBUTIONS / 24 WEEKS</text>
    <g transform="translate(0, 16)">{spark}</g>
    <text class="meta" x="0" y="78">total: {d['contributions']:,}</text>
    <text class="meta" x="0" y="96">{langs_line}</text>
  </g>

  <text class="meta" x="20" y="{H - 14}">updated {d['generated']} UTC &#183; refreshed daily via GitHub Actions</text>
</svg>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("username")
    ap.add_argument("output", help="path to write stats.svg")
    ap.add_argument("--demo", action="store_true", help="use synthetic data, skip the API")
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
