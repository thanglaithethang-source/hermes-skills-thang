# MoneyPrinterTurbo — Detailed Reference

Path: `C:\Users\thang\Downloads\_projects\MoneyPrinterTurbo\`
Version: 1.3.0
Python: `.venv/Scripts/python` (3.11, NOT system 3.14)

## Config (config.toml)

Active providers:
- **LLM:** DeepSeek v4 Pro via the configured OpenAI-compatible endpoint (`DEEPSEEK_API_KEY`)
- **Stock video:** Pixabay (`PIXABAY_API_KEY`), Pexels (`PEXELS_API_KEY`)
- **LLM fallback:** Gemini 2.5 Flash (`GOOGLE_API_KEY`)
- **TTS:** Edge TTS (free, `edge_tts_timeout = 30`)
- **Whisper:** large-v3, CPU, int8

Never commit API keys or tokens. Store them in the local `.env`/secrets store and keep that file outside the repository.

## CLI Usage

```bash
cd "$_PROJECTS/MoneyPrinterTurbo"

# Simplest: topic → video
.venv/Scripts/python cli.py --video-subject "How AI works"

# With custom script
.venv/Scripts/python cli.py --video-subject "AI" --video-script "script.txt"

# Vietnamese
.venv/Scripts/python cli.py --video-subject "Cách AI hoạt động" --video-language vi

# Short video, no subtitle
.venv/Scripts/python cli.py --video-subject "..." --paragraph-number 3 --no-subtitle-enabled

# Stop at audio only (preview TTS)
.venv/Scripts/python cli.py --video-subject "..." --stop-at audio
```

## Pipeline Stages

`--stop-at`: script → terms → audio → subtitle → materials → video (default)

## Key Options

| Option | Values | Default |
|---|---|---|
| `--video-source` | pexels, pixabay, coverr, local | pixabay |
| `--video-aspect` | "16:9", "9:16", "1:1" | "9:16" |
| `--video-concat-mode` | random, sequential | random |
| `--video-transition-mode` | none, shuffle, fade-in, fade-out, slide-in, slide-out | none |
| `--video-clip-duration` | seconds | auto |
| `--video-count` | 1+ | 1 |
| `--bgm-type` | none, random, custom | random |
| `--voice-name` | any Edge TTS voice | from config |
| `--subtitle-position` | top, center, bottom, custom | bottom |

## Web UI

```bash
.venv/Scripts/python main.py
# → http://127.0.0.1:8080/docs (API)
# → http://127.0.0.1:8080 (Web UI if enabled)
```

## Output

Videos go to `storage/` by default. Named by task UUID.
