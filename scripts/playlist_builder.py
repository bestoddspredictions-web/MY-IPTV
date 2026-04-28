#!/usr/bin/env python3
"""
Script 1 — Playlist Builder v1.3
Fetches channels + streams from iptv-org API.
Includes all streams (status field removed from API).
Outputs: output/merged_channels.m3u
Run: Weekly via GitHub Actions
"""

import requests
import os
import sys
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

API_BASE    = "https://iptv-org.github.io/api"
OUTPUT_DIR  = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "merged_channels.m3u")
HEADERS     = {"User-Agent": "Mozilla/5.0"}

# ─────────────────────────────────────────────
# FETCH API DATA
# ─────────────────────────────────────────────

def fetch_json(endpoint: str) -> list:
    url = f"{API_BASE}/{endpoint}"
    print(f"  [↓] Fetching {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            print(f"  [!] Unexpected response format from {endpoint}")
            return []
        return data
    except requests.exceptions.ConnectionError:
        print(f"  [!] Connection failed — check internet connection")
        return []
    except requests.exceptions.Timeout:
        print(f"  [!] Request timed out — server may be slow")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"  [!] HTTP error: {e}")
        return []
    except Exception as e:
        print(f"  [!] Unexpected error: {e}")
        return []

# ─────────────────────────────────────────────
# SAFE STRING HELPER
# ─────────────────────────────────────────────

def safe_str(value, fallback="") -> str:
    """Safely convert any value to string — handles None, int, etc."""
    if value is None:
        return fallback
    return str(value).strip()

# ─────────────────────────────────────────────
# BUILD M3U
# ─────────────────────────────────────────────

def build_m3u(channels: dict, streams: list) -> tuple:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    count   = 0
    skipped = 0
    now     = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"# Generated: {now}\n")
        f.write(f"# Source: iptv-org API\n\n")

        for stream in streams:

            # Skip blocked channels
            # Note: status field was removed from iptv-org API — include all streams
            if stream.get("is_blocked") == True:
                skipped += 1
                continue

            # Safely extract — some fields can be null in API
            channel_id = safe_str(stream.get("channel"))
            url        = safe_str(stream.get("url"))

            # Skip if missing channel ID or URL
            if not channel_id or not url:
                skipped += 1
                continue

            # Get channel metadata
            ch       = channels.get(channel_id, {})
            name     = safe_str(ch.get("name"), channel_id)
            logo     = safe_str(ch.get("logo"))
            country  = safe_str(ch.get("country"))
            langs    = ch.get("languages") or []
            language = ",".join(langs) if langs else ""
            cats     = ch.get("categories") or []
            group    = cats[0] if cats else "Uncategorised"

            # Build EXTINF line
            extinf = (
                f'#EXTINF:-1 '
                f'tvg-id="{channel_id}" '
                f'tvg-name="{name}" '
                f'tvg-logo="{logo}" '
                f'tvg-language="{language}" '
                f'tvg-country="{country}" '
                f'group-title="{group}",'
                f'{name}\n'
            )

            f.write(extinf)

            # Write referrer/user-agent if required by stream
            http_referrer = safe_str(stream.get("http_referrer"))
            user_agent    = safe_str(stream.get("user_agent"))

            if http_referrer:
                f.write(f'#EXTVLCOPT:http-referrer={http_referrer}\n')
            if user_agent:
                f.write(f'#EXTVLCOPT:http-user-agent={user_agent}\n')

            f.write(url + "\n\n")
            count += 1

    return count, skipped

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("\n╔══════════════════════════════════╗")
    print("║      Playlist Builder v1.3       ║")
    print("╚══════════════════════════════════╝\n")

    # Step 1 — Fetch channels
    print("► Step 1: Fetching channels...")
    channels_list = fetch_json("channels.json")
    if not channels_list:
        print("  [!] No channels loaded — aborting.")
        sys.exit(1)
    channels = {ch["id"]: ch for ch in channels_list if "id" in ch}
    print(f"  [✓] Loaded {len(channels)} channels\n")

    # Step 2 — Fetch streams
    print("► Step 2: Fetching streams...")
    streams = fetch_json("streams.json")
    if not streams:
        print("  [!] No streams loaded — aborting.")
        sys.exit(1)
    total = len(streams)
    print(f"  [✓] Total streams: {total}\n")

    if total == 0:
        print("  [!] No streams found — aborting.")
        sys.exit(1)

    # Step 3 — Build M3U
    print("► Step 3: Building M3U playlist...")
    count, skipped = build_m3u(channels, streams)

    if count == 0:
        print("  [!] No channels written — something went wrong.")
        sys.exit(1)

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"  [✓] Channels written: {count}")
    print(f"  [✓] Streams skipped:  {skipped}")
    print(f"  [✓] File size:        {size_kb:.1f} KB")
    print(f"  [✓] Saved → {OUTPUT_FILE}\n")

    print("╔══════════════════════════════════╗")
    print("║           DONE ✓                 ║")
    print("╚══════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
