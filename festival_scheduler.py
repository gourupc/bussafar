import os
import json
import urllib.request
import urllib.parse
import re
import time
from datetime import datetime, timedelta

def generate_ai_video(prompt, token):
    print(f"Triggering Replicate AI Video generation for prompt: '{prompt}'")
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }
    
    # Call Replicate predictions API (using LTX-Video, a fast, high-quality open-source text-to-video model)
    url = "https://api.replicate.com/v1/predictions"
    data = {
        # LTX-Video model version on Replicate
        "version": "087b7a1f59e6d0a47cb02dc9dcb6ea580c87b8d2507a27a1102db7b6d40bd672",
        "input": {
            "prompt": prompt + ", looping seamless, lofi ambient animation, high quality, 1080p",
            "width": 768,
            "height": 512,
            "num_frames": 49,
            "fps": 12
        }
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers)
        res = urllib.request.urlopen(req)
        prediction = json.loads(res.read().decode())
        pred_id = prediction["id"]
        
        # Poll prediction status until finished (max 6 minutes)
        status_url = f"https://api.replicate.com/v1/predictions/{pred_id}"
        for i in range(36):
            time.sleep(10)
            status_req = urllib.request.Request(status_url, headers=headers)
            status_res = urllib.request.urlopen(status_req)
            status_data = json.loads(status_res.read().decode())
            status = status_data["status"]
            print(f"Prediction {pred_id} status: {status}")
            
            if status == "succeeded":
                output = status_data.get("output")
                if isinstance(output, list) and output:
                    return output[0]
                elif isinstance(output, str):
                    return output
                break
            elif status in ["failed", "canceled"]:
                print(f"Replicate generation failed: {status_data.get('error')}")
                break
    except Exception as e:
        print(f"Replicate API error: {e}")
    return None

def download_file_with_headers(url, path):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response, open(path, 'wb') as out_file:
        out_file.write(response.read())

def get_pexels_loop_video(query):
    print(f"Searching Pexels for background loop video: '{query}'")
    search_url = "https://www.pexels.com/search/videos/" + urllib.parse.quote(query) + "/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        req = urllib.request.Request(search_url, headers=headers)
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        
        video_links = re.findall(r'href="/video/([a-zA-Z0-9\-]+/)"', html)
        if not video_links:
            return None
        
        first_video_url = "https://www.pexels.com/video/" + video_links[0]
        v_req = urllib.request.Request(first_video_url, headers=headers)
        v_html = urllib.request.urlopen(v_req, timeout=10).read().decode('utf-8')
        
        mp4_urls = re.findall(r'https://videos\.pexels\.com/video-files/[a-zA-Z0-9\-/\._]+\.mp4', v_html)
        if not mp4_urls:
            return None
        
        # Look for HD/Full HD landscapes
        resolutions = ["_1920_1080_", "-hd_1920_1080_", "_1280_720_", "-hd_1280_720_", "-uhd_", "_3840_2160_"]
        best_url = None
        for res in resolutions:
            for url in mp4_urls:
                if res in url:
                    best_url = url
                    break
            if best_url:
                break
        
        if not best_url:
            best_url = mp4_urls[0]
        return best_url
    except Exception as e:
        print(f"Pexels scraper error: {e}")
    return None

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

def clean_title_for_comparison(title):
    import re
    t = str(title).lower()
    # Replace 'ae' with 'aye' to match common spelling variations (e.g. Ae Watan vs Aye Watan)
    t = t.replace('ae', 'aye')
    t = re.sub(r'[^a-z0-9]', '', t)
    return t

def is_duplicate_title(new_title, existing_titles):
    new_clean = clean_title_for_comparison(new_title)
    if len(new_clean) < 8:
        return False
    for ext in existing_titles:
        ext_clean = clean_title_for_comparison(ext)
        if len(ext_clean) < 8:
            continue
        # Check prefix matching (first 12 characters)
        if new_clean[:12] == ext_clean[:12]:
            return True
        # Check if one clean title is entirely contained in the other
        if new_clean in ext_clean or ext_clean in new_clean:
            return True
    return False

def parse_duration(duration_text):
    if not duration_text:
        return 0
    try:
        parts = str(duration_text).split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except Exception:
        pass
    return 0

