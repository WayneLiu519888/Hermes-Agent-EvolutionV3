# 变更日志

HermesAgentEvolution 所有重要变更记录。

## [6.0.0] - 2026-05-11

### 紧急修复：OOM 防护

- **根因**：`evolution_memory_discover` 在不传 `entry_id` 时触发 `discover_all()`，对全部 4593 条记忆条目做 N×N 语义配对（约 1050 万次 Jaccard 比较），单事务生成 207 万条关联记录，内存峰值 14.8GB 触发 OOM Kill。
- **数据库清理**：`associations.db` 从 961MB（207 万行）→ 49MB（10 万行），手动清理 + VACUUM 回收。

### 变更

- `discover_all()` 新增 `max_entries` 参数（默认 200，硬上限 500），防止 N×N 组合爆炸
- `_fetch_all_entries()` 支持 `LIMIT` 子句，优先获取最近更新的条目
- `TOOL_MEMORY_DISCOVER_SCHEMA` 新增 `max_entries` 字段（整数，1-500，默认 200）
- `_handle_memory_discover()` 将 `max_entries` 透传给 `discover_all()`

### 版本

- 从 5.0.0 升级到 6.0.0

## [5.0.0] - 2026-05-11

### 架构优化（V4）

- 消除镜像代码：将 `hermes-plugin/__init__.py` 和 `src/evolution/_plugin/__init__.py` 统一为单一 `plugin_core.py`
- 统一 `db_utils.py` 为单一数据层（DatabasePool）
- 对齐 Hermes 原生能力：`registry.register()`、`hermes doctor`、`plugin.yaml`、`post_tool_call` hook
- 删除独立的框架重建（自建 MCP、健康检查、中间件管道）

## [3.0.4] - 2026-05-09

### 迭代8修复

- 修复健康评分系统：`self_monitor.py` 时间窗口从 1 天改为 7 天，新增 `_count_tools_from_db()` 回退逻辑
- 数据库清理：删除 826 个测试残留 db 文件（回收约 1.3GB）
- 修复 `evolution_create_tool` 参数不匹配（删除多余的 `description`/`tags`）
- 修复 `evolution_run_cycle` feedback 阶段的 `from src.xxx` 导入错误

## [3.0.2] - 2026-05-07

### 首次 PyPI 发布

- 首次发布到 PyPI 为 `hermes-agent-evolution`
- CLI 命令：`hermes-evolution`（check/setup/status/test）
- 422 测试通过，注册 7 工具 + 1 hook
