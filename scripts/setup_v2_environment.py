#!/usr/bin/env python3
"""
HermesAgentEvolution V2 - Phase 1 启动脚本
用于快速建立V2开发环境
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

def print_header(text):
    """打印标题"""
    print("\n" + "="*60)
    print(f" {text}")
    print("="*60)

def run_command(cmd, cwd=None):
    """运行命令并打印输出"""
    print(f"\n🚀 执行: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ 错误: {result.stderr}")
        return False
    print(f"✅ 成功: {result.stdout[:200]}...")
    return True

def check_requirements():
    """检查系统要求"""
    print_header("检查系统要求")
    
    requirements = [
        ("Python 3.10+", "python3 --version"),
        ("Git", "git --version"),
        ("Docker", "docker --version"),
        ("Docker Compose", "docker-compose --version"),
    ]
    
    all_ok = True
    for name, cmd in requirements:
        if run_command(cmd):
            print(f"✅ {name} 已安装")
        else:
            print(f"❌ {name} 未安装")
            all_ok = False
    
    return all_ok

def create_project_structure():
    """创建V2项目结构"""
    print_header("创建V2项目结构")
    
    # 基础目录结构
    directories = [
        "src/core/events",
        "src/core/config",
        "src/core/plugins",
        "src/core/monitoring",
        "src/evolution/learning",
        "src/evolution/memory",
        "src/evolution/tools",
        "plugins/feishu_notifier",
        "plugins/learning_observer",
        "tests/unit",
        "tests/integration",
        "tests/performance",
        "docs/architecture",
        "docs/api",
        "docs/plugins",
        "config",
        "docker",
        "scripts",
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ 创建目录: {directory}")
    
    return True

def create_requirements_file():
    """创建requirements.txt文件"""
    print_header("创建依赖文件")
    
    requirements = """# HermesAgentEvolution V2 - 依赖列表

## 核心依赖
python>=3.10
pydantic>=2.0
sqlalchemy>=2.0
redis>=4.0
structlog>=23.0

## 异步框架
asyncio
aiohttp>=3.9
aioredis>=2.0

## 事件系统
# (使用自定义实现)

## 监控和可观测性
prometheus-client>=0.17
opentelemetry-api>=1.20
opentelemetry-sdk>=1.20

## 开发工具
pytest>=7.4
pytest-asyncio>=0.21
pytest-cov>=4.1
black>=23.0
flake8>=6.0
mypy>=1.5
isort>=5.12

## 文档
sphinx>=7.0
sphinx-rtd-theme>=1.3

## 可选依赖
# numpy>=1.24  # 数值计算
# scikit-learn>=1.3  # 机器学习
# torch>=2.0  # 深度学习
"""
    
    with open("requirements.txt", "w") as f:
        f.write(requirements)
    
    print("✅ 创建 requirements.txt")
    return True

def create_gitignore():
    """创建.gitignore文件"""
    print_header("创建.gitignore文件")
    
    gitignore = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Database
*.db
*.sqlite
*.sqlite3

# Logs
*.log
logs/

# Environment variables
.env
.env.local

# Docker
docker-compose.override.yml

# Temporary files
*.tmp
*.temp

# Test coverage
.coverage
htmlcov/

# Documentation
docs/_build/

# OS
.DS_Store
Thumbs.db

# Backups
backup_*/
"""
    
    with open(".gitignore", "w") as f:
        f.write(gitignore)
    
    print("✅ 创建 .gitignore")
    return True

def create_docker_compose():
    """创建Docker Compose配置"""
    print_header("创建Docker Compose配置")
    
    docker_compose = """version: '3.8'

services:
  # 主应用
  hermes-app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - HERMES_ENV=development
      - HERMES_DATABASE__URL=postgresql://postgres:password@db/hermes
      - HERMES_EVENT_BUS__TYPE=redis
      - HERMES_EVENT_BUS__REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./:/app
      - ./data:/app/data
    command: python -m src.main

  # 数据库
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=hermes
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # Redis (缓存和事件总线)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  # 监控栈 (可选)
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./docker/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
"""
    
    os.makedirs("docker", exist_ok=True)
    with open("docker-compose.yml", "w") as f:
        f.write(docker_compose)
    
    print("✅ 创建 docker-compose.yml")
    return True

def create_basic_files():
    """创建基础文件"""
    print_header("创建基础文件")
    
    # 创建 __init__.py 文件
    init_files = [
        "src/__init__.py",
        "src/core/__init__.py",
        "src/core/events/__init__.py",
        "src/core/config/__init__.py",
        "src/core/plugins/__init__.py",
        "src/core/monitoring/__init__.py",
        "src/evolution/__init__.py",
        "src/evolution/learning/__init__.py",
        "src/evolution/memory/__init__.py",
        "src/evolution/tools/__init__.py",
    ]
    
    for file in init_files:
        with open(file, "w") as f:
            f.write('"""Module initialization"""\n')
        print(f"✅ 创建 {file}")
    
    # 创建README
    readme = """# HermesAgentEvolution V2

AI助手自我进化系统 - 现代化架构版本

## 项目状态
🚧 **开发中** - Phase 1: 基础架构重构

## 快速开始

### 使用Docker开发
```bash
# 启动开发环境
docker-compose up -d

# 查看日志
docker-compose logs -f hermes-app

# 停止环境
docker-compose down
```

### 本地开发
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\\Scripts\\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest tests/

# 启动应用
python -m src.main
```

## 项目结构
```
hermes_agent_evolution_v2/
├── src/                    # 源代码
│   ├── core/              # 核心框架
│   ├── evolution/         # 进化模块
│   └── main.py           # 应用入口
├── plugins/               # 插件目录
├── tests/                 # 测试
├── docs/                  # 文档
├── config/                # 配置文件
├── docker/                # Docker配置
└── scripts/               # 工具脚本
```

## 开发指南

### 代码规范
- 使用Black进行代码格式化
- 使用flake8进行代码检查
- 使用mypy进行类型检查
- 所有代码必须通过测试

### 提交规范
- 小步提交，频繁提交
- 提交信息清晰明确
- 必须有相关测试
- 必须通过代码审查

## 文档
- [架构设计](docs/architecture/ARCHITECTURE_V2.md)
- [API参考](docs/api/API_REFERENCE.md)
- [开发指南](docs/DEVELOPMENT_GUIDE.md)

## 联系方式
- 问题报告: GitHub Issues
- 讨论: GitHub Discussions
- 文档: 项目Wiki

---
*版本: V2.0 (开发中)*
"""
    
    with open("README.md", "w") as f:
        f.write(readme)
    
    print("✅ 创建 README.md")
    return True

