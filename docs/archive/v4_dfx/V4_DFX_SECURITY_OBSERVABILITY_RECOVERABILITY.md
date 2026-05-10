# HermesAgentEvolution DFX 专项审视报告

## 安全性 + 可观测性 + 可恢复性 合并评估

审视日期：2026-05-10
审视范围：项目全量代码（src/ 目录及入口文件）
审视方法：静态代码审查 + 配置审计 + 架构分析

---

# 第一部分：安全性 (Security)

## 1.1 敏感信息管理

### 发现

| 风险等级 | 文件 | 问题描述 |
|---------|------|---------|
| **HIGH** | `src/utils/feishu_notifier.py:31` | App ID 硬编码为默认值 `cli_a96b9943f1f8dcd2`，暴露在源码中 |
| **HIGH** | `src/services/system/deployment/deployment_service.py:165` | 数据库默认密码硬编码 `hermes123`，任何读取源码的人均可获取 |
| **MEDIUM** | `config/feishu_config.json` | 虽已加入 .gitignore，但 App ID 和 home_channel 信息以明文存储，泄露后攻击面大 |
| **LOW** | `src/utils/feishu_notifier.py:32` | App Secret 默认值为空字符串，依赖环境变量注入——设计合理，但无缺失时的警告 |

### 详析

**App ID 硬编码 (feishu_notifier.py:31):**
```python
"app_id": os.environ.get("FEISHU_APP_ID", "cli_a96b9943f1f8dcd2"),
```
默认值直接写入源码，已提交至 Git 仓库。即使 .gitignore 排除了配置文件，代码中的默认值已经泄漏了 App ID。

**数据库密码硬编码 (deployment_service.py:165):**
```python
"password": "hermes123",
```
V2 微服务部署配置中使用了弱密码且硬编码。虽然仅用于本地开发环境，但若部署到生产环境将构成严重风险。

### 建议

- **立即移除** 源码中所有硬编码的 App ID、密码等敏感值
- App ID 应完全依赖环境变量，默认值应为空（如 App Secret 的做法）
- 部署配置中的密码应使用 `secrets.token_urlsafe()` 生成，与 `secret_key` 一致
- 在应用启动时对所有必需的环境变量进行存在性检查，缺失时给出明确错误并拒绝启动

---

## 1.2 输入验证

### 发现

| 风险等级 | 位置 | 问题描述 |
|---------|------|---------|
| **MEDIUM** | 全局 | 缺乏统一的输入验证层；外部输入无 schema 校验 |
| **LOW** | `sandbox_executor.py` | 代码执行前的 AST 安全检查较完善（值得肯定） |
| **LOW** | `config_manager.py` | 配置验证框架存在但未全面启用 |

### 详析

项目没有统一的输入验证中间件或装饰器。飞书 webhook 回调、CLI 参数、配置文件加载等入口点各自处理输入，缺乏一致的校验策略。

**正面案例——沙箱代码安全分析 (sandbox_executor.py):**
`CodeSafetyAnalyzer` 使用 AST 遍历检测危险导入和函数调用，禁止了 95+ 个危险模块导入和 `eval/exec/compile/__import__` 等危险调用。这是项目中输入验证最完善的模块。

**负面案例——CLI 参数:**
`hermes_daemon.py` 和 `cli.py` 中的 argparse 参数仅做类型转换，未进行范围或合法性验证。例如 `--interval` 可以传入负数。

### 建议

- 创建 `src/evolution/security/input_validator.py`，提供统一的输入校验函数
- 为飞书消息回调添加签名验证（飞书开放平台支持）
- CLI 参数添加范围校验（如 interval 应在 10-86400 之间）
- 配置文件加载后进行 schema 校验（使用 pydantic 或 jsonschema）

---

## 1.3 SQL 注入风险

### 发现

