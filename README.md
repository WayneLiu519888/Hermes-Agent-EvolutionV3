# HermesAgentEvolution

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-3.0.4-blue)
![Tests](https://img.shields.io/badge/tests-422%20passed-brightgreen)
![CI](https://img.shields.io/badge/CI-passing-brightgreen)

**AI 自我进化框架 — V1 / V2 / V3 融合架构**

使 AI 助手能够从经验中学习、自动优化策略、持续改进自身能力。专为 HermesAgent 生态设计，也可作为独立库移植到任何 Python 项目中。

---

## ⚡ 5 秒安装

```bash
pip install hermes-agent-evolution && hermes-evolution setup
```

---

## 🧭 快速了解

| | | | |
|:---:|:---:|:---:|:---:|
| 🧠 **学习进化** | 🛠️ **工具进化** | 🧩 **记忆进化** | 🔒 **安全进化** |
| 记录交互经验 | 分析工具效果 | 关联记忆发现 | 审计日志追踪 |
| 模式识别分析 | 动态优化选择 | 检索性能优化 | 沙箱隔离执行 |
| 自动策略生成 | 自动创建工具 | 智能关联发现 | 威胁检测防护 |

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

## 📊 项目状态

| 模块 | 文件数 | 代码行数 | 测试文件 | 状态 |
|------|:------:|:--------:|:--------:|:----:|
| V1 进化引擎 (`src/evolution/`) | 30 | ~17,500 | 22 | ✅ |
| V2 微服务 (`src/services/`) | 11 | ~7,100 | — | ✅ |
| 融合桥 (`src/evolution/fusion/`) | 3 | ~2,200 | — | ✅ |
| **合计** | **44** | **~26,800** | **22** | **422 passed** |

---

## 🚀 快速上手

### 三步开始

```bash
# 1. 安装
pip install hermes-agent-evolution

# 2. 部署插件到 Hermes
cp -r hermes-plugin ~/.hermes/plugins/hermes-evolution/

# 3. 自检
make check
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

### Hermes 集成工具

| 工具 | 功能 |
|------|------|
| `evolution_run_cycle` | 触发完整进化周期 |
| `evolution_create_tool` | 从 API 描述自动创建工具 |
| `evolution_analyze_performance` | 分析工具性能指标 |
| `evolution_learn` | 记录学习经验/教训 |
| `evolution_self_monitor` | 获取系统健康状态 |
| `evolution_memory_discover` | 发现记忆之间的关联 |

> 📖 完整集成指南见 **[docs/HERMES_INTEGRATION.md](docs/HERMES_INTEGRATION.md)**

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
| [docs/iteration5_engineering_plan.md](docs/iteration5_engineering_plan.md) | 迭代 5 工程计划 |
| [docs/evolution_plan.md](docs/evolution_plan.md) | 进化路线图 |
| [docs/v2_architecture.md](docs/v2_architecture.md) | V2 微服务架构 |
| [docs/v2_status_report.md](docs/v2_status_report.md) | V2 状态报告 |

---

## 🤝 贡献

欢迎贡献！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

---

## 📄 许可证

MIT — 详见 [LICENSE](LICENSE)

---

## 📞 联系

- **问题报告**: [GitHub Issues](https://github.com/WayneLiu519888/Hermes-Agent-EvolutionV3/issues)
- **讨论区**: [GitHub Discussions](https://github.com/WayneLiu519888/Hermes-Agent-EvolutionV3/discussions)

---

*让 AI 助手不断进化，变得更智能、更高效！*
