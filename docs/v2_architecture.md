# HermesAgentEvolution V2 - 现代化AI Agent自我进化系统

## 项目概述

HermesAgentEvolution V2是一个基于事件驱动微服务架构的AI Agent自我进化系统。该系统实现了完整的自我学习、自我优化和自我扩展能力，采用业界最佳实践，整合了强化学习、元学习、反思机制等先进算法。

## 核心特性

### 🚀 现代化架构
- **事件驱动微服务架构**：异步处理，高扩展性
- **服务发现与注册**：动态服务管理
- **配置中心**：多环境配置管理
- **容器化部署**：Docker + Kubernetes支持

### 🧠 先进学习算法
- **强化学习服务**：支持DQN、PPO、A2C算法
- **元学习服务**：支持MAML、Reptile算法
- **反思机制服务**：深度分析和改进学习
- **自适应学习策略**：根据环境动态调整

### 🛠️ 动态工具生态
- **工具发现服务**：动态发现和注册工具
- **工具组合服务**：智能组合多个工具完成任务
- **工具质量评估**：自动评估工具效果
- **工具优化建议**：基于使用反馈优化工具

### 📊 系统监控与可观测性
- **实时监控服务**：系统健康、性能指标
- **结构化日志**：JSON格式日志，便于分析
- **分布式追踪**：请求链路追踪
- **告警系统**：异常检测和通知

### 🧪 完整测试框架
- **单元测试**：模块级别测试
- **集成测试**：服务间集成测试
- **性能测试**：基准测试和压力测试
- **端到端测试**：完整流程测试

### 🔄 自动化部署
- **CI/CD流水线**：自动化构建和部署
- **蓝绿部署**：零停机部署
- **配置热重载**：运行时配置更新
- **回滚机制**：自动故障恢复

## 系统架构

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway / Load Balancer               │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Event Bus (消息总线)                      │
└─────────────────────────────────────────────────────────────┘
                                │
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  学习服务    │  │  工具服务    │  │  监控服务    │
    │  Learning   │  │   Tools     │  │ Monitoring  │
    │  Services   │  │  Services   │  │  Services   │
    └─────────────┘  └─────────────┘  └─────────────┘
          │                 │                 │
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  强化学习    │  │  工具发现    │  │  健康检查    │
    │  RL Service │  │  Discovery  │  │  Health     │
    └─────────────┘  └─────────────┘  └─────────────┘
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  元学习      │  │  工具组合    │  │  指标收集    │
    │  Meta       │  │  Composition│  │  Metrics    │
    └─────────────┘  └─────────────┘  └─────────────┘
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  反思机制    │  │  工具评估    │  │  日志聚合    │
    │  Reflection │  │  Evaluation │  │  Logging    │
    └─────────────┘  └─────────────┘  └─────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Data Storage Layer                        │
│  PostgreSQL │  Redis  │  Elasticsearch │  MinIO/S3          │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件

1. **事件总线 (Event Bus)**
   - 异步消息传递
   - 发布/订阅模式
   - 事件持久化
   - 重试机制

2. **服务管理器 (Service Manager)**
   - 服务注册与发现
   - 负载均衡
   - 健康检查
   - 熔断机制

3. **配置管理器 (Config Manager)**
   - 多环境配置
   - 配置热重载
   - 配置版本控制
   - 配置验证

4. **学习服务 (Learning Services)**
   - 强化学习：DQN、PPO、A2C算法
   - 元学习：MAML、Reptile算法
   - 反思机制：经验分析和改进

5. **工具服务 (Tool Services)**
   - 工具发现：动态发现新工具
   - 工具组合：智能组合工具链
   - 工具评估：效果和质量评估

6. **监控服务 (Monitoring Services)**
   - 系统监控：CPU、内存、磁盘
   - 应用监控：请求量、响应时间、错误率
   - 业务监控：关键业务指标
   - 告警系统：异常检测和通知

## 快速开始

### 环境要求

- Python 3.9+
- Docker 20.10+
- Docker Compose 2.0+
- PostgreSQL 14+
- Redis 6+

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/your-org/hermes-agent-evolution-v2.git
   cd hermes-agent-evolution-v2
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境**
   ```bash
   cp config/config.example.yaml config/config.development.yaml
   # 编辑配置文件
   ```

