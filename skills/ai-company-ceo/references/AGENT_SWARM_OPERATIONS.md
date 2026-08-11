# Agent Swarm Operations — AI Company V5

## Normal path

Hermes communicates with the durable controller. The controller communicates with Agent Swarm.

```text
Hermes → company_start → SQLite project
Controller daemon → Agent Swarm send-task
Workers → join-swarm / get-tasks / task-action claim / store-progress
Controller → review / merge integration / deterministic evaluation / repair
```

## Worker task protocol

Each task contains a JSON envelope:

```json
{
  "protocol": "ai-company-task-v2",
  "envelope_sha256": "...",
  "project_id": "...",
  "local_task_id": "...",
  "kind": "producer|review|repair|final_audit",
  "prompt": "...",
  "workspace": "...",
  "sandbox": "read-only|workspace-write",
  "timeout_seconds": 2700,
  "worker_checks": []
}
```

Workers return:

```json
{
  "protocol": "ai-company-worker-result-v2",
  "envelope_sha256": "...",
  "task_id": "...",
  "agent_id": "...",
  "started_at": "...",
  "ended_at": "...",
  "exit_code": 0,
  "artifacts": [{"path":"...","sha256":"..."}],
  "checks": [],
  "structured": {},
  "structured_files": [],
  "telemetry": {"cost_usd": null, "input_tokens": 0, "output_tokens": 0}
}
```

## Direct Agent Swarm tools

Direct swarm tools are for status and diagnosis. The controller itself uses:

- `get-swarm`
- `get-tasks`
- `get-metrics`
- `send-task`
- `get-task-details`
- `task-action`
- `store-progress`

## Recovery

- Controller and worker state is stored in `runtime/company.db` and Agent Swarm.
- Restart with `scripts/restart-controller-test.ps1`.
- The same worker UUIDs are reused across restarts.
- Worktrees and integration branches remain on disk.
- Never delete Docker volumes during a normal stop.