| 风险等级 | 位置 | 问题描述 |
|---------|------|---------|
| **MEDIUM** | `db_utils.py:287` | `db_get_stats()` 使用 f-string 拼接表名 |
| **MEDIUM** | `health.py:61` | 健康检查使用 f-string 拼接表名 |
| **OK** | `audit_logger.py` | 所有用户输入均使用参数化查询 `?` 占位符 |
| **OK** | `permission_manager.py` | 无直接 SQL 操作 |

### 详析

**存在风险的表名拼接 (db_utils.py:287):**
```python
count_cursor = conn.execute(f"SELECT COUNT(*) FROM [{table_name}]")
```
虽然 `table_name` 来源于 `sqlite_master` 查询结果（系统表），本身不受用户控制，风险较低。但若未来代码演进中表名来源发生变化，此模式将成为漏洞。

**同样的问题 (health.py:61):**
```python
row_counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
```
表名 `t` 同样来自 `sqlite_master`，但缺少方括号包裹，若表名含特殊字符可能出错。

### 建议

- 表名拼接处添加白名单校验：仅允许已知的表名通过
- 使用 `sqlite3` 的参数化查询无法参数化表名，但可以改用 `?` 占位符 + 动态 SQL 构建函数
- 在 CI 中添加 `bandit` 或 `sqlfluff` 扫描，检测 SQL 注入模式

---

## 1.4 文件系统安全

### 发现

| 风险等级 | 位置 | 问题描述 |
|---------|------|---------|
| **MEDIUM** | `db_utils.py:82-84` | `get_evolution_db()` 接受绝对路径，若外部可控可导致任意文件访问 |
| **MEDIUM** | `sandbox_executor.py:275-279` | 临时文件写入临时目录（安全），但无竞态条件防护 |
| **LOW** | `audit_logger.py:640` | 归档清理使用 `os.remove()`，无符号链接检查 |

### 详析

**绝对路径数据库访问:**
```python
if os.path.isabs(db_name):
    db_path = db_name
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
```
如果 `db_name` 参数来自不可信输入（如 CLI 参数 `--data-dir`），攻击者可以指定任意路径。目前 `hermes_daemon.py` 的 `--data-dir` 参数允许用户指定路径，构成潜在风险。

**沙箱临时文件:**
使用 `tempfile.NamedTemporaryFile` 并在 `finally` 块中 `os.unlink()` 是正确的做法。但 `preexec_fn` 中设置资源限制使用 `resource` 模块，非 Linux 系统不可用，仅有一个警告日志。

### 建议

- 用户提供的路径参数应规范化为项目数据目录下的相对路径，拒绝绝对路径或使用 `..` 的路径
- 文件清理操作使用 `os.path.realpath()` 解析符号链接后再操作
- 沙箱执行在非 Linux 系统上的安全降级应有明确文档说明

---

## 1.5 飞书集成安全

### 发现

| 风险等级 | 位置 | 问题描述 |
|---------|------|---------|
| **MEDIUM** | `feishu_notifier.py:295-316` | 模拟模式将所有通知写入明文日志文件，可含敏感信息 |
| **LOW** | `feishu_notifier.py:72` | API 域名可配置但无校验 |
| **OK** | `feishu_notifier.py` | Token 管理：有效期 110 分钟（2 小时 token，安全边界合理） |
| **OK** | `feishu_notifier.py` | HTTPS 强制使用（open.feishu.cn） |

### 详析

**模拟模式的日志泄露风险:**
```python
log_file = "feishu_notifications.log"
with open(log_file, "a", encoding="utf-8") as f:
    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
```
当 webhook 或 OpenAPI 发送失败时，系统回退到模拟模式，将完整的通知内容（可能含系统状态、任务详情、甚至敏感信息）写入 `feishu_notifications.log`。虽然 `.gitignore` 排除了 `*.log`，但运行环境中的日志文件若被未授权访问则是信息泄露。

### 建议

- 模拟模式日志文件应写入数据目录（`data/evolution/`）而非项目根目录
- 日志中的敏感字段（如路径、配置信息）应脱敏处理
- 为 webhook 回调添加飞书签名验证（X-Lark-Signature 头）

