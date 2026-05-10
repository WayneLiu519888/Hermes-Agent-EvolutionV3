# HermesAgentEvolution 安装指南

> 版本: v5.0.0
> 最后更新: 2026-05-09
> Python: 3.9+ | 测试: 439 passed (24 测试文件) | 核心代码: ~26561 行

---

## 目录

1. [系统要求](#1-系统要求)
2. [快速安装 (pip)](#2-快速安装-pip)
3. [从源码安装](#3-从源码安装)
4. [Docker 部署](#4-docker-部署)
5. [验证安装](#5-验证安装)
6. [项目结构](#6-项目结构)
7. [常见问题](#7-常见问题)

---

## 1. 系统要求

### 最低要求

| 资源 | 要求 |
|------|------|
| **Python** | 3.9 或更高 |
| **操作系统** | Linux / macOS / Windows (WSL2) |
| **内存** | 2 GB RAM |
| **磁盘** | 500 MB 可用空间 |
| **网络** | 无需联网（LLM 功能可选） |

### 推荐环境

| 资源 | 推荐 |
|------|------|
| **Python** | 3.11+ |
| **操作系统** | Ubuntu 22.04+ / macOS 14+ |
| **内存** | 4 GB RAM |
| **磁盘** | 1 GB SSD |

### 依赖概览

v5.0.0 采用**零外部依赖**设计，核心依赖仅 Python 标准库：

| 依赖 | 用途 | 必需 |
|------|------|:--:|
| `sqlite3` | 7 个数据库持久化 (WAL 模式) | ✅ |
| `logging` | 统一日志框架 | ✅ |
| `asyncio` | 异步进化循环 | ✅ |
| `openai` (>=1.0) | LLM 工具生成 (可选) | ❌ |
| `anthropic` | Claude API (可选) | ❌ |

---

## 2. 快速安装 (pip)

### 2.1 一行安装

```bash
pip install hermes-agent-evolution
```

安装后立即可用：

```bash
# 环境自检
hermes-evolution check

# 查看系统状态
hermes-evolution status

# 运行测试套件
hermes-evolution test
```

### 2.2 创建虚拟环境（推荐）

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# 或
.venv\Scripts\activate          # Windows

# 安装
pip install hermes-agent-evolution
```

### 2.3 CLI 命令参考

安装后 `hermes-evolution` 注册到系统 PATH：

| 命令 | 说明 |
|------|------|
| `hermes-evolution check` | 环境自检 (Python 版本、模块导入、DB 连接) |
| `hermes-evolution setup` | 一键部署插件到 `~/.hermes/plugins/hermes-evolution/` |
| `hermes-evolution status` | 查看系统状态 (版本、模块数、测试、DB 文件) |
| `hermes-evolution test` | 运行测试套件 |

### 2.4 可选的 LLM 功能

如需使用 `create_from_description` 等 LLM 驱动功能：

```bash
pip install openai>=1.0.0
# 或
pip install anthropic
```

### 2.5 插件部署

将 Hermes Agent 插件部署到 Hermes Gateway：

```bash
# CLI 一键部署
hermes-evolution setup

# 验证插件
hermes-evolution check
# ✅ Hermes 插件已部署
```

部署后重启 Hermes Gateway 使插件生效：

```bash
hermes gateway restart
```

---

## 3. 从源码安装

### 3.1 克隆仓库

```bash
git clone https://github.com/WayneLiu519888/Hermes-Agent-EvolutionV3.git
cd Hermes-Agent-EvolutionV3
```

### 3.2 安装依赖

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 可编辑模式安装
pip install -e .

# 开发模式 (含测试/代码检查工具)
pip install -e ".[dev]"
```

### 3.3 验证源码安装

```bash
# 环境自检
hermes-evolution check

# 运行测试
hermes-evolution test
```

---

## 4. Docker 部署

### 4.1 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install hermes-agent-evolution

RUN mkdir -p /root/.hermes/data/evolution

ENV EVOLUTION_DATA_DIR=/root/.hermes/data/evolution

CMD ["hermes-evolution", "check"]
```

### 4.2 构建和运行

```bash
# 构建镜像
docker build -t hermes-agent-evolution:v5.0.0 .

# 运行容器
docker run -it --rm \
  -v hermes_data:/root/.hermes/data/evolution \
  hermes-agent-evolution:v5.0.0
```

### 4.3 Docker Compose

```yaml
version: '3.8'

services:
  evolution:
    image: hermes-agent-evolution:v5.0.0
    container_name: hermes-evolution
    volumes:
      - evolution_data:/root/.hermes/data/evolution
    environment:
      - EVOLUTION_LOG_LEVEL=INFO
      - EVOLUTION_DATA_DIR=/root/.hermes/data/evolution
    restart: unless-stopped

volumes:
  evolution_data:
```

### 4.4 环境变量文件 (.env)

```bash
# .env
EVOLUTION_LOG_LEVEL=INFO
EVOLUTION_DATA_DIR=/root/.hermes/data/evolution
EVOLUTION_SANDBOX_ENABLED=true
EVOLUTION_AUDIT_ENABLED=true
```

---

## 5. 验证安装

### 5.1 CLI 环境自检（推荐）

```bash
hermes-evolution check
```

输出示例：

```
🔍 HermesAgentEvolution 环境自检 (v5.0.0)
==================================================
  ✅ Python 3.12.3 ≥ 3.9
  ✅ 模块 工具注册表
  ✅ 模块 学习观察器
  ✅ 模块 记忆数据库
  ✅ 模块 安全审计
  ✅ 模块 协作编排
  ✅ 模块 闭环编排
  ✅ 模块 自进化审计器
  ✅ 模块 自我监控
  ✅ 模块 DB工具
  ✅ DB 可读写
  ✅ 数据目录: ~/.hermes/data/evolution
==================================================
  🎉 环境就绪，可以正常使用
```

### 5.2 系统状态

```bash
hermes-evolution status
```

输出示例：

```
版本: v5.0.0
测试: 439 passed (24 测试文件)
工具: 7 个
数据库: 7 个 (tools / tool_performance / learning_experiences /
         associations / retrieval_optimization / closed_loop / evolution_audit)
代码: ~26561 行核心
```

### 5.3 Python 导入验证

```python
# 核心模块导入
from evolution.tools import ToolRegistry
from evolution.learning import LearningObserver
from evolution.memory import EvolutionDatabase
from evolution.db_utils import get_evolution_db

# 验证 DB 连接
print(f"DB 路径: {get_evolution_db('tools.db')}")

# 初始化
registry = ToolRegistry()
observer = LearningObserver()
print("✅ 所有核心模块导入成功")
```

---

## 6. 项目结构

```
hermes_agent_evolution/
├── src/
│   └── evolution/
│       ├── __init__.py
│       ├── cli.py                  # CLI 入口 (check/setup/status/test)
│       ├── db_utils.py             # 数据库路径解析 + WAL 连接工厂
│       ├── self_monitor.py         # 自我监控
│       ├── logging_config.py       # 统一日志框架
│       ├── tools/                  # 工具能力层 (7 模块)
│       │   ├── __init__.py
│       │   ├── tool_registry.py    # 工具注册表
│       │   ├── tool_creator.py     # 工具创建器
│       │   ├── enhanced_tool_creator.py  # 增强创建器 (6 种方式)
│       │   ├── tool_performance_analyzer.py  # 性能分析器
│       │   ├── tool_auto_generator.py       # 工具自动生成
│       │   └── tool_integration.py          # 工具学习集成
│       ├── learning/               # 学习能力层 (5 模块)
│       │   ├── __init__.py
│       │   ├── experience.py       # 经验数据类
│       │   ├── observer.py         # 学习观察器
│       │   ├── analyzer.py         # 经验分析器
│       │   ├── pattern_recognizer.py  # 模式识别器
│       │   └── tool_strategy_learner.py  # 工具策略学习器 (SQLite 持久化)
│       ├── memory/                 # 记忆系统 (4 模块)
│       │   ├── __init__.py
│       │   ├── database.py         # 进化数据库
│       │   ├── association_discoverer.py  # 关联发现
│       │   ├── association_optimizer.py   # 关联优化
│       │   └── retrieval_optimizer.py     # 检索优化
│       ├── security/               # 安全层 (4 模块)
│       │   ├── __init__.py
│       │   ├── audit_logger.py     # 审计日志
│       │   ├── permission_manager.py  # 权限管理
│       │   ├── sandbox_executor.py    # 沙箱执行
│       │   └── threat_detector.py     # 威胁检测
│       ├── collaboration/          # 协作层 (4 模块)
│       │   ├── __init__.py
│       │   ├── agent_orchestrator.py  # 代理编排
│       │   ├── agent_registry.py      # 代理注册
│       │   ├── message_bus.py         # 消息总线
│       │   └── task_dispatcher.py     # 任务分发
│       ├── closed_loop/            # 闭环控制 (5 模块)
│       │   ├── __init__.py
│       │   ├── orchestrator.py     # 进化编排器
│       │   ├── action_executor.py  # 动作执行器
│       │   ├── daemon.py           # 守护进程
│       │   ├── metrics_collector.py  # 指标收集器
│       │   └── evolution_auditor.py  # 自进化审计器 (v5.0.0 新增)
│       └── fusion/                 # V1↔V2 融合桥 (3 模块)
│           ├── __init__.py
│           ├── bridge.py
│           ├── compatibility.py
│           └── unified_entry.py
├── hermes-plugin/                  # Hermes 插件 (7 工具)
│   ├── plugin.yaml
│   └── __init__.py
├── tests/                          # 24 测试文件 (439 passed)
├── docs/                           # 文档
├── pyproject.toml
└── README.md
```

### 数据目录

运行时数据存储在 `~/.hermes/data/evolution/`：

```
~/.hermes/data/evolution/
├── tools.db                     # 工具注册表
├── tool_performance.db          # 工具性能统计
├── learning_experiences.db      # 学习经验记录
├── associations.db              # 记忆关联数据
├── retrieval_optimization.db    # 检索优化配置
├── closed_loop.db               # 闭环控制状态
└── evolution_audit.db           # 自进化审计 (v5.0.0 新增)
```

---

## 7. 常见问题

### Q: 安装失败 "externally-managed-environment"？

```bash
pip install --break-system-packages hermes-agent-evolution
```

或使用虚拟环境 (推荐)。

### Q: CLI 命令找不到？

确认 pip 安装路径在 PATH 中：

```bash
# 查找安装位置
pip show hermes-agent-evolution | grep Location

# 或直接调用
python -m evolution.cli check
```

### Q: DB 权限错误？

```bash
# 检查数据目录权限
ls -la ~/.hermes/data/evolution/

# 使用临时目录
export EVOLUTION_DATA_DIR=/tmp/hermes-evo-data
hermes-evolution check
```

### Q: 如何卸载？

```bash
pip uninstall hermes-agent-evolution
rm -rf ~/.hermes/data/evolution   # 删除数据（可选）
rm -rf ~/.hermes/plugins/hermes-evolution  # 删除插件（可选）
```

### Q: 如何升级？

```bash
pip install --upgrade hermes-agent-evolution
hermes-evolution check     # 验证升级
```

---

## 下一步

- 📖 [快速上手指南](QUICKSTART.md) — 5 分钟开始使用
- 🏗️ [架构概述](ARCHITECTURE.md) — V3 融合架构详解
- ⚙️ [配置说明](CONFIGURATION.md) — 环境变量与调优
- 📋 [日志指南](LOGGING.md) — 统一日志框架
- 🧪 [测试指南](TESTING.md) — 24 文件 439 测试
