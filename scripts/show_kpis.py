import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import TRANSCRIPT_DIR, DATABASE_PATH
from src.transcript_manager import TranscriptManager
import json
import sqlite3
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import os

def get_file_size_mb(file_path):
    """Get file size in MB"""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except:
        return 0

def format_duration(seconds):
    """Convert seconds to readable format"""
    if seconds >= 3600:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        minutes = seconds // 60
        return f"{minutes}m"

def show_system_kpis():
    """Display comprehensive KPIs for the Vimeo transcript system"""
    print("=" * 80)
    print("VIMEO TRANSCRIPT MANAGER - KEY PERFORMANCE INDICATORS")
    print("=" * 80)
    
    # Check if data exists
    video_data_path = TRANSCRIPT_DIR / 'video_data.json'
    if not video_data_path.exists():
        print("❌ No video data found. Run download_videos.py first.")
        return
    
    try:
        # Load video data
        with open(video_data_path, 'r', encoding='utf-8') as f:
            videos = json.load(f)
    except Exception as e:
        print(f"❌ Error loading video data: {e}")
        return
    
    # BASIC STATISTICS
    print("\n📊 BASIC STATISTICS")
    print("-" * 50)
    print(f"Total videos in database: {len(videos)}")
    
    # Check transcripts on disk
    vtt_files = list(TRANSCRIPT_DIR.glob('*.vtt'))
    print(f"Transcript files on disk: {len(vtt_files)}")
    
    # Check database
    db_processed = 0
    total_segments = 0
    if DATABASE_PATH.exists():
        try:
            tm = TranscriptManager()
            processed_ids = tm.get_processed_video_ids()
            db_processed = len(processed_ids)
            
            # Get segment count
            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM transcript_segments')
            total_segments = c.fetchone()[0]
            conn.close()
        except Exception as e:
            print(f"Error accessing database: {e}")
    
    print(f"Videos processed in database: {db_processed}")
    print(f"Total transcript segments: {total_segments:,}")
    
    # YEAR BREAKDOWN
    print(f"\n📅 VIDEOS BY YEAR")
    print("-" * 50)
    year_stats = defaultdict(lambda: {
        'total': 0, 
        'has_transcript': 0, 
        'processed': 0,
        'total_duration': 0
    })
    
    processed_ids = set()
    if DATABASE_PATH.exists():
        try:
            tm = TranscriptManager()
            processed_ids = tm.get_processed_video_ids()
        except:
            pass
    
    for video in videos:
        try:
            video_date = datetime.fromisoformat(video['date'].replace('Z', '+00:00'))
            year = video_date.year
            
            year_stats[year]['total'] += 1
            year_stats[year]['total_duration'] += video.get('duration', 0)
            
            # Check if transcript exists
            transcript_file = TRANSCRIPT_DIR / f"{video['id']}_en-x-autogen.vtt"
            if transcript_file.exists():
                year_stats[year]['has_transcript'] += 1
            
            # Check if processed in database
            if video['id'] in processed_ids:
                year_stats[year]['processed'] += 1
                
        except Exception as e:
            print(f"Error processing video date: {e}")
    
    for year in sorted(year_stats.keys(), reverse=True):
        stats = year_stats[year]
        duration_str = format_duration(stats['total_duration'])
        print(f"{year}: {stats['total']} videos ({duration_str}) | "
              f"Transcripts: {stats['has_transcript']} | "
              f"Processed: {stats['processed']}")
    
    # RECENT ACTIVITY
    print(f"\n🕒 RECENT ACTIVITY (Last 30 days)")
    print("-" * 50)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_videos = []
    
    for video in videos:
        try:
            video_date = datetime.fromisoformat(video['date'].replace('Z', '+00:00'))
            if video_date >= thirty_days_ago:
                recent_videos.append(video)
        except:
            continue
    
    if recent_videos:
        print(f"Videos published in last 30 days: {len(recent_videos)}")
        for video in sorted(recent_videos, key=lambda x: x['date'], reverse=True)[:5]:
            date_str = video['date'][:10]
            transcript_exists = "✅" if (TRANSCRIPT_DIR / f"{video['id']}_en-x-autogen.vtt").exists() else "❌"
            processed = "✅" if video['id'] in processed_ids else "❌"
            print(f"  {date_str} | T:{transcript_exists} P:{processed} | {video['title'][:60]}")
        if len(recent_videos) > 5:
            print(f"  ... and {len(recent_videos) - 5} more")
    else:
        print("No videos published in the last 30 days")
    
    # LONGEST VIDEOS
    print(f"\n⏱️  LONGEST VIDEOS")
    print("-" * 50)
    sorted_videos = sorted(videos, key=lambda x: x.get('duration', 0), reverse=True)[:10]
    for i, video in enumerate(sorted_videos, 1):
        duration_str = format_duration(video.get('duration', 0))
        transcript_exists = "✅" if (TRANSCRIPT_DIR / f"{video['id']}_en-x-autogen.vtt").exists() else "❌"
        processed = "✅" if video['id'] in processed_ids else "❌"
        print(f"{i:2d}. {duration_str} | T:{transcript_exists} P:{processed} | {video['title'][:50]}")
    
    # STORAGE STATISTICS
    print(f"\n💾 STORAGE STATISTICS")
    print("-" * 50)
    
    # Calculate transcript file sizes
    transcript_size_total = 0
    for vtt_file in vtt_files:
        transcript_size_total += get_file_size_mb(vtt_file)
    
    # Database size
    db_size = get_file_size_mb(DATABASE_PATH) if DATABASE_PATH.exists() else 0
    
    # Video data JSON size
    json_size = get_file_size_mb(video_data_path)
    
    print(f"Transcript files (.vtt): {transcript_size_total:.2f} MB")
    print(f"Database (SQLite): {db_size:.2f} MB")
    print(f"Video metadata (JSON): {json_size:.2f} MB")
    print(f"Total storage used: {transcript_size_total + db_size + json_size:.2f} MB")
    
    # PROCESSING STATUS
    print(f"\n🔄 PROCESSING STATUS")
    print("-" * 50)
    
    videos_with_transcripts = len(vtt_files)
    processing_rate = (db_processed / len(videos)) * 100 if videos else 0
    transcript_rate = (videos_with_transcripts / len(videos)) * 100 if videos else 0
    
    print(f"Transcript availability rate: {transcript_rate:.1f}%")
    print(f"Database processing rate: {processing_rate:.1f}%")
    
    # Missing transcripts
    videos_without_transcripts = []
    for video in videos:
        transcript_file = TRANSCRIPT_DIR / f"{video['id']}_en-x-autogen.vtt"
        if not transcript_file.exists():
            videos_without_transcripts.append(video)
    
    if videos_without_transcripts:
        print(f"\n⚠️  VIDEOS WITHOUT TRANSCRIPTS ({len(videos_without_transcripts)})")
        print("-" * 50)
        for video in videos_without_transcripts[:10]:  # Show first 10
            date_str = video['date'][:10]
            duration_str = format_duration(video.get('duration', 0))
            print(f"  {date_str} | {duration_str} | {video['title'][:50]}")
        if len(videos_without_transcripts) > 10:
            print(f"  ... and {len(videos_without_transcripts) - 10} more")
    
    # Unprocessed videos (have transcript but not in database)
    unprocessed_videos = []
    for video in videos:
        transcript_file = TRANSCRIPT_DIR / f"{video['id']}_en-x-autogen.vtt"
        if transcript_file.exists() and video['id'] not in processed_ids:
            unprocessed_videos.append(video)
    
    if unprocessed_videos:
        print(f"\n⚠️  VIDEOS WITH TRANSCRIPTS BUT NOT PROCESSED ({len(unprocessed_videos)})")
        print("-" * 50)
        for video in unprocessed_videos[:10]:  # Show first 10
            date_str = video['date'][:10]
            duration_str = format_duration(video.get('duration', 0))
            print(f"  {date_str} | {duration_str} | {video['title'][:50]}")
        if len(unprocessed_videos) > 10:
            print(f"  ... and {len(unprocessed_videos) - 10} more")
        print(f"💡 Run 'python scripts/update_database.py' to process these")
    
    # RECOMMENDATIONS
    print(f"\n💡 RECOMMENDATIONS")
    print("-" * 50)
    
    if videos_without_transcripts:
        print(f"• {len(videos_without_transcripts)} videos missing transcripts - run download script")
    
    if unprocessed_videos:
        print(f"• {len(unprocessed_videos)} transcripts need database processing - run update_database.py")
    
    if not videos_without_transcripts and not unprocessed_videos:
        print("• ✅ All videos are fully processed and searchable!")
        print("• Consider running incremental updates regularly to catch new videos")
    
    print(f"\n📈 SYSTEM HEALTH: ", end="")
    if processing_rate >= 90:
        print("🟢 EXCELLENT")
    elif processing_rate >= 70:
        print("🟡 GOOD")
    else:
        print("🔴 NEEDS ATTENTION")

