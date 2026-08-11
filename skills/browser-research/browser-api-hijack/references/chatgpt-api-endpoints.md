# ChatGPT API Endpoints — Cấu trúc backend API + Chat message flow

**Ngày capture:** 2026-07-24 | **Tab:** ChatGPT (chatgpt.com) | **Plan:** Plus | **Locale:** vi-VN

Capture bằng 3 phương pháp: (1) CDP Network monitoring — 241 requests, 77 API calls; (2) JS Interceptor injection (post-load) — 24 fetch + 2 WS send (0 WS recv); (3) CDP Pre-load Interceptor — 112 fetch + 25 WS events (3 send + 22 recv). Phương pháp 3 là duy nhất bắt được WebSocket receive (stream tokens).

## Auth

Tất cả `/backend-api/*` endpoints dùng Bearer token trong header:
```
Authorization: Bearer eyJhbG...I1Ni...QfixJIUIBw
```

### Cách lấy Bearer token (3 phương pháp, theo độ ưu tiên)

**Cách 1 (BEST) — CDP Runtime.evaluate với awaitPromise:**
Gọi `/api/auth/session` từ page context — browser tự đính kèm httpOnly cookies:
```python
r = send_command({
    'type': 'cdp_command',
    'method': 'Runtime.evaluate',
    'params': {
        'expression': 'fetch("/api/auth/session",{credentials:"include"}).then(r=>r.json()).then(d=>JSON.stringify(d))',
        'awaitPromise': True,
        'returnByValue': True
    },
    'tabId': tab_id
})
auth = json.loads(r['result']['result']['value'])
token = auth['accessToken']  # Full 1828-char JWT
```
Response cũng chứa: user info (email, name, idp, mfa), account info (planType, structure), expires.

**Cách 2 — CDP Network.getAllCookies:**
Lấy tất cả cookies (kể cả httpOnly) nhưng KHÔNG có Bearer JWT — chỉ có session cookies như `__Secure-next-auth.session-token.0` (3933 chars, encrypted Next.js session, KHÔNG dùng được trực tiếp làm Bearer).

**Cách 3 — Captured request headers:**
Interceptor (Phương pháp 2 hoặc 3) bắt được `Authorization: Bearer ...` header trong fetch calls. Full token nằm trong `entry['headers']['authorization']`.

### JWT Payload (decoded)
```json
{
  "aud": ["https://api.openai.com/v1"],
  "client_id": "app_X8zY6vW2pQ9tR3dE7nK1jL5gH",
  "https://api.openai.com/auth": {
    "amr": ["pwd", "otp", "mfa", "urn:openai:amr:otp_email"],
    "chatgpt_account_id": "02a5bace-1496-4bd1-88b7-b1ae497c2606",
    "chatgpt_user_id": "user-iQrGYRPNuqkGhTpLO5yoPtDx",
    "chatgpt_plan_type": "plus"
  }
}
```
Token expire: ~3 tháng (captured 2026-07-24, expires 2026-10-22).

### Intermediate tokens (cần cho replay)

| Token | Source | Purpose |
|-------|--------|---------|
| conduit_token | `POST /backend-api/f/conversation/prepare` → `response.conduit_token` | Chat conversation |
| prepare_token | `POST /backend-api/sentinel/chat-requirements/prepare` → `response.prepare_token` | Anti-bot prepare |
| finalize_token | `POST /backend-api/sentinel/chat-requirements/finalize` → `response.token` | Anti-bot finalize |
| verify_token | WS URL query param (`?verify=...`) | WebSocket connection auth |
| resume_conversation_token | WS stream item #2 | Resume conversation |

Tất cả intermediate tokens được bắt đầy đủ bằng Phương pháp 3 (CDP pre-load interceptor).

## Chat message flow (capture bằng JS interceptor)

Khi user gửi 1 chat message, ChatGPT thực hiện 5 bước:

### 1. Prepare conversation
```
POST /backend-api/f/conversation/prepare
```
Response:
```json
{"status": "ok", "conduit_token": "eyJhbG...8yRA"}
```

### 2. Send message (endpoint chính)
```
POST /backend-api/f/conversation
```
Request body:
```json
{
  "action": "next",
  "messages": [{
    "id": "5a9f8aa5-...",
    "author": {"role": "user"},
    "create_time": 1784871536.694,
    "content": {
      "content_type": "text",
      "parts": ["What is 10 divided by 2?"]
    },
    "metadata": {
      "selected_sources": [],
      "serialization_metadata": {"custom_symbol_offsets": []}
    }
  }],
  "conversation_id": "6a62f972-3254-83ec-a9fc-5480254586ff",
  "parent_message_id": "2418d7b7-...",
  "model": "gpt-5-6-thinking",
  "client_prepare_state": "success",
  "timezone_offset_min": -420,
  "timezone": "Asia/Saigon",
  "conversation_mode": {"kind": "primary_assistant"},
  "enable_message_followups": true,
  "system_hints": [],
  "supports_buffering": true,
  "supported_encodings": ["v1"],
  "client_contextual_info": {
    "is_dark_mode": false,
    "time_since_loaded": 392,
    "prompt_type": "text"
  }
}
```

### 3. Anti-bot (sentinel)
```
POST /backend-api/sentinel/chat-requirements/prepare  → prepare_token
POST /backend-api/sentinel/chat-requirements/finalize  → token
POST /backend-api/sentinel/ping                        → giữ alive (lặp lại)
POST /backend-api/sentinel/req                          → challenge
```

### 4. Stream response (WebSocket)
```
wss://ws.chatgpt.com/p24/ws/user/user-iQrGYRPNuqkGhTpLO5yoPtDx?verify={verify_token}
```

Client gửi subscribe:
```json
[{"id": 13, "command": {"type": "subscribe", "topic_id": "conversation-turn-{turn_id}", "offset": "0"}}]
```

Server stream tokens về qua WS messages. Client gửi unsubscribe khi done:
```json
[{"id": 14, "command": {"type": "unsubscribe", "topic_id": "conversation-turn-{turn_id}"}}]
```

### 5. Post-completion
```
POST /backend-api/f/conversation/prepare   (prepare cho turn tiếp theo)
POST /backend-api/lat/r                     (latency report)
POST /ces/v1/t                             (analytics: "Generate Completion", "Stream Completed")
```

## Endpoint catalog (nhóm theo chức năng)

### User & Account
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/backend-api/me` | Thông tin user hiện tại |
| GET | `/backend-api/accounts/check/v4-2023-04-27?timezone_offset_min=-420` | Trạng thái account |
| GET | `/backend-api/accounts/optimized/check` | Check tối ưu |
| GET | `/backend-api/user_granular_consent` | Consent settings |
| GET | `/backend-api/subscriptions?account_id={id}` | Subscription info |
| GET | `/backend-api/settings/user` | User settings |
| GET | `/backend-api/pageConfigs/billing` | Billing page config |
| GET | `/backend-api/user_surveys/active` | Active surveys |

### Conversations
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/backend-api/conversations?offset=0&limit=28&order=updated&is_archived=false&is_starred=false` | List conversations |
| POST | `/backend-api/conversation/init` | Khởi tạo conversation mới |
| GET | `/backend-api/calpico/chatgpt/rooms/summary?limit=10&include_pinned=true` | Chat rooms summary |
| GET | `/backend-api/pins` | Pinned conversations |

### Models
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/backend-api/models?iim=false&is_gizmo=false&supports_model_picker_upgrade_presets=true` | Available models |
| GET | `/backend-api/tpp/models/` | TPP models |

### Chat Requirements (anti-bot)
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/backend-api/sentinel/chat-requirements/prepare` | Prepare chat requirements |
| POST | `/backend-api/sentinel/chat-requirements/finalize` | Finalize chat requirements |

