# youtube-music-importer

Claude generated script to move youtube playlists from one account to another. I recently migrated to a new youtube account and wanted to migrate my playlists. There was an easy way to export data from Google, but no easy way to import it, hence this script.

### Steps

* Export youtube data from [Google takeout](https://takeout.google.com/).
* Once downloaded, copy the `*csv` files from the downloaded `Takeout/YoutTube and YouTube Music` folder to `imports` folder in this repo.
* Download a client secret key from `https://console.cloud.google.com` under a new project or existing one from `https://console.cloud.google.com/apis/credentials` for the new account.
    * Store the key under `client_secret.json` in this folder.
    * Add your email under 'Test users' in `https://console.cloud.google.com/auth/audience` once the project is created to enable access.
* Run script with `uv run main.py`
    * This should first open up a scary oauth screen saying your app isn't authorized by Google.
    * Once authorized, you
