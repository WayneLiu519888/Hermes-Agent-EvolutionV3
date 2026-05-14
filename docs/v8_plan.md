# V8.0.0 规划方案

> 发布日期：待定
> 
> 主题：打破壁垒，统一环境，让进化真正运行

---

## 背景

7.x 系列（7.0.7 - 7.0.16）修了 10+ 个 bug，但三个结构性痛点未解：

| 痛点 | 症状 | 损失 |
|------|------|------|
| gateway 三层缓存 | 改代码不生效，手动 cp+清pyc+重启反复折腾 | 每次改代码多花 5-10 分钟 |
| 进化周期虚假执行 | run_cycle 总是 10 patterns, 3 issues, 5/5, 0.00 | 进化系统完全空转 |
| 双 Python 环境 | venv 3.11 跑 gateway / 系统 3.12 装包 / 手动 cp 同步 | 代码修改经常只改了一个路径 |

V8.0.0 目标：**一次根治，不再反复补漏。**

---

## A 组：打破三层缓存（3天）🔴 Blocker

### A1. 实施 `_make_dynamic_handler` 根治方案

网关三层缓存——① Python pyc 缓存、② Hermes dispatch 缓存、③ `_engine_instances` 竞争。修改 plugin_core.py 后重启 gateway 也常不生效。

```python
def _make_dynamic_handler(tool_name):
    def handler(params, **kwargs):
        import importlib
        importlib.invalidate_caches()
        from evolution import plugin_core
        importlib.reload(plugin_core)
        real_handler = getattr(plugin_core, f'_handle_{tool_name}')
        return real_handler(params, **kwargs)
    return handler
```

8 个工具的 `register()` 全部改用 `_make_dynamic_handler("xxx")`。

### A2. 验证标准

- 修改 plugin_core.py 任意一行 → 不重启 gateway → 返回新结果
- `evolution_self_monitor` 不再返回 "not available"

### 参考

- Pitfall 35：三层缓存叠加
- Pitfall 39：`del sys.modules[k]` KeyError

---

## B 组：进化周期真实性（2天）🔴

### B1. 诊断六阶段

`evolution_run_cycle` 每次都返回 `10 patterns, 3 issues, 5/5, 0.00`——框架在跑，数据是壳子。

- 每阶段注入唯一标记（trace_id + 随机后缀），验证两轮结果差异化
- 确认 `_engine_instances` 所有组件正确初始化（TTL 恢复 + threading.Lock）
- 追踪 `analyze() → plan() → execute()` 完整真实数据流

### B2. 验证标准

- 连续两次 run_cycle 返回不同的 analysis 结果
- `evolution_audit` 的 `improvements_detected` 不为 0

### 参考

- Pitfall 20：`_engine_instances` 多线程竞争
- Pitfall 26：TTL 恢复模式防 None 永久缓存
- Pitfall 36：进化周期虚假执行

---

## C 组：Python 环境统一到系统 3.12（1天）🟡

### 现状

```
系统 Python 3.12 (/usr/bin/python3)
  ├─ pip install HAE → /usr/local/lib/python3.12/dist-packages/evolution/
  └─ gateway 不从这里跑

gateway venv 3.11 (/root/.hermes/hermes-agent/.venv/bin/python)
  ├─ 无 pip，无法装包
  └─ 手动 cp 同步 evolution 代码
```

### 方案

| 步骤 | 操作 | 状态 |
|------|------|------|
| C1 | `evolution` 全 52 模块 Python 3.12 兼容性验证 | ✅ 已验证 |
| C2 | `PYTHONPATH=/root/.hermes/hermes-agent` 可找到 hermes-agent | ✅ 已验证 |
| C3 | systemd unit ExecStart 改为 `/usr/bin/python3 -m hermes_cli.main gateway run --replace` | 待执行 |
| C4 | systemd unit 加 `Environment=PYTHONPATH=/root/.hermes/hermes-agent` | 待执行 |
| C5 | 删除 venv site-packages 中的 evolution 手动副本 | 待执行 |

**效果：** `pip install -U hermes-agent-evolution` → gateway 自动加载 → 开发 1 步到位。

**回滚：** 改回原 ExecStart 即可，秒级恢复，无数据损失。

---

## D 组：数据闭环强化（2天）🟢

### D1. 审计追溯端到端生效

A 组完成后，`evolution_audit` 的新 action（`get_recent_issues`、`query_issues_by_type`）在 gateway 中可用。

验证：
- `evolution_audit get_recent_issues` → 返回真实问题（非空列表）
- `evolution_audit query_issues_by_type tool_low_performance` → 按类型筛选成功

### D2. hermes memory ↔ HAE memory_entries 桥接

V7.0.8 做了基础同步，连接的是测试垃圾数据。完善：
- `on_session_start` hook：正确注入 HAE 学习经验到 hermes memory
- `post_llm_call` hook：正确提取对话知识点

### 参考

- Pitfall 28：hermes memory 与 HAE 双系统桥接
- Pitfall 29：异步 Agent 知识点提取
- Pitfall 43：审计统计 vs 详情

---

## E 组：版本发布自动化（1天）🟢

