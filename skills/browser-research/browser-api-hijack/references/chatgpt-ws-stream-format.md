# ChatGPT WebSocket Stream Protocol

**Captured:** 2026-07-24 | **Method:** CDP `Page.addScriptToEvaluateOnNewDocument` (Phương pháp 3)

ChatGPT stream response qua WebSocket, KHÔNG phải HTTP SSE. Endpoint:
```
wss://ws.chatgpt.com/p24/ws/user/{user_id}?verify={verify_token}
```

## WS Connection lifecycle

### 1. Connect (page load)
Client gửi:
```json
[
  {"id": 1, "command": {"type": "connect", "presence": {"type": "presence", "state": "background"}}},
  {"id": 2, "command": {"type": "subscribe", "topic_id": "calpico-chatgpt"}},
  {"id": 3, "command": {"type": "subscribe", "topic_id": "conversations"}},
  {"id": 4, "command": {"type": "subscribe", "topic_id": "app_notifications"}}
]
```

Server reply:
```json
[
  {"id": 1, "type": "reply", "reply": {"type": "connect", "subscriptions": {}}},
  {"id": 2, "type": "reply", "reply": {"type": "subscribe", "topic_id": "calpico-chatgpt", "recovered": false}},
  {"id": 3, "type": "reply", "reply": {"type": "subscribe", "topic_id": "conversations", "recovered": false}},
  {"id": 4, "type": "reply", "reply": {"type": "subscribe", "topic_id": "app_notifications", "recovered": false}}
]
```

### 2. Subscribe to conversation turn (khi gửi message)
Client gửi:
```json
[
  {"id": 5, "command": {"type": "subscribe", "topic_id": "conversation-turn-{turn_id}", "offset": "0"}}
]
```

Server reply (with catchups if already started):
```json
[
  {"id": 5, "type": "reply", "reply": {"type": "subscribe", "topic_id": "conversation-turn-{turn_id}", "last_offset": "...", "recovered": true, "catchups": [...]}},
  {"type": "message", "topic_id": "conversation-turn-{turn_id}", "payload": {...}, "offset": "..."}
]
```

### 3. Stream items (server → client)

Mỗi WS message chứa 1 hoặc nhiều stream items. Mỗi stream item có:
```json
{
  "type": "message",
  "topic_id": "conversation-turn-{turn_id}",
  "payload": {
    "type": "conversation-turn-stream",
    "payload": {
      "type": "stream-item",
      "conversation_id": "...",
      "turn_id": "...",
      "encoded_item": "event: delta_encoding\ndata: \"v1\"\n\n",
      "stream_item_id": "...",
      "parent_stream_item_id": "...",
      "server_timestamp_ms": 1784872208745
    }
  },
  "offset": "1784872208758-0"
}
```

### 4. Stream item types (theo thứ tự xuất hiện)

| # | encoded_item | Ý nghĩa |
|---|---|---|
| 1 | `event: delta_encoding`<br>`data: "v1"` | Khai báo encoding v1 |
| 2 | `data: {"type": "resume_conversation_token", "kind": "topic", "token": "eyJhbG...", "conversation_id": "..."}` | Resume token cho conversation |
| 3 | `data: {"type": "input_message", "input_message": {...}}` | Echo user message (role=user, content) |
| 4 | `event: delta`<br>`data: {"p":"", "o":"add", "v":{"message":{...}}}` | Initial assistant message (content_type=code, recipient=genui.search) |
| 5 | `data: {"type": "message_marker", "marker": "cot_token", "event": "first"}` | Chain-of-thought bắt đầu |
| 6 | `event: delta`<br>`data: {"v":{"message":{"content":{"content_type":"reasoning_recap","content":"Đã xử lý trong 4s"}}}}` | Reasoning recap (thinking done) |
| 7 | `event: delta`<br>`data: {"v":{"message":{"content":{"content_type":"text","parts":[""]}}}}` | Assistant message bắt đầu (empty text) |
| 8 | `data: {"type": "message_marker", "marker": "user_visible_token", "event": "first"}` | User-visible token bắt đầu |
| 9 | `data: {"type": "message_marker", "marker": "final_channel_token", "event": "first"}` | Final channel token bắt đầu |
| 10 | `event: delta`<br>`data: {"p":"/message/content/parts/0", "o":"append", "v":"**Sếp"}` | Append text token |
| 11 | `event: delta`<br>`data: {"v":",** 45"}` | Append text token (tiếp) |
| 12 | `event: delta`<br>`data: {"p":"", "o":"patch", "v":[{"p":"/message/content/parts/0","o":"append","v":"."}, {"p":"/message/status","o":"replace","v":"finished_successfully"}, {"p":"/message/end_turn","o":"replace","v":true}, {"p":"/message/metadata","o":"append","v":{"is_complete":true,...}}]}` | Final patch: status, end_turn, metadata |
| 13 | `data: {"type": "message_marker", "marker": "last_token", "event": "last"}` | Last token |
| 14 | `data: {"type": "server_ste_metadata", "metadata": {...}}` | Server metadata (model_slug, cluster_region, plan_type, tool_invoked, etc.) |
| 15 | `data: {"type": "message_stream_complete", "conversation_id": "..."}` | Stream complete |
| 16 | `data: {"type": "conversation_detail_metadata", "limits_progress": [...]}` | Usage limits (deep_research: 22, image_gen: 120, file_upload: 80) |
| 17 | `data: [DONE]` | Done signal |
| 18 | `{"type": "done", "conversation_id": "...", "turn_id": "..."}` | Turn done |

