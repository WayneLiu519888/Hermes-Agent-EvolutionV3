# HermesAgentEvolution

![Version](https://img.shields.io/badge/version-7.0.1-blue)
![Tests](https://img.shields.io/badge/tests-566%20passed-brightgreen)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**HAE — 基于数据消费闭环的 AI 自主进化引擎**

打通了经验写入→关联消费→质量反馈→行为改进的完整闭环。专为 HermesAgent 生态设计，8工具+4Hook。

---

## 迭代时间线

| 版本 | 日期 | 核心成果 |
|------|------|---------|
| v3.0.4 | 2026-05-09 | 健康评分修复 · 插件部署审计 · DB 清理回收 1.3GB |
| v3.0.6 | 2026-05-09 | EvolutionAuditor 自进化审计器 · 10 个子系统 |
| v5.0.0 | 2026-05-11 | V4架构优化 · Hermes原生对齐 · WAL全覆盖 |
| v6.0.0 | 2026-05-11 | OOM根因修复 · discover_all max_entries 防护 |
| **v7.0.1** | **2026-05-11** | **数据消费闭环 · 关联质量打分 · 经验注入 · 8工具+4Hook** |

---

## 项目状态

| 指标 | 数值 |
|------|:----|
| 测试通过 | **566 / 566** (100%) |
| Hermes 工具 | 8 个 |
| Hermes Hook | 4 个 |
| Python | ≥ 3.9 |

---

## Hermes 集成工具（8 个）

| 工具 | 功能 |
|------|------|
| `evolution_memory_discover` | 结构化字段匹配发现记忆关联（tags+content_type+FTS5关键词共现） |
| `evolution_create_tool` | 从 API 描述自动创建工具 |
| `evolution_run_cycle` | 触发完整进化周期（6 阶段） |
| `evolution_learn` | 记录学习经验与教训 |
| `evolution_self_monitor` | 获取系统健康状态 |
| `evolution_audit` | 查询进化审计历史与趋势 |
| `evolution_analyze_performance` | 分析工具性能指标 |
| `evolution_recall_lessons` | V7新增 — 查询历史经验教训，返回可执行行为改进建议 |

## Hermes Hook（4 个）

| Hook | 功能 |
|------|------|
| `post_tool_call` | 工具执行后自动记录经验 |
| `on_session_start` | V7新增 — 会话启动时注入最近失败教训 |
| `pre_llm_call` | V7新增 — LLM调用前注入关联上下文 |
| `post_llm_call` | V7新增 — LLM回复后对关联质量打分 |

---

## 快速上手

```bash
pip install hermes-agent-evolution && hermes-evolution check
```

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 架构详解 |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | 变更日志 |
| [docs/v7_plan.md](docs/v7_plan.md) | V7 设计方案 |
| [docs/v7_dev_plan.md](docs/v7_dev_plan.md) | V7 开发计划 |
| [docs/INSTALLATION.md](docs/INSTALLATION.md) | 安装指南 |
| [docs/HERMES_INTEGRATION.md](docs/HERMES_INTEGRATION.md) | Hermes Agent 集成手册 |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | API 参考 |
| [docs/TESTING.md](docs/TESTING.md) | 测试指南 |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | 贡献指南 |

*让 AI 助手从经验中学习，持续进化。*
