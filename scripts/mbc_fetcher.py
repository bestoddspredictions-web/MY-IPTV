#!/usr/bin/env python3
"""
mbc_fetcher.py v4.0
Fetches live HLS stream URLs for all MBC Group channels from elahmad.com
Uses the mobile API endpoint (glarb.php) discovered via network inspection.

Endpoint : POST http://www.elahmad.com/tv/mobiletv/glarb.php
Headers  : Origin  → http://www.elahmad.com
           Referer → http://www.elahmad.com/tv/extension.php?id={channel_id}

Output   : output/mbc_channels.m3u
           output/mbc_fetch_log.json
"""

import requests
import re
import json
import os
import time
from datetime import datetime

# ─── OUTPUT SETUP ────────────────────────────────────────────────────────────
OUTPUT_DIR  = "output"
OUTPUT_M3U  = os.path.join(OUTPUT_DIR, "mbc_channels.m3u")
OUTPUT_LOG  = os.path.join(OUTPUT_DIR, "mbc_fetch_log.json")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── API CONFIG ──────────────────────────────────────────────────────────────
BASE_URL      = "http://www.elahmad.com"
API_ENDPOINT  = f"{BASE_URL}/tv/mobiletv/glarb.php"
REFERER_TMPL  = f"{BASE_URL}/tv/extension.php?id={{channel_id}}"

# ─── SESSION HEADERS ─────────────────────────────────────────────────────────
# Origin and Referer are REQUIRED — removing either causes the server to reject
# the request and return nothing (same as pasting the URL directly in VLC).
BASE_HEADERS = {
    "User-Agent"      : "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36",
    "Accept"          : "application/json, text/plain, */*",
    "Accept-Language" : "en-US,en;q=0.9,ar;q=0.8",
    "Origin"          : BASE_URL,
    "Connection"      : "keep-alive",
}

SESSION = requests.Session()
SESSION.headers.update(BASE_HEADERS)

# ─── MBC CHANNELS ────────────────────────────────────────────────────────────
# id_candidates: list of IDs to try in order (first working one wins)
# Confirmed IDs from network inspection: mbc2tv, mbc_max, mbc_action
MBC_CHANNELS = [
    {
        "name"         : "MBC 1",
        "tvg_id"       : "mbc1.sa",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbc1/logo/logo_mbc1.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc1tv", "mbc1", "mbc_1"],
    },
    {
        "name"         : "MBC 2",
        "tvg_id"       : "mbc2.sa",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbc2/logo/logo_mbc2.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc2tv", "mbc2", "mbc_2"],   # mbc2tv confirmed
    },
    {
        "name"         : "MBC 3",
        "tvg_id"       : "mbc3.sa",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbc3/logo/logo_mbc3.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc3tv", "mbc3", "mbc_3"],
    },
    {
        "name"         : "MBC 4",
        "tvg_id"       : "mbc4.sa",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbc4/logo/logo_mbc4.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc4tv", "mbc4", "mbc_4"],
    },
    {
        "name"         : "MBC 5",
        "tvg_id"       : "mbc5.sa",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbc5/logo/logo_mbc5.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc5tv", "mbc5", "mbc_5"],
    },
    {
        "name"         : "MBC Drama",
        "tvg_id"       : "mbcdrama.sa",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbcdrama/logo/logo_mbcdrama.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc_drama", "mbcdramatv", "mbcdrama"],
    },
    {
        "name"         : "MBC Drama Plus",
        "tvg_id"       : "mbcdramaplus.sa",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbcdramaplus/logo/logo_mbcdramaplus.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc_drama_plus", "mbcdramaplus", "drama_plus"],
    },
    {
        "name"         : "MBC Action",
        "tvg_id"       : "mbcaction.sa",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbcaction/logo/logo_mbcaction.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc_action", "mbcaction", "mbcactiontv"],   # mbc_action confirmed
    },
    {
        "name"         : "MBC Max",
        "tvg_id"       : "mbcmax.sa",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbcmax/logo/logo_mbcmax.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc_max", "mbcmax", "mbcmaxtv"],            # mbc_max confirmed
    },
    {
        "name"         : "MBC Masr",
        "tvg_id"       : "mbcmasr.eg",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbcmasr/logo/logo_mbcmasr.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc_masr", "mbcmasrtv", "mbcmasr"],
    },
    {
        "name"         : "MBC Masr 2",
        "tvg_id"       : "mbcmasr2.eg",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbcmasr2/logo/logo_mbcmasr2.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc_masr2", "mbcmasr2tv", "mbcmasr2"],
    },
    {
        "name"         : "MBC Iraq",
        "tvg_id"       : "mbciraq.iq",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbciraq/logo/logo_mbciraq.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc_iraq", "mbciraqtv", "mbciraq"],
    },
    {
        "name"         : "MBC Variety",
        "tvg_id"       : "mbcvariety.sa",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbcvariety/logo/logo_mbcvariety.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc_variety", "mbcvariety", "mbcvarietytv"],
    },
    {
        "name"         : "MBC Persia",
        "tvg_id"       : "mbcpersia.sa",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbcpersia/logo/logo_mbcpersia.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc_persia", "mbcpersia", "mbcpersiatv"],
    },
    {
        "name"         : "MBC Bollywood",
        "tvg_id"       : "mbcbollywood.sa",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbcbollywood/logo/logo_mbcbollywood.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc_bollywood", "mbcbollywood", "mbcbollywoodtv"],
    },
    {
        "name"         : "MBC Life",
        "tvg_id"       : "mbclife.sa",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbclife/logo/logo_mbclife.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc_life", "mbclife", "mbclifetv"],
    },
    {
        "name"         : "MBC Masr Drama",
        "tvg_id"       : "mbcmasrdrama.eg",
        "logo"         : "https://www.mbc.net/content/dam/mbc/ch/mbcmasrdrama/logo/logo_mbcmasrdrama.png",
        "group"        : "MBC Group",
        "id_candidates": ["mbc_masr_drama", "mbcmasrdrama", "masrdrama"],
    },
]

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def extract_stream_url(response_text: str) -> str | None:
    """Extract an HLS .m3u8 URL from the API response."""
    # Try JSON first
    try:
        data = json.loads(response_text)
        for key in ("url", "stream", "link", "hls", "src", "source", "file"):
            if key in data and isinstance(data[key], str) and "http" in data[key]:
                return data[key].strip()
        for val in data.values():
            if isinstance(val, dict):
                for k, v in val.items():
                    if isinstance(v, str) and ".m3u8" in v:
                        return v.strip()
    except (json.JSONDecodeError, AttributeError):
        pass

    # Fallback: regex scan for any .m3u8 URL in raw response
    matches = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', response_text)
    if matches:
        return matches[0].strip()

    return None


