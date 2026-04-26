# HermesAgentEvolution

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-beta-orange)
![Platform](https://img.shields.io/badge/platform-linux%20%7C%20windows%20%7C%20macos-lightgrey)

**AI助手自我进化系统** — 使AI助手能够从经验中学习并持续改进自身能力。  
本项目专为 HermesAgent 生态设计，同时可作为独立库移植到任何 Python 项目中。

---

## 📖 项目简介

HermesAgentEvolution 是一个元学习（meta-learning）框架，赋予 AI 助手自我进化的能力。核心思想是：

> **AI 助手不应只是静态执行指令，而应记录每次交互的经验，从中学习模式，并自动优化自身策略。**

系统包含三大进化方向：

| 进化方向 | 说明 |
|---------|------|
| 🧠 **学习能力进化** | 记录经验、识别模式、生成改进策略 |
| 🛠️ **工具能力进化** | 分析工具使用效果、动态优化工具选择、自动生成新工具 |
| 🔄 **自我监控** | 系统健康监控、自动反馈循环、持续改进 |

---

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────┐
│                  上层应用 / Agent                     │
├─────────────────────────────────────────────────────┤
│              HermesAgentEvolution 核心层              │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ 学习能力进化   │  │ 记忆系统进化   │  │ 工具能力进化 │ │
│  │              │  │              │  │            │ │
│  │ • Observer   │  │ • Database   │  │ • Registry │ │
│  │ • Analyzer   │  │ • Retrieval  │  │ • Creator  │ │
│  │ • Recognizer │  │ • Assoc.     │  │ • Analyzer │ │
│  │ • Learner    │  │ • Optimizer  │  │ • Generator│ │
│  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘ │
│         │                 │                 │        │
│         └─────────────────┼─────────────────┘        │
│                           │                          │
│                    ┌──────┴──────┐                   │
│                    │ SelfMonitor │  ← 自我监控       │
│                    └─────────────┘                   │
├─────────────────────────────────────────────────────┤
│                    基础设施层                          │
│    SQLite (存储)  ·  JSON (配置)  ·  Python 3.9+     │
└─────────────────────────────────────────────────────┘
```

### 模块结构

```
src/evolution/                    # 进化系统核心
├── __init__.py                   # 包入口
├── self_monitor.py               # 自我监控器
├── learning/                     # 学习能力进化
│   ├── __init__.py
│   ├── experience.py             # 经验数据模型
│   ├── observer.py               # 经验观察者
│   ├── analyzer.py               # 经验分析器
│   ├── pattern_recognizer.py     # 模式识别器
│   └── tool_strategy_learner.py  # 工具策略学习器
├── memory/                       # 记忆系统进化
│   ├── __init__.py
│   ├── database.py               # 经验数据库
│   ├── retrieval_optimizer.py    # 检索优化器
│   ├── association_discoverer.py # 关联发现器
│   └── association_optimizer.py  # 关联优化器
└── tools/                        # 工具能力进化
    ├── __init__.py
    ├── tool_registry.py          # 工具注册表
    ├── tool_creator.py           # 工具创建器
    ├── enhanced_tool_creator.py  # 增强工具创建器
    ├── tool_performance_analyzer.py  # 性能分析器
    ├── tool_auto_generator.py    # 自动生成器
    └── tool_integration.py       # 引擎与集成

tests/                            # 测试目录
├── test_tool_evolution.py
├── test_tool_performance.py
├── test_tool_auto_generator.py
├── test_enhanced_tool_creator.py
├── test_learning_evolution_integration.py
└── test_simple_integration.py

data/                             # 运行时数据（自动创建）
├── tools.db                      # 工具数据库
└── tool_performance.db           # 性能数据库
```

---

## 🚀 安装

### 前置要求

- **Python** >= 3.9
- **pip** (Python 包管理器)
- **sqlite3** (Python 内置，无需额外安装)

### 方法一：一键安装（推荐）

```bash
# 克隆项目
git clone https://github.com/yourusername/HermesAgentEvolution.git
cd HermesAgentEvolution

# 交互式安装
bash setup.sh

# 或直接开发模式
bash setup.sh --dev
```

### 方法二：pip 安装

```bash
cd HermesAgentEvolution

# 开发模式（推荐用于开发）
pip install -e .

# 生产模式
pip install .

# 包含开发依赖（测试等）
pip install -e ".[dev]"

# 包含所有可选依赖
pip install -e ".[full]"
```

### 方法三：仅安装依赖

```bash
pip install -r requirements.txt
```

---

## 💡 使用方法

### 基础用法

```python
from evolution.learning.observer import LearningObserver
from evolution.learning.analyzer import ExperienceAnalyzer
from evolution.learning.tool_strategy_learner import ToolStrategyLearner

# 初始化系统
observer = LearningObserver()
analyzer = ExperienceAnalyzer(observer)
strategy_learner = ToolStrategyLearner()

# 记录经验
observer.record_experience(experience)

# 分析学习
analysis = analyzer.analyze_recent_experiences(days=7)
print(f"成功率: {analysis.success_rate:.1%}")

# 获取工具推荐
recommendations = strategy_learner.recommend_tool(
    "文件操作", ["terminal", "read_file", "write_file"]
)
```

### 工具进化示例

```python
from evolution.tools import (
    ToolRegistry,
    ToolPerformanceAnalyzer,
    ToolEvolutionEngine,
)

# 注册工具
registry = ToolRegistry()
registry.register_tool("web_search", ...)

# 分析工具性能
analyzer = ToolPerformanceAnalyzer()
summary = analyzer.analyze_tool("web_search")
print(f"使用次数: {summary.total_calls}, 成功率: {summary.success_rate:.1%}")

# 启动进化引擎
engine = ToolEvolutionEngine(registry=registry)
engine.start()
```

### 完整示例

详见 [`examples/learning_evolution_demo.py`](examples/learning_evolution_demo.py)。

---

## 🧪 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_learning_evolution_integration.py -v

# 带覆盖率报告
python -m pytest tests/ --cov=src/evolution --cov-report=term-missing
```

---

## 📦 移植说明

本项目的核心设计原则是**高可移植性**。以下是从 HermesAgent 实例迁移到其它项目的步骤：

### 1. 最小移植（仅核心模块）

```bash
# 在目标项目中安装
pip install -e /path/to/hermes_agent_evolution
```

或者直接复制所需子包：

```bash
cp -r src/evolution /your_project/src/evolution
```

### 2. 在 HermesAgent 中集成

```python
# 在 HermesAgent 的 tools 目录添加进化系统
# hermes_agent/
#   tools/
#     evolution/   →  符号链接或复制
#   agent.py       →  集成 LearningObserver

from evolution.learning.observer import LearningObserver
from evolution.self_monitor import SelfMonitor

class HermesAgent:
    def __init__(self):
        self.observer = LearningObserver()
        self.monitor = SelfMonitor()

    def execute_tool(self, tool_name, params):
        # 记录经验
        self.observer.record_experience({
            "tool": tool_name,
            "params": params,
            "timestamp": datetime.now()
        })
        result = super().execute_tool(tool_name, params)
        # 记录结果
        self.observer.update_outcome(tool_name, result.success)
        return result
```

### 3. 依赖说明

| 依赖 | 类型 | 说明 |
|------|------|------|
| sqlite3 | 内置 | Python 标准库，无需安装 |
| json | 内置 | Python 标准库 |
| datetime | 内置 | Python 标准库 |
| dataclasses | 内置 | Python 3.9+ 内置 |
| pytest | 开发 | 仅测试需要 |
| requests | 可选 | 飞书通知（默认使用 simulated 模式） |
| numpy | 可选 | 高级数据分析 |
| scikit-learn | 可选 | 机器学习模式识别 |

> **核心模块零外部依赖！** 仅使用 Python 标准库即可运行。

### 4. 配置数据库路径

```python
# 自定义数据存储位置
observer = LearningObserver(db_path="./custom_data/experiences.db")

# 或使用内存数据库（测试用）
observer = LearningObserver(db_path=":memory:")
```

---

## 🔧 配置

### 飞书通知（可选）

```json
{
    "mode": "webhook",
    "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
    "fallback_mode": "simulated"
}
```

### 自定义数据库

```python
observer = LearningObserver(db_path="/custom/path/database.db")
```

---

## 📈 项目状态

### ✅ 已完成
- 学习能力进化（经验观察、分析、模式识别、策略学习）
- 工具能力进化（注册、创建、性能分析、自动生成）
- 记忆系统进化（存储、检索优化、关联发现）
- 自我监控与反馈循环
- 集成测试框架
- pip 安装支持

### 🔄 进行中
- 文档完善和示例丰富

### ⏳ 计划中
- 模式识别强化和自动策略生成
- 跨会话持久学习
- Web 管理界面

---

## 🤝 贡献

欢迎贡献！请查看[贡献指南](CONTRIBUTING.md)了解如何参与。

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 — 详见 [LICENSE](LICENSE) 文件。

---

## 📞 联系

- **问题报告**: [GitHub Issues](https://github.com/yourusername/HermesAgentEvolution/issues)
- **讨论区**: [GitHub Discussions](https://github.com/yourusername/HermesAgentEvolution/discussions)
- **文档**: [项目Wiki](https://github.com/yourusername/HermesAgentEvolution/wiki)

---

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者！

---

*让AI助手不断进化，变得更智能、更高效！*
