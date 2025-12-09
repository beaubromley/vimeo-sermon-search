import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import TRANSCRIPT_DIR
import json
from datetime import datetime

def check_recent_additions():
    video_data_path = TRANSCRIPT_DIR / 'video_data.json'
    
    if not video_data_path.exists():
        print("No video data found.")
        return
    
    with open(video_data_path, 'r', encoding='utf-8') as f:
        videos = json.load(f)
    
    print(f"Total videos in database: {len(videos)}")
    
    # Show most recent videos
    sorted_videos = sorted(videos, key=lambda x: x['date'], reverse=True)
    
    print(f"\n🕒 MOST RECENT 10 VIDEOS:")
    print("-" * 80)
    
    for i, video in enumerate(sorted_videos[:10], 1):
        date_str = video['date'][:10]
        transcript_file = TRANSCRIPT_DIR / f"{video['id']}_en-x-autogen.vtt"
        has_transcript = "✅" if transcript_file.exists() else "❌"
        
        print(f"{i:2d}. {date_str} | {has_transcript} | {video['title'][:60]}")
    
    # Check for videos newer than your VTT files
    print(f"\n🆕 VIDEOS NEWER THAN 6/28/2025:")
    print("-" * 80)
    
    cutoff_date = datetime(2025, 6, 28)
    newer_videos = []
    
    for video in videos:
        try:
            video_date = datetime.fromisoformat(video['date'].replace('Z', '+00:00'))
            if video_date > cutoff_date:
                newer_videos.append(video)
        except:
            continue
    
    if newer_videos:
        newer_videos.sort(key=lambda x: x['date'], reverse=True)
        for video in newer_videos:
            date_str = video['date'][:10]
            transcript_file = TRANSCRIPT_DIR / f"{video['id']}_en-x-autogen.vtt"
            has_transcript = "✅" if transcript_file.exists() else "❌"
            print(f"{date_str} | {has_transcript} | {video['title'][:60]}")
    else:
        print("No videos found newer than 6/28/2025")

if __name__ == "__main__":
    check_recent_additions()
