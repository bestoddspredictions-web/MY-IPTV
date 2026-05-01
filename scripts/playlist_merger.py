#!/usr/bin/env python3
"""
playlist_merger.py v1.0
Merges mbc_channels.m3u into merged_channels.m3u
- Removes any existing MBC entries from merged_channels.m3u
- Appends fresh MBC channels from mbc_channels.m3u
- Deduplicates by stream URL
Runs as part of playlist.yml after playlist_builder.py
"""

import os
import re

OUTPUT_DIR     = "output"
MAIN_PLAYLIST  = os.path.join(OUTPUT_DIR, "merged_channels.m3u")
MBC_PLAYLIST   = os.path.join(OUTPUT_DIR, "mbc_channels.m3u")

def parse_m3u(filepath: str) -> list:
    """Parse M3U file into list of (extinf, url) tuples."""
    channels = []
    if not os.path.exists(filepath):
        print(f"  ⚠ File not found: {filepath}")
        return channels

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.read().strip().split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF") and i + 1 < len(lines):
            url = lines[i + 1].strip()
            if url.startswith("http"):
                channels.append((line, url))
        i += 1

    return channels


def write_m3u(filepath: str, channels: list, epg_url: str = ""):
    """Write channels list to M3U file."""
    with open(filepath, "w", encoding="utf-8") as f:
        if epg_url:
            f.write(f'#EXTM3U x-tvg-url="{epg_url}"\n\n')
        else:
            f.write("#EXTM3U\n\n")
        for extinf, url in channels:
            f.write(f"{extinf}\n{url}\n\n")


def main():
    print("=" * 60)
    print("Playlist Merger v1.0")
    print("=" * 60)

    # ── Load main playlist ────────────────────────────────────────
    print(f"\n📂 Loading main playlist: {MAIN_PLAYLIST}")
    main_channels = parse_m3u(MAIN_PLAYLIST)
    print(f"  Total channels: {len(main_channels)}")

    # ── Load MBC playlist ─────────────────────────────────────────
    print(f"\n📂 Loading MBC playlist: {MBC_PLAYLIST}")
    mbc_channels = parse_m3u(MBC_PLAYLIST)
    print(f"  MBC channels: {len(mbc_channels)}")

    if not mbc_channels:
        print("\n⚠ No MBC channels to merge — keeping existing playlist unchanged")
        return

    # ── Remove existing MBC entries from main playlist ────────────
    mbc_keywords = ["mbc", "MBC", "Mbc"]
    non_mbc = []
    removed = 0
    for extinf, url in main_channels:
        is_mbc = any(kw in extinf for kw in mbc_keywords)
        if not is_mbc:
            is_mbc = any(kw.lower() in url.lower() for kw in ["mbc"])
        if is_mbc:
            removed += 1
        else:
            non_mbc.append((extinf, url))

    print(f"\n🗑 Removed {removed} existing MBC entries from main playlist")

    # ── Merge: non-MBC + fresh MBC ────────────────────────────────
    merged = non_mbc + mbc_channels

    # ── Deduplicate by URL ────────────────────────────────────────
    seen_urls = set()
    deduped = []
    for extinf, url in merged:
        if url not in seen_urls:
            seen_urls.add(url)
            deduped.append((extinf, url))

    dupes_removed = len(merged) - len(deduped)
    if dupes_removed:
        print(f"🔄 Removed {dupes_removed} duplicate URLs")

    # ── Write merged playlist ─────────────────────────────────────
    epg_url = "https://raw.githubusercontent.com/YOUR_USERNAME/MY-IPTV/main/output/merged_epg.xml"
    write_m3u(MAIN_PLAYLIST, deduped, epg_url)

    print(f"\n✅ Merged playlist written: {MAIN_PLAYLIST}")
    print(f"   Non-MBC channels : {len(non_mbc)}")
    print(f"   MBC channels     : {len(mbc_channels)}")
    print(f"   Total            : {len(deduped)}")


if __name__ == "__main__":
    main()