---

## 1.6 依赖安全

### 发现

| 风险等级 | 问题描述 |
|---------|---------|
| **MEDIUM** | 无依赖漏洞扫描机制（无 `safety`、`pip-audit`、Dependabot 配置） |
| **LOW** | 依赖数量少（核心仅 psutil, pyyaml, numpy, requests），攻击面较小 |
| **OK** | `pyproject.toml` 中使用 `>=` 版本约束，允许安全补丁自动升级 |

### 建议

- 在 CI 中添加 `pip-audit` 或 `safety check` 步骤
- 添加 `.github/dependabot.yml` 启用自动依赖更新
- 锁定 `requirements-lock.txt` 用于生产部署

---

## 1.7 错误信息泄漏

### 发现

| 风险等级 | 位置 | 问题描述 |
|---------|------|---------|
| **MEDIUM** | `health.py:72,90,121` | 健康检查返回 `str(e)` 原始异常信息，可能暴露内部路径和结构 |
| **LOW** | `sandbox_executor.py:443` | 沙箱异常消息 `f"Subprocess error: {e}"` 可能泄漏系统细节 |
| **OK** | 大部分模块 | 异常记录到 logger，不直接返回给用户 |

### 建议

- 健康检查对外输出应过滤掉文件路径和内部堆栈
- 用户可见的错误信息统一使用错误码 + 通用描述，详情只记录在服务端日志

---

## 1.8 审计日志完整性

### 发现

| 风险等级 | 问题描述 |
|---------|---------|
| **OK** | 审计日志系统设计良好：多级日志、事件分类、自动归档、统计查询 |
| **OK** | CRITICAL 事件自动推送飞书告警 |
| **LOW** | 审计数据库未加密；日志条目无签名，理论上可被篡改 |
| **LOW** | 缺少审计日志的导出/合规报告功能 |

### 优势总结

`AuditLogger` 是项目中最成熟的安全模块：
- 支持 6 种事件类型（AGENT_ACTION, TOOL_EXECUTION, SYSTEM_CONFIG, COLLABORATION, EVOLUTION, SECURITY）
- 4 级日志（INFO/WARNING/ERROR/CRITICAL）
- 10000 条记录自动归档
- `correlation_id` 支持跨组件追踪
- 与 FeishuNotifier、SelfMonitor 深度集成

---

# 第二部分：可观测性 (Observability)

## 2.1 结构化日志

### 发现

| 风险等级 | 问题描述 |
|---------|---------|
| **MEDIUM** | 日志格式为纯文本，非 JSON 结构化，不利于日志聚合工具（ELK/Loki）解析 |
| **OK** | 日志系统设计良好：层级化管理、文件+控制台双输出、幂等初始化 |
| **OK** | 安全模块日志级别默认 WARNING，减少噪音 |

### 详析

当前日志格式：
```
2026-05-10 16:46:17 | INFO  | hermes_evo.closed_loop    | 进化循环 #1 开始
```

此格式对人类可读但对机器解析不友好。字段间使用 ` | ` 分隔，无 key-value 结构。

### 建议

- 添加 JSON 日志格式选项，通过环境变量 `LOG_FORMAT=json` 切换
- JSON 格式应至少包含：timestamp, level, logger, message, module, correlation_id
- 日志中已有的 `correlation_id` 应自动附加到所有相关日志条目

---

## 2.2 健康检查

### 发现

| 风险等级 | 问题描述 |
|---------|---------|
| **MEDIUM** | 健康检查仅 CLI 可用（`hermes-evolution status`），无 HTTP 端点 |
| **OK** | 检查覆盖 4 个组件：DB、Monitor、Plugin、Memory |
| **OK** | 三级状态：healthy / degraded / critical |
| **LOW** | 健康检查未缓存，每次调用都重新实例化组件 |

### 详析

