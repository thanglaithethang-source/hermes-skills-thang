# OpenMontage — Detailed Reference

Path: `C:\Users\thang\Downloads\_projects\OpenMontage\`
Python: `.venv/Scripts/python` (full venv)
Config: `config.yaml` — Anthropic provider, mp4/h264/AAC, 1080p30, 30fps, CRF 23

## Architecture

**Instruction-driven. Agent IS the intelligence.** Python = tools + persistence only.

```
Agent reads pipeline YAML → Stage director skills (MD) → Tools (Python BaseTool)
→ Self-review (meta skill) → Checkpoints → Human approval
```

3 knowledge layers:
1. `tools/tool_registry.py` — what tools exist (capabilities, status, cost)
2. `skills/` — how OpenMontage uses them (project conventions)
3. `.agents/skills/` — generic API rules (technology-level)

## Entry Point

**ALWAYS read `AGENT_GUIDE.md` first.** It contains:
- Rule Zero: all production goes through pipeline system
- Pipeline selection guide
- Stage-by-stage execution rules
- Reference video workflow

## Pipelines (13 total)

| Pipeline | Manifest | Type |
|---|---|---|
| `talking-head` | talking-head.yaml | Footage-based |
| `animated-explainer` | animated-explainer.yaml | AI-generated |
| `animation` | animation.yaml | Animation-first |
| `cinematic` | cinematic.yaml | Cinematic edit |
| `screen-demo` | screen-demo.yaml | Screen recording |
| `clip-factory` | clip-factory.yaml | Short-form batch |
| `podcast-repurpose` | podcast-repurpose.yaml | Podcast |
| `character-animation` | character-animation.yaml | Rigged character |
| `hybrid` | hybrid.yaml | Source+support |
| `avatar-spokesperson` | avatar-spokesperson.yaml | Avatar presenter |
| `localization-dub` | localization-dub.yaml | Dubbing |
| `documentary-montage` | documentary-montage.yaml | Documentary |
| `framework-smoke` | framework-smoke.yaml | Test harness |

## Tool Registry

85 tools available. Key methods:
- `r.discover()` — scan all tool packages
- `r.list_all()` — all tool names
- `r.get_by_capability("audio")` — filter by capability
- `r.provider_menu()` — capability→provider mapping
- `r.tier_summary()` — free vs paid breakdown

## Config Loading

```python
from lib.config_model import OpenMontageConfig
c = OpenMontageConfig.load()
# c.llm.provider, c.output.default_format, c.budget.mode...
```

## Artifacts

Canonical pipeline artifacts (validated against JSON schemas in `schemas/artifacts/`):
`brief` → `script` → `scene_plan` → `asset_manifest` → `edit_decisions` → `render_report` → `publish_log`

## Budget

- Mode: warn (observe | warn | cap)
- Total: $10.00
- Reserve: 10%
- Auto-approve under $0.50
- New paid tools require approval
