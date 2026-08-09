#!/usr/bin/env python3
"""
Two big numbers: current streak and longest streak (in consecutive days
with at least one contribution), each with its date range underneath.
Same fade-in + divider treatment as the other cards.

Usage:
    GITHUB_TOKEN=... python generate_streak.py <username> <output-svg>
    python generate_streak.py <username> <output-svg> --demo
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
W, H = 620, 96
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

LIGHT = {"num": "#424a53", "muted": "#8c959f", "rule": "#d8dee4"}
DARK = {"num": "#f0f6fc", "muted": "#8b949e", "rule": "#30363d"}


def gh_graphql(query: str, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{API}/graphql", json={"query": query}, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def fetch_live(username: str, token: str) -> list[tuple[datetime.date, int]]:
    q = f"""
    query {{
      user(login: "{username}") {{
        contributionsCollection {{
          contributionCalendar {{
            weeks {{ contributionDays {{ contributionCount, date }} }}
          }}
        }}
      }}
    }}
    """
    data = gh_graphql(q, token)
    weeks = data["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [
        (datetime.date.fromisoformat(d["date"]), d["contributionCount"])
        for wk in weeks
        for d in wk["contributionDays"]
    ]
    days.sort(key=lambda x: x[0])
    return days


def demo_data() -> list[tuple[datetime.date, int]]:
    import random

    random.seed(3)
    today = datetime.date.today()
    days = []
    # a 21-day streak back in Jan 25 - Feb 14 (matching the reference's own
    # example numbers), then sparser activity since, ending on a gap.
    start = datetime.date(today.year, 1, 25)
    for i in range(21):
        days.append((start + datetime.timedelta(days=i), random.randint(1, 6)))
    d = start + datetime.timedelta(days=21)
    days.append((d, 0))  # force a clean break so the streak ends exactly at 21
    d += datetime.timedelta(days=1)
    while d < today:
        days.append((d, random.randint(0, 4) if random.random() > 0.4 else 0))
        d += datetime.timedelta(days=1)
    days.append((today - datetime.timedelta(days=1), 0))
    days.append((today, 0))
    return days


def fmt(d: datetime.date) -> str:
    return f"{MONTHS[d.month - 1]} {d.day}"


def compute_streaks(days: list[tuple[datetime.date, int]]):
    longest_len = 0
    longest_range = None
    run_start = None
    run_len = 0
    prev_date = None

    for date, count in days:
        active = count > 0
        if active:
            if run_len == 0:
                run_start = date
            run_len += 1
            prev_date = date
            if run_len > longest_len:
                longest_len = run_len
                longest_range = (run_start, prev_date)
        else:
            run_len = 0
            run_start = None

    current_len = 0
    current_range = None
    for date, count in reversed(days):
        if count > 0:
            current_len += 1
            if current_range is None:
                current_range = [date, date]
            current_range[0] = date
        else:
            break

    return {
        "current_len": current_len,
        "current_range": tuple(current_range) if current_range else None,
        "longest_len": longest_len,
        "longest_range": longest_range,
    }


def build_svg(s: dict, username: str) -> str:
    cur_sub = f"{fmt(s['current_range'][0])} \u2013 {fmt(s['current_range'][1])}" if s["current_range"] else "\u2014"
    long_sub = f"{fmt(s['longest_range'][0])} \u2013 {fmt(s['longest_range'][1])}" if s["longest_range"] else "\u2014"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none"
     font-family="{FONT_MONO}" role="img" aria-label="contribution streaks for {username}">
  <style>
    .num  {{ fill: {LIGHT['num']}; }}
    .muted{{ fill: {LIGHT['muted']}; }}
    .rule {{ stroke: {LIGHT['rule']}; }}
    @media (prefers-color-scheme: dark) {{
      .num  {{ fill: {DARK['num']}; }}
      .muted{{ fill: {DARK['muted']}; }}
      .rule {{ stroke: {DARK['rule']}; }}
    }}
  </style>

  <line x1="310" y1="16" x2="310" y2="80" class="rule" stroke-width="1" opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="0.20s" dur="0.45s" fill="freeze"/>
  </line>

  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="0.12s" dur="0.45s" fill="freeze"/>
    <text x="34" y="44" class="num" font-size="34" font-weight="600">{s['current_len']}</text>
    <text x="34" y="64" class="muted" font-size="11">current streak</text>
    <text x="34" y="80" class="muted" font-size="10">{cur_sub}</text>
  </g>

  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="0.26s" dur="0.45s" fill="freeze"/>
    <text x="344" y="44" class="num" font-size="34" font-weight="600">{s['longest_len']}</text>
    <text x="344" y="64" class="muted" font-size="11">longest streak</text>
    <text x="344" y="80" class="muted" font-size="10">{long_sub}</text>
  </g>
</svg>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("username")
    ap.add_argument("output")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if args.demo or not token:
        days = demo_data()
    else:
        try:
            days = fetch_live(args.username, token)
        except Exception as e:
            print(f"warning: live fetch failed ({e}), falling back to demo data", file=sys.stderr)
            days = demo_data()

    streaks = compute_streaks(days)
    svg = build_svg(streaks, args.username)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(svg, encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
