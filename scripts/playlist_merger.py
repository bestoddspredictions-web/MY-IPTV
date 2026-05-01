#!/usr/bin/env python3
"""
playlist_merger.py v2.0
Merges mbc_channels.m3u into merged_channels.m3u
- Removes any existing MBC entries from merged_channels.m3u
- Appends fresh MBC channels from mbc_channels.m3u
- Deduplicates by stream URL
"""

import os

OUTPUT_DIR    = "output"
MAIN_PLAYLIST = os.path.join(OUTPUT_DIR, "merged_channels.m3u")
MBC_PLAYLIST  = os.path.join(OUTPUT_DIR, "mbc_channels.m3u")
EPG_URL       = "https://raw.githubusercontent.com/bestoddspredictions-web/MY-IPTV/main/output/merged_epg.xml"

def parse_m3u(filepath: str) -> tuple:
    """Parse M3U file. Returns (header, [(extinf, url), ...])"""
    if not os.path.exists(filepath):
        print(f"  ⚠ Not found: {filepath}")
        return "", []

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    lines   = content.strip().split("\n")
    header  = lines[0] if lines[0].startswith("#EXTM3U") else "#EXTM3U"
    channels = []

    i = 1
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF") and i + 1 < len(lines):
            url = lines[i + 1].strip()
            if url.startswith("http"):
                channels.append((line, url))
        i += 1

    return header, channels


def write_m3u(filepath: str, channels: list):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f'#EXTM3U x-tvg-url="{EPG_URL}"\n\n')
        for extinf, url in channels:
            f.write(f"{extinf}\n{url}\n\n")


def main():
    print("=" * 60)
    print("Playlist Merger v2.0")
    print("=" * 60)

    # Load both playlists
    _, main_channels = parse_m3u(MAIN_PLAYLIST)
    _, mbc_channels  = parse_m3u(MBC_PLAYLIST)

    print(f"\n  Main playlist : {len(main_channels)} channels")
    print(f"  MBC playlist  : {len(mbc_channels)} channels")

    if not mbc_channels:
        print("\n⚠ No MBC channels found — keeping main playlist unchanged")
        return

    # Remove existing MBC entries from main
    mbc_keywords = ["mbc", "MBC", "Mbc"]
    non_mbc = []
    removed = 0
    for extinf, url in main_channels:
        is_mbc = any(kw in extinf for kw in mbc_keywords)
        if is_mbc:
            removed += 1
        else:
            non_mbc.append((extinf, url))

    print(f"\n  Removed {removed} existing MBC entries")

    # Merge and deduplicate
    merged   = non_mbc + mbc_channels
    seen     = set()
    deduped  = []
    for extinf, url in merged:
        if url not in seen:
            seen.add(url)
            deduped.append((extinf, url))

    print(f"  Removed {len(merged) - len(deduped)} duplicate URLs")

    # Write
    write_m3u(MAIN_PLAYLIST, deduped)

    print(f"\n✅ Final playlist: {len(deduped)} channels")
    print(f"   Non-MBC : {len(non_mbc)}")
    print(f"   MBC     : {len(mbc_channels)}")


if __name__ == "__main__":
    main()
