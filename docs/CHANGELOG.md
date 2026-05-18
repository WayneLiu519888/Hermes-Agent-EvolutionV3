# 变更日志 (Changelog)

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

---

## [9.0.0] — 2026-05-19

### 新增 — 同Session实时自进化闭环

基于 `analysis_01_realtime_self_evolution_closed_loop.md` 架构分析，实现5方案：

- **方案A: 同步知识提取** — `_sync_extract_knowledge()` 规则引擎，post_llm_call后零延迟提取关键知识点写入memory_entries，当前session立即可用
- **方案B: 洞察注入器** — 新增 `insight_injector.py`，将ClosedLoopOrchestrator的产出（模式/策略/趋势）注入pre_llm_call上下文
- **方案C: 会话状态机** — 新增 `session_state.py`，追踪当前session对话状态（话题/错误/重复提问/困惑），情境感知注入
- **方案D: 语义匹配** — 新增 `embedding_matcher.py`，TF-IDF向量化为inject_context提供第4阶段语义匹配（numpy不可用时自动降级Jaccard）
- **方案E: 自适应注入** — 新增 `adaptive_policy.py`，根据context_injection_logs历史采纳率动态调整注入量和策略

**架构**: 新增3模块（insight_injector / session_state / embedding_matcher / adaptive_policy），修改2文件（plugin_core / consumer），~800行代码。

---

## [8.0.18] — 2026-05-17

### 修复

- **post_tool_call 打通 tool_usage_history** — `_on_post_tool_call` hook 新增 `tools.db → tool_usage_history` 直写逻辑，消除 learning_experiences 与 tool_usage_history 两套追踪系统割裂。修复后 post_tool_call 每次工具调用自动写入成功率数据，`hae audit issues` 不再报 `low_success_rate: 0.0%`（v8.0.3 清空54157条脏数据后无新记录流入的遗留问题）

---

## [8.0.17] — 2026-05-17

### 改进

- **`hae cycle status` 表格化** — 从一行摘要改为展示最近20条周期表格（同 `hae cycle history` 格式）+ 一句总结（最新周期状态、OK/FAIL统计、累计问题、平均耗时）

---

## [8.0.16] — 2026-05-17

### 修复

- **`hae test` pip 安装兼容** — `cmd_test()` 不再依赖 `_project_root` 固定路径，改为多路查找 `tests/`，找不到时给出清晰提示 `git clone` 而非报 `ERROR: file or directory not found`

---

## [8.0.15] — 2026-05-17

### 改进

- **`hae log` 表格化** — 日志输出从纯文本改为表格，按时间/级别/来源/内容 4 列展示

---

## [8.0.14] — 2026-05-17

### 改进

- **`hae cycle detail` 表格化** — 完整展示周期所有字段（健康/成功率/工具/经验前后值、问题详情含严重度图标、模式详情含置信度条）
- **`hae audit trend` 表格化** — 健康分数可视化进度条 + 成功率/问题/动作/模式/改进趋势

---

## [8.0.13] — 2026-05-17

### 新增

- **`hae demo` 演示环境模块** — 三位一体命令：
  - `hae demo install` — 部署 demo DB（5工具/50经验/3周期/12动作），含演进数据
  - `hae demo status` — 查看 PROD/DEMO 模式
  - `hae demo uninstall` — 一键清除
- **`get_data_dir()` demo 切换** — 检测 `.demo_mode` 标记自动切路径，生产/demo DB 完全隔离
- **`tools.db` 清理** — 移除 5 个 demo 工具（add_numbers/add_tool/add_with_logging/api_func/broken_tool）

### 由繁入简

Demo CLI 采用功能完善的第一版方案（独立命令组），待验证后做简洁优化。

---

## [8.0.12] — 2026-05-17

### 改进

- **`hae audit cycles` 表格化** — 输出格式从文本行改为表格，含 ID/时间/状态/问题/动作/健康/模式/耗时 8 列

---

## [8.0.11] — 2026-05-17

### 改进

- **`hae audit summary` 表格化** — 输出格式从单行汇总改为完整表单，含 17 个维度（周期/健康/问题/动作）

---

## [8.0.10] — 2026-05-16

### 修复

- **`ToolRegistry` 参数类型错误** — `tool_integration.py` L84 `ToolStrategyLearner(self.registry)` → `ToolStrategyLearner(self.registry.db_path)`，消除 `startswith` 报错，学习模块恢复正常
- **FOREIGN KEY 断裂** — 删除 `_persist_actions`（随机 cycle_id）和分散的 `_audit_action`（cycle_id=None），actions 统一由 `_audit_cycle` 写入
- **actions 入口统一** — execute 阶段不再独立写 actions，与 cycle 审计保持同一 cycle_id

---

## [8.0.9] — 2026-05-16

### 修复

- **`_count_tools_from_db` 相对导入 bug** — `from ..db_utils` → `from evolution.db_utils`，tools_count 从 0 修正为 29，health_score 从 50 修正为 70

---

## [8.0.8] — 2026-05-16

### 修复

