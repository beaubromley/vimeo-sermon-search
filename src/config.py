# Configuration settings for the project

# Vimeo API credentials
VIMEO_CREDENTIALS = {
    'ACCESS_TOKEN': '9d8276ed72b3a9fbc5cbfefdbaab2095',
    'CLIENT_ID': 'f58d3b47076fb4115d9ec6d59f014c4f2f243ccb',
    'CLIENT_SECRET': 'dr/Y4aXu83Paj6k95bt9fGSDp7+VlkZjb95Hdi3sRLLPQ0Xr8ZBxl3GpKSohkUHmZy//Wqv/RVdKoxulCXEYblKj9tf2s+RojG6Yx4tdfmgNSSFrqxY19npA27HKnnpp'
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
