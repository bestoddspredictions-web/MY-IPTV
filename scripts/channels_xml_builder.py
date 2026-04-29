#!/usr/bin/env python3
"""
channels_xml_builder.py
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

PLAYLIST_FILE  = "output/merged_channels.m3u"
OUTPUT_FILE    = "channels.xml"
GUIDES_API     = "https://iptv-org.github.io/api/guides.json"
HEADERS        = {"User-Agent": "Mozilla/5.0"}

# Max channels to include in EPG grab
# Keep reasonable to stay within GitHub Actions 6hr limit
# Each channel takes ~2-5 seconds to grab
MAX_CHANNELS   = 2000

# ─────────────────────────────────────────────
# STEP 1 — READ CHANNEL IDs FROM PLAYLIST
# ─────────────────────────────────────────────

def read_playlist_ids(playlist_file: str) -> list:
    """Extract tvg-id list from M3U playlist."""
    if not os.path.exists(playlist_file):
        print(f"  [!] Playlist not found: {playlist_file}")
        return []

    ids = []
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
    """Fetch guides.json from iptv-org API."""
    print(f"  [↓] Fetching {GUIDES_API}")
    try:
        r = requests.get(GUIDES_API, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  [!] Failed to fetch guides: {e}")
        return []

# ─────────────────────────────────────────────
# STEP 3 — BUILD CHANNEL → GUIDE MAPPING
# ─────────────────────────────────────────────

def build_guide_map(guides: list) -> dict:
    """
    Build a map of channel_id → list of guide entries.
    guides.json structure: { channel, site, site_id, site_name, lang }
    """
    guide_map = defaultdict(list)
    for g in guides:
        ch_id = (g.get("channel") or "").strip()
        if ch_id:
            guide_map[ch_id].append(g)
    return guide_map

# ─────────────────────────────────────────────
# STEP 4 — WRITE CHANNELS.XML
# ─────────────────────────────────────────────

def write_channels_xml(playlist_ids: list, guide_map: dict) -> int:
    """
    Match playlist channel IDs to guide entries.
    Write channels.xml for iptv-org/epg grabber.
    """
    matched = []
    unmatched = 0

    for ch_id in playlist_ids:
        guides = guide_map.get(ch_id, [])
        if not guides:
            unmatched += 1
            continue

        # Pick the best guide entry — prefer English, else first available
        guide = next((g for g in guides if g.get("lang") == "en"), guides[0])

        site      = (guide.get("site") or "").strip()
        site_id   = (guide.get("site_id") or "").strip()
        site_name = (guide.get("site_name") or ch_id).strip()
        lang      = (guide.get("lang") or "en").strip()

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

    # Write XML
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<channels>\n')
        for ch in matched:
            # Escape any XML special chars in site_name
            name = ch["site_name"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
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
    print("║    Channels XML Builder v1.0     ║")
    print("╚══════════════════════════════════╝\n")

    # Step 1
    print("► Step 1: Reading playlist channel IDs...")
    playlist_ids = read_playlist_ids(PLAYLIST_FILE)
    if not playlist_ids:
        print("  [!] No channel IDs found — aborting.")
        sys.exit(1)
    print(f"  [✓] Found {len(playlist_ids)} unique channel IDs\n")

    # Step 2
    print("► Step 2: Fetching guides.json...")
    guides = fetch_guides()
    if not guides:
        print("  [!] No guides fetched — aborting.")
        sys.exit(1)
    print(f"  [✓] Loaded {len(guides)} guide entries\n")

    # Step 3
    print("► Step 3: Building guide map...")
    guide_map = build_guide_map(guides)
    print(f"  [✓] {len(guide_map)} channels have guide entries\n")

    # Step 4
    print("► Step 4: Writing channels.xml...")
    matched, unmatched = write_channels_xml(playlist_ids, guide_map)
    print(f"  [✓] Channels matched:   {matched}")
    print(f"  [✓] Channels unmatched: {unmatched}")
    print(f"  [✓] Saved → {OUTPUT_FILE}\n")

    if matched == 0:
        print("  [!] No channels matched — aborting.")
        sys.exit(1)

    print("╔══════════════════════════════════╗")
    print("║           DONE ✓                 ║")
    print("╚══════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
