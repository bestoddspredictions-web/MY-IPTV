#!/usr/bin/env python3
"""
mbc_fetcher.py v7.0
Uses cloudscraper to bypass Cloudflare protection on elahmad.org
Fetches each MBC channel page and extracts the m3u8 stream URL.
"""

import cloudscraper
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
BASE     = "https://elahmad.org"
PAGE_URL = f"{BASE}/tv/live/shahid_shaka.php?id={{channel_id}}"

# ─── MBC CHANNELS ────────────────────────────────────────────────────────────
MBC_CHANNELS = [
    {"name": "MBC 1",        "id": "mbc1",         "tvg_id": "MBC1.ae",        "logo": "https://www.mbc.net/content/dam/mbc/ch/mbc1/logo/logo_mbc1.png",           "group": "MBC Group"},
    {"name": "MBC 2",        "id": "mbc2",         "tvg_id": "MBC2.ae",        "logo": "https://www.mbc.net/content/dam/mbc/ch/mbc2/logo/logo_mbc2.png",           "group": "MBC Group"},
    {"name": "MBC 3",        "id": "mbc3",         "tvg_id": "MBC3.ae",        "logo": "https://www.mbc.net/content/dam/mbc/ch/mbc3/logo/logo_mbc3.png",           "group": "MBC Group"},
    {"name": "MBC 4",        "id": "mbc4",         "tvg_id": "MBC4.ae",        "logo": "https://www.mbc.net/content/dam/mbc/ch/mbc4/logo/logo_mbc4.png",           "group": "MBC Group"},
    {"name": "MBC 5",        "id": "mbc5",         "tvg_id": "MBC5.ae",        "logo": "https://www.mbc.net/content/dam/mbc/ch/mbc5/logo/logo_mbc5.png",           "group": "MBC Group"},
    {"name": "MBC Drama",    "id": "mbc_drama",    "tvg_id": "MBCDrama.ae",    "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcdrama/logo/logo_mbcdrama.png",   "group": "MBC Group"},
    {"name": "MBC Drama Plus","id": "mbc_drama_plus","tvg_id": "MBCDramaPlus.ae","logo": "https://www.mbc.net/content/dam/mbc/ch/mbcdramaplus/logo/logo_mbcdramaplus.png","group": "MBC Group"},
    {"name": "MBC Action",   "id": "mbc_action",   "tvg_id": "MBCAction.ae",   "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcaction/logo/logo_mbcaction.png", "group": "MBC Group"},
    {"name": "MBC Max",      "id": "mbc_max",      "tvg_id": "MBCMax.ae",      "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcmax/logo/logo_mbcmax.png",       "group": "MBC Group"},
    {"name": "MBC Masr",     "id": "mbc_masr",     "tvg_id": "MBCMasr.eg",     "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcmasr/logo/logo_mbcmasr.png",     "group": "MBC Group"},
    {"name": "MBC Masr 2",   "id": "mbc_masr2",    "tvg_id": "MBCMasr2.eg",    "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcmasr2/logo/logo_mbcmasr2.png",   "group": "MBC Group"},
    {"name": "MBC Iraq",     "id": "mbc_iraq",     "tvg_id": "MBCIraq.iq",     "logo": "https://www.mbc.net/content/dam/mbc/ch/mbciraq/logo/logo_mbciraq.png",     "group": "MBC Group"},
    {"name": "MBC Variety",  "id": "mbc_variety",  "tvg_id": "MBCVariety.ae",  "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcvariety/logo/logo_mbcvariety.png","group": "MBC Group"},
    {"name": "MBC Persia",   "id": "mbc_persia",   "tvg_id": "MBCPersia.ae",   "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcpersia/logo/logo_mbcpersia.png", "group": "MBC Group"},
    {"name": "MBC Bollywood","id": "mbc_bollywood","tvg_id": "MBCBollywood.ae","logo": "https://www.mbc.net/content/dam/mbc/ch/mbcbollywood/logo/logo_mbcbollywood.png","group": "MBC Group"},
    {"name": "MBC Life",     "id": "mbc_life",     "tvg_id": "MBCLife.ae",     "logo": "https://www.mbc.net/content/dam/mbc/ch/mbclife/logo/logo_mbclife.png",     "group": "MBC Group"},
    {"name": "MBC Masr Drama","id": "mbc_masr_drama","tvg_id": "MBCMasrDrama.eg","logo": "https://www.mbc.net/content/dam/mbc/ch/mbcmasrdrama/logo/logo_mbcmasrdrama.png","group": "MBC Group"},
]

# ─── STREAM EXTRACTION PATTERNS ──────────────────────────────────────────────
STREAM_PATTERNS = [
    r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
    r'(?:file|src|source|url|stream)\s*[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
    r'jwplayer[^}]+file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
    r'hls\.loadSource\(["\']([^"\']+\.m3u8[^"\']*)["\']',
    r'["\']([^"\']*\.m3u8[^"\']*)["\']',
]

# ─── SCRAPER SETUP ───────────────────────────────────────────────────────────
def make_scraper():
    """Create a cloudscraper instance that mimics a real Chrome browser."""
    return cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "mobile": False,
        }
    )

# ─── FETCH CHANNEL ────────────────────────────────────────────────────────────
def fetch_channel(scraper, ch: dict) -> str | None:
    """Fetch channel page and extract m3u8 URL."""
    id_variants = [
        ch["id"],
        ch["id"].replace("_", ""),
        ch["id"].replace("_", "-"),
    ]

    for variant in id_variants:
        url = PAGE_URL.format(channel_id=variant)
        try:
            print(f"  Trying: {url}")
            resp = scraper.get(url, timeout=30)
            print(f"  Status: {resp.status_code} | Length: {len(resp.text)}")

            if resp.status_code != 200:
                print(f"  ❌ Status {resp.status_code}")
                continue

            if "Just a moment" in resp.text or "cf-browser-verification" in resp.text:
                print(f"  ❌ Cloudflare JS challenge not solved")
                continue

            # Extract stream URL
            for pattern in STREAM_PATTERNS:
                matches = re.findall(pattern, resp.text, re.IGNORECASE)
                for m in matches:
                    m = m.strip()
                    if "m3u8" in m and m.startswith("http"):
                        print(f"  ✅ Found: {m[:80]}")
                        return m

            print(f"  ⚠ Page loaded but no stream URL found")
            print(f"  Snippet: {resp.text[300:500]}")

        except Exception as e:
            print(f"  ⚠ Error: {e}")

        time.sleep(2)

    return None

# ─── M3U WRITER ──────────────────────────────────────────────────────────────
def write_m3u(results: list):
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n\n")
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
    print(f"MBC Fetcher v7.0  |  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("Method: cloudscraper (Cloudflare bypass)")
    print("=" * 60)

    scraper = make_scraper()
    found   = []
    failed  = []

    for ch in MBC_CHANNELS:
        print(f"\n📺 {ch['name']} (id={ch['id']})")
        stream = fetch_channel(scraper, ch)
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
        print("\n⚠ cloudscraper could not bypass Cloudflare — proceeding to Step 2 (Selenium)")

    log = {
        "timestamp"      : datetime.utcnow().isoformat() + "Z",
        "method"         : "cloudscraper",
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
