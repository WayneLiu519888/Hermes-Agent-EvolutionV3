# 贡献指南 (CONTRIBUTING)

> 版本: v5.0.0 (V1/V2/V3 融合架构)
> 最后更新: 2026-05-09

欢迎为 HermesAgentEvolution 项目贡献代码！

---

## 目录

1. [开发环境搭建](#1-开发环境搭建)
2. [代码规范](#2-代码规范)
3. [测试要求](#3-测试要求)
4. [PR 流程](#4-pr-流程)
5. [分支策略](#5-分支策略)
6. [提交规范](#6-提交规范)
7. [项目结构](#7-项目结构)
8. [行为准则](#8-行为准则)

---

## 1. 开发环境搭建

### 1.1 环境要求

| 要求 | 说明 |
|------|------|
| **Python** | ≥ 3.9 (推荐 3.11+) |
| **操作系统** | Linux / macOS / Windows (WSL2) |
| **Git** | 最新稳定版 |

### 1.2 一键安装

```bash
# 克隆仓库
git clone https://github.com/WayneLiu519888/Hermes-Agent-EvolutionV3.git
cd Hermes-Agent-EvolutionV3

# 一键安装开发依赖
make install
```

等价于:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,full]"
```

### 1.3 验证环境

```bash
# 环境自检
make check

# 或
hermes-evolution check
```

预期输出所有检查项 ✅ 通过。

### 1.4 Makefile 常用命令

| 命令 | 说明 |
|------|------|
| `make install` | 安装开发依赖 (可编辑模式) |
| `make test` | 运行全量测试 (快速模式) |
| `make test-v` | 运行全量测试 (详细模式) |
| `make test-cov` | 运行测试 + 覆盖率报告 |
| `make test-failed` | 仅重跑上次失败的测试 |
| `make lint` | 代码检查 (ruff) |
| `make format` | 代码格式化 (ruff) |
| `make fix` | 自动修复 lint 问题 |
| `make check` | 环境自检 |
| `make check-all` | 全量检查 (lint + test) |
| `make clean` | 清理构建产物 |
| `make build` | 构建 PyPI 包 |

---

## 2. 代码规范

### 2.1 Ruff 代码检查

项目使用 **ruff** 进行代码检查和格式化（替代 flake8 + black）:

```bash
# 代码检查
make lint

# 代码格式化
make format

# 自动修复
make fix
```

**建议**: 提交前必须通过 `make lint`，建议配置 pre-commit hook:

```bash
make pre-commit-install
```

### 2.2 日志规范

使用 Python 标准 `logging` 模块，**禁止使用 `print()`** 输出日志:

```python
import logging

logger = logging.getLogger(__name__)

# ✅ 正确: 使用 logger
logger.info("工具注册成功: %s", tool_name)
logger.debug("数据库查询耗时: %.2fms", elapsed_ms)
logger.warning("重试第 %d 次", attempt)
logger.error("操作失败: %s", error_msg)

# ❌ 错误: 使用 print
print("工具注册成功")
```

日志级别指南:

| 级别 | 使用场景 |
|------|---------|
| `DEBUG` | 详细的调试信息 (DB 连接、参数值) |
| `INFO` | 关键操作流程 (进化周期、工具注册) |
| `WARNING` | 可恢复的异常 (重试、降级) |
| `ERROR` | 操作失败、需要关注的错误 |

### 2.3 数据库操作规范

所有数据库连接**必须**通过 `db_utils.get_evolution_db()` 获取，**禁止裸 `sqlite3.connect()`**:

```python
# ✅ 正确
from src.evolution.db_utils import get_evolution_db, close_all_connections

conn = get_evolution_db("tools.db")
conn.execute("SELECT ...")

# ❌ 错误
import sqlite3
conn = sqlite3.connect("data/tools.db")
```

### 2.4 其他规范

- 遵循 **PEP 8** 代码风格
- 每个模块以中文 docstring 开头，描述模块职责和核心类
- 类型注解**推荐**使用（非强制），公共接口建议标注
- 文件编码统一 UTF-8

---

## 3. 测试要求

### 3.1 测试框架

使用 **pytest** 框架:

```bash
# 运行全量测试
make test

# 或直接
python3 -m pytest tests/ -q
# 预期: 439 passed in ~30s

# 详细模式
make test-v

# 覆盖率报告
make test-cov
# 报告在 htmlcov/index.html
```

### 3.2 测试规范

- **新增功能必须有对应测试** — 目标覆盖率 ≥ 80%
- 测试文件命名: `tests/test_<module>.py`
- 每个测试方法必须有中文 docstring
- 测试应**独立、可重复、不依赖外部服务**

### 3.3 测试示例

```python
def test_tool_registry_register():
    """测试工具注册表的基本注册功能"""
    registry = ToolRegistry(db_path=":memory:")
    tool = ToolDefinition(
        name="test_tool",
        description="测试工具",
        category=ToolCategory.UTILITY
    )
    assert registry.register(tool) is True
    assert registry.get("test_tool") is not None
```

### 3.4 测试隔离

- 使用 `db_path=":memory:"` 避免污染生产数据
- 使用绝对路径指向 `/tmp/` 时，测试结束后清理

---

## 4. PR 流程

### 4.1 提交流程

```
① Fork 仓库 → ② 创建功能分支 → ③ 开发 + 测试 → ④ 提交 PR
```

### 4.2 PR 前检查清单

- [ ] `make lint` 通过，无 lint 错误
- [ ] `make format` 通过，代码已格式化
- [ ] `make test` 通过，**439 / 439 全部通过**
- [ ] 新增功能有对应测试
- [ ] 相关文档已更新 (README / CHANGELOG / docs/)
- [ ] Commit 遵循 Conventional Commits 规范

### 4.3 PR 描述模板

```markdown
## 变更类型
- [ ] 新功能 (feat)
- [ ] 修复 (fix)
- [ ] 文档 (docs)
- [ ] 重构 (refactor)
- [ ] 测试 (test)

## 变更说明
简要描述此 PR 做了什么。

## 关联 Issue
Closes #XX (如有)

## 测试
- [ ] make test 通过 (439 passed)
- [ ] make lint 通过
```

### 4.4 Code Review 要求

- 所有合并到 `main` 需要至少 1 人 review
- CI 全部通过（测试 + lint）
- 需关联 GitHub Issue（如有）
- Review 关注: 代码规范、测试覆盖、日志输出、DB 路径正确性

---

## 5. 分支策略

| 分支 | 说明 |
|------|------|
| `main` | 稳定分支，保护分支，禁止直接推送 |
| `feat/*` | 功能分支 |
| `fix/*` | 修复分支 |
| `docs/*` | 文档分支 |
| `chore/*` | 杂项分支 |

---

## 6. 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/):

```
<type>(<scope>): <描述>

type: feat | fix | docs | test | refactor | chore | perf
scope: 模块名 (如 fusion, memory, security, cli, auditor)
描述: 中文简述变更内容
```

示例:

```
feat(cli): 添加 hermes-evolution check 环境自检命令
fix(db_utils): 修复 WAL 模式连接泄漏
docs: 更新 CONTRIBUTING.md 到 v5.0.0 标准
test(auditor): 补测 evolution_auditor 查询接口
refactor(logging): 统一使用 logging 模块替代 print
```

---

## 7. 项目结构

```
hermes_agent_evolution/
├── src/evolution/               # 核心进化引擎 (V1 单体)
│   ├── __init__.py              # 版本号 v5.0.0
│   ├── cli.py                   # CLI 命令行工具
│   ├── db_utils.py              # 统一数据库连接工厂 (WAL)
│   ├── self_monitor.py          # 自我监控器
│   ├── health.py                # 健康检查
│   ├── logging_config.py        # 日志配置
│   ├── dependency_manager.py    # 依赖管理
│   │
│   ├── learning/                # 🧠 经验学习
│   │   ├── observer.py          #   学习观察者
│   │   ├── analyzer.py          #   经验分析器
│   │   ├── experience.py        #   经验数据模型
│   │   ├── pattern_recognizer.py #  模式识别
│   │   └── tool_strategy_learner.py # 工具策略学习 (v3.0.5 持久化)
│   │
│   ├── memory/                  # 🧩 关联记忆
│   │   ├── database.py          #   记忆数据库
│   │   ├── association_discoverer.py # 关联发现
│   │   ├── association_optimizer.py  # 关联优化
│   │   └── retrieval_optimizer.py    # 检索优化
│   │
│   ├── tools/                   # 🛠️ 工具进化
│   │   ├── tool_registry.py     #   工具注册表
│   │   ├── tool_creator.py      #   工具创建器
│   │   ├── enhanced_tool_creator.py # 增强工具创建器
│   │   ├── tool_auto_generator.py   # 工具自动生成
│   │   ├── tool_performance_analyzer.py # 性能分析器
│   │   └── tool_integration.py  #   工具集成
│   │
│   ├── security/                # 🔒 安全增强
│   │   ├── audit_logger.py      #   审计日志
│   │   ├── sandbox_executor.py  #   沙箱执行
│   │   ├── threat_detector.py   #   威胁检测
│   │   └── permission_manager.py #  权限管理
│   │
│   ├── collaboration/           # 🤝 多Agent协作
│   │   ├── agent_registry.py    #   Agent 注册
│   │   ├── agent_orchestrator.py #  Agent 编排
│   │   ├── task_dispatcher.py   #   任务分发
│   │   └── message_bus.py       #   消息总线
│   │
│   ├── closed_loop/             # 🔄 闭环自主进化
│   │   ├── orchestrator.py      #   进化编排器
│   │   ├── evolution_auditor.py #   📋 自进化审计器 (v5.0.0)
│   │   ├── daemon.py            #   守护进程
│   │   ├── action_executor.py   #   动作执行器
│   │   └── metrics_collector.py #   指标收集器
│   │
│   └── fusion/                  # 🌉 V1/V2/V3 融合桥
│       ├── bridge.py            #   V1V2Bridge 桥接器
│       ├── compatibility.py     #   兼容层/API 网关/降级
│       └── unified_entry.py     #   UnifiedAgent 统一入口
│
├── src/services/                # V2 微服务层
│   ├── core/                    #   核心服务
│   ├── learning/                #   学习服务
│   ├── tools/                   #   工具服务
│   └── system/                  #   系统服务
│
├── hermes-plugin/               # Hermes Agent 插件
│   └── plugin.yaml              #   插件配置 (7 工具 + 1 hook)
│
├── tests/                       # 测试 (24 文件, 439 用例)
│   ├── test_evolution_auditor.py      # 审计器测试 (v5.0.0)
│   ├── test_self_monitor.py
│   ├── test_closed_loop.py
│   ├── test_collaboration.py
│   ├── test_security.py
│   ├── test_fusion.py
│   ├── test_tool_*.py           # 工具相关测试 (6 文件)
│   ├── test_learning_*.py       # 学习相关测试
│   ├── test_memory_*.py         # 记忆相关测试
│   ├── test_iteration*.py       # 迭代集成测试
│   └── test_ci_guards.py
│
├── docs/                        # 文档
│   ├── ARCHITECTURE.md          #   V3 融合架构详解
│   ├── INSTALLATION.md          #   安装指南
│   ├── HERMES_INTEGRATION.md    #   Hermes 集成手册
│   ├── API_REFERENCE.md         #   API 参考
│   ├── TESTING.md               #   测试指南
│   ├── CONFIGURATION.md         #   配置参数
│   ├── QUICKSTART.md            #   快速上手
│   ├── LOGGING.md               #   日志指南
│   ├── RELEASE_CHECKLIST.md     #   发版清单
│   ├── PORTING.md               #   移植指南
│   ├── evolution_plan.md        #   进化路线图
│   ├── v2_architecture.md       #   V2 架构（已归档）
│   └── v2_status_report.md      #   V2 状态报告（已归档）
│
├── data/evolution/              # 本地开发数据库 (gitignored)
├── docker/                      # Docker 配置
├── .github/workflows/           # CI/CD
├── Makefile                     # 构建/测试/检查
├── pyproject.toml               # 项目配置
├── setup.py                     # 打包配置
├── install.sh                   # 一键安装脚本
└── docker-compose.yml           # Docker Compose
```

---

## 8. 行为准则

请保持专业和尊重的沟通。我们致力于为所有参与者提供一个友好、包容的环境。
