#!/usr/bin/env python3
"""
Bas Safar — Spotify Preview Server
Fetches your playlist tracks from Spotify API and plays 30-sec previews directly in the browser.

SETUP (takes 2 minutes):
  1. Go to https://developer.spotify.com/dashboard
  2. Click "Create app"  →  give any Name & Description
  3. Set Redirect URI to:  http://localhost:8080
  4. Click Save  →  then copy Client ID and Client Secret below
"""

CLIENT_ID     = 'PASTE_YOUR_CLIENT_ID_HERE'
CLIENT_SECRET = 'PASTE_YOUR_CLIENT_SECRET_HERE'
PLAYLIST_ID   = '3jU4pDLZuYICElkyyRJwQi'
PORT          = 8080
SERVE_DIR     = '/Users/rashmikeni/Downloads'

# ──────────────────────────────────────────────────────────────
import http.server, urllib.request, urllib.parse, json, base64, sys, os

def get_token():
    auth  = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode()).decode()
    data  = urllib.parse.urlencode({'grant_type': 'client_credentials'}).encode()
    req   = urllib.request.Request(
        'https://accounts.spotify.com/api/token', data=data,
        headers={'Authorization': f'Basic {auth}',
                 'Content-Type':  'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())['access_token']

def get_tracks(token):
    tracks, url = [], (
        f'https://api.spotify.com/v1/playlists/{PLAYLIST_ID}/tracks'
        '?fields=items(track(name,artists,album(name,images),preview_url,external_urls))'
        '&limit=50')
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
    for item in data.get('items', []):
        t = item.get('track')
        if not t:
            continue
        tracks.append({
            'name':        t.get('name', 'Unknown'),
            'artist':      ', '.join(a['name'] for a in t.get('artists', [])),
            'album':       t.get('album', {}).get('name', ''),
            'image':       (t.get('album', {}).get('images') or [{}])[0].get('url', ''),
            'preview_url': t.get('preview_url'),        # 30-sec MP3, may be None
            'spotify_url': t.get('external_urls', {}).get('spotify', ''),
        })
    return tracks

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SERVE_DIR, **kwargs)

    def do_GET(self):
        if self.path == '/api/tracks':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                tracks = get_tracks(get_token())
                self.wfile.write(json.dumps(tracks).encode())
            except Exception as e:
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            super().do_GET()

    def log_message(self, fmt, *args):
        pass   # silent

if __name__ == '__main__':
    if 'PASTE_YOUR' in CLIENT_ID or not CLIENT_ID.strip():
        print('\n' + '='*55)
        print('  ❌  Add your Spotify credentials to spotify_server.py')
        print('  1.  https://developer.spotify.com/dashboard')
        print('  2.  Create App  →  copy Client ID + Secret')
        print('='*55 + '\n')
        sys.exit(1)

    print(f'\n🎵  Bas Safar server  →  http://localhost:{PORT}/index.html\n')
    with http.server.HTTPServer(('', PORT), Handler) as s:
        s.serve_forever()
