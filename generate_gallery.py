#!/usr/bin/env python3
"""
Offline HTML Gallery Generator for Downloaded Instagram Media.
Creates a responsive, dark-mode, Instagram-style web gallery to browse downloaded media offline.
"""

import html
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any


def build_gallery(user_dir: Path) -> Path:
    """Scan downloaded media directory and create a self-contained gallery.html."""
    user_dir = user_dir.resolve()
    username = user_dir.name

    # 1. Look for profile picture
    avatar_url = ""
    avatar_dir = user_dir / "profile_pic"
    if avatar_dir.exists():
        avatars = [f for f in avatar_dir.glob("*.jpg")]
        if avatars:
            avatar_url = f"profile_pic/{avatars[0].name}"

    # 2. Gather posts
    posts_dir = user_dir / "posts"
    media_items: List[Dict[str, Any]] = []

    if posts_dir.exists():
        files = sorted(
            [f for f in posts_dir.iterdir() if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".mp4", ".webp")],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        # Group by post identifier (timestamp prefix before _1, _2 if carousel)
        grouped_posts: Dict[str, List[Path]] = {}
        for f in files:
            # Matches pattern like 2026-10-22_19-06-40_UTC(_1)?.(jpg|mp4)
            match = re.match(r"^(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_UTC)(?:_(\d+))?", f.name)
            base_key = match.group(1) if match else f.stem
            grouped_posts.setdefault(base_key, []).append(f)

        for key, group in grouped_posts.items():
            # Sort group so _1, _2 come in order
            group.sort(key=lambda p: p.name)
            first_file = group[0]
            is_carousel = len(group) > 1

            # Extract date for display
            date_match = re.match(r"^(\d{4}-\d{2}-\d{2})", key)
            date_str = date_match.group(1) if date_match else "Post"

            slides = []
            for item in group:
                is_vid = item.suffix.lower() == ".mp4"
                slides.append({
                    "src": f"posts/{item.name}",
                    "isVideo": is_vid,
                    "filename": item.name,
                })

            primary_is_video = first_file.suffix.lower() == ".mp4"

            media_items.append({
                "id": key,
                "date": date_str,
                "isCarousel": is_carousel,
                "slideCount": len(slides),
                "isVideo": primary_is_video,
                "thumbnail": f"posts/{first_file.name}",
                "slides": slides,
            })

    # Summary counts
    total_posts = len(media_items)
    total_files = sum(item["slideCount"] for item in media_items)
    total_videos = sum(1 for item in media_items for s in item["slides"] if s["isVideo"])
    total_photos = total_files - total_videos

    gallery_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@{html.escape(username)} — Instagram Media Gallery</title>
    <style>
        :root {{
            --bg-primary: #000000;
            --bg-secondary: #121212;
            --bg-card: #1c1c1c;
            --text-primary: #f5f5f5;
            --text-secondary: #a8a8a8;
            --accent: #0095f6;
            --border: #262626;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        body {{
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            padding-bottom: 50px;
        }}
        header {{
            max-width: 935px;
            margin: 0 auto;
            padding: 30px 20px 20px;
            display: flex;
            align-items: center;
            gap: 30px;
            border-bottom: 1px solid var(--border);
        }}
        .avatar {{
            width: 100px;
            height: 100px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid var(--border);
            background: var(--bg-card);
        }}
        .profile-info h1 {{
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            font-size: 14px;
            color: var(--text-secondary);
        }}
        .stats strong {{
            color: var(--text-primary);
        }}
        .filter-bar {{
            max-width: 935px;
            margin: 20px auto;
            padding: 0 20px;
            display: flex;
            gap: 10px;
        }}
        .filter-btn {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 8px 18px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s;
        }}
        .filter-btn.active, .filter-btn:hover {{
            background: var(--text-primary);
            color: var(--bg-primary);
            border-color: var(--text-primary);
        }}
        .gallery-grid {{
            max-width: 935px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            padding: 0 20px;
        }}
        @media (max-width: 768px) {{
            .gallery-grid {{
                grid-template-columns: repeat(2, 1fr);
                gap: 8px;
                padding: 0 10px;
            }}
            header {{
                gap: 20px;
                padding: 20px 10px;
            }}
            .avatar {{
                width: 75px;
                height: 75px;
            }}
        }}
        .media-card {{
            position: relative;
            aspect-ratio: 1 / 1;
            background: var(--bg-card);
            border-radius: 4px;
            overflow: hidden;
            cursor: pointer;
        }}
        .media-card img, .media-card video {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }}
        .badge {{
            position: absolute;
            top: 8px;
            right: 8px;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 12px;
            backdrop-filter: blur(4px);
        }}
        .badge-date {{
            position: absolute;
            bottom: 8px;
            left: 8px;
            background: rgba(0, 0, 0, 0.7);
            color: var(--text-secondary);
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
        }}
        /* Lightbox modal */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            inset: 0;
            background: rgba(0, 0, 0, 0.95);
            align-items: center;
            justify-content: center;
        }}
        .modal.open {{
            display: flex;
        }}
        .modal-content {{
            max-width: 90vw;
            max-height: 85vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
        }}
        .modal-media {{
            max-width: 85vw;
            max-height: 80vh;
            object-fit: contain;
            border-radius: 4px;
        }}
        .modal-close {{
            position: absolute;
            top: 20px;
            right: 25px;
            font-size: 32px;
            color: white;
            cursor: pointer;
            z-index: 1001;
        }}
        .modal-nav {{
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(255, 255, 255, 0.15);
            color: white;
            border: none;
            width: 44px;
            height: 44px;
            border-radius: 50%;
            font-size: 20px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
        }}
        .modal-nav:hover {{
            background: rgba(255, 255, 255, 0.35);
        }}
        .modal-prev {{ left: -60px; }}
        .modal-next {{ right: -60px; }}
        .modal-caption {{
            margin-top: 10px;
            font-size: 13px;
            color: var(--text-secondary);
            text-align: center;
        }}
        .empty-notice {{
            max-width: 935px;
            margin: 60px auto;
            text-align: center;
            color: var(--text-secondary);
        }}
    </style>
