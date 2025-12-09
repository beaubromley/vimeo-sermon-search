import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import json
from src.config import TRANSCRIPT_DIR

def check_status():
    print("\nChecking download status...")
    
    # Check video data
    video_data_path = TRANSCRIPT_DIR / 'video_data.json'
    if video_data_path.exists():
        with open(video_data_path, 'r', encoding='utf-8') as f:
            videos = json.load(f)
        print(f"\nFound metadata for {len(videos)} videos")
    else:
        print("ERROR: No video_data.json found!")
        return
        
    # Check transcripts
    vtt_files = list(TRANSCRIPT_DIR.glob('*.vtt'))
    if vtt_files:
        print(f"\nFound {len(vtt_files)} transcript files:")
        for vtt in vtt_files[:5]:  # Show first 5 only
            print(f"- {vtt.name}")
        if len(vtt_files) > 5:
            print(f"... and {len(vtt_files) - 5} more")
    else:
        print("\nNo transcript (.vtt) files found")

    print("\nNext steps:")
    if not video_data_path.exists():
        print("1. Run download_videos.py again to get video metadata")
    elif not vtt_files:
        print("1. Check if any videos should have transcripts")
    else:
        print("1. Run process_transcripts.py to create the searchable database")
        print("2. Then run search_interface.py to search through transcripts")

if __name__ == "__main__":
    check_status()
