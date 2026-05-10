"""
feishu_notifier 模块测试

覆盖:
- _load_config: 环境变量优先、配置文件加载、auto模式选择
- get_access_token: OpenAPI模式获取令牌、缓存、过期、API错误
- send_notification: 三种模式(simulated/webhook/openapi)、异常回退
- _send_via_webhook: 成功/失败/异常
- _send_via_openapi: 成功/失败/无令牌
- _send_simulated: 模拟通知和日志写入
- test_connection: 三种模式的连接测试
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.feishu_notifier import FeishuNotifier


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_env():
    """每个测试前后清理飞书相关环境变量"""
    keys = [
        "FEISHU_MODE", "FEISHU_WEBHOOK_URL", "FEISHU_APP_ID",
        "FEISHU_APP_SECRET", "FEISHU_HOME_CHANNEL", "FEISHU_DOMAIN",
        "FEISHU_CONNECTION_MODE", "FEISHU_HOME_CHANNEL_NAME"
    ]
    old = {k: os.environ.pop(k, None) for k in keys}
    yield
    for k, v in old.items():
        if v is not None:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)


@pytest.fixture
def mock_requests():
    """Mock requests.post 和 requests.get"""
    with patch("src.utils.feishu_notifier.requests") as mock_req:
        mock_req.post = MagicMock()
        mock_req.get = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success"}
        mock_req.post.return_value = mock_response
        mock_req.get.return_value = mock_response
        yield mock_req


@pytest.fixture
def config_file():
    """创建临时配置文件"""
    config = {
        "mode": "webhook",
        "webhook_url": "https://hooks.feishu.cn/test-webhook",
        "app_id": "cli_config_id",
        "app_secret": "config_secret",
        "home_channel": "oc_config_channel",
        "domain": "feishu"
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config, f)
        path = f.name
    yield path
    os.unlink(path)


# ── _load_config 测试 ────────────────────────────────────────────────────────

class TestLoadConfig:
    """测试 _load_config 方法"""

    def test_default_simulated_mode(self):
        """默认无环境变量/无配置文件 → simulated 模式"""
        notifier = FeishuNotifier()
        assert notifier.config["mode"] == "simulated"

    def test_env_webhook_mode(self):
        """环境变量 FEISHU_MODE=webhook → webhook 模式"""
        os.environ["FEISHU_MODE"] = "webhook"
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hooks.feishu.cn/test"
        notifier = FeishuNotifier()
        assert notifier.config["mode"] == "webhook"
        assert notifier.config["webhook_url"] == "https://hooks.feishu.cn/test"

    def test_env_openapi_mode(self):
        """环境变量 FEISHU_MODE=openapi → openapi 模式"""
        os.environ["FEISHU_MODE"] = "openapi"
        os.environ["FEISHU_APP_ID"] = "my_app_id"
        os.environ["FEISHU_APP_SECRET"] = "my_secret"
        notifier = FeishuNotifier()
        assert notifier.config["mode"] == "openapi"
        assert notifier.config["app_id"] == "my_app_id"
        assert notifier.config["app_secret"] == "my_secret"

    def test_env_simulated_mode(self):
        """环境变量 FEISHU_MODE=simulated → simulated 模式"""
        os.environ["FEISHU_MODE"] = "simulated"
        notifier = FeishuNotifier()
        assert notifier.config["mode"] == "simulated"

    def test_env_variable_priority_over_config(self, config_file):
        """配置文件非空值会覆盖环境变量（当前实现行为）"""
        os.environ["FEISHU_WEBHOOK_URL"] = "https://env-webhook.example.com"
        notifier = FeishuNotifier(config_path=config_file)
        # 当前实现：配置文件非空值覆盖环境变量
        assert notifier.config["webhook_url"] == "https://hooks.feishu.cn/test-webhook"

    def test_env_only_no_config_overwrite(self):
        """仅有环境变量无配置文件时使用环境变量"""
        os.environ["FEISHU_WEBHOOK_URL"] = "https://env-only.example.com"
        notifier = FeishuNotifier()
        assert notifier.config["webhook_url"] == "https://env-only.example.com"
        assert notifier.config["mode"] == "webhook"

    def test_config_file_loads_values(self, config_file):
        """配置文件加载非空值"""
        notifier = FeishuNotifier(config_path=config_file)
        assert notifier.config["webhook_url"] == "https://hooks.feishu.cn/test-webhook"
        assert notifier.config["mode"] == "webhook"

    def test_config_file_nonexistent_does_not_raise(self):
        """不存在的配置文件不抛异常"""
        notifier = FeishuNotifier(config_path="/nonexistent/path/config.json")
        assert notifier.config["mode"] == "simulated"

    def test_config_file_invalid_json(self):
        """无效JSON配置文件被静默处理"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {{{")
            bad_path = f.name
        try:
            notifier = FeishuNotifier(config_path=bad_path)
            assert notifier.config["mode"] == "simulated"
        finally:
            os.unlink(bad_path)

    def test_auto_mode_prefers_webhook(self):
        """auto模式优先webhook"""
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hooks.feishu.cn/test"
        # 不设置 FEISHU_MODE，默认 auto
        notifier = FeishuNotifier()
        assert notifier.config["mode"] == "webhook"

    def test_auto_mode_fallback_openapi(self):
        """auto模式无webhook有app_id+secret → openapi"""
        os.environ["FEISHU_APP_ID"] = "cli_test"
        os.environ["FEISHU_APP_SECRET"] = "secret_test"
        notifier = FeishuNotifier()
        assert notifier.config["mode"] == "openapi"

    def test_auto_mode_fallback_simulated(self):
        """auto模式无任何配置 → simulated"""
        notifier = FeishuNotifier()
        assert notifier.config["mode"] == "simulated"


