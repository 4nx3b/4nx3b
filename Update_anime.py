#!/usr/bin/env python3
"""
Fetches currently watching anime from AniList and updates README.md.
ANILIST_USERNAME must be set as a GitHub secret or env variable.
If not set, falls back to the hardcoded default below.
"""

import os
import re
import urllib.request
import urllib.error
import json
import sys

# ── CONFIG ────────────────────────────────────────────────────────────────────
ANILIST_USERNAME = os.environ.get("ANILIST_USERNAME") or "4nx3b"  # ← fallback username
MAX_SHOWS        = 8
README_PATH      = "README.md"
# ─────────────────────────────────────────────────────────────────────────────

print(f"✦ Using AniList username: {ANILIST_USERNAME}")

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
        }
      }
    }
  }
}
"""

def fetch_watching(username: str) -> list:
    payload = json.dumps({
        "query": QUERY,
        "variables": {"username": username}
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://graphql.anilist.co",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "github-readme-anilist-updater/1.0"
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            data = json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"✦ AniList HTTP error {e.code}: {body}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"✦ Request failed: {e}", file=sys.stderr)
        raise

    if "errors" in data:
        print(f"✦ AniList API errors: {data['errors']}", file=sys.stderr)
        raise ValueError(f"AniList returned errors: {data['errors']}")

    collection = data.get("data", {}).get("MediaListCollection")
    if not collection:
        print("✦ No MediaListCollection in response — is the list public?", file=sys.stderr)
        return []

    entries = []
    for lst in collection.get("lists", []):
        for e in lst.get("entries", []):
            media = e["media"]
            title = (media["title"].get("english") or media["title"].get("romaji") or "Unknown")
            eps   = media.get("episodes") or "?"
            prog  = e.get("progress", 0)
            entries.append({"title": title, "progress": prog, "episodes": eps})

    return entries[:MAX_SHOWS]


def build_typing_svg_url(entries: list) -> str:
    def encode_title(t: str) -> str:
        # Keep printable ASCII only, encode specials for URL
        safe = re.sub(r"[^a-zA-Z0-9 :\-!]", "", t)
        return (safe.strip()
                    .replace(" ", "+")
                    .replace(":", "%3A")
                    .replace("!", "%21"))

    if not entries:
        lines = ["%E2%9C%A6+%E2%96%B6+Nothing+in+watching+list"]
    else:
        lines = []
        for e in entries:
            safe  = encode_title(e["title"])
            prog  = e["progress"]
            eps   = e["episodes"]
            lines.append(f"%E2%9C%A6+%E2%96%B6+{safe}+%28{prog}%2F{eps}%29")

    line_str   = ";".join(lines)
    svg_height = max(60, len(lines) * 44)

    return (
        f"https://readme-typing-svg.demolab.com"
        f"?font=Share+Tech+Mono&weight=700&size=20&duration=1200&pause=0"
        f"&color=FCE7F3&center=true&vCenter=true&multiline=true&repeat=false"
        f"&width=860&height={svg_height}&lines={line_str}"
    )


def update_readme(svg_url: str, username: str) -> None:
    try:
        with open(README_PATH, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"✦ ERROR: {README_PATH} not found in working directory.", file=sys.stderr)
        print(f"✦ Working directory contents: {os.listdir('.')}", file=sys.stderr)
        sys.exit(1)

    new_img = f'<img src="{svg_url}" />'
    pattern = r"(<!-- ANIME_START -->).*?(<!-- ANIME_END -->)"

    if not re.search(pattern, content, flags=re.DOTALL):
        print("✦ ERROR: Could not find <!-- ANIME_START --> and <!-- ANIME_END --> markers in README.md", file=sys.stderr)
        sys.exit(1)

    updated = re.sub(pattern, rf"\1\n{new_img}\n\2", content, flags=re.DOTALL)

    # Update the AniList profile badge link
    updated = re.sub(
        r'(href="https://anilist\.co/user/)[^"]*(")',
        rf"\g<1>{username}\2",
        updated,
    )

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"✦ README.md updated successfully.")


if __name__ == "__main__":
    try:
        print("✦ Fetching AniList currently watching list...")
        entries = fetch_watching(ANILIST_USERNAME)
        print(f"✦ Found {len(entries)} entries:")
        for e in entries:
            print(f"   ▶ {e['title']}  ({e['progress']}/{e['episodes']})")
    except Exception as exc:
        print(f"✦ Fetch failed: {exc} — writing fallback placeholder.", file=sys.stderr)
        entries = []

    svg_url = build_typing_svg_url(entries)
    print(f"✦ SVG URL built ({len(entries)} lines)")
    update_readme(svg_url, ANILIST_USERNAME)
    print("✦ Done.")
  
