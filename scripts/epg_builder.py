#!/usr/bin/env python3
"""
Script 2 — EPG Builder v1.3
Uses reliable external XMLTV EPG sources directly.
iptv-org guides.json approach abandoned — URLs are not publicly hosted.
Outputs: output/merged_epg.xml
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

OUTPUT_DIR  = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "merged_epg.xml")
HEADERS     = {"User-Agent": "Mozilla/5.0"}

# ─────────────────────────────────────────────
# RELIABLE FREE XMLTV EPG SOURCES
# These are known-working public XMLTV feeds
# ─────────────────────────────────────────────

EPG_SOURCES = [
    # Global / Multi-region
    "https://epg.pw/api/epg.xml",
    "https://raw.githubusercontent.com/dp247/Freeview-EPG/master/epg.xml",

    # UK
    "https://raw.githubusercontent.com/AbuseGr/EPG/master/UK.xml",
    "https://raw.githubusercontent.com/iptv-org/epg/master/scripts/utils/parser.js",

    # USA
    "https://raw.githubusercontent.com/matthuisman/i.mjh.nz/master/PlutoTV/us.xml",
    "https://i.mjh.nz/PlutoTV/us.xml",

    # Middle East / Arabic
    "https://i.mjh.nz/PlutoTV/all.xml",
    "https://raw.githubusercontent.com/AbuseGr/EPG/master/ArabicEPG.xml",

    # Pluto TV (global — best free EPG source)
    "https://i.mjh.nz/PlutoTV/all.xml.gz",

    # Samsung TV Plus (global)
    "https://i.mjh.nz/SamsungTVPlus/all.xml",
    "https://i.mjh.nz/SamsungTVPlus/all.xml.gz",

    # Free global sources
    "https://raw.githubusercontent.com/acidjesuz/epg-github/master/guide.xml",
    "https://raw.githubusercontent.com/matthuisman/i.mjh.nz/master/all.xml",
    "https://i.mjh.nz/all.xml",
]

# ─────────────────────────────────────────────
# FETCH EPG XML CONTENT
# ─────────────────────────────────────────────

def fetch_epg_content(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()

        content = r.content

        # Handle gzip
        if url.endswith(".gz"):
            try:
                content = gzip.decompress(content)
            except Exception:
                pass

        # Also try gzip if content-encoding says so
        elif r.headers.get("content-encoding") == "gzip":
            try:
                content = gzip.decompress(content)
            except Exception:
                pass

        decoded = content.decode("utf-8", errors="ignore")

        # Validate it looks like XMLTV
        if "<tv" not in decoded and "<channel" not in decoded:
            print(f"    [!] Response is not valid XMLTV")
            return ""

        return decoded

    except requests.exceptions.ConnectionError:
        print(f"    [!] Connection failed")
        return ""
    except requests.exceptions.Timeout:
        print(f"    [!] Timed out")
        return ""
    except requests.exceptions.HTTPError as e:
        print(f"    [!] HTTP {e.response.status_code}")
        return ""
    except Exception as e:
        print(f"    [!] Error: {e}")
        return ""

# ─────────────────────────────────────────────
# PARSE EPG
# ─────────────────────────────────────────────

def parse_epg(xml_content: str) -> tuple:
    channels   = {}
    programmes = []

    if not xml_content:
        return channels, programmes

    # Extract full <channel> blocks
    channel_blocks = re.findall(
        r'(<channel[^>]+id="([^"]+)"[^>]*/?>(?:.*?</channel>)?)',
        xml_content, re.DOTALL
    )
    for ch_block, ch_id in channel_blocks:
        if ch_id and ch_id not in channels:
            channels[ch_id] = ch_block.strip()

    # Extract full <programme> blocks
    programme_blocks = re.findall(
        r'(<programme\s[^>]*>.*?</programme>)',
        xml_content, re.DOTALL
    )
    programmes.extend(programme_blocks)

    return channels, programmes

# ─────────────────────────────────────────────
# MERGE EPG SOURCES
# ─────────────────────────────────────────────

def merge_epg(epg_urls: list) -> tuple:
    all_channels   = {}
    all_programmes = []
    ch_prog_count  = defaultdict(int)
    fetched        = 0

    for url in epg_urls:
        print(f"  [↓] {url[:80]}...")
        content = fetch_epg_content(url)
        if not content:
            continue

        channels, programmes = parse_epg(content)
        if not channels and not programmes:
            continue

        # Count programmes per channel in this source
        source_counts = defaultdict(int)
        for prog in programmes:
            ch_match = re.search(r'channel="([^"]+)"', prog)
            if ch_match:
                source_counts[ch_match.group(1)] += 1

        # Keep version with most programmes per channel
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
        f.write(f'<tv source-info-name="merged-epg" generator-info-name="epg_builder" generated-at="{now}">\n\n')

        for ch_block in channels.values():
            f.write(ch_block + "\n")

        f.write("\n")

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
    print("║        EPG Builder v1.3          ║")
    print("╚══════════════════════════════════╝\n")

    print(f"► Fetching {len(EPG_SOURCES)} EPG sources...\n")
    channels, programmes, fetched = merge_epg(EPG_SOURCES)

    if fetched == 0:
        print("  [!] No EPG sources fetched successfully — aborting.")
        sys.exit(1)

    print(f"\n  [✓] Sources fetched:  {fetched}/{len(EPG_SOURCES)}")
    print(f"  [✓] Unique channels:  {len(channels)}")
    print(f"  [✓] Total programmes: {len(programmes)}\n")

    if not channels and not programmes:
        print("  [!] No EPG data to write — aborting.")
        sys.exit(1)

    print("► Writing merged_epg.xml...")
    write_xmltv(channels, programmes)

    print("\n╔══════════════════════════════════╗")
    print("║           DONE ✓                 ║")
    print("╚══════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
