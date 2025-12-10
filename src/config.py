# Configuration settings for the project

# Vimeo API credentials
VIMEO_CREDENTIALS = {
    'ACCESS_TOKEN': '###',
    'CLIENT_ID': '###',
    'CLIENT_SECRET': '###'
}

# File paths
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
TRANSCRIPT_DIR = DATA_DIR / 'transcripts'
DATABASE_DIR = DATA_DIR / 'database'
DATABASE_PATH = DATABASE_DIR / 'transcripts.db'

# Ensure directories exist
TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# Video settings
MIN_VIDEO_DURATION = 600  # 10 minutes in seconds

# API settings
RATE_LIMIT_WAIT = 2  # seconds between requests
RATE_LIMIT_EXCEEDED_WAIT = 65  # seconds to wait when rate limit hit
