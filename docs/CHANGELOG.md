# 变更日志 (Changelog)

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

---

## [7.0.13] — 2026-05-13

### Bug修复：进化周期执行动作持久化

**问题**：`evolution_run_cycle` 执行5个动作后，动作详情未写入 `evolution_actions` 表，导致审计查询只能看到周期概要，无法回溯具体动作。

**根因**：
1. `execute()` 阶段执行动作后未调用 `EvolutionAuditor.record_action()` 持久化
2. `run_full_cycle()` 返回的 `phases.execute` 中丢失了 `actions` 列表
3. `_make_dynamic_handler` 中 `del sys.modules[k]` 可能 KeyError 导致 try 块静默失败，fallback 到旧代码

**修复**：
- `execute()` 内部新增 `_persist_actions()` 方法，执行后立即写入 `evolution_actions` 表，绕过 `_audit_cycle` 的缓存问题
- `run_full_cycle()` 中 `phases.execute` 保留完整 `actions` 列表供审计使用
- `_audit_cycle()` 补设 actions 的 cycle_id 并批量写入
- `_make_dynamic_handler` 中 `del` → `sys.modules.pop(k, None)` 防 KeyError，清除范围扩大为所有 `evolution.*` 子模块

### 改进：feedback 去重

- `feedback()` 阶段检查最近经验中是否已存在相同 `task_id`，避免重复记录

---

## [7.0.1] — 2026-05-11

### Bug修复：pip install 一键部署

**问题**：pip install 后插件文件在 site-packages 但未部署到 ~/.hermes/plugins/，用户必须手动运行 `hermes-evolution setup`。

**修复**：CLI 懒部署 — 首次运行任何命令时自动检测并部署插件。用户 pip install 后直接使用，无需额外操作。

---

## [7.0.0] — 2026-05-11

### V7: 数据消费闭环 + prompt 注入

详见 docs/v7_plan.md

---

## [5.0.0] — 2026-05-11

### V4→V5: 架构优化 + DFX 工程化

#### 架构优化
- **Hermes 原生对齐**: 复用 registry.register()/hermes mcp serve/hermes doctor/plugin.yaml
- **消除镜像重复**: hermes-plugin 与 _plugin → plugin_core.py 单源
- **DatabasePool**: 统一连接池替代裸 sqlite3.connect()
- **WAL 7db 全覆盖**: checkpoint 零调用→全部覆盖
- **状态机编排**: 线性链→中断恢复
- **记忆分层**: 无界→LRU+FTS5

#### DFX 工程化
- 8 维 DFX 审视完成
- 业界 6 大框架对标
- 代码净减 375 行

---

## [3.0.6] — 2026-05-09

### 迭代 10: 自进化审计器 (Iteration 10)

#### 新增 (Added)

**EvolutionAuditor 自进化审计器** (`closed_loop/evolution_auditor.py`, ~350 行):
- **双表记录**:
  - `evolution_cycles` 表: 记录每次进化的完整元数据（6 阶段状态、健康分变化、问题/动作/改进计数）
  - `evolution_actions` 表: 记录每个进化动作的详情（类型、目标、变更状态、时间戳）
- **4 个查询接口**:
  - `record_cycle()`: 在 `run_full_cycle()` 末尾自动持久化进化周期
  - `query_cycles(limit, days, success_only)`: 按时间/状态查询进化历史
  - `get_cycle_detail(cycle_id)`: 单次进化的完整详情（含 phases + actions）
  - `get_summary(days)`: 统计汇总（成功率、健康分趋势、常见动作类型、按周趋势）
  - `get_latest_health_trend(limit)`: 最近 N 次健康分变化曲线

**集成**:
- `orchestrator.run_full_cycle()`: 自动记录审计数据（失败不影响主流程）
- `hermes-plugin`: 新增 `_get_evolution_auditor()` 单例
- `_handle_self_monitor(include_history=True)`: 返回中附加 `audit_summary`
- 新工具 `evolution_audit`: 向 Hermes Agent 暴露审计查询能力

**测试**:
- 新增 `test_evolution_auditor.py` (11 个测试) — 覆盖双表 CRUD、查询过滤、汇总统计
- 全量测试: **439 / 439 通过** (100%)

