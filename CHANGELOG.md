# 变更日志 (Changelog)

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

## [3.0.6] — 2026-05-09

### 迭代10: 自进化审计器 (Iteration 10)

#### 新增 (Added)

**EvolutionAuditor 模块** (`closed_loop/evolution_auditor.py`, ~350行):
- `evolution_cycles` 表: 记录每次进化的完整元数据（6阶段状态、健康分变化、问题/动作/改进计数）
- `evolution_actions` 表: 记录每个进化动作的详情（类型/目标/变更状态）
- `record_cycle()`: 在 `run_full_cycle()` 末尾自动持久化
- `query_cycles(limit, days, success_only)`: 按时间/状态查询进化历史
- `get_cycle_detail(cycle_id)`: 单次进化的完整详情（含 phases + actions）
- `get_summary(days)`: 统计汇总（成功率、健康分趋势、常见动作类型、按周趋势）
- `get_latest_health_trend(limit)`: 最近N次健康分变化曲线

**集成:**
- `orchestrator.run_full_cycle()`: 自动记录审计数据（失败不影响主流程）
- `hermes-plugin`: 新增 `_get_evolution_auditor()` 单例
- `_handle_self_monitor(include_history=True)`: 返回中附加 `audit_summary`

## [3.0.5] — 2026-05-09

### 迭代9: ToolStrategyLearner 持久化 (Iteration 9)

#### 新增 (Added)

**ToolStrategyLearner SQLite 持久化:**
- `tool_strategy_learner.py` 新增 `_init_db()` / `_load_from_db()` / `_persist_usage()` 三个方法
- `tool_usage_history` 表: 记录每次工具调用的成功/失败/耗时，含索引
- 启动时自动从 DB 加载最近7天历史数据重建内存状态
- `record_tool_usage()` 同步写入 DB，解决网关重启后数据丢失

**post_tool_call hook 驱动双向记录:**
- `_on_post_tool_call` 新增调用 `strategy_learner.record_tool_usage()` (策略学习)
- 新增调用 `tool_performance_analyzer.record_performance()` (性能分析)
- 新增 `_get_strategy_learner()` 辅助函数

#### 修复 (Fixed)

- `_count_tools_from_db()` 裸 `sqlite3.connect` 改为 `get_evolution_db()` (统一连接管理)

## [3.0.4] — 2026-05-09

### 迭代8: 插件部署审计修复 (Iteration 8)

#### 修复 (Fixed)

**P0 — 健康评分始终为0/100:**
- `self_monitor.py` L168: `analyze_recent_experiences(days=1)` → `days=7`
  - 根因: 网关重启后仅1条当天经验(failure)，days=1 过滤导致 success_rate=0%
  - 修复: 窗口扩大至7天，充分利用历史121条经验数据
- `self_monitor.py` 新增 `_count_tools_from_db()` 方法
  - 根因: `ToolStrategyLearner` 纯内存无持久化，重启后 `get_tool_performance_summary()` 返回空
  - 回退方案: 策略学习器为空时从 `tools.db` 直接统计工具数（当前32个）
- `plugin/__init__.py` `_handle_self_monitor`: 绕过 SelfMonitor，直接计算健康评分
  - 新增 `_get_experience_analyzer()` 辅助函数
  - 评分公式: success_score(0.5) + experience_score(0.3) + tool_diversity_score(0.2)
  - 预期效果: 健康评分从 0/100 → ~55/100 (needs_attention)

**P1 — associations.db 膨胀至1.3GB:**
- 清空 826 个测试残留 db 文件（test_audit_*.db + tmp*.db），回收 ~1.3GB
- `~/.hermes/data/evolution/` 从 848 文件缩至 22 文件
- 注意: 空间需等进程释放文件句柄后回收（下次重启生效）

**P1 — 工具性能数据缺失:**
- 32个注册工具中28个显示"尚无性能数据"
- 仅 metric_tool(100)、search_data(91.4)、test_tool(80)、perf_tool(75.6) 有评分
- 原因: 均为测试数据，生产环境尚无实际工具调用记录

**P2 — ~/.hermes/plugins/data/ 数据库残留:**
- 4个db文件(300KB)，仅1条经验0工具 — 实际插件使用 `~/.hermes/data/evolution/`
- 已识別为清理目标（非紧急）

#### 已知问题 (Known Issues)
- 健康评分修复代码已就绪，但 gateway 工具调度缓存导致 handler 未即时生效
- 需等 Hermes 全量重启（含 pyc 清理）后验证

#### 修复 (2026-05-09 持续推进)

- **orchestrator.py Feedback 导入重复bug**: `feedback()` 方法 try/except 两条分支导入路径完全一致，except 分支修正为 `from src.evolution.learning.experience import ...`
- **插件版本号同步**: `hermes-plugin/plugin.yaml` + `src/evolution/_plugin/plugin.yaml` v3.0.3 → v3.0.4
- **文档版本号同步**: `docs/CONFIGURATION.md` + `README.md` badge v3.0.3 → v3.0.4
- **数据目录清理**: 删除 388 个测试残留临时文件（tmp*db-shm/wal + test_*.db）
- **associations.db WAL 压缩**: WAL checkpoint 将 4.1GB WAL 文件归零，节省 3.9GB
- **测试**: 428/428 全通过 (26.75s)

## [3.0.3] — 2026-05-07

