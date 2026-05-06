# HermesAgentEvolution 安装指南

> 版本: v3.0.0 (V1/V2/V3 融合架构)
> 最后更新: 2026-05-06

---

## 目录

1. [系统要求](#1-系统要求)
2. [快速安装](#2-快速安装)
3. [从源码安装](#3-从源码安装)
4. [Docker 部署](#4-docker-部署)
5. [配置指南](#5-配置指南)
6. [验证安装](#6-验证安装)
7. [常见问题](#7-常见问题)

---

## 1. 系统要求

### 最低要求

| 资源 | 要求 |
|------|------|
| **Python** | 3.10 或更高 |
| **操作系统** | Linux / macOS / Windows (WSL2) |
| **内存** | 4 GB RAM |
| **磁盘** | 1 GB 可用空间 |
| **网络** | 需要访问 OpenAI API / Anthropic API (可选) |

### 推荐环境

| 资源 | 推荐 |
|------|------|
| **Python** | 3.11+ |
| **操作系统** | Ubuntu 22.04+ / macOS 13+ |
| **内存** | 8 GB RAM |
| **磁盘** | 5 GB SSD |
| **GPU** | 可选 (用于本地 LLM 推理) |

### 依赖概览

| 依赖 | 最低版本 | 用途 |
|------|----------|------|
| `openai` | 1.0+ | LLM 接口 (可选) |
| `anthropic` | — | Claude API 接口 (可选) |
| `aiohttp` | 3.8+ | 异步 HTTP 请求 |
| `sqlite3` | (内置) | 数据持久化 |
| `prometheus_client` | — | 监控指标 (可选) |

---

## 2. 快速安装

### 2.1 使用 pip

```bash
# 克隆仓库
git clone https://github.com/WayneLiu519888/Hermes-Agent-EvolutionV3.git
cd Hermes-Agent-EvolutionV3

# 创建虚拟环境 (推荐)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2.2 可选的 LLM 功能安装

如果使用基于 LLM 的工具生成功能（如 `create_from_description`、`ToolAutoGenerator` 的 LLM 策略），需要额外安装：

```bash
pip install openai>=1.0.0
# 或
pip install anthropic
```

### 2.3 开发模式安装

```bash
pip install -e ".[dev]"
# 包括: pytest, pytest-cov, black, flake8, mypy 等
```

---

## 3. 从源码安装

### 3.1 克隆仓库

```bash
git clone https://github.com/WayneLiu519888/Hermes-Agent-EvolutionV3.git
cd Hermes-Agent-EvolutionV3
```

### 3.2 项目结构

```
hermes_agent_evolution/
├── src/
│   └── evolution/
│       ├── __init__.py
│       ├── self_monitor.py
│       ├── tools/          # 工具能力层
│       │   ├── __init__.py
│       │   ├── tool_registry.py
│       │   ├── tool_creator.py
│       │   ├── enhanced_tool_creator.py
│       │   ├── tool_performance_analyzer.py
│       │   ├── tool_auto_generator.py
│       │   └── tool_integration.py
│       ├── learning/       # 学习能力层
│       │   ├── __init__.py
│       │   ├── experience.py
│       │   ├── observer.py
│       │   ├── analyzer.py
│       │   ├── pattern_recognizer.py
│       │   └── tool_strategy_learner.py
│       └── memory/         # 记忆系统
│           ├── __init__.py
│           ├── database.py
│           ├── association_discoverer.py
│           ├── association_optimizer.py
│           └── retrieval_optimizer.py
├── data/                   # 数据库文件 (运行时创建)
├── docs/                   # 文档
├── tests/                  # 测试
├── requirements.txt
└── setup.py
```

### 3.3 安装依赖

```bash
pip install -r requirements.txt
```

**`requirements.txt` 内容示例**:

```
# 核心依赖
aiohttp>=3.8.0

# LLM 接口 (可选)
# openai>=1.0.0
# anthropic

# 监控 (可选)
# prometheus-client>=0.17.0

# 开发依赖 (可选)
# pytest>=7.0.0
# pytest-cov>=4.0.0
# black>=23.0.0
# flake8>=6.0.0
# mypy>=1.0.0
```

### 3.4 验证安装

```bash
python -c "from src.evolution.tools import ToolRegistry; print('工具包导入成功')"
python -c "from src.evolution.learning import LearningObserver; print('学习包导入成功')"
```

---

## 4. Docker 部署

### 4.1 使用 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY setup.py .

# 创建数据目录
RUN mkdir -p data

# 设置环境变量
ENV PYTHONPATH=/app/src

# 默认命令
CMD ["python", "-c", "from src.evolution.tools import ToolEvolutionEngine; print('HermesAgentEvolution 就绪')"]
```

### 4.2 构建和运行

```bash
# 构建镜像
docker build -t hermes-agent-evolution .

# 运行容器
docker run -it --rm \
  -v $(pwd)/data:/app/data \
  -e OPENAI_API_KEY=your_key_here \
  hermes-agent-evolution
```

### 4.3 Docker Compose (推荐)

```yaml
version: '3.8'

services:
  evolution:
    build: .
    container_name: hermes-evolution
    volumes:
      - ./data:/app/data
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - LOG_LEVEL=INFO
    restart: unless-stopped

  # 可选: Prometheus 监控
  prometheus:
    image: prom/prometheus:latest
    container_name: hermes-monitor
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    profiles:
      - monitoring
```

### 4.4 环境变量文件 (.env)

```bash
# .env.example
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
LOG_LEVEL=INFO
DB_PATH=data
```

---

## 5. 配置指南

### 5.1 环境变量

| 变量名 | 说明 | 必需 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI API 密钥（用于 LLM 工具生成） | 仅 LLM 功能 |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | 仅 LLM 功能 |
| `LOG_LEVEL` | 日志级别 (DEBUG/INFO/WARNING/ERROR) | 否 |

### 5.2 EvolutionConfig 配置

通过 `EvolutionConfig` 类定制进化引擎行为:

```python
from src.evolution.tools import EvolutionConfig, ToolEvolutionEngine

config = EvolutionConfig(
    auto_evolve=True,              # 是否自动进化
    evolution_interval=3600,       # 进化检查间隔（秒）
    min_performance_score=60.0,    # 触发优化的最低性能分
    max_tool_age_days=30,          # 工具最大寿命（天）
    enable_auto_registration=True, # 自动注册新工具
    enable_performance_monitoring=True,  # 启用性能监控
    enable_optimization=True,      # 启用优化
    learning_integration_enabled=True,   # 集成学习系统
)

engine = ToolEvolutionEngine(config=config)
```

### 5.3 数据库路径配置

```python
# 使用文件数据库（持久化）
registry = ToolRegistry(db_path="data/custom_tools.db")
analyzer = ToolPerformanceAnalyzer(registry, db_path="data/custom_perf.db")

# 使用内存数据库（测试用）
memory_registry = ToolRegistry(db_path=":memory:")

# 学习观察器（自动创建在 data/ 目录）
from src.evolution.learning import LearningObserver
observer = LearningObserver(db_path="data/custom_experiences.db")
```

### 5.4 模式识别器配置

```python
from src.evolution.learning import PatternRecognizer

recognizer = PatternRecognizer(
    min_support=5,          # 最小支持度（出现次数）
    min_confidence=0.8      # 最小置信度
)
```

### 5.5 策略学习器配置

```python
from src.evolution.learning import ToolStrategyLearner

learner = ToolStrategyLearner()
learner.exploration_rate = 0.15  # 探索-利用平衡的探索率
learner.learning_rate = 0.05     # 策略更新学习率
learner.min_samples = 5          # 切换策略前的最少样本数
```

---

## 6. 验证安装

### 6.1 基础验证脚本

```python
"""
verify_installation.py - 验证 HermesAgentEvolution 安装
"""
import sys
import os

# 确保 src 在 Python 路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

def verify():
    errors = []
    
    # 1. 测试工具包导入
    try:
        from evolution.tools import (
            ToolDefinition, ToolRegistry, ToolCategory, ToolStatus,
            ToolCreator, ToolCreationResult,
            EnhancedToolCreator, CreationSource, ToolQuality,
            ToolPerformanceAnalyzer, PerformanceMetric, PerformanceLevel,
            ToolAutoGenerator, GenerationStrategy, ToolGenerationResult,
            ToolEvolutionEngine, EvolutionConfig, EvolutionStatus,
            ToolLearningIntegrator
        )
        print("✅ 工具包导入成功")
    except ImportError as e:
        errors.append(f"工具包导入失败: {e}")
    
    # 2. 测试学习包导入
    try:
        from evolution.learning import (
            Experience, ExperienceType, Outcome,
            LearningObserver,
            ExperienceAnalyzer,
            PatternRecognizer, RecognizedPattern, GeneratedStrategy,
            ToolStrategyLearner, ToolStrategyType, ToolRecommendation
        )
        print("✅ 学习包导入成功")
    except ImportError as e:
        errors.append(f"学习包导入失败: {e}")
    
    # 3. 测试工具注册表功能
    try:
        registry = ToolRegistry(db_path=":memory:")
        tool = ToolDefinition(
            name="test_tool",
            description="A test tool",
            category=ToolCategory.UTILITY
        )
        assert registry.register(tool) == True
        assert registry.get("test_tool") is not None
        assert len(registry.list_all()) == 1
        registry.update_usage_stats("test_tool", success=True)
        stats = registry.get_statistics()
        assert stats["total_tools"] == 1
        assert stats["total_usage"] == 1
        print("✅ 工具注册表功能正常")
    except Exception as e:
        errors.append(f"工具注册表测试失败: {e}")
    
    # 4. 测试经验数据类
    try:
        from evolution.learning import Experience, ExperienceType, Outcome
        exp = Experience(
            id="test-001",
            experience_type=ExperienceType.TOOL_USAGE,
            task_id="task-001",
            outcome=Outcome.SUCCESS
        )
        exp.add_action("test_tool", {"arg": 1}, "result", 0.5)
        exp.add_lesson_learned("Test lesson")
        exp_dict = exp.to_dict()
        assert exp_dict["experience_type"] == "tool_usage"
        assert exp_dict["outcome"] == "success"
        print("✅ 经验数据类功能正常")
    except Exception as e:
        errors.append(f"经验数据类测试失败: {e}")
    
    # 5. 测试工具策略学习器
    try:
        from evolution.learning import ToolStrategyLearner, ToolStrategyType
        learner = ToolStrategyLearner()
        learner.record_tool_usage("tool_a", True, 1.0)
        learner.record_tool_usage("tool_b", False, 3.0)
        recommendations = learner.recommend_tool(
            "test task", ["tool_a", "tool_b"]
        )
        assert len(recommendations) == 2
        # tool_a 应该排在前面（成功率更高）
        assert recommendations[0].tool_name == "tool_a"
        print("✅ 工具策略学习器功能正常")
    except Exception as e:
        errors.append(f"工具策略学习器测试失败: {e}")
    
    # 6. 测试进化引擎
    try:
        engine = ToolEvolutionEngine()
        state = engine.analyze_current_state()
        assert "total_tools" in state
        assert "performance_summaries" in state
        print("✅ 进化引擎初始化正常")
    except Exception as e:
        errors.append(f"进化引擎测试失败: {e}")
    
    # 总结
    print("\n" + "=" * 40)
    if errors:
        print(f"❌ 验证完成，发现 {len(errors)} 个问题:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("✅✅✅ 所有验证通过！HermesAgentEvolution 安装正确。")
        return True

if __name__ == "__main__":
    verify()
```

运行验证:
```bash
python verify_installation.py
```

### 6.2 运行测试套件

```bash
# 运行所有测试
pytest tests/

# 带覆盖率报告
pytest tests/ --cov=src/evolution --cov-report=html

# 运行特定模块测试
pytest tests/test_tools.py -v
pytest tests/test_learning.py -v
```

---

## 7. 常见问题

### Q1: 导入失败，提示 `ModuleNotFoundError: No module named 'evolution'`

**解决方法**: 确保 `src` 目录在 Python 路径中：

```bash
# 方式1: 设置 PYTHONPATH
export PYTHONPATH=/path/to/hermes_agent_evolution/src:$PYTHONPATH

# 方式2: 在脚本开头添加
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
```

### Q2: LLM 功能（工具生成）不可用

**原因**: 未安装 `openai` 或 `anthropic` 包，或未设置 API 密钥。

**解决方法**:
```bash
pip install openai>=1.0.0
export OPENAI_API_KEY=sk-your-key-here
```

系统会自动检测并降级：LLM 策略不可用时，回退到模板策略。

### Q3: 数据库文件位置

默认数据库文件创建在项目根目录的 `data/` 文件夹下：
- `data/tools.db` — 工具注册表
- `data/tool_performance.db` — 工具性能记录
- `data/learning_experiences.db` — 学习经验
- `data/associations.db` — 记忆关联

可通过构造函数参数自定义路径。

### Q4: SQLite 并发写入问题

SQLite 支持并发读取但写入会锁定。如果在高并发场景下使用：
- 使用内存数据库 (`:memory:`) 提升性能
- 考虑迁移到 PostgreSQL 等专业数据库

### Q5: 内存数据库的使用场景

```python
# 测试环境 — 每次运行都是全新的数据库
registry = ToolRegistry(db_path=":memory:")

# 生产环境 — 持久化到文件
registry = ToolRegistry(db_path="data/production_tools.db")
```

### Q6: 如何启用/禁用学习系统集成

学习系统默认启用。如果不需要，在创建进化引擎时关闭：

```python
config = EvolutionConfig(learning_integration_enabled=False)
engine = ToolEvolutionEngine(config=config)
```

缺省学习模块时，系统会自动检测并打印提示。

---

## 附录

- **架构概述**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **API 参考**: [API_REFERENCE.md](API_REFERENCE.md)
- **移植指南**: [PORTING.md](PORTING.md)
- **V2 详细设计**: [ARCHITECTURE_V2.md](ARCHITECTURE_V2.md)
