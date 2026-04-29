#!/usr/bin/env python3
"""
channels_xml_builder.py v1.1
Reads merged_channels.m3u + iptv-org guides.json
Builds channels.xml for iptv-org/epg grabber
Only includes channels that have a known EPG guide entry
"""

import requests
import re
import os
import sys
from collections import defaultdict

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

# Use GITHUB_WORKSPACE env var if available (GitHub Actions)
# Fall back to current directory (local run)
WORKSPACE      = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
PLAYLIST_FILE  = os.path.join(WORKSPACE, "output", "merged_channels.m3u")
OUTPUT_FILE    = os.path.join(WORKSPACE, "channels.xml")
OUTPUT_DIR     = os.path.join(WORKSPACE, "output")
GUIDES_API     = "https://iptv-org.github.io/api/guides.json"
HEADERS        = {"User-Agent": "Mozilla/5.0"}

# 200 channels = ~20-40 mins on GitHub Actions
# Safe within the 5hr timeout and 7GB RAM limit
MAX_CHANNELS   = 200

# ─────────────────────────────────────────────
# STEP 1 — READ CHANNEL IDs FROM PLAYLIST
# ─────────────────────────────────────────────

def read_playlist_ids(playlist_file: str) -> list:
    """Extract tvg-id list from M3U playlist."""
    if not os.path.exists(playlist_file):
        print(f"  [!] Playlist not found: {playlist_file}")
        print(f"  [!] Make sure Build Playlist workflow ran first.")
        return []

    ids  = []
    seen = set()

    with open(playlist_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            match = re.search(r'tvg-id="([^"]+)"', line)
            if match:
                ch_id = match.group(1).strip()
                if ch_id and ch_id not in seen:
                    seen.add(ch_id)
                    ids.append(ch_id)

    return ids

# ─────────────────────────────────────────────
# STEP 2 — FETCH GUIDES.JSON
# ─────────────────────────────────────────────

def fetch_guides() -> list:
    print(f"  [↓] Fetching {GUIDES_API}")
    try:
        r = requests.get(GUIDES_API, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            print(f"  [!] Unexpected response format from guides.json")
            return []
        return data
    except requests.exceptions.ConnectionError:
        print(f"  [!] Connection failed")
        return []
    except requests.exceptions.Timeout:
        print(f"  [!] Request timed out")
        return []
    except Exception as e:
        print(f"  [!] Failed: {e}")
        return []

# ─────────────────────────────────────────────
# STEP 3 — BUILD CHANNEL → GUIDE MAPPING
# ─────────────────────────────────────────────

def build_guide_map(guides: list) -> dict:
    guide_map = defaultdict(list)
    for g in guides:
        ch_id = (g.get("channel") or "").strip()
        if ch_id:
            guide_map[ch_id].append(g)
    return guide_map

# ─────────────────────────────────────────────
# STEP 4 — WRITE CHANNELS.XML
# ─────────────────────────────────────────────

def write_channels_xml(playlist_ids: list, guide_map: dict) -> tuple:
    matched   = []
    unmatched = 0

    for ch_id in playlist_ids:
        guides = guide_map.get(ch_id, [])
        if not guides:
            unmatched += 1
            continue

        # Prefer English guide, fall back to first available
        guide = next((g for g in guides if g.get("lang") == "en"), guides[0])

        site      = (guide.get("site")      or "").strip()
        site_id   = (guide.get("site_id")   or "").strip()
        site_name = (guide.get("site_name") or ch_id).strip()
        lang      = (guide.get("lang")      or "en").strip()

        if site and site_id:
            matched.append({
                "channel_id": ch_id,
                "site":       site,
                "site_id":    site_id,
                "site_name":  site_name,
                "lang":       lang,
            })

    # Cap at MAX_CHANNELS
    matched = matched[:MAX_CHANNELS]

    # Ensure output dir exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Write channels.xml
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<channels>\n')
        for ch in matched:
            # Escape XML special characters
            name = (ch["site_name"]
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;"))
            f.write(
                f'  <channel site="{ch["site"]}" '
                f'lang="{ch["lang"]}" '
                f'xmltv_id="{ch["channel_id"]}" '
                f'site_id="{ch["site_id"]}">'
                f'{name}</channel>\n'
            )
        f.write('</channels>\n')

    return len(matched), unmatched

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("\n╔══════════════════════════════════╗")
    print("║    Channels XML Builder v1.1     ║")
    print("╚══════════════════════════════════╝\n")

    print(f"  Workspace:     {WORKSPACE}")
    print(f"  Playlist:      {PLAYLIST_FILE}")
    print(f"  Output XML:    {OUTPUT_FILE}\n")

    # Step 1 — Read playlist
    print("► Step 1: Reading playlist channel IDs...")
    playlist_ids = read_playlist_ids(PLAYLIST_FILE)
    if not playlist_ids:
        print("  [!] No channel IDs found — aborting.")
        sys.exit(1)
    print(f"  [✓] Found {len(playlist_ids)} unique channel IDs\n")

    # Step 2 — Fetch guides
    print("► Step 2: Fetching guides.json...")
    guides = fetch_guides()
    if not guides:
        print("  [!] No guides fetched — aborting.")
        sys.exit(1)
    print(f"  [✓] Loaded {len(guides)} guide entries\n")

    # Step 3 — Build guide map
    print("► Step 3: Building guide map...")
    guide_map = build_guide_map(guides)
    print(f"  [✓] {len(guide_map)} channels have guide entries\n")

    # Step 4 — Write channels.xml
    print("► Step 4: Writing channels.xml...")
    matched, unmatched = write_channels_xml(playlist_ids, guide_map)
    print(f"  [✓] Channels matched:   {matched}")
    print(f"  [✓] Channels unmatched: {unmatched}")
    print(f"  [✓] Saved → {OUTPUT_FILE}")

    # Validate output has content
    if matched == 0:
        print("  [!] No channels matched any guide — aborting.")
        sys.exit(1)

    # Print first 3 entries so we can verify in Actions log
    print("\n  Preview (first 3 channels):")
    with open(OUTPUT_FILE, "r") as f:
        lines = f.readlines()
    for line in lines[2:5]:
        print(f"    {line.rstrip()}")

    print("\n╔══════════════════════════════════╗")
    print("║           DONE ✓                 ║")
    print("╚══════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