4. **启动服务**
   ```bash
   docker-compose up -d
   ```

5. **运行测试**
   ```bash
   python -m pytest tests/ -v
   ```

### 开发环境

1. **创建虚拟环境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate  # Windows
   ```

2. **安装开发依赖**
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **启动开发服务器**
   ```bash
   python src/main.py --env development
   ```

## 使用示例

### 启动自我进化系统

```python
from src.main import HermesAgentEvolution

# 创建系统实例
system = HermesAgentEvolution(
    env="development",
    config_path="./config/config.development.yaml"
)

# 启动系统
await system.start()

# 运行进化循环
await system.evolve(
    iterations=100,
    learning_rate=0.001,
    exploration_rate=0.1
)

# 停止系统
await system.stop()
```

### 使用强化学习服务

```python
from src.learning.reinforcement.rl_service import RLService

# 创建强化学习服务
rl_service = RLService()

# 配置环境
await rl_service.configure_environment(
    env_name="ToolSelectionEnv",
    state_size=128,
    action_size=10
)

# 训练模型
training_result = await rl_service.train(
    episodes=1000,
    batch_size=32,
    gamma=0.99,
    epsilon_start=1.0,
    epsilon_end=0.01
)

# 使用模型进行预测
action = await rl_service.predict(state)
```

### 使用工具发现服务

```python
from src.tools.discovery.tool_discovery_service import ToolDiscoveryService

# 创建工具发现服务
discovery_service = ToolDiscoveryService()

# 发现新工具
discovery_result = await discovery_service.discover_tools(
    search_query="data analysis",
    max_results=10,
    source="github"
)

# 注册工具
registration_result = await discovery_service.register_tool(
    tool_name="data_analyzer",
    tool_description="数据分析工具",
    tool_code="def analyze(data): ...",
    dependencies=["pandas", "numpy"]
)

# 获取可用工具
available_tools = await discovery_service.get_available_tools()
```

### 使用监控服务

```python
from src.system.monitoring.monitoring_service import monitoring_service

# 启动监控服务
await monitoring_service.start()

# 记录自定义指标
await monitoring_service.record_custom_metric(
    name="tool_execution_time",
    value=0.123,
    metric_type="histogram",
    labels={"tool_name": "data_analyzer"},
    description="工具执行时间"
)

# 获取健康状态
health_status = await monitoring_service.get_health()

# 获取指标数据
metrics = await monitoring_service.get_metrics(format="json")
```

## API文档

### REST API端点

#### 系统管理
- `GET /api/v1/health` - 健康检查
- `GET /api/v1/metrics` - 系统指标
- `GET /api/v1/config` - 配置信息
- `POST /api/v1/restart` - 重启服务

#### 学习服务
- `POST /api/v1/learning/train` - 训练模型
- `POST /api/v1/learning/predict` - 预测动作
- `GET /api/v1/learning/models` - 获取模型列表
- `DELETE /api/v1/learning/models/{model_id}` - 删除模型

#### 工具服务
- `GET /api/v1/tools` - 获取工具列表
- `POST /api/v1/tools/discover` - 发现新工具
- `POST /api/v1/tools/execute` - 执行工具
- `GET /api/v1/tools/{tool_id}/metrics` - 获取工具指标

#### 监控服务
- `GET /api/v1/monitoring/metrics` - 获取监控指标
- `GET /api/v1/monitoring/alerts` - 获取告警列表
- `POST /api/v1/monitoring/alerts` - 创建告警规则
- `DELETE /api/v1/monitoring/alerts/{alert_id}` - 删除告警规则

### WebSocket事件

系统支持以下WebSocket事件：

- `system.start` - 系统启动
- `system.stop` - 系统停止
- `learning.progress` - 学习进度更新
- `tool.execution` - 工具执行事件
- `monitoring.alert` - 监控告警事件

## 配置说明

### 配置文件结构

```yaml
# config/config.development.yaml
app:
  name: "HermesAgentEvolution"
  version: "2.0.0"
  env: "development"
  debug: true

