# streamlit_app.py
import streamlit as st
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.transcript_manager import TranscriptManager
from src.config import TRANSCRIPT_DIR, DATABASE_PATH
import json
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
import os
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Vimeo Transcript Search",
    page_icon="🎥",
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
    
    data = []
    for result in results:
        match_type = result.get('match_type', 'transcript')
        
        if match_type == 'title':
            data.append({
                'Type': 'Title',
                'Video Title': result['title'],
                'Timestamp': '00:00:00',
                'Match': result['match'],
                'URL': result['url']
            })
        else:
            data.append({
                'Type': 'Transcript',
                'Video Title': result['title'],
                'Timestamp': result['timestamp'],
                'Match': result['match'][:150] + '...' if len(result['match']) > 150 else result['match'],
                'URL': result['url']
            })
    
    return pd.DataFrame(data)

def main():
    # Compact header
    st.markdown('<p class="main-header">Vimeo Transcript Search</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Search through video transcripts and titles from the Henderson Hills channel</p>', unsafe_allow_html=True)
    
    # Load stats
    stats = load_video_stats()
    
    # Sidebar
    with st.sidebar:
        st.header("Statistics")
        
        if stats:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Videos", stats['total_videos'])
                st.metric("Transcripts", stats['transcripts_available'])
            with col2:
                st.metric("Processed", stats['db_processed'])
                st.metric("Segments", f"{stats['total_segments']:,}")
            
            st.markdown("---")
            st.subheader("Videos by Year")
            
            # Show year breakdown with transcript indicators
            for year in sorted(stats['year_stats'].keys(), reverse=True):
                year_data = stats['year_stats'][year]
                total = year_data['total']
                with_transcripts = year_data['with_transcripts']
                percentage = (with_transcripts / total * 100) if total > 0 else 0
                
                # Color code by percentage: green >= 90%, yellow 1-89%, gray 0%
                if percentage >= 90:
                    transcript_class = "has-transcript-full"
                elif percentage > 0:
                    transcript_class = "has-transcript-partial"
                else:
                    transcript_class = "no-transcript"
                
                st.markdown(f"""
                <div class="year-section">
                    <strong>{year}:</strong> {total} videos<br>
                    <span class="{transcript_class}">{with_transcripts} with transcripts ({percentage:.0f}%)</span>
                </div>
                """, unsafe_allow_html=True)
            
            # Show recent videos with transcript status
            st.markdown("---")
            st.subheader("Recent Videos")
            
            if stats['videos']:
                recent_videos = sorted(stats['videos'], key=lambda x: x['date'], reverse=True)[:10]
                for video in recent_videos:
                    has_transcript = video['id'] in stats['transcript_video_ids']
                    date_str = video['date'][:10]
                    
                    if has_transcript:
                        st.markdown(f"""
                        <div style="margin-bottom: 0.5rem;">
                            <span class="has-transcript-full">YES</span> <small>{date_str}</small><br>
                            <span style="font-size: 0.9rem;">{video['title'][:50]}...</span>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="margin-bottom: 0.5rem;">
                            <span class="no-transcript">NO</span> <small>{date_str}</small><br>
                            <span class="no-transcript" style="font-size: 0.9rem;">{video['title'][:50]}...</span>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.warning("No video data available. Run download_videos.py first.")
        
        st.markdown("---")
        st.subheader("About")
        st.info("""
        This tool searches through video transcripts and titles from the Vimeo channel.
        
        **Features:**
        - Search video titles
        - Search transcript content
        - Direct links to timestamps
        - Shows transcript availability
        - Filter by date range
        """)
        
        st.markdown("---")
        if st.button("Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        
    # Search input with on_change callback for dynamic search
    search_query = st.text_input(
        "Enter search terms:",
        placeholder="e.g., 'Jesus', 'sanctification', 'salvation', 'First Samuel', 'Psalm 51', then press enter.",
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
    
    # Check if search should be triggered - ALWAYS search if query exists and changed
    should_search = False
    if search_query:
        # Search if query changed OR dates changed OR this is first time with this query
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
            # Summary - more compact
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
                tab1, tab2, tab3 = st.tabs(["All Results", "Title Matches", "Transcript Matches"])
                
                with tab1:
                    df = results_to_dataframe(results, 'all')
                    if df is not None:
                        st.dataframe(
                            df,
                            column_config={
                                "URL": st.column_config.LinkColumn("Watch Video"),
                                "Type": st.column_config.TextColumn("Type", width="small"),
                                "Video Title": st.column_config.TextColumn("Video Title", width="medium"),
                                "Timestamp": st.column_config.TextColumn("Time", width="small"),
                                "Match": st.column_config.TextColumn("Match", width="large")
                            },
                            hide_index=True,
                            use_container_width=True,
                            height=600  # Fixed height for more rows visible
                        )
                
                with tab2:
                    df = results_to_dataframe(results, 'title')
                    if df is not None:
                        st.dataframe(
                            df,
                            column_config={
                                "URL": st.column_config.LinkColumn("Watch Video"),
                                "Type": st.column_config.TextColumn("Type", width="small"),
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
                
                with tab3:
                    df = results_to_dataframe(results, 'transcript')
                    if df is not None:
                        st.dataframe(
                            df,
                            column_config={
                                "URL": st.column_config.LinkColumn("Watch Video"),
                                "Type": st.column_config.TextColumn("Type", width="small"),
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
