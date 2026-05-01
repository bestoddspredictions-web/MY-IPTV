#!/usr/bin/env python3
"""
mbc_fetcher.py v8.0
Uses Selenium + undetected-chromedriver to:
1. Bypass Cloudflare (already solved by cloudscraper in v7)
2. Execute JavaScript on the page
3. Capture the dynamically loaded m3u8 stream URL

Strategy:
- Load each channel page in a real headless Chrome browser
- Wait for the video player to initialize
- Intercept network requests to find the m3u8 URL
- OR scan the page source after JS execution
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    {"name": "MBC 1",         "id": "mbc1",          "tvg_id": "MBC1.ae",         "logo": "https://www.mbc.net/content/dam/mbc/ch/mbc1/logo/logo_mbc1.png",              "group": "MBC Group"},
    {"name": "MBC 2",         "id": "mbc2",          "tvg_id": "MBC2.ae",         "logo": "https://www.mbc.net/content/dam/mbc/ch/mbc2/logo/logo_mbc2.png",              "group": "MBC Group"},
    {"name": "MBC 3",         "id": "mbc3",          "tvg_id": "MBC3.ae",         "logo": "https://www.mbc.net/content/dam/mbc/ch/mbc3/logo/logo_mbc3.png",              "group": "MBC Group"},
    {"name": "MBC 4",         "id": "mbc4",          "tvg_id": "MBC4.ae",         "logo": "https://www.mbc.net/content/dam/mbc/ch/mbc4/logo/logo_mbc4.png",              "group": "MBC Group"},
    {"name": "MBC 5",         "id": "mbc5",          "tvg_id": "MBC5.ae",         "logo": "https://www.mbc.net/content/dam/mbc/ch/mbc5/logo/logo_mbc5.png",              "group": "MBC Group"},
    {"name": "MBC Drama",     "id": "mbc_drama",     "tvg_id": "MBCDrama.ae",     "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcdrama/logo/logo_mbcdrama.png",      "group": "MBC Group"},
    {"name": "MBC Drama Plus","id": "mbc_drama_plus","tvg_id": "MBCDramaPlus.ae", "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcdramaplus/logo/logo_mbcdramaplus.png","group": "MBC Group"},
    {"name": "MBC Action",    "id": "mbc_action",    "tvg_id": "MBCAction.ae",    "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcaction/logo/logo_mbcaction.png",    "group": "MBC Group"},
    {"name": "MBC Max",       "id": "mbc_max",       "tvg_id": "MBCMax.ae",       "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcmax/logo/logo_mbcmax.png",          "group": "MBC Group"},
    {"name": "MBC Masr",      "id": "mbc_masr",      "tvg_id": "MBCMasr.eg",      "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcmasr/logo/logo_mbcmasr.png",        "group": "MBC Group"},
    {"name": "MBC Masr 2",    "id": "mbc_masr2",     "tvg_id": "MBCMasr2.eg",     "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcmasr2/logo/logo_mbcmasr2.png",      "group": "MBC Group"},
    {"name": "MBC Iraq",      "id": "mbc_iraq",      "tvg_id": "MBCIraq.iq",      "logo": "https://www.mbc.net/content/dam/mbc/ch/mbciraq/logo/logo_mbciraq.png",        "group": "MBC Group"},
    {"name": "MBC Variety",   "id": "mbc_variety",   "tvg_id": "MBCVariety.ae",   "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcvariety/logo/logo_mbcvariety.png",  "group": "MBC Group"},
    {"name": "MBC Persia",    "id": "mbc_persia",    "tvg_id": "MBCPersia.ae",    "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcpersia/logo/logo_mbcpersia.png",    "group": "MBC Group"},
    {"name": "MBC Bollywood", "id": "mbc_bollywood", "tvg_id": "MBCBollywood.ae", "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcbollywood/logo/logo_mbcbollywood.png","group": "MBC Group"},
    {"name": "MBC Life",      "id": "mbc_life",      "tvg_id": "MBCLife.ae",      "logo": "https://www.mbc.net/content/dam/mbc/ch/mbclife/logo/logo_mbclife.png",        "group": "MBC Group"},
    {"name": "MBC Masr Drama","id": "mbc_masr_drama","tvg_id": "MBCMasrDrama.eg", "logo": "https://www.mbc.net/content/dam/mbc/ch/mbcmasrdrama/logo/logo_mbcmasrdrama.png","group": "MBC Group"},
]

# ─── STREAM EXTRACTION PATTERNS ──────────────────────────────────────────────
STREAM_PATTERNS = [
    r'(https?://[^\s"\'\\<>]+\.m3u8[^\s"\'\\<>]*)',
    r'(?:file|src|source|url|stream)\s*[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
    r'hls\.loadSource\(["\']([^"\']+\.m3u8[^"\']*)["\']',
    r'["\']([^"\']*\.m3u8[^"\']*)["\']',
]

# ─── SELENIUM SETUP ───────────────────────────────────────────────────────────
def make_driver():
    """Create undetected Chrome in headless mode."""
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=en-US")
    
    # Enable performance logging to capture network requests
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = uc.Chrome(options=options, use_subprocess=True)
    return driver


# ─── EXTRACT FROM NETWORK LOGS ───────────────────────────────────────────────
def extract_from_network_logs(driver) -> str | None:
    """Scan Chrome network logs for m3u8 requests."""
    try:
        logs = driver.get_log("performance")
        for log in logs:
            msg = json.loads(log["message"])["message"]
            if msg.get("method") == "Network.requestWillBeSent":
                url = msg.get("params", {}).get("request", {}).get("url", "")
                if ".m3u8" in url and url.startswith("http"):
                    print(f"  ✅ Found in network log: {url[:80]}")
                    return url
    except Exception as e:
        print(f"  ⚠ Network log error: {e}")
    return None


# ─── EXTRACT FROM PAGE SOURCE ─────────────────────────────────────────────────
def extract_from_source(page_source: str) -> str | None:
    """Scan rendered page source for m3u8 URLs."""
    for pattern in STREAM_PATTERNS:
        matches = re.findall(pattern, page_source, re.IGNORECASE)
        for m in matches:
            m = m.strip()
            if "m3u8" in m and m.startswith("http"):
                return m
    return None


# ─── EXTRACT FROM JS VARIABLES ───────────────────────────────────────────────
def extract_from_js(driver) -> str | None:
    """Execute JS in browser to find stream URL from player variables."""
    js_attempts = [
        # JWPlayer
        "return jwplayer().getPlaylistItem().file",
        "return jwplayer().getPlaylistItem()['file']",
        # HLS.js
        "return window.hls && window.hls.url",
        # Video element src
        "return document.querySelector('video') && document.querySelector('video').src",
        # Common variable names
        "return window.streamUrl",
        "return window.hlsUrl",
        "return window.videoUrl",
        "return window.liveUrl",
    ]
    for js in js_attempts:
        try:
            result = driver.execute_script(js)
            if result and ".m3u8" in str(result):
                print(f"  ✅ Found via JS: {str(result)[:80]}")
                return result
        except Exception:
            pass
    return None


# ─── FETCH CHANNEL ────────────────────────────────────────────────────────────
def fetch_channel(driver, ch: dict) -> str | None:
    """Load channel page in Selenium and extract stream URL."""
    url = PAGE_URL.format(channel_id=ch["id"])
    print(f"  Loading: {url}")

    try:
        driver.get(url)

        # Wait for page to load
        time.sleep(5)

        # Check for Cloudflare
        if "Just a moment" in driver.page_source:
            print(f"  ⏳ Cloudflare challenge detected, waiting...")
            time.sleep(10)

        # Strategy 1: Network logs (most reliable)
        stream = extract_from_network_logs(driver)
        if stream:
            return stream

        # Strategy 2: Page source after JS execution
        stream = extract_from_source(driver.page_source)
        if stream:
            print(f"  ✅ Found in page source: {stream[:80]}")
            return stream

        # Strategy 3: JS variable extraction
        stream = extract_from_js(driver)
        if stream:
            return stream

        # Strategy 4: Wait longer and try again (some players load slowly)
        print(f"  ⏳ Waiting extra 8s for player to initialize...")
        time.sleep(8)

        stream = extract_from_network_logs(driver)
        if stream:
            return stream

        stream = extract_from_source(driver.page_source)
        if stream:
            print(f"  ✅ Found after wait: {stream[:80]}")
            return stream

        stream = extract_from_js(driver)
        if stream:
            return stream

        # Debug: print snippet of page source
        print(f"  ⚠ No stream found. Page title: {driver.title}")
        print(f"  Snippet: {driver.page_source[500:800]}")

    except Exception as e:
        print(f"  ❌ Error: {e}")

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
    print(f"MBC Fetcher v8.0  |  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("Method: Selenium + undetected-chromedriver")
    print("=" * 60)

    print("\n🌐 Starting Chrome browser...")
    driver = make_driver()
    print("  Browser started ✅")

    # Warm up — visit homepage first so Cloudflare trusts the session
    print("\n🔥 Warming up session on elahmad.org...")
    driver.get(BASE)
    time.sleep(4)
    print(f"  Homepage loaded: {driver.title}")

    found  = []
    failed = []

    try:
        for ch in MBC_CHANNELS:
            print(f"\n📺 {ch['name']} (id={ch['id']})")
            stream = fetch_channel(driver, ch)
            if stream:
                found.append((ch, stream))
            else:
                print(f"  ❌ Failed")
                failed.append(ch["name"])
            time.sleep(2)

    finally:
        driver.quit()
        print("\n🔒 Browser closed")

    print("\n" + "=" * 60)
    print(f"RESULTS  ✅ {len(found)} found   ❌ {len(failed)} failed")
    if failed:
        print(f"Failed: {', '.join(failed)}")

    if found:
        write_m3u(found)
    else:
        print("\n⚠ No streams found — check log for details")

    log = {
        "timestamp"      : datetime.utcnow().isoformat() + "Z",
        "method"         : "selenium-undetected-chromedriver",
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
