# Changelog

All notable changes to HermesAgentEvolution will be documented in this file.

## [6.0.0] - 2026-05-11

### Critical Fix: OOM Prevention
- **Root Cause**: `evolution_memory_discover` with no `entry_id` triggered `discover_all()` — N×N semantic pairing across all 4,593 memory entries produced ~10.5M Jaccard comparisons, generating 2.07M associations in a single transaction. Memory peaked at 14.8GB, triggering OOM Kill.
- **Database Cleanup**: `associations.db` reduced from 961MB (2.07M rows) → 49MB (100K rows) via manual cleanup + VACUUM.

### Changed
- `discover_all()` now requires `max_entries` parameter (default 200, hard cap 500) to prevent N×N combinatorial explosion
- `_fetch_all_entries()` supports `LIMIT` clause, fetching most recently updated entries first
- `TOOL_MEMORY_DISCOVER_SCHEMA` now includes `max_entries` field (integer, 1-500, default 200)
- `_handle_memory_discover()` passes `max_entries` through to `discover_all()`

### Version
- Bumped from 5.0.0 → 6.0.0

## [5.0.0] - 2026-05-11

### Architecture Optimization (V4)
- Eliminated mirror code: unified `hermes-plugin/__init__.py` and `src/evolution/_plugin/__init__.py` into single `plugin_core.py`
- Unified `db_utils.py` as single-source database layer with DatabasePool
- Aligned with Hermes native: `registry.register()`, `hermes doctor`, `plugin.yaml`, `post_tool_call` hook
- Removed independent framework reinventions (custom MCP, health checks, middleware pipeline)

## [3.0.4] - 2026-05-09

### Iteration 8 Fixes
- Fixed health score system: `self_monitor.py` days window 1→7, added `_count_tools_from_db()` fallback
- Database cleanup: removed 826 test-residue db files (~1.3GB recovered)
- Fixed `evolution_create_tool` parameter mismatch (removed extra `description`/`tags`)
- Fixed `evolution_run_cycle` feedback phase `from src.xxx` import error

## [3.0.2] - 2026-05-07

### Initial PyPI Release
- First published to PyPI as `hermes-agent-evolution`
- CLI command: `hermes-evolution` (check/setup/status/test)
- 422 tests passing, 7 tools + 1 hook registered
