# 变更日志 (Changelog)

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

## [3.0.0] — 2026-05-06

### 新增 (Added)

#### 融合架构 (V1+V2+V3)
- **`fusion/` 桥接层** — V1单体 ↔ V2微服务双向桥接
  - `fusion/bridge.py` — `V1V2Bridge` 事件转换、服务映射、数据格式转换
  - `fusion/compatibility.py` — 兼容层、枚举映射、API网关、服务降级、版本检测
  - `fusion/unified_entry.py` — `UnifiedAgent` 统一入口，支持 V1_ONLY / V2_ONLY / HYBRID 三种模式

#### CLI 命令行工具
- **`hermes-evolution` CLI** — 通过 `pyproject.toml [project.scripts]` 注册
  - `hermes-evolution check` — 环境自检: Python版本、9个核心模块导入、DB读写、插件部署
  - `hermes-evolution setup` — 一键部署 Hermes 插件到 `~/.hermes/plugins/hermes-evolution/`
  - `hermes-evolution status` — 系统状态: 版本、代码行数、测试结果、DB文件
  - `hermes-evolution test` — 运行测试套件

#### DB 路径隔离
- **`db_utils.py` 统一连接工厂** — 所有 evolution 模块通过 `get_evolution_db()` 获取连接
  - WAL 模式 + 30s busy_timeout + 8MB cache + foreign_keys
  - 线程安全连接缓存 (threading.Lock)
  - 路径解析: `EVOLUTION_DATA_DIR` → `HERMES_HOME/data/evolution/` → `~/.hermes/data/evolution/`
  - 指数退避重试装饰器 `@retry_on_db_error`
  - 便捷函数: `db_table_exists()`, `db_get_stats()`, `vacuum_database()`

#### 日志统一
- **Python `logging` 模块** — 统一使用 `logging.getLogger(__name__)` 替代裸 print
- 日志级别通过 `LOG_LEVEL` 环境变量控制 (DEBUG/INFO/WARNING/ERROR)
- DB连接/关闭/重试等关键路径均有日志输出

#### 工程化
- **Makefile** — 13 个标准化命令: `install`, `install-min`, `test`, `test-v`, `test-cov`, `test-failed`, `lint`, `format`, `fix`, `clean`, `build`, `check`, `check-all`
- **`make check`** — 集成 lint + test 的 CI 预检命令
- **`make build`** — PyPI 包构建 (python-build)

#### PyPI 打包
- **`pyproject.toml`** — 标准化项目配置，`[project.scripts]` CLI入口
- 可选依赖分组: `dev` (pytest), `full` (numpy/scikit-learn), `v2` (pyyaml/docker)

### 变更 (Changed)
- **版本号**: 2.0.0 → 3.0.0
- **架构**: 单体守护进程 → V1/V2/V3 三位一体融合架构
- **DB路径**: 项目根 `data/` → `~/.hermes/data/evolution/` (标准化隔离)
- **日志**: 分散的 print/logging → 统一 `logging` 模块
- **安装**: `pip install -r requirements.txt` → `pip install -e .` (pyproject.toml)
- **代码检查**: flake8/black → ruff (check + format)
- **测试入口**: `pytest tests/` → `make test` / `hermes-evolution test`

### 修复 (Fixed)
- SQLite 并发写入锁问题: 通过 WAL + busy_timeout=30s + 重试装饰器解决
- 跨线程连接安全: `check_same_thread=False` + 线程安全缓存

---

## [2.0.0] — 2026-04-28

### 新增 (Added)
- **迭代6: Hermes Agent 插件集成** — thin-layer 插件通过 `register(ctx)` 暴露 6 tools + 1 hook
- `pyproject.toml` 标准化打包配置
- 守护进程独立架构 (方案A): `hermes_daemon.py` 546行 + 插件薄层
- 飞书 OpenAPI 通知器 (支持 webhook/openapi/simulated 三种模式)
- Cron 定时进展汇报 (每2小时飞书推送)
- `test_iteration6_integration.py` 集成测试 (27用例, 覆盖5维度)

### 变更 (Changed)
- 版本号升级至 2.0.0
- 迭代6架构决策: 守护进程独立, 松耦合共享 SQLite

---

## [1.5.0] — 2026-04-28

### 新增 (Added)
- **迭代5: 闭环自主进化守护进程** — 完整的自主进化循环
  - `closed_loop/action_executor.py`
  - `closed_loop/metrics_collector.py`
  - `closed_loop/orchestrator.py`
  - `closed_loop/daemon.py`
- 飞书通知修复: OpenAPI 模式正常运行
- Cron 每2小时进展汇报

---

## [1.4.0] — 2026-04-26

### 新增 (Added)
- **迭代4: 安全增强** — `security/` 模块
  - `audit_logger.py` — 审计日志记录/查询/轮转
  - `permission_manager.py` — 权限管理/角色分配
  - `sandbox_executor.py` — 安全沙箱执行
  - `threat_detector.py` — 威胁检测
- **协作引擎** — `collaboration/` 模块
  - `agent_orchestrator.py` — 多Agent编排
  - `agent_registry.py` — Agent注册/发现
  - `message_bus.py` — 消息总线
  - `task_dispatcher.py` — 任务分发
- **V1/V2 融合层** — `fusion/` 模块
  - `bridge.py` — 桥接层
  - `unified_entry.py` — 统一入口
  - `compatibility.py` — 兼容层

### 变更 (Changed)
- 测试覆盖: 253/253 全通过 (19测试文件)
- 代码覆盖率: 66%

---

## [1.3.0] — 2026-04-26

### 新增 (Added)
- **迭代3: 工具能力进化**
  - `tools/enhanced_tool_creator.py` — 增强工具创建器
  - `tools/tool_auto_generator.py` — 工具自动生成
  - `tools/tool_integration.py` — 工具进化引擎
  - `tools/tool_performance_analyzer.py` — 性能分析器
  - `tools/tool_registry.py` — 工具注册表

---

## [1.2.0] — 2026-04-26

### 新增 (Added)
- **迭代2: 学习与记忆**
  - `learning/` 模块 — 经验学习/观测/分析/策略
  - `memory/` 模块 — 关联发现/检索优化/数据库
  - `self_monitor.py` — 自我监控

---

## [1.0.0] — 2026-04-26

### 新增 (Added)
- **初始发布: HermesAgentEvolution V1+V2**
  - V1 基础Agent框架 (`src/`)
  - V2 微服务架构 (`v2_project/`)
  - 基础测试框架 (pytest)
  - 项目文档框架
