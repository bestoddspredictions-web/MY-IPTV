#!/usr/bin/env python3
"""
mbc_fetcher.py v9.0
Uses Playwright (headless Chromium) to render JS pages on elahmad.org
and capture the dynamically loaded m3u8 stream URLs.
Playwright is purpose-built for GitHub Actions — no Chrome install needed.
"""

import re
import json
import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

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
    {"name": "MBC 1",         "id": "mbc1",          "tvg_id": "MBC1.ae",          "logo": "https://www.mbc.net/content/dam/mbc/ch/mbc1/logo/logo_mbc1.png",               "group": "MBC Group"},
    {"name": "MBC 2",         "id": "mbc2",          "tvg_id": "MBC2.ae",          "logo": "https://www.mbc.net/content/dam/mbc/ch/mbc2/logo/logo_mbc2.png",               "group": "MBC Group"},
    {"name": "MBC 3",         "id": "mbc3",          "tvg_id": "MBC3.ae",          "logo": "https://www.mbc.net/content/dam/mbc/ch/mbc3/logo/logo_mbc3.png",               "group": "MBC Group"},
    {"name": "MBC 4",         "id": "mbc4",          "tvg_id": "MBC4.ae",          "logo": "https://www.mbc.net/content/dam/mbc/ch/mbc4/logo/logo_mbc4.png",               "group": "MBC Group"},
    {"name": "MBC 5",         "id": "mbc5",          "tvg_id": "MBC5.ae",          "logo": "https://www.mbc.net/content/dam/mbc/ch/mbc5/logo/logo_mbc5.png",               "group": "MBC Group"},
    {"name": "MBC Drama",     "id": "mbc_drama",     "tvg_id": "MBCDrama.ae",      "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcdrama/logo/logo_mbcdrama.png",       "group": "MBC Group"},
    {"name": "MBC Drama Plus","id": "mbc_drama_plus","tvg_id": "MBCDramaPlus.ae",  "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcdramaplus/logo/logo_mbcdramaplus.png","group": "MBC Group"},
    {"name": "MBC Action",    "id": "mbc_action",    "tvg_id": "MBCAction.ae",     "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcaction/logo/logo_mbcaction.png",     "group": "MBC Group"},
    {"name": "MBC Max",       "id": "mbc_max",       "tvg_id": "MBCMax.ae",        "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcmax/logo/logo_mbcmax.png",           "group": "MBC Group"},
    {"name": "MBC Masr",      "id": "mbc_masr",      "tvg_id": "MBCMasr.eg",       "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcmasr/logo/logo_mbcmasr.png",         "group": "MBC Group"},
    {"name": "MBC Masr 2",    "id": "mbc_masr2",     "tvg_id": "MBCMasr2.eg",      "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcmasr2/logo/logo_mbcmasr2.png",       "group": "MBC Group"},
    {"name": "MBC Iraq",      "id": "mbc_iraq",      "tvg_id": "MBCIraq.iq",       "logo": "https://www.mbc.net/content/dam/mbc/ch/mbciraq/logo/logo_mbciraq.png",         "group": "MBC Group"},
    {"name": "MBC Variety",   "id": "mbc_variety",   "tvg_id": "MBCVariety.ae",    "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcvariety/logo/logo_mbcvariety.png",   "group": "MBC Group"},
    {"name": "MBC Persia",    "id": "mbc_persia",    "tvg_id": "MBCPersia.ae",     "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcpersia/logo/logo_mbcpersia.png",     "group": "MBC Group"},
    {"name": "MBC Bollywood", "id": "mbc_bollywood", "tvg_id": "MBCBollywood.ae",  "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcbollywood/logo/logo_mbcbollywood.png","group": "MBC Group"},
    {"name": "MBC Life",      "id": "mbc_life",      "tvg_id": "MBCLife.ae",       "logo": "https://www.mbc.net/content/dam/mbc/ch/mbclife/logo/logo_mbclife.png",         "group": "MBC Group"},
    {"name": "MBC Masr Drama","id": "mbc_masr_drama","tvg_id": "MBCMasrDrama.eg",  "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcmasrdrama/logo/logo_mbcmasrdrama.png","group": "MBC Group"},
]

# ─── FETCH CHANNEL ────────────────────────────────────────────────────────────
def fetch_channel(page, ch: dict) -> str | None:
    """Load channel page with Playwright and capture m3u8 from network requests."""
    url    = PAGE_URL.format(channel_id=ch["id"])
    stream = None

    # Intercept all network requests — catch m3u8 before page finishes loading
    def handle_request(request):
        nonlocal stream
        if ".m3u8" in request.url and stream is None:
            print(f"  ✅ Intercepted: {request.url[:80]}")
            stream = request.url

    page.on("request", handle_request)

    try:
        print(f"  Loading: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Wait for JS player to initialize and fire requests
        page.wait_for_timeout(8000)

        if stream:
            return stream

        # Strategy 2: scan rendered page source
        content = page.content()
        matches = re.findall(r'(https?://[^\s"\'\\<>]+\.m3u8[^\s"\'\\<>]*)', content)
        if matches:
            print(f"  ✅ Found in source: {matches[0][:80]}")
            return matches[0]

        # Strategy 3: query JS player objects
        js_queries = [
            "() => jwplayer && jwplayer().getPlaylistItem() && jwplayer().getPlaylistItem().file",
            "() => document.querySelector('video') && document.querySelector('video').src",
            "() => window.streamUrl || window.hlsUrl || window.videoUrl || null",
        ]
        for js in js_queries:
            try:
                result = page.evaluate(js)
                if result and ".m3u8" in str(result):
                    print(f"  ✅ Found via JS: {str(result)[:80]}")
                    return result
            except Exception:
                pass

        # Strategy 4: wait more and retry network
        print(f"  ⏳ Waiting extra 10s...")
        page.wait_for_timeout(10000)
        if stream:
            return stream

        # Final debug info
        print(f"  ⚠ No stream found. Title: {page.title()}")
        print(f"  Snippet: {page.content()[400:700]}")

    except PlaywrightTimeout:
        print(f"  ⏱ Page load timeout")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    finally:
        page.remove_listener("request", handle_request)

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
    print(f"MBC Fetcher v9.0  |  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("Method: Playwright (headless Chromium)")
    print("=" * 60)

    found  = []
    failed = []

    with sync_playwright() as p:
        print("\n🌐 Launching Chromium...")
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )

        page = context.new_page()

        # Warm up — visit homepage first
        print("\n🔥 Warming up on elahmad.org...")
        try:
            page.goto(BASE, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)
            print(f"  Homepage: {page.title()}")
        except Exception as e:
            print(f"  Warmup error (continuing): {e}")

        for ch in MBC_CHANNELS:
            print(f"\n📺 {ch['name']} (id={ch['id']})")
            stream = fetch_channel(page, ch)
            if stream:
                found.append((ch, stream))
            else:
                failed.append(ch["name"])
            time.sleep(2)

        browser.close()
        print("\n🔒 Browser closed")

    print("\n" + "=" * 60)
    print(f"RESULTS  ✅ {len(found)} found   ❌ {len(failed)} failed")
    if failed:
        print(f"Failed: {', '.join(failed)}")

    if found:
        write_m3u(found)
    else:
        print("\n⚠ No streams found")

    log = {
        "timestamp"      : datetime.utcnow().isoformat() + "Z",
        "method"         : "playwright-chromium",
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