def try_fetch_channel(channel_id: str) -> str | None:
    """POST to the glarb.php mobile API with the given channel_id."""
    referer = REFERER_TMPL.format(channel_id=channel_id)
    headers = {**BASE_HEADERS, "Referer": referer}

    # Try multiple POST body formats
    post_bodies = [
        {"id"     : channel_id},
        {"ch"     : channel_id},
        {"channel": channel_id},
        {"chid"   : channel_id},
    ]

    for body in post_bodies:
        try:
            resp = SESSION.post(API_ENDPOINT, data=body, headers=headers, timeout=15)
            if resp.status_code == 200 and resp.text.strip():
                stream = extract_stream_url(resp.text)
                if stream:
                    return stream
        except requests.exceptions.ConnectionError:
            print(f"    ❌ Connection error — site may be blocked. Enable VPN and retry.")
            return None
        except requests.exceptions.Timeout:
            print(f"    ⏱ Timeout with body {body}")
        except Exception as e:
            print(f"    ⚠ Error: {e}")

    return None


def fetch_channel(ch: dict) -> str | None:
    """Try all candidate IDs for a channel, return first working stream URL."""
    for cid in ch["id_candidates"]:
        print(f"  Trying id: {cid}")
        stream = try_fetch_channel(cid)
        if stream:
            print(f"  ✅ Found stream with id='{cid}'")
            return stream
        time.sleep(0.4)
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
    print(f"✅ Wrote {len(results)} channels → {OUTPUT_M3U}")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print(f"MBC Fetcher v4.0  |  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Endpoint : {API_ENDPOINT}")
    print("=" * 60)

    found  = []
    failed = []

    for ch in MBC_CHANNELS:
        print(f"\n📺 {ch['name']}")
        stream = fetch_channel(ch)
        if stream:
            found.append((ch, stream))
        else:
            print(f"  ❌ No stream found")
            failed.append(ch["name"])

    print("\n" + "=" * 60)
    print(f"RESULTS  ✅ {len(found)} found   ❌ {len(failed)} failed")
    if failed:
        print(f"Failed: {', '.join(failed)}")

    if found:
        write_m3u(found)
    else:
        print("\n⚠  No streams found.")
        print("   → If elahmad.com is ISP-blocked locally, enable VPN and re-run")
        print("   → Or push to GitHub — Actions servers are not ISP-blocked")

    log = {
        "timestamp"      : datetime.utcnow().isoformat() + "Z",
        "endpoint"       : API_ENDPOINT,
        "found_count"    : len(found),
        "failed_count"   : len(failed),
        "found_channels" : [ch["name"] for ch, _ in found],
        "failed_channels": failed,
    }
    with open(OUTPUT_LOG, "w") as f:
        json.dump(log, f, indent=2)
    print(f"Log saved → {OUTPUT_LOG}")


if __name__ == "__main__":
    main()
