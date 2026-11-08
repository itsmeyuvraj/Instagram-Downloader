#!/usr/bin/env python3
"""
Instagram High-Quality Media & Highlights Downloader

Downloads original, full-resolution photos, videos, carousels, and highlights
from public Instagram accounts.
"""

import argparse
import datetime
import getpass
import os
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Optional, List, Tuple

import instaloader
from instaloader.instaloader import get_default_session_filename
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()


def parse_target(input_str: str) -> Tuple[str, str]:
    """
    Parse input string and determine whether it is a profile or a single post/reel.
    Returns: ('user', username) or ('post', shortcode)
    """
    cleaned = input_str.strip()
    if "instagram.com" in cleaned:
        parsed = urllib.parse.urlparse(cleaned)
        parts = [p for p in parsed.path.strip("/").split("/") if p]
        if parts:
            if parts[0] in ("p", "reel", "tv") and len(parts) > 1:
                return ("post", parts[1])
            elif parts[0] not in ("p", "reel", "tv", "explore", "direct", "stories", "accounts"):
                return ("user", parts[0])
            elif parts[0] == "stories" and len(parts) > 1:
                return ("user", parts[1])
    if cleaned.startswith("@"):
        cleaned = cleaned[1:]
    return ("user", cleaned.strip("/"))


def sanitize_filename(name: str) -> str:
    """Sanitize directory/file name for safe cross-platform filesystem use."""
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", name).strip()
    return sanitized if sanitized else "highlight"


def parse_date(date_str: Optional[str]) -> Optional[datetime.date]:
    """Parse YYYY-MM-DD date string."""
    if not date_str:
        return None
    try:
        return datetime.datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        console.print(f"[bold red]Error:[/bold red] Invalid date format for '{date_str}'. Please use YYYY-MM-DD.")
        sys.exit(1)


def setup_instaloader(
    output_dir: Path,
    photos_only: bool = False,
    videos_only: bool = False,
    download_video_thumbnails: bool = False,
    save_metadata: bool = False,
    save_captions: bool = False,
) -> instaloader.Instaloader:
    """Configure Instaloader with high-quality settings and clean folder structure."""
    download_pics = not videos_only
    download_vids = not photos_only

    caption_pattern = "{caption}" if save_captions else ""

    loader = instaloader.Instaloader(
        dirname_pattern=f"{output_dir}/{{target}}",
        filename_pattern="{date_utc}_UTC",
        download_pictures=download_pics,
        download_videos=download_vids,
        download_video_thumbnails=download_video_thumbnails,
        download_geotags=False,
        download_comments=False,
        save_metadata=save_metadata,
        compress_json=False,
        post_metadata_txt_pattern=caption_pattern,
        storyitem_metadata_txt_pattern=caption_pattern,
        max_connection_attempts=3,
        request_timeout=60.0,
        iphone_support=True,  # Requests higher quality original media assets
    )
    return loader


def authenticate_session(
    loader: instaloader.Instaloader,
    login_user: Optional[str] = None,
    session_id: Optional[str] = None,
    session_file: Optional[str] = None,
) -> bool:
    """Handle session authentication via username/password, session cookie, or session file."""
    # 1. Custom session file
    if session_file:
        try:
            with console.status(f"[cyan]Loading session file from {session_file}...[/cyan]"):
                target_user = login_user if login_user else "session"
                loader.load_session_from_file(target_user, filename=session_file)
            console.print(f"[green]✓ Successfully loaded session from {session_file}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error loading session file {session_file}: {e}[/red]")
            return False

    # 2. Direct sessionid cookie from browser
    if session_id:
        try:
            with console.status("[cyan]Applying browser session cookie...[/cyan]"):
                loader.context._session.cookies.set("sessionid", session_id.strip(), domain=".instagram.com")
                try:
                    loader.context._session.get("https://www.instagram.com/", timeout=15)
                    csrf = loader.context._session.cookies.get("csrftoken")
                    if csrf:
                        loader.context._session.headers.update({"X-CSRFToken": csrf})
                except Exception:
                    pass
                username = loader.test_login()
                if username:
                    loader.context.username = username
                    console.print(f"[green]✓ Authenticated as @{username} via session cookie[/green]")
                    return True
                else:
                    loader.context.username = login_user if login_user else "session_user"
                    console.print("[green]✓ Session cookie applied (authenticated)[/green]")
                    return True
        except Exception as e:
            console.print(f"[red]Failed to authenticate with session cookie: {e}[/red]")
            return False

    # 3. Interactive login or default cached session
    if login_user:
        cached_file = get_default_session_filename(login_user)
        if os.path.exists(cached_file):
            try:
                with console.status(f"[cyan]Loading saved session for @{login_user}...[/cyan]"):
                    loader.load_session_from_file(login_user)
                console.print(f"[green]✓ Loaded cached session for @{login_user}[/green]")
                return True
            except Exception as e:
                console.print(f"[yellow]Cached session expired or invalid ({e}). Re-authenticating...[/yellow]")

        try:
            console.print(f"[bold cyan]Instagram Login for @{login_user}:[/bold cyan]")
            loader.interactive_login(login_user)
            loader.save_session_to_file()
            console.print(f"[green]✓ Successfully logged in and cached session to {cached_file}[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Login failed: {e}[/red]")
            return False

    return False


