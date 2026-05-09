# 文档全面重构计划

> **目标**: 代码与文档完全一致，所有版本号统一 v3.0.6，体现迭代1→10演进过程
> **策略**: 并行重构，分组执行

---

## 发现的核心问题

1. **版本碎片化**: 16个文档中散布 v2/2.0.0/v3.0.0/v3.0.3/v3.0.4/v3.0.6 共6种版本
2. **V2与V3架构矛盾**: v2_architecture.md 描述 PostgreSQL+Redis+K8s，V3实际为纯SQLite融合架构
3. **API文档严重过时**: API_REFERENCE.md 标注v2，缺少closed_loop/collaboration/security/fusion等11+模块
4. **测试数字不一致**: 不同文档引用374/406/422/428四种测试数
5. **Python版本矛盾**: INSTALLATION.md说3.10+，其他说3.9+
6. **数据库列表不完整**: 实际7个DB文件，各文档列表不一致

---

## 重构分组（4组并行）

### 组A: 核心入口文档（3个）
| # | 文件 | 当前状态 | 重构方向 |
|---|------|---------|---------|
| 1 | README.md | v3.0.4 badge, 422 passed | → v3.0.6, 439 passed, 迭代1-10完成, 75提交 |
| 2 | CHANGELOG.md | 已更新到v3.0.6 | 补充迭代9-10细节，统一格式 |
| 3 | CONTRIBUTING.md | v3.0.4 | → v3.0.6, 更新项目结构 |

### 组B: 架构与API文档（4个）
| # | 文件 | 当前状态 | 重构方向 |
|---|------|---------|---------|
| 4 | docs/ARCHITECTURE.md | v3.0.0, 缺evolution_auditor | → v3.0.6, 补全10个子系统, 补evolution_auditor+tool_strategy_learner持久化 |
| 5 | docs/API_REFERENCE.md | v2 (Iteration 3), 19模块 | → v3.0.6, 补全57个类的完整API, 含closed_loop/collaboration/security/fusion/services |
| 6 | docs/evolution_plan.md | v3.0.6, 迭代10完成 | 精修: 统一迭代描述, 补充成果数据 |
| 7 | docs/HERMES_INTEGRATION.md | 2.0.0, 6工具 | → v3.0.6, 7+工具, 含evolution_audit, 更新架构图 |

### 组C: 用户指南文档（4个）
| # | 文件 | 当前状态 | 重构方向 |
|---|------|---------|---------|
| 8 | docs/INSTALLATION.md | v3.0.0, Python 3.10+ | → v3.0.6, Python 3.9+, 更新pip install命令 |
| 9 | docs/CONFIGURATION.md | v3.0.6 | 精修: 补evolution_audit.db, 统一7个DB文件列表 |
| 10 | docs/QUICKSTART.md | 无版本号 | → v3.0.6, 更新示例代码匹配当前API |
| 11 | docs/LOGGING.md | 无版本号 | 精修: 更新logger层级含services实际路径 |

### 组D: 工程化+历史文档（5个）
| # | 文件 | 当前状态 | 重构方向 |
|---|------|---------|---------|
| 12 | docs/TESTING.md | 22文件, 428 passed | → 24文件, 439 passed, 补test_tool_strategy_persistence+test_evolution_auditor |
| 13 | docs/RELEASE_CHECKLIST.md | v3.0.0, 422 passed | → v3.0.6, 439 passed, 10文件版本同步, 补evolution_auditor验证 |
| 14 | docs/v2_architecture.md | V2.0.0 (2024) | → 顶部加"已归档"标记，保留作为历史参考 |
| 15 | docs/v2_status_report.md | V2.0.0 (2024) | → 顶部加"已归档"标记 |
| 16 | docs/iteration5_engineering_plan.md | v3.0.0 | → 加"✅ 已完成"标记，追加实际成果 vs 计划对比 |

### 组E: 迭代计划文档（归档） — 后续
| # | 文件 | 重构方向 |
|---|------|---------|
| 17 | docs/iteration9_plan.md | → 加"✅ 已完成 (v3.0.5)"标记 |
| 18 | docs/iteration10_auditor_plan.md | → 加"✅ 已完成 (v3.0.6)"标记 |
| 19 | docs/PORTING.md | → 标注v3.0.6, 修复过时代码示例 |

---

## 全局一致性规则

1. **版本号**: 所有文档统一 v3.0.6
2. **Python**: 统一 3.9+
3. **测试数**: 统一 439 passed
4. **DB文件**: 统一7个 (tools/tool_performance/learning_experiences/associations/retrieval_optimization/closed_loop/evolution_audit)
5. **工具数**: 7个 (evolution_memory_discover/evolution_create_tool/evolution_run_cycle/evolution_learn/evolution_self_monitor/evolution_audit/evolution_health_check)
6. **代码行数**: 核心~26,561行, 测试~9,700行
7. **总提交数**: 75
8. **迭代覆盖**: 迭代1-10全部完成
9. **导入路径**: 使用 `from evolution.xxx import` (pip安装兼容) 或 `from src.evolution.xxx import` (开发模式)
10. **数据库路径**: `~/.hermes/data/evolution/`
