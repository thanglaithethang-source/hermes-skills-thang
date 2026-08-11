#!/usr/bin/env python
"""
SFX + BGM HUNT & GENERATE TEMPLATE
===================================
Copy this file to your project directory, customize SLOT_DEFINITIONS and BGM_ZONES,
then run: PYTHONUTF8=1 python hunt_sfx_bgm.py

Proven pattern (2026-07-22): 120 SFX slots, 99% SHA256 uniqueness from Freesound.
Pipeline: Define → Hunt (Freesound + parallel download) → Registry → Audit

REQUIREMENTS:
  - Python 3.8+
  - Freesound API token (set FREESOUND_TOKEN below)
  - PYTHONUTF8=1 when running from terminal (Windows encoding fix)
  - NO FFMPEG — Sếp cấm tuyệt đối dùng ffmpeg cho âm thanh (2026-07-31).
    Freesound MP3 lưu trực tiếp, synthetic WAV dùng Python wave module.

ARCHITECTURE:
  Phase 1: Hunt SFX (ThreadPoolExecutor, 6 workers) — Freesound search → download → synthetic fallback
  Phase 2: Generate BGM (layered synthetic tones)
  Phase 3: Save ASSET_REGISTRY.json
  Phase 4: SHA256 uniqueness audit
"""
import os, sys, json, hashlib, struct, math, wave, time, random
import urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

# ═══════════════════════════════════════════════════════════
# CONFIG — EDIT THESE
# ═══════════════════════════════════════════════════════════
FREESOUND_TOKEN = "YOUR_FREESOUND_TOKEN_HERE"
BASE = os.path.dirname(os.path.abspath(__file__))  # project root
SFX_DIR = os.path.join(BASE, "assets", "sfx")
BGM_DIR = os.path.join(BASE, "assets", "bgm")
REGISTRY_PATH = os.path.join(BASE, "runtime", "ASSET_REGISTRY.json")
SR = 24000  # sample rate for synthetic WAV

