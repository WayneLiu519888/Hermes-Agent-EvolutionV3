# 变更日志 (Changelog)

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

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
