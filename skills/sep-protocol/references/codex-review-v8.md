# Codex Review V8 — Session Detail

## Review Score: 6.8/10 (deeper than V7's 7.4)

V8 score is LOWER than V7 because the review went deeper — found silent status conversions,
response drift, enrichment failures, and calibration gaps that V7's surface review missed.

## 31 Issues Found

### 6 HIGH
- H1: Live publish-date still broken — relative dates ("2 weeks ago") in all parsers, breaks outlier + keyword analytics
- H2: Response-format drift silently reported as `empty` or `ok` — unrecognized HTTP-200 should be `unsupported`
- H3: `/next` enrichment failure hidden by `video_info.status == "ok"` — should be `partial`
- H4: Reports claim `ok` when upstream components unavailable — need dependency reducer
- H5: Calibration labelled "validated" without enforcing schema (training_query_count, thresholds, coefficients)
- H6: Channel growth zero-length single-snapshot comparison reported as valid `ok`

### 18 MEDIUM
M1-M18 covering: autocomplete URL injection, transport error gaps, auth silent degrade, client metadata inconsistency, unvalidated inputs, duration None handling, Shorts classification inconsistency, channel stats empty=ok, suggested no pagination, count parser duplication, analytics fragility, SQLite resource handling, timestamp ordering, packaging incomplete, tests overstate coverage, docs stale, skill validator fail, RPM unreproducible.

### 7 LOW
L1-L7: dead code, region ignored, duplicate match, Result factory, error body verbatim, handoff exposure, shared mutable dicts.

## V8 Execution Results

- Codex tokens: 516,746
- Files modified: 99 (23 scripts + 56 tests + references + config)
- New modules: 10 (enrichment.py, calibration.py, validation.py, models.py, pagination.py, report_status.py, client_profile.py, exceptions.py, formatting.py, __init__.py)
- New tests: 50 files (transport, auth, parser diagnostics, duration, locale, input validation, storage, calibration, enrichment, report status, tracking edge cases, packaging, CLI, integration, live contracts)
- New fixtures: 8 (player_publish_date, player_unplayable, next_error, search_unknown_shape, browse_recognized_empty, search_mixed_known_unknown, player_publish_date_error, player_publish_date_missing)
- CI: .github/workflows/ci.yml + live.yml
- Packaging: pyproject.toml, requirements.txt, MANIFEST.in
- Final: 146 passed, 1 skipped, 0 failed (0.72s)

## Key Technical Decisions in V8

1. **Publish-date enrichment**: `/player` microformat call for each video to get ISO date. Failed enrichment → `publish_date=None`, retain `published_raw`, status `partial`.
2. **Parser diagnostics**: `recognized_container`, `candidate_nodes`, `parsed_nodes`, `unknown_renderer_types` in metadata. Unrecognized HTTP-200 = `unsupported`.
3. **Dependency reducer**: `report_status.py` — truth table for combining required/optional dependency statuses. No silent `ok` from unavailable inputs.
4. **Calibration validation**: `jsonschema` library + semantic checks (training_query_count >= 200, strictly increasing thresholds ending at 100, finite coefficients, provenance fields).
5. **Growth safety**: Distinct snapshot IDs + minimum 15-minute observed interval. Single snapshot = `partial`/`empty`.
6. **Packaging**: `pyproject.toml` with setuptools, `requests>=2.32` + `jsonschema>=4.23` deps. Relative imports. `scripts/__init__.py`.

## Known Issue: created_by Reset

When Codex rewrites SKILL.md during execution, it removes `created_by: agent` from frontmatter, setting it to `None`. This makes the skill "manually authored" and blocks future `skill_manage` patch/edit operations. Workaround: delete + recreate with `skill_manage action=create`, but this risks losing the skill directory. Best practice: after Codex execution, check SKILL.md frontmatter and recreate if needed.

## V9 Review Results (2026-07-27)

