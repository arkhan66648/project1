import json
import time
import requests
import os
import base64
import hashlib
import re
from datetime import datetime

# Current Time in Unix Milliseconds
NOW_MS = int(time.time() * 1000)

def load_config():
    if not os.path.exists('data/config.json'): return {}
    try:
        with open('data/config.json', 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def obfuscate_link(link):
    if not link: return ""
    return base64.b64encode(link.encode('utf-8')).decode('utf-8')

def clean_channel_name(raw_url):
    try:
        if '[' in raw_url:
            return raw_url.split('/channel/')[1].split('[')[0].replace('-', ' ').upper()
    except: pass
    return "HD STREAM"

def get_robust_id(title, start_time_ms):
    # Generates a stable ID from "Team A vs Team B" + Date
    # Ensures ID stays same even if time shifts slightly
    teams = re.split(r'\s+vs\.?\s+|\s+-\s+', title.lower())
    teams.sort()
    clean_teams = "".join([t.strip() for t in teams if t.strip()])
    date_str = datetime.fromtimestamp(start_time_ms / 1000).strftime('%Y%m%d')
    return hashlib.md5((clean_teams + date_str).encode('utf-8')).hexdigest()

def detect_sport_normalized(raw_sport, raw_league):
    s = str(raw_sport).upper()
    l = str(raw_league).upper()
    
    # Priority Detection
    if "BASKETBALL" in s:
        if "COLLEGE" in l or "NCAA" in l: return "NCAA Basketball"
        if "NBA" in l: return "NBA"
        return "Basketball"
    if "FOOTBALL" in s:
        if "COLLEGE" in l or "NCAA" in l: return "NCAA Football"
        if "NFL" in l: return "NFL"
        return "American Football"
    if "HOCKEY" in s: return "NHL" if "NHL" in l else "Ice Hockey"
    if "BASEBALL" in s: return "MLB" if "MLB" in l else "Baseball"
    if "SOCCER" in s: return "Soccer"
    if "FIGHT" in s or "UFC" in s: return "UFC"
    if "BOXING" in s: return "Boxing"
    if "RACING" in s or "F1" in s: return "F1"
    if "TENNIS" in s: return "Tennis"
    if "CRICKET" in s: return "Cricket"
    if "GOLF" in s: return "Golf"
    
    return raw_sport.title() or "Other"

def fetch_data():
    conf = load_config()
    matches = {} # Dictionary keyed by ID to remove duplicates
    
    # 1. Fetch Streamed.pk
    url_spk = conf.get('api_keys', {}).get('streamed_url')
    if url_spk:
        try:
            print(f"Fetching Streamed...")
            data = requests.get(url_spk, timeout=15).json()
            for m in data:
                try: start = int(m.get('date', 0))
                except: start = NOW_MS + 3600000
                
                title = m.get('title', 'Unknown')
                sport = detect_sport_normalized(m.get('category', 'Other'), title)
                mid = get_robust_id(title, start)
                
                streams = []
                for src in m.get('sources', []):
                    link = src.get('url') or src.get('id')
                    if link:
                        streams.append({
                            "id": obfuscate_link(link),
                            "name": src.get('source', 'Stream'),
                            "source": "spk"
                        })
                
                matches[mid] = {
                    "id": mid, "title": title, "sport": sport, "league": sport,
                    "start_time": start, "viewers": int(m.get('viewers', 0)),
                    "streams": streams, "origin": "streamed"
                }
        except Exception as e: print(f"Streamed Error: {e}")

    # 2. Fetch TopEmbed
    url_te = conf.get('api_keys', {}).get('topembed_url')
    if url_te:
        try:
            print(f"Fetching TopEmbed...")
            data = requests.get(url_te, timeout=15).json()
            # TopEmbed Structure: { events: { "2024-01-01": [ ... ] } }
            for events_list in data.get('events', {}).values():
                for ev in events_list:
                    try: start = int(ev['unixTimestamp']) * 1000
                    except: continue
                    
                    title = ev.get('match', 'Unknown')
                    sport = detect_sport_normalized(ev.get('sport', ''), ev.get('tournament', ''))
                    mid = get_robust_id(title, start)
                    
                    streams = []
                    channels = ev.get('channels', [])
                    if isinstance(channels, list):
                        for ch in channels:
                            link = ch if isinstance(ch, str) else ch.get('channel', '')
                            if link:
                                streams.append({
                                    "id": obfuscate_link(link),
                                    "name": clean_channel_name(link),
                                    "source": "te"
                                })
                    
                    # Merge Logic
                    if mid in matches:
                        matches[mid]['streams'].extend(streams)
                        # TopEmbed often has better League names
                        if matches[mid]['league'] == 'Other' and ev.get('tournament'):
                            matches[mid]['league'] = ev.get('tournament')
                    else:
                        matches[mid] = {
                            "id": mid, "title": title, "sport": sport, 
                            "league": ev.get('tournament', sport),
                            "start_time": start, "viewers": 0,
                            "streams": streams, "origin": "topembed"
                        }
        except Exception as e: print(f"TopEmbed Error: {e}")
        
    return list(matches.values())

if __name__ == "__main__":
    os.makedirs('data', exist_ok=True)
    
    # FETCH
    all_matches = fetch_data()
    
    # SAVE RAW DATA (Used by build_site.py)
    with open('data/matches_raw.json', 'w', encoding='utf-8') as f:
        json.dump(all_matches, f)
        
    print(f"✅ Extracted {len(all_matches)} matches.")
