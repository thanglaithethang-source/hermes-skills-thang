#!/usr/bin/env python3
"""Template: Bắt và replay YouTube InnerTube API bằng Python requests.
Kế thừa session/login từ Chrome của Sếp qua CDP.

YouTube InnerTube API KHÔNG có anti-bot (khác ChatGPT) → replay thành công bằng Python requests.

Cách dùng:
1. cd C:\\Users\\thang\\Downloads\\_projects\\hermes-chrome-extension
2. python -B this_script.py
3. Script sẽ: extract auth → replay player + search + next API
"""
import json, time, sys, os, hashlib
import requests as req_lib

PROJECT_DIR = os.path.expanduser("~/Downloads/_projects/hermes-chrome-extension")
sys.path.insert(0, PROJECT_DIR)
from chrome_send import send_command

# ===== CONFIG =====
TAB_ID = None  # Điền tab ID, hoặc None để tự chọn
VIDEO_ID = "9bZkp7q19f0"  # PSY - Gangnam Style (widely available)
SEARCH_QUERY = "AI automation 2026"
OUTPUT_DIR = os.path.join(PROJECT_DIR, "yt_replay_output")

# ===== FUNCTIONS =====

def get_tab_id():
    global TAB_ID
    if TAB_ID:
        return TAB_ID
    r = send_command({'type': 'list_tabs'})
    yt_tabs = [t for t in r.get('tabs', []) if 'youtube' in t.get('url', '').lower()]
    if len(yt_tabs) == 1:
        print(f"Auto-selected: [{yt_tabs[0]['id']}] {yt_tabs[0]['title'][:60]}")
        return yt_tabs[0]['id']
    for t in r.get('tabs', []):
        print(f"  [{t['id']}] {t['title'][:60]}")
    TAB_ID = int(input("Tab ID: ").strip())
    return TAB_ID


def extract_auth(tab_id):
    """Extract SAPISID cookie, compute SAPISIDHASH, get INNERTUBE context."""
    # 1. Get ALL cookies (including httpOnly) via CDP
    r = send_command({
        'type': 'cdp_command',
        'method': 'Network.getAllCookies',
        'params': {},
        'tabId': tab_id
    })
    all_cookies = r.get('result', {}).get('result', {}).get('cookies', [])
    if not all_cookies:
        all_cookies = r.get('result', {}).get('cookies', [])

    yt_cookies = {}
    for c in all_cookies:
        if 'youtube.com' in c.get('domain', ''):
            yt_cookies[c['name']] = c['value']

    sapisid = yt_cookies.get('SAPISID', '')
    if not sapisid:
        raise RuntimeError("SAPISID cookie not found — is Sếp logged into YouTube?")

    # 2. Compute SAPISIDHASH
    origin = 'https://www.youtube.com'
    timestamp = int(time.time())
    hash_input = f"{timestamp} {sapisid} {origin}"
    sapisidhash = hashlib.sha1(hash_input.encode('utf-8')).hexdigest()
    auth_header = f"SAPISIDHASH {timestamp}_{sapisidhash}"

    # 3. Get INNERTUBE context + API key
    r = send_command({
        'type': 'cdp_command',
        'method': 'Runtime.evaluate',
        'params': {
            'expression': 'JSON.stringify({api_key: window.ytcfg.get("INNERTUBE_API_KEY"), context: window.ytcfg.get("INNERTUBE_CONTEXT")})',
            'returnByValue': True
        },
        'tabId': tab_id
    })
    cfg = json.loads(r['result']['result']['value'])
    api_key = cfg['api_key']
    context = cfg['context']
    visitor_data = context['client']['visitorData']

    # 4. Build headers
    headers = {
        'Content-Type': 'application/json',
        'Authorization': auth_header,
        'X-Goog-AuthUser': '0',
        'X-Goog-Visitor-Id': visitor_data,
        'X-Origin': origin,
        'X-Youtube-Client-Name': '1',
        'X-Youtube-Client-Version': context['client']['clientVersion'],
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
        'Referer': f'https://www.youtube.com/watch?v={VIDEO_ID}',
        'Origin': origin,
    }

    print(f"  SAPISID: {sapisid[:20]}... (len={len(sapisid)})")
    print(f"  API Key: {api_key}")
    print(f"  Client: {context['client']['clientName']} v{context['client']['clientVersion']}")
    print(f"  Cookies: {len(yt_cookies)} YouTube cookies")

    return yt_cookies, headers, api_key, context


