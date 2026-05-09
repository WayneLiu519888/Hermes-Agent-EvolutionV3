> ⚠️ **已归档 — 2026-05-09**
> 本文档描述的是 V2.0.0 早期设计（2024年），基于 PostgreSQL/Redis/K8s 架构。
> 当前 V3.0.6 已采用纯 SQLite 融合架构。请参阅 [ARCHITECTURE.md](./ARCHITECTURE.md) 了解最新架构。
> 本文档保留仅供历史参考。

---

     1|# HermesAgentEvolution V2 - 现代化AI Agent自我进化系统
     2|
     3|## 项目概述
     4|
     5|HermesAgentEvolution V2是一个基于事件驱动微服务架构的AI Agent自我进化系统。该系统实现了完整的自我学习、自我优化和自我扩展能力，采用业界最佳实践，整合了强化学习、元学习、反思机制等先进算法。
     6|
     7|## 核心特性
     8|
     9|### 🚀 现代化架构
    10|- **事件驱动微服务架构**：异步处理，高扩展性
    11|- **服务发现与注册**：动态服务管理
    12|- **配置中心**：多环境配置管理
    13|- **容器化部署**：Docker + Kubernetes支持
    14|
    15|### 🧠 先进学习算法
    16|- **强化学习服务**：支持DQN、PPO、A2C算法
    17|- **元学习服务**：支持MAML、Reptile算法
    18|- **反思机制服务**：深度分析和改进学习
    19|- **自适应学习策略**：根据环境动态调整
    20|
    21|### 🛠️ 动态工具生态
    22|- **工具发现服务**：动态发现和注册工具
    23|- **工具组合服务**：智能组合多个工具完成任务
    24|- **工具质量评估**：自动评估工具效果
    25|- **工具优化建议**：基于使用反馈优化工具
    26|
    27|### 📊 系统监控与可观测性
    28|- **实时监控服务**：系统健康、性能指标
    29|- **结构化日志**：JSON格式日志，便于分析
    30|- **分布式追踪**：请求链路追踪
    31|- **告警系统**：异常检测和通知
    32|
    33|### 🧪 完整测试框架
    34|- **单元测试**：模块级别测试
    35|- **集成测试**：服务间集成测试
    36|- **性能测试**：基准测试和压力测试
    37|- **端到端测试**：完整流程测试
    38|
    39|### 🔄 自动化部署
    40|- **CI/CD流水线**：自动化构建和部署
    41|- **蓝绿部署**：零停机部署
    42|- **配置热重载**：运行时配置更新
    43|- **回滚机制**：自动故障恢复
    44|
    45|## 系统架构
    46|
    47|### 架构图
    48|
    49|```
    50|┌─────────────────────────────────────────────────────────────┐
    51|│                    API Gateway / Load Balancer               │
    52|└─────────────────────────────────────────────────────────────┘
    53|                                │
    54|┌─────────────────────────────────────────────────────────────┐
    55|│                    Event Bus (消息总线)                      │
    56|└─────────────────────────────────────────────────────────────┘
    57|                                │
    58|    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    59|    │  学习服务    │  │  工具服务    │  │  监控服务    │
    60|    │  Learning   │  │   Tools     │  │ Monitoring  │
    61|    │  Services   │  │  Services   │  │  Services   │
    62|    └─────────────┘  └─────────────┘  └─────────────┘
    63|          │                 │                 │
    64|    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    65|    │  强化学习    │  │  工具发现    │  │  健康检查    │
    66|    │  RL Service │  │  Discovery  │  │  Health     │
    67|    └─────────────┘  └─────────────┘  └─────────────┘
    68|    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    69|    │  元学习      │  │  工具组合    │  │  指标收集    │
    70|    │  Meta       │  │  Composition│  │  Metrics    │
    71|    └─────────────┘  └─────────────┘  └─────────────┘
    72|    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    73|    │  反思机制    │  │  工具评估    │  │  日志聚合    │
    74|    │  Reflection │  │  Evaluation │  │  Logging    │
    75|    └─────────────┘  └─────────────┘  └─────────────┘
    76|                                │
    77|┌─────────────────────────────────────────────────────────────┐
    78|│                    Data Storage Layer                        │
    79|│  PostgreSQL │  Redis  │  Elasticsearch │  MinIO/S3          │
    80|└─────────────────────────────────────────────────────────────┘
    81|```
    82|
    83|### 核心组件
    84|
    85|1. **事件总线 (Event Bus)**
    86|   - 异步消息传递
    87|   - 发布/订阅模式
    88|   - 事件持久化
    89|   - 重试机制
    90|
    91|2. **服务管理器 (Service Manager)**
    92|   - 服务注册与发现
    93|   - 负载均衡
    94|   - 健康检查
    95|   - 熔断机制
    96|
    97|3. **配置管理器 (Config Manager)**
    98|   - 多环境配置
    99|   - 配置热重载
   100|   - 配置版本控制
   101|   - 配置验证
   102|
   103|4. **学习服务 (Learning Services)**
   104|   - 强化学习：DQN、PPO、A2C算法
   105|   - 元学习：MAML、Reptile算法
   106|   - 反思机制：经验分析和改进
   107|
   108|5. **工具服务 (Tool Services)**
   109|   - 工具发现：动态发现新工具
   110|   - 工具组合：智能组合工具链
   111|   - 工具评估：效果和质量评估
   112|
   113|6. **监控服务 (Monitoring Services)**
   114|   - 系统监控：CPU、内存、磁盘
   115|   - 应用监控：请求量、响应时间、错误率
   116|   - 业务监控：关键业务指标
   117|   - 告警系统：异常检测和通知
   118|
   119|## 快速开始
   120|
   121|### 环境要求
   122|
   123|- Python 3.9+
   124|- Docker 20.10+
   125|- Docker Compose 2.0+
   126|- PostgreSQL 14+
   127|- Redis 6+
   128|
   129|### 安装步骤
   130|
   131|1. **克隆项目**
   132|   ```bash
   133|   git clone https://github.com/your-org/hermes-agent-evolution-v2.git
   134|   cd hermes-agent-evolution-v2
   135|   ```
   136|
   137|2. **安装依赖**
   138|   ```bash
   139|   pip install -r requirements.txt
   140|   ```
   141|
   142|3. **配置环境**
   143|   ```bash
   144|   cp config/config.example.yaml config/config.development.yaml
   145|   # 编辑配置文件
   146|   ```
   147|
   148|4. **启动服务**
   149|   ```bash
   150|   docker-compose up -d
   151|   ```
   152|
   153|5. **运行测试**
   154|   ```bash
   155|   python -m pytest tests/ -v
   156|   ```
   157|
   158|### 开发环境
   159|
   160|1. **创建虚拟环境**
   161|   ```bash
   162|   python -m venv venv
   163|   source venv/bin/activate  # Linux/Mac
   164|   # 或
   165|   venv\Scripts\activate  # Windows
   166|   ```
   167|
   168|2. **安装开发依赖**
   169|   ```bash
   170|   pip install -r requirements-dev.txt
   171|   ```
   172|
   173|3. **启动开发服务器**
   174|   ```bash
   175|   python src/main.py --env development
   176|   ```
   177|
   178|## 使用示例
   179|
   180|### 启动自我进化系统
   181|
   182|```python
   183|from src.main import HermesAgentEvolution
   184|
   185|# 创建系统实例
   186|system = HermesAgentEvolution(
   187|    env="development",
   188|    config_path="./config/config.development.yaml"
   189|)
   190|
   191|# 启动系统
   192|await system.start()
   193|
   194|# 运行进化循环
   195|await system.evolve(
   196|    iterations=100,
   197|    learning_rate=0.001,
   198|    exploration_rate=0.1
   199|)
   200|
   201|# 停止系统
   202|await system.stop()
   203|```
   204|
   205|### 使用强化学习服务
   206|
   207|```python
   208|from src.learning.reinforcement.rl_service import RLService
   209|
   210|# 创建强化学习服务
   211|rl_service = RLService()
   212|
   213|# 配置环境
   214|await rl_service.configure_environment(
   215|    env_name="ToolSelectionEnv",
   216|    state_size=128,
   217|    action_size=10
   218|)
   219|
   220|# 训练模型
   221|training_result = await rl_service.train(
   222|    episodes=1000,
   223|    batch_size=32,
   224|    gamma=0.99,
   225|    epsilon_start=1.0,
   226|    epsilon_end=0.01
   227|)
   228|
   229|# 使用模型进行预测
   230|action = await rl_service.predict(state)
   231|```
   232|
   233|### 使用工具发现服务
   234|
   235|```python
   236|from src.tools.discovery.tool_discovery_service import ToolDiscoveryService
   237|
   238|# 创建工具发现服务
   239|discovery_service = ToolDiscoveryService()
   240|
   241|# 发现新工具
   242|discovery_result = await discovery_service.discover_tools(
   243|    search_query="data analysis",
   244|    max_results=10,
   245|    source="github"
   246|)
   247|
   248|# 注册工具
   249|registration_result = await discovery_service.register_tool(
   250|    tool_name="data_analyzer",
   251|    tool_description="数据分析工具",
   252|    tool_code="def analyze(data): ...",
   253|    dependencies=["pandas", "numpy"]
   254|)
   255|
   256|# 获取可用工具
   257|available_tools = await discovery_service.get_available_tools()
   258|```
   259|
   260|### 使用监控服务
   261|
   262|```python
   263|from src.system.monitoring.monitoring_service import monitoring_service
   264|
   265|# 启动监控服务
   266|await monitoring_service.start()
   267|
   268|# 记录自定义指标
   269|await monitoring_service.record_custom_metric(
   270|    name="tool_execution_time",
   271|    value=0.123,
   272|    metric_type="histogram",
   273|    labels={"tool_name": "data_analyzer"},
   274|    description="工具执行时间"
   275|)
   276|
   277|# 获取健康状态
   278|health_status = await monitoring_service.get_health()
   279|
   280|# 获取指标数据
   281|metrics = await monitoring_service.get_metrics(format="json")
   282|```
   283|
   284|## API文档
   285|
   286|### REST API端点
   287|
   288|#### 系统管理
   289|- `GET /api/v1/health` - 健康检查
   290|- `GET /api/v1/metrics` - 系统指标
   291|- `GET /api/v1/config` - 配置信息
   292|- `POST /api/v1/restart` - 重启服务
   293|
   294|#### 学习服务
   295|- `POST /api/v1/learning/train` - 训练模型
   296|- `POST /api/v1/learning/predict` - 预测动作
   297|- `GET /api/v1/learning/models` - 获取模型列表
   298|- `DELETE /api/v1/learning/models/{model_id}` - 删除模型
   299|
   300|#### 工具服务
   301|- `GET /api/v1/tools` - 获取工具列表
   302|- `POST /api/v1/tools/discover` - 发现新工具
   303|- `POST /api/v1/tools/execute` - 执行工具
   304|- `GET /api/v1/tools/{tool_id}/metrics` - 获取工具指标
   305|
   306|#### 监控服务
   307|- `GET /api/v1/monitoring/metrics` - 获取监控指标
   308|- `GET /api/v1/monitoring/alerts` - 获取告警列表
   309|- `POST /api/v1/monitoring/alerts` - 创建告警规则
   310|- `DELETE /api/v1/monitoring/alerts/{alert_id}` - 删除告警规则
   311|
   312|### WebSocket事件
   313|
   314|系统支持以下WebSocket事件：
   315|
   316|- `system.start` - 系统启动
   317|- `system.stop` - 系统停止
   318|- `learning.progress` - 学习进度更新
   319|- `tool.execution` - 工具执行事件
   320|- `monitoring.alert` - 监控告警事件
   321|
   322|## 配置说明
   323|
   324|### 配置文件结构
   325|
   326|```yaml
   327|# config/config.development.yaml
   328|app:
   329|  name: "HermesAgentEvolution"
   330|  version: "2.0.0"
   331|  env: "development"
   332|  debug: true
   333|
   334|logging:
   335|  level: "DEBUG"
   336|  file: "logs/hermes_development.log"
   337|  max_size: "100MB"
   338|  backup_count: 10
   339|
   340|database:
   341|  host: "localhost"
   342|  port: 5432
   343|  database: "hermes_development"
   344|  username: "hermes"
   345|  password: "hermes123"
   346|  pool_size: 10
   347|  echo: true
   348|
   349|redis:
   350|  host: "localhost"
   351|  port: 6379
   352|  db: 0
   353|  password: ""
   354|  max_connections: 20
   355|
   356|api:
   357|  host: "0.0.0.0"
   358|  port: 8000
   359|  workers: 4
   360|  timeout: 30
   361|
   362|monitoring:
   363|  enabled: true
   364|  prometheus_port: 9090
   365|  grafana_port: 3000
   366|  metrics_interval: 60
   367|
   368|security:
   369|  secret_key: "your-secret-key-here"
   370|  token_expiry: 3600
   371|  cors_origins: ["*"]
   372|```
   373|
   374|### 环境变量
   375|
   376|系统支持以下环境变量：
   377|
   378|- `APP_ENV` - 应用环境 (development/staging/production)
   379|- `APP_NAME` - 应用名称
   380|- `APP_VERSION` - 应用版本
   381|- `LOG_LEVEL` - 日志级别
   382|- `DATABASE_URL` - 数据库连接字符串
   383|- `REDIS_URL` - Redis连接字符串
   384|- `API_HOST` - API主机地址
   385|- `API_PORT` - API端口
   386|- `SECRET_KEY` - 安全密钥
   387|
   388|## 部署指南
   389|
   390|### Docker部署
   391|
   392|1. **构建镜像**
   393|   ```bash
   394|   docker build -t hermes-agent-evolution:latest -f docker/Dockerfile .
   395|   ```
   396|
   397|2. **运行容器**
   398|   ```bash
   399|   docker run -d \
   400|     --name hermes-agent-evolution \
   401|     -p 8000:8000 \
   402|     -v ./logs:/app/logs \
   403|     -v ./data:/app/data \
   404|     -e APP_ENV=production \
   405|     -e DATABASE_URL=postgresql://user:***@host:port/db \
   406|     hermes-agent-evolution:latest
   407|   ```
   408|
   409|### Kubernetes部署
   410|
   411|1. **创建命名空间**
   412|   ```bash
   413|   kubectl create namespace hermes
   414|   ```
   415|
   416|2. **部署应用**
   417|   ```bash
   418|   kubectl apply -f k8s/deployment.yaml -n hermes
   419|   kubectl apply -f k8s/service.yaml -n hermes
   420|   kubectl apply -f k8s/ingress.yaml -n hermes
   421|   ```
   422|
   423|3. **检查状态**
   424|   ```bash
   425|   kubectl get all -n hermes
   426|   ```
   427|
   428|### 云平台部署
   429|
   430|#### AWS ECS
   431|```bash
   432|# 推送镜像到ECR
   433|aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
   434|docker tag hermes-agent-evolution:latest <account-id>.dkr.ecr.<region>.amazonaws.com/hermes-agent-evolution:latest
   435|docker push <account-id>.dkr.ecr.<region>.amazonaws.com/hermes-agent-evolution:latest
   436|
   437|# 部署到ECS
   438|aws ecs update-service --cluster hermes-cluster --service hermes-service --force-new-deployment
   439|```
   440|
   441|#### Google Cloud Run
   442|```bash
   443|# 推送镜像到GCR
   444|docker tag hermes-agent-evolution:latest gcr.io/<project-id>/hermes-agent-evolution:latest
   445|docker push gcr.io/<project-id>/hermes-agent-evolution:latest
   446|
   447|# 部署到Cloud Run
   448|gcloud run deploy hermes-agent-evolution \
   449|  --image gcr.io/<project-id>/hermes-agent-evolution:latest \
   450|  --platform managed \
   451|  --region us-central1 \
   452|  --allow-unauthenticated
   453|```
   454|
   455|## 测试指南
   456|
   457|### 运行测试
   458|
   459|```bash
   460|# 运行所有测试
   461|pytest tests/ -v
   462|
   463|# 运行单元测试
   464|pytest tests/unit/ -v
   465|
   466|# 运行集成测试
   467|pytest tests/integration/ -v
   468|
   469|# 运行性能测试
   470|pytest tests/performance/ -v
   471|
   472|# 生成测试报告
   473|pytest tests/ -v --html=reports/test-report.html --self-contained-html
   474|```
   475|
   476|### 测试覆盖率
   477|
   478|```bash
   479|# 生成覆盖率报告
   480|pytest tests/ -v --cov=src --cov-report=html --cov-report=xml
   481|
   482|# 查看覆盖率
   483|open htmlcov/index.html  # Mac
   484|start htmlcov/index.html  # Windows
   485|```
   486|
   487|### 代码质量检查
   488|
   489|```bash
   490|# 代码格式化
   491|black src/ tests/
   492|
   493|# 代码检查
   494|flake8 src/ tests/
   495|
   496|# 类型检查
   497|mypy src/
   498|
   499|# 安全检查
   500|bandit -r src/
   501|```
   502|
   503|## 性能优化
   504|
   505|### 数据库优化
   506|
   507|1. **索引优化**
   508|   ```sql
   509|   -- 为常用查询字段创建索引
   510|   CREATE INDEX idx_tool_executions_tool_id ON tool_executions(tool_id);
   511|   CREATE INDEX idx_learning_episodes_created_at ON learning_episodes(created_at);
   512|   ```
   513|
   514|2. **查询优化**
   515|   - 使用EXPLAIN分析查询计划
   516|   - 避免N+1查询问题
   517|   - 使用连接代替子查询
   518|
   519|### 缓存策略
   520|
   521|1. **Redis缓存**
   522|   ```python
   523|   # 使用Redis缓存频繁访问的数据
   524|   await redis_client.setex(
   525|       key=f"tool:{tool_id}:metrics",
   526|       ttl=300,  # 5分钟
   527|       value=json.dumps(metrics)
   528|   )
   529|   ```
   530|
   531|2. **内存缓存**
   532|   ```python
   533|   # 使用LRU缓存热点数据
   534|   from functools import lru_cache
   535|
   536|   @lru_cache(maxsize=128)
   537|   def get_tool_config(tool_id: str) -> Dict:
   538|       # 获取工具配置
   539|       pass
   540|   ```
   541|
   542|### 异步处理
   543|
   544|1. **使用异步I/O**
   545|   ```python
   546|   async def process_tool_execution(tool_id: str, input_data: Dict) -> Dict:
   547|       # 异步执行工具
   548|       result = await tool_service.execute_async(tool_id, input_data)
   549|       return result
   550|   ```
   551|
   552|2. **任务队列**
   553|   ```python
   554|   # 使用Celery处理后台任务
   555|   @celery.task
   556|   def analyze_learning_data(data: Dict) -> Dict:
   557|       # 分析学习数据
   558|       pass
   559|   ```
   560|
   561|## 故障排除
   562|
   563|### 常见问题
   564|
   565|1. **数据库连接失败**
   566|   ```
   567|   解决方案：
   568|   1. 检查数据库服务是否运行
   569|   2. 验证连接字符串
   570|   3. 检查网络连接
   571|   4. 查看防火墙设置
   572|   ```
   573|
   574|2. **Redis连接失败**
   575|   ```
   576|   解决方案：
   577|   1. 检查Redis服务是否运行
   578|   2. 验证密码和端口
   579|   3. 检查内存使用情况
   580|   4. 查看Redis日志
   581|   ```
   582|
   583|3. **API服务无法启动**
   584|   ```
   585|   解决方案：
   586|   1. 检查端口是否被占用
   587|   2. 验证配置文件
   588|   3. 查看应用日志
   589|   4. 检查依赖是否安装
   590|   ```
   591|
   592|### 日志分析
   593|
   594|日志文件位置：
   595|- 应用日志：`logs/hermes_{env}.log`
   596|- 访问日志：`logs/access_{env}.log`
   597|- 错误日志：`logs/error_{env}.log`
   598|
   599|日志格式：
   600|```json
   601|{
   602|  "timestamp": "2024-01-01T12:00:00.000Z",
   603|  "level": "ERROR",
   604|  "logger": "hermes.main",
   605|  "message": "Database connection failed",
   606|  "service": "hermes",
   607|  "error": "Connection refused",
   608|  "stack_trace": "..."
   609|}
   610|```
   611|
   612|### 监控告警
   613|
   614|系统支持以下监控告警：
   615|
   616|1. **系统资源告警**
   617|   - CPU使用率 > 80%
   618|   - 内存使用率 > 85%
   619|   - 磁盘使用率 > 90%
   620|
   621|2. **应用性能告警**
   622|   - API响应时间 > 5秒
   623|   - 错误率 > 1%
   624|   - 请求量突增/突降
   625|
   626|3. **业务指标告警**
   627|   - 学习进度停滞
   628|   - 工具执行失败率升高
   629|   - 数据一致性异常
   630|
   631|## 贡献指南
   632|
   633|### 开发流程
   634|
   635|1. **Fork项目**
   636|   ```bash
   637|   # Fork项目到自己的GitHub账户
   638|   ```
   639|
   640|2. **克隆项目**
   641|   ```bash
   642|   git clone https://github.com/your-username/hermes-agent-evolution-v2.git
   643|   cd hermes-agent-evolution-v2
   644|   ```
   645|
   646|3. **创建分支**
   647|   ```bash
   648|   git checkout -b feature/your-feature-name
   649|   ```
   650|
   651|4. **提交更改**
   652|   ```bash
   653|   git add .
   654|   git commit -m "feat: add your feature"
   655|   git push origin feature/your-feature-name
   656|   ```
   657|
   658|5. **创建Pull Request**
   659|   - 在GitHub上创建Pull Request
   660|   - 描述更改内容和原因
   661|   - 关联相关Issue
   662|
   663|### 代码规范
   664|
   665|1. **代码风格**
   666|   - 遵循PEP 8规范
   667|   - 使用Black格式化代码
   668|   - 使用Flake8检查代码
   669|
   670|2. **类型注解**
   671|   ```python
   672|   def process_data(data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
   673|       # 函数应该有类型注解
   674|       pass
   675|   ```
   676|
   677|3. **文档规范**
   678|   - 函数应该有docstring
   679|   - 类应该有类文档
   680|   - 模块应该有模块文档
   681|
   682|### 测试要求
   683|
   684|1. **新增功能需要测试**
   685|   - 单元测试覆盖率 > 80%
   686|   - 集成测试覆盖主要流程
   687|   - 性能测试验证性能影响
   688|
   689|2. **Bug修复需要测试**
   690|   - 添加回归测试
   691|   - 验证修复效果
   692|   - 确保不引入新问题
   693|
   694|## 许可证
   695|
   696|本项目采用MIT许可证。详见[LICENSE](LICENSE)文件。
   697|
   698|## 联系方式
   699|
   700|- 项目主页：https://github.com/your-org/hermes-agent-evolution-v2
   701|- 问题反馈：https://github.com/your-org/hermes-agent-evolution-v2/issues
   702|- 文档网站：https://hermes-agent-evolution.readthedocs.io/
   703|
   704|## 致谢
   705|
   706|感谢以下开源项目的贡献：
   707|
   708|- FastAPI - 现代Web框架
   709|- SQLAlchemy - ORM框架
   710|- Redis - 内存数据库
   711|- Docker - 容器平台
   712|- Kubernetes - 容器编排
   713|- Prometheus - 监控系统
   714|- Grafana - 数据可视化
   715|
   716|---
   717|
   718|**HermesAgentEvolution V2** - 构建智能的自我进化AI Agent系统