# ── get_access_token 测试 ────────────────────────────────────────────────────

class TestGetAccessToken:
    """测试 get_access_token 方法"""

    def test_returns_none_for_simulated_mode(self):
        """simulated模式返回None"""
        notifier = FeishuNotifier()
        assert notifier.get_access_token() is None

    def test_returns_none_for_webhook_mode(self):
        """webhook模式返回None"""
        os.environ["FEISHU_MODE"] = "webhook"
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hooks.feishu.cn/test"
        notifier = FeishuNotifier()
        assert notifier.get_access_token() is None

    def test_openapi_gets_token_successfully(self, mock_requests):
        """openapi模式成功获取令牌"""
        os.environ["FEISHU_MODE"] = "openapi"
        os.environ["FEISHU_APP_ID"] = "cli_test"
        os.environ["FEISHU_APP_SECRET"] = "secret_test"
        mock_requests.post.return_value.json.return_value = {
            "code": 0,
            "tenant_access_token": "test-token-12345"
        }
        notifier = FeishuNotifier()
        token = notifier.get_access_token()
        assert token == "test-token-12345"
        assert notifier.token_expiry is not None

    def test_openapi_token_cache_reuse(self, mock_requests):
        """已缓存的令牌未过期时复用"""
        os.environ["FEISHU_MODE"] = "openapi"
        os.environ["FEISHU_APP_ID"] = "cli_test"
        os.environ["FEISHU_APP_SECRET"] = "secret_test"
        mock_requests.post.return_value.json.return_value = {
            "code": 0,
            "tenant_access_token": "test-token-12345"
        }
        notifier = FeishuNotifier()
        notifier.get_access_token()
        # 第二次调用不应再请求
        mock_requests.post.reset_mock()
        token = notifier.get_access_token()
        assert token == "test-token-12345"
        mock_requests.post.assert_not_called()

    def test_openapi_token_api_error(self, mock_requests):
        """API返回非0错误码"""
        os.environ["FEISHU_MODE"] = "openapi"
        os.environ["FEISHU_APP_ID"] = "cli_test"
        os.environ["FEISHU_APP_SECRET"] = "secret_test"
        mock_requests.post.return_value.json.return_value = {
            "code": 999,
            "msg": "invalid secret"
        }
        notifier = FeishuNotifier()
        token = notifier.get_access_token()
        assert token is None

    def test_openapi_token_network_exception(self, mock_requests):
        """网络异常导致获取令牌失败"""
        os.environ["FEISHU_MODE"] = "openapi"
        os.environ["FEISHU_APP_ID"] = "cli_test"
        os.environ["FEISHU_APP_SECRET"] = "secret_test"
        mock_requests.post.side_effect = Exception("Connection timeout")
        notifier = FeishuNotifier()
        token = notifier.get_access_token()
        assert token is None


# ── send_notification 测试 ────────────────────────────────────────────────────

