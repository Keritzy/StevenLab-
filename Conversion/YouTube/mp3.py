#!/usr/bin/env python3
"""
YouTube to MP3 Batch Converter - 2026 Fixed
"""

import argparse
import sys
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    print("❌ Please install: pip install yt-dlp --upgrade")
    sys.exit(1)


def download_audio(url: str, output_dir: str, quality: str = "320"):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(output_path / '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': quality,
        }],
        # Anti-blocking options
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'web', 'web_safari', 'web_embedded'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        },
        'retries': 10,
        'fragment_retries': 10,
        'ignoreerrors': True,        # Continue even if one fails
        'quiet': False,
    }
    
    try:
        print(f"🔗 Processing: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"✅ Finished: {url}\n")
    except Exception as e:
        print(f"❌ Failed {url}: {e}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube to MP3 Batch Downloader")
    parser.add_argument("urls", nargs="*", help="YouTube URLs (space separated)")
    parser.add_argument("-o", "--output", default="YouTube_MP3s", help="Output folder")
    parser.add_argument("-q", "--quality", default="320", choices=["128", "192", "256", "320"], 
                       help="Audio quality in kbps")
    
    args = parser.parse_args()
    
    if not args.urls:
        print("No URLs provided. Enter them separated by space or comma:")
        input_urls = input().replace(",", " ")
        args.urls = input_urls.split()
    
    print(f"📥 Starting batch download to: {args.output}")
    print(f"🎵 Quality: {args.quality}kbps | Total videos: {len(args.urls)}\n")
    
    for url in args.urls:
        if url.strip():
            download_audio(url.strip(), args.output, args.quality)
    
    print("🎉 All downloads completed!")