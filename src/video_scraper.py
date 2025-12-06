import sys
from pathlib import Path
import vimeo
import json
import time
from datetime import datetime
import requests
import os

class VimeoChannelScraper:
    def __init__(self):
        self.client = vimeo.VimeoClient(
            token='9d8276ed72b3a9fbc5cbfefdbaab2095',  # Replace with your actual credentials
            key='f58d3b47076fb4115d9ec6d59f014c4f2f243ccb',
            secret='dr/Y4aXu83Paj6k95bt9fGSDp7+VlkZjb95Hdi3sRLLPQ0Xr8ZBxl3GpKSohkUHmZy//Wqv/RVdKoxulCXEYblKj9tf2s+RojG6Yx4tdfmgNSSFrqxY19npA27HKnnpp'
        )
        self.rate_limit_wait = 2  # Wait 2 seconds between requests
        self.min_duration = 600  # 10 minutes in seconds

    def make_request(self, url):
        """Make a rate-limited request with improved error handling"""
        max_retries = 3
        current_retry = 0
        
        while current_retry < max_retries:
            try:
                print(f"Making request to: {url}")
                response = self.client.get(url)
                
                if response.status_code == 429:  # Too Many Requests
                    wait_time = 65  # Wait 65 seconds if rate limited
                    print(f"\nRate limit hit. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                    
                if response.status_code != 200:
                    print(f"Error: Received status code {response.status_code}")
                    print(f"Response: {response.text}")
                    current_retry += 1
                    if current_retry < max_retries:
                        wait_time = 30 * (current_retry + 1)
                        print(f"Retrying in {wait_time} seconds... (Attempt {current_retry + 1} of {max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        print("Max retries reached.")
                        return None
                
                # Success - got a 200 response
                time.sleep(self.rate_limit_wait)  # Wait between requests
                return response
                
            except Exception as e:
                print(f"Request error: {str(e)}")
                current_retry += 1
                if current_retry < max_retries:
                    wait_time = 30 * (current_retry + 1)
                    print(f"Retrying in {wait_time} seconds... (Attempt {current_retry + 1} of {max_retries})")
                    time.sleep(wait_time)
                else:
                    print("Max retries reached.")
                    return None
        
        return None

    def get_channel_videos(self, channel_name):
        try:
            print(f"Starting to fetch videos longer than {self.min_duration/60} minutes...")
            
            # First get the channel/user information
            response = self.make_request(f'/users/{channel_name}/videos')
            
            if not response:
                print("Failed to get initial response.")
                return None
            
            videos = []
            data = response.json()
            
            # Process first page
            new_videos = self.process_video_data(data['data'])
            long_videos = [v for v in new_videos if v['duration'] >= self.min_duration]
            videos.extend(long_videos)
            print(f"Fetched first page: {len(long_videos)} long videos")
            
            # Handle pagination
            page = 1
            while 'next' in data['paging']:
                page += 1
                print(f"\nFetching page {page}... (Found {len(videos)} long videos so far)")
                response = self.make_request(data['paging']['next'])
                
                if not response:
                    print(f"Failed to get page {page}")
                    break
                
                data = response.json()
                new_videos = self.process_video_data(data['data'])
                long_videos = [v for v in new_videos if v['duration'] >= self.min_duration]
                videos.extend(long_videos)
                print(f"Added {len(long_videos)} long videos from page {page}")
            
            return videos
            
        except Exception as e:
            print(f"Error fetching videos: {e}")
            return None

    def process_video_data(self, video_list):
        processed_videos = []
        for video in video_list:
            processed_videos.append({
                'id': video['uri'].split('/')[-1],
                'title': video['name'],
                'url': video['link'],
                'date': video['release_time'],
                'duration': video['duration'],
                'description': video['description'],
                'privacy': video['privacy']['view']
            })
        return processed_videos

    def download_transcript(self, video_id):
        """Download transcript for a video"""
        try:
            print(f"Fetching transcripts for video {video_id}")
            response = self.make_request(f'/videos/{video_id}/texttracks')
            
            if not response:
                print("Failed to get transcript information")
                return None
                
            tracks = response.json()['data']
            
            if not tracks:
                print("No transcripts available for this video")
                return None
                
            for track in tracks:
                print(f"Found transcript in language: {track['language']}")
                
                # Download VTT file
                vtt_response = requests.get(track['link'])
                if vtt_response.status_code == 200:
                    # Create transcripts directory if it doesn't exist
                    os.makedirs('data/transcripts', exist_ok=True)
                    
                    filename = f"data/transcripts/{video_id}_{track['language']}.vtt"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(vtt_response.text)
                    print(f"Saved transcript to: {filename}")
                    return filename
                else:
                    print(f"Failed to download transcript. Status code: {vtt_response.status_code}")
                    
        except Exception as e:
            print(f"Error downloading transcript: {e}")
        return None

def format_duration(seconds):
    """Convert seconds to HH:MM:SS format"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{remaining_seconds:02d}"
    else:
        return f"{minutes}:{remaining_seconds:02d}"