**文档全面重构**:
- README.md: 全中文重写，v3.0.6 badge，10 个子系统简介，迭代时间线表格
- CHANGELOG.md: 补充 v3.0.5/v3.0.6 完整变更
- CONTRIBUTING.md: 更新项目结构，统一 439 passed

---

## [5.0.0] — 2026-05-11

### V4→V5: 架构优化 + DFX 工程化

#### 架构优化 (V4 Phase)
- **Hermes 原生对齐**: 复用 registry.register()、hermes mcp serve、hermes doctor、plugin.yaml，不自建框架
- **消除镜像重复**: hermes-plugin 与 _plugin 1908行镜像 → plugin_core.py 单源 ~920行
- **DatabasePool**: 统一连接池，替代 4处裸 sqlite3.connect()
- **WAL checkpoint 7db全覆盖**: auto_checkpoint_if_needed() 零调用→全部7个db覆盖
- **retry_on_db_error**: 已实现零使用→全部关键路径接入
- **状态机编排**: 闭环编排硬编码 Phase 1→6 线性链→状态机支持中断恢复
- **记忆分层**: _experiences_cache 无界增长→LRU+FTS5 分层管理
- **Schema 版本化**: DDL 迁移管理 schema_migrations.py
- **输入验证**: InputValidator 统一校验层
- **安全加固**: 飞书 App ID 脱敏 + 日志签名防篡改

#### DFX 工程化 (V4-V5)
- **DFX 8 维审视**: 可靠性/可用性/性能/安全/可维护性/可观测性/可测试性/可扩展性全面审计
- **业界对标**: 6 大框架 (LangChain/AutoGPT/Open Interpreter/CrewAI/Home Assistant/n8n) 设计模式分析
- **代码精简**: -2045行/+1670行，净减375行，消除所有重复函数
- **测试**: 439/439 全通过

#### 迭代 1-10 回顾
- 迭代 1-5: V1/V2/V3 融合架构 (7 子系统 28 模块)
- 迭代 6: Hermes Agent 集成 (daemon/plugin/feishu)
- 迭代 7: API 同步守卫 (dependency_manager)
- 迭代 8: P0 修复 + 数据治理 (WAL checkpoint + cleanup)
- 迭代 9: ToolStrategyLearner 持久化
- 迭代 10: EvolutionAuditor 自进化审计器

---


## [3.0.5] — 2026-05-09

### 迭代 9: ToolStrategyLearner 持久化 (Iteration 9)

#### 新增 (Added)

**ToolStrategyLearner SQLite 持久化**:
- `tool_strategy_learner.py` 新增 `_init_db()` / `_load_from_db()` / `_persist_usage()` 三个方法
- `tool_usage_history` 表: 记录每次工具调用的成功/失败/耗时，含索引
- 启动时自动从 DB 加载最近 7 天历史数据重建内存状态
- `record_tool_usage()` 同步写入 DB，解决网关重启后数据丢失问题

**post_tool_call hook 双向记录**:
- `_on_post_tool_call` 新增调用 `strategy_learner.record_tool_usage()` — 策略学习记录
- 新增调用 `tool_performance_analyzer.record_performance()` — 性能分析记录
- 新增 `_get_strategy_learner()` 辅助函数
- 实现策略层 + 性能层的双向数据采集

**版本号同步 9 文件**:
- 全项目版本号统一为 v3.0.5: `__init__.py`、`README.md`、`plugin.yaml`（两处）、`Makefile`、`setup.py`、`CONTRIBUTING.md`、`docs/CONFIGURATION.md`、`CHANGELOG.md`

#### 修复 (Fixed)

- `_count_tools_from_db()` 裸 `sqlite3.connect` 改为 `get_evolution_db()` — 统一连接管理

---

## [3.0.4] — 2026-05-09

### 迭代 7–8: 插件部署审计修复

#### 修复 (Fixed)

**P0 — 健康评分始终为 0/100:**
- `self_monitor.py` L168: `analyze_recent_experiences(days=1)` → `days=7`
  - 根因: 网关重启后仅 1 条当天经验 (failure)，days=1 过滤导致 success_rate=0%
  - 修复: 窗口扩大至 7 天，充分利用历史 121 条经验数据
