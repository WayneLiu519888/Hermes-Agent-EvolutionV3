# HermesAgentEvolution 项目架构文档

## 项目概述

HermesAgentEvolution 是一个AI助手自我进化系统，旨在使AI助手能够从经验中学习并持续改进自身能力。项目采用模块化设计，便于移植到不同的HermesAgent实例。

## 系统架构

### 核心模块

```
HermesAgentEvolution/
├── src/evolution/              # 进化系统核心
│   ├── learning/              # 学习能力进化
│   │   ├── __init__.py
│   │   ├── experience.py      # 经验数据类
│   │   ├── observer.py        # 学习观察器
│   │   ├── analyzer.py        # 经验分析器
│   │   └── tool_strategy_learner.py  # 工具策略学习器
│   ├── memory/                # 记忆系统进化
│   │   ├── __init__.py
│   │   ├── database.py        # 关联数据库
│   │   ├── association_discoverer.py  # 关联发现器
│   │   ├── retrieval_optimizer.py     # 检索优化器
│   │   └── association_optimizer.py   # 关联优化器
│   ├── tools/                 # 工具能力进化
│   │   ├── __init__.py
│   │   ├── tool_creator.py    # 工具创建器
│   │   └── tool_registry.py   # 工具注册表
│   └── self_monitor.py        # 自我监控器
├── src/utils/                 # 工具模块
│   ├── feishu_notifier.py    # 飞书通知器
│   └── progress_reporter.py  # 进展报告器
├── tests/                    # 测试目录
│   ├── test_*.py            # 单元测试
│   └── test_*_integration.py # 集成测试
├── config/                   # 配置文件
│   └── feishu_config.json   # 飞书配置
├── data/                     # 数据目录
│   └── *.db                 # 数据库文件
├── docs/                     # 文档目录
├── examples/                 # 示例代码
└── requirements.txt          # 依赖列表
```

## 模块详细说明

### 1. 学习能力进化模块 (src/evolution/learning/)

#### 1.1 Experience (经验数据类)
- **功能**: 定义经验数据的结构和类型
- **核心类**: `Experience`, `ExperienceType`, `Outcome`
- **数据字段**: id, 类型, 任务ID, 时间戳, 描述, 上下文, 动作, 推理步骤, 结果, 指标, 经验教训

#### 1.2 LearningObserver (学习观察器)
- **功能**: 观察和记录AI助手的执行经验
- **核心方法**: `record_experience()`, `get_recent_experiences()`
- **数据存储**: SQLite数据库

#### 1.3 ExperienceAnalyzer (经验分析器)
- **功能**: 分析经验数据，提取模式，生成改进建议
- **核心方法**: `analyze_recent_experiences()`, `identify_success_patterns()`, `identify_failure_patterns()`
- **输出**: `AnalysisResult` 包含统计、模式、洞察和建议

#### 1.4 ToolStrategyLearner (工具策略学习器)
- **功能**: 分析工具使用模式，优化工具选择策略
- **核心方法**: `record_tool_usage()`, `recommend_tool()`, `learn_from_experiences()`
- **策略类型**: 效率优化、可靠性优化、准确性优化、自适应

### 2. 记忆系统进化模块 (src/evolution/memory/)

#### 2.1 AssociationDatabase (关联数据库)
- **功能**: 存储和管理记忆关联数据
- **核心表**: memory_entries, associations, association_discovery_logs

#### 2.2 AssociationDiscoverer (关联发现器)
- **功能**: 自动发现记忆条目之间的关联关系
- **发现方法**: 语义相似性、共现分析、模式匹配

#### 2.3 RetrievalOptimizer (检索优化器)
- **功能**: 优化记忆检索策略，提高检索效率和准确性
- **优化技术**: 相关性排序、上下文增强、缓存优化

### 3. 工具能力进化模块 (src/evolution/tools/)

#### 3.1 ToolCreator (工具创建器)
- **功能**: 根据需求自动创建新的工具
- **创建流程**: 需求分析、代码生成、测试验证、注册部署

#### 3.2 ToolRegistry (工具注册表)
- **功能**: 管理和维护可用工具集合
- **管理功能**: 工具注册、版本控制、依赖管理、权限控制

### 4. 自我监控器 (src/evolution/self_monitor.py)

#### 4.1 SelfMonitor (自我监控器)
- **功能**: 协调各个进化组件，监控系统状态，生成改进计划
- **核心方法**: `monitor_and_improve()`, `get_system_health_report()`
- **监控指标**: 成功率、效率、工具多样性、策略效果

