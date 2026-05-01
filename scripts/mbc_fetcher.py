#!/usr/bin/env python3
"""
mbc_fetcher.py v5.0
Fetches MBC Group channels from elahmad.org's own M3U playlist endpoint.
Filters MBC channels and saves to output/mbc_channels.m3u

Strategy:
1. Fetch the full elahmad.org playlist (231 channels)
2. Filter only MBC group channels
3. Save clean M3U to output/mbc_channels.m3u
"""

import requests
import os
import json
import time
from datetime import datetime

# ─── OUTPUT SETUP ────────────────────────────────────────────────────────────
OUTPUT_DIR = "output"
OUTPUT_M3U = os.path.join(OUTPUT_DIR, "mbc_channels.m3u")
OUTPUT_LOG = os.path.join(OUTPUT_DIR, "mbc_fetch_log.json")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── PLAYLIST URLS TO TRY ────────────────────────────────────────────────────
# Multiple URLs in case one is blocked or token changes
PLAYLIST_URLS = [
    "https://www.elahmad.org/tv/m3u/play_list_3.m3u?id=arabic_1&t=111111111",
    "https://www.elahmad.org/tv/m3u/play_list_3.m3u?id=arabic_1&t=999999999",
    "https://www.elahmad.org/tv/m3u/play_list_3.m3u?id=arabic_1",
    "http://www.elahmad.org/tv/m3u/play_list_3.m3u?id=arabic_1&t=111111111",
]

# ─── HEADERS ─────────────────────────────────────────────────────────────────
HEADERS_LIST = [
    # Mobile browser headers
    {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Referer": "https://www.elahmad.org/tv/stream_player.php",
        "Origin": "https://www.elahmad.org",
        "Accept": "*/*",
        "Accept-Language": "ar,en;q=0.9",
    },
    # Desktop browser headers
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.elahmad.org/tv/stream_player.php",
        "Origin": "https://www.elahmad.org",
        "Accept": "*/*",
        "Accept-Language": "ar,en;q=0.9",
    },
    # Minimal headers
    {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36",
        "Referer": "https://www.elahmad.org/",
    },
]

# ─── MBC CHANNEL KEYWORDS ────────────────────────────────────────────────────
# Used to filter MBC channels from the full playlist
MBC_KEYWORDS = [
    "mbc", "MBC", "Mbc",
]

# ─── FETCH PLAYLIST ──────────────────────────────────────────────────────────

def fetch_playlist() -> str | None:
    """Try all URL + header combinations to fetch the playlist."""
    for url in PLAYLIST_URLS:
        for headers in HEADERS_LIST:
            try:
                print(f"\n  Trying: {url}")
                print(f"  Referer: {headers.get('Referer', 'none')}")
                
                resp = requests.get(url, headers=headers, timeout=20)
                
                print(f"  Status: {resp.status_code}")
                print(f"  Content length: {len(resp.text)} chars")
                print(f"  Preview: {resp.text[:100]}")
                
                if resp.status_code == 200 and "#EXTM3U" in resp.text:
                    print(f"  ✅ Got valid M3U playlist!")
                    return resp.text
                elif resp.status_code == 200:
                    print(f"  ⚠ Got 200 but not M3U content")
                else:
                    print(f"  ❌ Failed: {resp.status_code}")
                    
            except requests.exceptions.ConnectionError as e:
                print(f"  ❌ Connection error: {e}")
            except requests.exceptions.Timeout:
                print(f"  ⏱ Timeout")
            except Exception as e:
                print(f"  ⚠ Error: {e}")
            
            time.sleep(1)
    
    return None


# ─── PARSE AND FILTER ────────────────────────────────────────────────────────

def filter_mbc_channels(m3u_content: str) -> list:
    """Parse M3U and extract only MBC channels."""
    channels = []
    lines = m3u_content.strip().split("\n")
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith("#EXTINF"):
            # Check if this is an MBC channel
            is_mbc = any(kw in line for kw in MBC_KEYWORDS)
            
            # Also check the stream URL line
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if not is_mbc:
                    is_mbc = any(kw.lower() in next_line.lower() for kw in ["mbc"])
            
            if is_mbc and i + 1 < len(lines):
                extinf = line
                stream_url = lines[i + 1].strip()
                
                # Make sure it's an actual stream URL
                if stream_url.startswith("http"):
                    channels.append((extinf, stream_url))
                    print(f"  ✅ Found: {extinf[:80]}")
        
        i += 1
    
    return channels


# ─── WRITE M3U ───────────────────────────────────────────────────────────────

def write_m3u(channels: list):
    """Write filtered MBC channels to M3U file."""
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n\n")
        for extinf, stream_url in channels:
            # Ensure group-title is MBC Group
            if "group-title=" not in extinf:
                extinf = extinf.replace("#EXTINF:-1", '#EXTINF:-1 group-title="MBC Group"')
            f.write(f"{extinf}\n{stream_url}\n\n")
    
    print(f"\n✅ Wrote {len(channels)} MBC channels → {OUTPUT_M3U}")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print(f"MBC Fetcher v5.0  |  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("Strategy: Fetch elahmad.org M3U playlist, filter MBC channels")
    print("=" * 60)

    # Step 1: Fetch the playlist
    print("\n📡 Fetching playlist...")
    content = fetch_playlist()

    if not content:
        print("\n❌ Could not fetch playlist from any URL/header combination")
        print("   elahmad.org may be blocking this IP range")
        
        log = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "failed",
            "reason": "Could not fetch playlist - IP blocked or site down",
            "found_count": 0,
            "failed_count": 17,
        }
        with open(OUTPUT_LOG, "w") as f:
            json.dump(log, f, indent=2)
        return

    # Step 2: Count total channels
    total = content.count("#EXTINF")
    print(f"\n📋 Total channels in playlist: {total}")

    # Step 3: Filter MBC channels
    print("\n🔍 Filtering MBC channels...")
    mbc_channels = filter_mbc_channels(content)

    print(f"\n{'=' * 60}")
    print(f"RESULTS  ✅ {len(mbc_channels)} MBC channels found from {total} total")

    if mbc_channels:
        write_m3u(mbc_channels)
    else:
        print("⚠ No MBC channels found in playlist")

    # Save log
    log = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "success" if mbc_channels else "no_mbc_found",
        "total_channels_in_playlist": total,
        "mbc_found": len(mbc_channels),
        "mbc_channels": [e.split(",")[-1] for e, _ in mbc_channels],
    }
    with open(OUTPUT_LOG, "w") as f:
        json.dump(log, f, indent=2)
    print(f"Log → {OUTPUT_LOG}")


if __name__ == "__main__":
    main()
