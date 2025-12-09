import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.transcript_manager import TranscriptManager
from src.config import TRANSCRIPT_DIR
import json
from datetime import datetime

def update_database():
    print("\nChecking for new transcripts and updating database...")
    tm = TranscriptManager()
    
    # Load existing video data
    try:
        with open(TRANSCRIPT_DIR / 'video_data.json', 'r', encoding='utf-8') as f:
            videos = json.load(f)
        print(f"Loaded metadata for {len(videos)} videos")
    except Exception as e:
        print(f"Error reading video data: {e}")
        return

    # Get list of all VTT files
    vtt_files = list(TRANSCRIPT_DIR.glob('*_en-x-autogen.vtt'))
    print(f"Found {len(vtt_files)} transcript files")

    # Get list of already processed videos
    processed_videos = tm.get_processed_video_ids()
    print(f"Database currently contains {len(processed_videos)} processed videos")

    # Process new videos
    new_count = 0
    for video in videos:
        vtt_file = TRANSCRIPT_DIR / f"{video['id']}_en-x-autogen.vtt"
        if vtt_file.exists() and video['id'] not in processed_videos:
            print(f"\nProcessing new video: {video['title']}")
            try:
                if tm.add_video(video, str(vtt_file)):
                    new_count += 1
                    print("Successfully processed!")
                else:
                    print("Failed to process")
            except Exception as e:
                print(f"Error processing video: {e}")

    print(f"\nUpdate complete!")
    print(f"Added {new_count} new videos to the database")
    print(f"Total videos in database: {len(processed_videos) + new_count}")

if __name__ == "__main__":
    update_database()
