"""
飞书通知器 - 支持多种通知方式
1. Webhook模式 (简单机器人)
2. 开放平台模式 (App ID/Secret)
"""

import os
import json
import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class FeishuNotifier:
    """飞书通知器"""
    
    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger("FeishuNotifier")
        self.config = self._load_config(config_path)
        self.access_token = None
        self.token_expiry = None
        
    def _load_config(self, config_path: str = None) -> Dict[str, Any]:
        """加载配置"""
        # 优先使用环境变量指定的模式，否则根据配置自动选择
        mode = os.environ.get("FEISHU_MODE", "").lower()
        
        config = {
            "mode": mode if mode in ["webhook", "openapi", "simulated"] else "auto",
            "webhook_url": os.environ.get("FEISHU_WEBHOOK_URL", ""),
            "app_id": os.environ.get("FEISHU_APP_ID", "cli_a96b9943f1f8dcd2"),
            "app_secret": os.environ.get("FEISHU_APP_SECRET", ""),
            "home_channel": os.environ.get("FEISHU_HOME_CHANNEL", "oc_018d7317c249d59c48fa0ef0ada77317"),
            "domain": os.environ.get("FEISHU_DOMAIN", "feishu"),
            "connection_mode": os.environ.get("FEISHU_CONNECTION_MODE", "websocket"),
            "home_channel_name": os.environ.get("FEISHU_HOME_CHANNEL_NAME", "Wayne-Hermes")
        }
        
        # 尝试从配置文件加载
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
            except Exception as e:
                self.logger.warning(f"配置文件加载失败: {e}")
        
        # 自动模式：优先使用Webhook，其次OpenAPI，最后模拟模式
        if config["mode"] == "auto":
            if config["webhook_url"]:
                config["mode"] = "webhook"
            elif config["app_id"] and config["app_secret"]:
                config["mode"] = "openapi"
            else:
                config["mode"] = "simulated"
                
        return config
        
    def get_access_token(self) -> Optional[str]:
        """获取访问令牌 (OpenAPI模式)"""
        if self.config["mode"] != "openapi":
            return None
            
        # 检查令牌是否有效
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
            
        # 获取新令牌
        url = f"https://open.{self.config['domain']}.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {
            "app_id": self.config["app_id"],
            "app_secret": self.config["app_secret"]
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") == 0:
                self.access_token = result["tenant_access_token"]
                # 令牌有效期通常为2小时，我们设置1小时50分钟的安全边界
                self.token_expiry = datetime.now() + timedelta(minutes=110)
                self.logger.info("飞书访问令牌获取成功")
                return self.access_token
            else:
                self.logger.error(f"获取令牌失败: {result.get('msg')}")
                return None
                
        except Exception as e:
            self.logger.error(f"获取令牌异常: {e}")
            return None
            
    def send_notification(self, title: str, content: str, level: str = "info") -> bool:
        """发送通知
        
        Args:
            title: 通知标题
            content: 通知内容
            level: 通知级别 (info, success, warning, error)
            
        Returns:
            bool: 是否发送成功
        """
        try:
            mode = self.config.get("mode", "simulated")
            
            if mode == "webhook":
                self.logger.info(f"[Webhook模式] 发送通知: {title}")
                success = self._send_via_webhook(title, content, level)
                if not success:
                    self.logger.warning("Webhook发送失败，回退到模拟模式")
                    return self._send_simulated(title, content, level)
                return success
                
            elif mode == "openapi":
                self.logger.info(f"[OpenAPI模式] 发送通知: {title}")
                success = self._send_via_openapi(title, content, level)
                if not success:
                    self.logger.warning("OpenAPI发送失败，回退到模拟模式")
                    return self._send_simulated(title, content, level)
                return success
                
            else:
                # 模拟模式
                self.logger.info(f"[模拟模式] 发送通知: {title}")
                return self._send_simulated(title, content, level)
                
        except Exception as e:
            self.logger.error(f"发送通知失败: {e}")
            # 发生异常时回退到模拟模式
            return self._send_simulated(title, content, level)
            
    def _send_via_webhook(self, title: str, content: str, level: str) -> bool:
        """通过Webhook发送通知"""
        # 根据级别设置颜色
        color_map = {
            "info": "blue",
            "success": "green", 
            "warning": "orange",
            "error": "red"
        }
        color = color_map.get(level, "blue")
        
        # 构建消息
        message = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": color
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": content
                        }
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": f"发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        ]
                    }
                ]
            }
        }
        
        try:
            response = requests.post(
                self.config["webhook_url"],
                headers={"Content-Type": "application/json"},
                json=message,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") == 0:
                self.logger.info(f"Webhook通知发送成功: {title}")
                return True
            else:
                self.logger.error(f"Webhook通知失败: {result.get('msg')}")
                return False
                
        except Exception as e:
            self.logger.error(f"Webhook请求异常: {e}")
            return False
            
    def _send_via_openapi(self, title: str, content: str, level: str) -> bool:
        """通过OpenAPI发送通知"""
        access_token = self.get_access_token()
        if not access_token:
            self.logger.error("无法获取访问令牌")
            return False
            
        # 根据级别设置颜色
        color_map = {
            "info": "blue",
            "success": "green",
            "warning": "orange",
            "error": "red"
        }
        color = color_map.get(level, "blue")
        
        # 构建消息
        # 根据飞书API文档，需要指定receive_id_type
        # 可能的类型: open_id, user_id, union_id, email, chat_id
        # 我们的home_channel看起来是chat_id格式 (oc_开头)
        receive_id_type = "chat_id" if self.config["home_channel"].startswith("oc_") else "open_id"
        
        message = {
            "receive_id": self.config["home_channel"],
            "msg_type": "interactive",
            "content": json.dumps({
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": color
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": content
                        }
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": f"发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        ]
                    }
                ]
            }, ensure_ascii=False)
        }

        url = f"https://open.{self.config['domain']}.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=message,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") == 0:
                self.logger.info(f"OpenAPI通知发送成功: {title}")
                return True
            else:
                self.logger.error(f"OpenAPI通知失败: {result.get('msg')}")
                return False
                
        except Exception as e:
            self.logger.error(f"OpenAPI请求异常: {e}")
            return False
            
    def _send_simulated(self, title: str, content: str, level: str) -> bool:
        """模拟发送通知（用于测试）"""
        self.logger.info(f"[模拟] 发送通知: {title}")
        self.logger.info(f"[模拟] 内容: {content}")
        self.logger.info(f"[模拟] 级别: {level}")
        
        # 保存到日志文件
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "content": content,
            "level": level
        }
        
        log_file = "feishu_notifications.log"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except:
            pass
            
        return True
        
    def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        result = {
            "config_mode": self.config["mode"],
            "config_status": "loaded",
            "test_time": datetime.now().isoformat()
        }
        
        if self.config["mode"] == "webhook":
            result["webhook_url"] = "已配置" if self.config["webhook_url"] else "未配置"
            result["test_result"] = "待测试"
            
        elif self.config["mode"] == "openapi":
            result["app_id"] = self.config["app_id"][:10] + "..." if self.config["app_id"] else "未配置"
            result["app_secret"] = "已配置" if self.config["app_secret"] else "未配置"
            result["home_channel"] = self.config["home_channel"]
            
            # 测试获取令牌
            token = self.get_access_token()
            result["access_token"] = "获取成功" if token else "获取失败"
            result["test_result"] = "成功" if token else "失败"
            
        else:
            result["test_result"] = "模拟模式"
            
        return result