- `self_monitor.py` 新增 `_count_tools_from_db()` 方法
  - 根因: `ToolStrategyLearner` 纯内存无持久化，重启后 `get_tool_performance_summary()` 返回空
  - 回退方案: 策略学习器为空时从 `tools.db` 直接统计工具数（当前 32 个）
- `plugin/__init__.py` `_handle_self_monitor`: 绕过 SelfMonitor，直接计算健康评分
  - 新增 `_get_experience_analyzer()` 辅助函数
  - 评分公式: success_score(0.5) + experience_score(0.3) + tool_diversity_score(0.2)
  - 预期效果: 健康评分从 0/100 → ~55/100 (needs_attention)

**P1 — associations.db 膨胀至 1.3GB:**
- 清空 826 个测试残留 db 文件（test_audit_*.db + tmp*.db），回收 ~1.3GB
- `~/.hermes/data/evolution/` 从 848 文件缩至 22 文件
- 注意: 空间需等进程释放文件句柄后回收（下次重启生效）

**P1 — 工具性能数据缺失:**
- 32 个注册工具中 28 个显示"尚无性能数据"
- 仅 metric_tool(100)、search_data(91.4)、test_tool(80)、perf_tool(75.6) 有评分
- 原因: 均为测试数据，生产环境尚无实际工具调用记录

**P2 — ~/.hermes/plugins/data/ 数据库残留:**
- 4 个 db 文件 (300KB)，仅 1 条经验 0 工具 — 实际插件使用 `~/.hermes/data/evolution/`
- 已识别为清理目标（非紧急）

#### 已知问题 (Known Issues)
- 健康评分修复代码已就绪，但 gateway 工具调度缓存导致 handler 未即时生效
- 需等 Hermes 全量重启（含 pyc 清理）后验证

#### 修复 (持续推进)
- **orchestrator.py Feedback 导入重复 bug**: `feedback()` 方法 try/except 两条分支导入路径完全一致，except 分支修正为 `from src.evolution.learning.experience import ...`
- **插件版本号同步**: `hermes-plugin/plugin.yaml` + `src/evolution/_plugin/plugin.yaml` v3.0.3 → v3.0.4
- **文档版本号同步**: `docs/CONFIGURATION.md` + `README.md` badge v3.0.3 → v3.0.4
- **数据目录清理**: 删除 388 个测试残留临时文件（tmp*db-shm/wal + test_*.db）
- **associations.db WAL 压缩**: WAL checkpoint 将 4.1GB WAL 文件归零，节省 3.9GB
- **测试**: 428/428 全通过 (26.75s)

---

## [3.0.3] — 2026-05-07

### 迭代 6: 工具补全与文档建设

#### 新增 (Added)
- **docs/LOGGING.md** (174 行) — 日志框架使用指南: Logger 层级、API 参考、便捷函数、最佳实践
- **docs/CONFIGURATION.md** (153 行) — 配置参数表: 环境变量、DB 文件说明、开发/CI/生产场景
- **docs/QUICKSTART.md** (161 行) — 5 分钟上手: pip 安装→自检→部署→API 示例→FAQ
- **docs/RELEASE_CHECKLIST.md** (117 行) — 发版检查清单: 代码/版本/包/插件/CI/Docker 全覆盖

#### 修复 (Fixed)
- `enhanced_tool_creator.py` 3 个 TODO 空壳函数替换为可用实现:
  - L313: `create_from_config` 支持 `module_path`/`function_name` 动态加载函数
  - L695: `_generate_api_code` 实现 `urllib.error` 真实 API 调用（替代 NotImplementedError）
  - L805: `_get_template` 默认模板改为带日志的通用工具
- `tests/test_iteration6_integration.py` MockCtx.register_tool 签名添加 `toolset` 参数 — 修复 hermes-plugin 新增 toolset 关键字调用后 11 个测试失败
- 全项目版本号同步: `__init__.py` / `README.md` / `plugin.yaml` / `install.sh` / `Makefile` / `CONTRIBUTING.md` / `docs/CONFIGURATION.md` → 统一 v3.0.3

---

## [3.0.2] — 2026-05-07

#### 修复 (Fixed)
- 远程仓库与本地同步 (fc36e85)
- `hermes-evolution check` 自检通过验证

---

## [3.0.1] — 2026-05-06

