# HermesAgentEvolution 迭代5：全面工程化 — 设计方案与实施计划

> **制定日期**: 2026-05-06  
> **当前版本**: v3.0.0 (V1/V2/V3 融合架构)  
> **迭代目标**: 全面工程化 → 发布 Release 版本 → 用户一键安装、零门槛使用

---

## 一、当前状态基线

### 1.1 架构现状

```
hermes_agent_evolution/
├── src/evolution/         # V1 单体进化引擎 (~13000行)
│   ├── tools/             #   工具注册/创建/自动生成/性能分析/集成 (6模块)
│   ├── learning/          #   观察/分析/模式识别/经验/策略学习 (5模块)
│   ├── memory/            #   数据库/关联发现/关联优化/检索优化 (4模块)
│   ├── security/          #   权限管理/威胁检测/沙箱执行/审计日志 (4模块)
│   ├── collaboration/     #   代理注册/编排/消息总线/任务分发 (4模块)
│   ├── closed_loop/       #   指标收集/动作执行/守护进程/编排器 (4模块)
│   ├── fusion/            #   V1↔V2融合桥(桥接/兼容/统一入口) (3模块)
│   ├── self_monitor.py    #   自我监控 (1模块)
│   └── db_utils.py        #   数据库工具 (共享DB路径解析-已知P0缺陷)
├── src/services/          # V2 微服务层 (~7100行)
│   ├── core/              #   配置/事件/服务管理 (3模块)
│   ├── learning/          #   元学习/反思/强化学习 (3模块)
│   ├── tools/             #   工具发现/组合 (2模块)
│   └── system/            #   部署/监控/测试 (3模块)
├── src/utils/             # 飞书通知/进度汇报 (2模块)
├── hermes-plugin/         # Hermes 插件 (6工具+1钩子)
├── tests/                 # 22文件, 422测试 (406通过, 16失败)
├── docs/                  # 11个文档 (其中5个过时)
├── docker/                # Dockerfile + docker-compose.yml
└── scripts/               # cron报告/V2启动脚本
```

### 1.2 关键指标

| 指标 | 当前值 | Release目标 |
|------|--------|-------------|
| Python总行数 | 38,096 | — |
| 测试总数 | 422 | ≥450 |
| 测试通过率 | 96.2% (406/422) | 100% |
| P0阻塞缺陷 | 16个测试失败 (DB路径) | 0 |
| 版本一致性 | 6个文件, 2个不一致(setup.py v2.0.0, 文档v2) | 全部 v3.0.0 |
| 文档过时率 | 5/11 (45%) | 0% |
| 日志系统 | 无统一框架 | 统一日志框架 |
| 安装方式 | git clone + pip install -e | `pip install hermes-agent-evolution` |
| CI/CD | 无 | GitHub Actions |
| 插件验证 | 无自动化 | 自动化集成测试 |

### 1.3 P0 阻塞项 (上线前必修)

| # | 问题 | 影响范围 | 根因 |
|---|------|---------|------|
| 1 | 16个测试失败 | test_observer/test_retrieval/test_tool_* | db_utils.py DB路径解析忽略测试临时路径 |
| 2 | setup.py 版本 v2.0.0 | pip安装版本 | 版本同步遗漏 |
| 3 | docs/INSTALLATION.md 过时 (v2) | 用户安装指引 | 迭代3-4后未更新 |
| 4 | docs/ARCHITECTURE.md 过时 (v2) | 架构理解 | 融合架构后未更新 |
| 5 | README badge 374 passed (实际406) | 项目首页 | 硬编码未更新 |

---

## 二、迭代5 设计目标

```
用户视角:
  pip install hermes-agent-evolution        ← 一行安装
  hermes-evolution --help                   ← CLI 自文档
  cp -r hermes-plugin ~/.hermes/plugins/    ← 插件部署
  hermes gateway restart                    ← 即刻生效
  → Agent 开始自我进化                      ← 零配置使用

开发者视角:
  git clone → make test → make build → make release  ← 标准化流程
  任何贡献者可一键重建开发环境                      ← 低门槛贡献
```

---

## 三、任务分组与详细设计

### 📦 组A：版本统一与文档同步 (P0, 预计 3h)

#### A1. 版本号全面同步

