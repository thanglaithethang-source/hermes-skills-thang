# Gemini API — Endpoints & Capture Notes

**Ngày capture:** 2026-07-29 | **Tab:** gemini.google.com | **Account:** thanglaithethang@gmail.com | **Model:** Pro Extended

Capture bằng CDP Network monitoring + JS interceptor (Phương pháp 2) + computer_use typing.

## Endpoints

### Chat (StreamGenerate)
```
POST https://gemini.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate
```
Params: `bl`, `f.sid`, `hl`, `_reqid`, `rt=c`

Body: `f.req` = URL-encoded nested JSON array:
```
[\"\",0,null,null,null,null,0],[\"en\"],[\"c_{conversation_id}\",\"r_{response_id}\",\"rc_{context_id}\",null,null,null,null,null,null,null,\"{token}\"]
```

**Cannot replay via Python requests** — needs CDP type/enter just like ChatGPT.

### Batchexecute RPCs
```
POST https://gemini.google.com/_/BardChatUi/data/batchexecute
```
Multiple RPC IDs observed:

| RPC ID | Purpose |
|--------|---------|
| `w7J4ee` | Send message (contains user input text) |
| `aPya6c` | Poll/keepalive (empty body `[]`) |
| `MyzX6c` | Poll (empty body) |
| `VxUbXb` | Poll (empty body) |
| `ESY5D` | Check bard_activity_enabled |
| `qpEbW` | Position tracking `[[1,4],[6,6],[1,15]]` |

Body: `f.req` URL-encoded JSON, e.g.:
```json
[[["w7J4ee","[[\"{token}\"],[null,\"r_{response_id}\"],\"Hello, what is 2+2?\"]]",null,"generic"]]]
```

Auth: `at=ADR5zap...` token in query string + SAPISIDHASH via Cookie.

### Signaler WebSocket
```
wss://signaler-pa.clients6.google.com/punctual/multi-watch/channel?VER=8&gsessionid=...
```
Used for real-time communication. Not HTTP — cannot capture via CDP Network alone.

### Telemetry
```
POST https://play.google.com/log?format=json&hasfast=true&authuser=0
POST https://play.google.com/log?hasfast=true&auth=SAPISIDHASH+...
```
Gzipped protobuf payloads containing performance metrics.

### Analytics
```
https://www.google-analytics.com/g/collect
https://analytics.google.com/g/collect
https://googleads.g.doubleclick.net/pagead/viewthroughconversion/{id}/
```

## Auth
- **SAPISIDHASH** in Cookie + `Authorization` header
- **at=** token in query string (timed, rotates on reload)
- SAPISID is httpOnly cookie → must use CDP `Network.getAllCookies`

## UI Elements
- Input: `div.ql-editor.textarea.new-input-ui` (contenteditable, placeholder "Enter a prompt for Gemini")
- Send: Enter key (keyboard event)
- Mode picker: button "Open mode picker, currently Pro Extended"
- Response rendered in `div.ql-editor:not(.textarea):not(.ql-clipboard)` or `[class*="response"]`

## Capture Workflow
1. Bridge server running + tab opened on gemini.google.com
2. Start CDP `network_start` on tab
3. Inject JS interceptor via `execute_js` (set `window.__API` = array, patch fetch/WS)
4. Use **computer_use** to click input, type text, press Enter (bridge `execute_js` with long JS strings can silently fail to return values)
5. Wait 15s for response
6. Stop CDP `network_stop` for URL list
7. Read `window.__API` via short `execute_js` to get captured interceptor data
8. Read response via short `execute_js` querying DOM selectors

## Limitation
- CDP Network monitoring on Gemini only captures CSP reports and analytics — **not** the actual chat API calls.
- JS interceptor (Phương pháp 2) is required to see `StreamGenerate` and `batchexecute` calls.
- Even with full auth/interceptor, **cannot replay** via Python requests — Gemini uses browser-specific anti-abuse similar to ChatGPT's Turnstile. Must use CDP type/enter flow.
