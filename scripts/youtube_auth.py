"""One-time: turn a Google OAuth client into a refresh token for YT_REFRESH_TOKEN.

  1. Google Cloud Console -> enable "YouTube Data API v3"
  2. Credentials -> OAuth client ID -> Desktop app -> download client_secret.json
  3. python scripts/youtube_auth.py client_secret.json
  4. Paste the printed token into the YT_REFRESH_TOKEN secret (plus YT_CLIENT_ID / YT_CLIENT_SECRET)
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__); sys.exit(1)
    flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    secrets = json.load(open(sys.argv[1]))["installed"]
    print("\nYT_CLIENT_ID=" + secrets["client_id"])
    print("YT_CLIENT_SECRET=" + secrets["client_secret"])
    print("YT_REFRESH_TOKEN=" + creds.refresh_token)
