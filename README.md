# HermesAgentEvolution

![Version](https://img.shields.io/badge/version-3.0.6-blue)
![Tests](https://img.shields.io/badge/tests-439%20passed-brightgreen)
![CI](https://img.shields.io/badge/CI-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**V1 / V2 / V3 融合架构的 AI 自主进化引擎**

使 AI 助手能够从经验中学习、自动优化策略、持续改进自身能力。专为 HermesAgent 生态设计，也可作为独立库移植到任何 Python 项目中。

---

## ⚡ 5 秒安装

```bash
pip install hermes-agent-evolution && hermes-evolution check
```

---

## 📈 迭代时间线

> 4 天 · 75 次提交 · 10 次迭代 — 从融合架构到自进化审计器

| 版本 | 日期 | 迭代 | 核心成果 |
|------|------|:----:|---------|
| v3.0.0 | 2026-05-06 | 1–5 | V1/V2/V3 融合架构 · CLI 工具 · DB 路径隔离 · 日志统一 · CI/CD |
| v3.0.1 | 2026-05-06 | — | 版本号同步 · 文档刷新 · 422 测试全通过 |
| v3.0.2 | 2026-05-07 | — | 远程仓库同步 · `check` 命令验证 |
| v3.0.3 | 2026-05-07 | 6 | TODO 空壳函数补全 · 文档四件套 · 版本号全项目同步 |
| v3.0.4 | 2026-05-09 | 7–8 | 健康评分修复 · 插件部署审计 · DB 清理回收 1.3GB · 428 测试 |
| v3.0.5 | 2026-05-09 | 9 | ToolStrategyLearner 持久化 · post_tool_call hook 双向记录 |
| **v3.0.6** | **2026-05-09** | **10** | **EvolutionAuditor 自进化审计器 · 双表记录 · 4 查询接口 · 439 测试** |

---

## 📊 项目状态

| 子系统 | 迭代覆盖 | 状态 |
|--------|:--------:|:----:|
| 🧠 经验学习 (`learning/`) | 1–9 | ✅ |
| 🧩 关联记忆 (`memory/`) | 1–7 | ✅ |
| 🛠️ 工具进化 (`tools/`) | 1–6 | ✅ |
| 🔒 安全增强 (`security/`) | 1–4 | ✅ |
| 🤝 多Agent协作 (`collaboration/`) | 1–4 | ✅ |
| 🔄 闭环自主进化 (`closed_loop/`) | 1–8 | ✅ |
| 📊 自我监控 (`self_monitor`) | 1–8 | ✅ |
| 🌉 融合桥 (`fusion/`) | 1–3 | ✅ |
| 📈 工具策略学习 (`tool_strategy_learner`) | 9 | ✅ |
| 📋 自进化审计器 (`evolution_auditor`) | 10 | ✅ |

| 指标 | 数值 |
|------|:----|
| 核心代码 | ~26,561 行 |
| 测试代码 | ~9,700 行 |
| 测试文件 | 24 个 |
| 测试通过 | **439 / 439** (100%) |
| Hermes 工具 | 7 个 |
| 数据库 | 7 个 (SQLite WAL) |
| Python | ≥ 3.9 |

---

## 🏗️ V3 融合架构

```
┌──────────────────────────────────────────────────────────────┐
│                     Hermes Agent / 上层应用                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌────────────────  V1 单体进化引擎 ────────────────┐        │
│   │                                                  │        │
│   │  🧠 learning/    🧩 memory/    🛠️ tools/        │        │
│   │  🔒 security/    🤝 collaboration/               │        │
│   │  🔄 closed_loop/   📊 self_monitor               │        │
│   │  📈 tool_strategy_learner  📋 evolution_auditor  │        │
│   │                                                  │        │
│   └──────────────────────┬───────────────────────────┘        │
│                          │                                    │
│              ┌───────────┴───────────┐                        │
│              │   🔗 融合桥 (Fusion)   │                        │
│              │  bridge · compat · uni │                        │
│              └───────────┬───────────┘                        │
│                          │                                    │
│   ┌──────────────────────┴───────────────────────────┐        │
│   │              V2 微服务层 (services/)               │        │
│   │                                                  │        │
│   │  core/events/    core/services/    core/config/  │        │
│   │  learning/meta/  learning/refl/    learning/rl/  │        │
│   │  tools/discov/   tools/compos/                   │        │
│   │  system/deploy/  system/monitor/  system/test/   │        │
│   └──────────────────────────────────────────────────┘        │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  基础设施: SQLite (WAL) · JSON · Python 3.9+ · Docker       │
└──────────────────────────────────────────────────────────────┘
```

> V1 单体引擎承载核心进化逻辑；V2 微服务提供事件驱动、可水平扩展的服务层；融合桥实现 V1 ↔ V2 双向互通，统一入口零感知切换。

---

## 🧩 10 个子系统简介

| # | 子系统 | 简介 |
|:--:|--------|------|
| 1 | **经验学习** (`learning/`) | 记录 Agent 交互经验，模式识别分析，自动策略生成 |
| 2 | **关联记忆** (`memory/`) | 记忆关联发现，检索性能优化，智能关联推荐 |
| 3 | **工具进化** (`tools/`) | 工具效果分析，动态优化选择，从 API 描述自动创建工具 |
| 4 | **安全增强** (`security/`) | 审计日志追踪，沙箱隔离执行，威胁检测防护 |
| 5 | **多Agent协作** (`collaboration/`) | Agent 注册与发现，任务分发，消息总线 |
| 6 | **闭环自主进化** (`closed_loop/`) | 自动化进化周期：观察→分析→规划→执行→验证→学习 |
| 7 | **自我监控** (`self_monitor`) | 系统健康评分，组件状态检查，趋势报告 |
| 8 | **融合桥** (`fusion/`) | V1↔V2 双向桥接，事件转换，统一入口 |
| 9 | **工具策略学习** (`tool_strategy_learner`) | SQLite 持久化工具调用历史，自动策略推荐 |
| 10 | **自进化审计器** (`evolution_auditor`) | 双表记录进化周期+动作，4 种查询接口，趋势分析 |

---

## 🔧 Hermes 集成工具（7 个）

| 工具 | 功能 |
|------|------|
| `evolution_memory_discover` | 发现记忆之间的关联 |
| `evolution_create_tool` | 从 API 描述自动创建工具 |
| `evolution_run_cycle` | 触发完整进化周期（6 阶段） |
| `evolution_learn` | 记录学习经验与教训 |
| `evolution_self_monitor` | 获取系统健康状态 + 审计摘要 |
| `evolution_audit` | 查询进化审计历史与趋势 |
| `evolution_health_check` | 快速健康检查 |

> 📖 完整集成指南见 **[docs/HERMES_INTEGRATION.md](docs/HERMES_INTEGRATION.md)**

---

## 🗄️ 数据库（7 个）

所有数据库位于 `~/.hermes/data/evolution/`，统一使用 SQLite WAL 模式：

| 数据库 | 用途 |
|--------|------|
| `tools.db` | 工具注册表 |
| `tool_performance.db` | 工具性能指标 |
| `learning_experiences.db` | 学习经验记录 |
| `associations.db` | 记忆关联数据 |
| `retrieval_optimization.db` | 检索优化缓存 |
| `closed_loop.db` | 闭环进化状态 |
| `evolution_audit.db` | 进化审计记录（v3.0.6 新增） |

---

## 🚀 快速上手

### 三步开始

```bash
# 1. 安装
pip install hermes-agent-evolution

# 2. 自检
hermes-evolution check

# 3. 部署插件到 Hermes
cp -r hermes-plugin ~/.hermes/plugins/hermes-evolution/
```

### CLI 命令

```bash
hermes-evolution check      # 环境自检
hermes-evolution setup      # 一键部署插件
hermes-evolution status     # 系统状态
hermes-evolution test       # 运行测试
```

### 基础用法

```python
from evolution.learning.observer import LearningObserver
from evolution.learning.analyzer import ExperienceAnalyzer

observer = LearningObserver()
analyzer = ExperienceAnalyzer(observer)

# 记录经验
observer.record_experience(experience)

# 分析学习
analysis = analyzer.analyze_recent_experiences(days=7)
print(f"成功率: {analysis.success_rate:.1%}")
```

---

## 🔧 Makefile 命令速查

| 命令 | 说明 |
|------|------|
| `make help` | 显示所有可用命令 |
| `make install` | 安装开发依赖（可编辑模式） |
| `make install-min` | 最小安装（仅核心依赖） |
| `make test` | 运行全量测试（快速模式） |
| `make test-v` | 运行全量测试（详细模式） |
| `make test-cov` | 运行测试 + 覆盖率报告 |
| `make test-failed` | 仅重跑上次失败的测试 |
| `make lint` | 代码检查（ruff） |
| `make format` | 代码格式化 |
| `make fix` | 自动修复 lint 问题 |
| `make clean` | 清理构建产物 |
| `make build` | 构建 PyPI 包 |
| `make check` | 环境自检 |
| `make check-all` | 全量检查（lint + test） |
| `make docker-build` | 构建 Docker 镜像 |

---

## 📚 文档索引

| 文档 | 说明 |
|------|------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | V3 融合架构详解 |
| [docs/INSTALLATION.md](docs/INSTALLATION.md) | 详细安装指南 |
| [docs/HERMES_INTEGRATION.md](docs/HERMES_INTEGRATION.md) | Hermes Agent 集成手册 |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | API 参考 |
| [docs/TESTING.md](docs/TESTING.md) | 测试指南 |
| [docs/PORTING.md](docs/PORTING.md) | 移植到其他项目 |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | 配置参数详解 |
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | 5 分钟快速上手 |
| [docs/LOGGING.md](docs/LOGGING.md) | 日志框架指南 |
| [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) | 发版检查清单 |
| [docs/evolution_plan.md](docs/evolution_plan.md) | 进化路线图 |
| [docs/v2_architecture.md](docs/v2_architecture.md) | V2 微服务架构（已归档） |
| [docs/v2_status_report.md](docs/v2_status_report.md) | V2 状态报告（已归档） |

---

## 🤝 贡献

欢迎贡献！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

详见 **[CONTRIBUTING.md](CONTRIBUTING.md)**

---

## 📄 许可证

MIT — 详见 [LICENSE](LICENSE)

---

## 📞 联系

- **问题报告**: [GitHub Issues](https://github.com/WayneLiu519888/Hermes-Agent-EvolutionV3/issues)
- **讨论区**: [GitHub Discussions](https://github.com/WayneLiu519888/Hermes-Agent-EvolutionV3/discussions)

---

*让 AI 助手不断进化，变得更智能、更高效！*
