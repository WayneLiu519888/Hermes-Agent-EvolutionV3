# 贡献指南 (CONTRIBUTING)

欢迎为 HermesAgentEvolution 项目贡献代码！

## 分支策略

- `main` — 稳定分支，保护分支，禁止直接推送
- `feat/*` — 功能分支
- `fix/*` — 修复分支
- `docs/*` — 文档分支
- `chore/*` — 杂项分支

## 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/)：

```
<type>(<scope>): <描述>

type: feat | fix | docs | test | refactor | chore | perf
scope: 模块名 (如 memory, security, learning)
描述: 中文简述变更内容
```

示例:
```
feat(security): 添加沙箱执行器
fix(memory): 修复 WAL 模式连接泄漏
docs: 更新 CONTRIBUTING.md
test(closed_loop): 补测 daemon 生命周期
```

## 开发环境

```bash
# Python 版本
Python >= 3.12

# 安装依赖
pip install -e ".[dev]"

# 运行测试
python3 -m pytest tests/ -v

# 运行单个测试文件
python3 -m pytest tests/test_closed_loop.py -v
```

## 测试要求

- **新增功能必须有对应测试** — 目标覆盖率 ≥80%
- 使用 pytest 框架（优先，兼容 unittest）
- 测试文件命名: `tests/test_<module>.py`
- 每个测试方法必须有中文 docstring
- 测试应独立、可重复、不依赖外部服务

详见 [TESTING.md](docs/TESTING.md)

## 代码风格

- 遵循 PEP 8
- 模块以中文 docstring 开头
- 类型注解推荐使用（非强制）
- 数据库操作必须通过 `db_utils.get_evolution_db()` 获取连接

## 代码审查

- 所有合并到 main 需要 PR review
- CI 全部通过（测试 + lint）
- 需关联 GitHub Issue（如有）

## 项目结构

```
hermes_agent_evolution/
├── src/evolution/        # 核心演化引擎
│   ├── closed_loop/      # 闭环自主演化
│   ├── collaboration/    # 多Agent协作
│   ├── fusion/           # V1/V2融合
│   ├── learning/         # 经验学习
│   ├── memory/           # 关联记忆
│   ├── security/         # 安全增强
│   └── tools/            # 工具进化
├── tests/                # 测试
├── docs/                 # 文档
├── hermes-plugin/        # Hermes Agent 插件
└── pyproject.toml        # 项目配置
```

## 行为准则

请保持专业和尊重的沟通。
