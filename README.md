# 📺 Personal IPTV — Auto-Updated Playlist & EPG

Private IPTV setup using iptv-org API with GitHub Actions for automatic updates.

---

## 📁 Repository Structure

```
├── scripts/
│   ├── playlist_builder.py   # Builds M3U playlist (runs weekly)
│   ├── epg_builder.py        # Builds EPG XML (runs daily)
│   └── mbc_fetcher.py        # Fetches MBC Group streams (run manually)
├── .github/
│   └── workflows/
│       ├── playlist.yml      # Weekly playlist cron
│       └── epg.yml           # Daily EPG cron
├── output/
│   ├── merged_channels.m3u   # Auto-generated playlist
│   └── merged_epg.xml        # Auto-generated EPG
└── README.md
```

---

## 📡 TiviMate Setup (One Time)

Add these two URLs to TiviMate — they never change:

**M3U Playlist:**
```
https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/output/merged_channels.m3u
```

**EPG Source:**
```
https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/output/merged_epg.xml
```

Replace `YOUR_USERNAME` and `YOUR_REPO` with your actual GitHub username and repo name.

---

## ⚙️ How It Works

| Script | Runs | Does |
|--------|------|------|
| `playlist_builder.py` | Every Sunday 2AM UTC | Fetches online streams from iptv-org API, builds M3U |
| `epg_builder.py` | Every day 3AM UTC | Fetches EPG guides from iptv-org API, builds XMLTV |
| `mbc_fetcher.py` | Manually when needed | Fetches MBC 2, Max, Action stream URLs |

---

## 🚀 Manual Trigger

To run any workflow manually:
1. Go to your GitHub repo
2. Click **Actions** tab
3. Select the workflow
4. Click **Run workflow**

---

## 🔧 Local Setup (VS Code)

Install dependencies:
```bash
pip install requests
```

Run scripts manually:
```bash
python scripts/playlist_builder.py
python scripts/epg_builder.py
python scripts/mbc_fetcher.py
```

---

## 📊 Update Schedule

| File | Updates | Via |
|------|---------|-----|
| `merged_channels.m3u` | Weekly (Sunday) | GitHub Actions |
| `merged_epg.xml` | Daily | GitHub Actions |
| MBC channels | When streams die | Manual run |

---

## ⚠️ Notes

- This repo should be **private** — keep it personal
- EPG and playlist use the same channel IDs from iptv-org — guaranteed matching
- GitHub Actions is completely free for private repos (2,000 minutes/month)
- EPG file can be large — GitHub handles up to 100MB per file
