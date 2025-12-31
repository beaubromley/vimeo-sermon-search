# streamlit_app.py
import streamlit as st
import sys
from pathlib import Path
from collections import defaultdict
import plotly.graph_objects as go
from datetime import datetime
import plotly.express as px
from collections import Counter



# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.transcript_manager import TranscriptManager
from pathlib import Path

# Define paths directly since config.py is not in repo
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
TRANSCRIPT_DIR = DATA_DIR / 'transcripts'
DATABASE_DIR = DATA_DIR / 'database'
DATABASE_PATH = DATABASE_DIR / 'transcripts.db'

import json
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
import os
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="HHBC Sermon Search",
    page_icon="assets/page_icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling and reduced whitespace
st.markdown("""
    <style>
    /* Reduce padding and margins */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* Reduce header spacing */
    h1, h2, h3 {
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    /* Compact metrics */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
    
    /* Reduce expander spacing */
    .streamlit-expanderHeader {
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
    }
    
    /* Reduce space between elements */
    .element-container {
        margin-bottom: 0.5rem;
    }
    
    /* Compact dataframe */
    .dataframe {
        font-size: 0.9rem;
    }
    
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.25rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 0.5rem;
    }
    .has-transcript-full {
        color: #4caf50;
        font-weight: bold;
    }
    .has-transcript-partial {
        color: #ff9800;
        font-weight: bold;
    }
    .no-transcript {
        color: #999;
    }
    .year-section {
        background-color: #f5f5f5;
        padding: 0.5rem;
        border-radius: 0.3rem;
        margin-bottom: 0.5rem;
    }
    
    /* Hide streamlit branding for more space */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Reduce tab spacing */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'last_search_query' not in st.session_state:
    st.session_state.last_search_query = ""
if 'last_start_date' not in st.session_state:
    st.session_state.last_start_date = None
if 'last_end_date' not in st.session_state:
    st.session_state.last_end_date = None
if 'search_results' not in st.session_state:
    st.session_state.search_results = None

@st.cache_resource
def get_transcript_manager():
    """Cache the TranscriptManager instance"""
    return TranscriptManager()

@st.cache_data
def load_video_stats():
    """Load and cache video statistics"""
    video_data_path = TRANSCRIPT_DIR / 'video_data.json'
    if not video_data_path.exists():
        return None
    
    try:
        with open(video_data_path, 'r', encoding='utf-8') as f:
            videos = json.load(f)
        
        # Calculate statistics
        total_videos = len(videos)
        vtt_files = list(TRANSCRIPT_DIR.glob('*.vtt'))
        transcripts_available = len(vtt_files)
        
        # Create set of video IDs with transcripts
        transcript_video_ids = set()
        for vtt_file in vtt_files:
            # Extract video ID from filename (format: {video_id}_en-x-autogen.vtt)
            video_id = vtt_file.stem.replace('_en-x-autogen', '')
            transcript_video_ids.add(video_id)
        
        # Database stats
        db_processed = 0
        total_segments = 0
        if DATABASE_PATH.exists():
            tm = get_transcript_manager()
            processed_ids = tm.get_processed_video_ids()
            db_processed = len(processed_ids)
            
            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM transcript_segments')
            total_segments = c.fetchone()[0]
            conn.close()
        
        # Year breakdown with transcript info
        year_stats = defaultdict(lambda: {'total': 0, 'with_transcripts': 0})
        for video in videos:
            try:
                video_date = datetime.fromisoformat(video['date'].replace('Z', '+00:00'))
                year = video_date.year
                year_stats[year]['total'] += 1
                if video['id'] in transcript_video_ids:
                    year_stats[year]['with_transcripts'] += 1
            except:
                pass
        
        return {
            'total_videos': total_videos,
            'transcripts_available': transcripts_available,
            'db_processed': db_processed,
            'total_segments': total_segments,
            'year_stats': dict(year_stats),
            'videos': videos,
            'transcript_video_ids': transcript_video_ids
        }
    except Exception as e:
        st.error(f"Error loading video data: {e}")
        return None

def format_duration(seconds):
    """Convert seconds to readable format"""
    if seconds >= 3600:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        minutes = seconds // 60
        return f"{minutes}m"

def perform_search(search_query, start_date=None, end_date=None):
    """Perform the actual search - always search both"""
    if not search_query or len(search_query) < 2:
        return None
    
    tm = get_transcript_manager()
    
    # Get all results (no limit)
    results = tm.search_transcripts(search_query, context_size=2, search_titles=True)
    
    # Filter by date if provided
    if start_date or end_date:
        # Load video data to get dates
        video_data_path = TRANSCRIPT_DIR / 'video_data.json'
        if video_data_path.exists():
            with open(video_data_path, 'r', encoding='utf-8') as f:
                videos = json.load(f)
            
            # Create a mapping of video titles to dates
            video_dates = {}
            for video in videos:
                try:
                    video_date = datetime.fromisoformat(video['date'].replace('Z', '+00:00')).date()
                    video_dates[video['title']] = video_date
                except:
                    pass
            
            # Filter results by date
            filtered_results = []
            for result in results:
                video_title = result['title']
                if video_title in video_dates:
                    video_date = video_dates[video_title]
                    
                    # Check date range
                    if start_date and video_date < start_date:
                        continue
                    if end_date and video_date > end_date:
                        continue
                    
                    filtered_results.append(result)
            
            results = filtered_results
    
    return results  # Return all results, no limit

def results_to_dataframe(results, result_type='all'):
    """Convert search results to a pandas DataFrame"""
    if not results:
        return None
    
    # Filter by type if needed
    if result_type == 'title':
        results = [r for r in results if r.get('match_type') == 'title']
    elif result_type == 'transcript':
        results = [r for r in results if r.get('match_type') == 'transcript']
    
    if not results:
        return None
    
    # Load video data to get descriptions/speakers
    video_data_path = TRANSCRIPT_DIR / 'video_data.json'
    speaker_map = {}
    if video_data_path.exists():
        with open(video_data_path, 'r', encoding='utf-8') as f:
            videos = json.load(f)
        
        # Extract speaker names from descriptions
        for video in videos:
            speaker = "Unknown"
            desc = video.get('description', '')
            
            if desc and 'Speaker:' in desc:
                # Handle format like "Speaker: Dennis Newkirk"
                try:
                    start = desc.index('Speaker:') + len('Speaker:')
                    # Get text after "Speaker:" until newline or end
                    rest = desc[start:].strip()
                    speaker = rest.split('\n')[0].strip()
                except:
                    pass
            elif desc and 'Presented by' in desc:
                # Extract name between "Presented by" and "on"
                try:
                    start = desc.index('Presented by') + len('Presented by')
                    end = desc.index(' on ', start)
                    speaker = desc[start:end].strip()
                except:
                    pass
            elif desc and 'preaches' in desc.lower():
                # Handle format like "Chris Cross preaches"
                try:
                    speaker = desc.split('preaches')[0].strip()
                except:
                    pass
            
            speaker_map[video['title']] = speaker
    
    data = []
    for result in results:
        match_type = result.get('match_type', 'transcript')
        speaker = speaker_map.get(result['title'], 'Unknown')
        
        if match_type == 'title':
            data.append({
                'Type': 'Title',
                'Speaker': speaker,
                'Video Title': result['title'],
                'Timestamp': '00:00:00',
                'Match': result['match'],
                'URL': result['url']
            })
        else:
            data.append({
                'Type': 'Transcript',
                'Speaker': speaker,
                'Video Title': result['title'],
                'Timestamp': result['timestamp'],
                'Match': result['match'][:150] + '...' if len(result['match']) > 150 else result['match'],
                'URL': result['url']
            })
    
    return pd.DataFrame(data)


def main():
    # Logo
    logo_path = Path("assets/download.png")
    if logo_path.exists():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(str(logo_path), use_column_width=True)

    else:
        # Fallback to text header if image not found
        st.markdown('<p class="main-header">Henderson Hills Sermon Library</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Search sermons and explore the teaching archive</p>', unsafe_allow_html=True)

    
    # Load stats
    stats = load_video_stats()
    
    # Main navigation tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Home", "Video List", "Bible Heat Map", "Speaker Stats"])
    
    # TAB 1: HOME - SERMON SEARCH
    with tab1:
        st.header("Sermon Search")
        
        # Search input
        search_query = st.text_input(
            "Enter search terms:",
            placeholder="e.g., 'faith', 'prayer', 'salvation', 'grace', etc.",
            help="Search updates as you type",
            key="search_input"
        )
        
        # Date filter (optional) - more compact
        with st.expander("Date Filter (Optional)"):
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Start Date",
                    value=None,
                    help="Filter videos from this date onwards",
                    key="start_date_input"
                )
            with col2:
                end_date = st.date_input(
                    "End Date",
                    value=None,
                    help="Filter videos up to this date",
                    key="end_date_input"
                )
            
            if start_date or end_date:
                if start_date and end_date and start_date > end_date:
                    st.error("Start date must be before end date")
        
        # Check if search should be triggered
        should_search = False
        if search_query:
            if (search_query != st.session_state.last_search_query or
                start_date != st.session_state.last_start_date or
                end_date != st.session_state.last_end_date):
                should_search = True
        
        # Perform search automatically when conditions change
        if should_search and search_query:
            if len(search_query) < 2:
                st.warning("Please enter at least 2 characters to search")
                st.session_state.search_results = None
            else:
                # Validate dates
                if start_date and end_date and start_date > end_date:
                    st.error("Start date must be before end date")
                    st.session_state.search_results = None
                else:
                    # Update session state
                    st.session_state.last_search_query = search_query
                    st.session_state.last_start_date = start_date
                    st.session_state.last_end_date = end_date
                    
                    with st.spinner("Searching..."):
                        results = perform_search(search_query, start_date, end_date)
                        st.session_state.search_results = results
        
        # Display results if they exist
        if st.session_state.search_results is not None:
            results = st.session_state.search_results
            
            if results:
                # Summary
                transcript_count = len([r for r in results if r.get('match_type') == 'transcript'])
                title_count = len([r for r in results if r.get('match_type') == 'title'])
                
                date_filter_text = ""
                if st.session_state.last_start_date or st.session_state.last_end_date:
                    if st.session_state.last_start_date and st.session_state.last_end_date:
                        date_filter_text = f" (from {st.session_state.last_start_date} to {st.session_state.last_end_date})"
                    elif st.session_state.last_start_date:
                        date_filter_text = f" (from {st.session_state.last_start_date} onwards)"
                    elif st.session_state.last_end_date:
                        date_filter_text = f" (up to {st.session_state.last_end_date})"
                
                st.success(f"Found {len(results)} matches for '{st.session_state.last_search_query}'{date_filter_text}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Matches", len(results))
                with col2:
                    st.metric("Title Matches", title_count)
                with col3:
                    st.metric("Transcript Matches", transcript_count)
                
                # Tabs for different result types
                if title_count > 0 and transcript_count > 0:
                    result_tab1, result_tab2, result_tab3 = st.tabs(["All Results", "Title Matches", "Transcript Matches"])
                    
                    with result_tab1:
                        df = results_to_dataframe(results, 'all')
                        if df is not None:
                            st.dataframe(
                                df,
                                column_config={
                                    "URL": st.column_config.LinkColumn("Watch Video"),
                                    "Type": st.column_config.TextColumn("Type", width="small"),
                                    "Speaker": st.column_config.TextColumn("Speaker", width="small"),
                                    "Video Title": st.column_config.TextColumn("Video Title", width="medium"),
                                    "Timestamp": st.column_config.TextColumn("Time", width="small"),
                                    "Match": st.column_config.TextColumn("Match", width="large")
                                },
                                hide_index=True,
                                use_container_width=True,
                                height=600
                            )
                    
                    with result_tab2:
                        df = results_to_dataframe(results, 'title')
                        if df is not None:
                            st.dataframe(
                                df,
                                column_config={
                                    "URL": st.column_config.LinkColumn("Watch Video"),
                                    "Type": st.column_config.TextColumn("Type", width="small"),
                                    "Speaker": st.column_config.TextColumn("Speaker", width="small"),
                                    "Video Title": st.column_config.TextColumn("Video Title", width="medium"),
                                    "Timestamp": st.column_config.TextColumn("Time", width="small"),
                                    "Match": st.column_config.TextColumn("Match", width="large")
                                },
                                hide_index=True,
                                use_container_width=True,
                                height=600
                            )
                        else:
                            st.info("No title matches")
                    
                    with result_tab3:
                        df = results_to_dataframe(results, 'transcript')
                        if df is not None:
                            st.dataframe(
                                df,
                                column_config={
                                    "URL": st.column_config.LinkColumn("Watch Video"),
                                    "Type": st.column_config.TextColumn("Type", width="small"),
                                    "Speaker": st.column_config.TextColumn("Speaker", width="small"),
                                    "Video Title": st.column_config.TextColumn("Video Title", width="medium"),
                                    "Timestamp": st.column_config.TextColumn("Time", width="small"),
                                    "Match": st.column_config.TextColumn("Match", width="large")
                                },
                                hide_index=True,
                                use_container_width=True,
                                height=600
                            )
                        else:
                            st.info("No transcript matches")
                else:
                    # Just show all results in a table
                    df = results_to_dataframe(results, 'all')
                    if df is not None:
                        st.dataframe(
                            df,
                            column_config={
                                "URL": st.column_config.LinkColumn("Watch Video"),
                                "Type": st.column_config.TextColumn("Type", width="small"),
                                "Speaker": st.column_config.TextColumn("Speaker", width="small"),
                                "Video Title": st.column_config.TextColumn("Video Title", width="medium"),
                                "Timestamp": st.column_config.TextColumn("Time", width="small"),
                                "Match": st.column_config.TextColumn("Match", width="large")
                            },
                            hide_index=True,
                            use_container_width=True,
                            height=600
                        )
            else:
                st.warning(f"No matches found for '{st.session_state.last_search_query}'")
                st.info("Try different search terms or adjust the date filter")
    
    # TAB 2: VIDEO LIST
    with tab2:
        st.header("Video List")
        
        # Load video data
        video_data_path = TRANSCRIPT_DIR / 'video_data.json'
        if not video_data_path.exists():
            st.error("Video data not found")
            return
        
        with open(video_data_path, 'r', encoding='utf-8') as f:
            all_videos = json.load(f)
        
        # Extract speakers from all videos
        speakers_set = set()
        video_speakers = {}
        for video in all_videos:
            desc = video.get('description', '')
            speaker = "Unknown"
            
            if desc and 'Speaker:' in desc:
                try:
                    start = desc.index('Speaker:') + len('Speaker:')
                    speaker = desc[start:].strip().split('\n')[0].strip()
                except:
                    pass
            elif desc and 'Presented by' in desc:
                try:
                    start = desc.index('Presented by') + len('Presented by')
                    end = desc.index(' on ', start)
                    speaker = desc[start:end].strip()
                except:
                    pass
            elif desc and 'preaches' in desc.lower():
                try:
                    speaker = desc.split('preaches')[0].strip()
                except:
                    pass
            
            speakers_set.add(speaker)
            video_speakers[video['id']] = speaker
        
        # Filters
        st.subheader("Filters")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            speaker_filter = st.selectbox(
                "Speaker",
                ["All"] + sorted(list(speakers_set)),
                key="video_list_speaker"
            )
        
        with col2:
            # Get unique years
            years = set()
            for video in all_videos:
                try:
                    video_date = datetime.fromisoformat(video['date'].replace('Z', '+00:00'))
                    years.add(video_date.year)
                except:
                    pass
            
            year_filter = st.selectbox(
                "Year",
                ["All"] + sorted(list(years), reverse=True),
                key="video_list_year"
            )
        
        with col3:
            # Get books from bible_references table
            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()
            c.execute('SELECT DISTINCT book FROM bible_references ORDER BY book')
            books = [row[0] for row in c.fetchall()]
            
            book_filter = st.selectbox(
                "Bible Book",
                ["All"] + books,
                key="video_list_book"
            )
        
        with col4:
            # Get topics from theological_topics table
            c.execute('SELECT DISTINCT topic FROM theological_topics ORDER BY topic')
            topics = [row[0] for row in c.fetchall()]
            
            topic_filter = st.selectbox(
                "Theological Topic",
                ["All"] + topics,
                key="video_list_topic"
            )
        
        # Build filtered video list
        filtered_videos = []
        
        # Get list of videos that are in the database (have transcripts)
        c.execute('SELECT DISTINCT video_id FROM transcript_segments')
        videos_in_db = set(row[0] for row in c.fetchall())
        
        for video in all_videos:
            # Check if video is in database (has transcript)
            if video['id'] not in videos_in_db:
                continue  # Skip videos without transcripts

            
            # Apply speaker filter
            if speaker_filter != "All":
                if video_speakers.get(video['id']) != speaker_filter:
                    continue
            
            # Apply year filter
            if year_filter != "All":
                try:
                    video_date = datetime.fromisoformat(video['date'].replace('Z', '+00:00'))
                    if video_date.year != year_filter:
                        continue
                except:
                    continue
            
            # Apply book filter
            if book_filter != "All":
                c.execute('''
                    SELECT COUNT(*) FROM bible_references 
                    WHERE video_id = ? AND book = ?
                ''', (video['id'], book_filter))
                if c.fetchone()[0] == 0:
                    continue
            
            # Apply topic filter
            if topic_filter != "All":
                c.execute('''
                    SELECT COUNT(*) FROM theological_topics 
                    WHERE video_id = ? AND topic = ?
                ''', (video['id'], topic_filter))
                if c.fetchone()[0] == 0:
                    continue
            
            filtered_videos.append(video)
        
        conn.close()
        
        # Display results
        st.markdown("---")
        st.subheader(f"Results ({len(filtered_videos)} sermons)")
        
        if filtered_videos:
            # Create dataframe
            video_list_data = []
            for video in filtered_videos:
                try:
                    video_date = datetime.fromisoformat(video['date'].replace('Z', '+00:00'))
                    date_str = video_date.strftime('%Y-%m-%d')
                except:
                    date_str = video['date'][:10]
                
                speaker = video_speakers.get(video['id'], 'Unknown')
                
                # Use player URL format
                video_id = video['url'].split('/')[-1]
                player_url = f"https://player.vimeo.com/video/{video_id}"
                
                video_list_data.append({
                    'Date': date_str,
                    'Speaker': speaker,
                    'Title': video['title'],
                    'Duration': format_duration(video.get('duration', 0)),
                    'URL': player_url
                })
            
            df = pd.DataFrame(video_list_data)
            
            st.dataframe(
                df,
                column_config={
                    "URL": st.column_config.LinkColumn("Watch"),
                    "Date": st.column_config.TextColumn("Date", width="small"),
                    "Speaker": st.column_config.TextColumn("Speaker", width="medium"),
                    "Title": st.column_config.TextColumn("Title", width="large"),
                    "Duration": st.column_config.TextColumn("Duration", width="small")
                },
                hide_index=True,
                use_container_width=True,
                height=600
            )
        else:
            st.info("No videos match the selected filters")

    
    # TAB 3: BIBLE HEAT MAP
    with tab3:
        st.header("Bible Heat Map")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Get speakers from videos that have Bible references
            conn_temp = sqlite3.connect(DATABASE_PATH)
            c_temp = conn_temp.cursor()
            
            # Get video IDs that have Bible references
            c_temp.execute('SELECT DISTINCT video_id FROM bible_references')
            video_ids_with_refs = [row[0] for row in c_temp.fetchall()]
            conn_temp.close()
            
            # Load video data and extract speakers from those videos
            video_data_path = TRANSCRIPT_DIR / 'video_data.json'
            speakers = set()
            
            if video_data_path.exists():
                with open(video_data_path, 'r', encoding='utf-8') as f:
                    videos_data = json.load(f)
                
                for video in videos_data:
                    if video['id'] in video_ids_with_refs:
                        desc = video.get('description', '')
                        speaker = None
                        
                        if desc and 'Speaker:' in desc:
                            try:
                                start = desc.index('Speaker:') + len('Speaker:')
                                speaker = desc[start:].strip().split('\n')[0].strip()
                            except:
                                pass
                        elif desc and 'Presented by' in desc:
                            try:
                                start = desc.index('Presented by') + len('Presented by')
                                end = desc.index(' on ', start)
                                speaker = desc[start:end].strip()
                            except:
                                pass
                        elif desc and 'preaches' in desc.lower():
                            try:
                                speaker = desc.split('preaches')[0].strip()
                            except:
                                pass
                        
                        if speaker:
                            speakers.add(speaker)
            
            speaker_filter = st.selectbox(
                "Filter by Speaker",
                ["All Speakers"] + sorted(list(speakers)),
                key="bible_speaker_filter"
            )

        
        with col2:
            # Year filter
            if stats and stats['year_stats']:
                years = sorted(stats['year_stats'].keys(), reverse=True)
                year_filter = st.selectbox(
                    "Filter by Year",
                    ["All Years"] + years,
                    key="bible_year_filter"
                )
            else:
                year_filter = "All Years"
        
        with col3:
            # Testament filter
            testament_filter = st.selectbox(
                "Testament",
                ["Both", "Old Testament", "New Testament"],
                key="testament_filter"
            )
        
        # Query bible references with filters
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        
        # Build query based on filters
        query = '''
            SELECT br.book, COUNT(*) as count
            FROM bible_references br
            JOIN videos v ON br.video_id = v.video_id
            WHERE 1=1
        '''
        params = []
        
        # Apply year filter
        if year_filter != "All Years":
            query += " AND strftime('%Y', v.date_published) = ?"
            params.append(str(year_filter))
        
        # Apply speaker filter (need to join with video_data.json)
        # We'll filter in Python after getting results
        
        query += " GROUP BY br.book ORDER BY count DESC"
        
        c.execute(query, params)
        book_counts = c.fetchall()
        
        # Filter by speaker if needed (requires checking descriptions)
        if speaker_filter != "All Speakers":
            # Load video data
            video_data_path = TRANSCRIPT_DIR / 'video_data.json'
            if video_data_path.exists():
                with open(video_data_path, 'r', encoding='utf-8') as f:
                    videos_data = json.load(f)
                
                # Get video IDs for this speaker
                speaker_video_ids = set()
                for video in videos_data:
                    desc = video.get('description', '')
                    speaker = None
                    
                    if desc and 'Presented by' in desc:
                        try:
                            start = desc.index('Presented by') + len('Presented by')
                            end = desc.index(' on ', start)
                            speaker = desc[start:end].strip()
                        except:
                            pass
                    elif desc and 'Speaker:' in desc:
                        try:
                            start = desc.index('Speaker:') + len('Speaker:')
                            speaker = desc[start:].strip().split('\n')[0].strip()
                        except:
                            pass
                    
                    if speaker == speaker_filter:
                        speaker_video_ids.add(video['id'])
                
                # Re-query with speaker filter
                if speaker_video_ids:
                    placeholders = ','.join('?' * len(speaker_video_ids))
                    query = f'''
                        SELECT br.book, COUNT(*) as count
                        FROM bible_references br
                        WHERE br.video_id IN ({placeholders})
                    '''
                    if year_filter != "All Years":
                        query += '''
                            AND br.video_id IN (
                                SELECT video_id FROM videos 
                                WHERE strftime('%Y', date_published) = ?
                            )
                        '''
                        params = list(speaker_video_ids) + [str(year_filter)]
                    else:
                        params = list(speaker_video_ids)
                    
                    query += " GROUP BY br.book ORDER BY count DESC"
                    c.execute(query, params)
                    book_counts = c.fetchall()
        
        # Define book order and testament
        old_testament_books = [
            'Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy',
            'Joshua', 'Judges', 'Ruth', '1 Samuel', '2 Samuel',
            '1 Kings', '2 Kings', '1 Chronicles', '2 Chronicles',
            'Ezra', 'Nehemiah', 'Esther', 'Job', 'Psalms', 'Proverbs',
            'Ecclesiastes', 'Song of Solomon', 'Isaiah', 'Jeremiah',
            'Lamentations', 'Ezekiel', 'Daniel', 'Hosea', 'Joel',
            'Amos', 'Obadiah', 'Jonah', 'Micah', 'Nahum', 'Habakkuk',
            'Zephaniah', 'Haggai', 'Zechariah', 'Malachi'
        ]
        
        new_testament_books = [
            'Matthew', 'Mark', 'Luke', 'John', 'Acts', 'Romans',
            '1 Corinthians', '2 Corinthians', 'Galatians', 'Ephesians',
            'Philippians', 'Colossians', '1 Thessalonians', '2 Thessalonians',
            '1 Timothy', '2 Timothy', 'Titus', 'Philemon', 'Hebrews',
            'James', '1 Peter', '2 Peter', '1 John', '2 John', '3 John',
            'Jude', 'Revelation'
        ]
        
        # Filter by testament
        if testament_filter == "Old Testament":
            book_counts = [(b, c) for b, c in book_counts if b in old_testament_books]
        elif testament_filter == "New Testament":
            book_counts = [(b, c) for b, c in book_counts if b in new_testament_books]
        
        # Create book abbreviations
        book_abbrev = {
            'Genesis': 'Gen', 'Exodus': 'Ex', 'Leviticus': 'Lev', 'Numbers': 'Num',
            'Deuteronomy': 'Deut', 'Joshua': 'Josh', 'Judges': 'Judg', 'Ruth': 'Ruth',
            '1 Samuel': '1Sam', '2 Samuel': '2Sam', '1 Kings': '1Kgs', '2 Kings': '2Kgs',
            '1 Chronicles': '1Chr', '2 Chronicles': '2Chr', 'Ezra': 'Ezra',
            'Nehemiah': 'Neh', 'Esther': 'Est', 'Job': 'Job', 'Psalms': 'Ps',
            'Proverbs': 'Prov', 'Ecclesiastes': 'Eccl', 'Song of Solomon': 'Song',
            'Isaiah': 'Isa', 'Jeremiah': 'Jer', 'Lamentations': 'Lam',
            'Ezekiel': 'Ezek', 'Daniel': 'Dan', 'Hosea': 'Hos', 'Joel': 'Joel',
            'Amos': 'Amos', 'Obadiah': 'Obad', 'Jonah': 'Jonah', 'Micah': 'Mic',
            'Nahum': 'Nah', 'Habakkuk': 'Hab', 'Zephaniah': 'Zeph',
            'Haggai': 'Hag', 'Zechariah': 'Zech', 'Malachi': 'Mal',
            'Matthew': 'Matt', 'Mark': 'Mark', 'Luke': 'Luke', 'John': 'John',
            'Acts': 'Acts', 'Romans': 'Rom', '1 Corinthians': '1Cor',
            '2 Corinthians': '2Cor', 'Galatians': 'Gal', 'Ephesians': 'Eph',
            'Philippians': 'Phil', 'Colossians': 'Col', '1 Thessalonians': '1Thes',
            '2 Thessalonians': '2Thes', '1 Timothy': '1Tim', '2 Timothy': '2Tim',
            'Titus': 'Titus', 'Philemon': 'Phlm', 'Hebrews': 'Heb',
            'James': 'Jas', '1 Peter': '1Pet', '2 Peter': '2Pet',
            '1 John': '1Jn', '2 John': '2Jn', '3 John': '3Jn',
            'Jude': 'Jude', 'Revelation': 'Rev'
        }
        
        if book_counts:
            # Create heat map data
            book_dict = {book: count for book, count in book_counts}
            
            st.subheader("Biblical Coverage")
            
            # Prepare data for Plotly
            import plotly.graph_objects as go
            
            # Old Testament grid (3 rows)
            if testament_filter in ["Both", "Old Testament"]:
                st.markdown("**Old Testament**")
                
                ot_rows = [
                    old_testament_books[0:13],
                    old_testament_books[13:26],
                    old_testament_books[26:39]
                ]
                
                # Create matrix for heatmap
                z_values = []
                hover_text = []
                x_labels = []
                y_labels = ['Row 1', 'Row 2', 'Row 3']
                
                max_cols = max(len(row) for row in ot_rows)
                
                for row_idx, row in enumerate(ot_rows):
                    z_row = []
                    hover_row = []
                    
                    for book in row:
                        count = book_dict.get(book, 0)
                        z_row.append(count)
                        hover_row.append(f"{book}<br>{count} references")
                    
                    # Pad row if needed
                    while len(z_row) < max_cols:
                        z_row.append(None)
                        hover_row.append("")
                    
                    z_values.append(z_row)
                    hover_text.append(hover_row)
                
                # Get x labels from longest row
                x_labels = [book_abbrev.get(book, book[:4]) for book in ot_rows[0]]
                
                # Create heatmap
                fig = go.Figure(data=go.Heatmap(
                    z=z_values,
                    x=x_labels,
                    y=y_labels,
                    text=hover_text,
                    texttemplate="%{text}",
                    hovertemplate='%{text}<extra></extra>',
                    colorscale='Greens',  # White to green
                    showscale=True,
                    colorbar=dict(title="References")
                ))
                
                fig.update_layout(
                    height=300,
                    margin=dict(l=20, r=20, t=20, b=20),
                    xaxis=dict(side='top'),
                    yaxis=dict(showticklabels=False, autorange='reversed')  # Add autorange='reversed'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # New Testament grid
            if testament_filter in ["Both", "New Testament"]:
                st.markdown("**New Testament**")
                
                nt_rows = [
                    new_testament_books[0:11],
                    new_testament_books[11:22],
                    new_testament_books[22:27]
                ]
                
                z_values = []
                hover_text = []
                x_labels = []
                y_labels = ['Row 1', 'Row 2', 'Row 3']
                
                max_cols = max(len(row) for row in nt_rows)
                
                for row_idx, row in enumerate(nt_rows):
                    z_row = []
                    hover_row = []
                    
                    for book in row:
                        count = book_dict.get(book, 0)
                        z_row.append(count)
                        hover_row.append(f"{book}<br>{count} references")
                    
                    # Pad row
                    while len(z_row) < max_cols:
                        z_row.append(None)
                        hover_row.append("")
                    
                    z_values.append(z_row)
                    hover_text.append(hover_row)
                
                x_labels = [book_abbrev.get(book, book[:4]) for book in nt_rows[0]]
                
                fig = go.Figure(data=go.Heatmap(
                    z=z_values,
                    x=x_labels,
                    y=y_labels,
                    text=hover_text,
                    texttemplate="%{text}",
                    hovertemplate='%{text}<extra></extra>',
                    colorscale='Greens',
                    showscale=True,
                    colorbar=dict(title="References")
                ))
                
                fig.update_layout(
                    height=300,
                    margin=dict(l=20, r=20, t=20, b=20),
                    xaxis=dict(side='top'),
                    yaxis=dict(showticklabels=False, autorange='reversed')  # Add autorange='reversed'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Drill-down section
            st.markdown("---")
            st.subheader("Drill Down by Book")
            
            # Select a book to see details
            books_with_refs = [book for book, count in book_counts]
            selected_book = st.selectbox("Select a book to see chapter/verse details:", [""] + books_with_refs)
            
            if selected_book:
                # Get chapter/verse breakdown
                c.execute('''
                    SELECT chapter, verse_start, verse_end, COUNT(*) as count
                    FROM bible_references
                    WHERE book = ?
                    GROUP BY chapter, verse_start, verse_end
                    ORDER BY chapter, verse_start
                ''', (selected_book,))
                
                chapter_data = c.fetchall()
                
                if chapter_data:
                    st.markdown(f"**{selected_book} - Chapter & Verse References**")
                    
                    # Group by chapter
                    chapters = defaultdict(list)
                    for chapter, verse_start, verse_end, count in chapter_data:
                        if verse_start:
                            if verse_end and verse_end != verse_start:
                                verse_ref = f"{verse_start}-{verse_end}"
                            else:
                                verse_ref = str(verse_start)
                        else:
                            verse_ref = "Whole chapter"
                        
                        chapters[chapter].append((verse_ref, count))
                    
                    # Display by chapter (handle None for standalone mentions)
                    sorted_chapters = sorted([c for c in chapters.keys() if c is not None])
                    if None in chapters:
                        sorted_chapters.append(None)
                    
                    for chapter in sorted_chapters:
                        if chapter is None:
                            chapter_label = "General mentions (no specific chapter)"
                        else:
                            chapter_label = f"Chapter {chapter}"
                        
                        with st.expander(f"{chapter_label} ({sum(c for _, c in chapters[chapter])} references)"):
                            for verse_ref, count in chapters[chapter]:
                                st.write(f"  Verse {verse_ref}: {count} mentions")
                            
                            # Show sermons that reference this chapter
                            c.execute('''
                                SELECT DISTINCT v.title, v.url, br.start_time
                                FROM bible_references br
                                JOIN videos v ON br.video_id = v.video_id
                                WHERE br.book = ? AND br.chapter = ?
                                ORDER BY v.date_published DESC
                                LIMIT 10
                            ''', (selected_book, chapter))
                            
                            sermons = c.fetchall()
                            if sermons:
                                st.markdown("**Sermons referencing this chapter:**")
                                for title, url, start_time in sermons:
                                    timestamp_url = f"https://player.vimeo.com/video/{video_id}#t={int(start_time)}s"
                                    st.markdown(f"- [{title}]({timestamp_url})")
                
                        
        else:
            st.info("No Bible references found in database. Run extract_bible_references.py first.")
        
        conn.close()
        
        
                
        # Add white space at the bottom
        st.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)

    
    # TAB 4: SPEAKER STATS
    with tab4:
        st.header("Speaker Statistics")
        
        # Load video data from database instead of JSON file
        conn_videos = sqlite3.connect(DATABASE_PATH)
        c_videos = conn_videos.cursor()
        
        c_videos.execute('SELECT video_id, title, duration, url, date_published FROM videos')
        video_rows = c_videos.fetchall()
        
        # Convert to same format as JSON
        all_videos = []
        for video_id, title, duration, url, date_published in video_rows:
            all_videos.append({
                'id': video_id,
                'title': title,
                'duration': duration,
                'url': url,
                'date': date_published,
                'description': ''  # We'll get this from another source if needed
            })
        
        conn_videos.close()
        
        # Build speaker data
        speaker_videos = defaultdict(list)
        for video in all_videos:
            desc = video.get('description', '')
            speaker = "Unknown"
            
            if desc and 'Speaker:' in desc:
                try:
                    start = desc.index('Speaker:') + len('Speaker:')
                    speaker = desc[start:].strip().split('\n')[0].strip()
                except:
                    pass
            elif desc and 'Presented by' in desc:
                try:
                    start = desc.index('Presented by') + len('Presented by')
                    end = desc.index(' on ', start)
                    speaker = desc[start:end].strip()
                except:
                    pass
            elif desc and 'preaches' in desc.lower():
                try:
                    speaker = desc.split('preaches')[0].strip()
                except:
                    pass
            
            # Only include videos with transcripts
            vtt_file = TRANSCRIPT_DIR / f"{video['id']}_en-x-autogen.vtt"
            if vtt_file.exists():
                speaker_videos[speaker].append(video)
        
        # Remove "Unknown" if no videos
        if not speaker_videos.get("Unknown"):
            speaker_videos.pop("Unknown", None)
        
        # Speaker selector
        speakers = sorted([s for s in speaker_videos.keys() if s != "Unknown"])
        selected_speaker = st.selectbox(
            "Select a speaker:",
            speakers,
            key="speaker_stats_select"
        )
        
        if selected_speaker:
            videos = speaker_videos[selected_speaker]
            video_ids = [v['id'] for v in videos]
            
            conn = sqlite3.connect(DATABASE_PATH)
            c = conn.cursor()
            
            # Overview stats
            st.subheader(f"{selected_speaker} - Overview")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Sermons", len(videos))
            
            with col2:
                total_duration = sum(v.get('duration', 0) for v in videos)
                hours = int(total_duration // 3600)
                st.metric("Total Teaching Time", f"{hours}h")
            
            with col3:
                # Count Bible references
                placeholders = ','.join('?' * len(video_ids))
                c.execute(f'SELECT COUNT(*) FROM bible_references WHERE video_id IN ({placeholders})', video_ids)
                bible_ref_count = c.fetchone()[0]
                st.metric("Bible References", bible_ref_count)
            
            with col4:
                # Get date range
                dates = []
                for v in videos:
                    try:
                        dates.append(datetime.fromisoformat(v['date'].replace('Z', '+00:00')))
                    except:
                        pass
                if dates:
                    years_active = max(dates).year - min(dates).year + 1
                    st.metric("Years Active", years_active)
            
            # Most Referenced Books
            st.markdown("---")
            st.subheader("Most Referenced Bible Books")
            
            c.execute(f'''
                SELECT book, COUNT(*) as count
                FROM bible_references
                WHERE video_id IN ({placeholders})
                GROUP BY book
                ORDER BY count DESC
                LIMIT 10
            ''', video_ids)
            
            top_books = c.fetchall()
            
            if top_books:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Bar chart
                    import plotly.express as px
                    df_books = pd.DataFrame(top_books, columns=['Book', 'References'])
                    fig = px.bar(df_books, x='References', y='Book', orientation='h',
                                color='References', color_continuous_scale='Greens')
                    fig.update_layout(height=400, showlegend=False, yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown("**Top 10 Books:**")
                    for book, count in top_books:
                        st.write(f"{book}: {count}")
            
            # Theological Topics
            st.markdown("---")
            st.subheader("Theological Topics Covered")
            
            c.execute(f'''
                SELECT topic, COUNT(*) as count
                FROM theological_topics
                WHERE video_id IN ({placeholders})
                GROUP BY topic
                ORDER BY count DESC
            ''', video_ids)
            
            topics = c.fetchall()
            
            if topics:
                # Create word cloud style display
                topic_data = []
                for topic, count in topics:
                    topic_data.append({'Topic': topic, 'Mentions': count})
                
                df_topics = pd.DataFrame(topic_data)
                
                # Bar chart
                fig = px.bar(df_topics, x='Mentions', y='Topic', orientation='h',
                            color='Mentions', color_continuous_scale='Blues')
                fig.update_layout(height=600, showlegend=False, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No theological topics found. Run extract_theological_topics.py first.")
            
            # Most Referenced Verses
            st.markdown("---")
            st.subheader("Most Referenced Verses")
            
            c.execute(f'''
                SELECT book, chapter, verse_start, verse_end, COUNT(*) as count
                FROM bible_references
                WHERE video_id IN ({placeholders})
                AND verse_start IS NOT NULL
                GROUP BY book, chapter, verse_start, verse_end
                ORDER BY count DESC
                LIMIT 15
            ''', video_ids)
            
            top_verses = c.fetchall()
            
            if top_verses:
                verse_list = []
                for book, chapter, verse_start, verse_end, count in top_verses:
                    if verse_end and verse_end != verse_start:
                        verse_ref = f"{book} {chapter}:{verse_start}-{verse_end}"
                    else:
                        verse_ref = f"{book} {chapter}:{verse_start}"
                    
                    verse_list.append({'Reference': verse_ref, 'Mentions': count})
                
                df_verses = pd.DataFrame(verse_list)
                st.dataframe(df_verses, hide_index=True, use_container_width=True)
            
            # Bible Coverage
            st.markdown("---")
            st.subheader("Bible Coverage")
            
            placeholders = ','.join('?' * len(video_ids))
            c.execute(f'''
                SELECT book, COUNT(*) as count
                FROM bible_references
                WHERE video_id IN ({placeholders})
                GROUP BY book
                ORDER BY count DESC
            ''', video_ids)
            
            book_coverage = c.fetchall()
            
            if book_coverage:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Horizontal bar chart
                    import plotly.express as px
                    df_books = pd.DataFrame(book_coverage, columns=['Book', 'References'])
                    fig = px.bar(df_books.head(15), x='References', y='Book', orientation='h',
                                color='References', color_continuous_scale='Greens',
                                title=f"Top 15 Books Referenced")
                    fig.update_layout(height=500, showlegend=False, yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown("**Coverage Stats:**")
                    total_books = len(book_coverage)
                    st.metric("Books Referenced", f"{total_books}/66")
                    
                    ot_books = len([b for b, c in book_coverage if b in old_testament_books])
                    nt_books = len([b for b, c in book_coverage if b in new_testament_books])
                    st.write(f"OT: {ot_books}/39")
                    st.write(f"NT: {nt_books}/27")
            
            # Theological Topics
            st.markdown("---")
            st.subheader("Theological Emphasis")
            
            c.execute(f'''
                SELECT topic, COUNT(*) as count
                FROM theological_topics
                WHERE video_id IN ({placeholders})
                GROUP BY topic
                ORDER BY count DESC
                LIMIT 15
            ''', video_ids)
            
            topic_coverage = c.fetchall()
            
            if topic_coverage:
                df_topics = pd.DataFrame(topic_coverage, columns=['Topic', 'Mentions'])
                fig = px.bar(df_topics, x='Mentions', y='Topic', orientation='h',
                            color='Mentions', color_continuous_scale='Blues',
                            title=f"Top 15 Theological Topics")
                fig.update_layout(height=500, showlegend=False, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            
            # Recent Sermons
            st.markdown("---")
            st.subheader("Recent Sermons")
            
            recent_videos = sorted(videos, key=lambda x: x['date'], reverse=True)[:10]
            
            for video in recent_videos:
                try:
                    video_date = datetime.fromisoformat(video['date'].replace('Z', '+00:00'))
                    date_str = video_date.strftime('%Y-%m-%d')
                except:
                    date_str = video['date'][:10]
                
                # Use player URL format
                video_id = video['url'].split('/')[-1]
                player_url = f"https://player.vimeo.com/video/{video_id}"
                
                st.markdown(f"**{date_str}** - [{video['title']}]({player_url})")
            
            conn.close()
        
        else:
            st.info("Select a speaker to see their statistics")



if __name__ == "__main__":
    # Check if database exists
    if not DATABASE_PATH.exists():
        st.error("Database not found!")
        st.info("""
        Please run the following commands first:
        1. `python scripts/download_videos.py` - Download videos and transcripts
        2. `python scripts/update_database.py` - Process transcripts into database
        
        Or simply run: `python update_and_run.py`
        """)
    else:
        main()
