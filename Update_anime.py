#!/usr/bin/env python3
"""
Fetches currently watching anime from AniList and updates README.md.
Set ANILIST_USERNAME in the environment or edit the variable below.
"""

import os
import re
import urllib.request
import urllib.parse
import json

# ── CONFIG ────────────────────────────────────────────────────────────────────
ANILIST_USERNAME = os.environ.get("ANILIST_USERNAME", "4nx3b")   # ← change or set as env var
MAX_SHOWS        = 8    # max entries to display in the typing SVG
README_PATH      = "README.md"
# ─────────────────────────────────────────────────────────────────────────────

QUERY = """
query ($username: String) {
  MediaListCollection(userName: $username, type: ANIME, status: CURRENT, sort: UPDATED_TIME_DESC) {
    lists {
      entries {
        progress
        media {
          title {
            english
            romaji
          }
          episodes
          coverImage { color }
        }
      }
    }
  }
}
"""

def fetch_watching(username: str) -> list[dict]:
    payload = json.dumps({"query": QUERY, "variables": {"username": username}}).encode()
    req = urllib.request.Request(
        "https://graphql.anilist.co",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    entries = []
    for lst in data["data"]["MediaListCollection"]["lists"]:
        for e in lst["entries"]:
            media = e["media"]
            title = media["title"]["english"] or media["title"]["romaji"]
            eps   = media.get("episodes") or "?"
            prog  = e.get("progress", 0)
            entries.append({"title": title, "progress": prog, "episodes": eps})
    return entries[:MAX_SHOWS]


def build_typing_svg_url(entries: list[dict]) -> str:
    """
    Builds a readme-typing-svg URL where each line is one anime entry.
    Format: ✦ ▶ Title (ep X / Y)
    """
    if not entries:
        lines = ["%E2%9C%A6+%E2%96%B6+Nothing+currently+watching"]
    else:
        raw_lines = []
        for e in entries:
            # Sanitise title for URL: keep alphanumeric, spaces→+, drop special chars
            safe = re.sub(r"[^a-zA-Z0-9 :'\-!]", "", e["title"])
            safe = safe.replace(" ", "+").replace("'", "%27").replace(":", "%3A")
            prog = e["progress"]
            eps  = e["episodes"]
            raw_lines.append(f"%E2%9C%A6+%E2%96%B6+{safe}+%28{prog}%2F{eps}%29")
        lines = raw_lines

    line_str  = ";".join(lines)
    svg_height = max(60, len(lines) * 44)
    url = (
        f"https://readme-typing-svg.demolab.com"
        f"?font=Share+Tech+Mono&weight=700&size=20&duration=1200&pause=0"
        f"&color=FCE7F3&center=true&vCenter=true&multiline=true&repeat=false"
        f"&width=860&height={svg_height}&lines={line_str}"
    )
    return url


def update_readme(url: str, username: str) -> None:
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace the typing SVG between the ANIME_START / ANIME_END markers
    new_img = f'<img src="{url}" />'
    pattern = r"(<!-- ANIME_START -->).*?(<!-- ANIME_END -->)"
    replacement = rf"\1\n{new_img}\n\2"
    updated = re.sub(pattern, replacement, content, flags=re.DOTALL)

    # Also update the AniList profile badge href
    updated = re.sub(
        r'(href="https://anilist\.co/user/)[^"]*(")',
        rf"\g<1>{username}\2",
        updated,
    )

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"✦ README updated with {username}'s AniList data.")


if __name__ == "__main__":
    print(f"✦ Fetching AniList data for: {ANILIST_USERNAME}")
    try:
        entries = fetch_watching(ANILIST_USERNAME)
        print(f"✦ Found {len(entries)} currently watching entries")
        for e in entries:
            print(f"  ▶ {e['title']}  ({e['progress']}/{e['episodes']})")
    except Exception as exc:
        print(f"✦ AniList fetch failed: {exc}")
        entries = []

    svg_url = build_typing_svg_url(entries)
    update_readme(svg_url, ANILIST_USERNAME)
  
