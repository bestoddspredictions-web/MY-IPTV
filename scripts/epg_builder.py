#!/usr/bin/env python3
"""
Script 2 — EPG Builder
Fetches guides from iptv-org API.
Downloads EPG XML per channel.
Merges into one clean merged_epg.xml
Run: Daily via GitHub Actions
"""

import requests
import gzip
import os
import re
import sys
from datetime import datetime, timezone
from collections import defaultdict

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

API_BASE    = "https://iptv-org.github.io/api"
OUTPUT_DIR  = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "merged_epg.xml")
HEADERS     = {"User-Agent": "Mozilla/5.0"}

# Max EPG sources to fetch (keeps run time reasonable on GitHub Actions)
MAX_SOURCES = 50

# ─────────────────────────────────────────────
# FETCH JSON
# ─────────────────────────────────────────────

def fetch_json(endpoint: str) -> list:
    url = f"{API_BASE}/{endpoint}"
    print(f"  [↓] Fetching {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            print(f"  [!] Unexpected response format")
            return []
        return data
    except requests.exceptions.ConnectionError:
        print(f"  [!] Connection failed — check internet connection")
        return []
    except requests.exceptions.Timeout:
        print(f"  [!] Request timed out")
        return []
    except Exception as e:
        print(f"  [!] Failed: {e}")
        return []

# ─────────────────────────────────────────────
# FETCH EPG XML CONTENT
# ─────────────────────────────────────────────

def fetch_epg_content(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()

        # Handle gzip compressed files
        content = r.content
        if url.endswith(".gz"):
            try:
                content = gzip.decompress(content)
            except Exception:
                pass  # Try decoding as-is if decompression fails

        return content.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    [!] Failed: {e}")
        return ""

# ─────────────────────────────────────────────
# PARSE EPG — extract channel + programme blocks
# ─────────────────────────────────────────────

def parse_epg(xml_content: str) -> tuple:
    """
    Returns:
        channels   — dict of { channel_id: full_channel_xml_block }
        programmes — list of full programme xml blocks
    """
    channels   = {}
    programmes = []

    if not xml_content:
        return channels, programmes

    # Extract full <channel ...>...</channel> blocks
    channel_blocks = re.findall(
        r'(<channel[^>]+id="([^"]+)"[^>]*/?>(?:.*?</channel>)?)',
        xml_content, re.DOTALL
    )
    for ch_block, ch_id in channel_blocks:
        if ch_id and ch_id not in channels:
            channels[ch_id] = ch_block.strip()

    # Extract full <programme ...>...</programme> blocks
    programme_blocks = re.findall(
        r'(<programme\s[^>]*>.*?</programme>)',
        xml_content, re.DOTALL
    )
    programmes.extend(programme_blocks)

    return channels, programmes

# ─────────────────────────────────────────────
# MERGE EPG SOURCES
# ─────────────────────────────────────────────

def merge_epg(guides: list) -> tuple:
    """
    Fetch and merge multiple EPG sources.
    For duplicate channels — keep the one with most programme entries.
    Returns: (channels_dict, programmes_list, fetched_count)
    """
    all_channels   = {}          # channel_id → xml block
    all_programmes = []          # all programme entries
    ch_prog_count  = defaultdict(int)  # channel_id → best programme count

    # Deduplicate guide URLs first
    seen_urls     = set()
    unique_guides = []
    for g in guides:
        url = g.get("url", "").strip()
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_guides.append(g)

    print(f"  [✓] Unique EPG sources: {len(unique_guides)}")
    print(f"  [~] Fetching up to {MAX_SOURCES} sources...\n")

    fetched = 0
    for guide in unique_guides[:MAX_SOURCES]:
        url = guide.get("url", "").strip()
        if not url:
            continue

        print(f"  [↓] {url[:80]}...")
        content = fetch_epg_content(url)
        if not content:
            continue

        channels, programmes = parse_epg(content)
        if not channels and not programmes:
            print(f"    [!] No data parsed from this source")
            continue

        # Count programmes per channel in this source
        source_counts = defaultdict(int)
        for prog in programmes:
            ch_match = re.search(r'channel="([^"]+)"', prog)
            if ch_match:
                source_counts[ch_match.group(1)] += 1

        # For each channel — keep version with most programmes
        for ch_id, ch_block in channels.items():
            source_count = source_counts.get(ch_id, 0)
            if source_count > ch_prog_count.get(ch_id, 0):
                all_channels[ch_id]  = ch_block
                ch_prog_count[ch_id] = source_count

        all_programmes.extend(programmes)
        fetched += 1
        print(f"    [✓] {len(channels)} channels | {len(programmes)} programmes")

    return all_channels, all_programmes, fetched

# ─────────────────────────────────────────────
# WRITE OUTPUT XMLTV
# ─────────────────────────────────────────────

def write_xmltv(channels: dict, programmes: list):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S +0000")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
        f.write(f'<tv source-info-name="iptv-org-epg" generator-info-name="epg_builder" generated-at="{now}">\n\n')

        # Write channel blocks
        for ch_block in channels.values():
            f.write(ch_block + "\n")

        f.write("\n")

        # Write full programme blocks — these are already complete XML elements
        for prog in programmes:
            f.write(prog.strip() + "\n")

        f.write("\n</tv>\n")

    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"\n  [✓] Saved → {OUTPUT_FILE} ({size_mb:.1f} MB)")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("\n╔══════════════════════════════════╗")
    print("║        EPG Builder v1.1          ║")
    print("╚══════════════════════════════════╝\n")

    # Step 1 — Fetch guides list
    print("► Step 1: Fetching EPG guide sources...")
    guides = fetch_json("guides.json")
    if not guides:
        print("  [!] No guide sources found — aborting.")
        sys.exit(1)
    print(f"  [✓] Found {len(guides)} guide sources\n")

    # Step 2 — Merge EPG sources
    print("► Step 2: Fetching and merging EPG data...")
    channels, programmes, fetched = merge_epg(guides)

    if fetched == 0:
        print("  [!] No EPG sources fetched successfully — aborting.")
        sys.exit(1)

    print(f"\n  [✓] Sources fetched:    {fetched}")
    print(f"  [✓] Unique channels:    {len(channels)}")
    print(f"  [✓] Total programmes:   {len(programmes)}\n")

    if not channels and not programmes:
        print("  [!] No EPG data to write — aborting.")
        sys.exit(1)

    # Step 3 — Write output
    print("► Step 3: Writing merged_epg.xml...")
    write_xmltv(channels, programmes)

    print("\n╔══════════════════════════════════╗")
    print("║           DONE ✓                 ║")
    print("╚══════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