</head>
<body>
    <header>
        {"<img class='avatar' src='" + avatar_url + "' alt='Avatar'>" if avatar_url else "<div class='avatar'></div>"}
        <div class="profile-info">
            <h1>@{html.escape(username)}</h1>
            <div class="stats">
                <span><strong>{total_posts}</strong> posts</span>
                <span><strong>{total_photos}</strong> photos</span>
                <span><strong>{total_videos}</strong> videos</span>
            </div>
        </div>
    </header>

    <div class="filter-bar">
        <button class="filter-btn active" onclick="filterMedia('all', this)">All ({total_files})</button>
        <button class="filter-btn" onclick="filterMedia('photo', this)">Photos ({total_photos})</button>
        <button class="filter-btn" onclick="filterMedia('video', this)">Videos ({total_videos})</button>
    </div>

    <main class="gallery-grid" id="galleryGrid">
        {"".join(f'''
        <div class="media-card" data-type="{'video' if item['isVideo'] else 'photo'}" onclick="openModal({i})">
            {'<video src="' + item['thumbnail'] + '#t=0.5" preload="metadata"></video>' if item['isVideo'] else '<img src="' + item['thumbnail'] + '" loading="lazy" alt="Instagram Post">'}
            {'<span class="badge">Carousel (' + str(item['slideCount']) + ')</span>' if item['isCarousel'] else ('<span class="badge">▶ Reel</span>' if item['isVideo'] else '')}
            <span class="badge-date">{item['date']}</span>
        </div>
        ''' for i, item in enumerate(media_items))}
    </main>

    {"<div class='empty-notice'><h2>No media downloaded yet.</h2><p>Run <code>./download.sh " + html.escape(username) + "</code> to download posts.</p></div>" if not media_items else ""}

    <div class="modal" id="mediaModal" onclick="handleBackdropClick(event)">
        <span class="modal-close" onclick="closeModal()">&times;</span>
        <div class="modal-content">
            <button class="modal-nav modal-prev" onclick="prevSlide(event)">&#10094;</button>
            <div id="modalMediaContainer"></div>
            <button class="modal-nav modal-next" onclick="nextSlide(event)">&#10095;</button>
            <div class="modal-caption" id="modalCaption"></div>
        </div>
    </div>

    <script>
        const mediaData = {json.dumps(media_items)};
        let currentPostIdx = 0;
        let currentSlideIdx = 0;

        function openModal(idx) {{
            currentPostIdx = idx;
            currentSlideIdx = 0;
            renderModalSlide();
            document.getElementById('mediaModal').classList.add('open');
        }}

        function closeModal() {{
            document.getElementById('mediaModal').classList.remove('open');
            const container = document.getElementById('modalMediaContainer');
            container.innerHTML = '';
        }}

        function handleBackdropClick(e) {{
            if (e.target.id === 'mediaModal') {{
                closeModal();
            }}
        }}

        function renderModalSlide() {{
            const post = mediaData[currentPostIdx];
            if (!post) return;
            const slide = post.slides[currentSlideIdx];
            const container = document.getElementById('modalMediaContainer');
            container.innerHTML = '';

            if (slide.isVideo) {{
                const video = document.createElement('video');
                video.src = slide.src;
                video.className = 'modal-media';
                video.controls = true;
                video.autoplay = true;
                container.appendChild(video);
            }} else {{
                const img = document.createElement('img');
                img.src = slide.src;
                img.className = 'modal-media';
                container.appendChild(img);
            }}

            const caption = document.getElementById('modalCaption');
            const totalSlides = post.slides.length;
            const slideIndicator = totalSlides > 1 ? ` (Slide ${{currentSlideIdx + 1}} of ${{totalSlides}})` : '';
            caption.innerText = `${{post.date}}${{slideIndicator}} — ${{slide.filename}}`;
        }}

        function nextSlide(e) {{
            if (e) e.stopPropagation();
            const post = mediaData[currentPostIdx];
            if (currentSlideIdx < post.slides.length - 1) {{
                currentSlideIdx++;
            }} else if (currentPostIdx < mediaData.length - 1) {{
                currentPostIdx++;
                currentSlideIdx = 0;
            }} else {{
                currentPostIdx = 0;
                currentSlideIdx = 0;
            }}
            renderModalSlide();
        }}

        function prevSlide(e) {{
            if (e) e.stopPropagation();
            if (currentSlideIdx > 0) {{
                currentSlideIdx--;
            }} else if (currentPostIdx > 0) {{
                currentPostIdx--;
                currentSlideIdx = mediaData[currentPostIdx].slides.length - 1;
            }} else {{
                currentPostIdx = mediaData.length - 1;
                currentSlideIdx = mediaData[currentPostIdx].slides.length - 1;
            }}
            renderModalSlide();
        }}

        document.addEventListener('keydown', (e) => {{
            const modal = document.getElementById('mediaModal');
            if (!modal.classList.contains('open')) return;
            if (e.key === 'ArrowRight') nextSlide();
            if (e.key === 'ArrowLeft') prevSlide();
            if (e.key === 'Escape') closeModal();
        }});

        function filterMedia(type, btn) {{
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const cards = document.querySelectorAll('.media-card');
            cards.forEach(card => {{
                if (type === 'all' || card.getAttribute('data-type') === type) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}
    </script>
</body>
</html>
"""

    gallery_file = user_dir / "gallery.html"
    gallery_file.write_text(gallery_html, encoding="utf-8")
    return gallery_file


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python generate_gallery.py <path_to_user_downloads_dir>")
        sys.exit(1)
    target_path = Path(sys.argv[1])
    if not target_path.exists():
        print(f"Error: {target_path} does not exist.")
        sys.exit(1)
    out = build_gallery(target_path)
    print(f"Gallery generated: {out}")