`health.py` 的健康检查设计合理，覆盖了关键组件：
- DB：文件大小、表列表、行计数
- Monitor：成功率、周期数、工具追踪数
- Plugin：部署状态和部署时间
- Memory：条目数和关联数

但仅通过 CLI 调用，无法被外部监控系统（如 Kubernetes liveness probe、Prometheus Blackbox）探测。

### 建议

- 添加一个简单的 HTTP 健康检查端点（如 `GET /health`），返回 JSON 格式状态
- 或至少提供一个 `hermes_evolution.health:health_check` 可被 Hermes Agent 直接调用的 Python API
- 健康检查结果添加缓存（TTL 30 秒），避免每次检查都重新连接数据库

---

## 2.3 指标暴露

### 发现

| 风险等级 | 问题描述 |
|---------|---------|
| **MEDIUM** | 指标仅写入 `system_metrics.jsonl` 文件，无 Prometheus/graphite 导出 |
| **OK** | 指标维度较全面：CPU、内存、线程、成功率、错误率、响应时间 |
| **OK** | `SystemMetricsCollector` 支持自定义指标注册 |
| **LOW** | `evolution_analyze_performance` 函数未在代码库中找到，可能尚未实现或已更名 |

### 详析

`SystemMetricsCollector` 采集的指标维度：
- 系统级：CPU 使用率、内存（MB/%）、线程数、打开文件数、运行时间
- 应用级：工具调用次数、成功率、平均响应时间、错误率
- 进化级：经验数、模式数、改进数

但指标仅以 JSONL 格式写入本地文件，无法被 Prometheus、Grafana 等标准监控栈消费。

### 建议

- 实现 Prometheus metrics exporter（使用 `prometheus_client` 库）
- 暴露指标：`hermes_evolution_cpu_percent`, `hermes_evolution_memory_mb`, `hermes_evolution_success_rate`, `hermes_evolution_tool_calls_total`, `hermes_evolution_cycle_duration_seconds` 等
- `evolution_analyze_performance` 若为文档中承诺的函数，应确认其实现状态

---

## 2.4 告警机制

### 发现

| 风险等级 | 问题描述 |
|---------|---------|
| **MEDIUM** | 告警仅推送到飞书，无多渠道（邮件、短信、PagerDuty） |
| **OK** | 关键安全事件（CRITICAL 级审计日志）自动推送飞书 |
| **OK** | ThreatDetector 的 MEDIUM+ 告警推送飞书 |
| **LOW** | WAL 大小超过阈值仅日志记录，无主动告警 |
| **LOW** | 连续进化失败 5 次仅记录 CRITICAL 日志，未推送告警 |

### 建议

- WAL 超过 100MB 阈值时发送飞书告警
- 连续进化失败 3 次即发送告警（而非等到 5 次停止后）
- 系统健康分数低于 60 时发送告警
- 添加告警静默/聚合机制，避免告警风暴

---

## 2.5 追踪能力

### 发现

| 风险等级 | 问题描述 |
|---------|---------|
| **OK** | `AuditEntry` 包含 `correlation_id` 字段，支持跨组件追踪 |
| **MEDIUM** | `correlation_id` 未自动生成和传播；需调用方显式传入 |
| **LOW** | 无分布式追踪（OpenTelemetry / Jaeger）集成 |

### 建议

- 在 `logging_config.py` 中添加 `correlation_id` 的自动生成（使用 `uuid4`）并通过 `logging.Filter` 自动注入到所有日志记录
- 在进化循环入口处自动创建 `correlation_id`，并通过上下文传播到所有子系统

---

# 第三部分：可恢复性 (Recoverability)

## 3.1 进程恢复

### 发现

| 风险等级 | 问题描述 |
|---------|---------|
| **HIGH** | Daemon 重启后不加载先前的状态：`_load_state()` 方法存在但从未被调用 |
| **MEDIUM** | 无 systemd / supervisor 集成，进程崩溃后无法自动重启 |
| **OK** | 优雅关闭机制完善：`stop_event` + 信号处理 + `stop(timeout=10)` |
| **OK** | 数据目录自动创建（`mkdir(parents=True, exist_ok=True)`） |

