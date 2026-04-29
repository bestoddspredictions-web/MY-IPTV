#!/usr/bin/env python3
"""
Script 1 — Playlist Builder v1.5
Fetches channels + streams from iptv-org API.
Removes duplicates by channel ID (keeps first).
Checks dead streams via HTTP HEAD requests (multi-threaded).
Outputs: output/merged_channels.m3u
Run: Weekly via GitHub Actions
"""

import requests
import os
import sys
import threading
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

WORKSPACE   = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
API_BASE    = "https://iptv-org.github.io/api"
OUTPUT_DIR  = os.path.join(WORKSPACE, "output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "merged_channels.m3u")
HEADERS     = {"User-Agent": "Mozilla/5.0"}

# Dead stream check settings
CHECK_DEAD_STREAMS = True
STREAM_TIMEOUT     = 10      # seconds per stream check
MAX_THREADS        = 50     # concurrent checks — safe for GitHub Actions

# ─────────────────────────────────────────────
# SAFE STRING HELPER
# ─────────────────────────────────────────────

def safe_str(value, fallback="") -> str:
    if value is None:
        return fallback
    return str(value).strip()

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
            print(f"  [!] Unexpected response format")
            return []
        return data
    except requests.exceptions.ConnectionError:
        print(f"  [!] Connection failed")
        return []
    except requests.exceptions.Timeout:
        print(f"  [!] Request timed out")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"  [!] HTTP error: {e}")
        return []
    except Exception as e:
        print(f"  [!] Unexpected error: {e}")
        return []

# ─────────────────────────────────────────────
# STEP 1 — DEDUPLICATE BY CHANNEL ID
# ─────────────────────────────────────────────

def deduplicate(streams: list) -> list:
    """
    Keep only one stream per channel ID.
    Priority: first stream found per channel.
    Also removes streams with missing channel ID or URL.
    """
    seen_channels = set()
    seen_urls     = set()
    unique        = []
    dupes         = 0

    for stream in streams:
        channel_id = safe_str(stream.get("channel"))
        url        = safe_str(stream.get("url"))

        if not channel_id or not url:
            dupes += 1
            continue

        # Skip duplicate channel IDs
        if channel_id in seen_channels:
            dupes += 1
            continue

        # Skip duplicate URLs
        if url in seen_urls:
            dupes += 1
            continue

        seen_channels.add(channel_id)
        seen_urls.add(url)
        unique.append(stream)

    print(f"  [✓] Removed {dupes} duplicates — {len(unique)} unique streams remain")
    return unique

# ─────────────────────────────────────────────
# STEP 2 — REMOVE DEAD STREAMS
# ─────────────────────────────────────────────

def check_stream(stream: dict, live: list, lock: threading.Lock):
    """Check a single stream URL — add to live list if reachable."""
    url = safe_str(stream.get("url"))
    if not url:
        return
    try:
        r = requests.head(
            url,
            timeout=STREAM_TIMEOUT,
            headers=HEADERS,
            allow_redirects=True
        )
        if r.status_code < 400:
            with lock:
                live.append(stream)
    except Exception:
        pass  # Dead stream — skip


def remove_dead_streams(streams: list) -> list:
    """Multi-threaded dead stream removal."""
    print(f"  [~] Checking {len(streams)} streams with {MAX_THREADS} threads...")
    print(f"  [~] Timeout per stream: {STREAM_TIMEOUT}s — please wait...\n")

    live   = []
    lock   = threading.Lock()
    total  = len(streams)
    done   = [0]

    def checked_check(stream):
        check_stream(stream, live, lock)
        with lock:
            done[0] += 1
            if done[0] % 500 == 0:
                print(f"  [~] Progress: {done[0]}/{total} checked — {len(live)} alive so far")

    # Process in batches to avoid overwhelming memory
    batch_size = MAX_THREADS
    for i in range(0, len(streams), batch_size):
        batch   = streams[i:i + batch_size]
        threads = [threading.Thread(target=checked_check, args=(s,)) for s in batch]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    dead = total - len(live)
    print(f"\n  [✓] Dead streams removed: {dead}")
    print(f"  [✓] Live streams:         {len(live)}")
    return live

# ─────────────────────────────────────────────
# STEP 3 — BUILD M3U
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
            channel_id = safe_str(stream.get("channel"))
            url        = safe_str(stream.get("url"))

            if not channel_id or not url:
                skipped += 1
                continue

            ch       = channels.get(channel_id, {})
            name     = safe_str(ch.get("name"), channel_id)
            logo     = safe_str(ch.get("logo"))
            country  = safe_str(ch.get("country"))
            langs    = ch.get("languages") or []
            language = ",".join(langs) if langs else ""
            cats     = ch.get("categories") or []
            group    = cats[0] if cats else "Uncategorised"

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

            referrer   = safe_str(stream.get("referrer") or stream.get("http_referrer"))
            user_agent = safe_str(stream.get("user_agent"))

            if referrer:
                f.write(f'#EXTVLCOPT:http-referrer={referrer}\n')
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
    print("║      Playlist Builder v1.5       ║")
    print("╚══════════════════════════════════╝\n")

    print(f"  Workspace:   {WORKSPACE}")
    print(f"  Output file: {OUTPUT_FILE}\n")

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
    print(f"  [✓] Total streams: {len(streams)}\n")

    # Step 3 — Deduplicate
    print("► Step 3: Removing duplicates...")
    streams = deduplicate(streams)
    print()

    # Step 4 — Remove dead streams
    if CHECK_DEAD_STREAMS:
        print("► Step 4: Checking dead streams...")
        streams = remove_dead_streams(streams)
    else:
        print("► Step 4: Dead stream check SKIPPED\n")

    if not streams:
        print("  [!] No streams remaining — aborting.")
        sys.exit(1)

    # Step 5 — Build M3U
    print("\n► Step 5: Building M3U playlist...")
    count, skipped = build_m3u(channels, streams)

    if count == 0:
        print("  [!] No channels written — aborting.")
        sys.exit(1)

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"  [✓] Channels written: {count}")
    print(f"  [✓] Skipped:          {skipped}")
    print(f"  [✓] File size:        {size_kb:.1f} KB")
    print(f"  [✓] Saved → {OUTPUT_FILE}\n")

    print("╔══════════════════════════════════╗")
    print("║           DONE ✓                 ║")
    print("╚══════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