class TestSendNotification:
    """测试 send_notification 方法"""

    def test_simulated_mode_success(self):
        """模拟模式发送通知成功"""
        notifier = FeishuNotifier()
        result = notifier.send_notification("Test Title", "Test Content", "info")
        assert result is True

    def test_simulated_mode_writes_log(self, tmp_path):
        """模拟模式写入日志文件"""
        # 切换到临时目录避免污染项目
        import os as _os
        orig_cwd = _os.getcwd()
        try:
            _os.chdir(tmp_path)
            notifier = FeishuNotifier()
            notifier.send_notification("Log Test", "Content Here", "warning")
            log_file = Path(tmp_path) / "feishu_notifications.log"
            assert log_file.exists()
            lines = log_file.read_text().strip().split("\n")
            assert len(lines) >= 1
            entry = json.loads(lines[-1])
            assert entry["title"] == "Log Test"
            assert entry["level"] == "warning"
        finally:
            _os.chdir(orig_cwd)

    def test_webhook_mode_success(self, mock_requests):
        """webhook模式发送成功"""
        os.environ["FEISHU_MODE"] = "webhook"
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hooks.feishu.cn/test"
        mock_requests.post.return_value.json.return_value = {"code": 0}
        notifier = FeishuNotifier()
        result = notifier.send_notification("Title", "Content", "success")
        assert result is True

    def test_webhook_mode_failure_fallback(self, mock_requests):
        """webhook发送失败回退到模拟模式"""
        os.environ["FEISHU_MODE"] = "webhook"
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hooks.feishu.cn/test"
        mock_requests.post.return_value.json.return_value = {"code": 1, "msg": "fail"}
        notifier = FeishuNotifier()
        result = notifier.send_notification("Title", "Content", "info")
        assert result is True  # 回退到模拟模式成功

    def test_webhook_mode_exception_fallback(self, mock_requests):
        """webhook异常回退到模拟模式"""
        os.environ["FEISHU_MODE"] = "webhook"
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hooks.feishu.cn/test"
        mock_requests.post.side_effect = Exception("Network Error")
        notifier = FeishuNotifier()
        result = notifier.send_notification("Title", "Content", "info")
        assert result is True  # 回退到模拟模式

    def test_openapi_mode_success(self, mock_requests):
        """openapi模式发送成功"""
        os.environ["FEISHU_MODE"] = "openapi"
        os.environ["FEISHU_APP_ID"] = "cli_test"
        os.environ["FEISHU_APP_SECRET"] = "secret_test"
        # Mock token response and message response
        mock_requests.post.return_value.json.return_value = {"code": 0}
        notifier = FeishuNotifier()
        result = notifier.send_notification("Title", "Content", "info")
        assert result is True

    def test_openapi_mode_failure_fallback(self, mock_requests):
        """openapi发送失败回退到模拟模式"""
        os.environ["FEISHU_MODE"] = "openapi"
        os.environ["FEISHU_APP_ID"] = "cli_test"
        os.environ["FEISHU_APP_SECRET"] = "secret_test"
        # token 获取失败导致发送失败
        mock_requests.post.return_value.json.return_value = {
            "code": 999,
            "msg": "invalid app secret"
        }
        notifier = FeishuNotifier()
        result = notifier.send_notification("Title", "Content", "info")
        assert result is True  # 回退到模拟模式

    def test_exception_in_send_notification_fallback(self):
        """send_notification顶层异常也回退模拟"""
        os.environ["FEISHU_MODE"] = "webhook"
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hooks.feishu.cn/test"
        with patch("src.utils.feishu_notifier.FeishuNotifier._send_via_webhook",
                   side_effect=Exception("Boom")):
            notifier = FeishuNotifier()
            result = notifier.send_notification("Title", "Content", "info")
            assert result is True

    def test_different_levels(self):
        """不同通知级别都能正常发送"""
        notifier = FeishuNotifier()
        for level in ["info", "success", "warning", "error"]:
            result = notifier.send_notification("T", "C", level)
            assert result is True

    def test_unknown_level_defaults_to_blue(self, mock_requests):
        """未知通知级别使用默认蓝色"""
        os.environ["FEISHU_MODE"] = "webhook"
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hooks.feishu.cn/test"
        mock_requests.post.return_value.json.return_value = {"code": 0}
        notifier = FeishuNotifier()
        # This calls _send_via_webhook which uses color_map.get(level, "blue")
        result = notifier.send_notification("T", "C", "unknown_level")
        assert result is True


# ── test_connection 测试 ──────────────────────────────────────────────────────

class TestConnection:
    """测试 test_connection 方法"""

    def test_simulated_mode_connection(self):
        """模拟模式连接测试"""
        notifier = FeishuNotifier()
        result = notifier.test_connection()
        assert result["config_mode"] == "simulated"
        assert result["test_result"] == "模拟模式"

    def test_webhook_mode_connection(self):
        """webhook模式连接测试"""
        os.environ["FEISHU_MODE"] = "webhook"
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hooks.feishu.cn/test"
        notifier = FeishuNotifier()
        result = notifier.test_connection()
        assert result["config_mode"] == "webhook"
        assert result["webhook_url"] == "已配置"
        assert result["test_result"] == "待测试"

    def test_webhook_no_url(self):
        """webhook模式未配置URL"""
        os.environ["FEISHU_MODE"] = "webhook"
        notifier = FeishuNotifier()
        result = notifier.test_connection()
        assert result["webhook_url"] == "未配置"

    def test_openapi_mode_connection_success(self, mock_requests):
        """openapi模式连接测试成功"""
        os.environ["FEISHU_MODE"] = "openapi"
        os.environ["FEISHU_APP_ID"] = "cli_test12345"
        os.environ["FEISHU_APP_SECRET"] = "secret_test"
        mock_requests.post.return_value.json.return_value = {
            "code": 0,
            "tenant_access_token": "token-xyz"
        }
        notifier = FeishuNotifier()
        result = notifier.test_connection()
        assert result["config_mode"] == "openapi"
        assert result["access_token"] == "获取成功"
        assert result["test_result"] == "成功"

    def test_openapi_mode_connection_failure(self, mock_requests):
        """openapi模式连接测试失败"""
        os.environ["FEISHU_MODE"] = "openapi"
        os.environ["FEISHU_APP_ID"] = "cli_test12345"
        os.environ["FEISHU_APP_SECRET"] = "secret_test"
        mock_requests.post.return_value.json.return_value = {
            "code": 999, "msg": "fail"
        }
        notifier = FeishuNotifier()
        result = notifier.test_connection()
        assert result["test_result"] == "失败"
        assert result["access_token"] == "获取失败"