def show_detailed_video_list():
    """Show detailed list of all videos"""
    print("\n" + "=" * 80)
    print("DETAILED VIDEO LIST")
    print("=" * 80)
    
    video_data_path = TRANSCRIPT_DIR / 'video_data.json'
    if not video_data_path.exists():
        print("❌ No video data found.")
        return
    
    try:
        with open(video_data_path, 'r', encoding='utf-8') as f:
            videos = json.load(f)
    except Exception as e:
        print(f"❌ Error loading video data: {e}")
        return
    
    # Get processed video IDs
    processed_ids = set()
    if DATABASE_PATH.exists():
        try:
            tm = TranscriptManager()
            processed_ids = tm.get_processed_video_ids()
        except:
            pass
    
    print(f"Legend: T=Transcript Available, P=Processed in Database")
    print("-" * 80)
    
    for i, video in enumerate(videos, 1):
        date_str = video['date'][:10]
        duration_str = format_duration(video.get('duration', 0))
        transcript_exists = "✅" if (TRANSCRIPT_DIR / f"{video['id']}_en-x-autogen.vtt").exists() else "❌"
        processed = "✅" if video['id'] in processed_ids else "❌"
        
        print(f"{i:3d}. {date_str} | {duration_str:>6} | T:{transcript_exists} P:{processed} | {video['title']}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Show KPIs for Vimeo Transcript Manager')
    parser.add_argument('--detailed', '-d', action='store_true', 
                       help='Show detailed list of all videos')
    
    args = parser.parse_args()
    
    show_system_kpis()
    
    if args.detailed:
        show_detailed_video_list()
    else:
        print(f"\n💡 Use --detailed flag to see complete video list")
