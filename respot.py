#!/usr/bin/env python3
import argparse
import re
import os
from datetime import datetime, timedelta
from itertools import islice
import pylast
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from urllib.parse import quote

def spotify_client():
    scope = [
        "playlist-modify-public",
        "app-remote-control",
        "user-read-playback-state",
        "user-modify-playback-state",
    ]
    return spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

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

def last_fm_tracks(lastfm, username, days, days_end):
    now = datetime.utcnow() - timedelta(days=days_end)
    yesterday = now - timedelta(days=days)
    return lastfm.get_user(username).get_recent_tracks(
        limit=None,
        time_from=yesterday.strftime('%s'),
        time_to=now.strftime('%s'),
    )

def populate_spotify_playlist(spotify, last_fm_tracks, playlist):
    sp_ids = []
    for track in last_fm_tracks:
        album = track.album
        artist = track.track.artist.name
        track_name = track.track.title

        # Cleanup featuring info in artist name
        if re.search(r'(ft|feat)\.', artist, re.I):
            artist = re.sub(r'(ft|feat)\..*', '', artist, re.I).strip()

        # TODO: removing just a single quote below, but seems like this
        # should be handled by the spotipy lib instead. Other chars
        # might also be problematic. Unicode seems to be a problem...
        search_string = 'track:{track_name} album:{album} artist:{artist}'.format(
            track_name=track_name.replace("'", '').replace("’", ''),
            artist=artist.replace("'", '').replace("’", ''),
            album=album.replace("'", '').replace("’", ''),
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
        help="Do no play the playlist",
        action="store_true",
    )
    return parser.parse_args()

def main():
    args = process_args()
    spotify = spotify_client()
    lastfm = last_fm_client()
    clear_spotify_playlist(spotify, args.playlist)
    tracks = last_fm_tracks(lastfm, args.last_fm_username, args.days, args.days_end)

    if not len(tracks):
        exit

    populate_spotify_playlist(spotify, tracks, args.playlist)

    if not args.disable_playback:
        start_spotify_playback(spotify, args.device, args.playlist)

if __name__ == '__main__':
    main()
