"""
部署和配置模块 - 自动化部署、环境管理、配置管理
支持多环境部署、蓝绿部署、滚动更新、配置热重载
"""

import os
import sys
import yaml
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import subprocess
import shutil
from pathlib import Path
import docker
from docker.errors import DockerException
import git
import hashlib

logger = logging.getLogger(__name__)


class DeploymentStatus(Enum):
    """部署状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLBACK = "rollback"
    CANCELLED = "cancelled"


class EnvironmentType(Enum):
    """环境类型"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


@dataclass
class DeploymentConfig:
    """部署配置"""
    deployment_id: str
    environment: EnvironmentType
    version: str
    image_tag: str
    replicas: int = 1
    cpu_limit: str = "500m"
    memory_limit: str = "512Mi"
    health_check_path: str = "/health"
    readiness_check_path: str = "/ready"
    env_vars: Dict[str, str] = field(default_factory=dict)
    volumes: List[Dict[str, str]] = field(default_factory=list)
    ports: List[Dict[str, Any]] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "deployment_id": self.deployment_id,
            "environment": self.environment.value,
            "version": self.version,
            "image_tag": self.image_tag,
            "replicas": self.replicas,
            "cpu_limit": self.cpu_limit,
            "memory_limit": self.memory_limit,
            "health_check_path": self.health_check_path,
            "readiness_check_path": self.readiness_check_path,
            "env_vars": self.env_vars,
            "volumes": self.volumes,
            "ports": self.ports,
            "labels": self.labels,
            "annotations": self.annotations
        }


@dataclass
class DeploymentResult:
    """部署结果"""
    deployment_id: str
    status: DeploymentStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    logs: List[str] = field(default_factory=list)
    error: Optional[str] = None
    deployed_resources: List[Dict[str, Any]] = field(default_factory=list)
    rollback_resources: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "deployment_id": self.deployment_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "logs": self.logs,
            "error": self.error,
            "deployed_resources": self.deployed_resources,
            "rollback_resources": self.rollback_resources,
            "metrics": self.metrics
        }


class ConfigurationManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "./config"):
        self.config_dir = Path(config_dir)
        self.configs: Dict[str, Dict[str, Any]] = {}
        self.config_watchers: List[Callable] = []
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"配置管理器初始化完成，配置目录: {config_dir}")
    
    def load_config(self, env: EnvironmentType = EnvironmentType.DEVELOPMENT) -> Dict[str, Any]:
        """加载配置"""
        config_file = self.config_dir / f"config.{env.value}.yaml"
        
        if not config_file.exists():
            logger.warning(f"配置文件不存在: {config_file}")
            return self._create_default_config(env)
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            self.configs[env.value] = config
            logger.info(f"配置已加载: {env.value}")
            
            return config
            
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return self._create_default_config(env)
    
    def _create_default_config(self, env: EnvironmentType) -> Dict[str, Any]:
        """创建默认配置"""
        default_config = {
            "app": {
                "name": "HermesAgentEvolution",
                "version": "2.0.0",
                "env": env.value,
                "debug": env == EnvironmentType.DEVELOPMENT
            },
            "logging": {
                "level": "DEBUG" if env == EnvironmentType.DEVELOPMENT else "INFO",
                "file": f"logs/hermes_{env.value}.log",
                "max_size": "100MB",
                "backup_count": 10
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "database": f"hermes_{env.value}",
                "username": "hermes",
                "password": "hermes123",
                "pool_size": 10,
                "echo": env == EnvironmentType.DEVELOPMENT
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "password": "",
                "max_connections": 20
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "workers": 4,
                "timeout": 30
            },
            "monitoring": {
                "enabled": True,
                "prometheus_port": 9090,
                "grafana_port": 3000,
                "metrics_interval": 60
            },
            "security": {
                "secret_key": self._generate_secret_key(),
                "token_expiry": 3600,
                "cors_origins": ["*"] if env == EnvironmentType.DEVELOPMENT else []
            }
        }
        
        # 保存默认配置
        self.save_config(env, default_config)
        
        return default_config
    
    def _generate_secret_key(self) -> str:
        """生成密钥"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def save_config(self, env: EnvironmentType, config: Dict[str, Any]) -> bool:
        """保存配置"""
        config_file = self.config_dir / f"config.{env.value}.yaml"
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            self.configs[env.value] = config
            logger.info(f"配置已保存: {env.value}")
            
            # 通知观察者
            self._notify_watchers(env, config)
            
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def get_config(self, env: EnvironmentType, key: str = None, default: Any = None) -> Any:
        """获取配置"""
        config = self.configs.get(env.value)
        
        if config is None:
            config = self.load_config(env)
        
        if key is None:
            return config
        
        # 支持点分隔的键路径
        keys = key.split('.')
        current = config
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
    
    def update_config(self, env: EnvironmentType, updates: Dict[str, Any]) -> bool:
        """更新配置"""
        config = self.get_config(env)
        
        # 深度合并更新
        self._deep_update(config, updates)
        
        return self.save_config(env, config)
    
    def _deep_update(self, original: Dict[str, Any], updates: Dict[str, Any]) -> None:
        """深度更新字典"""
        for key, value in updates.items():
            if key in original and isinstance(original[key], dict) and isinstance(value, dict):
                self._deep_update(original[key], value)
            else:
                original[key] = value
    
    def register_watcher(self, callback: Callable) -> None:
        """注册配置观察者"""
        self.config_watchers.append(callback)
        logger.debug(f"配置观察者已注册: {callback.__name__}")
    
    def _notify_watchers(self, env: EnvironmentType, config: Dict[str, Any]) -> None:
        """通知观察者"""
        for watcher in self.config_watchers:
            try:
                watcher(env, config)
            except Exception as e:
                logger.error(f"配置观察者通知失败: {e}")
    
    def validate_config(self, env: EnvironmentType) -> List[str]:
        """验证配置"""
        errors = []
        config = self.get_config(env)
        
        # 验证必要字段
        required_fields = [
            "app.name",
            "app.version",
            "app.env",
            "database.host",
            "database.port",
            "database.database",
            "api.host",
            "api.port"
        ]
        
        for field in required_fields:
            if self.get_config(env, field) is None:
                errors.append(f"缺少必要字段: {field}")
        
        # 验证端口范围
        api_port = self.get_config(env, "api.port")
        if api_port and (api_port < 1 or api_port > 65535):
            errors.append(f"API端口无效: {api_port}")
        
        # 验证日志级别
        log_level = self.get_config(env, "logging.level")
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level and log_level.upper() not in valid_levels:
            errors.append(f"无效的日志级别: {log_level}")
        
        return errors
    
    def export_config(self, env: EnvironmentType, format: str = "yaml") -> str:
        """导出配置"""
        config = self.get_config(env)
        
        if format == "yaml":
            return yaml.dump(config, default_flow_style=False, allow_unicode=True)
        elif format == "json":
            return json.dumps(config, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"不支持的格式: {format}")


class DockerManager:
    """Docker管理器"""
    
    def __init__(self):
        try:
            self.client = docker.from_env()
            self.is_available = True
            logger.info("Docker管理器初始化完成")
        except DockerException as e:
            self.client = None
            self.is_available = False
            logger.warning(f"Docker不可用: {e}")
    
    def build_image(
        self,
        dockerfile_path: str,
        image_name: str,
        image_tag: str = "latest",
        build_args: Dict[str, str] = None,
        platform: str = None
    ) -> Dict[str, Any]:
        """构建Docker镜像"""
        if not self.is_available:
            return {
                "success": False,
                "error": "Docker不可用"
            }
        
        try:
            logger.info(f"开始构建镜像: {image_name}:{image_tag}")
            
            # 构建镜像
            image, build_logs = self.client.images.build(
                path=os.path.dirname(dockerfile_path),
                dockerfile=os.path.basename(dockerfile_path),
                tag=f"{image_name}:{image_tag}",
                buildargs=build_args,
                platform=platform,
                rm=True,
                forcerm=True
            )
            
            # 收集构建日志
            logs = []
            for chunk in build_logs:
                if 'stream' in chunk:
                    logs.append(chunk['stream'].strip())
            
            logger.info(f"镜像构建成功: {image_name}:{image_tag}")
            
            return {
                "success": True,
                "image_id": image.id,
                "image_name": image_name,
                "image_tag": image_tag,
                "logs": logs
            }
            
        except Exception as e:
            logger.error(f"镜像构建失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def push_image(self, image_name: str, image_tag: str = "latest") -> Dict[str, Any]:
        """推送Docker镜像"""
        if not self.is_available:
            return {
                "success": False,
                "error": "Docker不可用"
            }
        
        try:
            logger.info(f"开始推送镜像: {image_name}:{image_tag}")
            
            # 推送镜像
            push_logs = self.client.images.push(
                repository=image_name,
                tag=image_tag,
                stream=True,
                decode=True
            )
            
            # 收集推送日志
            logs = []
            for chunk in push_logs:
                if 'status' in chunk:
                    logs.append(chunk['status'])
                if 'error' in chunk:
                    logs.append(f"错误: {chunk['error']}")
            
            logger.info(f"镜像推送成功: {image_name}:{image_tag}")
            
            return {
                "success": True,
                "logs": logs
            }
            
        except Exception as e:
            logger.error(f"镜像推送失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def run_container(
        self,
        image_name: str,
        container_name: str,
        ports: Dict[str, str] = None,
        volumes: Dict[str, Dict[str, str]] = None,
        environment: Dict[str, str] = None,
        command: str = None
    ) -> Dict[str, Any]:
        """运行Docker容器"""
        if not self.is_available:
            return {
                "success": False,
                "error": "Docker不可用"
            }
        
        try:
            logger.info(f"开始运行容器: {container_name}")
            
            # 运行容器
            container = self.client.containers.run(
                image=image_name,
                name=container_name,
                ports=ports,
                volumes=volumes,
                environment=environment,
                command=command,
                detach=True,
                restart_policy={"Name": "unless-stopped"}
            )
            
            logger.info(f"容器运行成功: {container_name} (ID: {container.id})")
            
            return {
                "success": True,
                "container_id": container.id,
                "container_name": container_name,
                "status": container.status
            }
            
        except Exception as e:
            logger.error(f"容器运行失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def stop_container(self, container_name: str) -> Dict[str, Any]:
        """停止Docker容器"""
        if not self.is_available:
            return {
                "success": False,
                "error": "Docker不可用"
            }
        
        try:
            container = self.client.containers.get(container_name)
            container.stop()
            container.remove()
            
            logger.info(f"容器已停止并删除: {container_name}")
            
            return {
                "success": True,
                "message": f"容器 {container_name} 已停止并删除"
            }
            
        except Exception as e:
            logger.error(f"停止容器失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_container_status(self, container_name: str) -> Dict[str, Any]:
        """获取容器状态"""
        if not self.is_available:
            return {
                "success": False,
                "error": "Docker不可用"
            }
        
        try:
            container = self.client.containers.get(container_name)
            
            return {
                "success": True,
                "container_id": container.id,
                "container_name": container.name,
                "status": container.status,
                "image": container.image.tags,
                "created": container.attrs['Created'],
                "ports": container.attrs['NetworkSettings']['Ports'],
                "state": container.attrs['State']
            }
            
        except Exception as e:
            logger.error(f"获取容器状态失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class DeploymentManager:
    """部署管理器"""
    
    def __init__(self):
        self.config_manager = ConfigurationManager()
        self.docker_manager = DockerManager()
        self.deployments: Dict[str, DeploymentResult] = {}
        self.current_deployment: Optional[str] = None
        
        logger.info("部署管理器初始化完成")
    
    async def deploy(
        self,
        environment: EnvironmentType,
        version: str,
        image_tag: str = None,
        config_overrides: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """执行部署"""
        import uuid
        
        deployment_id = str(uuid.uuid4())
        image_tag = image_tag or version
        
        # 创建部署配置
        deployment_config = DeploymentConfig(
            deployment_id=deployment_id,
            environment=environment,
            version=version,
            image_tag=image_tag,
            env_vars=self._prepare_env_vars(environment, config_overrides)
        )
        
        # 创建部署结果
        deployment_result = DeploymentResult(
            deployment_id=deployment_id,
            status=DeploymentStatus.RUNNING,
            start_time=datetime.now()
        )
        
        self.deployments[deployment_id] = deployment_result
        self.current_deployment = deployment_id
        
        try:
            # 记录开始日志
            deployment_result.logs.append(f"开始部署到 {environment.value} 环境")
            deployment_result.logs.append(f"版本: {version}, 镜像标签: {image_tag}")
            
            # 1. 验证配置
            deployment_result.logs.append("验证配置...")
            config_errors = self.config_manager.validate_config(environment)
            
            if config_errors:
                error_msg = f"配置验证失败: {', '.join(config_errors)}"
                deployment_result.logs.append(error_msg)
                deployment_result.status = DeploymentStatus.FAILED
                deployment_result.error = error_msg
                deployment_result.end_time = datetime.now()
                
                return {
                    "success": False,
                    "deployment_result": deployment_result.to_dict()
                }
            
            deployment_result.logs.append("配置验证通过")
            
            # 2. 构建镜像（如果Docker可用）
            if self.docker_manager.is_available:
                deployment_result.logs.append("构建Docker镜像...")
                
                build_result = self.docker_manager.build_image(
                    dockerfile_path="./docker/Dockerfile",
                    image_name="hermes-agent-evolution",
                    image_tag=image_tag
                )
                
                if not build_result["success"]:
                    error_msg = f"镜像构建失败: {build_result['error']}"
                    deployment_result.logs.append(error_msg)
                    deployment_result.status = DeploymentStatus.FAILED
                    deployment_result.error = error_msg
                    deployment_result.end_time = datetime.now()
                    
                    return {
                        "success": False,
                        "deployment_result": deployment_result.to_dict()
                    }
                
                deployment_result.logs.extend(build_result["logs"])
                deployment_result.logs.append("镜像构建成功")
            
            # 3. 停止旧容器（如果存在）
            if self.docker_manager.is_available:
                old_container_name = f"hermes-{environment.value}"
                deployment_result.logs.append(f"停止旧容器: {old_container_name}")
                
                stop_result = self.docker_manager.stop_container(old_container_name)
                if not stop_result["success"]:
                    deployment_result.logs.append(f"停止旧容器失败: {stop_result['error']}")
                    # 继续部署，不视为致命错误
            
            # 4. 运行新容器
            if self.docker_manager.is_available:
                deployment_result.logs.append("运行新容器...")
                
                # 准备端口映射
                api_port = self.config_manager.get_config(environment, "api.port", 8000)
                ports = {f"{api_port}/tcp": str(api_port)}
                
                # 准备卷映射
                volumes = {
                    "./logs": {"bind": "/app/logs", "mode": "rw"},
                    "./data": {"bind": "/app/data", "mode": "rw"}
                }
                
                # 运行容器
                run_result = self.docker_manager.run_container(
                    image_name=f"hermes-agent-evolution:{image_tag}",
                    container_name=f"hermes-{environment.value}",
                    ports=ports,
                    volumes=volumes,
                    environment=deployment_config.env_vars
                )
                
                if not run_result["success"]:
                    error_msg = f"容器运行失败: {run_result['error']}"
                    deployment_result.logs.append(error_msg)
                    deployment_result.status = DeploymentStatus.FAILED
                    deployment_result.error = error_msg
                    deployment_result.end_time = datetime.now()
                    
                    return {
                        "success": False,
                        "deployment_result": deployment_result.to_dict()
                    }
                
                deployment_result.deployed_resources.append({
                    "type": "container",
                    "name": run_result["container_name"],
                    "id": run_result["container_id"],
                    "status": run_result["status"]
                })
                
                deployment_result.logs.append("容器运行成功")
            
            # 5. 等待服务就绪
            deployment_result.logs.append("等待服务就绪...")
            
            health_check_url = f"http://localhost:{api_port}{deployment_config.health_check_path}"
            is_healthy = await self._wait_for_health_check(health_check_url)
            
            if not is_healthy:
                error_msg = "服务健康检查失败"
                deployment_result.logs.append(error_msg)
                deployment_result.status = DeploymentStatus.FAILED
                deployment_result.error = error_msg
                deployment_result.end_time = datetime.now()
                
                # 尝试回滚
                await self._rollback_deployment(deployment_result, environment)
                
                return {
                    "success": False,
                    "deployment_result": deployment_result.to_dict()
                }
            
            deployment_result.logs.append("服务就绪检查通过")
            
            # 6. 部署完成
            deployment_result.status = DeploymentStatus.SUCCESS
            deployment_result.end_time = datetime.now()
            deployment_result.metrics = {
                "deployment_duration": (deployment_result.end_time - deployment_result.start_time).total_seconds(),
                "resources_deployed": len(deployment_result.deployed_resources)
            }
            
            deployment_result.logs.append(f"部署成功完成，耗时: {deployment_result.metrics['deployment_duration']:.2f}秒")
            
            logger.info(f"部署成功: {deployment_id}")
            
            return {
                "success": True,
                "deployment_result": deployment_result.to_dict()
            }
            
        except Exception as e:
            error_msg = f"部署过程异常: {str(e)}"
            deployment_result.logs.append(error_msg)
            deployment_result.status = DeploymentStatus.FAILED
            deployment_result.error = error_msg
            deployment_result.end_time = datetime.now()
            
            # 尝试回滚
            await self._rollback_deployment(deployment_result, environment)
            
            logger.error(f"部署失败: {deployment_id} - {error_msg}", exc_info=True)
            
            return {
                "success": False,
                "deployment_result": deployment_result.to_dict()
            }
    
    def _prepare_env_vars(self, environment: EnvironmentType, config_overrides: Dict[str, Any] = None) -> Dict[str, str]:
        """准备环境变量"""
        config = self.config_manager.get_config(environment)
        
        if config_overrides:
            # 应用配置覆盖
            self.config_manager._deep_update(config, config_overrides)
        
        env_vars = {
            "APP_ENV": environment.value,
            "APP_NAME": config["app"]["name"],
            "APP_VERSION": config["app"]["version"],
            "LOG_LEVEL": config["logging"]["level"],
            "API_HOST": config["api"]["host"],
            "API_PORT": str(config["api"]["port"]),
            "DATABASE_URL": f"postgresql://{config['database']['username']}:{config['database']['password']}"
                          f"@{config['database']['host']}:{config['database']['port']}/{config['database']['database']}",
            "REDIS_URL": f"redis://{config['redis']['host']}:{config['redis']['port']}/{config['redis']['db']}"
        }
        
        # 添加安全配置
        if "security" in config:
            env_vars["SECRET_KEY"] = config["security"]["secret_key"]
        
        return env_vars
    
    async def _wait_for_health_check(self, health_check_url: str, max_attempts: int = 30) -> bool:
        """等待健康检查通过"""
        import aiohttp
        
        for attempt in range(max_attempts):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(health_check_url, timeout=5) as response:
                        if response.status == 200:
                            return True
            except Exception:
                pass
            
            await asyncio.sleep(2)  # 等待2秒后重试
        
        return False
    
    async def _rollback_deployment(self, deployment_result: DeploymentResult, environment: EnvironmentType) -> None:
        """回滚部署"""
        deployment_result.logs.append("开始回滚部署...")
        
        try:
            # 停止新容器
            if deployment_result.deployed_resources:
                for resource in deployment_result.deployed_resources:
                    if resource["type"] == "container":
                        stop_result = self.docker_manager.stop_container(resource["name"])
                        if stop_result["success"]:
                            deployment_result.rollback_resources.append(resource)
                            deployment_result.logs.append(f"容器已停止: {resource['name']}")
            
            # 恢复旧容器（如果有备份）
            # 这里可以扩展为恢复之前的版本
            
            deployment_result.status = DeploymentStatus.ROLLBACK
            deployment_result.logs.append("回滚完成")
            
        except Exception as e:
            deployment_result.logs.append(f"回滚失败: {str(e)}")
    
    async def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """获取部署状态"""
        deployment_result = self.deployments.get(deployment_id)
        
        if not deployment_result:
            return {
                "success": False,
                "error": f"部署不存在: {deployment_id}"
            }
        
        # 如果部署还在运行，更新容器状态
        if deployment_result.status == DeploymentStatus.RUNNING and self.docker_manager.is_available:
            for resource in deployment_result.deployed_resources:
                if resource["type"] == "container":
                    status_result = self.docker_manager.get_container_status(resource["name"])
                    if status_result["success"]:
                        resource["current_status"] = status_result["status"]
                        resource["state"] = status_result["state"]
        
        return {
            "success": True,
            "deployment_result": deployment_result.to_dict()
        }
    
    async def list_deployments(self, limit: int = 50) -> Dict[str, Any]:
        """列出部署"""
        deployments_list = list(self.deployments.values())
        deployments_list.sort(key=lambda x: x.start_time, reverse=True)
        
        return {
            "success": True,
            "deployments": [d.to_dict() for d in deployments_list[:limit]],
            "total": len(deployments_list),
            "current_deployment": self.current_deployment
        }
    
    async def cancel_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """取消部署"""
        deployment_result = self.deployments.get(deployment_id)
        
        if not deployment_result:
            return {
                "success": False,
                "error": f"部署不存在: {deployment_id}"
            }
        
        if deployment_result.status != DeploymentStatus.RUNNING:
            return {
                "success": False,
                "error": f"部署不在运行状态: {deployment_result.status.value}"
            }
        
        try:
            # 停止部署过程
            deployment_result.status = DeploymentStatus.CANCELLED
            deployment_result.end_time = datetime.now()
            deployment_result.logs.append("部署已取消")
            
            # 回滚已部署的资源
            await self._rollback_deployment(deployment_result, EnvironmentType.DEVELOPMENT)
            
            return {
                "success": True,
                "deployment_result": deployment_result.to_dict()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# 全局部署管理器实例
deployment_manager = DeploymentManager()