# 变更日志 (Changelog)

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

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