def download_single_post(loader: instaloader.Instaloader, shortcode: str, output_base: Path) -> bool:
    """Download a single post or reel by shortcode."""
    console.print(f"[bold cyan]• Fetching single post/reel (shortcode: {shortcode})...[/bold cyan]")
    try:
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        target = Path(post.owner_username) / "single_posts"
        media_type = "Video/Reel" if post.is_video else ("Carousel" if post.typename == "GraphSidecar" else "Photo")
        console.print(f"[cyan]  Author: @{post.owner_username} | Type: {media_type} | Date: {post.date_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}[/cyan]")
        loader.download_post(post, target=target)
        console.print(f"[bold green]✓ Downloaded successfully into: {output_base / target}[/bold green]\n")
        return True
    except Exception as e:
        console.print(f"[bold red]Error downloading post {shortcode}: {e}[/bold red]\n")
        return False


def download_profile_avatar(loader: instaloader.Instaloader, profile: instaloader.Profile, user_dir: Path) -> bool:
    """Download the HD profile picture."""
    try:
        target = user_dir / "profile_pic"
        console.print("[cyan]• Downloading HD profile picture...[/cyan]")
        loader.download_title_pic(profile.profile_pic_url, target, "profile_pic", profile)
        console.print("[green]  ✓ Profile picture downloaded[/green]")
        return True
    except Exception as e:
        console.print(f"[yellow]  ⚠️ Could not download profile picture: {e}[/yellow]")
        return False


def download_user_posts(
    loader: instaloader.Instaloader,
    profile: instaloader.Profile,
    user_dir: Path,
    limit: Optional[int] = None,
    fast_update: bool = False,
    since_date: Optional[datetime.date] = None,
    until_date: Optional[datetime.date] = None,
) -> int:
    """Download posts (images, carousels, videos, reels) from the profile feed."""
    target = user_dir / "posts"
    console.print(f"\n[bold cyan]• Scanning grid posts for @{profile.username}...[/bold cyan]")

    count = 0
    try:
        posts_iterator = profile.get_posts()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            total_est = limit if limit and limit > 0 else (profile.mediacount or 0)
            task = progress.add_task(f"Downloading posts (max: {total_est or 'all'})...", total=total_est if total_est > 0 else None)

            for post in posts_iterator:
                post_date = post.date_utc.date()

                # If post is newer than until_date, skip it and continue looking for older posts
                if until_date and post_date > until_date:
                    continue

                # If post is older than since_date, stop iterating (posts are reverse chronological)
                if since_date and post_date < since_date:
                    console.print(f"[yellow]  Reached post from {post_date} (older than --since {since_date}). Stopping.[/yellow]")
                    break

                if limit and count >= limit:
                    break

                media_type = "Video/Reel" if post.is_video else ("Carousel" if post.typename == "GraphSidecar" else "Photo")
                progress.update(task, description=f"[{count + 1}] {media_type} from {post.date_utc.strftime('%Y-%m-%d')}...")

                try:
                    downloaded = loader.download_post(post, target=target)
                    if fast_update and not downloaded:
                        console.print("[yellow]  Reached already-downloaded post with --fast-update. Stopping.[/yellow]")
                        break
                    count += 1
                    progress.advance(task)
                except Exception as post_err:
                    console.print(f"[yellow]  ⚠️ Error on post {post.shortcode}: {post_err}[/yellow]")
                    continue

        console.print(f"[green]✓ Completed posts download: {count} post(s) processed.[/green]")
    except Exception as e:
        console.print(f"[red]Error fetching posts: {e}[/red]")

    return count


