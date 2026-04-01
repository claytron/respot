#!/usr/bin/env python3
import argparse
import re
import os
import time
import datetime as d
from datetime import datetime, timedelta
from itertools import islice
import pylast
import spotipy
import tidalapi
from pathlib import Path
from spotipy.oauth2 import SpotifyOAuth

def spotify_client():
    scope = [
        "playlist-modify-public",
        "app-remote-control",
        "user-read-playback-state",
        "user-modify-playback-state",
    ]
    return spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

TIDAL_SESSION_FILE = Path('~/.config/respot/tidal_session.json').expanduser()

def tidal_client():
    TIDAL_SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    session = tidalapi.Session()
    if not session.login_session_file(TIDAL_SESSION_FILE, do_pkce=True, fn_print=lambda s: print(s, flush=True)):
        print("Tidal login failed")
        exit(1)
    return session

def last_fm_client():
    # Last.fm API creds
    api_key = os.environ.get('PYLAST_API_KEY', '')
    api_secret = os.environ.get('PYLAST_API_SECRET', '')

    if not (api_key or api_secret):
        print("Last.fm credentials required")
        exit(1)

    return pylast.LastFMNetwork(
        api_key=api_key,
        api_secret=api_secret,
    )

def clear_spotify_playlist(spotify, playlist):
    while True:
        playlist_items = spotify.playlist_items(playlist, limit=100)

        if playlist_items['total'] == 0:
            break

        to_remove = []
        for item in playlist_items['items']:
            to_remove.append(item['track']['uri'])
        # Clear out the playlist first
        spotify.playlist_remove_all_occurrences_of_items(playlist, to_remove)

def clear_tidal_playlist(tidal, playlist_id):
    playlist = tidal.playlist(playlist_id)
    items = list(playlist.items())
    if items:
        playlist.remove_by_indices(list(range(len(items))))

def timeframe(days=None, days_end=0, all_day=True):
    end = datetime.now(d.UTC) - timedelta(days=days_end)
    start = end - timedelta(days=days)
    if all_day:
        midnight = datetime.min.time()
        end = datetime.combine(end, midnight)
        start = datetime.combine(start, midnight)
    return [start.strftime('%s'), end.strftime('%s')]

def last_fm_tracks(lastfm, username, start, end):
    tracks = lastfm.get_user(username).get_recent_tracks(
        limit=None,
        time_from=start,
        time_to=end,
    )
    # Make sure it is chronological
    tracks.reverse()
    return tracks

def populate_spotify_playlist(spotify, last_fm_tracks, playlist):
    sp_ids = []
    for track in last_fm_tracks:
        album = track.album
        artist = track.track.artist.name
        track_name = track.track.title

        # Cleanup featuring info in artist name
        if re.search(r'(ft|feat)\.', artist, re.I):
            artist = re.sub(r'(ft|feat)\..*', '', artist, flags=re.I).strip()

        # TODO: removing just a single quote below, but seems like this
        # should be handled by the spotipy lib instead. Other chars
        # might also be problematic. Unicode seems to be a problem...
        search_string = 'track:{track_name} album:{album} artist:{artist}'.format(
            track_name=track_name.replace("'", '').replace("'", ''),
            artist=artist.replace("'", '').replace("'", ''),
            album=album.replace("'", '').replace("'", ''),
        )
        res = spotify.search(search_string, type='track', limit=1)
        items = res['tracks']['items']
        if len(items):
            sp_ids.append(items[0]['uri'])
        else:
            print("Couldn't find {}".format(search_string))

    print("Found {} items".format(len(sp_ids)))

    sp_ids_iter = iter(sp_ids)
    batches = list(iter(lambda: list(islice(sp_ids_iter, 100)), []))
    for batch in batches:
        spotify.playlist_add_items(playlist, batch)

def populate_tidal_playlist(tidal, last_fm_tracks, playlist_id):
    playlist = tidal.playlist(playlist_id)
    track_ids = []
    for track in last_fm_tracks:
        artist = track.track.artist.name
        track_name = track.track.title

        # Cleanup featuring info in artist name
        if re.search(r'(ft|feat)\.', artist, re.I):
            artist = re.sub(r'(ft|feat)\..*', '', artist, flags=re.I).strip()

        query = '{} {}'.format(track_name, artist)
        delay = 1
        while True:
            try:
                results = tidal.search(query, models=[tidalapi.Track], limit=1)
                break
            except tidalapi.exceptions.TooManyRequests:
                print("Rate limited, waiting {}s...".format(delay))
                time.sleep(delay)
                delay = min(delay * 2, 60)
        items = results.get('tracks') or []
        if items:
            track_ids.append(str(items[0].id))
        else:
            print("Couldn't find {} on Tidal".format(query))

    print("Found {} items on Tidal".format(len(track_ids)))

    track_ids_iter = iter(track_ids)
    batches = list(iter(lambda: list(islice(track_ids_iter, 100)), []))
    for batch in batches:
        playlist.add(batch)

def start_spotify_playback(spotify, device, playlist):
    spotify.start_playback(
        device_id=device,
        context_uri='spotify:playlist:{}'.format(playlist),
    )

def process_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--playlist",
        help="The Spotify ID of the playlist to populate and play",
    )
    parser.add_argument(
        "--tidal-playlist",
        help="The Tidal UUID of the playlist to populate",
    )
    parser.add_argument(
        "--device",
        help="The device ID of the place to play the playlist",
    )
    parser.add_argument(
        "--last-fm-username",
        help="The username for the last.fm account",
    )
    parser.add_argument(
        "--days",
        help="Number of days back to sync. Default: 1",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--days-end",
        help="Number of days back to start sync. Default: 0",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--disable-playback",
        help="Do not play the playlist",
        action="store_true",
    )
    return parser.parse_args()

def main():
    args = process_args()
    lastfm = last_fm_client()
    times = timeframe(args.days, args.days_end)
    tracks = last_fm_tracks(lastfm, args.last_fm_username, times[0], times[1])

    if not tracks:
        return

    if args.playlist:
        spotify = spotify_client()
        clear_spotify_playlist(spotify, args.playlist)
        populate_spotify_playlist(spotify, tracks, args.playlist)
        if not args.disable_playback:
            start_spotify_playback(spotify, args.device, args.playlist)

    if args.tidal_playlist:
        tidal = tidal_client()
        clear_tidal_playlist(tidal, args.tidal_playlist)
        populate_tidal_playlist(tidal, tracks, args.tidal_playlist)

if __name__ == '__main__':
    main()
