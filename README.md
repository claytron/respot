I don't use Spotify as my main music player anymore, but I still want to be a part of the year in review.
So this script does the following:

- Reads the last _n_ days from last.fm
- Populates a playlist in Spotify
- Plays the playlist
- Profit

Then you get credit for all those tracks you played elsewhere.

## Setup

Clone this repo and run the following:

```sh
$ pip install -r requirements.txt
```

Create a playlist in Sptify that will be cleared and populated when the script runs.

The script requires the following environment variables:

```sh
# For spotify playlist creation and playing via spotipy
# NOTE: these are what spotipy expects for auth
SPOTIPY_CLIENT_ID
SPOTIPY_CLIENT_SECRET
SPOTIPY_REDIRECT_URI

# To get the tracks from last.fm via pylast
# NOTE: these are set via the respot.py script, not pylast
PYLAST_API_KEY
PYLAST_API_SECRET
```

Then you'll need to run this via cron or something similar.
I use the 1password `op run` via a service user to populate the env.

Then you can run the script once you know the playlist and device id:

```sh
$ python respot.py playlist_id device_id
```
