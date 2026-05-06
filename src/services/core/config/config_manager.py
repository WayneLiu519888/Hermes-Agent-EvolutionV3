"""
配置管理系统 - 支持多环境配置、热重载、配置验证
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from pathlib import Path
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfigSource(Enum):
    """配置来源"""
    ENV = "env"          # 环境变量
    FILE = "file"        # 配置文件
    DATABASE = "db"      # 数据库
    API = "api"          # API
    DEFAULT = "default"  # 默认值


class ConfigType(Enum):
    """配置类型"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    SECRET = "secret"    # 敏感信息


@dataclass
class ConfigItem:
    """配置项"""
    key: str
    value: Any
    config_type: ConfigType
    description: str = ""
    source: ConfigSource = ConfigSource.DEFAULT
    required: bool = False
    validation_rules: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> bool:
        """验证配置值"""
        try:
            # 类型验证
            if self.config_type == ConfigType.STRING:
                if not isinstance(self.value, str):
                    return False
            elif self.config_type == ConfigType.INTEGER:
                if not isinstance(self.value, int):
                    return False
            elif self.config_type == ConfigType.FLOAT:
                if not isinstance(self.value, (int, float)):
                    return False
            elif self.config_type == ConfigType.BOOLEAN:
                if not isinstance(self.value, bool):
                    return False
            elif self.config_type == ConfigType.LIST:
                if not isinstance(self.value, list):
                    return False
            elif self.config_type == ConfigType.DICT:
                if not isinstance(self.value, dict):
                    return False
            
            # 自定义验证规则
            for rule in self.validation_rules:
                if not self._apply_validation_rule(rule):
                    return False
            
            return True
        except Exception:
            return False
    
    def _apply_validation_rule(self, rule: str) -> bool:
        """应用验证规则"""
        if rule.startswith("min:"):
            try:
                min_val = float(rule[4:])
                return float(self.value) >= min_val
            except:
                return False
        elif rule.startswith("max:"):
            try:
                max_val = float(rule[4:])
                return float(self.value) <= max_val
            except:
                return False
        elif rule.startswith("len_min:"):
            try:
                min_len = int(rule[8:])
                return len(str(self.value)) >= min_len
            except:
                return False
        elif rule.startswith("len_max:"):
            try:
                max_len = int(rule[8:])
                return len(str(self.value)) <= max_len
            except:
                return False
        elif rule == "not_empty":
            return bool(self.value)
        elif rule.startswith("regex:"):
            import re
            pattern = rule[6:]
            return bool(re.match(pattern, str(self.value)))
        
        return True


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "config", env: str = None):
        self.config_dir = Path(config_dir)
        self.env = env or os.getenv("APP_ENV", "development")
        self.configs: Dict[str, ConfigItem] = {}
        self._lock = asyncio.Lock()
        self._watchers: List[Callable] = []
        self._config_hash: str = ""
        
        # 创建配置目录
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self._load_configs()
    
    def _load_configs(self) -> None:
        """加载配置"""
        # 加载默认配置
        self._load_default_configs()
        
        # 加载环境特定配置
        env_config_file = self.config_dir / f"config.{self.env}.yaml"
        if env_config_file.exists():
            self._load_config_file(env_config_file, ConfigSource.FILE)
        
        # 加载通用配置文件
        common_config_file = self.config_dir / "config.yaml"
        if common_config_file.exists():
            self._load_config_file(common_config_file, ConfigSource.FILE)
        
        # 加载环境变量
        self._load_env_vars()
        
        # 计算配置哈希
        self._update_config_hash()
    
    def _load_default_configs(self) -> None:
        """加载默认配置"""
        default_configs = {
            "app.name": ConfigItem(
                key="app.name",
                value="HermesAgentEvolution",
                config_type=ConfigType.STRING,
                description="应用名称",
                source=ConfigSource.DEFAULT
            ),
            "app.version": ConfigItem(
                key="app.version",
                value="2.0.0",
                config_type=ConfigType.STRING,
                description="应用版本",
                source=ConfigSource.DEFAULT
            ),
            "app.env": ConfigItem(
                key="app.env",
                value=self.env,
                config_type=ConfigType.STRING,
                description="运行环境",
                source=ConfigSource.DEFAULT
            ),
            "app.debug": ConfigItem(
                key="app.debug",
                value=self.env == "development",
                config_type=ConfigType.BOOLEAN,
                description="调试模式",
                source=ConfigSource.DEFAULT
            ),
            "logging.level": ConfigItem(
                key="logging.level",
                value="INFO" if self.env == "production" else "DEBUG",
                config_type=ConfigType.STRING,
                description="日志级别",
                source=ConfigSource.DEFAULT
            ),
            "event_bus.max_history": ConfigItem(
                key="event_bus.max_history",
                value=1000,
                config_type=ConfigType.INTEGER,
                description="事件总线最大历史记录数",
                source=ConfigSource.DEFAULT,
                validation_rules=["min:100", "max:10000"]
            ),
            "service_manager.heartbeat_interval": ConfigItem(
                key="service_manager.heartbeat_interval",
                value=30,
                config_type=ConfigType.INTEGER,
                description="服务心跳间隔(秒)",
                source=ConfigSource.DEFAULT,
                validation_rules=["min:5", "max:300"]
            ),
            "database.url": ConfigItem(
                key="database.url",
                value="sqlite:///data/hermes.db",
                config_type=ConfigType.STRING,
                description="数据库连接URL",
                source=ConfigSource.DEFAULT
            ),
            "redis.url": ConfigItem(
                key="redis.url",
                value="redis://localhost:6379/0",
                config_type=ConfigType.STRING,
                description="Redis连接URL",
                source=ConfigSource.DEFAULT
            )
        }
        
        for key, config_item in default_configs.items():
            self.configs[key] = config_item
    
    def _load_config_file(self, config_file: Path, source: ConfigSource) -> None:
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.suffix in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                elif config_file.suffix == '.json':
                    config_data = json.load(f)
                else:
                    logger.warning(f"不支持的配置文件格式: {config_file}")
                    return
            
            self._update_configs_from_dict(config_data, source)
            logger.info(f"配置文件加载成功: {config_file}")
            
        except Exception as e:
            logger.error(f"配置文件加载失败: {config_file}, 错误: {e}")
    
    def _load_env_vars(self) -> None:
        """加载环境变量"""
        env_prefix = "HERMES_"
        
        for env_key, env_value in os.environ.items():
            if env_key.startswith(env_prefix):
                # 转换环境变量名: HERMES_DATABASE_URL -> database.url
                config_key = env_key[len(env_prefix):].lower().replace('_', '.')
                
                # 尝试解析值
                parsed_value = self._parse_env_value(env_value)
                
                # 创建或更新配置项
                if config_key in self.configs:
                    self.configs[config_key].value = parsed_value
                    self.configs[config_key].source = ConfigSource.ENV
                    self.configs[config_key].last_updated = datetime.now()
                else:
                    # 推断类型
                    config_type = self._infer_type(parsed_value)
                    self.configs[config_key] = ConfigItem(
                        key=config_key,
                        value=parsed_value,
                        config_type=config_type,
                        source=ConfigSource.ENV,
                        description=f"环境变量: {env_key}"
                    )
    
    def _parse_env_value(self, value: str) -> Any:
        """解析环境变量值"""
        # 尝试解析为JSON
        try:
            return json.loads(value)
        except:
            pass
        
        # 尝试解析为布尔值
        if value.lower() in ['true', 'yes', '1']:
            return True
        elif value.lower() in ['false', 'no', '0']:
            return False
        
        # 尝试解析为数字
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except:
            pass
        
        # 返回字符串
        return value
    
    def _infer_type(self, value: Any) -> ConfigType:
        """推断类型"""
        if isinstance(value, str):
            return ConfigType.STRING
        elif isinstance(value, bool):
            return ConfigType.BOOLEAN
        elif isinstance(value, int):
            return ConfigType.INTEGER
        elif isinstance(value, float):
            return ConfigType.FLOAT
        elif isinstance(value, list):
            return ConfigType.LIST
        elif isinstance(value, dict):
            return ConfigType.DICT
        else:
            return ConfigType.STRING
    
    def _update_configs_from_dict(self, config_dict: Dict, source: ConfigSource) -> None:
        """从字典更新配置"""
        def _update_nested(key_prefix: str, data: Dict):
            for key, value in data.items():
                full_key = f"{key_prefix}.{key}" if key_prefix else key
                
                if isinstance(value, dict):
                    _update_nested(full_key, value)
                else:
                    if full_key in self.configs:
                        self.configs[full_key].value = value
                        self.configs[full_key].source = source
                        self.configs[full_key].last_updated = datetime.now()
                    else:
                        config_type = self._infer_type(value)
                        self.configs[full_key] = ConfigItem(
                            key=full_key,
                            value=value,
                            config_type=config_type,
                            source=source
                        )
        
        _update_nested("", config_dict)
    
    def _update_config_hash(self) -> None:
        """更新配置哈希"""
        config_str = json.dumps(
            {k: v.value for k, v in sorted(self.configs.items())},
            sort_keys=True
        )
        self._config_hash = hashlib.md5(config_str.encode()).hexdigest()
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        config_item = self.configs.get(key)
        if config_item:
            return config_item.value
        return default
    
    def get_item(self, key: str) -> Optional[ConfigItem]:
        """获取配置项"""
        return self.configs.get(key)
    
    def set(self, key: str, value: Any, config_type: ConfigType = None) -> bool:
        """设置配置值"""
        if key in self.configs:
            config_item = self.configs[key]
            config_item.value = value
            config_item.source = ConfigSource.API
            config_item.last_updated = datetime.now()
            
            if config_type:
                config_item.config_type = config_type
            
            # 验证
            if not config_item.validate():
                logger.warning(f"配置验证失败: {key}")
                return False
        else:
            if config_type is None:
                config_type = self._infer_type(value)
            
            config_item = ConfigItem(
                key=key,
                value=value,
                config_type=config_type,
                source=ConfigSource.API
            )
            
            if not config_item.validate():
                logger.warning(f"配置验证失败: {key}")
                return False
            
            self.configs[key] = config_item
        
        self._update_config_hash()
        self._notify_watchers()
        return True
    
    def delete(self, key: str) -> bool:
        """删除配置"""
        if key in self.configs:
            del self.configs[key]
            self._update_config_hash()
            self._notify_watchers()
            return True
        return False
    
    def validate_all(self) -> Dict[str, List[str]]:
        """验证所有配置"""
        errors = {}
        
        for key, config_item in self.configs.items():
            if not config_item.validate():
                errors[key] = ["配置验证失败"]
            
            if config_item.required and config_item.value is None:
                if key not in errors:
                    errors[key] = []
                errors[key].append("必填配置项为空")
        
        return errors
    
    def subscribe(self, callback: Callable) -> None:
        """订阅配置变更"""
        if callback not in self._watchers:
            self._watchers.append(callback)
    
    def unsubscribe(self, callback: Callable) -> None:
        """取消订阅"""
        if callback in self._watchers:
            self._watchers.remove(callback)
    
    def _notify_watchers(self) -> None:
        """通知观察者"""
        for callback in self._watchers:
            try:
                callback(self._config_hash)
            except Exception as e:
                logger.error(f"配置变更通知失败: {e}")
    
    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        """保存配置到文件"""
        try:
            if file_path is None:
                file_path = self.config_dir / f"config.{self.env}.yaml"
            
            config_dict = {}
            for key, config_item in self.configs.items():
                if config_item.source != ConfigSource.ENV:  # 不保存环境变量
                    # 构建嵌套字典
                    keys = key.split('.')
                    current = config_dict
                    for k in keys[:-1]:
                        if k not in current:
                            current[k] = {}
                        current = current[k]
                    current[keys[-1]] = config_item.value
            
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"配置已保存到文件: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"配置保存失败: {e}")
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return {k: v.value for k, v in self.configs.items()}
    
    def get_config_hash(self) -> str:
        """获取配置哈希"""
        return self._config_hash


# 全局配置管理器实例
config_manager = ConfigManager()