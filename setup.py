#!/usr/bin/env python
"""
HermesAgentEvolution 安装脚本

支持:
  pip install -e .            # 开发模式安装
  pip install .               # 普通安装
  pip install .[dev]          # 包含开发依赖
  pip install .[full]         # 包含所有可选依赖
"""

import re
from setuptools import setup, find_packages

# 读取长描述
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# 读取 requirements.txt，过滤注释和空行，忽略标准库模块
def parse_requirements():
    requirements = []
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            # 跳过注释、空行、以及标注为Python内置的模块
            if not line or line.startswith("#") or "Python内置" in line or "Python标准库" in line:
                continue
            if line.startswith("-"):
                continue
            requirements.append(line)
    return requirements

install_requires = parse_requirements()

setup(
    name="hermes-agent-evolution",
    version="3.0.3",
    author="HermesAgentEvolution Team",
    author_email="contact@example.com",
    description="AI自我进化系统 V1/V2/V3 融合版 — 单体+微服务混合架构",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/WayneLiu519888/Hermes-Agent-EvolutionV3",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={
        "evolution": ["data/*.db", "config/*.json"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=install_requires,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
        "full": [
            "requests>=2.25.0",
            "numpy>=1.19.0",
            "scikit-learn>=0.24.0",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/HermesAgentEvolution/issues",
        "Source": "https://github.com/yourusername/HermesAgentEvolution",
        "Documentation": "https://github.com/yourusername/HermesAgentEvolution/wiki",
    },
)
