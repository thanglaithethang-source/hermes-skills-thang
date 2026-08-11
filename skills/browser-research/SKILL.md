---
name: browser-research
description: Web research, documentation lookup, solution discovery, claim verification.
version: 1.0.0
---

# Browser Research

## Activation
When task involves: finding current information, checking docs, finding repos, researching solutions, comparing tools, verifying claims.

## Workflow
1. Define the question precisely
2. Break into search queries
3. Prioritize official sources (docs, repos, papers)
4. Check dates and versions
5. Cross-reference multiple sources
6. Separate fact from inference
7. Save evidence (URLs, excerpts)
8. Produce actionable conclusion

## Source Priority
1. Official documentation
2. Authoritative repositories (GitHub, GitLab)
3. Academic papers (arXiv, conferences)
4. Technical blogs from recognized experts
5. Community discussions (only for context, not conclusions)

## Rules
- Never use a single weak source as sole evidence
- Always check publication date and version compatibility
- Mark clearly: VERIFIED / INFERRED / ASSUMED / UNKNOWN
- Research must lead to a specific decision or action

## Completion Criteria
- Question answered with sources
- Fact/inference/assumption clearly separated
- Actionable conclusion provided

## References

- `references/github-repo-evaluation.md` — Pattern for evaluating GitHub repos: clone → verify integration → concise verdict. Covers distinguishing marketing tags from real code support.

## Common Failures
- Trusting marketing content as technical evidence
- **Over-explaining research findings** — when the verdict is clear (repo is immature, incompatible, etc.), give a one-line verdict with evidence, not a full architecture breakdown. Sếp wants decisive conclusions, not theory lectures.
- Using outdated information without checking
- Drawing conclusions from insufficient sources
- **Trusting GitHub search/README tags without codebase verification** — "supports X" in a repo description means nothing. Clone and grep the source.
