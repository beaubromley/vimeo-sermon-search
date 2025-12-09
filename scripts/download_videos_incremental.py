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

def get_existing_video_ids():
    """Get set of existing video IDs from stored data"""
    video_data_path = TRANSCRIPT_DIR / 'video_data.json'
    if video_data_path.exists():
        try:
            with open(video_data_path, 'r', encoding='utf-8') as f:
                existing_videos = json.load(f)
            return {video['id'] for video in existing_videos}
        except Exception as e:
            print(f"Error loading existing video data: {e}")
            return set()
    return set()

def incremental_fetch(scraper, channel_name, existing_ids):
    """Fetch videos incrementally, stopping when we hit an existing video"""
    print(f"Starting incremental fetch for channel: {channel_name}")
    print(f"Will stop when we encounter a video we already have...")
    
    new_videos = []
    page = 1
    
    try:
        # Get first page
        print(f"Fetching page {page}...")
        response = scraper.make_request(f'/users/{channel_name}/videos')
        
        if not response:
            print("Failed to get initial response.")
            return []
        
        data = response.json()
        
        # Process videos from first page
        page_videos = scraper.process_video_data(data['data'])
        
        for video in page_videos:
            if video['id'] in existing_ids:
                print(f"\nFound existing video: '{video['title']}' (ID: {video['id']})")
                print(f"Stopping incremental fetch. Found {len(new_videos)} new videos.")
                return new_videos
            else:
                new_videos.append(video)
                print(f"New video found: {video['title']}")
        
        # Continue with additional pages if we haven't hit an existing video
        while 'next' in data['paging']:
            page += 1
            print(f"\nFetching page {page}... (Found {len(new_videos)} new videos so far)")
            
            response = scraper.make_request(data['paging']['next'])
            if not response:
                print(f"Failed to get page {page}")
                break
            
            data = response.json()
            page_videos = scraper.process_video_data(data['data'])
            
            # Check each video on this page
            for video in page_videos:
                if video['id'] in existing_ids:
                    print(f"\nFound existing video: '{video['title']}' (ID: {video['id']})")
                    print(f"Stopping incremental fetch. Found {len(new_videos)} new videos total.")
                    return new_videos
                else:
                    new_videos.append(video)
                    print(f"New video found: {video['title']}")
        
        print(f"\nReached end of channel. Found {len(new_videos)} new videos total.")
        return new_videos
        
    except Exception as e:
        print(f"Error during incremental fetch: {e}")
        return new_videos  # Return what we found so far

def main():
    print("Incremental Vimeo Video Download")
    print("=" * 40)
    print("This will fetch new videos until it encounters one we already have.")
    print("Use download_videos.py for a complete refresh.\n")
    
    scraper = VimeoChannelScraper()
    channel_name = "hendersonhills"
    
    # Load existing video IDs
    existing_ids = get_existing_video_ids()
    print(f"Found {len(existing_ids)} existing videos in database")
    
    if not existing_ids:
        print("No existing videos found. Running full download instead...")
        print("Consider running download_videos.py first.")
        return
    
    # Fetch new videos incrementally
    new_videos = incremental_fetch(scraper, channel_name, existing_ids)
    
    if not new_videos:
        print("\nNo new videos found.")
        return
    
    # Filter for recent videos (2023+)
    recent_new_videos = filter_recent_videos(new_videos)
    print(f"\nFound {len(recent_new_videos)} new videos from 2023 onwards out of {len(new_videos)} total new videos")
    
    if not recent_new_videos:
        print("No recent new videos to process.")
        return
    
    # Load existing video data and append new videos
    video_data_path = TRANSCRIPT_DIR / 'video_data.json'
    try:
        with open(video_data_path, 'r', encoding='utf-8') as f:
            existing_videos = json.load(f)
    except Exception as e:
        print(f"Error loading existing video data: {e}")
        existing_videos = []
    
    # Combine videos (new ones go at the beginning to maintain chronological order)
    combined_videos = recent_new_videos + existing_videos
    
    # Save updated video data
    try:
        with open(video_data_path, 'w', encoding='utf-8') as f:
            json.dump(combined_videos, f, indent=2, ensure_ascii=False)
        print(f"\nUpdated video data saved to: {video_data_path}")
        print(f"Total videos in database: {len(combined_videos)}")
    except Exception as e:
        print(f"Error saving video data: {e}")
        return
    
    # Download transcripts for new videos
    new_transcripts = 0
    for video in recent_new_videos:
        transcript_file = TRANSCRIPT_DIR / f"{video['id']}_en-x-autogen.vtt"
        if not transcript_file.exists():
            print(f"\nDownloading transcript for: {video['title']} ({video['date'][:10]})")
            downloaded_file = scraper.download_transcript(video['id'])
            if downloaded_file:
                new_transcripts += 1
                print(f"Successfully downloaded transcript")
            else:
                print(f"No transcript available or error downloading")
    
    print(f"\nIncremental update completed!")
    print(f"New videos added: {len(recent_new_videos)}")
    print(f"New transcripts downloaded: {new_transcripts}")
    print("\nNext steps:")
    print("1. Run update_database.py to process new transcripts")
    print("2. Run search_interface.py to search through all transcripts")

if __name__ == "__main__":
    main()