### 5. Unsubscribe (client → server)
```json
[{"id": 6, "command": {"type": "unsubscribe", "topic_id": "conversation-turn-{turn_id}"}}]
```

### 6. Conversation-update (server → client, post-turn)
```json
{
  "type": "conversation-update",
  "payload": {
    "conversation_id": "...",
    "update_type": "async-task-update-message",
    "update_content": {
      "async_task_id": "...",
      "message": {
        "id": "...",
        "author": {"role": "assistant"},
        "content": {"content_type": "text", "parts": ["**Sếp,** 45."]},
        "status": "finished_successfully",
        "end_turn": true,
        "metadata": {"resolved_model_slug": "gpt-5-6-thinking", ...}
      }
    }
  }
}
```

### 7. Turn complete (server → client)
```json
[
  {"type": "message", "topic_id": "conversations", "payload": {"type": "conversation-turn-complete", "payload": {"conversation_id": "..."}}}
]
```

## Delta patch format (JSON Patch)

ChatGPT dùng JSON Patch để stream text. Mỗi delta có:
- `"p"`: path (VD: `/message/content/parts/0`)
- `"o"`: operation (`add`, `append`, `replace`, `patch`)
- `"v"`: value (text token, hoặc array of patches)

**Append pattern:** Text được stream từng phần qua `append`:
```
append "**Sếp" → append ",** 45" → append "." → patch status=finished
```

Final response assembled: `"**Sếp,** 45."`

## CRITICAL: Deduplication by stream_item_id

WS protocol gửi catchups (replay) + live messages → CÙNG stream item xuất hiện nhiều lần.
Nếu không deduplicate → response text bị lặp N lần (VD: "Sếp" xuất hiện 9 lần, "+ 5 = 10." xuất hiện 9 lần).

**Fix:** Track `stream_item_id` trong set. Skip nếu đã seen.

```python
seen_ids = set()
for item in ws_messages:
    # ... parse to inner_payload ...
    sid = inner_payload.get('stream_item_id')
    if sid:
        if sid in seen_ids:
            continue
        seen_ids.add(sid)
    # ... parse encoded_item ...
```

Test result: 189 WS messages → 16 unique stream_item_ids → correct response "**Sếp + 5 = 10." (15 chars, không lặp).

## Completion Detection

Cách biết stream đã xong:
1. Tìm `[DONE]` hoặc `"type":"done"` trong `encoded_item`
2. Tìm `conversation-turn-complete` event type
3. Tìm `conversation-update` event type
4. Count stability: WS message count không đổi trong 4 lần poll (12s)

NOTE: `conversation-update` KHÔNG phải lúc nào cũng xuất hiện. Có khi chỉ có `conversation-turn-complete` (thiếu full text). Phải accumulate delta appends làm fallback.

## Key tokens for replay

| Token | Source | Purpose |
|-------|--------|---------|
| Bearer JWT (1828 chars) | `GET /api/auth/session` (via CDP Runtime.evaluate awaitPromise) | Auth cho mọi backend-api call |
| conduit_token | `POST /backend-api/f/conversation/prepare` response | Chat conversation |
| prepare_token | `POST /backend-api/sentinel/chat-requirements/prepare` response | Anti-bot prepare |
| finalize_token | `POST /backend-api/sentinel/chat-requirements/finalize` response | Anti-bot finalize |
| verify_token | WS URL query param | WebSocket connection auth |
| resume_conversation_token | WS stream item #2 | Resume conversation |
