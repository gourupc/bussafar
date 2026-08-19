import os
import json
import urllib.request
import urllib.parse
import re

PLAYLIST_ID = '29aKY5vrd3S2CZweLp1JK3'

def get_spotify_tracks_public():
    url = f'https://open.spotify.com/embed/playlist/{PLAYLIST_ID}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
    
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">([^<]+)</script>', html)
    if not match:
        raise Exception('Could not find __NEXT_DATA__ script tag in Spotify embed page.')
    
    data = json.loads(match.group(1))
    props = data.get('props', {}).get('pageProps', {}).get('state', {}).get('data', {})
    entity = props.get('entity', {})
    track_list = entity.get('trackList', [])
    
    tracks = []
    for item in track_list:
        tracks.append({
            'title': item.get('title'),
            'artist': item.get('subtitle')
        })
    return tracks

def get_youtube_id(query):
    try:
        url = 'https://www.youtube.com/results?search_query=' + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            match = re.search(r'\"videoId\":\"([^\"]+)\"', html)
            if match:
                return match.group(1)
    except Exception as e:
        print(f'Error searching YouTube for {query}: {e}')
    return ''

def main():
    cache = {}
    try:
        with open('tracks.json', 'r') as f:
            existing = json.load(f)
            for track in existing:
                cache[f"{track['title']}|{track['artist']}"] = track
    except Exception as e:
        print('No existing tracks.json cache found:', e)

    print('Fetching tracks from Spotify public embed page...')
    try:
        spotify_tracks = get_spotify_tracks_public()
    except Exception as e:
        print(f'Error fetching Spotify tracks: {e}. Aborting sync to protect local data.')
        return

    print(f'Found {len(spotify_tracks)} tracks in Spotify playlist.')
    if not spotify_tracks or len(spotify_tracks) == 0:
        print('Warning: Retrieved 0 tracks from Spotify. Aborting sync to prevent emptying tracks.json.')
        return

    final_tracks = []
    for track in spotify_tracks:
        key = f"{track['title']}|{track['artist']}"
        entry = cache.get(key, {})
        yt_id = entry.get('yt_id')
        yt_slowed_id = entry.get('yt_slowed_id')
        
        if not yt_id:
            query = f"{track['title']} {track['artist']} high quality audio"
            print(f'Searching YouTube for: {query}')
            yt_id = get_youtube_id(query)

        if not yt_slowed_id:
            slowed_query = f"{track['title']} {track['artist']} slowed and reverb audio"
            print(f'Searching YouTube for slowed: {slowed_query}')
            yt_slowed_id = get_youtube_id(slowed_query) or yt_id
        
        if yt_id:
            final_tracks.append({
                'title': track['title'],
                'artist': track['artist'],
                'yt_id': yt_id,
                'yt_slowed_id': yt_slowed_id or yt_id
            })

    # Save to tracks.json
    with open('tracks.json', 'w') as out:
        json.dump(final_tracks, out, indent=2)
    print('Updated tracks.json with latest tracks.')

if __name__ == '__main__':
    main()
