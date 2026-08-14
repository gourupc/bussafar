import os
import json
import urllib.request
import urllib.parse
import re
from datetime import datetime, timedelta

def get_youtube_video_id_for_loop(query):
    print(f"Searching YouTube for background loop video: '{query}'")
    try:
        url = 'https://www.youtube.com/results?search_query=' + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        
        # Scrape top video ID
        video_ids = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html)
        # De-duplicate
        unique_ids = []
        for vid in video_ids:
            if vid not in unique_ids:
                unique_ids.append(vid)
        
        if unique_ids:
            print(f"Found loop background video: {unique_ids[0]}")
            return unique_ids[0]
    except Exception as e:
        print(f"Error fetching YouTube loop video: {e}")
    # Fallback to a high-quality aesthetic ambient background loop (rainy bus driver)
    return "busdriver.mp4"

def find_videos_in_json(obj, results):
    if isinstance(obj, dict):
        if 'videoId' in obj and 'title' in obj:
            try:
                video_id = obj['videoId']
                title_runs = obj['title'].get('runs', [])
                title = title_runs[0]['text'] if title_runs else obj['title'].get('simpleText', 'New Track')
                owner_runs = obj.get('ownerText', {}).get('runs', [])
                if not owner_runs:
                    owner_runs = obj.get('shortBylineText', {}).get('runs', [])
                artist = owner_runs[0]['text'].replace(' - Topic', '') if owner_runs else 'Artist'
                
                if len(video_id) == 11 and title:
                    results.append({
                        'title': title,
                        'artist': artist,
                        'yt_id': video_id,
                        'yt_slowed_id': video_id
                    })
            except Exception:
                pass
        else:
            for k, v in obj.items():
                find_videos_in_json(v, results)
    elif isinstance(obj, list):
        for item in obj:
            find_videos_in_json(item, results)

def scrape_youtube_playlist(query, limit=35):
    print(f"Searching YouTube for tracks: '{query}'")
    results = []
    try:
        url = 'https://www.youtube.com/results?search_query=' + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        
        json_match = re.search(r'var ytInitialData = (\{.*?\});</script>', html)
        if json_match:
            data = json.loads(json_match.group(1))
            find_videos_in_json(data, results)
    except Exception as e:
        print(f"Error scraping YouTube tracks: {e}")

    # De-duplicate by yt_id
    unique_results = []
    seen_ids = set()
    for r in results:
        # Filter out obvious non-music results or channel/user items
        if r['yt_id'] not in seen_ids and len(r['title']) < 180:
            seen_ids.add(r['yt_id'])
            unique_results.append(r)
            
    print(f"Scraped {len(unique_results[:limit])} unique tracks.")
    return unique_results[:limit]

def main():
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    modes_path = os.path.join(repo_dir, "modes.json")
    festivals_path = os.path.join(repo_dir, "festivals.json")

    if not os.path.exists(modes_path) or not os.path.exists(festivals_path):
        print("Required config files modes.json or festivals.json not found!")
        return

    with open(modes_path, 'r') as f:
        modes = json.load(f)
    with open(festivals_path, 'r') as f:
        festivals = json.load(f)

    # Get current date in YYYY-MM-DD
    # Allows setting a custom system date via environment variable for local testing!
    simulated_date_str = os.getenv("SIMULATED_DATE")
    if simulated_date_str:
        today = datetime.strptime(simulated_date_str, "%Y-%m-%d").date()
        print(f"Using simulated date: {today}")
    else:
        today = datetime.now().date()
        print(f"Current Date: {today}")

    has_changes = False

    # Default modes that should never be deleted
    permanent_mode_ids = {"bus", "club", "mic"}
    current_mode_ids = {m["id"] for m in modes}

    for f in festivals:
        fest_id = f["id"]
        fest_date = datetime.strptime(f["date"], "%Y-%m-%d").date()
        days_active = f.get("days_active", 1)
        
        # Calculate active window: starting 3 days before, ending days_active - 1 days after
        start_date = fest_date - timedelta(days=3)
        end_date = fest_date + timedelta(days=days_active - 1)
        
        is_active = (start_date <= today <= end_date)
        print(f"Festival '{f['name']}' ({f['date']}): window {start_date} to {end_date} -> Active={is_active}")

        if is_active:
            # If active but not currently in modes.json, create it!
            if fest_id not in current_mode_ids:
                print(f"Creating festival tab: {f['name']}...")
                
                # 1. Scrape 30-40 themed songs
                scraped_tracks = scrape_youtube_playlist(f["search_query"])
                if not scraped_tracks:
                    print(f"Warning: No tracks found for {f['name']}. Using empty playlist.")
                    scraped_tracks = []
                
                # 2. Write tracklist file
                playlist_filename = f"{fest_id}_tracks.json"
                playlist_path = os.path.join(repo_dir, playlist_filename)
                with open(playlist_path, 'w') as pf:
                    json.dump(scraped_tracks, pf, indent=2)
                
                # 3. Find background video loop (defaults to a scenic ambient loop if not found)
                bg_loop_id = get_youtube_video_id_for_loop(f.get("video_query", f"{f['name']} aesthetic lofi loop"))
                
                # 4. Append new mode details
                new_mode = {
                    "id": fest_id,
                    "title": f["name"],
                    "title_hindi": f["name_hindi"],
                    "icon": f["emoji"],
                    "theme": f["theme"],
                    "video_src": bg_loop_id,
                    "playlist_file": playlist_filename,
                    "show_slowed": False
                }
                modes.append(new_mode)
                has_changes = True
                print(f"Successfully activated festival mode: {f['name']}")
        else:
            # If not active, but currently in modes.json, delete it!
            if fest_id in current_mode_ids:
                print(f"Cleaning up/deleting festival tab: {f['name']}...")
                
                # 1. Remove tracklist file
                playlist_filename = f"{fest_id}_tracks.json"
                playlist_path = os.path.join(repo_dir, playlist_filename)
                if os.path.exists(playlist_path):
                    os.remove(playlist_path)
                    print(f"Deleted playlist file: {playlist_filename}")
                
                # 2. Remove entry from modes.json
                modes = [m for m in modes if m["id"] != fest_id]
                has_changes = True
                print(f"Successfully cleaned up festival mode: {f['name']}")

    if has_changes:
        # Write back updated modes.json
        with open(modes_path, 'w') as mf:
            json.dump(modes, mf, indent=2)
        print("Updated modes.json saved successfully.")
    else:
        print("No scheduler changes required today.")

if __name__ == "__main__":
    main()