**问题**: setup.py 声明 v2.0.0，pyproject.toml 声明 v3.0.0，文档标注 v2

**方案**: 单一真理源 → 从 `pyproject.toml` (v3.0.0) 派生

| 文件 | 当前 | 目标 | 修改方式 |
|------|------|------|---------|
| `setup.py:37` | `version="2.0.0"` | `version="3.0.0"` | 直接改 |
| `setup.py:39` | `description="..."` | `description="AI自我进化系统 V1/V2/V3 融合版"` | 同步pyproject.toml |
| `docs/INSTALLATION.md:3` | `v2 (Iteration 3)` | `v3.0.0 (V1/V2/V3融合)` | 全文重审 |
| `docs/ARCHITECTURE.md:3` | `v2 (事件驱动微服务架构)` | `v3.0.0 (V1/V2/V3 融合架构)` | 全文重审 |
| `README.md:6` | `tests-374 passed` | `tests-406 passed` | 改为动态统计或更新 |

**Pitfall**: 未来版本号变更必须同步 6 个文件 (pyproject.toml / setup.py / plugin.yaml / README badge / docs/INSTALLATION / docs/ARCHITECTURE)

#### A2. 文档全量刷新

**需重写的文档** (5个):

| 文档 | 问题 | 重写要点 |
|------|------|---------|
| `docs/INSTALLATION.md` | v2版本，缺少插件安装 | 更新为 v3.0.0，增加 Hermes 插件部署章节 |
| `docs/ARCHITECTURE.md` | v2 事件驱动架构 | 更新为 V1/V2/V3 融合架构图，fusion桥接说明 |
| `docs/API_REFERENCE.md` | 需确认模块全覆盖 | 补全 30 个模块的API入口 |
| `CHANGELOG.md` | 迭代3-5缺失 | 补全 v3.0.0 变更日志 |
| `CONTRIBUTING.md` | 需加入工程化规范 | 加入 logging/测试/CI规范 |

**新增文档** (4个):

| 文档 | 用途 |
|------|------|
| `docs/LOGGING.md` | 日志框架使用指南 |
| `docs/CONFIGURATION.md` | 配置参数完整说明 |
| `docs/QUICKSTART.md` | 5分钟上手指南 |
| `docs/RELEASE_CHECKLIST.md` | 发版检查清单 |

---

### 🛠️ 组B：日志系统统一化 (P1, 预计 5h)

#### B1. 日志框架选型与设计

**当前问题**: 各模块日志方式不一致（print / root logger / 无日志），无法按级别过滤，无法输出到文件

**设计方案**:

```python
# src/evolution/logging_config.py — 统一日志配置

import logging
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)-5s | %(name)-30s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 预定义 logger 层级
LOGGER_HIERARCHY = {
    "hermes_evo":                  logging.INFO,   # 根logger
    "hermes_evo.tools":            logging.INFO,
    "hermes_evo.tools.registry":   logging.DEBUG,
    "hermes_evo.learning":         logging.INFO,
    "hermes_evo.memory":           logging.INFO,
    "hermes_evo.security":         logging.WARNING,
    "hermes_evo.collaboration":    logging.INFO,
    "hermes_evo.closed_loop":      logging.INFO,
    "hermes_evo.services":         logging.INFO,
    "hermes_evo.plugin":           logging.INFO,
}

def setup_logging(
    level: str = "INFO",
    log_file: str = None,
    console: bool = True,
) -> None:
    """统一日志初始化，被 main()/register() 调用一次"""
    
    root = logging.getLogger("hermes_evo")
    root.setLevel(getattr(logging, level.upper()))
    root.handlers.clear()
    
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    
    if console:
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(formatter)
        root.addHandler(h)
    
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        h = logging.FileHandler(log_file)
        h.setFormatter(formatter)
        root.addHandler(h)
    
    # 设置各模块默认级别
    for name, lvl in LOGGER_HIERARCHY.items():
        logging.getLogger(name).setLevel(lvl)
    
    root.info("Logging initialized (level=%s)", level)
```

**使用约定**:

| 场景 | 级别 | 示例 |
|------|------|------|
| 工具创建/注册 | INFO | `log.info("Tool registered: %s (id=%s)", name, tid)` |
| 学习循环步骤 | INFO | `log.info("Cycle %d: observe → analyze → plan", n)` |
| 模式识别详情 | DEBUG | `log.debug("Pattern %s confidence=%.2f", p, c)` |
| DB连接/查询 | DEBUG | `log.debug("SQL: %s [%.1fms]", sql, ms)` |
| 安全拒绝 | WARNING | `log.warning("Permission denied: %s by %s", op, user)` |
| 异常但不致命 | ERROR | `log.error("Tool %s failed: %s", name, exc_info=True)` |
| 沙箱逃逸尝试 | CRITICAL | `log.critical("Sandbox violation: %s", detail)` |

#### B2. 日志实现改造计划

**改造策略**: 渐进式，不重写业务逻辑，只替换输出方式

```python
# 改造前 (如 self_monitor.py)
print(f"[SelfMonitor] Health check: {status}")

# 改造后
import logging
log = logging.getLogger("hermes_evo.self_monitor")
log.info("Health check: %s", status)
```

**改造优先级** (按模块依赖顺序):

| 优先级 | 模块数 | 文件 | 预计改动行数 |
|--------|--------|------|-------------|
| 1 | 1 | `db_utils.py` | ~5行 (添加1个logger) |
| 2 | 4 | `tools/*.py` | ~40行 (每文件~10个日志点) |
| 3 | 5 | `learning/*.py` | ~50行 |
| 4 | 4 | `memory/*.py` | ~40行 |
| 5 | 4 | `security/*.py` | ~40行 |
| 6 | 4 | `collaboration/*.py` | ~40行 |
| 7 | 1 | `self_monitor.py` | ~15行 |
| 8 | 3 | `fusion/*.py` | ~30行 |
| 9 | 11 | `services/*.py` | ~110行 |
| 10 | 2 | `utils/*.py` | ~20行 |
| **合计** | **39** | | **~390行改动** |

---

### 🔧 组C：DB路径解析修复 (P0, 预计 6h)

#### C1. 根因分析

**缺陷位置**: `src/evolution/db_utils.py::get_evolution_db()`

**当前行为**:
```python
# db_utils.py (当前)
def get_evolution_db(db_name: str = "evolution.db") -> str:
    data_dir = Path.home() / ".hermes" / "data" / "evolution"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / db_name)
```

**问题**: 所有 DB 名称 → `~/.hermes/data/evolution/`，完全忽略绝对路径和测试临时路径。16 个测试失败均为同一根因：
- `no such table` — module A 在 `/tmp/test_xxx.db` 创建表，但代码从 `~/.hermes/data/evolution/associations.db` 读取
- 计数不匹配 (`29 == 5`) — 共享 DB 累积历史数据

**修复方案**: 增加绝对路径检测

```python
def get_evolution_db(db_name: str = "evolution.db") -> str:
    import os
    # 如果传入的是绝对路径，直接使用（测试隔离场景）
    if os.path.isabs(db_name):
        parent = os.path.dirname(db_name)
        os.makedirs(parent, exist_ok=True)
        return db_name
    
    # 检查环境变量覆盖（测试/CI场景）
    data_dir = os.environ.get(
        "EVOLUTION_DATA_DIR",
        str(Path.home() / ".hermes" / "data" / "evolution")
    )
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, db_name)
```

#### C2. 关联修复

受影响模块需要同步检查:

| 文件 | 行号 | 修复 |
|------|------|------|
| `database.py` | ~29 | `self.db_path` 应传递给 `get_evolution_db()` 而非硬编码 `"associations.db"` |
| `memory/database.py` | 全局 | 使用 `os.path.basename(self.db_path)` 而非硬编码字符串 |
| 16个测试文件 | 各处 | 测试已在向 `/tmp/tmpXXXX.db` 传递 — 修复 db_utils 后自动通过 |

#### C3. 测试隔离验证

修复后运行:
```bash
python3 -m pytest tests/ -q --tb=line  # 期望: 422 passed
```

---

### 🔌 组D：一键安装体验 (P0, 预计 8h)

#### D1. PyPI 发布流程

```
项目源码 → pyproject.toml → build → twine upload → PyPI
                                                ↓
                                   pip install hermes-agent-evolution
```

**实现步骤**:

1. **统一 pyproject.toml 为唯一打包配置** (废弃 setup.py)
   - 所有元数据从 pyproject.toml 读取
   - setup.py 改为薄封装 (`setup()` 空调用) 或删除

2. **添加 `[project.scripts]` CLI 入口**
```toml
[project.scripts]
hermes-evolution = "evolution.cli:main"
hermes-evolution-setup = "evolution.cli:setup"
```

3. **创建 `src/evolution/cli.py`** — CLI 工具
```python
"""HermesAgentEvolution CLI — 安装/配置/状态/自检"""
# 子命令: install, check, status, config, plugin-deploy, test
```

4. **Build → Test → Publish 流程**
```bash
python3 -m build                    # 构建 .whl + .tar.gz
twine check dist/*                  # 验证包格式
twine upload --repository testpypi dist/*  # 先上 TestPyPI
pip install -i https://test.pypi.org/ hermes-agent-evolution  # 验证安装
twine upload dist/*                 # 正式发布 PyPI
```

#### D2. 一键安装脚本

`install.sh` (一键脚本):

```bash
#!/bin/bash
set -e
echo "🚀 HermesAgentEvolution v3.0.0 安装程序"

# 1. Python 检查
python3 -c "import sys; assert sys.version_info >= (3,9)" || {
    echo "❌ 需要 Python 3.9+"; exit 1
}

# 2. pip 安装核心包
pip install hermes-agent-evolution

# 3. Hermes 插件部署
HERMES_PLUGIN_DIR="${HOME}/.hermes/plugins/hermes-evolution"
mkdir -p "${HERMES_PLUGIN_DIR}"
python3 -m evolution.cli plugin-deploy --target "${HERMES_PLUGIN_DIR}"

# 4. 重启 Hermes (如已安装)
hermes gateway restart 2>/dev/null || echo "⚠️  Hermes未运行, 手动执行: hermes gateway restart"

# 5. 验证
python3 -m evolution.cli check

echo "✅ 安装完成! 运行 'hermes-evolution --help' 开始使用"
```

**安装后用户体验**:
```
$ pip install hermes-agent-evolution
Successfully installed hermes-agent-evolution-3.0.0

$ hermes-evolution check
✅ Python 3.11.2
✅ 核心模块已加载: 30/30
✅ DB 可读写: ~/.hermes/data/evolution/
✅ Hermes 插件已部署: ~/.hermes/plugins/hermes-evolution/
✅ 环境就绪

$ hermes-evolution status
版本: v3.0.0
测试: 422 passed (100%)
模块: V1×30 + V2×11
服务: 运行中 (pid=12345)
```

#### D3. Docker 一键部署

更新 `docker-compose.yml`:
```yaml
services:
  hermes-evolution:
    image: wayneliu519888/hermes-agent-evolution:3.0.0
    ports:
      - "8080:8080"
    volumes:
      - evolution_data:/root/.hermes/data/evolution
    environment:
      - LOG_LEVEL=INFO
      - EVOLUTION_DATA_DIR=/root/.hermes/data/evolution
```

---

### 🧪 组E：测试修复与CI/CD (P0, 预计 6h)

#### E1. 测试修复 (C组完成后自动验证)

| 当前状态 | 修复后目标 |
|---------|-----------|
| 406/422 通过 (96.2%) | 422/422 通过 (100%) |
| 16个DB路径相关失败 | 0失败 |

#### E2. GitHub Actions CI 流水线