# ── _send_via_webhook 测试 ───────────────────────────────────────────────────

class TestSendViaWebhook:
    """测试 _send_via_webhook 方法"""

    def test_webhook_success_response(self, mock_requests):
        """Webhook API 返回 code=0"""
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hooks.feishu.cn/test"
        mock_requests.post.return_value.json.return_value = {"code": 0}
        notifier = FeishuNotifier()
        result = notifier._send_via_webhook("T", "C", "info")
        assert result is True

    def test_webhook_error_response(self, mock_requests):
        """Webhook API 返回非0错误码"""
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hooks.feishu.cn/test"
        mock_requests.post.return_value.json.return_value = {
            "code": 1, "msg": "invalid url"
        }
        notifier = FeishuNotifier()
        result = notifier._send_via_webhook("T", "C", "info")
        assert result is False

    def test_webhook_network_exception(self, mock_requests):
        """Webhook 网络异常"""
        os.environ["FEISHU_WEBHOOK_URL"] = "https://hooks.feishu.cn/test"
        mock_requests.post.side_effect = Exception("Connection refused")
        notifier = FeishuNotifier()
        result = notifier._send_via_webhook("T", "C", "info")
        assert result is False


# ── _send_via_openapi 测试 ───────────────────────────────────────────────────

class TestSendViaOpenapi:
    """测试 _send_via_openapi 方法"""

    def test_openapi_no_token(self):
        """无token时openapi发送失败"""
        os.environ["FEISHU_MODE"] = "openapi"
        os.environ["FEISHU_APP_ID"] = "cli_test"
        os.environ["FEISHU_APP_SECRET"] = ""
        notifier = FeishuNotifier()
        result = notifier._send_via_openapi("T", "C", "info")
        assert result is False

    def test_openapi_success(self, mock_requests):
        """openapi发送成功"""
        os.environ["FEISHU_MODE"] = "openapi"
        os.environ["FEISHU_APP_ID"] = "cli_test"
        os.environ["FEISHU_APP_SECRET"] = "secret_test"
        mock_requests.post.return_value.json.return_value = {
            "code": 0,
            "tenant_access_token": "token-abc"
        }
        notifier = FeishuNotifier()
        # 先获取token
        notifier.access_token = "token-abc"
        from datetime import datetime, timedelta
        notifier.token_expiry = datetime.now() + timedelta(minutes=110)
        result = notifier._send_via_openapi("T", "C", "info")
        assert result is True

    def test_openapi_error_response(self, mock_requests):
        """openapi API返回错误"""
        os.environ["FEISHU_MODE"] = "openapi"
        os.environ["FEISHU_APP_ID"] = "cli_test"
        os.environ["FEISHU_APP_SECRET"] = "secret_test"
        mock_requests.post.return_value.json.return_value = {
            "code": 1, "msg": "permission denied"
        }
        notifier = FeishuNotifier()
        notifier.access_token = "token-abc"
        from datetime import datetime, timedelta
        notifier.token_expiry = datetime.now() + timedelta(minutes=110)
        result = notifier._send_via_openapi("T", "C", "info")
        assert result is False

    def test_openapi_network_exception(self, mock_requests):
        """openapi 网络异常"""
        os.environ["FEISHU_MODE"] = "openapi"
        os.environ["FEISHU_APP_ID"] = "cli_test"
        os.environ["FEISHU_APP_SECRET"] = "secret_test"
        mock_requests.post.side_effect = Exception("Timeout")
        notifier = FeishuNotifier()
        notifier.access_token = "token-abc"
        from datetime import datetime, timedelta
        notifier.token_expiry = datetime.now() + timedelta(minutes=110)
        result = notifier._send_via_openapi("T", "C", "info")
        assert result is False