`scripts/release.sh <version>` 一键完成：

1. 版本号同步（pyproject.toml / setup.py / __init__.py / VERSION / CHANGELOG）
2. 自动检测 `hermes-plugin/` 与 `src/evolution/_plugin/` 同步
3. 冒烟测试：`python3 -c "import evolution.plugin_core"`
4. 全量 pytest（失败阻止发布）
5. Git 提交 + tag + push
6. `python3 -m build` + `twine upload`

### 参考

- Pitfall 23：版本发布标准工作流
- Pitfall 24：双 plugin 目录同步
- Pitfall 46：缩进冒烟测试

---

## F 组：`hae uninstall` 一键卸载（0.5天）🟢

### 7 层清理

| 层 | 内容 | 选项控制 |
|----|------|----------|
| 1 | pip 包 `hermes-agent-evolution` | — |
| 2 | 插件 `~/.hermes/plugins/hermes-evolution/` | — |
| 3 | 系统 site-packages `evolution/` | — |
| 4 | venv site-packages `evolution/` | — |
| 5 | 所有 `__pycache__/` | — |
| 6 | 数据 `~/.hermes/data/evolution/` (116MB) | `--keep-data` 跳过 |
| 7 | pipx（如存在） | — |

### CLI

```
hae uninstall [--dry-run] [--keep-data] [--force]
```

| 参数 | 效果 |
|------|------|
| 默认 | 交互式确认，删 1-6 层 |
| `--dry-run` | 只列出会删什么，不执行 |
| `--keep-data` | 保留第 6 层（数据目录） |
| `--force` | 跳过确认，直接删 |

---

## G 组：简化指令 `HAE`（0.5天）🟢

```toml
[project.scripts]
hermes-evolution = "evolution.cli:main"
hae = "evolution.cli:main"
```

| 旧命令 | 新命令 | 长度缩减 |
|--------|--------|----------|
| `hermes-evolution check` | `hae check` | -65% |
| `hermes-evolution setup` | `hae install` | -60% |
| `hermes-evolution version` | `hae version` | -58% |

`hermes-evolution` 保留，不破坏已有用户习惯。

---

## H 组：`hae` 完整命令体系 + help 系统（1天）🟢

### 10 个一级命令，28 个二级子命令

```
hae install [--force]                               部署插件到 Hermes
hae uninstall [--dry-run|--keep-data|--force]
hae check [--fix|--clean]                           环境自检
hae status [--detail|--json]                        运行状态
hae version [--all]                                 版本信息
hae test [--quick|--suite <name>]                   测试
hae db info|clean|vacuum|backup                     数据库管理
hae cycle run|status|history|detail                 进化控制
hae audit summary|cycles|detail|issues|trend        审计查询
hae log [--tail|--level]                            日志查看
hae config show|doctor|validate                     配置诊断
```

### help 系统（三级）

```
hae --help              总览所有命令
hae db --help           二级：db 子命令
hae db clean --help     三级：clean 详细用法 + 示例
```

### 示例输出

```
$ hae --help
HAE — Hermes Agent Evolution 命令行工具

核心命令:
    install         部署 HAE 插件到 Hermes
    uninstall       一键卸载，清理所有残留
    check           环境自检
    status          查看系统运行状态
    version         显示版本信息

进化控制:    cycle    run / status / history / detail
审计查询:    audit    summary / cycles / issues / trend
数据管理:    db       info / clean / vacuum / backup
测试诊断:    test / log / config

运行 'hae <command> --help' 查看子命令详情。
```

### 助记规则

| 分类 | 一级命令 | 二级命令 |
|------|----------|----------|
| 生命周期 | install / uninstall | — |
| 状态 | check / status / version | — |
| 数据库 | db | info / clean / vacuum / backup |
| 进化 | cycle | run / status / history / detail |
| 审计 | audit | summary / cycles / detail / issues / trend |
| 诊断 | test / log / config | — |

---

## 总览

| 组 | 内容 | 工时 | 优先级 | 前置 |
|----|------|------|--------|------|
| **A** | 打破三层缓存 | 3天 | 🔴 Blocker | — |
| **B** | 进化周期真实性 | 2天 | 🔴 | A |
| **C** | Python 环境统一 | 1天 | 🟡 | A |
| **D** | 数据闭环强化 | 2天 | 🟢 | A+B |
| **E** | 版本发布自动化 | 1天 | 🟢 | — |
| **F** | `hae uninstall` 一键卸载 | 0.5天 | 🟢 | — |
| **G** | 简化指令 `HAE` | 0.5天 | 🟢 | — |
| **H** | `hae` 完整命令体系 + help | 1天 | 🟢 | G |

**总计：11 天工时，8 组 23 个任务。**

### 执行顺序

```
A 组（破缓存）────────────────────────────┐
  ├──→ C 组（统环境）  ← 可并行          │
  ├──→ B 组（真进化）                    │
  │     └──→ D 组（闭循环）              │
  ├──→ E 组（自动化）  ← 可并行          │
  └──→ G → H（hae 体系） ← 可并行        │
       └──→ F（卸载）                    │
```
