# HAE 工具调度问题 — 根因分析与解决方案

## 问题现象

evolution_self_monitor 等在 gateway 中返回 "not available" 或旧版错误信息，
硬编码 return 测试证实 handler 从未被执行。

## 根因

**三层缓存叠加导致工具调用阻塞：**

### 1. Python import 缓存
`plugin_core.py` 在进程启动时 import，修改代码后进程不自动 reload。
- CLI 主进程在代码修改前启动 → 使用旧 handler
- Gateway 主进程在代码修改前启动 → 使用旧 handler

### 2. Hermes dispatch 缓存（gateway 特有）
技能文件 `gateway-handler-dispatch-cache.md` 记录：
gateway 对失败的 tool call 有响应缓存。首次调用失败（多线程竞争导致
`_engine_instances` 为 None）后，后续调用直接返回缓存的错误响应，
不再执行 handler。

### 3. _engine_instances 多线程竞争
gateway 多线程同时首次调用时，注册和初始化并发触发，
None 被缓存导致 handler 内部获取不到实例。

## 完整调用链路（已验证，CLI 和 Gateway 完全一致）

```
gateway/CLI → discover_plugins()
  → PluginManager.discover_and_load()
    → _load_plugin() → register(ctx)
      → ctx.register_tool(name, toolset, schema, handler)
        → registry.register(handler=handler)  # 存入 self._tools[name]
          → dispatch(name, args)
            → entry.handler(args, **kwargs)
```

## 已验证（本次排查）

1. ✅ 链路一致 — CLI 和 gateway 同路径
2. ✅ _handle_self_monitor — health_score=100, 正常
3. ✅ _handle_audit — 正常
4. ✅ _handle_recall_lessons — 正常
5. ✅ _handle_analyze_performance — 已修复 `analyze()`→`generate_performance_report()`
6. ✅ 新进程调用 handler 完全正常

## 修复方案

### 方案 A（推荐，根治）：handler 动态 reload

在 `plugin_core.py` 的 `register()` 中，每个 handler 改为动态 import：

```python
def _make_reloading_handler(module_name, func_name):
    def handler(params, **kwargs):
        import importlib
        mod = importlib.import_module(module_name)
        importlib.reload(mod)  # 清除 import 缓存
        fn = getattr(mod, func_name)
        return fn(params, **kwargs)
    return handler
```

然后在 tools 列表中：
```python
tools = [
    ("evolution_run_cycle", ..., _make_reloading_handler("evolution.plugin_core", "_handle_run_cycle")),
    ...
]
```

优点：每次工具调用都实时加载最新代码，永不缓存。
缺点：有轻微性能开销（importlib.reload）。

### 方案 B（简单）：重启触发点

在 `register()` 函数中添加 `importlib.invalidate_caches()`，确保
每次 gateway 启动时强制清除 Python import 缓存。

### 方案 C（已实施的当前状态）
重启 gateway + 清 pyc → 新会话可用。但不是永久方案。

## 已修复的 Bug

- `_handle_analyze_performance`: `analyzer.analyze()` → `analyzer.generate_performance_report()`
  （文件：`src/evolution/plugin_core.py` L142-157）
