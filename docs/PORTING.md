# HermesAgentEvolution 移植指南

> 版本: v3.0.6
> 最后更新: 2026-05-09

---

## 目录

1. [概述](#1-概述)
2. [自定义工具开发](#2-自定义工具开发)
3. [集成到现有项目](#3-集成到现有项目)
4. [定制学习系统](#4-定制学习系统)
5. [扩展和插件开发](#5-扩展和插件开发)
6. [数据库迁移](#6-数据库迁移)
7. [多语言移植](#7-多语言移植)

---

## 1. 概述

本指南涵盖四种主要的移植/扩展场景：

| 场景 | 说明 | 难度 |
|------|------|:--:|
| **场景 A**: 自定义工具开发 | 在现有框架内创建新工具 | ⭐ |
| **场景 B**: 集成到现有项目 | 将 HermesAgentEvolution 作为模块嵌入 | ⭐⭐ |
| **场景 C**: 深度定制 | 替换核心组件、添加新能力 | ⭐⭐⭐ |
| **场景 D**: 跨语言移植 | 将核心设计移植到其他语言 | ⭐⭐⭐ |

---

## 2. 自定义工具开发

### 2.1 从函数创建工具

```python
from evolution.tools import ToolRegistry, ToolCreator, ToolCategory

registry = ToolRegistry()
creator = ToolCreator(registry)

def calculate_sentiment(text: str) -> dict:
    """
    分析文本情感。

    Args:
        text: 待分析的文本

    Returns:
        dict: 包含情感评分和关键词的字典
    """
    positive_words = ["good", "great", "excellent", "happy"]
    negative_words = ["bad", "terrible", "sad", "angry"]

    words = text.lower().split()
    pos_count = sum(1 for w in words if w in positive_words)
    neg_count = sum(1 for w in words if w in negative_words)

    score = (pos_count - neg_count) / max(len(words), 1)
    return {"score": score, "positive": pos_count, "negative": neg_count}

result = creator.create_from_function(
    func=calculate_sentiment,
    name="sentiment_analyzer",
    description="分析文本情感倾向",
    category=ToolCategory.AI,
    tags=["nlp", "sentiment", "text-analysis"]
)

if result.success:
    print(f"工具创建成功: {result.tool_definition.name}")
else:
    print(f"创建失败: {result.error_message}")
```

### 2.2 使用增强创建器（6 种方式）

```python
from evolution.tools import EnhancedToolCreator, ToolRegistry, ToolCategory

registry = ToolRegistry()
creator = EnhancedToolCreator(registry)

# 方式1: 从函数创建
result = creator.create_from_function(my_func, name="my_tool")

# 方式2: 从代码字符串创建
code = """
def greet(name: str) -> str:
    return f"Hello, {name}!"
"""
result = creator.create_from_code(code, name="greeter",
                                  description="Simple greeting tool",
                                  category=ToolCategory.UTILITY)

# 方式3: 从描述创建（需要 LLM 支持）
result = creator.create_from_description(
    description="创建一个工具，用于查询天气信息",
    name="weather_query",
    category=ToolCategory.NETWORK
)

# 方式4: 从模板创建
result = creator.create_from_template(
    template_name="http_client",
    params={"method": "GET", "base_url": "https://api.example.com"},
    name="api_client",
    category=ToolCategory.NETWORK
)

# 方式5: 克隆现有工具
result = creator.create_from_existing(
    source_name="existing_tool",
    modifications={"description": "Modified version"},
    new_name="existing_tool_v2"
)

# 方式6: 进化创建
result = creator.create_from_evolution(
    source_name="slow_tool",
    evolution_goal="优化性能，减少执行时间"
)
```

### 2.3 添加性能监控

```python
from evolution.tools import ToolPerformanceAnalyzer

analyzer = ToolPerformanceAnalyzer(registry, db_path="tool_performance.db")

# 记录工具执行性能
analyzer.record_performance(
    tool_name="my_tool",
    metric="execution_time",
    value=0.125,
    metadata={"success": True}
)
```

---

## 3. 集成到现有项目

### 3.1 作为模块集成

```python
# 在你的项目中
import sys
sys.path.insert(0, "/path/to/hermes_agent_evolution/src")

from evolution.tools import ToolRegistry
from evolution.learning.observer import LearningObserver
from evolution.learning.tool_strategy_learner import ToolStrategyLearner
from evolution.db_utils import get_evolution_db

class YourApplication:
    def __init__(self):
        # 使用自定义数据库路径避免冲突
        self.registry = ToolRegistry()
        self.observer = LearningObserver()

        # v3.0.6: ToolStrategyLearner 需要 db_path 参数
        self.learner = ToolStrategyLearner(db_path="tools.db")

    def register_app_tools(self):
        """注册你的应用特有工具"""
        self.registry.register("app_tool", my_func, category="utility")

    def record_interaction(self, tool_name, params, output, success):
        """记录一次交互"""
        # 记录经验
        self.observer.record_experience(
            tool_name=tool_name,
            input_params=params,
            output=output,
            duration_ms=0.5,
            success=success,
            context={"app": "YourApplication"}
        )

        # 驱动策略学习器记录
        self.learner.record_tool_usage(
            tool_name=tool_name,
            success=success,
            execution_time=0.5,
            context={"params": str(params)[:200]}
        )

    def get_tool_recommendation(self, task_description: str):
        """获取工具推荐"""
        tools = self.registry.list_all()
        available = [t["name"] for t in tools if t.get("status") == "active"]

        return self.learner.recommend_tool(
            task_description=task_description,
            available_tools=available
        )
```

### 3.2 与 Web 框架集成 (Flask)

```python
from flask import Flask, jsonify, request
from evolution.tools import ToolRegistry, EnhancedToolCreator, ToolCategory

app = Flask(__name__)
registry = ToolRegistry()

@app.route("/api/tools", methods=["GET"])
def list_tools():
    tools = registry.list_all()
    return jsonify(tools)

@app.route("/api/tools", methods=["POST"])
def create_tool():
    data = request.json
    creator = EnhancedToolCreator(registry)

    result = creator.create_from_description(
        description=data["description"],
        name=data["name"],
        category=ToolCategory(data.get("category", "custom"))
    )

    return jsonify({
        "success": result.success,
        "tool": result.tool_definition.to_dict() if result.success else None,
        "error": result.error_message
    })
```

### 3.3 与 asyncio 应用集成

```python
import asyncio
from evolution.learning.observer import LearningObserver
from evolution.learning.tool_strategy_learner import ToolStrategyLearner

class AsyncEvolutionApp:
    def __init__(self):
        self.observer = LearningObserver()
        self.learner = ToolStrategyLearner(db_path="tools.db")
        self._running = False

    async def record_loop(self, interval: int = 3600):
        """后台记录循环"""
        self._running = True
        while self._running:
            # 异步记录交互
            await asyncio.to_thread(
                self.learner.record_tool_usage,
                tool_name="background_tool",
                success=True,
                execution_time=0.1
            )
            await asyncio.sleep(interval)

    async def stop(self):
        self._running = False
```

---

## 4. 定制学习系统

### 4.1 自定义模式识别策略

```python
from evolution.learning import PatternRecognizer, RecognizedPattern
from evolution.learning.experience import Experience

class CustomPatternRecognizer(PatternRecognizer):
    """支持自定义领域特定模式"""

    def __init__(self, domain: str, **kwargs):
        super().__init__(**kwargs)
        self.domain = domain

    def recognize(self, experiences):
        # 先调用父类通用模式识别
        patterns = super().recognize(experiences)

        # 添加领域特定模式
        if self.domain == "financial":
            patterns.extend(self._recognize_financial(experiences))

        return patterns

    def _recognize_financial(self, experiences):
        patterns = []
        for exp in experiences:
            if "risk_level" in exp.context:
                pattern = RecognizedPattern(
                    pattern_id=f"fin_{exp.id}",
                    description=f"金融风险模式: {exp.context.get('risk_level')}",
                    confidence=0.8,
                    support_count=1,
                )
                patterns.append(pattern)
        return patterns
```

### 4.2 自定义经验分析器

```python
from evolution.learning import ExperienceAnalyzer

class CustomExperienceAnalyzer(ExperienceAnalyzer):
    """添加自定义分析指标"""

    def _perform_analysis(self, experiences):
        base_result = super()._perform_analysis(experiences)

        # 计算工具组合效率
        tool_combinations = {}
        for exp in experiences:
            tools_used = tuple(
                a["tool_name"] for a in exp.actions if "tool_name" in a
            )
            if tools_used:
                tool_combinations.setdefault(tools_used, []).append(
                    exp.outcome == "success"
                )

        for combo, outcomes in tool_combinations.items():
            if len(outcomes) >= 3:
                success_rate = sum(outcomes) / len(outcomes)
                if success_rate > 0.8:
                    base_result.key_insights.append(
                        f"高效工具组合 {combo} ({success_rate:.0%})"
                    )
        return base_result
```

---

## 5. 扩展和插件开发

### 5.1 添加新的创建来源

```python
from evolution.tools import EnhancedToolCreator, ToolCreationResult, ToolCategory
from evolution.tools.tool_registry import ToolDefinition

class ExtendedToolCreator(EnhancedToolCreator):
    """扩展创建器，支持更多来源"""

    def create_from_database(self, db_config: dict, table_name: str,
                             name: str) -> ToolCreationResult:
        """从数据库表结构创建工具"""
        try:
            code = self._generate_crud_code(table_name)
            tool = ToolDefinition(
                name=name,
                description=f"从数据库表 {table_name} 生成的 CRUD 工具",
                category=ToolCategory.DATA_PROCESSING,
                source_code=code,
                tags=["database", "auto-generated", table_name]
            )

            success = self.registry.register(tool)
            return ToolCreationResult(
                success=success,
                tool_definition=tool if success else None
            )
        except Exception as e:
            return ToolCreationResult(success=False, error_message=str(e))

    def _generate_crud_code(self, table_name: str) -> str:
        """生成 CRUD 操作代码"""
        return f"# Auto-generated CRUD for {table_name}\ndef query_{table_name}(): ..."
```

---

## 6. 数据库迁移

### 6.1 数据导出和导入

```python
import json
from evolution.tools import ToolRegistry

def export_tools_to_json(registry: ToolRegistry, filepath: str):
    """导出工具到 JSON 文件"""
    tools = registry.list_all()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(tools, f, ensure_ascii=False, indent=2)
    print(f"已导出 {len(tools)} 个工具到 {filepath}")


def import_tools_from_json(registry: ToolRegistry, filepath: str):
    """从 JSON 文件导入工具"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    imported = 0
    for item in data:
        tool = ToolDefinition.from_dict(item)
        if registry.register(tool):
            imported += 1

    print(f"成功导入 {imported}/{len(data)} 个工具")

# 用法
registry = ToolRegistry()
export_tools_to_json(registry, "tools_backup.json")
import_tools_from_json(registry, "tools_backup.json")
```

### 6.2 从 SQLite 迁移到 PostgreSQL

v3.0.6 使用纯 SQLite（7 个数据库 + WAL 模式），已足够支撑大多数场景。如需迁移到 PostgreSQL，请参考以下接口适配：

```python
import psycopg2

class PostgresToolRegistry:
    """PostgreSQL 版工具注册表"""

    def __init__(self, conn_string: str):
        self.conn_string = conn_string
        self._init_database()

    def _init_database(self):
        conn = psycopg2.connect(self.conn_string)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tools (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                description TEXT NOT NULL,
                category VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL,
                version VARCHAR(50) NOT NULL,
                parameters JSONB NOT NULL DEFAULT '{}',
                tags JSONB NOT NULL DEFAULT '[]',
                source_code TEXT NOT NULL DEFAULT '',
                is_builtin BOOLEAN DEFAULT FALSE
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()

    # 实现 register / get / list_all / search 等方法...
```

---

## 7. 多语言移植

### 7.1 架构对齐指南

| Python 组件 | 等效概念 (其他语言) |
|-------------|---------------------|
| `@dataclass` | 结构体/记录类型 (Rust struct, Go struct, Java record) |
| `Enum` | 枚举（所有主流语言支持） |
| `sqlite3` + WAL | SQLite 绑定 (rusqlite, Go database/sql) |
| `logging` | 各语言日志框架 (log, slog, log4j) |
| `Optional` / `Dict` / `List` | 泛型/可选类型 |

### 7.2 核心接口速查

移植时按以下优先级实现：

1. **ToolRegistry** — 工具注册/查询/搜索 (CRUD)
2. **LearningObserver** — 经验记录与统计
3. **ToolStrategyLearner** — 策略学习与持久化
4. **EvolutionDatabase** — 关联存储与检索

### 7.3 Rust 示例

```rust
// tool_registry.rs — Rust 版工具注册表核心
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct ToolDefinition {
    pub name: String,
    pub description: String,
    pub category: String,
    pub status: String,
    pub version: String,
    pub tags: Vec<String>,
    pub source_code: String,
}

pub struct ToolRegistry {
    tools: HashMap<String, ToolDefinition>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        ToolRegistry { tools: HashMap::new() }
    }

    pub fn register(&mut self, tool: ToolDefinition) -> bool {
        self.tools.insert(tool.name.clone(), tool);
        true
    }

    pub fn get(&self, name: &str) -> Option<&ToolDefinition> {
        self.tools.get(name)
    }

    pub fn list_all(&self) -> Vec<&ToolDefinition> {
        self.tools.values().collect()
    }
}
```

### 7.4 TypeScript 示例

```typescript
// tool_registry.ts — TypeScript 版工具注册表
interface ToolDefinition {
  name: string;
  description: string;
  category: string;
  status: string;
  version: string;
  tags: string[];
  sourceCode: string;
}

class ToolRegistry {
  private tools: Map<string, ToolDefinition> = new Map();

  register(tool: ToolDefinition): boolean {
    this.tools.set(tool.name, tool);
    return true;
  }

  get(name: string): ToolDefinition | undefined {
    return this.tools.get(name);
  }

  listAll(): ToolDefinition[] {
    return Array.from(this.tools.values());
  }

  search(query: string): ToolDefinition[] {
    const q = query.toLowerCase();
    return Array.from(this.tools.values()).filter(t =>
      t.name.toLowerCase().includes(q) ||
      t.description.toLowerCase().includes(q)
    );
  }
}
```

---

## 参见

- [安装指南](INSTALLATION.md) — pip/源码/Docker 安装
- [架构概述](ARCHITECTURE.md) — V3 融合架构详解
- [配置说明](CONFIGURATION.md) — 环境变量与调优
- [快速上手](QUICKSTART.md) — 5 分钟开始使用
