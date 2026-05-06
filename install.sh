#!/bin/bash
set -e

# ═══════════════════════════════════════════════════════════════════
# HermesAgentEvolution v3.0.0 — 一键安装脚本
# ═══════════════════════════════════════════════════════════════════

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🚀 HermesAgentEvolution v3.0.0 安装程序"
echo "=========================================="
echo ""

# ── 1. Python 版本检查 ──
echo -n "📌 检查 Python 版本... "
PYTHON=$(which python3 2>/dev/null || which python 2>/dev/null)
if [ -z "$PYTHON" ]; then
    echo -e "${RED}❌ 未找到 Python${NC}"
    echo "   请安装 Python 3.9+: https://www.python.org/downloads/"
    exit 1
fi

PY_VER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_OK=$($PYTHON -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" 2>/dev/null && echo "yes" || echo "no")

if [ "$PY_OK" = "yes" ]; then
    echo -e "${GREEN}✅ Python $PY_VER${NC}"
else
    echo -e "${RED}❌ Python $PY_VER (需要 ≥3.9)${NC}"
    exit 1
fi

# ── 2. pip 安装核心包 ──
echo -n "📦 安装 hermes-agent-evolution... "

# 优先从源码安装（开发模式）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_DIR/pyproject.toml" ]; then
    $PYTHON -m pip install -e "$PROJECT_DIR" --quiet 2>&1
    echo -e "${GREEN}✅ 源码安装完成${NC}"
else
    # 尝试从 PyPI 安装
    $PYTHON -m pip install hermes-agent-evolution --quiet 2>&1 || {
        echo -e "${YELLOW}⚠️  PyPI 安装失败，尝试从源码安装${NC}"
        echo "   请手动: git clone ... && pip install -e ."
        exit 1
    }
    echo -e "${GREEN}✅ PyPI 安装完成${NC}"
fi

# ── 3. 环境自检 ──
echo "🔍 环境自检..."
$PYTHON -c "
import sys
sys.path.insert(0, '$PROJECT_DIR/src')
from evolution.cli import cmd_check
ok = cmd_check()
" || {
    echo -e "${YELLOW}⚠️  部分检查未通过，但核心功能可能仍可用${NC}"
}

# ── 4. 插件部署 ──
echo ""
echo -n "🔌 部署 Hermes 插件... "
HERMES_PLUGIN_DIR="${HOME}/.hermes/plugins/hermes-evolution"

if [ -d "$PROJECT_DIR/hermes-plugin" ]; then
    mkdir -p "$HERMES_PLUGIN_DIR"
    cp -r "$PROJECT_DIR/hermes-plugin/"* "$HERMES_PLUGIN_DIR/" 2>/dev/null || true
    echo -e "${GREEN}✅ 已部署到 $HERMES_PLUGIN_DIR${NC}"
else
    echo -e "${YELLOW}⚠️  未找到 hermes-plugin/ 目录${NC}"
fi

# ── 5. 重启 Hermes ──
if command -v hermes &> /dev/null; then
    echo -n "🔄 重启 Hermes Gateway... "
    hermes gateway restart 2>/dev/null && echo -e "${GREEN}✅${NC}" || echo -e "${YELLOW}⚠️  手动执行: hermes gateway restart${NC}"
fi

# ── 6. 完成 ──
echo ""
echo "=========================================="
echo -e "${GREEN}✅ 安装完成!${NC}"
echo ""
echo "验证安装:"
echo "  python3 -m src.evolution.cli check"
echo "  python3 -m src.evolution.cli status"
echo ""
echo "Hermes 中使用:"
echo "  hermes tools list | grep evolution"
echo "  (应该显示 6 个 evolution_* 工具)"
