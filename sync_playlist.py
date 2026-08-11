import os
import json
import urllib.request
import urllib.parse
import base64
import re

CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
PLAYLIST_ID = '29aKY5vrd3S2CZweLp1JK3'

def get_token():
    auth = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()
    data = urllib.parse.urlencode({'grant_type': 'client_credentials'}).encode()
    req = urllib.request.Request(
        'https://accounts.spotify.com/api/token', data=data,
        headers={'Authorization': f'Basic {auth}', 'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())['access_token']

def get_spotify_tracks(token):
    tracks = []
    url = f'https://api.spotify.com/v1/playlists/{PLAYLIST_ID}/tracks?limit=100'
    while url:
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
        with urllib.request.urlopen(req) as r:
            res = json.loads(r.read())
        for item in res.get('items', []):
            t = item.get('track')
            if not t:
                continue
            tracks.append({
                'title': t.get('name'),
                'artist': ', '.join(a['name'] for a in t.get('artists', []))
            })
        url = res.get('next')
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
    if not CLIENT_ID or not CLIENT_SECRET:
        print('Error: SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET environment variables not set.')
        return

    # Load existing tracks.json as cache
    cache = {}
    try:
        with open('tracks.json', 'r') as f:
            existing = json.load(f)
            for track in existing:
                cache[f"{track['title']}|{track['artist']}"] = track['yt_id']
    except Exception as e:
        print('No existing tracks.json cache found:', e)

    print('Fetching tracks from Spotify...')
    token = get_token()
    spotify_tracks = get_spotify_tracks(token)
    print(f'Found {len(spotify_tracks)} tracks in Spotify playlist.')

    final_tracks = []
    for track in spotify_tracks:
        key = f"{track['title']}|{track['artist']}"
        yt_id = cache.get(key)
        
        if not yt_id:
            query = f"{track['title']} {track['artist']} audio"
            print(f'Searching YouTube for: {query}')
            yt_id = get_youtube_id(query)
        
        if yt_id:
            final_tracks.append({
                'title': track['title'],
                'artist': track['artist'],
                'yt_id': yt_id
            })

    # Save to tracks.json
    with open('tracks.json', 'w') as out:
        json.dump(final_tracks, out, indent=2)
    print('Updated tracks.json with latest tracks.')

if __name__ == '__main__':
    main()
