#!/usr/bin/env python3
"""
Script 2 — EPG Builder v1.2
guides.json has NO url field — it maps channels to EPG sites.
We use it to build per-site XMLTV URLs and fetch them directly.
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

API_BASE    = "https://iptv-org.github.io/api"
OUTPUT_DIR  = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "merged_epg.xml")
HEADERS     = {"User-Agent": "Mozilla/5.0"}

# Max EPG sites to fetch (each site has its own XML file)
MAX_SITES = 50

# Known EPG XML URL patterns for popular sites
# Format: site domain → URL template (use {lang} if needed)
KNOWN_EPG_SITES = {
    "tvtv.us":           "https://iptv-org.github.io/epg/guides/us/tvtv.us.epg.xml",
    "sky.co.uk":         "https://iptv-org.github.io/epg/guides/gb/sky.co.uk.epg.xml",
    "tvguide.com":       "https://iptv-org.github.io/epg/guides/us/tvguide.com.epg.xml",
    "tv.apple.com":      "https://iptv-org.github.io/epg/guides/us/tv.apple.com.epg.xml",
    "bbc.co.uk":         "https://iptv-org.github.io/epg/guides/gb/bbc.co.uk.epg.xml",
    "rcti.id":           "https://iptv-org.github.io/epg/guides/id/rcti.id.epg.xml",
    "ontvtonight.com":   "https://iptv-org.github.io/epg/guides/us/ontvtonight.com.epg.xml",
}

# Fallback EPG sources (these are standalone XMLTV files)
FALLBACK_EPG_URLS = [
    "https://iptv-org.github.io/epg/guides/us/tvtv.us.epg.xml",
    "https://iptv-org.github.io/epg/guides/gb/sky.co.uk.epg.xml",
    "https://iptv-org.github.io/epg/guides/us/tvguide.com.epg.xml",
    "https://iptv-org.github.io/epg/guides/gb/bbc.co.uk.epg.xml",
    "https://iptv-org.github.io/epg/guides/de/tvspielfilm.de.epg.xml",
    "https://iptv-org.github.io/epg/guides/fr/programme-tv.net.epg.xml",
    "https://iptv-org.github.io/epg/guides/es/movistar.es.epg.xml",
    "https://iptv-org.github.io/epg/guides/au/foxtel.com.au.epg.xml",
    "https://iptv-org.github.io/epg/guides/us/ontvtonight.com.epg.xml",
    "https://iptv-org.github.io/epg/guides/ae/osn.com.epg.xml",
    "https://iptv-org.github.io/epg/guides/sa/shahid.net.epg.xml",
    "https://iptv-org.github.io/epg/guides/eg/shahid.net.epg.xml",
]

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
# BUILD EPG URL LIST FROM GUIDES.JSON
# ─────────────────────────────────────────────

def build_epg_urls(guides: list) -> list:
    """
    guides.json = list of { channel, site, site_id, lang }
    Build XMLTV URLs from the site names using iptv-org EPG pattern.
    Pattern: https://iptv-org.github.io/epg/guides/{country}/{site}.epg.xml
    """
    seen   = set()
    urls   = []

    # First add known sites
    for site, url in KNOWN_EPG_SITES.items():
        if url not in seen:
            seen.add(url)
            urls.append(url)

    # Then build URLs from guides.json site names
    for guide in guides:
        site = guide.get("site", "").strip()
        lang = guide.get("lang", "en").strip()

        if not site:
            continue

        # Map lang code to country folder (best guess)
        lang_to_country = {
            "en": "us", "fr": "fr", "de": "de", "es": "es",
            "it": "it", "pt": "pt", "ar": "ae", "nl": "nl",
            "pl": "pl", "ru": "ru", "tr": "tr", "id": "id",
            "ja": "jp", "ko": "kr", "zh": "cn", "hi": "in",
        }
        country = lang_to_country.get(lang, lang)
        url = f"https://iptv-org.github.io/epg/guides/{country}/{site}.epg.xml"

        if url not in seen:
            seen.add(url)
            urls.append(url)

    # Add fallbacks at the end
    for url in FALLBACK_EPG_URLS:
        if url not in seen:
            seen.add(url)
            urls.append(url)

    return urls

# ─────────────────────────────────────────────
# FETCH EPG XML CONTENT
# ─────────────────────────────────────────────

def fetch_epg_content(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()

        content = r.content
        if url.endswith(".gz"):
            try:
                content = gzip.decompress(content)
            except Exception:
                pass

        return content.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    [!] Failed: {e}")
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

    print(f"  [~] Fetching up to {MAX_SITES} EPG sources...\n")

    for url in epg_urls[:MAX_SITES]:
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
        f.write(f'<tv source-info-name="iptv-org-epg" generator-info-name="epg_builder" generated-at="{now}">\n\n')

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
    print("║        EPG Builder v1.2          ║")
    print("╚══════════════════════════════════╝\n")

    # Step 1 — Fetch guides list to extract site names
    print("► Step 1: Fetching EPG guide sources...")
    guides = fetch_json("guides.json")
    print(f"  [✓] Found {len(guides)} guide entries\n")

    # Step 2 — Build EPG URLs from site names
    print("► Step 2: Building EPG URL list...")
    epg_urls = build_epg_urls(guides)
    print(f"  [✓] Built {len(epg_urls)} unique EPG URLs\n")

    # Step 3 — Fetch and merge
    print("► Step 3: Fetching and merging EPG data...")
    channels, programmes, fetched = merge_epg(epg_urls)

    if fetched == 0:
        print("  [!] No EPG sources fetched — aborting.")
        sys.exit(1)

    print(f"\n  [✓] Sources fetched:  {fetched}")
    print(f"  [✓] Unique channels:  {len(channels)}")
    print(f"  [✓] Total programmes: {len(programmes)}\n")

    if not channels and not programmes:
        print("  [!] No EPG data to write — aborting.")
        sys.exit(1)

    # Step 4 — Write output
    print("► Step 4: Writing merged_epg.xml...")
    write_xmltv(channels, programmes)

    print("\n╔══════════════════════════════════╗")
    print("║           DONE ✓                 ║")
    print("╚══════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