logging:
  level: "DEBUG"
  file: "logs/hermes_development.log"
  max_size: "100MB"
  backup_count: 10

database:
  host: "localhost"
  port: 5432
  database: "hermes_development"
  username: "hermes"
  password: "hermes123"
  pool_size: 10
  echo: true

redis:
  host: "localhost"
  port: 6379
  db: 0
  password: ""
  max_connections: 20

api:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  timeout: 30

monitoring:
  enabled: true
  prometheus_port: 9090
  grafana_port: 3000
  metrics_interval: 60

security:
  secret_key: "your-secret-key-here"
  token_expiry: 3600
  cors_origins: ["*"]
```

### 环境变量

系统支持以下环境变量：

- `APP_ENV` - 应用环境 (development/staging/production)
- `APP_NAME` - 应用名称
- `APP_VERSION` - 应用版本
- `LOG_LEVEL` - 日志级别
- `DATABASE_URL` - 数据库连接字符串
- `REDIS_URL` - Redis连接字符串
- `API_HOST` - API主机地址
- `API_PORT` - API端口
- `SECRET_KEY` - 安全密钥

## 部署指南

### Docker部署

1. **构建镜像**
   ```bash
   docker build -t hermes-agent-evolution:latest -f docker/Dockerfile .
   ```

2. **运行容器**
   ```bash
   docker run -d \
     --name hermes-agent-evolution \
     -p 8000:8000 \
     -v ./logs:/app/logs \
     -v ./data:/app/data \
     -e APP_ENV=production \
     -e DATABASE_URL=postgresql://user:pass@host:port/db \
     hermes-agent-evolution:latest
   ```

### Kubernetes部署

1. **创建命名空间**
   ```bash
   kubectl create namespace hermes
   ```

2. **部署应用**
   ```bash
   kubectl apply -f k8s/deployment.yaml -n hermes
   kubectl apply -f k8s/service.yaml -n hermes
   kubectl apply -f k8s/ingress.yaml -n hermes
   ```

3. **检查状态**
   ```bash
   kubectl get all -n hermes
   ```

### 云平台部署

#### AWS ECS
```bash
# 推送镜像到ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
docker tag hermes-agent-evolution:latest <account-id>.dkr.ecr.<region>.amazonaws.com/hermes-agent-evolution:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/hermes-agent-evolution:latest

# 部署到ECS
aws ecs update-service --cluster hermes-cluster --service hermes-service --force-new-deployment
```

#### Google Cloud Run
```bash
# 推送镜像到GCR
docker tag hermes-agent-evolution:latest gcr.io/<project-id>/hermes-agent-evolution:latest
docker push gcr.io/<project-id>/hermes-agent-evolution:latest

# 部署到Cloud Run
gcloud run deploy hermes-agent-evolution \
  --image gcr.io/<project-id>/hermes-agent-evolution:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## 测试指南

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 运行性能测试
pytest tests/performance/ -v

# 生成测试报告
pytest tests/ -v --html=reports/test-report.html --self-contained-html
```

### 测试覆盖率

```bash
# 生成覆盖率报告
pytest tests/ -v --cov=src --cov-report=html --cov-report=xml

# 查看覆盖率
open htmlcov/index.html  # Mac
start htmlcov/index.html  # Windows
```

### 代码质量检查

```bash
# 代码格式化
black src/ tests/

# 代码检查
flake8 src/ tests/

# 类型检查
mypy src/

