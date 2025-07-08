# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "google-auth",
#   "google-auth-oauthlib",
#   "google-api-python-client"
# ]
# ///
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import csv
import glob
from typing import Optional, Dict, List

SCOPES = ["https://www.googleapis.com/auth/youtube"]

def youtube_client() -> "googleapiclient.discovery.Resource":
    creds: Optional[Credentials] = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                creds = None

        if not creds:
            if not os.path.exists("client_secret.json"):
                raise FileNotFoundError("client_secret.json not found. Please download it from Google Cloud Console.")

            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())

    return build("youtube", "v3", credentials=creds, cache_discovery=False)

def get_existing_playlists(youtube) -> Dict[str, str]:
    """Get existing playlists and return a dict of title -> playlist_id"""
    playlists = {}
    try:
        request = youtube.playlists().list(
            part="snippet",
            mine=True,
            maxResults=50
        )
        response = request.execute()

        for playlist in response.get('items', []):
            title = playlist['snippet']['title']
            playlist_id = playlist['id']
            playlists[title] = playlist_id

    except Exception as e:
        print(f"Error fetching existing playlists: {e}")

    return playlists

def create_playlist(youtube, title: str, description: str = "") -> Optional[str]:
    """Create a new playlist and return its ID"""
    try:
        request = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description
                },
                "status": {
                    "privacyStatus": "private"
                }
            }
        )
        response = request.execute()
        playlist_id = response['id']
        print(f"Created playlist: {title} [ID: {playlist_id}]")
        return playlist_id
    except Exception as e:
        print(f"Error creating playlist '{title}': {e}")
        return None

def get_existing_playlist_items(youtube, playlist_id: str) -> set:
    """Get existing video IDs in a playlist"""
    video_ids = set()
    try:
        next_page_token = None
        while True:
            request = youtube.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response.get('items', []):
                video_id = item['snippet']['resourceId']['videoId']
                video_ids.add(video_id)

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

    except Exception as e:
        print(f"Error fetching playlist items for {playlist_id}: {e}")

    return video_ids

def add_video_to_playlist(youtube, playlist_id: str, video_id: str) -> bool:
    """Add a video to a playlist"""
    try:
        request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        )
        request.execute()
        return True
    except Exception as e:
        print(f"Error adding video {video_id} to playlist: {e}")
        return False

def read_video_ids_from_csv(file_path: str) -> List[str]:
    """Read video IDs from a CSV file"""
    video_ids = []
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                video_id = row.get('Video ID', '').strip()
                if video_id:
                    video_ids.append(video_id)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return video_ids

def process_imports_folder(youtube):
    """Process all playlist files in the imports folder"""
    imports_path = "imports"

    if not os.path.exists(imports_path):
        print(f"Imports folder '{imports_path}' not found.")
        return

    # Get existing playlists
    existing_playlists = get_existing_playlists(youtube)
    print(f"Found {len(existing_playlists)} existing playlists")

    # Process each CSV file (excluding playlists.csv)
    csv_files = glob.glob(os.path.join(imports_path, "*-videos.csv"))

    for csv_file in csv_files:
        # Extract playlist name from filename
        filename = os.path.basename(csv_file)
        playlist_name = filename.replace("-videos.csv", "")

        print(f"\nProcessing: {playlist_name}")

        # Read video IDs from CSV
        video_ids = read_video_ids_from_csv(csv_file)
        print(f"Found {len(video_ids)} videos in {filename}")

        if not video_ids:
            print(f"No videos found in {filename}, skipping...")
            continue

        # Get or create playlist
        playlist_id = existing_playlists.get(playlist_name)
        if not playlist_id:
            playlist_id = create_playlist(youtube, playlist_name)
            if playlist_id:
                existing_playlists[playlist_name] = playlist_id
        else:
            print(f"Using existing playlist: {playlist_name} [ID: {playlist_id}]")

        if not playlist_id:
            print(f"Failed to get/create playlist for {playlist_name}")
            continue

        # Get existing videos in playlist
        existing_video_ids = get_existing_playlist_items(youtube, playlist_id)
        print(f"Playlist already contains {len(existing_video_ids)} videos")

        # Filter out videos that already exist in the playlist
        videos_to_add = [vid for vid in video_ids if vid not in existing_video_ids]

        if not videos_to_add:
            print(f"All videos already exist in {playlist_name}")
            continue

        print(f"Adding {len(videos_to_add)} new videos to {playlist_name}")

        # Add videos to playlist
        added_count = 0
        for video_id in videos_to_add:
            if add_video_to_playlist(youtube, playlist_id, video_id):
                added_count += 1

        print(f"Successfully added {added_count}/{len(videos_to_add)} new videos to {playlist_name}")

def main():
    try:
        youtube = youtube_client()
        print("OAuth authentication successful!")
        process_imports_folder(youtube)
    except Exception as e:
        print(f"Authentication failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure client_secret.json is in the current directory")
        print("2. Ensure you've enabled YouTube Data API v3 in Google Cloud Console")
        print("3. Check that your OAuth consent screen is configured")


if __name__ == "__main__":
    main()