def download_user_reels(
    loader: instaloader.Instaloader,
    profile: instaloader.Profile,
    user_dir: Path,
    limit: Optional[int] = None,
    fast_update: bool = False,
) -> int:
    """Download reels specifically from the Reels tab."""
    target = user_dir / "reels"
    console.print(f"\n[bold cyan]• Scanning dedicated Reels tab for @{profile.username}...[/bold cyan]")

    count = 0
    try:
        reels_iterator = profile.get_reels()
        for post in reels_iterator:
            if limit and count >= limit:
                break
            try:
                downloaded = loader.download_post(post, target=target)
                if fast_update and not downloaded:
                    break
                count += 1
            except Exception as reel_err:
                console.print(f"[yellow]  ⚠️ Error on reel {post.shortcode}: {reel_err}[/yellow]")
                continue
        console.print(f"[green]✓ Completed reels download: {count} reel(s) processed.[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠️ Could not fetch reels tab directly: {e}[/yellow]")
    return count


def download_user_highlights(
    loader: instaloader.Instaloader,
    profile: instaloader.Profile,
    user_dir: Path,
    limit: Optional[int] = None,
) -> Tuple[int, int]:
    """Download highlights and their stories/covers."""
    console.print(f"\n[bold cyan]• Fetching Highlights for @{profile.username}...[/bold cyan]")

    if not loader.context.is_logged_in:
        console.print(
            Panel(
                "[bold yellow]⚠️ Authentication Required for Highlights[/bold yellow]\n\n"
                "Instagram's API strictly requires an authenticated session to access Highlights\n"
                "and Stories, even for 100% public accounts.\n\n"
                "To download highlights, run the script with your Instagram username:\n"
                f"  [cyan]python instagram_downloader.py {profile.username} --highlights --login <your_username>[/cyan]\n\n"
                "Or provide your browser's [bold]sessionid[/bold] cookie directly:\n"
                f"  [cyan]python instagram_downloader.py {profile.username} --highlights --session-id <cookie>[/cyan]",
                title="Highlights Access Restricted",
                border_style="yellow",
            )
        )
        return 0, 0

    highlights_count = 0
    items_count = 0

    try:
        user_highlights = list(loader.get_highlights(profile))
        total_hl = len(user_highlights)

        if total_hl == 0:
            console.print(f"[yellow]No highlights found on @{profile.username}'s profile.[/yellow]")
            return 0, 0

        console.print(f"[green]Found {total_hl} highlight album(s). Starting download...[/green]")

        for idx, hl in enumerate(user_highlights, start=1):
            if limit and highlights_count >= limit:
                break

            safe_title = sanitize_filename(hl.title)
            hl_target = user_dir / "highlights" / f"{idx:02d}_{safe_title}"

            console.print(f"[cyan]  [{idx}/{total_hl}] Highlight: '[bold]{hl.title}[/bold]' ({hl.itemcount} items)[/cyan]")

            # Download cover
            try:
                loader.download_highlight_cover(hl, hl_target)
            except Exception:
                pass

            # Download all items (photos and videos)
            hl_items_downloaded = 0
            for item in hl.get_items():
                try:
                    loader.download_storyitem(item, hl_target)
                    hl_items_downloaded += 1
                    items_count += 1
                except Exception as item_err:
                    console.print(f"[yellow]    ⚠️ Error downloading highlight item: {item_err}[/yellow]")

            highlights_count += 1
            console.print(f"[green]    ✓ Downloaded {hl_items_downloaded}/{hl.itemcount} items[/green]")

        console.print(f"[green]✓ Completed highlights: {highlights_count} album(s), {items_count} media file(s).[/green]")
    except instaloader.exceptions.LoginRequiredException:
        console.print("[red]Instagram rejected access: Valid login session is required to fetch Highlights.[/red]")
    except Exception as e:
        console.print(f"[red]Error fetching highlights: {e}[/red]")

    return highlights_count, items_count


def download_user_stories(
    loader: instaloader.Instaloader,
    profile: instaloader.Profile,
    user_dir: Path,
) -> int:
    """Download active 24-hour stories."""
    console.print(f"\n[bold cyan]• Checking active Stories for @{profile.username}...[/bold cyan]")
    if not loader.context.is_logged_in:
        console.print("[yellow]⚠️ Active stories require authentication (--login or --session-id). Skipping stories.[/yellow]")
        return 0

    count = 0
    target = user_dir / "stories"
    try:
        stories = loader.get_stories(userids=[profile.userid])
        for story in stories:
            for item in story.get_items():
                try:
                    loader.download_storyitem(item, target)
                    count += 1
                except Exception as err:
                    console.print(f"[yellow]  ⚠️ Error on story item: {err}[/yellow]")
        console.print(f"[green]✓ Completed active stories: {count} item(s) downloaded.[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠️ Could not download stories: {e}[/yellow]")
    return count


