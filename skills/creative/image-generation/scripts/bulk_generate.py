"""
Bulk image generation script for wan2.7-image-pro.
Usage: python bulk_generate.py prompts.txt
  prompts.txt: one prompt per line
Output: images saved to OUTPUT_DIR + manifest.csv
"""
import yaml, requests, os, time, hashlib, csv, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# === CONFIG ===
CONFIG_PATH = r"C:\Users\thang\AppData\Local\hermes\config.yaml"
OUTPUT_DIR = r"C:\Users\thang\Downloads\New folder"
MODEL = "wan2.7-image-pro"
SIZE = "1024x1024"
MAX_WORKERS = 20
N_PER_REQUEST = 1  # tăng lên nếu API hỗ trợ n>1

# Load API key
with open(CONFIG_PATH) as f:
    cfg = yaml.safe_load(f)
BASE_URL = cfg['custom_providers'][0]['base_url']
API_KEY = cfg['custom_providers'][0]['api_key']
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

def sanitize_filename(prompt, max_len=40):
    safe = prompt[:max_len].replace(" ", "_").replace("/", "_").replace("\\", "_")
    safe = "".join(c for c in safe if c.isalnum() or c in "_-")
    return safe or "image"

def generate_and_save(prompt, idx):
    ts = time.strftime("%Y%m%d_%H%M%S")
    fname = f"{ts}_{sanitize_filename(prompt)}.png"
    fpath = os.path.join(OUTPUT_DIR, fname)

    try:
        # Generate
        resp = requests.post(f"{BASE_URL}/images/generations", headers=HEADERS, json={
            "model": MODEL, "prompt": prompt, "n": N_PER_REQUEST, "size": SIZE
        }, timeout=90)
        resp.raise_for_status()
        data = resp.json()
        img_url = data['data'][0]['url']

        # Download
        img_data = requests.get(img_url, timeout=30).content

        # Save
        with open(fpath, "wb") as f:
            f.write(img_data)

        sha = hashlib.sha256(img_data).hexdigest()[:12]
        size_kb = len(img_data) / 1024
        return idx, fpath, size_kb, sha, None

    except Exception as e:
        return idx, None, 0, "", str(e)

def main(prompts_file):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(prompts_file, "r", encoding="utf-8") as f:
        prompts = [line.strip() for line in f if line.strip()]

    print(f"Generating {len(prompts)} images with {MAX_WORKERS} workers...")
    start = time.time()

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(generate_and_save, p, i): i for i, p in enumerate(prompts)}
        for future in as_completed(futures):
            results.append(future.result())
            done = len(results)
            if done % 10 == 0:
                print(f"  {done}/{len(prompts)} done ({time.time()-start:.0f}s)")

    results.sort(key=lambda r: r[0])

    # Manifest CSV
    manifest_path = os.path.join(OUTPUT_DIR, f"manifest_{time.strftime('%Y%m%d_%H%M%S')}.csv")
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "prompt", "file_path", "size_kb", "sha256", "error"])
        for idx, fpath, size_kb, sha, err in results:
            writer.writerow([idx, prompts[idx], fpath or "", f"{size_kb:.0f}", sha, err or ""])

    ok = sum(1 for r in results if r[1])
    fail = len(results) - ok
    elapsed = time.time() - start
    print(f"\nDone: {ok} OK, {fail} failed | {elapsed:.0f}s total")
    print(f"Manifest: {manifest_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bulk_generate.py prompts.txt")
        sys.exit(1)
    main(sys.argv[1])
