# HermesAgentEvolution 移植指南

> 版本: v2 (Iteration 3)
> 最后更新: 2026-04-24

---

## 目录

1. [概述](#1-概述)
2. [自定义工具开发](#2-自定义工具开发)
3. [集成到现有项目](#3-集成到现有项目)
4. [定制学习系统](#4-定制学习系统)
5. [扩展和插件开发](#5-扩展和插件开发)
6. [数据库迁移](#6-数据库迁移)
7. [API 适配器模式](#7-api-适配器模式)
8. [多语言/跨语言移植](#8-多语言跨语言移植)

---

## 1. 概述

本指南涵盖三种主要的移植/扩展场景：

| 场景 | 说明 | 难度 |
|------|------|------|
| **场景 A**: 自定义工具开发 | 在现有框架内创建新的工具 | ⭐ |
| **场景 B**: 集成到现有项目 | 将 HermesAgentEvolution 作为模块嵌入 | ⭐⭐ |
| **场景 C**: 深度定制 | 替换核心组件、添加新能力 | ⭐⭐⭐ |

---

## 2. 自定义工具开发

### 2.1 从函数创建工具

最简方式——只需定义一个 Python 函数：

```python
from evolution.tools import ToolCreator, ToolRegistry, ToolCategory

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
    # 简易实现
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

### 2.2 使用增强创建器（6种方式）

```python
from evolution.tools import EnhancedToolCreator, ToolRegistry, ToolCategory

registry = ToolRegistry()
creator = EnhancedToolCreator(registry)

# 方式1: 从函数创建
result = creator.create_from_function(my_func, name="my_tool", ...)

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
from evolution.tools import ToolPerformanceAnalyzer, monitor_performance

analyzer = ToolPerformanceAnalyzer(registry)

# 使用装饰器自动捕获性能数据
@monitor_performance(analyzer, tool_name="my_tool")
def my_tool_function(param1: str, param2: int) -> str:
    # 你的工具逻辑
    return f"Processed: {param1} x {param2}"
```

### 2.4 注册自定义模板

```python
from evolution.tools import ToolAutoGenerator

generator = ToolAutoGenerator(registry)

# 模板结构
custom_template = {
    "name": "data_transformer",
    "description": "数据转换工具模板",
    "code_template": """
def {name}(data: list, transform_type: str = "{default_transform}") -> list:
    \"\"\"
    {description}
    
    Args:
        data: 输入数据列表
        transform_type: 转换类型 ({transform_options})
        
    Returns:
        list: 转换后的数据列表
    \"\"\"
    transforms = {transforms_dict}
    transform_fn = transforms.get(transform_type, lambda x: x)
    return [transform_fn(item) for item in data]
""",
    "parameters": {
        "default_transform": "identity",
        "transform_options": "identity, normalize, scale",
        "transforms_dict": {
            "identity": "lambda x: x",
            "normalize": "lambda x: x / max(data) if data else x",
            "scale": "lambda x: x * 2"
        }
    }
}

# 使用自定义模板
result = generator.generate_from_template(
    template_name="data_transformer",
    params={
        "name": "double_values",
        "description": "将列表中的每个值加倍",
        "default_transform": "scale"
    }
)
```

---

## 3. 集成到现有项目

### 3.1 作为子模块集成

```python
# 在你的项目中
import sys
import os

# 添加 HermesAgentEvolution 到路径
sys.path.insert(0, "/path/to/hermes_agent_evolution/src")

from evolution.tools import ToolEvolutionEngine, ToolRegistry

class YourApplication:
    def __init__(self):
        # 使用自定义数据库路径避免冲突
        self.registry = ToolRegistry(db_path="my_app_tools.db")
        self.engine = ToolEvolutionEngine(registry=self.registry)
    
    def register_app_tools(self):
        """注册你的应用特有工具"""
        # ... 注册自定义工具
    
    def run_evolution_if_needed(self):
        """按需运行进化周期"""
        state = self.engine.analyze_current_state()
        print(f"当前工具数: {state['total_tools']}")
        
        if state['total_tools'] > 0:
            result = self.engine.run_evolution_cycle()
            return result
        return None
    
    def get_tool_suggestions(self, task_description: str):
        """获取工具推荐"""
        from evolution.learning import ToolStrategyLearner
        
        learner = ToolStrategyLearner()
        tools = self.registry.list_all()
        available = [t.name for t in tools if t.status.value == "active"]
        
        # 加载历史性能数据
        for tool in tools:
            if tool.usage_count > 0:
                learner.record_tool_usage(
                    tool_name=tool.name,
                    success=(tool.success_count / max(tool.usage_count, 1) > 0.5),
                    execution_time=1.0,
                )
        
        return learner.recommend_tool(
            task_description=task_description,
            available_tools=available
        )
```

### 3.2 与 Web 框架集成

```python
# Flask 集成示例
from flask import Flask, jsonify, request
from evolution.tools import ToolEvolutionEngine, ToolRegistry

app = Flask(__name__)
registry = ToolRegistry(db_path="data/web_tools.db")
engine = ToolEvolutionEngine(registry=registry)

@app.route("/api/tools", methods=["GET"])
def list_tools():
    category = request.args.get("category")
    tools = registry.list_all(category=category)
    return jsonify([t.to_dict() for t in tools])

@app.route("/api/tools", methods=["POST"])
def create_tool():
    data = request.json
    from evolution.tools import EnhancedToolCreator, ToolCategory
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

@app.route("/api/evolve", methods=["POST"])
def trigger_evolution():
    result = engine.run_evolution_cycle()
    return jsonify(result)

@app.route("/api/report", methods=["GET"])
def get_report():
    report = engine.generate_evolution_report()
    return jsonify({"report": report})
```

### 3.3 与 asyncio 应用集成

```python
import asyncio
from evolution.tools import ToolEvolutionEngine

class AsyncEvolutionApp:
    def __init__(self):
        self.engine = ToolEvolutionEngine()
        self._running = False
    
    async def start_evolution_loop(self, interval: int = 3600):
        """后台进化循环"""
        self._running = True
        while self._running:
            print("运行进化周期...")
            result = await asyncio.to_thread(self.engine.run_evolution_cycle)
            
            if result.get("success"):
                print(f"进化完成: {len(result.get('optimizations', []))} 项优化")
            else:
                print(f"进化失败: {result.get('error')}")
            
            await asyncio.sleep(interval)
    
    async def stop(self):
        self._running = False

# 使用
async def main():
    app = AsyncEvolutionApp()
    await app.start_evolution_loop(interval=1800)  # 每30分钟

asyncio.run(main())
```

---

## 4. 定制学习系统

### 4.1 自定义模式识别策略

```python
from evolution.learning import PatternRecognizer, PatternCategory, RecognizedPattern

class CustomPatternRecognizer(PatternRecognizer):
    """支持自定义领域特定模式"""
    
    def __init__(self, domain: str, **kwargs):
        super().__init__(**kwargs)
        self.domain = domain
        self.domain_patterns = {
            "financial": self._recognize_financial_patterns,
            "healthcare": self._recognize_healthcare_patterns,
        }
    
    def recognize(self, experiences):
        # 先调用父类通用模式识别
        patterns = super().recognize(experiences)
        
        # 再添加领域特定模式
        domain_fn = self.domain_patterns.get(self.domain)
        if domain_fn:
            domain_patterns = domain_fn(experiences)
            patterns.extend(domain_patterns)
        
        return patterns
    
    def _recognize_financial_patterns(self, experiences):
        """金融领域特定模式"""
        patterns = []
        for exp in experiences:
            if "risk_level" in exp.context:
                # 识别风险相关模式
                pattern = RecognizedPattern(
                    pattern_id=f"fin_{exp.id}",
                    category=PatternCategory.CONTEXTUAL_PATTERN,
                    description=f"金融风险模式: {exp.context.get('risk_level')}",
                    confidence=0.8,
                    support_count=1,
                    conditions={"risk_level": exp.context["risk_level"]},
                    examples=[exp.id],
                    implications=["需要更保守的工具选择策略"]
                )
                patterns.append(pattern)
        return patterns
    
    def _recognize_healthcare_patterns(self, experiences):
        """医疗领域特定模式"""
        # ... 实现医疗领域模式识别
        return []

# 使用自定义识别器
recognizer = CustomPatternRecognizer(
    domain="financial",
    min_support=3,
    min_confidence=0.7
)
```

### 4.2 自定义经验分析器

```python
from evolution.learning import ExperienceAnalyzer, AnalysisResult
from evolution.learning.experience import Experience, Outcome

class CustomExperienceAnalyzer(ExperienceAnalyzer):
    """添加自定义分析指标"""
    
    def _perform_analysis(self, experiences):
        # 调用父类基础分析
        base_result = super()._perform_analysis(experiences)
        
        # 添加自定义指标
        custom_insights = self._calculate_custom_metrics(experiences)
        base_result.key_insights.extend(custom_insights)
        
        return base_result
    
    def _calculate_custom_metrics(self, experiences):
        """计算自定义业务指标"""
        insights = []
        
        # 计算工具组合效率
        tool_combinations = {}
        for exp in experiences:
            tools_used = tuple(
                a["tool_name"] for a in exp.actions 
                if "tool_name" in a
            )
            if tools_used in tool_combinations:
                tool_combinations[tools_used].append(exp.outcome == Outcome.SUCCESS)
            else:
                tool_combinations[tools_used] = [exp.outcome == Outcome.SUCCESS]
        
        for combo, outcomes in tool_combinations.items():
            if len(outcomes) >= 3:  # 至少3个样本
                success_rate = sum(outcomes) / len(outcomes)
                if success_rate > 0.8:
                    insights.append(
                        f"工具组合 {combo} 高效 ({success_rate:.0%} 成功率)"
                    )
                elif success_rate < 0.3:
                    insights.append(
                        f"工具组合 {combo} 低效 ({success_rate:.0%} 成功率)，建议替换"
                    )
        
        return insights
```

---

## 5. 扩展和插件开发

### 5.1 添加新的创建来源

```python
from evolution.tools import EnhancedToolCreator, CreationSource, ToolCreationResult
from evolution.tools.tool_registry import ToolDefinition, ToolCategory
from enum import Enum

class CustomCreationSource(Enum):
    """自定义创建来源"""
    DATABASE_IMPORT = "database_import"
    API_IMPORT = "api_import"

class ExtendedToolCreator(EnhancedToolCreator):
    """扩展创建器，支持更多来源"""
    
    def create_from_database(self, db_config: dict, table_name: str, 
                              name: str) -> ToolCreationResult:
        """从数据库表结构创建工具"""
        try:
            # 1. 读取表结构
            # schema = self._read_table_schema(db_config, table_name)
            
            # 2. 生成代码
            code = self._generate_crud_code(table_name, schema)
            
            # 3. 创建工具定义
            tool = ToolDefinition(
                name=name,
                description=f"从数据库表 {table_name} 生成的 CRUD 工具",
                category=ToolCategory.DATA_PROCESSING,
                source_code=code,
                tags=["database", "auto-generated", table_name]
            )
            
            # 4. 注册
            success = self.registry.register(tool)
            
            return ToolCreationResult(
                success=success,
                tool_definition=tool if success else None
            )
        except Exception as e:
            return ToolCreationResult(
                success=False,
                error_message=str(e)
            )
    
    def _generate_crud_code(self, table_name: str, schema: dict) -> str:
        """生成 CRUD 操作代码"""
        # ... 实现代码生成
        return f"# Auto-generated CRUD for {table_name}\n..."
```

### 5.2 添加新的性能指标

```python
from evolution.tools import PerformanceMetric, ToolPerformanceAnalyzer
from enum import Enum

class ExtendedMetric(Enum):
    """扩展性能指标"""
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    USER_SATISFACTION = "user_satisfaction"

class ExtendedPerformanceAnalyzer(ToolPerformanceAnalyzer):
    """支持更多性能指标的分析器"""
    
    def record_extended_metric(self, tool_name: str, 
                                metric: ExtendedMetric,
                                value: float):
        """记录扩展指标"""
        # 映射到通用指标存储
        return self.record_performance(
            tool_name=tool_name,
            metric=PerformanceMetric.RESOURCE_USAGE,
            value=value,
            context={"extended_metric": metric.value}
        )
```

---

## 6. 数据库迁移

### 6.1 从 SQLite 迁移到 PostgreSQL

由于默认使用 SQLite，如果需要更高并发或分布式部署，可以适配其他数据库。

```python
import psycopg2
from evolution.tools.tool_registry import ToolDefinition, ToolCategory, ToolStatus
from typing import Dict, List, Optional, Any
import json


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
                author VARCHAR(255) NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                parameters JSONB NOT NULL DEFAULT '{}',
                return_type VARCHAR(100) NOT NULL DEFAULT 'Any',
                dependencies JSONB NOT NULL DEFAULT '[]',
                tags JSONB NOT NULL DEFAULT '[]',
                source_code TEXT NOT NULL DEFAULT '',
                is_builtin BOOLEAN DEFAULT FALSE
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
    
    def register(self, tool: ToolDefinition) -> bool:
        conn = psycopg2.connect(self.conn_string)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO tools 
                (name, description, category, status, version, author,
                 created_at, updated_at, parameters, return_type,
                 dependencies, tags, source_code, is_builtin)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET
                    description = EXCLUDED.description,
                    category = EXCLUDED.category,
                    status = EXCLUDED.status,
                    version = EXCLUDED.version,
                    updated_at = EXCLUDED.updated_at,
                    parameters = EXCLUDED.parameters,
                    source_code = EXCLUDED.source_code
            """, (
                tool.name, tool.description, tool.category.value,
                tool.status.value, tool.version, tool.author,
                tool.created_at, tool.updated_at,
                json.dumps(tool.parameters), tool.return_type,
                json.dumps(tool.dependencies), json.dumps(tool.tags),
                tool.source_code, tool.is_builtin
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"注册失败: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    # ... 实现 get(), list_all(), search() 等方法
```

### 6.2 数据导出和导入

```python
import json
from evolution.tools import ToolRegistry


def export_tools_to_json(registry: ToolRegistry, filepath: str):
    """导出工具到 JSON 文件"""
    tools = registry.list_all()
    data = [t.to_dict() for t in tools]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
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
registry = ToolRegistry(db_path="old_tools.db")
export_tools_to_json(registry, "tools_backup.json")

new_registry = ToolRegistry(db_path="new_tools.db")
import_tools_from_json(new_registry, "tools_backup.json")
```

---

## 7. API 适配器模式

### 7.1 为其他 Agent 框架提供适配器

```python
class LangChainToolAdapter:
    """将 LangChain 工具适配为 HermesAgentEvolution 工具"""
    
    def __init__(self, registry):
        self.registry = registry
    
    def import_langchain_tool(self, langchain_tool) -> bool:
        """导入 LangChain 工具"""
        from evolution.tools import (
            ToolDefinition, ToolCategory, ToolStatus
        )
        
        tool = ToolDefinition(
            name=langchain_tool.name,
            description=langchain_tool.description,
            category=self._map_category(langchain_tool),
            status=ToolStatus.ACTIVE,
            parameters=self._extract_args(langchain_tool),
            return_type="str",
            tags=["langchain", "imported"],
            is_builtin=False
        )
        
        return self.registry.register(tool)
    
    def _map_category(self, langchain_tool):
        from evolution.tools import ToolCategory
        # 类别映射逻辑
        return ToolCategory.UTILITY
    
    def _extract_args(self, langchain_tool):
        """提取 LangChain 工具参数"""
        args = {}
        if hasattr(langchain_tool, 'args'):
            for name, field in langchain_tool.args.items():
                args[name] = {
                    "type": str(field.type_),
                    "description": field.description,
                    "required": True
                }
        return args


class CrewAIToolAdapter:
    """将 CrewAI 工具适配为 HermesAgentEvolution 工具"""
    
    def __init__(self, registry):
        self.registry = registry
    
    def import_crewai_tool(self, crewai_tool) -> bool:
        """导入 CrewAI 工具"""
        # ... 实现 CrewAI 工具适配
        pass


class AutoGPTToolAdapter:
    """将 AutoGPT 插件适配为 HermesAgentEvolution 工具"""
    
    def __init__(self, registry):
        self.registry = registry
    
    def import_autogpt_plugin(self, plugin) -> bool:
        """导入 AutoGPT 插件"""
        # ... 实现 AutoGPT 插件适配
        pass
```

### 7.2 通用适配器基类

```python
from abc import ABC, abstractmethod
from evolution.tools import ToolDefinition, ToolRegistry


class BaseToolAdapter(ABC):
    """工具适配器基类"""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
    
    @abstractmethod
    def import_tool(self, external_tool) -> bool:
        """导入外部工具"""
        pass
    
    @abstractmethod
    def export_tool(self, tool_name: str) -> any:
        """导出为外部工具格式"""
        pass
    
    def batch_import(self, external_tools: list) -> dict:
        """批量导入"""
        results = {"success": 0, "failed": 0, "errors": []}
        for tool in external_tools:
            try:
                if self.import_tool(tool):
                    results["success"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(str(e))
        return results
```

---

## 8. 多语言/跨语言移植

### 8.1 架构对齐指南

如果要将核心设计移植到其他语言，遵循以下架构映射：

| Python 组件 | 等效概念 (其他语言) |
|-------------|---------------------|
| `@dataclass` | 结构体/记录类型 (Rust struct, Go struct, Java record) |
| `Enum` | 枚举 (所有主流语言都支持) |
| `sqlite3` | SQLite 绑定 (rust-postgres, Go database/sql) |
| `asyncio` | async/await 运行时 |
| `Optional` / `Dict` / `List` | 泛型/可选类型 |

### 8.2 Rust 移植示例

```rust
// tool_registry.rs — Rust 版工具注册表核心
use serde::{Serialize, Deserialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ToolCategory {
    Utility,
    DataProcessing,
    FileOperation,
    Network,
    Ai,
    Custom,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ToolStatus {
    Active,
    Deprecated,
    Experimental,
    Disabled,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolDefinition {
    pub name: String,
    pub description: String,
    pub category: ToolCategory,
    pub status: ToolStatus,
    pub version: String,
    pub author: String,
    pub usage_count: u64,
    pub success_count: u64,
    pub error_count: u64,
    pub parameters: HashMap<String, serde_json::Value>,
    pub return_type: String,
    pub tags: Vec<String>,
    pub source_code: String,
    pub is_builtin: bool,
}

pub struct ToolRegistry {
    tools: HashMap<String, ToolDefinition>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        ToolRegistry {
            tools: HashMap::new(),
        }
    }
    
    pub fn register(&mut self, tool: ToolDefinition) -> bool {
        if self.tools.contains_key(&tool.name) {
            // Update existing
            self.tools.insert(tool.name.clone(), tool);
        } else {
            // Insert new
            self.tools.insert(tool.name.clone(), tool);
        }
        true
    }
    
    pub fn get(&self, name: &str) -> Option<&ToolDefinition> {
        self.tools.get(name)
    }
    
    pub fn list_all(&self) -> Vec<&ToolDefinition> {
        self.tools.values().collect()
    }
    
    pub fn search(&self, query: &str) -> Vec<&ToolDefinition> {
        let query_lower = query.to_lowercase();
        self.tools.values()
            .filter(|t| {
                t.name.to_lowercase().contains(&query_lower)
                    || t.description.to_lowercase().contains(&query_lower)
                    || t.tags.iter().any(|tag| tag.contains(&query_lower))
            })
            .collect()
    }
}
```

### 8.3 TypeScript/Node.js 移植示例

```typescript
// tool_registry.ts — TypeScript 版工具注册表
export enum ToolCategory {
  UTILITY = "utility",
  DATA_PROCESSING = "data_processing",
  FILE_OPERATION = "file_operation",
  NETWORK = "network",
  AI = "ai",
  CUSTOM = "custom",
}

export enum ToolStatus {
  ACTIVE = "active",
  DEPRECATED = "deprecated",
  EXPERIMENTAL = "experimental",
  DISABLED = "disabled",
}

export interface ToolDefinition {
  name: string;
  description: string;
  category: ToolCategory;
  status: ToolStatus;
  version: string;
  author: string;
  usageCount: number;
  successCount: number;
  errorCount: number;
  parameters: Record<string, any>;
  returnType: string;
  tags: string[];
  sourceCode: string;
  isBuiltin: boolean;
}

export class ToolRegistry {
  private tools: Map<string, ToolDefinition> = new Map();
  
  register(tool: ToolDefinition): boolean {
    this.tools.set(tool.name, tool);
    return true;
  }
  
  get(name: string): ToolDefinition | undefined {
    return this.tools.get(name);
  }
  
  listAll(category?: ToolCategory): ToolDefinition[] {
    const all = Array.from(this.tools.values());
    return category ? all.filter(t => t.category === category) : all;
  }
  
  search(query: string): ToolDefinition[] {
    const q = query.toLowerCase();
    return Array.from(this.tools.values()).filter(t =>
      t.name.toLowerCase().includes(q) ||
      t.description.toLowerCase().includes(q) ||
      t.tags.some(tag => tag.toLowerCase().includes(q))
    );
  }
  
  getStatistics(): Record<string, any> {
    const tools = Array.from(this.tools.values());
    return {
      totalTools: tools.length,
      byCategory: this.countBy(tools, 'category'),
      byStatus: this.countBy(tools, 'status'),
      totalUsage: tools.reduce((s, t) => s + t.usageCount, 0),
    };
  }
  
  private countBy(tools: ToolDefinition[], field: string): Record<string, number> {
    const counts: Record<string, number> = {};
    for (const tool of tools) {
      const key = String((tool as any)[field]);
      counts[key] = (counts[key] || 0) + 1;
    }
    return counts;
  }
}
```

---

## 附录

- **架构概述**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **API 参考**: [API_REFERENCE.md](API_REFERENCE.md)
- **安装指南**: [INSTALLATION.md](INSTALLATION.md)
- **V2 详细设计**: [ARCHITECTURE_V2.md](ARCHITECTURE_V2.md)
