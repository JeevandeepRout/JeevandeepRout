#!/usr/bin/env python3
"""
A year of contributions rendered as a character-ramp heatmap (same
character-density idea as the portrait, applied to the contribution
calendar instead of a photo): one row per weekday, one character per
week, each row wipes in with a clip-path, same as the other cards.

Usage:
    GITHUB_TOKEN=... python generate_year.py <username> <output-svg>
    python generate_year.py <username> <output-svg> --demo
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
W, H = 620, 147
CHART_X = 34
CHART_W = 574.0     # pixel span the character rows wipe across when full
ROW_H = 11
ROW0_Y = 44.0
RAMP = " :+#@"       # 5 levels, light -> dense, matches the reference legend
WEEKDAY_LABELS = {1: "mon", 3: "wed", 5: "fri"}
MONTH_NAMES = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

LIGHT = {"dim": "#6e7681", "muted": "#8c959f"}
DARK = {"dim": "#c9d1d9", "muted": "#8b949e"}


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
            weeks {{ contributionDays {{ contributionCount, date, weekday }} }}
          }}
        }}
      }}
    }}
    """
    data = gh_graphql(q, token)
    cal = data["user"]["contributionsCollection"]["contributionCalendar"]
    return {"weeks": cal["weeks"], "total": cal["totalContributions"]}


def demo_data() -> dict:
    import random

    random.seed(42)
    today = datetime.date.today()
    start = today - datetime.timedelta(days=364)
    start -= datetime.timedelta(days=(start.weekday() + 1) % 7)  # back up to a Sunday

    weeks = []
    cur = start
    week = []
    while cur <= today:
        weekday = (cur.weekday() + 1) % 7  # 0=Sun .. 6=Sat, to match GitHub's convention
        base = random.random()
        if base < 0.35:
            count = 0
        elif base < 0.6:
            count = random.randint(1, 3)
        elif base < 0.85:
            count = random.randint(4, 8)
        else:
            count = random.randint(9, 16)
        week.append({"contributionCount": count, "date": cur.isoformat(), "weekday": weekday})
        if weekday == 6 or cur == today:
            weeks.append({"contributionDays": week})
            week = []
        cur += datetime.timedelta(days=1)

    total = sum(d["contributionCount"] for wk in weeks for d in wk["contributionDays"])
    return {"weeks": weeks, "total": total}


def char_for(count: int, thresholds: list[int]) -> str:
    if count <= 0:
        return RAMP[0]
    for i, t in enumerate(thresholds):
        if count <= t:
            return RAMP[i + 1]
    return RAMP[-1]


def build_rows(weeks: list[dict]):
    all_counts = sorted(
        d["contributionCount"] for wk in weeks for d in wk["contributionDays"] if d["contributionCount"] > 0
    )
    if all_counts:
        n = len(all_counts)
        thresholds = [
            all_counts[min(n - 1, int(n * 0.35))],
            all_counts[min(n - 1, int(n * 0.60))],
            all_counts[min(n - 1, int(n * 0.85))],
        ]
    else:
        thresholds = [1, 2, 3]

    rows = {wd: [] for wd in range(7)}
    month_marks = []  # (week_index, month_name)
    seen_months = set()
    for wi, wk in enumerate(weeks):
        for d in wk["contributionDays"]:
            wd = d["weekday"]
            rows[wd].append(char_for(d["contributionCount"], thresholds))
            date = datetime.date.fromisoformat(d["date"])
            key = (date.year, date.month)
            if date.day <= 7 and key not in seen_months:
                seen_months.add(key)
                month_marks.append((wi, MONTH_NAMES[date.month - 1]))

    row_strings = {wd: "".join(chars) for wd, chars in rows.items()}
    active_days = sum(
        1 for wk in weeks for d in wk["contributionDays"] if d["contributionCount"] > 0
    )
    total_days = min(365, sum(len(wk["contributionDays"]) for wk in weeks))
    return row_strings, month_marks, active_days, total_days


def build_svg(data: dict, username: str) -> str:
    row_strings, month_marks, active_days, total_days = build_rows(data["weeks"])
    max_len = max(len(s) for s in row_strings.values()) or 1
    px_per_char = CHART_W / max_len

    row_svgs = []
    for wd in range(7):
        s = row_strings[wd]
        y_top = ROW0_Y + wd * ROW_H
        y_text = y_top + 8.6
        width = px_per_char * len(s)
        delay = 0.30 + wd * 0.07
        clip_id = f"ry{wd}"
        row_svgs.append(
            f'<clipPath id="{clip_id}"><rect x="{CHART_X}" y="{y_top:.1f}" height="{ROW_H}" width="0">'
            f'<animate attributeName="width" from="0" to="{width:.1f}" begin="{delay:.2f}s" dur="0.40s" fill="freeze"/>'
            f'</rect></clipPath>'
            f'<g clip-path="url(#{clip_id})">'
            f'<text xml:space="preserve" x="{CHART_X}" y="{y_text:.1f}" class="d-f" font-size="9.2">{s}</text></g>'
        )
        if wd in WEEKDAY_LABELS:
            row_svgs.append(
                f'<text x="{CHART_X - 7}" y="{y_text:.1f}" class="m-f" font-size="9" text-anchor="end">'
                f'{WEEKDAY_LABELS[wd]}</text>'
            )

    month_svgs = []
    for wi, name in month_marks:
        x = CHART_X + wi * px_per_char
        month_svgs.append(f'<text x="{x:.1f}" y="{ROW0_Y + 7 * ROW_H + 6:.1f}" class="m-f" font-size="9">{name}</text>')

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none"
     font-family="{FONT_MONO}" role="img" aria-label="contribution calendar for {username}, last 12 months">
  <style>
    .d-f {{ fill: {LIGHT['dim']}; }}
    .m-f {{ fill: {LIGHT['muted']}; }}
    @media (prefers-color-scheme: dark) {{
      .d-f {{ fill: {DARK['dim']}; }}
      .m-f {{ fill: {DARK['muted']}; }}
    }}
  </style>

  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="0.10s" dur="0.45s" fill="freeze"/>
    <text x="{CHART_X}" y="16" class="m-f" font-size="9" letter-spacing="1.3">THE YEAR</text>
    <text x="{CHART_X}" y="32" class="m-f" font-size="11">{active_days} of {total_days} days had a contribution</text>
  </g>

  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="1.30s" dur="0.45s" fill="freeze"/>
    <text x="{W - 84}" y="32" class="m-f" font-size="9" text-anchor="end">less</text>
    <text xml:space="preserve" x="{W - 78}" y="32" class="d-f" font-size="9.2">{RAMP}</text>
    <text x="{W - 6}" y="32" class="m-f" font-size="9" text-anchor="end">more</text>
  </g>

  {''.join(row_svgs)}
  {''.join(month_svgs)}
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