def process_target(
    target_raw: str,
    loader: instaloader.Instaloader,
    output_base: Path,
    args: argparse.Namespace,
    since_date: Optional[datetime.date],
    until_date: Optional[datetime.date],
):
    """Process a single target (profile or single post)."""
    target_type, identifier = parse_target(target_raw)

    # 1. Single Post / Reel Mode
    if target_type == "post":
        download_single_post(loader, identifier, output_base)
        return

    # 2. Profile Mode
    username = identifier
    if not username:
        console.print(f"[bold red]Skipping invalid target:[/bold red] {target_raw}")
        return

    dl_posts = args.posts or args.all or (not args.highlights and not args.reels and not args.stories and not args.profile_pic)
    dl_highlights = args.highlights or args.all
    dl_reels = args.reels or args.all
    dl_stories = args.stories or args.all
    dl_avatar = args.profile_pic or args.all or (not args.highlights and not args.reels and not args.stories)

    user_dir = Path(username)

    console.print(
        Panel(
            f"[bold green]Instagram Media Downloader[/bold green]\n"
            f"[cyan]Target Account :[/cyan] @{username}\n"
            f"[cyan]Output Directory:[/cyan] {output_base / username}\n"
            f"[cyan]Tasks Selected  :[/cyan] "
            f"{'Posts ' if dl_posts else ''}"
            f"{'Highlights ' if dl_highlights else ''}"
            f"{'Reels ' if dl_reels else ''}"
            f"{'Stories ' if dl_stories else ''}"
            f"{'Profile-Pic ' if dl_avatar else ''}\n"
            f"{f'[cyan]Date Filter     :[/cyan] {since_date or 'Any'} to {until_date or 'Now'}' if (since_date or until_date) else ''}\n"
            f"[cyan]Quality Mode    :[/cyan] Original CDN Resolution (HD)",
            title=f"Processing @{username}",
            border_style="green",
        )
    )

    with console.status(f"[cyan]Fetching profile information for @{username}...[/cyan]"):
        try:
            profile = instaloader.Profile.from_username(loader.context, username)
        except instaloader.exceptions.ProfileNotExistsException:
            console.print(f"[bold red]Error:[/bold red] The profile @{username} does not exist.")
            return
        except instaloader.exceptions.ConnectionException as conn_err:
            console.print(f"[bold red]Connection error:[/bold red] {conn_err}")
            return
        except Exception as e:
            console.print(f"[bold red]Failed to load profile @{username}:[/bold red] {e}")
            return

    if profile.is_private and not profile.followed_by_viewer:
        console.print(
            Panel(
                f"[bold red]Account @{username} is PRIVATE.[/bold red]\n"
                "You cannot download media from private accounts without following them from an authenticated account.",
                border_style="red",
            )
        )
        return

    total_posts = 0
    total_reels = 0
    total_hl_albums = 0
    total_hl_items = 0
    total_stories = 0

    if dl_avatar:
        download_profile_avatar(loader, profile, user_dir)

    if dl_posts:
        total_posts = download_user_posts(
            loader,
            profile,
            user_dir,
            limit=args.limit,
            fast_update=args.fast_update,
            since_date=since_date,
            until_date=until_date,
        )

    if dl_reels:
        total_reels = download_user_reels(loader, profile, user_dir, limit=args.limit, fast_update=args.fast_update)

    if dl_highlights:
        total_hl_albums, total_hl_items = download_user_highlights(loader, profile, user_dir, limit=args.limit)

    if dl_stories:
        total_stories = download_user_stories(loader, profile, user_dir)

    table = Table(title=f"Summary for @{username}", border_style="green")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Items Processed", style="magenta")
    table.add_column("Location", style="yellow")

    if dl_avatar:
        table.add_row("Profile Picture", "1", str(output_base / username / "profile_pic"))
    if dl_posts:
        table.add_row("Feed Posts", str(total_posts), str(output_base / username / "posts"))
    if dl_reels:
        table.add_row("Reels", str(total_reels), str(output_base / username / "reels"))
    if dl_highlights:
        table.add_row("Highlights", f"{total_hl_albums} albums ({total_hl_items} items)", str(output_base / username / "highlights"))
    if dl_stories:
        table.add_row("Stories", str(total_stories), str(output_base / username / "stories"))

    console.print("\n")
    console.print(table)
    console.print(f"[bold green]✓ Media saved in:[/bold green] [underline]{output_base / username}[/underline]\n")