def replay_player(yt_cookies, headers, api_key, context, video_id):
    """Replay /youtubei/v1/player — video details + streaming data."""
    print(f"\n{'='*60}")
    print(f"REPLAY: /youtubei/v1/player (videoId={video_id})")
    print(f"{'='*60}")

    body = {
        "videoId": video_id,
        "context": context,
        "playbackContext": {
            "contentPlaybackContext": {
                "html5Preference": "HTML5_PREF_WANTS",
                "signatureTimestamp": 20195
            }
        }
    }
    url = f'https://www.youtube.com/youtubei/v1/player?key={api_key}&prettyPrint=false'
    resp = req_lib.post(url, headers=headers, cookies=yt_cookies, json=body, timeout=15)
    print(f"Status: {resp.status_code}")

    data = resp.json()
    vd = data.get('videoDetails', {})
    ps = data.get('playabilityStatus', {})
    sd = data.get('streamingData', {})

    print(f"\nTitle: {vd.get('title', 'N/A')}")
    print(f"VideoId: {vd.get('videoId', 'N/A')}")
    print(f"Author: {vd.get('author', 'N/A')}")
    print(f"ChannelId: {vd.get('channelId', 'N/A')}")
    print(f"Length: {vd.get('lengthSeconds', 'N/A')}s")
    print(f"Views: {vd.get('viewCount', 'N/A')}")
    print(f"Playability: {ps.get('status', 'N/A')}")
    if ps.get('reason'):
        print(f"  Reason: {ps['reason']}")
    print(f"Has streamingData: {len(sd) > 0}")

    if sd:
        fmts = sd.get('formats', [])
        afmts = sd.get('adaptiveFormats', [])
        print(f"Formats: {len(fmts)}")
        for f in fmts:
            print(f"  itag={f.get('itag')} quality={f.get('quality')} mime={f.get('mimeType','')[:40]} hasUrl={bool(f.get('url'))}")
        print(f"Adaptive formats: {len(afmts)}")
        for f in afmts[:5]:
            print(f"  itag={f.get('itag')} quality={f.get('quality')} mime={f.get('mimeType','')[:40]}")

    return data


def replay_search(yt_cookies, headers, api_key, context, query):
    """Replay /youtubei/v1/search — search videos."""
    print(f"\n{'='*60}")
    print(f"REPLAY: /youtubei/v1/search (query='{query}')")
    print(f"{'='*60}")

    body = {
        "context": context,
        "query": query
    }
    url = f'https://www.youtube.com/youtubei/v1/search?key={api_key}&prettyPrint=false'
    resp = req_lib.post(url, headers=headers, cookies=yt_cookies, json=body, timeout=15)
    print(f"Status: {resp.status_code}")

    data = resp.json()
    contents = data.get('contents', {})
    two_col = contents.get('twoColumnSearchResultsRenderer', {})
    primary = two_col.get('primaryContents', {})
    section_list = primary.get('sectionListRenderer', {})
    items = section_list.get('contents', [])

    video_results = []
    for item in items:
        contents_inner = item.get('itemSectionRenderer', {}).get('contents', [])
        for c in contents_inner:
            vr = c.get('videoRenderer')
            if vr:
                title = ''
                if vr.get('title', {}).get('runs'):
                    title = vr['title']['runs'][0].get('text', '')
                channel = ''
                if vr.get('ownerText', {}).get('runs'):
                    channel = vr['ownerText']['runs'][0].get('text', '')
                video_results.append({
                    'videoId': vr.get('videoId'),
                    'title': title,
                    'channel': channel,
                    'viewCount': vr.get('viewCountText', {}).get('simpleText', ''),
                    'length': vr.get('lengthText', {}).get('simpleText', ''),
                    'publishedTime': vr.get('publishedTimeText', {}).get('simpleText', ''),
                })

    print(f"Search results: {len(video_results)} videos")
    for i, v in enumerate(video_results[:10]):
        print(f"\n  [{i+1}] {v['title']}")
        print(f"      ID: {v['videoId']} | Channel: {v['channel']} | Views: {v['viewCount']} | Length: {v['length']} | Published: {v['publishedTime']}")

    return data, video_results


