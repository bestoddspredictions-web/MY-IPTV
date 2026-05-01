#!/usr/bin/env python3
"""
mbc_fetcher.py v6.0
Fetches MBC Group stream URLs from elahmad.org/tv/live/shahid_shaka.php
Each channel page embeds the actual m3u8 stream URL in the page source.

URL pattern: https://elahmad.org/tv/live/shahid_shaka.php?id={channel_id}
"""

import requests
import re
import json
import os
import time
from datetime import datetime

# ─── OUTPUT SETUP ────────────────────────────────────────────────────────────
OUTPUT_DIR = "output"
OUTPUT_M3U = os.path.join(OUTPUT_DIR, "mbc_channels.m3u")
OUTPUT_LOG = os.path.join(OUTPUT_DIR, "mbc_fetch_log.json")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── BASE URL ────────────────────────────────────────────────────────────────
BASE = "https://elahmad.org"
PAGE_URL = f"{BASE}/tv/live/shahid_shaka.php?id={{channel_id}}"

# ─── MBC CHANNELS ────────────────────────────────────────────────────────────
# id confirmed from browser URL bar in screenshots
MBC_CHANNELS = [
    {
        "name"    : "MBC 1",
        "id"      : "mbc1",
        "tvg_id"  : "MBC1.ae",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbc1/logo/logo_mbc1.png",
        "group"   : "MBC Group",
    },
    {
        "name"    : "MBC 2",
        "id"      : "mbc2",
        "tvg_id"  : "MBC2.ae",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbc2/logo/logo_mbc2.png",
        "group"   : "MBC Group",
    },
    {
        "name"    : "MBC 3",
        "id"      : "mbc3",
        "tvg_id"  : "MBC3.ae",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbc3/logo/logo_mbc3.png",
        "group"   : "MBC Group",
    },
    {
        "name"    : "MBC 4",
        "id"      : "mbc4",
        "tvg_id"  : "MBC4.ae",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbc4/logo/logo_mbc4.png",
        "group"   : "MBC Group",
    },
    {
        "name"    : "MBC 5",
        "id"      : "mbc5",
        "tvg_id"  : "MBC5.ae",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbc5/logo/logo_mbc5.png",
        "group"   : "MBC Group",
    },
    {
        "name"    : "MBC Drama",
        "id"      : "mbc_drama",
        "tvg_id"  : "MBCDrama.ae",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbcdrama/logo/logo_mbcdrama.png",
        "group"   : "MBC Group",
    },
    {
        "name"    : "MBC Drama Plus",
        "id"      : "mbc_drama_plus",
        "tvg_id"  : "MBCDramaPlus.ae",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbcdramaplus/logo/logo_mbcdramaplus.png",
        "group"   : "MBC Group",
    },
    {
        "name"    : "MBC Action",
        "id"      : "mbc_action",
        "tvg_id"  : "MBCAction.ae",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbcaction/logo/logo_mbcaction.png",
        "group"   : "MBC Group",
    },
    {
        "name"    : "MBC Max",
        "id"      : "mbc_max",
        "tvg_id"  : "MBCMax.ae",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbcmax/logo/logo_mbcmax.png",
        "group"   : "MBC Group",
    },
    {
        "name"    : "MBC Masr",
        "id"      : "mbc_masr",
        "tvg_id"  : "MBCMasr.eg",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbcmasr/logo/logo_mbcmasr.png",
        "group"   : "MBC Group",
    },
    {
        "name"    : "MBC Masr 2",
        "id"      : "mbc_masr2",
        "tvg_id"  : "MBCMasr2.eg",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbcmasr2/logo/logo_mbcmasr2.png",
        "group"   : "MBC Group",
    },
    {
        "name"    : "MBC Iraq",
        "id"      : "mbc_iraq",
        "tvg_id"  : "MBCIraq.iq",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbciraq/logo/logo_mbciraq.png",
        "group"   : "MBC Group",
    },
    {
        "name"    : "MBC Variety",
        "id"      : "mbc_variety",
        "tvg_id"  : "MBCVariety.ae",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbcvariety/logo/logo_mbcvariety.png",
        "group"   : "MBC Group",
    },
    {
        "name"    : "MBC Persia",
        "id"      : "mbc_persia",
        "tvg_id"  : "MBCPersia.ae",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbcpersia/logo/logo_mbcpersia.png",
        "group"   : "MBC Group",
    },
    {
        "name"    : "MBC Bollywood",
        "id"      : "mbc_bollywood",
        "tvg_id"  : "MBCBollywood.ae",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbcbollywood/logo/logo_mbcbollywood.png",
        "group"   : "MBC Group",
    },
    {
        "name"    : "MBC Life",
        "id"      : "mbc_life",
        "tvg_id"  : "MBCLife.ae",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbclife/logo/logo_mbclife.png",
        "group"   : "MBC Group",
    },
    {
        "name"    : "MBC Masr Drama",
        "id"      : "mbc_masr_drama",
        "tvg_id"  : "MBCMasrDrama.eg",
        "logo"    : "https://www.mbc.net/content/dam/mbc/ch/mbcmasrdrama/logo/logo_mbcmasrdrama.png",
        "group"   : "MBC Group",
    },
]