## 数据流和工作流程

### 经验记录流程
```
AI助手执行任务 → LearningObserver记录经验 → 存储到数据库
```

### 学习分析流程
```
ExperienceAnalyzer读取经验 → 统计分析 → 模式识别 → 生成改进建议
```

### 工具优化流程
```
ToolStrategyLearner记录工具使用 → 性能分析 → 策略优化 → 工具推荐
```

### 自我监控流程
```
SelfMonitor协调各组件 → 系统状态分析 → 生成改进计划 → 反馈到执行
```

## 配置系统

### 飞书通知配置 (config/feishu_config.json)
```json
{
    "mode": "webhook",
    "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
    "fallback_mode": "simulated"
}
```

### 数据库配置
- **默认路径**: `data/learning_experiences.db`
- **支持**: 自定义数据库路径
- **迁移**: 支持数据库迁移和备份

## 安装和部署

### 环境要求
- Python 3.8+
- SQLite3
- 网络访问（用于飞书通知）

### 安装步骤
1. 克隆项目
2. 安装依赖: `pip install -r requirements.txt`
3. 配置飞书通知（可选）
4. 运行测试: `python -m pytest tests/`
5. 开始使用

### 快速开始
```python
from src.evolution.learning.observer import LearningObserver
from src.evolution.learning.analyzer import ExperienceAnalyzer
from src.evolution.learning.tool_strategy_learner import ToolStrategyLearner

# 初始化系统
observer = LearningObserver()
analyzer = ExperienceAnalyzer(observer)
strategy_learner = ToolStrategyLearner()

# 记录经验
observer.record_experience(experience)

# 分析学习
analysis = analyzer.analyze_recent_experiences(days=7)

# 获取工具推荐
recommendations = strategy_learner.recommend_tool(
    "文件操作", ["terminal", "read_file", "write_file"], 
    {"complexity": 0.5}
)
```

## 测试框架

### 单元测试
- 位置: `tests/test_*.py`
- 覆盖: 所有核心模块
- 运行: `python -m pytest tests/`

### 集成测试
- 位置: `tests/test_*_integration.py`
- 测试: 组件集成和工作流程
- 验证: 系统端到端功能

### 测试数据
- 使用临时数据库
- 模拟经验数据
- 自动化清理

## 性能考虑

### 数据库优化
- 索引优化
- 查询缓存
- 定期清理

### 内存管理
- 分页加载
- 流式处理
- 资源监控

### 并发处理
- 线程安全设计
- 数据库连接池
- 异步操作支持

## 扩展和定制

### 添加新的经验类型
1. 在`ExperienceType`枚举中添加新类型
2. 更新`ExperienceAnalyzer`的分析逻辑
3. 添加相应的测试用例

### 自定义分析算法
1. 继承`ExperienceAnalyzer`类
2. 重写分析方法
3. 注册到系统

### 集成外部系统
1. 实现适配器接口
2. 配置连接参数
3. 添加错误处理

## 故障排除

### 常见问题
1. **数据库连接失败**: 检查文件权限和路径
2. **飞书通知失败**: 检查网络连接和配置
3. **导入错误**: 检查Python路径和依赖
4. **测试失败**: 检查测试数据和环境

### 日志和监控
- 日志文件: `evolution_system.log`
- 飞书通知日志: `feishu_notifications.log`
- 系统健康报告: `SelfMonitor.get_system_health_report()`

## 版本历史

### v1.0 (迭代1) - 记忆系统进化
- 关联发现系统
- 检索优化框架
- 基础数据库设计

### v2.0 (迭代2) - 学习能力进化
- 经验观察和记录
- 经验分析和模式识别
- 工具策略学习和优化
- 自我监控和反馈循环

### 未来计划
- 迭代3: 工具能力进化
- 迭代4: 多智能体协作进化
- 迭代5: 跨平台部署和集成

## 贡献指南

### 代码规范
- 遵循PEP 8
- 添加类型注解
- 编写文档字符串
- 添加单元测试

### 提交流程
1. Fork项目
2. 创建功能分支
3. 编写代码和测试
4. 提交Pull Request
5. 代码审查和合并

### 问题报告
- 使用GitHub Issues
- 提供复现步骤
- 包含环境信息
- 建议解决方案

## 许可证

本项目采用MIT许可证。详见LICENSE文件。

---

*最后更新: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