def replay_next(yt_cookies, headers, api_key, context, video_id):
    """Replay /youtubei/v1/next — recommendations."""
    print(f"\n{'='*60}")
    print(f"REPLAY: /youtubei/v1/next (videoId={video_id})")
    print(f"{'='*60}")

    body = {
        "context": context,
        "videoId": video_id
    }
    url = f'https://www.youtube.com/youtubei/v1/next?key={api_key}&prettyPrint=false'
    resp = req_lib.post(url, headers=headers, cookies=yt_cookies, json=body, timeout=15)
    print(f"Status: {resp.status_code}")

    data = resp.json()
    contents = data.get('contents', {})
    two_col = contents.get('twoColumnWatchNextResults', {})
    results = two_col.get('results', {}).get('results', {}).get('contents', [])

    rec_videos = []
    for item in results:
        if 'itemSectionRenderer' in item:
            sec_contents = item['itemSectionRenderer'].get('contents', [])
            for c in sec_contents:
                if 'videoRenderer' in c:
                    vr = c['videoRenderer']
                    title = vr.get('title', {}).get('runs', [{}])[0].get('text', '') if vr.get('title') else ''
                    channel = vr.get('ownerText', {}).get('runs', [{}])[0].get('text', '') if vr.get('ownerText') else ''
                    rec_videos.append({
                        'videoId': vr.get('videoId'),
                        'title': title,
                        'channel': channel,
                        'viewCount': vr.get('viewCountText', {}).get('simpleText', ''),
                        'length': vr.get('lengthText', {}).get('simpleText', ''),
                    })

    secondary = two_col.get('secondaryResults', {}).get('secondaryResults', {}).get('results', [])
    for item in secondary:
        if 'compactVideoRenderer' in item:
            vr = item['compactVideoRenderer']
            title = vr.get('title', {}).get('runs', [{}])[0].get('text', '') if vr.get('title') else ''
            channel = vr.get('longBylineText', {}).get('runs', [{}])[0].get('text', '') if vr.get('longBylineText') else ''
            rec_videos.append({
                'videoId': vr.get('videoId'),
                'title': title,
                'channel': channel,
                'viewCount': vr.get('viewCountText', {}).get('simpleText', ''),
                'length': vr.get('lengthText', {}).get('simpleText', ''),
            })

    print(f"Recommended videos: {len(rec_videos)}")
    for i, v in enumerate(rec_videos[:8]):
        print(f"\n  [{i+1}] {v['title']}")
        print(f"      ID: {v['videoId']} | Channel: {v['channel']} | Views: {v['viewCount']} | Length: {v['length']}")

    return data, rec_videos


# ===== MAIN =====
if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tab_id = get_tab_id()

    print("\n=== EXTRACTING AUTH ===")
    yt_cookies, headers, api_key, context = extract_auth(tab_id)

    # 1. Player API
    player_data = replay_player(yt_cookies, headers, api_key, context, VIDEO_ID)
    with open(os.path.join(OUTPUT_DIR, 'player_replay.json'), 'w', encoding='utf-8') as f:
        json.dump(player_data, f, indent=2, ensure_ascii=False)

    # 2. Search API
    search_data, search_results = replay_search(yt_cookies, headers, api_key, context, SEARCH_QUERY)
    with open(os.path.join(OUTPUT_DIR, 'search_replay.json'), 'w', encoding='utf-8') as f:
        json.dump(search_data, f, indent=2, ensure_ascii=False)

    # 3. Next API (recommendations)
    next_data, rec_results = replay_next(yt_cookies, headers, api_key, context, VIDEO_ID)
    with open(os.path.join(OUTPUT_DIR, 'next_replay.json'), 'w', encoding='utf-8') as f:
        json.dump(next_data, f, indent=2, ensure_ascii=False)

    print(f"\n\n{'='*60}")
    print(f"DONE — Output saved to: {OUTPUT_DIR}")
    print(f"  player_replay.json — video details + streaming data")
    print(f"  search_replay.json — search results ({len(search_results)} videos)")
    print(f"  next_replay.json — recommendations ({len(rec_results)} videos)")
    print(f"{'='*60}")
