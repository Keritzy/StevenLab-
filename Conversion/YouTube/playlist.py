import yt_dlp
import sys
import os

def get_playlist_info(playlist_url, limit=10):
    """Fetch videos from playlist or channel"""
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'ignoreerrors': True,
        'playlistend': limit,
        'extractor_args': {'youtube': {'player_client': ['web', 'ios', 'android', 'web_safari']}},
    }
   
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(playlist_url, download=False)
            return info
        except Exception as e:
            print(f"Error fetching info: {e}")
            return None

def print_video_details(video):
    print("\n" + "═" * 90)
    print(f"Title : {video.get('title', 'N/A')}")
    print(f"URL   : https://www.youtube.com/watch?v={video.get('id')}")
    print(f"Duration : {video.get('duration_string', 'N/A')}")
    print(f"Views    : {video.get('view_count', 'N/A')}")
    print(f"Upload   : {video.get('upload_date', 'N/A')}")
    desc = video.get('description') or ''
    print(f"Desc  : {desc[:150]}{'...' if len(desc) > 150 else ''}")
    print("═" * 90)

def download_as_mp3(urls, output_dir='youtube_mp3'):
    os.makedirs(output_dir, exist_ok=True)
   
    ydl_opts = {
        'outtmpl': f'{output_dir}/%(upload_date)s_%(title)s.%(ext)s',
        'format': 'bestaudio/best',           # Best audio quality
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',        # 192 kbps (good quality/size balance)
        }],
        'quiet': False,
        'ignoreerrors': True,
        'retries': 5,
        'sleep_interval': 5,
        'extractor_args': {'youtube': {'player_client': ['web', 'ios', 'android', 'web_safari']}},
    }
   
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print(f"\nDownloading {len(urls)} videos as MP3...")
        ydl.download(urls)

def main():
    if len(sys.argv) < 2:
        print("Usage: python video_mp3.py <playlist_or_channel_url> [limit]")
        print("Example: python video_mp3.py https://www.youtube.com/playlist?list=PL... 20")
        print("         python video_mp3.py https://www.youtube.com/@hjeilchurch/videos 15")
        sys.exit(1)

    url = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    print(f"Fetching from: {url}")
    info = get_playlist_info(url, limit)

    if not info or not info.get('entries'):
        print("Failed to fetch data. Try again later.")
        return

    print(f"\nTitle: {info.get('title', 'N/A')}\n")

    video_urls = []
    for i, entry in enumerate(info.get('entries', [])[:limit], 1):
        if entry and entry.get('id'):
            print(f"{i}. {entry.get('title', 'N/A')}")
            print_video_details(entry)
            video_urls.append(f"https://www.youtube.com/watch?v={entry['id']}")

    if video_urls:
        choice = input(f"\nDownload all {len(video_urls)} videos as MP3? (y/n): ").strip().lower()
        if choice == 'y':
            download_as_mp3(video_urls)
        else:
            print("Download cancelled.")

if __name__ == "__main__":
    main()