# 发版检查清单

> 每次发布前逐项验证，确保质量。

---

## 代码质量

- [ ] 测试全部通过：`hermes-evolution test` → `422 passed`
- [ ] `ruff check src/ tests/` 零错误
- [ ] 所有 `print()` 已替换为 `logger`（或确认有意保留）
- [ ] 无硬编码绝对路径
- [ ] `EVOLUTION_DATA_DIR` 环境变量可覆盖 DB 路径
- [ ] `enhanced_tool_creator.py` 无未完成的 TODO（L313/L695/L805）

---

## 版本一致性

| 文件 | 版本字段 | 检查 |
|------|----------|:--:|
| `pyproject.toml` | `[project] version` | |
| `setup.py` | `version="x.y.z"` | |
| `hermes-plugin/plugin.yaml` | `version: "x.y.z"` | |
| `README.md` | badges 版本号 + 测试数 | |
| `docs/INSTALLATION.md` | 版本号 | |
| `docs/ARCHITECTURE.md` | 版本号 | |
| `src/evolution/cli.py` | 硬编码版本号 | |
| `CHANGELOG.md` | 新增版本条目 | |

---

## 包发布

- [ ] `python3 -m build` 成功
- [ ] `twine check dist/*` 零 warning
- [ ] TestPyPI 安装验证：`pip install -i https://test.pypi.org/ hermes-agent-evolution`
- [ ] 生产 PyPI 上传：`twine upload dist/*`
- [ ] 全新 venv 安装验证：`pip install hermes-agent-evolution && hermes-evolution check`

---

## 插件部署验证

- [ ] `hermes-evolution setup` 成功
- [ ] `~/.hermes/plugins/hermes-evolution/plugin.yaml` 存在
- [ ] Hermes 重启后 `hermes tools list | grep evolution` 显示 6 个工具
- [ ] 每个工具调用成功（在 Hermes 会话中测试）

---

## 文档

- [ ] README.md — 5秒安装、V3架构图、项目状态表、badge 最新
- [ ] docs/INSTALLATION.md — pip + 插件 + Docker 三路径
- [ ] docs/ARCHITECTURE.md — V3 融合架构图 + fusion 桥说明
- [ ] docs/QUICKSTART.md — 5分钟上手
- [ ] docs/LOGGING.md — 日志使用指南
- [ ] docs/CONFIGURATION.md — 配置参数表
- [ ] docs/API_REFERENCE.md — 30 模块全覆盖
- [ ] CHANGELOG.md — 完整变更日志
- [ ] CONTRIBUTING.md — 开发规范

---

## CI/CD

- [ ] `.github/workflows/ci.yml` 存在且通过
- [ ] `.pre-commit-config.yaml` 存在
- [ ] push 到 main → GitHub Actions 全绿
- [ ] Python 3.9/3.10/3.11/3.12/3.13 matrix 全部通过

---

## 功能验证

- [ ] `hermes-evolution check` 全部 ✅
- [ ] `hermes-evolution status` 信息准确
- [ ] 全新 venv 安装 → `from evolution import ...` 无 ImportError
- [ ] 工具创建：`evolution_create_tool` 成功注册
- [ ] 学习循环：`evolution_learn` + `evolution_run_cycle` 无异常
- [ ] 记忆关联：`evolution_memory_discover` 返回结果
- [ ] 自我监控：`evolution_self_monitor` 返回健康分数

---

## Docker（可选）

- [ ] `docker build -t hermes-agent-evolution:x.y.z -f docker/Dockerfile .` 成功
- [ ] `docker-compose up -d` → 健康检查通过
- [ ] （如推 Hub）`docker push wayneliu519888/hermes-agent-evolution:x.y.z`

---

## 发布流程

```bash
# 1. 最终检查
make check-all

# 2. 更新版本号（6个文件）
#    pyproject.toml / setup.py / plugin.yaml / README / docs/INSTALLATION / docs/ARCHITECTURE

# 3. 更新 CHANGELOG
vim CHANGELOG.md

# 4. 提交 + 打 tag
git add -A
git commit -m "release: vx.y.z"
git tag "vx.y.z"
git push origin main --tags

# 5. 构建 + 发布
make build
twine check dist/*
twine upload dist/*
```
