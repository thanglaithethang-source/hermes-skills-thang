# SFX & BGM Hunting — Freesound Workflow (2026-07-22 verified)

Proven technique for building complete audio libraries from Freesound for video projects.

## Freesound API
- Key: in agent memory (r7EZFGAUP9iKxnPLLghnZ7WuWdUkjMGFAmbeh9Xs)
- Search: `https://freesound.org/apiv2/search/text/?query=<q>&token=<key>&page_size=8&fields=id,name,duration,previews`
- Preview download: `https://cdn.freesound.org/previews/<xx>/<id>_<hash>-hq.mp3` — WORKS, no OAuth2 needed
- Rate limit: ~1 req/0.3s
- Broader 1-2 word queries beat specific long queries

## Pattern
1. Map each SFX/BGM to a search query
2. Parallel download with ThreadPoolExecutor (5-8 workers)
3. Sort results by duration (longer preferred for ambience/BGM)
4. Synth fallback with Python `wave` module for unfindable sounds

## Audio import into CapCut
```json
{"id":"<UUID>","type":"extract_music","category_name":"local","name":"file.wav","path":"C:/absolute/path.wav","duration":<us>}
```
Path must be absolute with forward slashes.
