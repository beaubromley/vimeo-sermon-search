import sqlite3
import webvtt # Make sure this import is present
from pathlib import Path
from pathlib import Path

# Define DATABASE_PATH directly since config.py is not in repo
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
DATABASE_DIR = DATA_DIR / 'database'
DATABASE_PATH = DATABASE_DIR / 'transcripts.db'


class TranscriptManager:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.setup_database()

    def setup_database(self):
        """Create SQLite database and tables"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Create tables
        c.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                duration INTEGER,
                url TEXT,
                date_published TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS transcript_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                start_time REAL,
                end_time REAL,
                text TEXT,
                vimeo_url TEXT,
                FOREIGN KEY (video_id) REFERENCES videos (video_id)
            )
        ''')
        
        # Create full-text search index
        c.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS transcript_search 
            USING fts5(video_id, start_time, end_time, text, vimeo_url)
        ''')
        
        conn.commit()
        conn.close()

    def _timestamp_to_seconds(self, timestamp):
        """Convert VTT timestamp to seconds"""
        try:
            parts = timestamp.split(':')
            if len(parts) == 3:
                h, m, s = parts
                return float(h) * 3600 + float(m) * 60 + float(s)
            elif len(parts) == 2: # Handle MM:SS.mmm
                m, s = parts
                return float(m) * 60 + float(s)
            else:
                # Fallback or error for unexpected format
                return 0.0 # Or raise an error
        except ValueError:
             # Handle cases like "WEBVTT" or other non-timestamp lines if webvtt library doesn't filter them
            return 0.0 # Or raise an error


    def _format_timestamp(self, seconds):
        """Convert seconds to HH:MM:SS format"""
        try:
            # Convert string to float if necessary
            if isinstance(seconds, str):
                seconds = float(seconds)
            
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        except Exception as e:
            print(f"Error formatting timestamp {seconds}: {e}")
            return "00:00:00"

    def add_video(self, video_data, vtt_file):
        """Add video and its transcript to database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Add video info
            c.execute('''
                INSERT OR REPLACE INTO videos 
                (video_id, title, duration, url, date_published)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                video_data['id'],
                video_data['title'],
                video_data['duration'],
                video_data['url'],
                video_data['date']
            ))
            
            # Parse and add transcript segments
            for caption in webvtt.read(vtt_file):
                start_time = self._timestamp_to_seconds(caption.start)
                end_time = self._timestamp_to_seconds(caption.end)
                
                # Use player.vimeo.com to avoid spam check
                video_id = video_data['url'].split('/')[-1]
                vimeo_url = f"https://player.vimeo.com/video/{video_id}#t={int(start_time)}s"
                
                # Add to main table
                c.execute('''
                    INSERT INTO transcript_segments 
                    (video_id, start_time, end_time, text, vimeo_url)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    video_data['id'],
                    start_time,
                    end_time,
                    caption.text,
                    vimeo_url
                ))
                
                # Add to search index
                c.execute('''
                    INSERT INTO transcript_search 
                    (video_id, start_time, end_time, text, vimeo_url)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    video_data['id'],
                    str(start_time), # FTS5 stores everything as text
                    str(end_time),
                    caption.text,
                    vimeo_url
                ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error adding video {video_data.get('id', 'Unknown ID')} with VTT file {vtt_file}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_processed_video_ids(self):
        """Get list of video IDs that have already been processed"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute('SELECT video_id FROM videos')
            return set(row[0] for row in c.fetchall())
        except Exception as e:
            print(f"Error getting processed video IDs: {e}")
            return set()
        finally:
            conn.close()

    def search_transcripts(self, query, context_size=2, search_titles=True):
        """Search transcripts and video titles, return matches with context"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        results = []
        try:
            # First, search in transcript text
            c.execute('''
                SELECT 
                    v.title,
                    ts_search.start_time, 
                    ts_search.text, 
                    ts_search.vimeo_url,
                    'transcript' as match_type
                FROM transcript_search AS ts_search
                JOIN videos AS v ON ts_search.video_id = v.video_id
                WHERE ts_search.text MATCH ?
                ORDER BY v.title, CAST(ts_search.start_time AS REAL)
            ''', (query,))
            
            transcript_matches = c.fetchall()
            
            # Process transcript matches
            for match in transcript_matches:
                title, start_time_str, text, url, match_type = match
                start_time_float = float(start_time_str)
                
                results.append({
                    'title': title,
                    'timestamp': self._format_timestamp(start_time_float),
                    'url': url,
                    'match': text,
                    'match_type': 'transcript',
                    'context': [(text, start_time_float, url)]
                })
            
            # If search_titles is enabled, also search video titles
            if search_titles:
                # Search for videos where title contains the query (case-insensitive)
                c.execute('''
                    SELECT 
                        v.title,
                        v.url,
                        v.video_id
                    FROM videos AS v
                    WHERE v.title LIKE ?
                    ORDER BY v.title
                ''', (f'%{query}%',))
                
                title_matches = c.fetchall()
                
                # Process title matches
                for match in title_matches:
                    title, video_url, video_id = match
                    
                    results.append({
                        'title': title,
                        'timestamp': '00:00:00',  # Start of video for title matches
                        'url': video_url,
                        'match': f"Title contains: '{query}'",
                        'match_type': 'title',
                        'context': [(f"Title match: {title}", 0, video_url)]
                    })
            
            return results
            
        except Exception as e:
            print(f"Error searching transcripts: {e}")
            return []
        finally:
            conn.close()


