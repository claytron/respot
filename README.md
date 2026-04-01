I don't use Spotify or Tidal as my main music player anymore, but I still want to be a part of the year in review.
So this script does the following:

- Reads the last _n_ days from last.fm
- Populates a playlist in Spotify and/or Tidal
- Plays the Spotify playlist
- Profit

Then you get credit for all those tracks you played elsewhere.

## Setup

Clone this repo and run the following:

```sh
$ pip install -r requirements.txt
```

Create a playlist in Spotify and/or Tidal that will be cleared and populated when the script runs.

The script requires the following environment variables:

```sh
# For Spotify playlist creation and playback via spotipy
# NOTE: these are what spotipy expects for auth
SPOTIPY_CLIENT_ID
SPOTIPY_CLIENT_SECRET
SPOTIPY_REDIRECT_URI

# To get the tracks from last.fm via pylast
PYLAST_API_KEY
PYLAST_API_SECRET
```

Spotify credentials are only required when using `--playlist`.
Last.fm credentials are always required.

### Tidal authentication

Tidal uses a one-time PKCE browser login.
On first run with `--tidal-playlist`, the script will print a URL to visit in your browser.
Log in with your Tidal account, then copy the full redirect URL from the address bar (the browser will land on an error page — that's expected) and paste it back into the terminal.
The session is saved to `~/.config/respot/tidal_session.json` and reused on subsequent runs.

## Usage

```sh
$ python respot.py --last-fm-username your_username --playlist spotify_playlist_id --device device_id
```

Populate both Spotify and Tidal:

```sh
$ python respot.py --last-fm-username your_username \
    --playlist spotify_playlist_id \
    --device device_id \
    --tidal-playlist tidal_playlist_uuid
```

Tidal only (no Spotify):

```sh
$ python respot.py --last-fm-username your_username --tidal-playlist tidal_playlist_uuid
```

### All options

```
--last-fm-username    Last.fm username to pull scrobbles from
--playlist            Spotify playlist ID to populate and play
--tidal-playlist      Tidal playlist UUID to populate
--device              Spotify device ID to start playback on
--days                Number of days back to sync (default: 1)
--days-end            Number of days back to end the sync window (default: 0)
--disable-playback    Populate the Spotify playlist but don't start playback
```

Then you'll need to run this via cron or something similar.
I use the 1password `op run` via a service user to populate the env.
