import json
from pathlib import Path

def check_downloads():
    # Check video data
    data_path = Path('data/transcripts/video_data.json')
    if data_path.exists():
        with open(data_path, 'r', encoding='utf-8') as f:
            videos = json.load(f)
        print(f"\nFound metadata for {len(videos)} videos")
    else:
        print("No video_data.json found")
        
    # Check transcripts
    transcript_path = Path('data/transcripts')
    vtt_files = list(transcript_path.glob('*.vtt'))
    if vtt_files:
        print(f"Found {len(vtt_files)} transcript files:")
        for vtt in vtt_files:
            print(f"- {vtt.name}")
    else:
        print("No transcript (.vtt) files found")

if __name__ == "__main__":
    check_downloads()
