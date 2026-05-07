# 5 分钟上手 HermesAgentEvolution

> 从零到 AI 自我进化 — 最快路径

---

## 前提条件

- Python 3.9+
- （可选）Hermes Agent 已安装

---

## 步骤 1：安装（10 秒）

```bash
pip install hermes-agent-evolution
```

---

## 步骤 2：环境自检（5 秒）

```bash
hermes-evolution check
```

期望输出：
```
✅ Python 3.11.15 ≥ 3.9
✅ 模块 工具注册表
✅ 模块 学习观察器
✅ 模块 记忆数据库
✅ 模块 安全审计
✅ 模块 协作编排
✅ 模块 闭环编排
✅ 模块 自我监控
✅ 模块 DB工具
✅ DB 可读写
✅ 数据目录: ~/.hermes/data/evolution
🎉 环境就绪，可以正常使用
```

---

## 步骤 3：部署到 Hermes Agent（15 秒）

```bash
hermes-evolution setup
```

> 如果没装 Hermes Agent，跳过此步骤，进化系统仍可作为 Python 库使用。

---

## 步骤 4：验证（30 秒）

```bash
# 查看系统状态
hermes-evolution status

# 运行测试
hermes-evolution test
```

---

## 步骤 5：开始使用

### 如果你是 Hermes Agent 用户

重启 Hermes 后，进化工具自动可用：

```
你: 学习今天的经验
Hermes: [调用 evolution_learn 记录本次对话的交互模式]

你: 查看系统健康状态
Hermes: [调用 evolution_self_monitor 返回成功率/性能指标]

你: 触发进化周期
Hermes: [调用 evolution_run_cycle 执行 监控→分析→规划→执行→验证]
```

### 如果你是开发者

```python
from evolution.cli import cmd_check, cmd_status
from evolution.db_utils import get_evolution_db
from evolution.learning.observer import LearningObserver
from evolution.tools.tool_registry import ToolRegistry

# 初始化
registry = ToolRegistry()
observer = LearningObserver()

# 注册一个工具
registry.register("my_tool", lambda x: x * 2, category="utility")

# 观察一次交互
observer.observe(
    tool_name="my_tool",
    input_params={"x": 5},
    output=10,
    duration_ms=0.5,
    success=True,
    context={"phase": "test"}
)

# 查看学习结果
print(observer.get_statistics())
```

---

## 可用的进化工具

部署到 Hermes 后，以下 6 个工具可用：

| 工具名 | 功能 |
|--------|------|
| `evolution_learn` | 记录学习经验 |
| `evolution_self_monitor` | 查看系统健康度 |
| `evolution_run_cycle` | 触发完整进化周期 |
| `evolution_create_tool` | 动态创建新工具 |
| `evolution_memory_discover` | 发现记忆关联 |
| `evolution_analyze_performance` | 分析工具性能 |

---

## 接下来

- 📖 [安装指南](INSTALLATION.md) — pip/插件/Docker 三路径
- 🏗️ [架构文档](ARCHITECTURE.md) — V1/V2/V3 融合架构
- 📚 [API 参考](API_REFERENCE.md) — 30 个模块完整接口
- ⚙️ [配置说明](CONFIGURATION.md) — 环境变量与调优
- 📋 [日志指南](LOGGING.md) — 统一日志框架

---

## 常见问题

### Q: 安装失败 "externally-managed-environment"？

```bash
pip install --break-system-packages hermes-agent-evolution
```

### Q: 测试报 DB 错误？

```bash
export EVOLUTION_DATA_DIR=/tmp/hermes-evo-test
hermes-evolution test
```

### Q: 如何卸载？

```bash
pip uninstall hermes-agent-evolution
rm -rf ~/.hermes/data/evolution   # 删除数据（可选）
```
