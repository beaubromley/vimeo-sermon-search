import time
from datetime import datetime

def format_duration(seconds):
    """Convert seconds to HH:MM:SS format"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{remaining_seconds:02d}"
    else:
        return f"{minutes}:{remaining_seconds:02d}"

def timestamp_to_seconds(timestamp):
    """Convert HH:MM:SS timestamp to seconds"""
    h, m, s = timestamp.split(':')
    return float(h) * 3600 + float(m) * 60 + float(s)

def format_filename(base_name, extension):
    """Create filename with timestamp"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{base_name}_{timestamp}.{extension}"

def rate_limited(func):
    """Decorator for rate limiting API calls"""
    last_called = {}
    
    def wrapper(*args, **kwargs):
        from .config import RATE_LIMIT_WAIT
        now = time.time()
        
        if func not in last_called or now - last_called[func] >= RATE_LIMIT_WAIT:
            result = func(*args, **kwargs)
            last_called[func] = now
            return result
        else:
            wait_time = RATE_LIMIT_WAIT - (now - last_called[func])
            time.sleep(wait_time)
            return func(*args, **kwargs)
            
    return wrapper