# ─── HEADERS ─────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent"     : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept"         : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Referer"        : f"{BASE}/tv/mbc-stream.php",
    "Origin"         : BASE,
}

# ─── STREAM EXTRACTION PATTERNS ──────────────────────────────────────────────
STREAM_PATTERNS = [
    # Direct m3u8 URLs
    r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
    # file: or src: assignments
    r'(?:file|src|source|url|stream)\s*[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
    # jwplayer setup
    r'jwplayer[^}]+file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
    # HLS source
    r'hls\.loadSource\(["\']([^"\']+\.m3u8[^"\']*)["\']',
    # General quoted URL with m3u8
    r'["\']([^"\']*\.m3u8[^"\']*)["\']',
]

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ─── FETCH CHANNEL ────────────────────────────────────────────────────────────

def fetch_channel(ch: dict) -> str | None:
    """Fetch the channel embed page and extract the m3u8 stream URL."""
    url = PAGE_URL.format(channel_id=ch["id"])
    
    # Also try alternate ID formats
    id_variants = [
        ch["id"],
        ch["id"].replace("_", ""),   # mbc_action → mbcaction
        ch["id"].replace("_", "-"),  # mbc_action → mbc-action
    ]
    
    for variant in id_variants:
        page_url = PAGE_URL.format(channel_id=variant)
        try:
            print(f"  Trying: {page_url}")
            resp = SESSION.get(page_url, timeout=20)
            print(f"  Status: {resp.status_code} | Length: {len(resp.text)}")
            
            if resp.status_code != 200:
                continue
            
            # Check if it's a Cloudflare block
            if "Just a moment" in resp.text or "cf-browser-verification" in resp.text:
                print(f"  ❌ Cloudflare blocked")
                return None
            
            # Try all stream patterns
            for pattern in STREAM_PATTERNS:
                matches = re.findall(pattern, resp.text, re.IGNORECASE)
                for m in matches:
                    m = m.strip()
                    if "m3u8" in m and m.startswith("http"):
                        print(f"  ✅ Found: {m[:80]}")
                        return m
            
            # If page loaded but no stream found, show snippet for debugging
            print(f"  ⚠ Page loaded but no stream URL found")
            print(f"  Preview: {resp.text[200:400]}")
            
        except requests.exceptions.ConnectionError as e:
            print(f"  ❌ Connection error: {e}")
            return None
        except requests.exceptions.Timeout:
            print(f"  ⏱ Timeout")
        except Exception as e:
            print(f"  ⚠ Error: {e}")
        
        time.sleep(1)
    
    return None


# ─── M3U WRITER ──────────────────────────────────────────────────────────────

def write_m3u(results: list):
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("#EXTM3U x-tvg-url=\"https://raw.githubusercontent.com/YOUR_USERNAME/MY-IPTV/main/output/merged_epg.xml\"\n\n")
        for ch, stream_url in results:
            f.write(
                f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" '
                f'tvg-name="{ch["name"]}" '
                f'tvg-logo="{ch["logo"]}" '
                f'group-title="{ch["group"]}",{ch["name"]}\n'
            )
            f.write(f"{stream_url}\n\n")
    print(f"\n✅ Wrote {len(results)} channels → {OUTPUT_M3U}")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print(f"MBC Fetcher v6.0  |  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Source: {BASE}/tv/live/shahid_shaka.php?id={{channel_id}}")
    print("=" * 60)

    found  = []
    failed = []

    for ch in MBC_CHANNELS:
        print(f"\n📺 {ch['name']} (id={ch['id']})")
        stream = fetch_channel(ch)
        if stream:
            found.append((ch, stream))
        else:
            print(f"  ❌ Failed")
            failed.append(ch["name"])

    print("\n" + "=" * 60)
    print(f"RESULTS  ✅ {len(found)} found   ❌ {len(failed)} failed")
    if failed:
        print(f"Failed: {', '.join(failed)}")

    if found:
        write_m3u(found)
    else:
        print("\n⚠ No streams found — elahmad.org may be blocking GitHub IPs (Cloudflare)")

    log = {
        "timestamp"      : datetime.utcnow().isoformat() + "Z",
        "source"         : "elahmad.org/tv/live/shahid_shaka.php",
        "found_count"    : len(found),
        "failed_count"   : len(failed),
        "found_channels" : [ch["name"] for ch, _ in found],
        "failed_channels": failed,
    }
    with open(OUTPUT_LOG, "w") as f:
        json.dump(log, f, indent=2)
    print(f"Log → {OUTPUT_LOG}")


if __name__ == "__main__":
    main()