- **`health_score` 审计写入** — `SelfMonitor.monitor_and_improve()` 新增 `health_score` 输出，`_audit_cycle` 提取写入审计 DB
- **`tools_count` 审计写入** — `monitor_and_improve()` 新增 `tools_count` 输出

### health_score 公式

```
health_score = success_rate×50 + experiences×0.6 + tools×4
             (成功率权重0.5, 经验权重0.3, 工具多样性权重0.2, 均归一到0-100)
```

---

## [8.0.7] — 2026-05-16

### 修复

- **health 提取路径对齐** — 根据 `SelfMonitor.monitor_and_improve()` 实际返回结构修正字段路径
- health_score 暂空（当前 SelfMonitor 未输出），success_rate/experiences 正确提取

---

## [8.0.6] — 2026-05-16

### 修复

- **`health_score` 提取路径修正** — `_audit_cycle` 从 `health` 顶层取 `health_score`，不再嵌套 `analysis` 层
- **`duration_ms` is-not-None 修复** — `0.0 if 0.0 else 0` → `val if val is not None else 0`，彻底解决 falsy 截断

---

## [8.0.5] — 2026-05-16

### 修复

- **`duration_ms` falsy bug** — `(0.0 or 0)*1000` → `(val if val else 0)*1000`，短周期不再丢 duration
- **health/success_rate 写入** — `_audit_cycle` 从 `analysis._details` 提取 health 指标传给 `record_cycle`
- **审计字段补全** — health_score/success_rate/tools_count/experiences 前后值现在正确写入

---

## [8.0.4] — 2026-05-15

### 修复

- **审计写入统一入口** — `EvolutionAuditor.record_cycle()` 使用 `_next_cycle_id()` DB 自增，不再依赖内存 `cycle_history` 计数器
- **消除双重写入** — 删除 `_handle_run_cycle` 中的直写 SQL（原 V8.0.0 绕过模块缓存方案），审计完全由 `EvolutionAuditor` 负责
- **`duration_ms` 修复** — `record_cycle()` 使用 `(result['duration'] or 0) * 1000`，不再为 0
- **补全审计字段** — `record_cycle()` 已写满 28 个字段（含 health_score/success_rate），之前因 cycle_id 始终=1 被覆盖
- **学习经验清空** — `learning_experiences.db` 7875 条测试遗留经验已清空，PatternRecognizer 不再基于脏数据

### 架构变更

```
旧: _handle_run_cycle ─直写SQL(不完整)→ evolution_audit.db
    run_full_cycle ─_audit_cycle→ EvolutionAuditor(完整, 但 cycle_id=1)

新: _handle_run_cycle → orch.run_full_cycle → _audit_cycle → EvolutionAuditor(完整 + 自增ID)
    唯一写入路径，28 字段全量
```

---

## [8.0.3] — 2026-05-15

### 修复

- **`action_executor` 假数据写入移除** — `_execute_strategy_switch()` 不再向 search_files/terminal/read_file/write_file 伪造 success=True 记录，消除 tool_usage_history 污染
- **`tool_usage_history` 表清空** — 删除 54,157 条假数据（策略切换伪造 + 旧版本测试残留），工具成功率从失真恢复
- **`search_files` 假 issue 清除** — evolution_audit.db 中 search_files 相关的 tool_low_performance 已移除

### 根因分析

search_files 成功率 14.3% 的假告警链路：
1. `action_executor._execute_strategy_switch()` 每周期往 tool_usage_history 伪造工具使用记录
2. `ToolStrategyLearner._load_from_db()` 加载脏数据计算成功率
3. `orchestrator._analyze_phase()` 生成 tool_low_performance issue
4. 旧版本遗留 1037 条 search_files 失败记录 + 173 条伪造成功 = 14.3% 失真

---

## [8.0.2] — 2026-05-15

### 修复

- **`__version__` 同步** — `src/evolution/__init__.py` 版本号 8.0.0→8.0.1（此前发布漏同步）
- **`hae status` pip 兼容** — 版本读取改用 `__version__`，模块统计从包安装路径读取，不再依赖 `_project_root`/`pyproject.toml`

---

## [8.0.1] — 2026-05-15

### 修复

- **`hae status` 超时修复** — 移除 `cmd_status()` 中的 pytest 全量测试调用，改为轻量级测试文件计数，秒级返回

---

## [8.0.0] — 2026-05-15

### 🚀 重大更新：打破壁垒，统一环境，全新命令体系

#### 核心改进

- **A: 打破三层缓存** — `_make_dynamic_handler` 每次调用 reload 模块，改代码重启即生效
- **B: 进化周期真实性** — 确认六阶段真实执行，analyze 每次产出不同数据
- **C: Python 环境统一** — gateway 改用系统 Python 3.12，`pip install` 一步到位，不再手动 cp 同步
- **D: 数据闭环** — 审计追溯端到端打通（`issues_details` 持久化），hermes memory 桥接正常
- **E: 版本发布自动化** — `scripts/release.sh` 一键：版本同步→冒烟→pytest→commit→build→PyPI
- **F: `hae uninstall`** — 7层清理，`--dry-run`/`--keep-data`/`--force`
- **G: 简化指令 `HAE`** — `hermes-evolution` + `hae` 双入口
- **H: 完整命令体系** — 10命令/28子命令 + 三级 help 系统

