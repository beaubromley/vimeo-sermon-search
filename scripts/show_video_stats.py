import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import TRANSCRIPT_DIR
import json
from datetime import datetime
from collections import Counter

def show_video_stats():
    try:
        # Load video data
        with open(TRANSCRIPT_DIR / 'video_data.json', 'r', encoding='utf-8') as f:
            videos = json.load(f)
        
        # Count videos by year
        year_counts = Counter()
        for video in videos:
            try:
                date = datetime.fromisoformat(video['date'].replace('Z', '+00:00'))
                year_counts[date.year] += 1
            except Exception as e:
                print(f"Error parsing date for video: {video['title']}")
        
        # Show statistics
        print("\nVideo Distribution by Year:")
        print("-" * 30)
        for year in sorted(year_counts.keys()):
            print(f"{year}: {year_counts[year]} videos")
        
        # Check transcripts
        transcript_counts = Counter()
        for video in videos:
            vtt_file = TRANSCRIPT_DIR / f"{video['id']}_en-x-autogen.vtt"
            if vtt_file.exists():
                try:
                    date = datetime.fromisoformat(video['date'].replace('Z', '+00:00'))
                    transcript_counts[date.year] += 1
                except Exception:
                    pass
        
        print("\nTranscripts Available by Year:")
        print("-" * 30)
        for year in sorted(transcript_counts.keys()):
            print(f"{year}: {transcript_counts[year]} transcripts")
        
    except Exception as e:
        print(f"Error reading video data: {e}")

if __name__ == "__main__":
    show_video_stats()