### 详析

`EvolutionDaemon._load_state()` (line 382-390) 可以读取 `daemon_state.json` 恢复先前的循环计数、连续失败次数和最近快照，但该方法从未被调用。`HermesEvolutionDaemon.initialize_components()` 在启动时不会恢复状态，意味着每次重启后循环计数器归零，快照历史丢失。

```python
def _load_state(self) -> Optional[Dict[str, Any]]:
    """加载之前的守护进程状态"""
    if self.state_path.exists():
        try:
            with open(self.state_path, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return None
```

### 建议

- 在 `start()` 方法中调用 `_load_state()` 并恢复 cycle_count、consecutive_failures 等状态
- 提供 systemd unit 文件模板：
```ini
[Unit]
Description=Hermes Agent Evolution Daemon
After=network.target

[Service]
Type=simple
User=hermes
ExecStart=/usr/bin/python3 /opt/hermes/hermes_daemon.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 3.2 数据库恢复

### 发现

| 风险等级 | 问题描述 |
|---------|---------|
| **OK** | WAL 模式已启用：SQLite 崩溃后自动恢复，无需手动干预 |
| **OK** | WAL checkpoint 机制完善：PASSIVE/TRUNCATE 模式 + 自动触发 |
| **MEDIUM** | 无定期 `PRAGMA integrity_check` 执行 |
| **MEDIUM** | 无数据库备份自动化 |
| **OK** | `retry_on_db_error` 装饰器提供 SQLite 忙等重试（指数退避） |

### 详析

`db_utils.py` 的数据库连接配置质量高：
- `PRAGMA journal_mode=WAL` — 崩溃后自动恢复
- `PRAGMA synchronous=NORMAL` — WAL 模式下安全且性能好
- `PRAGMA busy_timeout=30000` — 30 秒忙等
- `check_same_thread=False` — 多线程安全

`auto_checkpoint_if_needed()` 监控 WAL 文件大小，超过 100MB 自动 checkpoint，有 PASSIVE→TRUNCATE 的渐进策略。但项目曾出现 89GB WAL 的生产事故，说明当前的 100MB 阈值可能需根据实际负载调整。

### 建议

- 在 daemon 启动时和每日定时执行 `PRAGMA integrity_check` 并记录结果
- 实现自动备份脚本：每日将 SQLite 数据库复制到 `backup_YYYYMMDD/` 目录
- 备份保留策略：保留最近 7 天的日备份 + 最近 4 周的周备份
- 将 WAL 监控阈值配置化，而非硬编码 100MB

---

## 3.3 服务降级

### 发现

| 风险等级 | 问题描述 |
|---------|---------|
| **OK** | 飞书不可用 → 自动回退到模拟模式（本地日志记录） |
| **OK** | 组件初始化独立：单个组件失败不阻止系统启动 |
| **OK** | `collect_minimal()` 提供降级指标采集 |
| **MEDIUM** | 无熔断器（Circuit Breaker）模式 |
| **LOW** | 飞书回退到模拟模式后无自动恢复尝试 |

### 详析

**飞书服务降级 (feishu_notifier.py):**
```python
if mode == "webhook":
    success = self._send_via_webhook(title, content, level)
    if not success:
        return self._send_simulated(title, content, level)
