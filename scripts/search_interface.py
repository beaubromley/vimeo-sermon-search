import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.transcript_manager import TranscriptManager

def format_search_results(results):
    if not results:
        return "\nNo matches found."
        
    output = []
    
    # Group results by type
    transcript_results = [r for r in results if r['match_type'] == 'transcript']
    title_results = [r for r in results if r['match_type'] == 'title']
    
    # Show title matches first
    if title_results:
        output.append(f"\n🎬 TITLE MATCHES ({len(title_results)}):")
        output.append("=" * 60)
        for result in title_results:
            output.append(f"\n📺 {result['title']}")
            output.append(f"🔗 URL: {result['url']}")
            output.append(f"📍 Match: {result['match']}")
            output.append("-" * 40)
    
    # Show transcript matches
    if transcript_results:
        output.append(f"\n📝 TRANSCRIPT MATCHES ({len(transcript_results)}):")
        output.append("=" * 60)
        for result in transcript_results:
            output.append(f"\n📺 {result['title']}")
            output.append(f"⏰ Timestamp: {result['timestamp']}")
            output.append(f"🔗 URL: {result['url']}")
            output.append("\n💬 Transcript:")
            
            # Add context with matched text highlighted
            for text, time, _ in result['context']:
                if text == result['match']:
                    output.append(f">>> {text}")
                else:
                    output.append(text)
            
            output.append("-" * 40)
    
    return "\n".join(output)

def main():
    print("\n🎥 Vimeo Transcript & Title Search")
    print("=" * 50)
    print("Search through video transcripts AND titles")
    print("- Enter your search terms")
    print("- Results will show both title matches and transcript matches")
    print("- Transcript matches include timestamps and direct links")
    print("- Type 'transcripts only' to search only transcripts")
    print("- Type 'titles only' to search only titles")
    print("- Press Ctrl+C or type 'quit' to exit")
    print("\n💡 Tip: Try searching for specific phrases, keywords, or video titles\n")
    
    tm = TranscriptManager()
    search_mode = "both"  # Default to searching both
    
    while True:
        try:
            query = input(f"\nEnter search term (mode: {search_mode}): ").strip()
            if not query:
                continue
            if query.lower() == 'quit':
                break
            
            # Handle mode switching
            if query.lower() == 'transcripts only':
                search_mode = "transcripts"
                print("🔄 Switched to transcript-only search mode")
                continue
            elif query.lower() == 'titles only':
                search_mode = "titles"
                print("🔄 Switched to title-only search mode")
                continue
            elif query.lower() == 'both' or query.lower() == 'all':
                search_mode = "both"
                print("🔄 Switched to search both titles and transcripts")
                continue
            
            print(f"\n🔍 Searching ({search_mode})...")
            
            # Determine search parameters based on mode
            if search_mode == "titles":
                # Search only titles - we'll modify the search to return empty transcript results
                results = tm.search_transcripts("", search_titles=True)  # Empty query for transcripts
                # Filter to only title matches and search manually
                conn = tm.db_path
                import sqlite3
                conn = sqlite3.connect(tm.db_path)
                c = conn.cursor()
                c.execute('''
                    SELECT title, url, video_id
                    FROM videos
                    WHERE title LIKE ?
                    ORDER BY title
                ''', (f'%{query}%',))
                title_matches = c.fetchall()
                conn.close()
                
                results = []
                for title, video_url, video_id in title_matches:
                    results.append({
                        'title': title,
                        'timestamp': '00:00:00',
                        'url': video_url,
                        'match': f"Title contains: '{query}'",
                        'match_type': 'title',
                        'context': [(f"Title match: {title}", 0, video_url)]
                    })
            elif search_mode == "transcripts":
                results = tm.search_transcripts(query, search_titles=False)
            else:  # both
                results = tm.search_transcripts(query, search_titles=True)
            
            if results:
                total_matches = len(results)
                transcript_count = len([r for r in results if r['match_type'] == 'transcript'])
                title_count = len([r for r in results if r['match_type'] == 'title'])
                
                print(f"\n📊 Found {total_matches} total matches:")
                if title_count > 0:
                    print(f"   📺 {title_count} title matches")
                if transcript_count > 0:
                    print(f"   📝 {transcript_count} transcript matches")
                    
                print(format_search_results(results))
            else:
                print(f"\n❌ No matches found for '{query}' in {search_mode}.")
                
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
            break
        except Exception as e:
            print(f"\n❌ Error during search: {e}")

if __name__ == "__main__":
    main()