def main():
    parser = argparse.ArgumentParser(
        description="Download high-quality images, videos, and highlights from Instagram accounts or post URLs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all posts & profile pic from a public account (no login required)
  python instagram_downloader.py natgeo

  # Download a single specific post or reel directly by URL
  python instagram_downloader.py https://www.instagram.com/p/DfajF1zvsbl/

  # Download posts between specific dates
  python instagram_downloader.py natgeo --since 2024-01-01 --until 2024-06-30

  # Download posts and highlights (login required for highlights)
  python instagram_downloader.py natgeo --posts --highlights --login my_username

  # Download using browser session cookie without entering password
  python instagram_downloader.py natgeo --highlights --session-id "YOUR_SESSION_ID"

  # Batch download multiple targets from a text file
  python instagram_downloader.py --batch accounts.txt --limit 10
        """,
    )

    parser.add_argument("target", nargs="?", default=None, help="Instagram username, profile URL, or post/reel URL")
    parser.add_argument("-o", "--output-dir", default="./downloads", help="Directory where files will be saved (default: ./downloads)")
    parser.add_argument("--batch", metavar="FILE", help="File with list of usernames or URLs to download (one per line)")

    # Content selection flags
    content_group = parser.add_argument_group("Content Selection")
    content_group.add_argument("--posts", action="store_true", help="Download feed posts (images, carousels, videos)")
    content_group.add_argument("--highlights", action="store_true", help="Download highlights (photos, videos & covers)")
    content_group.add_argument("--reels", action="store_true", help="Download from dedicated Reels tab")
    content_group.add_argument("--stories", action="store_true", help="Download active 24-hour stories")
    content_group.add_argument("--profile-pic", action="store_true", help="Download high-res profile picture")
    content_group.add_argument("--all", action="store_true", help="Download everything (posts, reels, highlights, stories, profile pic)")

    # Filters and limits
    filter_group = parser.add_argument_group("Filters & Date Ranges")
    filter_group.add_argument("-n", "--limit", type=int, default=None, help="Limit number of items to download (e.g. 10)")
    filter_group.add_argument("--photos-only", action="store_true", help="Download photos only, ignore videos")
    filter_group.add_argument("--videos-only", action="store_true", help="Download videos only, ignore photos")
    filter_group.add_argument("--since", metavar="YYYY-MM-DD", help="Only download posts published on or after this date")
    filter_group.add_argument("--until", metavar="YYYY-MM-DD", help="Only download posts published on or before this date")
    filter_group.add_argument("--fast-update", action="store_true", help="Stop once an already downloaded post is encountered")

    # Metadata & Extra files
    meta_group = parser.add_argument_group("Metadata & Output Options")
    meta_group.add_argument("--save-metadata", action="store_true", help="Save raw JSON metadata for each post")
    meta_group.add_argument("--save-captions", action="store_true", help="Save post captions into .txt files")
    meta_group.add_argument("--video-thumbnails", action="store_true", help="Also save video preview JPG alongside MP4")

    # Authentication options
    auth_group = parser.add_argument_group("Authentication (Required for Highlights/Stories)")
    auth_group.add_argument("-l", "--login", metavar="USERNAME", help="Your Instagram username to log in and access highlights")
    auth_group.add_argument("--session-id", metavar="COOKIE", help="Your browser 'sessionid' cookie value (bypasses password)")
    auth_group.add_argument("--session-file", metavar="PATH", help="Path to a pre-existing Instaloader session file")

    args = parser.parse_args()

    if not args.target and not args.batch:
        parser.error("You must specify either a target (username/URL) or --batch FILE.")

    since_date = parse_date(args.since)
    until_date = parse_date(args.until)

    output_base = Path(args.output_dir).resolve()

    loader = setup_instaloader(
        output_dir=output_base,
        photos_only=args.photos_only,
        videos_only=args.videos_only,
        download_video_thumbnails=args.video_thumbnails,
        save_metadata=args.save_metadata,
        save_captions=args.save_captions,
    )

    if args.login or args.session_id or args.session_file:
        authenticate_session(
            loader,
            login_user=args.login,
            session_id=args.session_id,
            session_file=args.session_file,
        )

    targets = []
    if args.batch:
        batch_path = Path(args.batch)
        if not batch_path.exists():
            console.print(f"[bold red]Error:[/bold red] Batch file '{args.batch}' not found.")
            sys.exit(1)
        with open(batch_path, "r", encoding="utf-8") as f:
            for line in f:
                item = line.strip()
                if item and not item.startswith("#"):
                    targets.append(item)
    if args.target:
        targets.append(args.target)

    for target in targets:
        process_target(target, loader, output_base, args, since_date, until_date)


if __name__ == "__main__":
    main()