# 安全检查
bandit -r src/
```

## 性能优化

### 数据库优化

1. **索引优化**
   ```sql
   -- 为常用查询字段创建索引
   CREATE INDEX idx_tool_executions_tool_id ON tool_executions(tool_id);
   CREATE INDEX idx_learning_episodes_created_at ON learning_episodes(created_at);
   ```

2. **查询优化**
   - 使用EXPLAIN分析查询计划
   - 避免N+1查询问题
   - 使用连接代替子查询

### 缓存策略

1. **Redis缓存**
   ```python
   # 使用Redis缓存频繁访问的数据
   await redis_client.setex(
       key=f"tool:{tool_id}:metrics",
       ttl=300,  # 5分钟
       value=json.dumps(metrics)
   )
   ```

2. **内存缓存**
   ```python
   # 使用LRU缓存热点数据
   from functools import lru_cache

   @lru_cache(maxsize=128)
   def get_tool_config(tool_id: str) -> Dict:
       # 获取工具配置
       pass
   ```

### 异步处理

1. **使用异步I/O**
   ```python
   async def process_tool_execution(tool_id: str, input_data: Dict) -> Dict:
       # 异步执行工具
       result = await tool_service.execute_async(tool_id, input_data)
       return result
   ```

2. **任务队列**
   ```python
   # 使用Celery处理后台任务
   @celery.task
   def analyze_learning_data(data: Dict) -> Dict:
       # 分析学习数据
       pass
   ```

## 故障排除

### 常见问题

1. **数据库连接失败**
   ```
   解决方案：
   1. 检查数据库服务是否运行
   2. 验证连接字符串
   3. 检查网络连接
   4. 查看防火墙设置
   ```

2. **Redis连接失败**
   ```
   解决方案：
   1. 检查Redis服务是否运行
   2. 验证密码和端口
   3. 检查内存使用情况
   4. 查看Redis日志
   ```

3. **API服务无法启动**
   ```
   解决方案：
   1. 检查端口是否被占用
   2. 验证配置文件
   3. 查看应用日志
   4. 检查依赖是否安装
   ```

### 日志分析

日志文件位置：
- 应用日志：`logs/hermes_{env}.log`
- 访问日志：`logs/access_{env}.log`
- 错误日志：`logs/error_{env}.log`

日志格式：
```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "level": "ERROR",
  "logger": "hermes.main",
  "message": "Database connection failed",
  "service": "hermes",
  "error": "Connection refused",
  "stack_trace": "..."
}
```

### 监控告警

系统支持以下监控告警：

1. **系统资源告警**
   - CPU使用率 > 80%
   - 内存使用率 > 85%
   - 磁盘使用率 > 90%

2. **应用性能告警**
   - API响应时间 > 5秒
   - 错误率 > 1%
   - 请求量突增/突降

3. **业务指标告警**
   - 学习进度停滞
   - 工具执行失败率升高
   - 数据一致性异常

## 贡献指南

### 开发流程

1. **Fork项目**
   ```bash
   # Fork项目到自己的GitHub账户
   ```

2. **克隆项目**
   ```bash
   git clone https://github.com/your-username/hermes-agent-evolution-v2.git
   cd hermes-agent-evolution-v2
   ```

3. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **提交更改**
   ```bash
   git add .
   git commit -m "feat: add your feature"
   git push origin feature/your-feature-name
   ```

5. **创建Pull Request**
   - 在GitHub上创建Pull Request
   - 描述更改内容和原因
   - 关联相关Issue

### 代码规范

1. **代码风格**
   - 遵循PEP 8规范
   - 使用Black格式化代码
   - 使用Flake8检查代码

2. **类型注解**
   ```python
   def process_data(data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
       # 函数应该有类型注解
       pass
   ```

3. **文档规范**
   - 函数应该有docstring
   - 类应该有类文档
   - 模块应该有模块文档

### 测试要求

1. **新增功能需要测试**
   - 单元测试覆盖率 > 80%
   - 集成测试覆盖主要流程
   - 性能测试验证性能影响

2. **Bug修复需要测试**
   - 添加回归测试
   - 验证修复效果
   - 确保不引入新问题

## 许可证

本项目采用MIT许可证。详见[LICENSE](LICENSE)文件。

## 联系方式

- 项目主页：https://github.com/your-org/hermes-agent-evolution-v2
- 问题反馈：https://github.com/your-org/hermes-agent-evolution-v2/issues
- 文档网站：https://hermes-agent-evolution.readthedocs.io/

## 致谢

感谢以下开源项目的贡献：

- FastAPI - 现代Web框架
- SQLAlchemy - ORM框架
- Redis - 内存数据库
- Docker - 容器平台
- Kubernetes - 容器编排
- Prometheus - 监控系统
- Grafana - 数据可视化

---

**HermesAgentEvolution V2** - 构建智能的自我进化AI Agent系统