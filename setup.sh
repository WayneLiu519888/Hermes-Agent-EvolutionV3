#!/usr/bin/env bash
#
# HermesAgentEvolution 一键安装脚本
# 支持: pip install, 开发模式, 测试验证
#
# 使用方法:
#   bash setup.sh              # 交互式安装
#   bash setup.sh --dev        # 开发模式安装 (pip install -e .)
#   bash setup.sh --prod       # 生产模式安装
#   bash setup.sh --test       # 安装并运行测试
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_python() {
    if command -v python3 &>/dev/null; then
        PYTHON=python3
    elif command -v python &>/dev/null; then
        PYTHON=python
    else
        log_error "未找到 Python 3 (python3/python)。请先安装 Python >= 3.9"
        exit 1
    fi

    PY_VERSION=$($PYTHON --version 2>&1 | grep -oP '\d+\.\d+')
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

    if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
        log_error "需要 Python >= 3.9，当前版本: $($PYTHON --version 2>&1)"
        exit 1
    fi

    log_ok "Python: $($PYTHON --version 2>&1)"
}

install_dev() {
    log_info "安装开发模式 (pip install -e .) ..."
    cd "$PROJECT_DIR"
    $PYTHON -m pip install --upgrade pip -q
    $PYTHON -m pip install -e . -q
    log_ok "开发模式安装完成"
}

install_prod() {
    log_info "安装生产模式 (pip install .) ..."
    cd "$PROJECT_DIR"
    $PYTHON -m pip install --upgrade pip -q
    $PYTHON -m pip install . -q
    log_ok "生产模式安装完成"
}

install_dev_full() {
    log_info "安装开发模式（含dev依赖）..."
    cd "$PROJECT_DIR"
    $PYTHON -m pip install --upgrade pip -q
    $PYTHON -m pip install -e ".[dev]" -q
    log_ok "开发模式（含dev）安装完成"
}

run_tests() {
    log_info "运行测试..."
    cd "$PROJECT_DIR"
    if $PYTHON -m pytest tests/ -v --tb=short 2>/dev/null; then
        log_ok "所有测试通过"
    else
        log_warn "部分测试失败，请检查输出"
    fi
}

verify_import() {
    log_info "验证模块导入..."
    cd "$PROJECT_DIR"
    if $PYTHON -c "from evolution import __version__; print(f'evolution v{__version__} 导入成功')" 2>&1; then
        log_ok "模块导入验证通过"
    else
        log_error "模块导入失败，请检查安装"
        exit 1
    fi
}

print_usage() {
    cat <<EOF
${CYAN}HermesAgentEvolution 一键安装脚本${NC}

用法: bash setup.sh [选项]

选项:
  --dev        开发模式安装 (pip install -e .)
  --prod       生产模式安装 (pip install .)
  --dev-full   开发模式安装 + 测试工具
  --test       安装并运行测试
  --help       显示此帮助信息

无参数时进入交互式安装向导。

示例:
  bash setup.sh --dev       # 开发模式
  bash setup.sh --test      # 安装 + 测试
EOF
}

interactive_install() {
    echo ""
    echo "========================================"
    echo "  HermesAgentEvolution 安装向导"
    echo "========================================"
    echo ""

    PS3="请选择安装方式 (输入数字): "
    options=("开发模式 (pip install -e .)" "生产模式 (pip install .)" "安装并测试" "退出")
    select opt in "${options[@]}"; do
        case $opt in
            "开发模式 (pip install -e .)")
                install_dev
                verify_import
                break
                ;;
            "生产模式 (pip install .)")
                install_prod
                verify_import
                break
                ;;
            "安装并测试")
                install_dev_full
                verify_import
                run_tests
                break
                ;;
            "退出")
                log_info "安装已取消"
                exit 0
                ;;
            *)
                log_error "无效选项: $REPLY"
                ;;
        esac
    done

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  安装完成！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "  Python 包: ${CYAN}evolution${NC}"
    echo -e "  导入方式: ${CYAN}from evolution import ...${NC}"
    echo -e "  示例:     ${CYAN}from evolution.learning.observer import LearningObserver${NC}"
    echo ""

    # 询问是否运行测试
    read -r -p "是否运行测试验证安装？(y/N): " run_test
    if [[ "$run_test" =~ ^[Yy]$ ]]; then
        run_tests
    fi
}

# ====== 主入口 ======

echo ""
echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      HermesAgentEvolution 安装脚本     ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""

check_python

# 解析命令行参数
MODE=""
if [ $# -gt 0 ]; then
    case "$1" in
        --dev)
            MODE="dev"
            ;;
        --prod)
            MODE="prod"
            ;;
        --dev-full)
            MODE="dev-full"
            ;;
        --test)
            MODE="test"
            ;;
        --help|-h)
            print_usage
            exit 0
            ;;
        *)
            log_error "未知选项: $1"
            print_usage
            exit 1
            ;;
    esac
fi

case "$MODE" in
    dev)
        install_dev
        verify_import
        ;;
    prod)
        install_prod
        verify_import
        ;;
    dev-full)
        install_dev_full
        verify_import
        ;;
    test)
        install_dev_full
        verify_import
        run_tests
        ;;
    *)
        interactive_install
        ;;
esac

echo ""
log_ok "安装脚本执行完毕"
