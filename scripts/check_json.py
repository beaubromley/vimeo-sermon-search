import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import TRANSCRIPT_DIR
import json

def check_json_file():
    json_path = TRANSCRIPT_DIR / 'video_data.json'
    print(f"\nChecking JSON file at: {json_path}")
    
    if not json_path.exists():
        print("Error: File does not exist!")
        return
        
    print(f"File size: {json_path.stat().st_size / 1024:.2f} KB")
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Successfully read JSON data")
        print(f"Number of videos: {len(data)}")
        if len(data) > 0:
            print("\nFirst video example:")
            first_video = data[0]
            for key, value in first_video.items():
                print(f"{key}: {value}")
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    check_json_file()
