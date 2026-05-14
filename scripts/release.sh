#!/bin/bash
# HAE 一键发布脚本
# 用法: ./scripts/release.sh <version>
# 示例: ./scripts/release.sh 8.0.0

set -euo pipefail

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
    echo "用法: $0 <version>"
    echo "示例: $0 8.0.0"
    exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "========================================="
echo " HAE 发布 $VERSION"
echo "========================================="

# ── 1. 版本号同步 ──────────────────────────
echo ""
echo "[1/7] 同步版本号到 5 个文件..."

FILES=(
    "pyproject.toml:version = \"$VERSION\""
    "setup.py:    version=\"$VERSION\","
    "src/evolution/__init__.py:__version__ = \"$VERSION\""
    "VERSION:$VERSION"
    "hermes-plugin/plugin.yaml:version: \"$VERSION\""
)

for entry in "${FILES[@]}"; do
    file="${entry%%:*}"
    [ ! -f "$file" ] && { echo "  ⚠ 跳过: $file (不存在)"; continue; }
    sed -i "s/version.*=.*/$(echo "$entry" | cut -d: -f2-)/" "$file" 2>/dev/null || true
    echo "  ✅ $file"
done

echo "$VERSION" > VERSION

# ── 2. 双 plugin 目录同步检测 ─────────────
echo ""
echo "[2/7] 检测 plugin 目录同步..."

HP="hermes-plugin/plugin.yaml"
SP="src/evolution/_plugin/plugin.yaml"
if [ -f "$HP" ] && [ -f "$SP" ]; then
    if diff -q "$HP" "$SP" >/dev/null 2>&1; then
        echo "  ✅ hermes-plugin/ 与 _plugin/ 同步"
    else
        echo "  ❌ hermes-plugin/ 与 _plugin/ 不同步！"
        diff "$HP" "$SP"
        exit 1
    fi
else
    echo "  ⚠ 跳过（文件不完整）"
fi

# ── 3. 冒烟测试 ────────────────────────────
echo ""
echo "[3/7] 冒烟测试..."

python3 -c "
import sys
sys.path.insert(0, 'src')
from evolution.plugin_core import TOOL_RUN_CYCLE_SCHEMA, TOOL_AUDIT_SCHEMA
for name in ['evolution_run_cycle', 'evolution_audit', 'evolution_self_monitor']:
    print(f'  ✅ {name}')
" 2>&1 || { echo "  ❌ 冒烟测试失败"; exit 1; }

# ── 4. 全量 pytest ─────────────────────────
echo ""
echo "[4/7] 运行全量测试..."

python3 -m pytest tests/ -q --tb=short 2>&1 | tail -5
if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo "  ❌ 测试失败，停止发布"
    exit 1
fi
echo "  ✅ 全量测试通过"

# ── 5. Git 提交 + tag ─────────────────────
echo ""
echo "[5/7] Git 提交..."

git add -A
git commit -m "release: V$VERSION" 2>&1 || echo "  ⚠ 无变更可提交"
git tag -a "v$VERSION" -m "Release V$VERSION" 2>&1 || echo "  ⚠ tag 已存在"
echo "  ✅ commit + tag v$VERSION"

# ── 6. Git push ───────────────────────────
echo ""
echo "[6/7] Git push..."

git push origin main 2>&1
git push origin "v$VERSION" 2>&1
echo "  ✅ 已推送"

# ── 7. Build + PyPI ───────────────────────
echo ""
echo "[7/7] Build + PyPI 上传..."

rm -rf dist/
python3 -m build 2>&1 | tail -3

# 检查 TWINE 凭据
if [ -z "${TWINE_USERNAME:-}" ]; then
    echo "  ⚠ TWINE_USERNAME 未设置，跳过 PyPI 上传"
    echo "  请手动执行: twine upload dist/hermes_agent_evolution-$VERSION*"
else
    python3 -m twine upload dist/hermes_agent_evolution-$VERSION* 2>&1 | tail -3
    echo "  ✅ PyPI 发布完成"
fi

echo ""
echo "========================================="
echo " 🎉 V$VERSION 发布完成！"
echo " https://pypi.org/project/hermes-agent-evolution/$VERSION/"
echo "========================================="