def parse_view_count(view_text):
    if not view_text:
        return 0
    try:
        view_text = str(view_text).lower().replace(",", "")
        match = re.search(r'([0-9.]+)\s*(k|m|b)?\s*views?', view_text)
        if match:
            num = float(match.group(1))
            suffix = match.group(2)
            if suffix == 'k':
                return int(num * 1000)
            elif suffix == 'm':
                return int(num * 1000000)
            elif suffix == 'b':
                return int(num * 1000000000)
            return int(num)
    except Exception:
        pass
    return 0

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
                
                # Extract views
                view_text = obj.get('viewCountText', {}).get('simpleText', '')
                if not view_text:
                    view_runs = obj.get('viewCountText', {}).get('runs', [])
                    if view_runs:
                        view_text = view_runs[0].get('text', '')
                if not view_text:
                    view_text = obj.get('shortViewCountText', {}).get('simpleText', '')
                
                views = parse_view_count(view_text)

                # Extract and parse duration
                duration_text = obj.get('lengthText', {}).get('simpleText', '')
                duration_sec = parse_duration(duration_text)

                # Enforce individual song duration limit (90 seconds to 420 seconds / 7 minutes)
                # This guarantees that we skip short YouTube clips/Shorts and long 30-60min Jukeboxes/Compilations!
                if 90 <= duration_sec <= 600:
                    if len(video_id) == 11 and title:
                        results.append({
                            'title': title,
                            'artist': artist,
                            'yt_id': video_id,
                            'yt_slowed_id': video_id,
                            'views': views
                        })
            except Exception:
                pass
        else:
            for k, v in obj.items():
                find_videos_in_json(v, results)
    elif isinstance(obj, list):
        for item in obj:
            find_videos_in_json(item, results)