```
当 webhook 或 OpenAPI 发送失败时，自动降级到模拟模式（写入本地日志），保证系统持续运行。但降级后不会自动恢复到正常模式。

**组件独立初始化 (hermes_daemon.py:123-293):**
11 个组件逐一初始化，部分失败（如 `PatternRecognizer`、`ToolRegistry`）不会阻止系统启动，仅标记为非关键并继续。

### 建议

- 实现飞书服务的自动恢复：每隔 5 分钟尝试一次正常发送，成功后切回正常模式
- 为外部依赖添加熔断器：连续失败 N 次后进入熔断状态，M 秒后尝试半开
- 为数据库操作添加超时 + 回退（如内存缓存）

---

## 3.4 状态一致性

### 发现

| 风险等级 | 问题描述 |
|---------|---------|
| **MEDIUM** | 进化循环中断后无法从中间阶段恢复：无检查点机制 |
| **MEDIUM** | Daemon 状态持久化 (`_save_state`) 在每个循环后执行，但循环中途崩溃时可能丢失本次状态 |
| **OK** | `EvolutionSnapshot` 记录了每个阶段的完成情况（`phases_completed` 字段） |
| **LOW** | 审计日志写入和业务操作不在同一事务中 |

### 详析

`EvolutionDaemon._execute_single_cycle()` 执行 6 个阶段（Monitor→Analyze→Plan→Execute→Verify→Feedback），但如果在阶段 4（Execute）中途崩溃，已执行的动作可能已生效但未被记录到快照中，重启后快照历史丢失。

`EvolutionSnapshot.phases_completed` 字段记录了已完成阶段列表，但该字段在循环结束后才通过 `_save_state()` 持久化，重启后无法获知上次中断在哪个阶段。

### 建议

- 在每个阶段完成后立即持久化阶段进度（检查点机制）
- Execute 阶段执行动作前，先将待执行的动作用 WAL 模式写入 pending 状态，执行成功后标记为 committed
- 重启时检查 pending 动作并根据幂等性决定重放或回滚

---

## 3.5 备份策略

### 发现

| 风险等级 | 问题描述 |
|---------|---------|
| **HIGH** | 无自动备份机制：数据库文件仅依赖 SQLite WAL 恢复 |
| **MEDIUM** | 审计日志自动归档（`data/audit_archives/`），但主数据库无备份 |
| **LOW** | `.gitignore` 包含 `backup_*/` 目录，但无备份脚本 |
| **LOW** | 配置文件 (`evolution_config.yaml`) 无版本控制备份 |

### 详析

项目依赖 SQLite WAL 模式进行崩溃恢复，但 WAL 无法防御以下场景：
- 磁盘故障
- 文件误删除
- 数据库文件损坏（非崩溃导致）
- 人为操作错误

**已有措施：**
- 审计日志归档：超过 10000 条后自动归档到 `audit_archive_YYYYMMDD_HHMMSS.db`
- 归档文件 90 天自动清理

**缺失措施：**
- 主数据库（associations.db, tools.db, learning_experiences.db 等）无备份
- daemon 状态文件无备份
- 无备份脚本或 cron job

### 建议

- 创建 `scripts/backup.sh`：
```
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup_${DATE}"
mkdir -p ${BACKUP_DIR}
cp data/evolution/*.db ${BACKUP_DIR}/
cp data/evolution/daemon_state.json ${BACKUP_DIR}/
echo "Backup completed: ${BACKUP_DIR}"
```
- 通过 cron 每日执行备份
- 保留策略：7 天日备份 + 4 周周备份
- 备份文件应存储到独立于项目目录的位置

---

## 3.6 回滚能力

### 发现

| 风险等级 | 问题描述 |
|---------|---------|
| **MEDIUM** | 无代码/配置回滚机制 |
| **LOW** | `evolution_config.yaml` 中声明了 `rollback_on_failure: true`，但未找到实现 |
| **LOW** | 审计日志归档保留了历史记录，但无法用于回滚 |

### 详析

配置文件声明了回滚能力：
```yaml
rollback:
  enabled: true
  max_versions: 10
  auto_rollback_on_failure: true
```

但代码库中未找到对应的回滚实现。进化引擎的 `ActionExecutor` 执行改进动作后，若验证阶段（Verify）发现退化，没有机制可以撤销已执行的动作。

### 建议

- 为每种改进动作类型实现对应的回滚操作（策略切换可回退、参数调整可恢复原值）
- 在 Execute 阶段前保存当前状态快照，Verify 检测到退化时自动回滚
- 如需完整的版本回退能力，建议引入 Git tag + 数据库迁移脚本的组合方案

---

# 第四部分：综合评估与优先修复建议

## 4.1 风险矩阵

### 安全性

| 风险项 | 等级 | 紧迫度 |
|-------|------|-------|
| App ID 硬编码在源码 | HIGH | 立即修复 |
| DB 默认密码硬编码 | HIGH | 立即修复 |
| 无依赖安全扫描 | MEDIUM | 本周 |
| 日志明文写敏感信息 | MEDIUM | 本周 |
| 异常信息泄漏内部路径 | MEDIUM | 本周 |
| 无输入校验统一层 | MEDIUM | 本月 |
| 用户路径参数未 normalize | MEDIUM | 本月 |

### 可观测性

| 风险项 | 等级 | 紧迫度 |
|-------|------|-------|
| 无 HTTP 健康检查端点 | MEDIUM | 本周 |
| 无 Prometheus 指标导出 | MEDIUM | 本月 |
| 日志非 JSON 结构化 | MEDIUM | 本月 |
| WAL 超阈值无告警 | LOW | 本月 |
| correlation_id 未自动传播 | LOW | 本月 |

### 可恢复性

| 风险项 | 等级 | 紧迫度 |
|-------|------|-------|
| Daemon 重启不恢复状态 | HIGH | 立即修复 |
| 无自动备份机制 | HIGH | 本周 |
| 进化循环无检查点 | MEDIUM | 本周 |
| 无 systemd 集成 | MEDIUM | 本月 |
| 飞书降级后无自动恢复 | LOW | 本月 |
| 回滚机制仅声明未实现 | MEDIUM | 本月 |

---

## 4.2 优先修复路线图

### 第一优先级（立即修复，1-3 天）

1. **移除硬编码敏感信息**
   - `feishu_notifier.py`: 移除 App ID 默认值
   - `deployment_service.py`: 移除 `hermes123` 默认密码

2. **Daemon 状态恢复**
   - 在 `EvolutionDaemon.start()` 中调用 `_load_state()`
   - 恢复 cycle_count、consecutive_failures、快照历史

### 第二优先级（本周内，3-7 天）

3. **自动备份实现**
   - 创建 `scripts/backup.sh` + cron job
   - 备份所有数据库和状态文件

4. **进化循环检查点**
   - 在 `_execute_single_cycle()` 中每个阶段完成后立即持久化进度

5. **依赖安全扫描**
   - CI 中添加 `pip-audit`
   - 添加 Dependabot 配置

6. **HTTP 健康检查端点**
   - 在 `health.py` 中添加 Flask/FastAPI 端点
   - 或集成到 Hermes Agent 的插件 API

### 第三优先级（本月内，7-30 天）

7. **Prometheus 指标导出**
   - 添加 `prometheus_client` 依赖
   - 实现核心指标 exporter

8. **结构化日志**
   - 添加 JSON 日志格式选项
   - 自动注入 correlation_id

9. **统一输入验证层**
   - 创建 `input_validator.py`
   - CLI 参数范围校验

10. **systemd 集成**
    - 提供 systemd unit 文件
    - 添加健康检查脚本

---

## 4.3 已具备的优势

项目在以下方面表现良好，值得保持：

- **审计日志系统**：完善的多级审计、自动归档、威胁告警联动
- **威胁检测引擎**：8 条内置规则、频率检测、正则匹配、自定义条件
- **权限控制系统**：RBAC 四级角色、继承链、资源所有权
- **沙箱执行环境**：AST 代码分析、资源限制、临时文件清理
- **WAL 数据库模式**：崩溃自动恢复、并发读写支持
- **服务降级设计**：飞书不可用时自动切换到本地日志
- **组件独立初始化**：单点故障不阻塞系统启动

---

审视完成。报告生成时间：2026-05-10
