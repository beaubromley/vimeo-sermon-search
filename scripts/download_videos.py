import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.video_scraper import VimeoChannelScraper
from src.config import TRANSCRIPT_DIR
import json
from datetime import datetime

def filter_recent_videos(videos, start_year=2023):
    """Filter videos from 2023 onwards"""
    recent_videos = []
    for video in videos:
        try:
            # Parse the date string to datetime
            video_date = datetime.fromisoformat(video['date'].replace('Z', '+00:00'))
            if video_date.year >= start_year:
                recent_videos.append(video)
        except Exception as e:
            print(f"Error parsing date for video {video['title']}: {e}")
    
    return recent_videos

def main():
    print("Initializing Vimeo Channel Scraper...")
    scraper = VimeoChannelScraper()
    
    channel_name = "hendersonhills"
    print(f"\nFetching videos for channel: {channel_name}")
    
    # Load existing video data if it exists
    existing_videos = []
    video_data_path = TRANSCRIPT_DIR / 'video_data.json'
    if video_data_path.exists():
        try:
            with open(video_data_path, 'r', encoding='utf-8') as f:
                existing_videos = json.load(f)
            print(f"Loaded {len(existing_videos)} existing videos from database")
        except Exception as e:
            print(f"Error loading existing video data: {e}")
    
    # Get new videos
    new_videos = scraper.get_channel_videos(channel_name)
    
    if new_videos:
        # Filter for recent videos
        recent_videos = filter_recent_videos(new_videos)
        print(f"\nFound {len(recent_videos)} videos from 2023 onwards out of {len(new_videos)} total videos")
        
        # Combine with existing videos, avoiding duplicates
        existing_ids = {v['id'] for v in existing_videos}
        combined_videos = existing_videos + [v for v in recent_videos if v['id'] not in existing_ids]
        
        # Save combined video data
        try:
            with open(video_data_path, 'w', encoding='utf-8') as f:
                json.dump(combined_videos, f, indent=2, ensure_ascii=False)
            print(f"\nSaved video data to: {video_data_path}")
            print(f"Total videos in database: {len(combined_videos)}")
        except Exception as e:
            print(f"Error saving video data: {e}")
            return

        # Download transcripts only for recent videos
        new_transcripts = 0
        for video in recent_videos:
            # Check if transcript already exists
            transcript_file = TRANSCRIPT_DIR / f"{video['id']}_en-x-autogen.vtt"
            if not transcript_file.exists():
                print(f"\nDownloading transcript for: {video['title']} ({video['date'][:10]})")
                transcript_file = scraper.download_transcript(video['id'])
                if transcript_file:
                    new_transcripts += 1
                    print(f"Successfully downloaded transcript")
                else:
                    print(f"No transcript available or error downloading")

        print("\nProcess completed!")
        print(f"New transcripts downloaded: {new_transcripts}")
        print("You can now run update_database.py to process the new transcripts")

if __name__ == "__main__":
    main()
