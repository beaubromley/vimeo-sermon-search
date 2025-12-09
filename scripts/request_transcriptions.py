import vimeo
import sys

# --- Configuration ---
# Replace with your actual Vimeo API credentials
ACCESS_TOKEN = "9d8276ed72b3a9fbc5cbfefdbaab2095"
CLIENT_ID = "f58d3b47076fb4115d9ec6d59f014c4f2f243ccb"    # Also known as Client Key
CLIENT_SECRET = "dr/Y4aXu83Paj6k95bt9fGSDp7+VlkZjb95Hdi3sRLLPQ0Xr8ZBxl3GpKSohkUHmZy//Wqv/RVdKoxulCXEYblKj9tf2s+RojG6Yx4tdfmgNSSFrqxY19npA27HKnnpp"

# --- Video and Language ---
# Replace with the ID of the video you want to caption
VIDEO_ID_TO_CAPTION = "99530525"
# Specify the language of the video for caption generation (e.g., "en" for English, "es" for Spanish)
LANGUAGE_CODE = "en"
# --- End Configuration ---


def request_automatic_captions(video_id, language_code, client):
    """
    Requests Vimeo to generate automatic captions for a specific video.

    Args:
        video_id (str): The ID of the video.
        language_code (str): The BCP 47 language code for the captions.
        client (vimeo.VimeoClient): An initialized Vimeo API client.
    """
    endpoint = f'/videos/{video_id}/texttracks'
    
    data = {
        'type': 'automatic',
        'language': language_code,
        # 'active': True # Optional: attempt to make active immediately.
                         # Vimeo might ignore this or it might be a separate step.
    }

    print(f"Requesting automatic captions in '{language_code}' for video ID: {video_id}...")

    try:
        response = client.post(endpoint, data=data)

        # A successful request usually returns a 201 Created or 202 Accepted status code
        if response and response.status_code in [201, 202]: # 201: Created, 202: Accepted for processing
            print(f"Successfully requested automatic captions. Vimeo is now processing.")
            try:
                response_data = response.json()
                print(f"Response details: {response_data}")
                if 'uri' in response_data:
                    print(f"You can check the status of this text track later at: {response_data['uri']}")
            except Exception as e:
                print(f"Could not parse JSON response, but request seemed successful. Raw response: {response.text[:200]}...")
            return True
        elif response:
            print(f"Failed to request automatic captions. Status: {response.status_code}")
            try:
                print(f"Error details: {response.json()}")
            except Exception:
                print(f"Raw error response: {response.text}")
            return False
        else:
            print("Failed to request automatic captions. No response from server.")
            return False

    except vimeo.exceptions.VideoNotFoundError:
        print(f"Error: Video with ID {video_id} not found.")
        return False
    except vimeo.exceptions.APIRateLimitExceededError:
        print("Error: API rate limit exceeded. Please wait and try again.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while requesting automatic captions for video {video_id}: {e}")
        return False


if __name__ == "__main__":
    if (ACCESS_TOKEN == "YOUR_VIMEO_ACCESS_TOKEN" or
        CLIENT_ID == "YOUR_VIMEO_CLIENT_ID" or
        CLIENT_SECRET == "YOUR_VIMEO_CLIENT_SECRET"):
        print("ERROR: Please update your Vimeo API credentials in the script.")
        sys.exit(1)

    if VIDEO_ID_TO_CAPTION == "YOUR_VIDEO_ID_HERE":
        print("ERROR: Please set the VIDEO_ID_TO_CAPTION variable in the script.")
        sys.exit(1)

    # Initialize the Vimeo client
    try:
        vimeo_client = vimeo.VimeoClient(
            token=ACCESS_TOKEN,
            key=CLIENT_ID,
            secret=CLIENT_SECRET
        )
        print("Vimeo client initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Vimeo client: {e}")
        sys.exit(1)

    # Request captions
    success = request_automatic_captions(VIDEO_ID_TO_CAPTION, LANGUAGE_CODE, vimeo_client)

    if success:
        print(f"\nAutomatic caption request for video {VIDEO_ID_TO_CAPTION} was submitted.")
        print("It may take some time for Vimeo to process and generate the captions.")
        print("You can check the video's settings on Vimeo or use the API to see the status of the text track.")
    else:
        print(f"\nFailed to submit automatic caption request for video {VIDEO_ID_TO_CAPTION}.")
    
    print("\nScript finished.")
