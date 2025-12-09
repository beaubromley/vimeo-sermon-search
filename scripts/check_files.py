import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import TRANSCRIPT_DIR
import os

def check_files():
    print("\nChecking directory structure and files...")
    
    # Check if transcripts directory exists
    print(f"\nTranscript directory path: {TRANSCRIPT_DIR}")
    if not TRANSCRIPT_DIR.exists():
        print("ERROR: Transcripts directory does not exist!")
        return
        
    # List all files in the transcripts directory
    print("\nFiles in transcripts directory:")
    files = list(TRANSCRIPT_DIR.glob('*'))
    if not files:
        print("No files found in transcripts directory")
    else:
        for file in files:
            print(f"- {file.name} ({file.stat().st_size / 1024:.2f} KB)")
            
    # Specifically look for VTT files
    vtt_files = list(TRANSCRIPT_DIR.glob('*.vtt'))
    print(f"\nVTT files found: {len(vtt_files)}")
    
    # Check if video_data.json exists
    json_path = TRANSCRIPT_DIR / 'video_data.json'
    if json_path.exists():
        print(f"\nvideo_data.json exists: {json_path.stat().st_size / 1024:.2f} KB")
    else:
        print("\nERROR: video_data.json not found!")

if __name__ == "__main__":
    check_files()