`.github/workflows/ci.yml`:

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev,full]"
      - run: pytest tests/ -q --tb=line --cov=src/evolution --cov-report=xml
      - uses: codecov/codecov-action@v4

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ruff
      - run: ruff check src/ tests/

  build:
    needs: [test, lint]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install build twine
      - run: python3 -m build
      - run: twine check dist/*
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
```

#### E3. pre-commit 配置

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest tests/ -q --tb=line
        language: system
        pass_filenames: false
        always_run: true
```

---

### 📋 组F：README/首页重构 (P1, 预计 3h)

**当前 README 问题**: badge 过期 (374 vs 406)、架构图不反映 V3 融合、无快速上手示例

**重构结构**:

```markdown
# HermesAgentEvolution v3.0.0

[![PyPI version](https://badge.fury.io/py/hermes-agent-evolution.svg)]
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)]
[![Tests](https://img.shields.io/badge/tests-422%20passed-brightgreen)]
[![License: MIT](https://img.shields.io/badge/license-MIT-green)]
[![CI](https://github.com/.../workflows/CI/badge.svg)]

## ⚡ 5秒安装
pip install hermes-agent-evolution && hermes-evolution setup

## 🎯 一句话描述
AI自我进化框架 — 让Agent从经验中学习、自动优化策略、动态创建工具

## 📖 30秒了解
- 🧠 学习进化: 观察→分析→模式识别→策略生成
- 🛠️ 工具进化: 注册→性能分析→自动生成→动态组合
- 💾 记忆进化: 关联发现→检索优化→压缩自适应
- 🔒 安全进化: 沙箱执行→威胁检测→权限管理

## 🏗️ V3融合架构
[SVG 架构图 — 展示V1单体/V2微服务/V3融合桥]

## 📊 项目状态
| 模块 | 文件 | 行数 | 测试 |
|------|------|------|------|
| V1进化引擎 | 30 | ~13000 | ✅ |
| V2微服务 | 11 | ~7100 | ✅ |
| 融合桥 | 3 | ~500 | ✅ |
| 合计 | 44 | ~21000 | 422 |

## 🚀 快速上手
[3个场景: pip安装 → 插件部署 → Docker启动]

## 📚 文档
[docs/ 文件索引表]

## 🤝 贡献
[CONTRIBUTING.md 链接]
```

---

### 🏗️ 组G：工程化基础设施 (P1, 预计 4h)

#### G1. Makefile

```makefile
.PHONY: install test lint clean build publish docker

install:
	pip install -e ".[dev,full]"

test:
	pytest tests/ -q --tb=line

test-cov:
	pytest tests/ --cov=src/evolution --cov-report=html

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf dist/ build/ *.egg-info .pytest_cache

build:
	python3 -m build

publish-test: build
	twine upload --repository testpypi dist/*

publish: build
	twine upload dist/*

docker-build:
	docker build -t hermes-agent-evolution:3.0.0 -f docker/Dockerfile .

docker-run:
	docker-compose up -d

check-all: lint test
	@echo "✅ All checks passed"
```

#### G2. 环境自检脚本

`src/evolution/cli.py` 中的 `check` 命令逻辑:

```python
def cmd_check():
    checks = []
    # 1. Python版本
    checks.append(("Python ≥3.9", sys.version_info >= (3, 9)))
    # 2. 核心模块可导入
    for mod in MODULE_LIST:
        try:
            __import__(mod)
            checks.append((f"模块 {mod}", True))
        except ImportError as e:
            checks.append((f"模块 {mod}", False, str(e)))
    # 3. DB可读写
    db_path = get_evolution_db()
    try:
        # 尝试创建测试表并删除
        ...
        checks.append(("DB读写", True))
    except Exception as e:
        checks.append(("DB读写", False, str(e)))
    # 4. Hermes插件已部署
    plugin_dir = Path.home() / ".hermes" / "plugins" / "hermes-evolution"
    checks.append(("Hermes插件", plugin_dir.exists()))
    
    for name, ok, *detail in checks:
        icon = "✅" if ok else "❌"
        print(f"{icon} {name}")
        if detail:
            print(f"   → {detail[0]}")
    
    return all(c[1] for c in checks)
```

---

## 四、实施计划与时间线

```
总工时: ~35h
建议周期: 2周 (10个工作日)

Week 1 — 修复 + 基础 (16h)
┌─────────────────────────────────────────────────┐
│ Day 1-2: 组C DB路径修复         ████████ 6h     │ → 16 failed → 0
│ Day 2-3: 组A 版本统一+文档      ████     3h     │ → 6文件版本一致
│ Day 3-5: 组B 日志统一化         ██████   5h     │ → 39模块统一日志
│ Day 5:   组G 工程化基础(Make)   ██       2h     │ → Makefile+自检
└─────────────────────────────────────────────────┘

Week 2 — 发布 + CI (19h)
┌─────────────────────────────────────────────────┐
│ Day 6-8: 组D 一键安装(PyPI)     ████████ 8h     │ → pip install可用
│ Day 8-9: 组E CI/CD              ██████   6h     │ → GitHub Actions
│ Day 9:   组F README重构         ███      3h     │ → 首页翻新
│ Day 10:  全量验证+Release       ██       2h     │ → v3.0.0 release
└─────────────────────────────────────────────────┘
```

### 任务依赖图

```
组C(DB修复)
  ├─→ 组E(CI)     [需测试全绿]
  └─→ 组D(安装)   [需DB正常]
  
组A(版本同步)     [独立, 优先做]
组B(日志)         [独立, 可与A/C并行]
组G(Makefile)     [独立]

组D(安装) → 组F(README) → Release
组C→组E(CI) → Release
```

---

## 五、Release v3.0.0 检查清单

发布前必须全部打勾:

### 代码质量
- [ ] 测试 422/422 通过 (100%)
- [ ] ruff lint 零错误
- [ ] 所有 print() 替换为 logger
- [ ] 无硬编码绝对路径
- [ ] `EVOLUTION_DATA_DIR` 环境变量可覆盖 DB 路径

### 版本一致性
- [ ] `pyproject.toml` → v3.0.0
- [ ] `setup.py` → v3.0.0
- [ ] `hermes-plugin/plugin.yaml` → v3.0.0
- [ ] `README.md` badges → v3.0.0 + 422 passed
- [ ] `docs/INSTALLATION.md` → v3.0.0
- [ ] `docs/ARCHITECTURE.md` → v3.0.0

### 包发布
- [ ] `python3 -m build` 成功
- [ ] `twine check dist/*` 零 warning
- [ ] TestPyPI 安装验证: `pip install -i https://test.pypi.org/ hermes-agent-evolution`
- [ ] PyPI 正式发布
- [ ] `pip install hermes-agent-evolution` 成功 (任意机器)

### 插件部署
- [ ] `cp -r hermes-plugin ~/.hermes/plugins/hermes-evolution/`
- [ ] `hermes gateway restart` 无错误
- [ ] `hermes tools list | grep evolution` 显示 6 个工具

### 文档
- [ ] README.md — 重构完成
- [ ] docs/INSTALLATION.md — 含 pip + Docker + 插件 三路径
- [ ] docs/ARCHITECTURE.md — V3 融合架构图
- [ ] docs/QUICKSTART.md — 5分钟上手
- [ ] docs/LOGGING.md — 日志使用指南
- [ ] docs/CONFIGURATION.md — 配置参数表
- [ ] CHANGELOG.md — v3.0.0 完整变更
- [ ] CONTRIBUTING.md — 开发规范

### CI/CD
- [ ] GitHub Actions `.github/workflows/ci.yml` 存在
- [ ] push → lint → test → build 全流程通过
- [ ] codecov 覆盖率报告生成

### 验证
- [ ] `hermes-evolution check` 全部 ✅
- [ ] clean venv 安装后 `from evolution import ...` 无 ImportError
- [ ] Docker: `docker-compose up -d` → 服务启动 → 健康检查通过

---

## 六、风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| DB路径修复引入新回归 | 中 | 高 | 组C修改最小化(只改3行)，全量测试在隔离docker中验证 |
| PyPI 包名冲突 | 低 | 中 | 先上 TestPyPI 验证，保留 `hermes-agent-evolution` 命名 |
| 文档重写耗时超预期 | 中 | 低 | AI辅助生成初稿，人工review修改 |
| CI 配置需要多次调试 | 高 | 低 | 先用 `act` 本地模拟 GitHub Actions |
| 用户环境差异 | 中 | 中 | `check` 命令检测所有前置条件，给明确修复提示 |

---

## 七、决策点（需要你确认）

请对以下决策给出你的意见：

1. **setup.py 去留**: ✅ 保留 setup.py，兼容旧 pip

2. **支持 Python 版本范围**: ✅ 加入 3.13，CI matrix 覆盖 3.9/3.10/3.11/3.12/3.13

3. **Docker 镜像发布**: ✅ 方案二：只提供 Dockerfile 供高级用户自构建，不推 Docker Hub。主推 `pip install` + `hermes-evolution setup` 一键安装

4. **CLI 语言**: ✅ 中文

5. **文档语言策略**: ✅ 全部中文（README + 架构 + API + 教程统一中文）

6. **发布节奏**: ✅ 一次性 GA，全部组完成后发布 v3.0.0
