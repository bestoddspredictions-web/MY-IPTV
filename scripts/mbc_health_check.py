#!/usr/bin/env python3
"""
mbc_health_check.py v1.0
Daily health check for MBC static stream URLs.
Tests each URL and reports which are alive/dead.
Does NOT update the playlist — just flags broken URLs so you can fix manually.
"""

import requests
import json
import os
from datetime import datetime

OUTPUT_DIR  = "output"
HEALTH_LOG  = os.path.join(OUTPUT_DIR, "mbc_health_log.json")
M3U_FILE    = os.path.join(OUTPUT_DIR, "mbc_channels.m3u")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── STREAM URLs ─────────────────────────────────────────────────────────────
MBC_STREAMS = [
    {"name": "MBC 2",        "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-2/51db9d7fa48a27d051f1eecb68069151/index.mpd"},
    {"name": "MBC 3",        "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-3/946fc698e47c30df2193962ca541d868/index.mpd"},
    {"name": "MBC 4",        "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-4/24f134f1cd63db9346439e96b86ca6ed/index.m3u8"},
    {"name": "MBC 5",        "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-5/ee6b000cee0629411b666ab26cb13e9b/index.m3u8"},
    {"name": "MBC Drama",    "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-drama/2c28a458e2f3253e678b07ac7d13fe71/index.m3u8"},
    {"name": "MBC Drama Plus","url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-plus-drama/e37251ec2aac8f6c98f75cd0fa37cd28/index.m3u8"},
    {"name": "MBC Action",   "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-action/8ea6ca1108d03e03da5e61372354f5c8/index.mpd"},
    {"name": "MBC Max",      "url": "https://shd-gcp-live.akamaized.net/live/bitmovin-mbc-max/b628d2bbaee0431a17859963edf2975f/index.mpd"},
    {"name": "MBC Masr",     "url": "https://shd-gcp-live.lg.mncdn.com/live/bitmovin-mbc-masr/956eac069c78a35d47245db6cdbb1575/index.m3u8"},
    {"name": "MBC Masr 2",   "url": "https://shd-gcp-live.edgenextcdn.net/live/bitmovin-mbc-masr-2/7eaa7c0393e9a9637ae311aac75eb40e/index.mpd"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

def check_stream(name: str, url: str) -> dict:
    try:
        resp = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
        alive = resp.status_code in (200, 206)
        print(f"  {'✅' if alive else '❌'} {name} — HTTP {resp.status_code}")
        return {"name": name, "url": url, "status": resp.status_code, "alive": alive}
    except Exception as e:
        print(f"  ❌ {name} — Error: {e}")
        return {"name": name, "url": url, "status": 0, "alive": False, "error": str(e)}

def main():
    print("=" * 60)
    print(f"MBC Health Check  |  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    results = []
    for ch in MBC_STREAMS:
        print(f"\n📺 {ch['name']}")
        result = check_stream(ch["name"], ch["url"])
        results.append(result)

    alive  = [r for r in results if r["alive"]]
    dead   = [r for r in results if not r["alive"]]

    print(f"\n{'=' * 60}")
    print(f"RESULTS  ✅ {len(alive)} alive   ❌ {len(dead)} dead")

    if dead:
        print(f"\n⚠ BROKEN CHANNELS — UPDATE NEEDED:")
        for r in dead:
            print(f"  - {r['name']} (HTTP {r['status']})")
        print(f"\n  To fix: visit elahmad.org/tv/live/shahid_shaka.php?id=CHANNEL_ID")
        print(f"  Run the console command to get new URL, update mbc_channels.m3u")

    log = {
        "timestamp"   : datetime.utcnow().isoformat() + "Z",
        "alive_count" : len(alive),
        "dead_count"  : len(dead),
        "alive"       : [r["name"] for r in alive],
        "dead"        : [{"name": r["name"], "status": r["status"]} for r in dead],
        "all_results" : results,
    }
    with open(HEALTH_LOG, "w") as f:
        json.dump(log, f, indent=2)
    print(f"\nLog → {HEALTH_LOG}")

    # Exit with error code if any dead — makes GitHub Actions show warning
    if dead:
        exit(1)

if __name__ == "__main__":
    main()
