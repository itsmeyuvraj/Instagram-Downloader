# Instagram High-Quality Media & Highlights Downloader

A command-line script to download original, full-resolution photos, carousels, videos, reels, and highlights from public Instagram accounts.

---

## Features

- **Highest Available Quality**: Downloads original full-resolution media straight from Instagram's CDN (`.jpg` and `.mp4`).
- **Complete Media Support**:
  - **Photos & Single Images**
  - **Multi-slide Carousels** (every slide saved with `_1.jpg`, `_2.mp4`, etc.)
  - **Videos & Reels** (full 1080p MP4)
  - **Highlights** (all story albums, videos, photos, and highlight cover pictures)
  - **Active 24-Hour Stories**
  - **HD Profile Picture**
- **Clean File Organization**: Organizes media into structured folders without cluttering your system with `.json.xz` metadata unless explicitly requested.
- **Preserves Original Dates**: Sets downloaded files' modification timestamps (`mtime`) to when the media was originally published on Instagram.
- **Incremental Sync**: Resume and fast-update options (`--fast-update`) to skip already downloaded media.
- **Anonymous or Authenticated**:
  - Public posts, videos, reels, and profile pictures can be downloaded **without any login** (anonymous).
  - Highlights and stories can be unlocked using your account session or browser cookie.

---

## Directory Structure

Downloaded files are organized neatly under your chosen output directory (default: `./downloads`):

```
downloads/
└── <username>/
    ├── profile_pic/
    │   └── 2025-09-20_00-00-36_UTC_profile_pic.jpg
    ├── posts/
    │   ├── 2026-10-25_14-30-00_UTC.jpg
    │   ├── 2026-10-26_18-20-00_UTC_1.jpg
    │   ├── 2026-10-26_18-20-00_UTC_2.mp4
    │   └── 2026-11-06_21-16-10_UTC.mp4
    ├── reels/
    │   └── ...
    ├── highlights/
    │   ├── 01_Travel_Tokyo/
    │   │   ├── cover.jpg
    │   │   ├── 2026-04-12_08-11-22_UTC.mp4
    │   │   └── 2026-04-12_09-15-44_UTC.jpg
    │   └── 02_Food/
    │       └── ...
    └── stories/
        └── ...
```

---

## Installation & Setup

1. The script requires Python 3.8+ and comes with a prepared virtual environment.
2. If setting up on a new machine, install dependencies with:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Usage Guide

You can run the script via `./download.sh` or directly using the virtual environment python:

```bash
./download.sh <username_or_url> [options]
```

### 1. Download Public Posts & Videos (No Login Required)

To download posts and HD profile picture from a public account:

```bash
# By username
./download.sh natgeo

# Or by pasting full Instagram URL
./download.sh https://www.instagram.com/natgeo/

# Download only the 10 most recent posts
./download.sh natgeo --limit 10
```

### 2. Download Highlights & Stories (Login Required)

> [!IMPORTANT]
> **Why is login required for highlights?**
> Instagram's GraphQL servers enforce an authenticated session to query `edge_highlight_reels` and stories, even on 100% public accounts. Anonymous viewers are blocked by Instagram's API.

You have two convenient ways to authenticate:

#### Method A: Using your Instagram username (interactive login)
The script asks for your password once securely (supports 2FA) and caches the session locally in `~/.config/instaloader/` so you won't need to re-enter credentials:

```bash
./download.sh natgeo --highlights --login your_ig_username
```

#### Method B: Using your browser's session cookie (Fast & No Password Needed)
If you do not want to enter your password in the terminal:
1. Open [instagram.com](https://www.instagram.com) in Chrome, Safari, or Firefox and ensure you are logged in.
2. Open Developer Tools (`F12` or `Cmd + Option + I`).
3. Navigate to **Application** (Chrome) or **Storage** (Firefox) -> **Cookies** -> `https://www.instagram.com`.
4. Copy the value of the `sessionid` cookie.
5. Run:
```bash
./download.sh natgeo --highlights --session-id "YOUR_COPIED_SESSIONID_COOKIE"
```

---

## Common Use Cases & Examples

| Goal | Command |
| :--- | :--- |
| **Download last 20 posts from public account** | `./download.sh natgeo --limit 20` |
| **Download all Highlights only** | `./download.sh natgeo --highlights --login myuser` |
| **Download both Posts & Highlights** | `./download.sh natgeo --posts --highlights --login myuser` |
| **Download ONLY Videos & Reels** | `./download.sh natgeo --videos-only` |
| **Download ONLY Photos** | `./download.sh natgeo --photos-only` |
| **Download Everything (Posts, Reels, Highlights, Stories, Avatar)** | `./download.sh natgeo --all --login myuser` |
| **Custom output directory** | `./download.sh natgeo -o ~/Pictures/Instagram` |
| **Save captions alongside media (`.txt`)** | `./download.sh natgeo --save-captions` |
| **Incremental update (stop on already downloaded items)** | `./download.sh natgeo --fast-update` |

---

## Command Line Options Reference

```text
positional arguments:
  target                Instagram username or profile URL (e.g. 'natgeo' or 'https://instagram.com/natgeo')

options:
  -h, --help            Show this help message and exit
  -o, --output-dir DIR  Directory where files will be saved (default: ./downloads)

Content Selection:
  --posts               Download feed posts (images, carousels, videos)
  --highlights          Download highlights (photos, videos & covers)
  --reels               Download from dedicated Reels tab
  --stories             Download active 24-hour stories
  --profile-pic         Download high-res profile picture
  --all                 Download everything (posts, reels, highlights, stories, profile pic)

Filters & Limits:
  -n, --limit LIMIT     Limit number of items to download (e.g. 10)
  --photos-only         Download photos only, ignore videos
  --videos-only         Download videos only, ignore photos
  --fast-update         Stop once an already downloaded post is encountered

Metadata & Output:
  --save-metadata       Save raw JSON metadata for each post (.json)
  --save-captions       Save post captions into text files (.txt)
  --video-thumbnails    Save video preview JPG alongside MP4

Authentication:
  -l, --login USERNAME  Your Instagram username to log in and access highlights
  --session-id COOKIE   Your browser 'sessionid' cookie value (bypasses password)
  --session-file PATH   Path to a pre-existing Instaloader session file
```

---

## Best Practices & Rate Limit Tips

1. **Use `--limit` for Large Accounts**: Accounts with thousands of posts should be downloaded with `--limit` (e.g. `--limit 50`) to avoid Instagram rate-limiting your IP address.
2. **Periodic Backups**: When running periodically, use `--fast-update`. The script checks existing files and stops as soon as it reaches previously downloaded media, saving bandwidth and avoiding rate limits.
3. **Session Caching**: When using `--login`, the session is cached securely on your machine so subsequent runs do not trigger security verification alerts from Instagram.