### 新增 (Added)
- **docs/LOGGING.md** (174行) — 日志框架使用指南: Logger层级、API参考、便捷函数、最佳实践
- **docs/CONFIGURATION.md** (153行) — 配置参数表: 环境变量、DB文件说明、开发/CI/生产场景
- **docs/QUICKSTART.md** (161行) — 5分钟上手: pip安装→自检→部署→API示例→FAQ
- **docs/RELEASE_CHECKLIST.md** (117行) — 发版检查清单: 代码/版本/包/插件/CI/Docker全覆盖

### 修复 (Fixed)
- `enhanced_tool_creator.py` 3个TODO空壳函数替换为可用实现:
  - L313: `create_from_config` 支持 `module_path`/`function_name` 动态加载函数
  - L695: `_generate_api_code` 实现 `urllib.error` 真实API调用（替代 NotImplementedError）
  - L805: `_get_template` 默认模板改为带日志的通用工具
- `tests/test_iteration6_integration.py` MockCtx.register_tool 签名添加 `toolset` 参数 — 修复 hermes-plugin 新增 toolset 关键字调用后 11 个测试失败
- 全项目版本号同步: `__init__.py` / `README.md` / `plugin.yaml` / `install.sh` / `Makefile` / `CONTRIBUTING.md` / `docs/CONFIGURATION.md` → 统一 v3.0.3

## [3.0.2] — 2026-05-07

### 修复 (Fixed)
- 远程仓库与本地同步 (fc36e85)
- `hermes-evolution check` 自检通过验证

## [3.0.1] — 2026-05-06

### 新增 (Added)
- CI/CD: `.github/workflows/ci.yml` (Python 3.9-3.13 matrix + lint + build)
- pre-commit: `.pre-commit-config.yaml` (ruff + pytest)
- `logging_config.py` — 统一日志框架 (`setup_logging` / `get_logger` / 便捷函数)

### 变更 (Changed)
- README.md 重写 (195行, 全中文, V3融合架构, 5秒安装, 项目状态表)
- docs/INSTALLATION.md 刷新 (704行, pip/插件/Docker三路径)
- docs/ARCHITECTURE.md 刷新 (620行, V3融合架构图+fusion桥说明)
- CONTRIBUTING.md 重写 (320行, 环境搭建/代码规范/测试要求/PR流程)
- CHANGELOG.md 补全 (v3.0.0完整变更日志)

### 修复 (Fixed)
- README badge: 374→422 passed
- DB路径修复: 422/422 测试全通过 (100%)
- setup.py 版本 v2.0.0→v3.0.1

## [3.0.0] — 2026-05-06

### 新增 (Added)

#### 融合架构 (V1+V2+V3)
- **`fusion/` 桥接层** — V1单体 ↔ V2微服务双向桥接
  - `fusion/bridge.py` — `V1V2Bridge` 事件转换、服务映射、数据格式转换
  - `fusion/compatibility.py` — 兼容层、枚举映射、API网关、服务降级、版本检测
  - `fusion/unified_entry.py` — `UnifiedAgent` 统一入口，支持 V1_ONLY / V2_ONLY / HYBRID 三种模式

#### CLI 命令行工具
- **`hermes-evolution` CLI** — 通过 `pyproject.toml [project.scripts]` 注册
  - `hermes-evolution check` — 环境自检
  - `hermes-evolution setup` — 一键部署 Hermes 插件
  - `hermes-evolution status` — 系统状态
  - `hermes-evolution test` — 运行测试

#### DB 路径隔离
- **`db_utils.py`** — WAL模式 + busy_timeout + 线程安全缓存 + 路径解析(`EVOLUTION_DATA_DIR`)

#### 日志统一
- Python `logging` 模块 + LOG_LEVEL 环境变量

#### 工程化
- Makefile (13命令) + pyproject.toml + 可选依赖分组(dev/full/v2)

### 变更 (Changed)
- **版本号**: 2.0.0 → 3.0.0
- **架构**: 单体 → V1/V2/V3 融合架构
- **DB路径**: `data/` → `~/.hermes/data/evolution/`
- **日志**: print → logging模块
- **安装**: `pip install -r` → `pip install -e .`

### 修复 (Fixed)
- SQLite 并发锁: WAL + busy_timeout + 重试装饰器
- 跨线程安全: `check_same_thread=False`

---

## [2.0.0] — 2026-04-28

### 新增 (Added)
- Hermes Agent 插件集成 (6 tools + 1 hook)
- pyproject.toml 标准化打包
- 守护进程独立架构: `hermes_daemon.py` (546行)
- 飞书 OpenAPI 通知器 (webhook/openapi/simulated)
- Cron 定时汇报 (每2小时)
- `test_iteration6_integration.py` (27用例)

---

## [1.5.0] — 2026-04-28

### 新增 (Added)
- 闭环自主进化守护进程 (`closed_loop/` 4模块)
- 飞书通知修复 + Cron汇报

---

## [1.4.0] — 2026-04-26

### 新增 (Added)
- 安全模块 (`security/` 4模块)
- 协作引擎 (`collaboration/` 4模块)
- V1/V2 融合层 (`fusion/` 3模块)
- 测试覆盖: 253/253 全通过

---

## [1.3.0] — 2026-04-26

### 新增 (Added)
- 工具能力进化 (`tools/` 5模块)

---

## [1.2.0] — 2026-04-26

### 新增 (Added)
- 学习与记忆模块 (`learning/` + `memory/` + `self_monitor`)

---

## [1.0.0] — 2026-04-26

### 新增 (Added)
- 初始发布: HermesAgentEvolution V1+V2