- V9 score: 7.3/10 (up from V8's 6.8)
- 7 new HIGH, 12 MEDIUM, 8 LOW found
- V8 fixes verified: 7 fully fixed, 18 partial (implemented in helper module but not propagated to all consumers)
- Key remaining issues:
  - H1: Reports silently convert partial /next video results into OK
  - H2: Dependency reducer truth-table bug (required partial + no output = empty, should be partial)
  - H3: Trending converts transport errors → unsupported (should be error)
  - H4: Handle-based channel lookup bypasses drift diagnostics
  - H5: Storage failures escape public Result boundaries
  - H6: Competitor tracking ignores partial refresh → stale growth as OK
  - H7: CI fails on clean checkout (packaging test needs artifacts before build)
- ruff check: PASS, ruff format: PASS, mypy scripts: PASS
- Coverage: 90.06% (barely above 90% gate; storage 82%, tracking 83%, video 85%)
- Wheel build + install + import outside repo: PASS

## Live Test Results (2026-07-27, post-V8)

CRITICAL: 146/146 unit tests pass but live API tests reveal 3 broken features:

| Feature | V7 (pre-refactor) | V8 (post-refactor) | Root Cause |
|---|---|---|---|
| video_info | Working | BROKEN (UNPLAYABLE) | playabilityStatus check too strict — all videos report UNPLAYABLE |
| autocomplete | Working (14 suggestions) | BROKEN (JSONP parse) | GET params change broke response format |
| trending | Working (VN region) | BROKEN (unsupported) | Transport errors → unsupported instead of error |
| search | Working (40 items, 4 pages) | PARTIAL (15/20) | Parser coverage incomplete (channelRenderer, gridShelfViewModel unknown) |
| channel_info | Working (825K subs) | Working (825K subs) | OK |
| keyword signals | Working (features returned) | EMPTY (0 eligible) | Enrichment failed → no ISO publish_date → all excluded as invalid_views_or_age |
| keyword report | Working (206 chars) | PARTIAL (0 analyzed) | All dependencies degraded |

### Lesson: Unit tests with mocked fixtures do NOT catch live API regressions

V8 added 126 new tests, all passing. But every test uses `ScriptedClient` with canned JSON fixtures.
When the code hits the real YouTube API, the response shape and playabilityStatus fields differ
from fixture assumptions. ALWAYS run live integration tests after a major Codex refactor.

### Search volume is NOT available

YouTube hides search volume. InnerTube API does NOT expose demand data. Only YouTube Studio
(channel owner) or Google Trends API has search volume. This is a known limitation, not a bug.

### Context path requirement

After V8, `DEFAULT_CONTEXT_PATH` is empty. Must pass `context_path` explicitly:
```python
yt = YouTubeResearch(authenticated=True, context_path=r"C:\Users\thang\Downloads\_projects\hermes-chrome-extension\yt_context.json")
```

### Import pattern after V8

V8 changed to relative imports. Must import as package:
```python
import sys
sys.path.insert(0, r"C:\Users\thang\AppData\Local\hermes\skills\youtube-research")
from scripts.youtube_research import YouTubeResearch
```
NOT `sys.path.insert(0, ".../scripts")` — that breaks with relative imports.

## Diminishing Returns Analysis (V1→V9)

Score progression: V1=3 → V4=6 → V7=7.4 → V8=6.8 → V9=7.3

Score can DECREASE between rounds (V7→V8) when reviewer goes deeper — not regression, just deeper inspection finding silent failures missed before.

3 structural reasons why 10/10 is hard to reach:
1. **Regression**: Each fix round creates new bugs. 31 fixes → 27 new issues. New module report_status.py → truth-table bug. New enrichment.py → keyword report discards enriched date. New storage abstraction → in-memory mode broken.
2. **Partial propagation**: Fix implemented in helper module but not propagated to ALL consumers. Parser diagnostics: search/channel OK, handle path MISSING. Input validation: main collectors OK, browse/tracking MISSING. Format 180s: outlier/keyword OK, retention still 300s.
3. **Codebase bloat**: 3663 → 7109 lines in one round. 13 → 23 scripts, 20 → 146 tests. Coupling increases. Codex can't verify every consumer within token budget.

**Decision framework**: Stop when score stabilizes (7-8/10 across 2+ rounds) AND known issues are edge cases (handle lookup, in-memory SQLite, CI ordering) that don't affect live usage. Continue only if HIGH issues break core functionality (search, video_info, autocomplete broken in live test).

## Final Packaging (2026-07-27)

Skill packaged as V9 final:
- 23 scripts (~5000 lines), 56 test files (146 tests), 16 fixtures, 6 references
- pyproject.toml, requirements.txt, CI workflows, MANIFEST.in
- SKILL.md rewritten with accurate docs, known issues, full file map
- All review files, plan files, pycache, build artifacts deleted
- Git commit: d70ee3e
- Path: C:\Users\thang\AppData\Local\hermes\skills\youtube-research\