### Gizmos (Custom GPTs)
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/backend-api/gizmos/snorlax/sidebar?owned_only=true&conversations_per_gizmo=5&limit=20` | Sidebar gizmos |
| GET | `/backend-api/gizmos/{gizmo_id}` | Gizmo detail |
| GET | `/backend-api/gizmos/{gizmo_id}/conversations?cursor=0&limit=5&owned_only=true` | Gizmo conversations |

### Connectors (Integrations)
| Method | Endpoint | Body |
|--------|----------|------|
| POST | `/backend-api/aip/connectors/list_accessible?skip_actions=true&external_logos=true&skip_directory=true` | — |
| POST | `/backend-api/aip/connectors/links/list_accessible` | `{"link_refresh_strategy":"BLOCKING","principals":[]}` |

### Voice & Audio
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/backend-api/settings/voices?voice_mode=advanced` | Voice settings |
| GET | `/backend-api/settings/voices?spoken_language=vi&voice_mode=advanced` | Voice settings (Vietnamese) |

### System & Content
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/backend-api/system_hints?mode=basic` | System hints basic |
| GET | `/backend-api/system_hints?mode=plugins` | System hints plugins |
| GET | `/backend-api/system_hints?mode=custom_agents` | System hints custom agents |
| GET | `/backend-api/system_hints?mode=plugins&suggestions=true` | Plugin suggestions |
| GET | `/backend-api/images/bootstrap` | Image feature bootstrap |
| GET | `/backend-api/beacons/home?current_chatgpt_web_tab=chat` | Home beacons |
| GET | `/backend-api/amphora/notifications?limit=20` | Notifications |
| GET | `/backend-api/hazelnuts?include_permissions=true&scope=installed` | Hazelnuts (extensions) |
| GET | `/backend-api/checkout_pricing_config/configs/VN` | Pricing config (Vietnam) |
| GET | `/backend-api/tasks` | Tasks |
| GET | `/backend-api/task_suggestions` | Task suggestions |
| GET | `/backend-api/client/strings` | Client strings (i18n) |
| GET | `/backend-api/apps/sources_dropdown` | App sources |
| GET | `/backend-api/prompt_library/?limit=4&use_v2=true&model_slug=gpt-5-3` | Prompt library (gpt-5-3) |
| GET | `/backend-api/prompt_library/?limit=4&use_v2=true&model_slug=gpt-5-6-thinking` | Prompt library (gpt-5-6-thinking) |
| POST | `/backend-api/files/library` | Files library |
| GET | `/backend-api/celsius/ws/user` | Celsius WebSocket user info |

### Analytics (Segment.io)
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/ces/v1/p` | Page tracking |
| POST | `/ces/v1/t` | Event tracking (Sidebar Show, Locale Loaded, page_load_ttfi, etc.) |
| POST | `/ces/v1/i` | Identify (userId, plan_type) |
| POST | `/ces/v1/rgstr` | Registration events |

## Key observations

1. **Model slugs observed:** `gpt-5-3`, `gpt-5-6-thinking` — ChatGPT Plus có thể chọn nhiều model
2. **Locale:** `vi-VN` — Sếp's Chrome set locale Vietnamese
3. **Plan type:** `plus` — từ Segment identify event
4. **Anti-bot:** `sentinel/chat-requirements` prepare + finalize phải chạy trước khi chat
5. **Chat response stream:** Qua WebSocket (`wss://ws.chatgpt.com/p24/ws/user/...`), KHÔNG phải HTTP SSE
6. **Account ID:** `02a5bace-1496-4bd1-88b7-b1ae497c2606`
7. **User ID:** `user-iQrGYRPNuqkGhTpLO5yoPtDx`
8. **Conversation API path:** `/backend-api/f/conversation` (không phải `/backend-api/conversation` như cũ)
9. **Prepare endpoint:** `/backend-api/f/conversation/prepare` trả về `conduit_token` — cần thiết cho conversation request