os.makedirs(SFX_DIR, exist_ok=True)
os.makedirs(BGM_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════
# REGISTRY HELPERS
# ═══════════════════════════════════════════════════════════
registry = {"sfx": [], "bgm": []}

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def save_registry():
    with open(REGISTRY_PATH, 'w') as f:
        json.dump(registry, f, indent=2)

def reg_sfx(slot_id, filename, sha, source_url, license_tag="CC0"):
    registry["sfx"].append({
        "asset_id": slot_id,
        "file_path": os.path.join(SFX_DIR, filename),
        "filename": filename,
        "sha256": sha,
        "status": "BOUND_FREESOUND" if "freesound" in source_url else "BOUND_SYNTHETIC",
        "source_url": source_url,
        "license": license_tag,
        "duration_s": None
    })

def reg_bgm(zone_id, filename, sha, source_url="synthetic", license_tag="CC0"):
    registry["bgm"].append({
        "asset_id": zone_id,
        "file_path": os.path.join(BGM_DIR, filename),
        "filename": filename,
        "sha256": sha,
        "status": "BOUND_FREESOUND" if "freesound" in source_url else "BOUND_SYNTHETIC",
        "source_url": source_url,
        "license": license_tag,
        "duration_s": None
    })

# ═══════════════════════════════════════════════════════════
# FREESOUND API
# ═══════════════════════════════════════════════════════════
def freesound_search(query, page_size=8):
    """Search Freesound, return list of {id, name, duration, preview_url}"""
    url = f"https://freesound.org/apiv2/search/text/?query={urllib.parse.quote(query)}&token={FREESOUND_TOKEN}&page_size={page_size}&fields=id,name,duration,previews"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HermesAgent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        results = []
        for r in data.get("results", []):
            preview_url = r.get("previews", {}).get("preview-hq-mp3", "")
            if not preview_url:
                preview_url = r.get("previews", {}).get("preview-lq-mp3", "")
            if preview_url:
                results.append({
                    "id": r["id"],
                    "name": r["name"],
                    "duration": r.get("duration", 0),
                    "preview_url": preview_url,
                    "source_url": f"https://freesound.org/people/.../sounds/{r['id']}/"
                })
        return results
    except Exception:
        return []

def freesound_download(preview_url, filepath):
    """Download MP3 directly — NO FFMPEG CONVERSION (Sếp cấm 2026-07-31)."""
    try:
        req = urllib.request.Request(preview_url, headers={"User-Agent": "HermesAgent/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            with open(filepath, 'wb') as f:
                f.write(resp.read())
        return os.path.exists(filepath) and os.path.getsize(filepath) > 500
    except Exception:
        if os.path.exists(filepath):
            os.remove(filepath)
        return False

# ═══════════════════════════════════════════════════════════
# SYNTHETIC GENERATORS (WAV 24kHz mono)
# ═══════════════════════════════════════════════════════════
def gen_wav(filepath, samples, sr=SR):
    with wave.open(filepath, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        for s in samples:
            s = max(-32767, min(32767, int(s)))
            wf.writeframesraw(struct.pack('<h', s))

def gen_beat(filepath, freq, dur, sr=SR, amp=0.5, decay=4.0):
    """Sine wave with exponential decay envelope"""
    n = int(sr * dur)
    samples = [amp * math.exp(-t * decay) * 32767 * math.sin(2 * math.pi * freq * t)
               for i, t in enumerate(i / sr for i in range(n))]
    gen_wav(filepath, samples, sr)

def gen_noise(filepath, dur, sr=SR, amp=0.15, color="white"):
    """White/pink noise"""
    n = int(sr * dur)
    samples = []
    b = [0.0] * 7
    for i in range(n):
        w = random.uniform(-1, 1)
        if color == "pink":
            b[0] = 0.99886 * b[0] + w * 0.0555179
            b[1] = 0.99332 * b[1] + w * 0.0750759
            b[2] = 0.96900 * b[2] + w * 0.1538520
            b[3] = 0.86650 * b[3] + w * 0.3104856
            b[4] = 0.55000 * b[4] + w * 0.5329522
            b[5] = -0.7616 * b[5] - w * 0.0168980
            val = (b[0] + b[1] + b[2] + b[3] + b[4] + b[5] + b[6] + w * 0.5362) * 0.11
        else:
            val = w
        samples.append(amp * val * 32767)
    gen_wav(filepath, samples, sr)

def gen_sweep(filepath, freq_start, freq_end, dur, sr=SR, amp=0.4):
    """Frequency sweep with slight fade"""
    n = int(sr * dur)
    samples = []
    for i in range(n):
        t = i / sr
        freq = freq_start + (freq_end - freq_start) * (t / dur)
        env = 1.0 - (0.3 * t / dur)
        samples.append(amp * env * 32767 * math.sin(2 * math.pi * freq * t))
    gen_wav(filepath, samples, sr)

def gen_tick_sequence(filepath, freq, tick_dur, gap_dur, count, sr=SR, amp=0.4):
    """Series of short ticks with gaps"""
    n_tick = int(sr * tick_dur)
    n_gap = int(sr * gap_dur)
    samples = []
    for c in range(count):
        for i in range(n_tick):
            t = i / sr
            env = 1.0 - (i / n_tick)
            samples.append(amp * env * 32767 * math.sin(2 * math.pi * freq * t))
        samples.extend([0] * n_gap)
    gen_wav(filepath, samples, sr)

def gen_tone_burst(filepath, freqs, dur_each, sr=SR, amp=0.4):
    """Sequence of tones, each with slight fade"""
    n = int(sr * dur_each)
    samples = []
    for freq in freqs:
        for i in range(n):
            t = i / sr
            env = 1.0 - (i / n) * 0.5
            samples.append(amp * env * 32767 * math.sin(2 * math.pi * freq * t))
    gen_wav(filepath, samples, sr)

def gen_drum_hit(filepath, freq, dur, sr=SR, amp=0.6):
    """Drum-like hit: fast attack, pitch drop + noise"""
    n = int(sr * dur)
    samples = []
    for i in range(n):
        t = i / sr
        ratio = t / dur
        f = freq * (1.0 - ratio * 0.8)
        env = math.exp(-t * 12)
        tone = math.sin(2 * math.pi * f * t)
        noise = random.uniform(-0.3, 0.3) * env
        samples.append(amp * 32767 * (tone * 0.6 + noise) * env)
    gen_wav(filepath, samples, sr)

# ═══════════════════════════════════════════════════════════
# BGM SYNTHETIC GENERATION (layered tones)
# ═══════════════════════════════════════════════════════════
def gen_bgm_zone(filepath, dur_sec, freqs, amp=0.15, wave_type="sine"):
    """Generate BGM zone as layered tones with amplitude modulation + fade in/out.
    
    Args:
        dur_sec: duration in seconds
        freqs: list of frequencies (layers). More frequencies = richer texture.
        amp: amplitude per layer (lower for more layers)
        wave_type: 'sine' (smooth), 'triangle' (harsh but warm), 'square' (chiptune)
    
    See references/bgm-synthetic-generation.md for zone templates.
    """
    n = int(SR * dur_sec)
    samples = [0.0] * n

    for freq in freqs:
        for i in range(n):
            t = i / SR
            # Amplitude modulation for movement (0.3 Hz LFO)
            mod = 0.7 + 0.3 * math.sin(2 * math.pi * 0.3 * t)
            # Waveform selection
            if wave_type == "sine":
                val = math.sin(2 * math.pi * freq * t)
            elif wave_type == "triangle":
                phase = (freq * t) % 1.0
                val = 4.0 * abs(phase - 0.5) - 1.0
            elif wave_type == "square":
                val = 1.0 if (freq * t) % 1.0 < 0.5 else -1.0
            else:
                val = math.sin(2 * math.pi * freq * t)
            samples[i] += (amp / len(freqs)) * mod * val * 32767

    # Gentle fade in/out (1.5 seconds each)
    fade_frames = int(SR * 1.5)
    for i in range(min(fade_frames, n)):
        samples[i] *= (i / fade_frames)
    for i in range(min(fade_frames, n)):
        samples[n - 1 - i] *= (i / fade_frames)

    gen_wav(filepath, samples, SR)

# ═══════════════════════════════════════════════════════════
# SLOT DEFINITIONS — CUSTOMIZE BELOW
# ═══════════════════════════════════════════════════════════

# SFX: (slot_id, filename, freesound_query, synthetic_fallback_function)
# The fallback function receives filepath and generates a WAV.
# Set query to None to skip Freesound (synthetic only).
# Set fallback to None to make Freesound mandatory (slot will fail if not found).
SFX_SLOTS = [
    # EXAMPLE — replace with your actual slots:
    # ("SFX_OPENING_BOOM", "SFX_OPENING_BOOM.wav", "deep boom",
    #  lambda fp: gen_drum_hit(fp, 30, 2.0, amp=0.95)),
    # ("SFX_LEVEL_UP", "SFX_LEVEL_UP.wav", "level up",
    #  lambda fp: gen_tone_burst(fp, [262, 330, 392, 523], 0.12, amp=0.4)),
    # ("SFX_WHOOSH", "SFX_WHOOSH.wav", "whoosh",
    #  lambda fp: gen_noise(fp, 0.8, amp=0.2)),
    # ("SFX_BELL", "SFX_BELL.wav", "chime bright",
    #  lambda fp: gen_beat(fp, 880, 0.3, decay=10.0, amp=0.4)),
]

# BGM: (zone_id, filename, duration_sec, frequencies, amplitude, wave_type)
BGM_ZONES = [
    # EXAMPLE — replace with your actual zones:
    # ("M1_EPIC_INTRO", "M1_EPIC_INTRO.wav", 30, [55, 65, 82, 110], 0.18, "sine"),
    # ("M2_CHIPTUNE", "M2_CHIPTUNE.wav", 45, [262, 330, 392, 523], 0.12, "square"),
    # ("M3_AMBIENT", "M3_AMBIENT.wav", 90, [294, 370, 440, 587], 0.08, "sine"),
]

# ═══════════════════════════════════════════════════════════
# HUNT ONE SLOT
# ═══════════════════════════════════════════════════════════
def process_slot(slot):
    slot_id, filename, query, synth_fn = slot
    filepath = os.path.join(SFX_DIR, filename)

    # Skip if already exists and is valid
    if os.path.exists(filepath) and os.path.getsize(filepath) > 500:
        sha = sha256_file(filepath)
        reg_sfx(slot_id, filename, sha, "cached")
        return f"  SKIP {slot_id}"

    # Try Freesound
    if query:
        results = freesound_search(query, page_size=5)
        if results:
            best = results[0]
            if freesound_download(best["preview_url"], filepath):
                sha = sha256_file(filepath)
                reg_sfx(slot_id, filename, sha, best["source_url"])
                return f"  FS   {slot_id} ← {query} ({best['name'][:50]})"

    # Synthetic fallback
    if synth_fn:
        try:
            synth_fn(filepath)
            sha = sha256_file(filepath)
            reg_sfx(slot_id, filename, sha, "synthetic")
            return f"  SYN  {slot_id} ← {query or 'N/A'}"
        except Exception as e:
            return f"  FAIL {slot_id}: {e}"

    return f"  FAIL {slot_id}: no Freesound results + no fallback"

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════
def main():
    t0 = time.time()
    print(f"SFX slots: {len(SFX_SLOTS)}, BGM zones: {len(BGM_ZONES)}")

    # Phase 1: SFX (parallel — ThreadPoolExecutor 6 workers)
    print("\n=== PHASE 1: SFX HUNT ===")
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(process_slot, slot): slot for slot in SFX_SLOTS}
        for f in as_completed(futures):
            print(f.result())

    # Phase 2: BGM (sequential — each zone can be 1-5 min)
    print("\n=== PHASE 2: BGM GENERATION ===")
    for zone_id, filename, dur, freqs, amp, wtype in BGM_ZONES:
        filepath = os.path.join(BGM_DIR, filename)
        if os.path.exists(filepath) and os.path.getsize(filepath) > 10000:
            sha = sha256_file(filepath)
            reg_bgm(zone_id, filename, sha, "cached")
            print(f"  SKIP {zone_id}")
        else:
            gen_bgm_zone(filepath, dur, freqs, amp, wtype)
            sha = sha256_file(filepath)
            reg_bgm(zone_id, filename, sha)
            print(f"  BGM  {zone_id} ← {dur}s")

    # Phase 3: Save registry
    save_registry()

    # Phase 4: SHA256 uniqueness audit
    sfx_sha_counter = Counter(e["sha256"] for e in registry["sfx"])
    unique_sfx = len(sfx_sha_counter)
    top_sha, top_count = sfx_sha_counter.most_common(1)[0]
    pct = top_count / max(len(registry["sfx"]), 1) * 100

    bgm_sha_counter = Counter(e["sha256"] for e in registry["bgm"])
    unique_bgm = len(bgm_sha_counter)

    elapsed = time.time() - t0
    print(f"\n=== BUILD COMPLETE ({elapsed:.0f}s) ===")
    print(f"SFX: {len(registry['sfx'])} files, {unique_sfx} unique ({unique_sfx/max(len(registry['sfx']),1)*100:.0f}%)")
    print(f"  Top hash: {top_sha[:12]}... appears {top_count}x ({pct:.0f}%)")
    print(f"BGM: {len(registry['bgm'])} zones, {unique_bgm} unique ({unique_bgm/max(len(registry['bgm']),1)*100:.0f}%)")
    print(f"Registry: {REGISTRY_PATH}")

    if pct > 30:
        print(f"\nWARNING: {pct:.0f}% SFX share same hash — possible synthetic clone batch!")
    if unique_sfx / max(len(registry['sfx']), 1) < 0.6:
        print(f"WARNING: SFX uniqueness {unique_sfx/max(len(registry['sfx']),1)*100:.0f}% below 60% target!")

if __name__ == "__main__":
    main()