def setup_git():
    """设置Git仓库"""
    print_header("设置Git仓库")
    
    if not os.path.exists(".git"):
        run_command("git init")
        run_command('git config user.email "dev@hermes-evolution.com"')
        run_command('git config user.name "Hermes Evolution Team"')
        print("✅ Git仓库初始化")
    else:
        print("⚠️ Git仓库已存在，跳过初始化")
    
    return True

def install_dependencies():
    """安装Python依赖"""
    print_header("安装Python依赖")
    
    # 创建虚拟环境
    if not os.path.exists("venv"):
        print("创建Python虚拟环境...")
        run_command("python3 -m venv venv")
    
    # 激活虚拟环境并安装依赖
    if sys.platform == "win32":
        activate_cmd = "venv\\Scripts\\activate"
        pip_cmd = "venv\\Scripts\\pip"
    else:
        activate_cmd = "source venv/bin/activate"
        pip_cmd = "venv/bin/pip"
    
    # 安装依赖
    print("安装依赖包...")
    run_command(f"{pip_cmd} install --upgrade pip")
    run_command(f"{pip_cmd} install -r requirements.txt")
    
    print("✅ 依赖安装完成")
    return True

def create_initial_commit():
    """创建初始提交"""
    print_header("创建初始提交")
    
    run_command("git add .")
    run_command('git commit -m "feat: 初始化HermesAgentEvolution V2项目骨架"')
    
    print("✅ 初始提交完成")
    return True

def print_next_steps():
    """打印下一步操作指南"""
    print_header("下一步操作")
    
    steps = """
🎉 V2项目骨架创建完成！接下来：

1. **开始Phase 1开发**
   ```
   # 切换到开发分支
   git checkout -b feature/phase1-architecture
   
   # 开始实现事件系统
   # 参考: docs/PHASE1_IMPLEMENTATION_GUIDE.md
   ```

2. **启动开发环境**
   ```
   # 使用Docker
   docker-compose up -d
   
   # 或使用本地环境
   source venv/bin/activate  # Linux/Mac
   python -m src.main
   ```

3. **开发工作流**
   ```
   # 运行测试
   pytest tests/
   
   # 代码格式化
   black src/ tests/
   
   # 代码检查
   flake8 src/ tests/
   mypy src/
   ```

4. **文档和计划**
   - 阅读架构设计: docs/ARCHITECTURE_V2.md
   - 查看实施计划: docs/IMPLEMENTATION_PLAN_V2.md
   - 遵循Phase 1指南: docs/PHASE1_IMPLEMENTATION_GUIDE.md

5. **团队协作**
   - 每日站会: 9:00 AM
   - 代码审查: GitHub Pull Requests
   - 问题跟踪: GitHub Issues

📞 如有问题，请查看文档或联系团队！
"""
    
    print(steps)

def main():
    """主函数"""
    print_header("HermesAgentEvolution V2 - Phase 1 环境搭建")
    print("开始创建V2开发环境...")
    
    # 记录开始时间
    start_time = datetime.now()
    
    # 检查当前目录
    current_dir = os.getcwd()
    print(f"当前目录: {current_dir}")
    
    # 确认操作
    response = input("\n⚠️  这将在当前目录创建V2项目结构。继续吗？ (y/N): ")
    if response.lower() != 'y':
        print("操作取消")
        return
    
    # 执行步骤
    steps = [
        ("检查系统要求", check_requirements),
        ("创建项目结构", create_project_structure),
        ("创建依赖文件", create_requirements_file),
        ("创建.gitignore", create_gitignore),
        ("创建Docker配置", create_docker_compose),
        ("创建基础文件", create_basic_files),
        ("设置Git仓库", setup_git),
        ("安装依赖", install_dependencies),
        ("创建初始提交", create_initial_commit),
    ]
    
    all_success = True
    for step_name, step_func in steps:
        try:
            if not step_func():
                print(f"❌ {step_name} 失败")
                all_success = False
                break
        except Exception as e:
            print(f"❌ {step_name} 异常: {e}")
            all_success = False
            break
    
    # 计算耗时
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    if all_success:
        print_header("环境搭建完成")
        print(f"✅ 所有步骤完成！耗时: {duration:.1f}秒")
        print_next_steps()
    else:
        print_header("环境搭建失败")
        print("❌ 部分步骤失败，请检查错误信息")
        print(f"耗时: {duration:.1f}秒")

if __name__ == "__main__":
    main()