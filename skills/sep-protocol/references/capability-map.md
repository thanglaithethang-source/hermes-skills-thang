# Agent Capability Map

Cập nhật: 2026-07-23 | Tổng: 94 skills, 34 tools, 12 models

---

## Models (api.ai-box.vn — 12 model)

### Text (10)
| Nhóm | Model | Context |
|------|-------|---------|
| DeepSeek | `deepseek-v4-pro[1m]` *(default)* | 1M |
| DeepSeek | `deepseek-v4-flash[1m]` | 1M |
| DeepSeek | `deepseek-v4-pro` | chuẩn |
| DeepSeek | `deepseek-v4-flash` | chuẩn |
| Qwen | `qwen3.8-max-preview` | — |
| Qwen | `qwen3.7-max` | — |
| Qwen | `qwen3.7-plus` | — |
| Kimi | `kimi-k2.7-code` | — |
| Kimi | `kimi-k2.6` | — |
| GLM | `glm-5.2` | — |

### Image (2)
| Model |
|-------|
| `wan2.7-image-pro` |
| `qwen-image-2.0` |

**API check:** `GET https://api.ai-box.vn/v1/models` với Bearer token từ config `custom_providers[0].api_key`.

---

## Tools (34 tools / 10 nhóm)

### Desktop Automation (1)
`computer_use` — cua-driver background: capture, click, type, scroll, drag

### Browser Control (10)
`browser_navigate` `browser_snapshot` `browser_click` `browser_type` `browser_press` `browser_scroll` `browser_back` `browser_console` `browser_get_images` `browser_vision`

### Agency & Delegation (5)
`agency_agents_search` `agency_agents_inspect` `agency_agents_load` `agency_agents_delegate` `delegate_task`

### File System (4)
`read_file` `write_file` `patch` `search_files`

### Shell & Process (2)
`terminal` `process`

### Code Execution (1)
`execute_code` — Python + Hermes SDK (read_file, write_file, search_files, patch, terminal, json_parse, shell_quote, retry)

### Knowledge Management (4)
`memory` `session_search` `skill_view` `skill_manage`

### Task Management (2)
`todo` `cronjob`

### Interaction (2)
`clarify` `text_to_speech`

### MCP: AI Company (8)
`company_start` `company_stop` `company_pause` `company_resume` `company_status` `company_result` `company_steer` `company_request_action` `company_approve` `company_execute_approved_action`

### Vision (1)
`vision_analyze`

---

## Skills (94 skills / 22+ nhóm)

### CORE — Vận hành Sếp (4)
`sep-protocol` `sep-workflow` `sep-operating-rules` `sep-workspace`

### Agent Enhancement (2)
`self-improving-agent` `ontology-knowledge-graph`

### Autonomous AI Agents (5)
`claude-code` `codex` `opencode` `gemini-subagents` `hermes-agent`

### Software Development (8)
`plan` `spike` `test-driven-development` `systematic-debugging` `requesting-code-review` `simplify-code` `node-inspect-debugger` `hermes-agent-skill-authoring`

### Computer Control (4)
`computer-use` `computer-control` `chrome-cdp-control` `hermes-chrome-bridge`

### Browser Research (3)
`browser-research` `browser-api-hijack` `cao`

### GitHub (6)
`github-auth` `github-repo-management` `github-pr-workflow` `github-code-review` `github-issues` `codebase-inspection`

### Post-Production (7)
`post-production-planning` `capcut-production-executor` `capcut-draft-editing` `capcut-draft-repair` `capcut-filter-id-resolution` `resolve-post-production` `toonflow-control`

### Video Production (1)
`video-production`

### Creative (14)
`architecture-diagram` `excalidraw` `manim-video` `p5js` `touchdesigner-mcp` `comfyui` `claude-design` `sketch` `popular-web-designs` `pretext` `ascii-art` `ascii-video` `humanizer` `design-md`

### Productivity (8)
`google-workspace` `notion` `airtable` `powerpoint` `nano-pdf` `ocr-and-documents` `teams-meeting-pipeline` `maps`

### Research (5)
`multi-search-engine` `arxiv` `blogwatcher` `llm-wiki` `polymarket`

### Media (4)
`youtube-content` `gif-search` `stock-images` `songsee`

### MLOps (4)
`huggingface-hub` `llama-cpp` `weights-and-biases` `segment-anything-model`

### Operations (7)
`hermes-tool-integration` `hermes-messaging-setup` `ai-company-v5-windows` `windows-tool-setup` `windows-disk-cleanup` `file-management` `project-audit-handover`

### Khác (7)
`obsidian` `himalaya` `jupyter-live-kernel` `system-diagnostics` `system-cleanup` `dogfood` `document-data` `chrome-control-reference` `coding-engineering` `coding-subagents`
