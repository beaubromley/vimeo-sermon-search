import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.transcript_manager import TranscriptManager
from src.config import TRANSCRIPT_DIR
import json

def process_existing_videos():
    print("\nInitializing transcript processing...")
    tm = TranscriptManager()
    
    # Load video data with explicit UTF-8 encoding
    try:
        with open(TRANSCRIPT_DIR / 'video_data.json', 'r', encoding='utf-8') as f:
            videos = json.load(f)
        print(f"Loaded metadata for {len(videos)} videos")
    except Exception as e:
        print(f"Error reading video data: {e}")
        return
    
    processed_count = 0
    for video in videos:
        # Update the file pattern to match the actual files
        vtt_file = TRANSCRIPT_DIR / f"{video['id']}_en-x-autogen.vtt"
        if vtt_file.exists():
            print(f"\nProcessing: {video['title']}")
            try:
                if tm.add_video(video, str(vtt_file)):
                    processed_count += 1
                    print("Successfully processed!")
                else:
                    print("Failed to process")
            except Exception as e:
                print(f"Error processing video: {e}")
    
    print(f"\nProcessing complete!")
    print(f"Successfully processed {processed_count} videos with transcripts")
    print(f"Out of {len(videos)} total videos")

if __name__ == "__main__":
    process_existing_videos()
