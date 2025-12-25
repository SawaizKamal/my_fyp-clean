import yt_dlp
import os
from pathlib import Path


def download_youtube_video(url: str, output_path: str = "data/video.mp4") -> str:
    """
    Download a YouTube video using yt-dlp.
    
    Args:
        url: YouTube video URL
        output_path: Path where the video should be saved (default: "data/video.mp4")
    
    Returns:
        Path to the downloaded video file
    
    Raises:
        Exception: If download fails
    """
    print(f"📥 Downloading video from: {url}")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # yt-dlp options with anti-bot detection measures
    ydl_opts = {
        'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        'outtmpl': output_path,
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
        # Anti-bot detection measures
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],  # Try android client first (less bot detection)
                'player_skip': ['webpage', 'configs'],
            }
        },
        # Retry options
        'retries': 3,
        'fragment_retries': 3,
        'ignoreerrors': False,
        # Additional headers to appear more like a browser
        'http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
            'Keep-Alive': '300',
            'Connection': 'keep-alive',
        },
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Download the video
            ydl.download([url])
        
        # Find the actual downloaded file (yt-dlp might add extensions)
        base_path = os.path.splitext(output_path)[0]  # Remove .mp4 extension
        possible_extensions = ['.mp4', '.webm', '.mkv', '.avi']
        
        actual_file = None
        for ext in possible_extensions:
            test_path = base_path + ext
            if os.path.exists(test_path):
                actual_file = test_path
                break
            # Also check if yt-dlp added extension to the full path
            test_path = output_path + ext
            if os.path.exists(test_path):
                actual_file = test_path
                break
        
        if actual_file:
            print(f"✅ Video downloaded successfully to: {actual_file}")
            return actual_file
        else:
            print(f"❌ Could not find downloaded file. Expected: {output_path}")
            raise Exception(f"Downloaded file not found at expected location: {output_path}")
        
    except yt_dlp.DownloadError as e:
        print(f"❌ Download error: {str(e)}")
        raise Exception(f"Failed to download video: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error during download: {str(e)}")
        raise


def is_valid_youtube_url(url: str) -> bool:
    """
    Check if the provided URL is a valid YouTube URL.
    
    Args:
        url: URL string to validate
    
    Returns:
        True if URL is a valid YouTube URL, False otherwise
    """
    youtube_domains = ['youtube.com', 'youtu.be', 'www.youtube.com', 'm.youtube.com']
    url_lower = url.lower().strip()
    
    if not url_lower.startswith(('http://', 'https://')):
        return False
    
    for domain in youtube_domains:
        if domain in url_lower:
            return True
    
    return False

