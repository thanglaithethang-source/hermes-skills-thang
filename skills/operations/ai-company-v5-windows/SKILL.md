---
name: ai-company-v5-windows
description: "Bootstrap AI Company V5 on Windows — PowerShell encoding fixes, import paths, validator patches, Docker-less mode fallback."
version: 1.0.0
metadata:
  hermes:
    tags: [ai-company, v5, windows, bootstrap, powershell, docker-less]
    category: operations
triggers:
  - "cài AI Company"
  - "bootstrap V5"
  - "ai company windows"
  - "V5 không chạy"
  - "Docker-less AI Company"
pitfalls:
  - "PowerShell 5.1 chokes on Unicode em-dash in PS1 scripts — convert to ASCII before running."
  - "Tools in tools/ import ai_company but package root not on sys.path — add sys.path.insert."
  - "validate_package.py scans vendor/agent-swarm Helm templates — exclude vendor/ from scans."
  - "pycache from compile_roles + unit tests breaks validator — auto-clean at validation time."
  - "Docker is a hard dependency for Agent Swarm. Without it: no swarm, no e2e smoke, no handoff READY."
  - "bootstrap.ps1 line 58: $Name: $actual parsed as PSDrive — use ${Name}:."
---

# AI Company V5 — Windows Bootstrap

Bootstrapping the V5 package on Windows PowerShell 5.1 without Docker.
Follow `INSTALL.md` flow but apply runtime fixes for encoding, imports, and validation.

## Quick Path (no Docker)

```powershell
# 1. Fix all PS1 encoding (once, before any script)
python -c "
import glob
for f in glob.glob('D:/AI-COMPANY/scripts/*.ps1'):
    with open(f,'r',encoding='utf-8-sig') as fh: t=fh.read()
    t=t.replace('\u2014','--').replace('\u2013','-').lstrip('\ufeff')
    with open(f,'w',encoding='utf-8',newline='\r\n') as fh: fh.write(t)
"

# 2. Patch bootstrap.ps1: remove docker from required, skip docker info
# 3. Run bootstrap
.\scripts\bootstrap.ps1 -Root D:\AI-COMPANY

# 4. Skip onboard-agent-swarm.ps1 and configure-hermes.ps1
# 5. Controller MCP is auto-available; Agency Agents already loaded
```

## PowerShell 5.1 Encoding

All PS1 scripts from the V5 package need encoding fixes before they can run:

| Issue | Symptom | Fix |
|-------|---------|-----|
| Em-dash (—) | Parser error "Unexpected token" | Replace with `--` |
| En-dash (–) | Parser error | Replace with `-` |
| BOM on UTF-8 | `?param` not recognized | Strip BOM, save UTF-8 no-BOM |
| Smart quotes | Parser errors | Replace with straight quotes |

Run `scripts/ps1-encoding-fix.py --root D:/AI-COMPANY` for the one-shot fixer script.

## Python Import Path

Affected tools: `compile_roles.py`, `acceptance_gate.py`, `collect_runtime_evidence.py`

Symptom: `ModuleNotFoundError: No module named 'ai_company'`

Fix: Add before the first `from ai_company` import:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```

## Validator Patches

`tools/validate_package.py` needs two runtime fixes for Windows bootstrap:

1. **Skip vendor/ scans** — `vendor/agent-swarm/` contains Helm chart templates with `{{ }}` Go syntax that fail YAML parsing. Add `if any(p in path.parts for p in ("vendor", ".venv", "backups", "__pycache__")): continue` before JSON/YAML/Python rglob loops.

2. **Auto-clean pycache** — Running compile_roles + unit tests creates `__pycache__/` in `ai_company/`, `tests/`, `tools/`. Instead of erroring, auto-delete: `shutil.rmtree(unwanted, ignore_errors=True)` for dirs, `unwanted.unlink(missing_ok=True)` for files. Only skip `.venv/`, `backups/`, `vendor/`.

## Bootstrap PS1 Fix

`bootstrap.ps1` line 58: `Write-Host "$Name: $actual"` → PowerShell parses `$Name:` as a PSDrive. Fix: `${Name}: $actual`.

## Docker Requirement

`bootstrap.ps1` line 22-26 requires `docker` in PATH + `docker info`. If no Docker:
- Remove `docker` from the `@('git','python','npm','docker')` array
- Remove the `docker info` check block
- Replace with: `Write-Host 'Docker: skipped per Sếp instruction'`

## What Works / What's Blocked Without Docker

**Works:**
- Environment audit (except Docker checks)
- Bootstrap: venv, deps, clone repos, compile 21 roles, 45 unit tests, validate package
- Agency Agents: search/inspect/load/delegate (254 agents)
- Controller MCP: all `company_*` tools
- Hermes native `delegate_task` for multi-agent

**Blocked:**
- `onboard-agent-swarm.ps1` (needs Docker containers)
- Agent Swarm MCP (needs running containers)
- `run-e2e-smoke.ps1` (needs Docker + live workers)
- `verify-handoff.ps1` → stays BLOCKED
- Full durable orchestration via Agent Swarm task pool

**Verdict:** Controller + Agency Agents + delegate_task give functional multi-agent without Docker. The durable orchestration layer (pause/resume/steer/repair via Swarm) is the missing piece.