#### 新增 CLI 命令

```
hae install / uninstall     部署 / 卸载
hae check / status / version
hae test                     测试
hae db info|clean|vacuum|backup
hae cycle run|status|history|detail
hae audit summary|cycles|detail|issues|trend
hae log / config show|doctor|validate
```

#### 技术细节

- `_handle_run_cycle` 中直接 sqlite3 写入审计，绕过 gateway 模块缓存
- `EvolutionAuditor` 新增 `_next_cycle_id()` 方法
- systemd unit ExecStart → `/usr/bin/python3`，PYTHONPATH 指向 hermes-agent
- `pyproject.toml` 新增 `hae` 入口点

---

## [7.0.16] — 2026-05-14

### Bug修复

- **`EvolutionAuditor` 使用相对路径导致审计数据写入错误位置**
  - 根因：`_audit_cycle`、`_persist_actions`、`_audit_action` 三处 `EvolutionAuditor()` 使用默认相对路径 `"evolution_audit.db"`，workdir 不同时写到错误位置
  - 修复：三处全部改为 `EvolutionAuditor(db_path=str(get_data_dir() / "evolution_audit.db"))`

### 改进
- 版本号统一 7.0.16

---

## [7.0.15] — 2026-05-14

### Bug修复

- **`evolution_analyze_performance` 无参调用缺少 `success` 字段**
  - 根因：不传 `tool_name` 时走 `generate_performance_report("json")` 分支，返回 `{"report_generated": ..., "summaries": ...}`，未包裹 `success` 字段，与其它工具返回格式不一致
  - 修复：`_handle_analyze_performance` else 分支解析 JSON 后包裹 `{"success": true, ...}`；同时 `tool_name` 分支也统一补上 `success` 字段
  - 文件：`src/evolution/plugin_core.py` L149-168

- **`TOOL_AUDIT_SCHEMA` 缩进错误（V7.0.14 引入）**
  - 根因：V7.0.14 修改 audit schema 时 patch 误加了 4 格缩进，导致常量嵌套定义，模块顶层不可见，27 个集成测试 import 阶段报 `NameError`
  - 修复：恢复模块顶层定义

### 改进
- 版本号统一：`pyproject.toml` / `setup.py` / `__init__.py` 全部 7.0.15

---

## [7.0.14] — 2026-05-14

### 新增：进化审计问题追溯（三层升级）

**问题**：`evolution_audit` 只记录统计数字（issues_found=3），不保存问题详情（什么问题、什么严重程度、影响哪个工具），导致事后无法追溯。

**层级一（最小改动）**：
- `run_full_cycle()` 的 `phases.analyze` 新增 `_details` 字段，保留完整分析结果
- `record_cycle()` 从 `_details` 提取 issues/patterns 序列化存入 `notes` 列

**层级二（规范化存储）**：
- `evolution_cycles` 表新增 `issues_details TEXT` 和 `patterns_details TEXT` 列
- `_init_db()` 新增 `ALTER TABLE` 兼容迁移（旧数据库自动升级）
- `record_cycle()` 分别写入 `issues_details` / `patterns_details` / `notes` 三列
- `get_cycle_detail()` 返回新增 `analysis_details` 字段（含 issues + patterns 解析后数组）

**层级三（可查询追溯）**：
- `EvolutionAuditor` 新增三个查询方法：
  - `get_latest_issues(limit)` — 获取最近发现问题详情
  - `query_issues_by_type(issue_type, days)` — 按类型筛选
  - `query_issues_by_severity(severity, days)` — 按严重程度筛选
- `evolution_audit` tool 新增三个 action：
  - `get_recent_issues` — 最近问题
  - `query_issues_by_type` — 按类型查
  - `query_issues_by_severity` — 按严重程度查

### 改进
- 版本号统一：`pyproject.toml` / `setup.py` / `__init__.py` 全部同步到 7.0.14

---

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

### Bug修复：evolution_recall_lessons 静默返回空列表

**问题**：`evolution_recall_lessons` 始终返回空列表，即使经验库中有多条 failure 记录。

**根因（三重断裂）**：
1. SQL 列名不匹配 — 查询用 `content`/`lessons`，表实际列名为 `description`/`lessons_learned`
2. db_pool 方法名错误 — 调用 `get_connection()` 但实际方法是 `connection()`，返回上下文管理器而非连接对象
3. 异常被 `except Exception` 静默吞没，返回空列表无任何告警

**修复**：
- `consumer.py` `recall_lessons()`: SQL 改用 `description as content`、`lessons_learned as lessons`
- `consumer.py` 全部 6 处: `get_connection()` → `connection()`，用 `with ... as conn:` 包裹
- 排查发现: Gateway 运行在 Python 3.11 venv，与系统 Python 3.12 路径不同，修复需同步到 `/root/.hermes/hermes-agent/.venv/lib/python3.11/site-packages/evolution/`

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
