# HermesAgentEvolution

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-beta-orange)

**AI助手自我进化系统** - 使AI助手能够从经验中学习并持续改进自身能力

## ✨ 特性

### 🧠 学习能力进化
- **经验观察**: 自动记录AI助手的执行经验
- **模式识别**: 分析成功和失败模式
- **智能建议**: 生成针对性的改进建议
- **自适应学习**: 持续优化执行策略

### 🛠️ 工具能力进化
- **工具性能分析**: 监控工具使用效果
- **策略优化**: 动态调整工具选择策略
- **智能推荐**: 基于上下文推荐最佳工具
- **探索与利用**: 平衡已知工具和新工具探索

### 🔄 自我监控
- **系统健康监控**: 实时监控进化系统状态
- **自动改进**: 基于分析结果自动调整策略
- **反馈循环**: 建立持续改进的闭环系统

### 📊 集成测试框架
- **组件集成测试**: 确保各模块协同工作
- **端到端测试**: 验证完整工作流程
- **学习效果验证**: 测试学习算法的有效性

## 🚀 快速开始

### 安装
```bash
# 克隆项目
git clone https://github.com/yourusername/HermesAgentEvolution.git
cd HermesAgentEvolution

# 安装依赖
pip install -r requirements.txt
```

### 基本使用
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
print(f"成功率: {analysis.success_rate:.1%}")

# 获取工具推荐
recommendations = strategy_learner.recommend_tool(
    "文件操作", ["terminal", "read_file", "write_file"]
)
```

## 📁 项目结构

```
HermesAgentEvolution/
├── src/evolution/          # 进化系统核心
│   ├── learning/          # 学习能力进化
│   ├── memory/           # 记忆系统进化
│   ├── tools/            # 工具能力进化
│   └── self_monitor.py   # 自我监控器
├── tests/                # 测试目录
├── docs/                # 文档目录
├── examples/            # 示例代码
└── config/              # 配置文件
```

## 📈 当前状态

### 已完成 (迭代2 - 学习能力进化)
- ✅ 经验观察和记录系统
- ✅ 经验分析和模式识别
- ✅ 工具策略学习和优化
- ✅ 自我监控和反馈循环
- ✅ 集成测试框架

### 进行中
- 🔄 项目文档和安装配置完善

### 计划中
- ⏳ 模式识别和策略生成模块
- ⏳ 学习能力进化示例应用

## 🧪 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行集成测试
python -m pytest tests/test_*_integration.py -v

# 生成测试报告
python -m pytest tests/ --cov=src --cov-report=html
```

## 📚 文档

- [架构设计](docs/ARCHITECTURE.md) - 系统架构和模块设计
- [安装指南](docs/INSTALLATION.md) - 详细安装和配置步骤
- [API参考](docs/API.md) - 模块API文档
- [使用示例](examples/) - 代码示例和用例

## 🔧 配置

### 飞书通知 (可选)
```json
{
    "mode": "webhook",
    "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
    "fallback_mode": "simulated"
}
```

### 数据库配置
```python
# 使用自定义数据库路径
observer = LearningObserver(db_path="/custom/path/database.db")
```

## 🤝 贡献

欢迎贡献！请查看[贡献指南](CONTRIBUTING.md)了解如何参与项目开发。

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看[LICENSE](LICENSE)文件了解详情。

## 📞 联系

- 问题报告: [GitHub Issues](https://github.com/yourusername/HermesAgentEvolution/issues)
- 讨论区: [GitHub Discussions](https://github.com/yourusername/HermesAgentEvolution/discussions)
- 文档: [项目Wiki](https://github.com/yourusername/HermesAgentEvolution/wiki)

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者！

---

*让AI助手不断进化，变得更智能、更高效！*
