.PHONY: install test lint format clean build check help

# ═══════════════════════════════════════════════════════════════════
# HermesAgentEvolution v7.0.1 — Makefile
# ═══════════════════════════════════════════════════════════════════

PYTHON = python3
PIP = $(PYTHON) -m pip
PYTEST = $(PYTHON) -m pytest
RUFF = $(PYTHON) -m ruff

help: ## 显示可用命令
	@echo "HermesAgentEvolution v7.0.1"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装开发依赖 (可编辑模式)
	$(PIP) install -e ".[dev,full]"

install-min: ## 最小安装 (仅核心依赖)
	$(PIP) install -e .

test: ## 运行全量测试 (快速模式)
	$(PYTEST) tests/ -q --tb=line

test-v: ## 运行全量测试 (详细模式)
	$(PYTEST) tests/ -v --tb=short

test-cov: ## 运行测试 + 覆盖率报告
	$(PYTEST) tests/ --cov=src/evolution --cov=src/services --cov-report=html --cov-report=term

test-failed: ## 仅重跑上次失败的测试
	$(PYTEST) tests/ -q --tb=short --lf

lint: ## 代码检查
	$(RUFF) check src/ tests/

format: ## 代码格式化
	$(RUFF) format src/ tests/

fix: ## 自动修复 lint 问题
	$(RUFF) check src/ tests/ --fix

clean: ## 清理构建产物
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info htmlcov/ .coverage reports/*.json reports/*.md 2>/dev/null || true

build: ## 构建 PyPI 包
	$(PIP) install build --quiet
	$(PYTHON) -m build

check: ## 环境自检
	$(PYTHON) -c "from src.evolution.cli import cmd_check; exit(0 if cmd_check() else 1)"

setup: ## 一键部署 Hermes 插件
	$(PYTHON) -c "from src.evolution.cli import cmd_setup; exit(0 if cmd_setup() else 1)"

check-all: lint test ## 全量检查 (lint + test)
	@echo ""
	@echo "✅ 全量检查通过"

pre-commit-install: ## 安装 pre-commit hooks
	$(PIP) install pre-commit --quiet
	pre-commit install

docker-build: ## 构建 Docker 镜像 (高级用户)
	docker build -t hermes-agent-evolution:3.0.3 -f docker/Dockerfile .

version: ## 显示当前版本
	@$(PYTHON) -c "from pathlib import Path; import re; \
		c = Path('pyproject.toml').read_text(); \
		m = re.search(r'version\s*=\s*\"([^\"]+)\"', c); \
		print(m.group(1) if m else 'unknown')"
