#!/usr/bin/env python3
"""Generate local SVG stats from GitHub API data."""

import json, os, re
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/github.json"
ASSETS = ROOT / "assets"
DATA.parent.mkdir(parents=True, exist_ok=True)

USER = os.environ.get("GITHUB_USER", "JeevandeepRout")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

def get(url):
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as r:
        return json.load(r)

profile = get(f"https://api.github.com/users/{USER}")
repos = get(f"https://api.github.com/users/{USER}/repos?per_page=100&sort=updated")

repo_count = profile.get("public_repos", 0)
followers = profile.get("followers", 0)
stars = sum(r.get("stargazers_count", 0) for r in repos)
languages = [r.get("language") for r in repos if r.get("language")]
top_languages = []
for lang in languages:
    if lang not in top_languages:
        top_languages.append(lang)
top_languages = top_languages[:5]

# Public contribution count via GraphQL when a token is available.
contributions = 0
if TOKEN:
    import json as _json
    from datetime import datetime, timezone
    query = """
    query($login:String!) {
      user(login:$login) {
        contributionsCollection {
          contributionCalendar { totalContributions }
        }
      }
    }
    """
    payload = _json.dumps({"query": query, "variables": {"login": USER}}).encode()
    req = Request("https://api.github.com/graphql", data=payload,
                 headers={"Accept":"application/vnd.github+json",
                          "Authorization":f"Bearer {TOKEN}",
                          "Content-Type":"application/json"})
    with urlopen(req, timeout=30) as r:
        data = _json.load(r)
    contributions = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]

pulse = min(100, max(5, int(contributions / 365 * 100))) if contributions else 8

stats = ASSETS.joinpath("stats.svg").read_text()
stats = stats.replace("{{REPOS}}", str(repo_count))
stats = stats.replace("{{FOLLOWERS}}", str(followers))
stats = stats.replace("{{STARS}}", str(stars))
stats = stats.replace("{{CONTRIBUTIONS}}", str(contributions))
stats = stats.replace("{{PULSE}}", str(pulse))
stats = stats.replace("{{LANGUAGES}}", "STACK // " + " · ".join(top_languages or ["building"]))

# Simple deterministic activity animation: no remote service needed.
cells = []
for i in range(52):
    level = (stars + followers + i * 7) % 5
    opacity = ["0.08", "0.22", "0.38", "0.65", "1"][level]
    x = (i % 26) * 27
    y = (i // 26) * 27
    cells.append(
        f'<rect x="{x}" y="{y}" width="20" height="20" rx="4" fill="#111" opacity="{opacity}">'
        f'<animate attributeName="opacity" values="{opacity};0.12;{opacity}" dur="{1.2 + (i%5)*0.2}s" begin="{(i%7)*0.12}s" repeatCount="indefinite"/></rect>'
    )

activity = ASSETS.joinpath("activity.svg").read_text()
activity = activity.replace("{{CELLS}}", "".join(cells))

DATA.write_text(json.dumps({
    "user": USER,
    "repositories": repo_count,
    "followers": followers,
    "stars": stars,
    "contributions": contributions,
    "languages": top_languages
}, indent=2) + "\n", encoding="utf-8")

ASSETS.joinpath("stats.svg").write_text(stats, encoding="utf-8")

# Keep section headings as generated SVG assets too.
for label in ("about", "stack", "projects", "activity"):
    heading = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 62" '
        f'role="img" aria-label="{label}">'
        f'<text x="0" y="36" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" '
        f'font-size="20" font-weight="700" fill="#111">{label.upper()}</text>'
        '<path d="M0 49H760" stroke="#111" stroke-width="2" stroke-dasharray="5 7">'
        '<animate attributeName="stroke-dashoffset" from="0" to="-24" dur="1.6s" repeatCount="indefinite"/>'
        '</path></svg>'
    )
    ASSETS.joinpath(f"section-{label}.svg").write_text(heading, encoding="utf-8")
ASSETS.joinpath("activity.svg").write_text(activity, encoding="utf-8")
print("Generated local SVG stats.")
