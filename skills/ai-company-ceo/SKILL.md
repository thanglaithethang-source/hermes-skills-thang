---
name: ai-company-ceo
description: Operate a durable multi-functional AI company through the AI Company Controller, Agency Agents and Agent Swarm until machine-verifiable acceptance or a controlled stop.
version: 5.0.0
metadata:
  hermes:
    tags: [multi-agent, orchestration, company, codex, durable-workflows]
    category: autonomous-ai-agents
---

# AI COMPANY CEO

## When to use

Use this skill when Sếp gives a multi-step goal that benefits from multiple specialties, parallel execution, durable state, review and repair. Do not activate the full company for a trivial one-step task.

## Required preflight

1. Confirm `runtime/HERMES_HANDOFF_READY.json` exists and has `status: READY`.
2. Confirm the Agency Agents router exposes:
   - `agency_agents_search`
   - `agency_agents_inspect`
   - `agency_agents_load`
   - `agency_agents_delegate`
3. Confirm MCP server `ai_company_controller` exposes the `company_*` tools.
4. Confirm MCP server `ai_company_swarm` is available for transparent read-only inspection.
5. Confirm worker profile, workspace, budget, time and approval boundaries.
6. If any prerequisite fails, report `BLOCKED` with exact evidence.

## Goal Contract

Before execution, create a Goal Contract containing:

- objective;
- deliverables;
- measurable acceptance criteria;
- deterministic verification command or bounded path check for every criterion;
- constraints and allowed resources;
- prohibited actions;
- approval gates;
- topology (`local_safe`, `local_heavy`, `distributed`, or `distributed_30`);
- max retries and repair cycles;
- stop conditions.

Never use “looks good” as an acceptance criterion.

## Recruit

Use Agency Agents lazily to choose role slugs. The controller compiles each selected Agency role into a runtime profile containing:

- role identity and specialist prompt;
- Codex or Hermes runtime;
- capabilities;
- model tier and reasoning effort;
- sandbox mode;
- task time limit.

Do not preload the complete roster.

## Start durable execution

Use `company_start` on `ai_company_controller`.

Pass:

- `goal_contract`;
- `topology`;
- `repo_path` when code or files in a repository must change;
- optional `task_plan`.

When `task_plan` is omitted, the durable controller sends a planning task to the lead agent and compiles the returned DAG. The controller—not the Hermes chat session—owns the long-running loop.

Do not manually fan out durable project tasks with direct `send-task` unless diagnosing controller failure.

## Controller tools

- `company_start`: create a durable project.
- `company_status`: read state, tasks, reviews, repairs and result.
- `company_steer`: add instructions without resetting passed work.
- `company_pause`: pause dispatch and evaluation.
- `company_resume`: resume from SQLite state.
- `company_request_action`: run the approval policy.
- `company_approve`: record Sếp’s explicit decision.
- `company_execute_approved_action`: resume the exact approved internal checkpoint; external actions still require a dedicated executor.
- `company_stop`: controlled stop.
- `company_result`: retrieve the final result.

Use the exact MCP-prefixed names discovered in the current Hermes session.

## Durable state machine

The controller owns:

```text
CREATED → CONTRACTED → PLANNING → EXECUTING
→ REVIEWING → INTEGRATING → EVALUATING
→ REPAIRING → ACCEPTED
```

Controlled terminal or waiting states:

```text
APPROVAL_REQUIRED
BLOCKED
FAILED_LIMIT
STOPPED
```

Closing or restarting Hermes must not stop workers or erase project state.

## Parallelism

- Independent tasks are dispatched before waiting.
- Tasks carry real `dependsOn` relationships.
- Capability routing includes both `role:<slug>` and `runtime:<codex|hermes>`.
- Worker processes claim tasks from Agent Swarm.
- Respect topology and provider concurrency limits.
- Queue overflow is preferred to uncontrolled spawning.

## Workspace isolation

For every task that produces repository artifacts:

- controller creates a dedicated Git branch;
- controller creates a dedicated Git worktree;
- Codex may write only in its assigned worktree;
- Hermes runs with the safe toolset and returns bounded structured files for the worker to materialize;
- main branch is never merged automatically;
- accepted branches merge only into the project integration branch;
- conflicts become BLOCKED or scoped repair tasks.

## Review and repair

Every producer result requires an independent review task. Producer and reviewer must be different worker IDs.

On failure:

1. preserve passed work;
2. record the failed task/check;
3. create a linked repair task;
4. run an independent review of the repair;
5. rerun deterministic checks;
6. run regression checks;
7. continue until PASS or a stop limit.

## Machine-verifiable completion

Do not accept self-attested booleans or manually edited evidence JSON.

The valid completion path is:

```text
runtime collector reads Agent Swarm + workers + SQLite + Git + Docker + Hermes
→ evidence bundle is HMAC-signed
→ acceptance engine verifies runtime identities, timestamps, worktrees,
  reviewer separation, repair lineage, deterministic tests and restart durability
→ HERMES_HANDOFF_READY.json
```

A project is DONE only when controller state is `ACCEPTED` and machine acceptance passes.

## Safety

Use `company_request_action` before:

- merging main;
- production deployment;
- external messaging or publishing;
- spending money;
- account or permission changes;
- destructive operations;
- registry/firewall/security changes;
- opening public ports;
- accessing sensitive data not explicitly authorized.

No approval means no action.

## Reporting

Use compact sections:

STATUS, GOAL, PHASE, TASK COUNTS, RUNNING WORKERS, PASS, FAIL, BLOCKERS, APPROVAL NEEDED, NEXT ACTION, ARTIFACTS, EVIDENCE.