#### 新增 (Added)
- CI/CD: `.github/workflows/ci.yml` (Python 3.9–3.13 matrix + lint + build)
- pre-commit: `.pre-commit-config.yaml` (ruff + pytest)
- `logging_config.py` — 统一日志框架 (`setup_logging` / `get_logger` / 便捷函数)

#### 变更 (Changed)
- README.md 重写 (195 行, 全中文, V3 融合架构, 5 秒安装, 项目状态表)
- docs/INSTALLATION.md 刷新 (704 行, pip/插件/Docker 三路径)
- docs/ARCHITECTURE.md 刷新 (620 行, V3 融合架构图 + fusion 桥说明)
- CONTRIBUTING.md 重写 (320 行, 环境搭建/代码规范/测试要求/PR 流程)
- CHANGELOG.md 补全 (v3.0.0 完整变更日志)

#### 修复 (Fixed)
- README badge: 374→422 passed
- DB 路径修复: 422/422 测试全通过 (100%)
- setup.py 版本 v2.0.0→v3.0.1

---

## [3.0.0] — 2026-05-06

### 迭代 1–5: V1/V2/V3 融合架构

#### 新增 (Added)

**融合架构 (V1+V2+V3):**
- **`fusion/` 桥接层** — V1 单体 ↔ V2 微服务双向桥接
  - `fusion/bridge.py` — `V1V2Bridge` 事件转换、服务映射、数据格式转换
  - `fusion/compatibility.py` — 兼容层、枚举映射、API 网关、服务降级、版本检测
  - `fusion/unified_entry.py` — `UnifiedAgent` 统一入口，支持 V1_ONLY / V2_ONLY / HYBRID 三种模式

**CLI 命令行工具:**
- **`hermes-evolution` CLI** — 通过 `pyproject.toml [project.scripts]` 注册
  - `hermes-evolution check` — 环境自检
  - `hermes-evolution setup` — 一键部署 Hermes 插件
  - `hermes-evolution status` — 系统状态
  - `hermes-evolution test` — 运行测试

**DB 路径隔离:**
- **`db_utils.py`** — WAL 模式 + busy_timeout + 线程安全缓存 + 路径解析 (`EVOLUTION_DATA_DIR`)

**日志统一:**
- Python `logging` 模块 + LOG_LEVEL 环境变量

**工程化:**
- Makefile (13 命令) + pyproject.toml + 可选依赖分组 (dev/full/v2)

#### 变更 (Changed)
- **版本号**: 2.0.0 → 3.0.0
- **架构**: 单体 → V1/V2/V3 融合架构
- **DB 路径**: `data/` → `~/.hermes/data/evolution/`
- **日志**: print → logging 模块
- **安装**: `pip install -r` → `pip install -e .`

#### 修复 (Fixed)
- SQLite 并发锁: WAL + busy_timeout + 重试装饰器
- 跨线程安全: `check_same_thread=False`

---

## [2.0.0] — 2026-04-28

#### 新增 (Added)
- Hermes Agent 插件集成 (6 tools + 1 hook)
- pyproject.toml 标准化打包
- 守护进程独立架构: `hermes_daemon.py` (546 行)
- 飞书 OpenAPI 通知器 (webhook/openapi/simulated)
- Cron 定时汇报 (每 2 小时)
- `test_iteration6_integration.py` (27 用例)

---

## [1.5.0] — 2026-04-28

#### 新增 (Added)
- 闭环自主进化守护进程 (`closed_loop/` 4 模块)
- 飞书通知修复 + Cron 汇报

---

## [1.4.0] — 2026-04-26

#### 新增 (Added)
- 安全模块 (`security/` 4 模块)
- 协作引擎 (`collaboration/` 4 模块)
- V1/V2 融合层 (`fusion/` 3 模块)
- 测试覆盖: 253/253 全通过

---

## [1.3.0] — 2026-04-26

#### 新增 (Added)
- 工具能力进化 (`tools/` 5 模块)

---

## [1.2.0] — 2026-04-26

#### 新增 (Added)
- 学习与记忆模块 (`learning/` + `memory/` + `self_monitor`)

---

## [1.0.0] — 2026-04-26

#### 新增 (Added)
- 初始发布: HermesAgentEvolution V1+V2