def scrape_youtube_playlist(query):
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
    return results

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
                
                # 1. Run multiple search queries to compile a large, diverse hit song list
                queries_to_run = list(f.get("search_queries", []))
                
                # Generate 10 search queries to ensure we get a huge candidate pool (min 30 clean tracks)
                name_clean = f["name"].lower()
                devotional_themes = ['janmashtami', 'ganesh chaturthi', 'dussehra', 'dhanteras', 'diwali', 'vasant panchami', 'maha shivaratri', 'holika dahan']
                
                if name_clean in ['independence day', 'republic day']:
                    queries_to_run.extend([
                        f"{name_clean} hindi songs",
                        f"{name_clean} bollywood songs",
                        f"desh bhakti {name_clean} songs",
                        "desh bhakti hindi songs",
                        "desh bhakti geet",
                        "patriotic bollywood hits",
                        "desh bhakti song"
                    ])
                elif name_clean in devotional_themes:
                    queries_to_run.extend([
                        f"{name_clean} bhajan hits",
                        f"{name_clean} aarti bhajan",
                        f"{name_clean} devotional songs",
                        f"bhajan shree {name_clean}",
                        f"popular {name_clean} geet",
                        f"devotional {name_clean} tracks",
                        f"{name_clean} popular bhajan"
                    ])
                elif name_clean == 'holi':
                    queries_to_run.extend([
                        "holi popular songs",
                        "holi special songs",
                        "holi bollywood geet",
                        "holi geet hits",
                        "holi dhol hits",
                        "holi hindi songs",
                        "holi top hits"
                    ])
                else:
                    # Default localized variations
                    queries_to_run.extend([
                        f"{name_clean} hindi songs",
                        f"{name_clean} bollywood songs",
                        f"{name_clean} special songs",
                        f"best {name_clean} tracks",
                        f"popular {name_clean} songs",
                        f"{name_clean} hit tracks",
                        f"{name_clean} celebration songs"
                    ])
                
                raw_matches = []
                for q in queries_to_run:  # Run all specified query variations
                    raw_matches.extend(scrape_youtube_playlist(q))
                
                # Filter out Jukeboxes, Remixes, Shorts, and duplicates (strictly blocking dance/covers/school/live performances)
                banned_terms = [
                    'mashup', 'mash up', 'remix', 'mix', 'jukebox', 'nonstop', 'non-stop', 
                    'vdj', 'dj', 'visual', 'playlist', 'full album', 'compilation', 
                    'collection', '& more', 'and more', 'songs collection', 'full jukebox', 
                    'special 2026', 'special 2025', 'special 2024',
                    'dance', 'choreography', 'cover by', 'school performance', 'kids performance',
                    'performance in', 'reaction', 'karaoke', 'lesson', 'tutorial',
                    'live performance', 'live concert', 'live stage', 'live show', 'concert', 
                    'live sing', 'stage performance', 'live version'
                ]
                
                # Sort raw matches by views count descending FIRST, so that we always keep the official/highest-view version of each song!
                raw_matches.sort(key=lambda x: x.get('views', 0), reverse=True)

                scraped_tracks = []
                seen_ids = set()
                seen_titles = []
                for r in raw_matches:
                    yt_id = r.get('yt_id')
                    if not yt_id or yt_id in seen_ids:
                        continue
                    
                    title_lower = r['title'].lower()
                    has_banned = any(term in title_lower for term in banned_terms)
                    if not has_banned and len(r['title']) < 180:
                        # Apply smart title similarity de-duplication
                        if not is_duplicate_title(r['title'], seen_titles):
                            seen_ids.add(yt_id)
                            seen_titles.append(r['title'])
                            scraped_tracks.append(r)
                
                # Sort the entire list by total view count (highest first!)
                scraped_tracks.sort(key=lambda x: x.get('views', 0), reverse=True)
                
                # Enforce limit of 35-40 tracks (guarantees minimum 30 hit songs!)
                final_playlist = scraped_tracks[:35]
                print(f"Successfully compiled {len(final_playlist)} unique hit tracks for {f['name']}.")
                
                # 2. Write tracklist file
                playlist_filename = f"{fest_id}_tracks.json"
                playlist_path = os.path.join(repo_dir, playlist_filename)
                with open(playlist_path, 'w') as pf:
                    json.dump(final_playlist, pf, indent=2)
                
                # 3. Get background visual (prioritizes Pexels loop, then Replicate AI, then fallback YouTube/Unsplash!)
                bg_loop_id = None
                
                # Try fetching a gorgeous looping stock video from Pexels (100% free, no key!)
                pexels_query = f.get("video_query", f"{f['name']} loop")
                pexels_url = get_pexels_loop_video(pexels_query)
                if pexels_url:
                    try:
                        mp4_filename = f"{fest_id}.mp4"
                        mp4_path = os.path.join(repo_dir, mp4_filename)
                        print(f"Downloading premium Pexels loop to: {mp4_filename}")
                        download_file_with_headers(pexels_url, mp4_path)
                        bg_loop_id = mp4_filename
                    except Exception as e:
                        print(f"Failed to download Pexels loop: {e}")
                
                # Check for Replicate AI Video Generation Token (Fallback if Pexels fails)
                if not bg_loop_id:
                    replicate_token = os.getenv("REPLICATE_API_TOKEN")
                    if replicate_token:
                        generated_url = generate_ai_video(f.get("video_query", f"{f['name']} aesthetic lofi loop"), replicate_token)
                        if generated_url:
                            try:
                                mp4_filename = f"{fest_id}.mp4"
                                mp4_path = os.path.join(repo_dir, mp4_filename)
                                print(f"Downloading generated AI video to: {mp4_filename}")
                                download_file_with_headers(generated_url, mp4_path)
                                bg_loop_id = mp4_filename
                            except Exception as e:
                                print(f"Failed to download generated AI video: {e}")

                # If no video is resolved, use pre-configured Unsplash image or scrape YouTube
                if not bg_loop_id:
                    bg_loop_id = f.get("video_src")
                    if not bg_loop_id:
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
                
                # Also delete downloaded video loop file if present
                mp4_filename = f"{fest_id}.mp4"
                mp4_path = os.path.join(repo_dir, mp4_filename)
                if os.path.exists(mp4_path):
                    try:
                        os.remove(mp4_path)
                        print(f"Deleted video loop file: {mp4_filename}")
                    except Exception as e:
                        print(f"Failed to delete video loop file: {e}")
                
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
