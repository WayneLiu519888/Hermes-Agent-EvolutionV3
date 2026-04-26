# 🔧 飞书通知配置指南

## 📋 当前配置状态

**检测到的配置:**
- 模式: OpenAPI (App ID/Secret)
- App ID: cli_a96b9943f1f8dcd2
- App Secret: 已配置 (但可能已过期)
- 频道: oc_018d7317c249d59c48fa0ef0ada77317 (Wayne-Hermes)

**问题诊断:**
1. ✅ 访问令牌获取成功
2. ❌ 消息发送失败
3. ⚠️ 可能是频道权限问题或App Secret过期

## 🚀 解决方案

### 方案1: 修复OpenAPI配置 (推荐)
1. 登录飞书开放平台: https://open.feishu.cn/
2. 检查应用 `cli_a96b9943f1f8dcd2` 的状态
3. 确保App Secret未过期
4. 确认机器人已添加到频道 `Wayne-Hermes`
5. 验证频道ID是否正确

### 方案2: 切换到Webhook模式 (简单)
1. 在飞书群聊中添加"群机器人"
2. 获取Webhook URL
3. 更新配置文件:
```json
{
  "mode": "webhook",
  "webhook_url": "你的Webhook URL",
  "fallback_mode": "simulated"
}
```

### 方案3: 使用模拟模式 (临时)
- 系统会自动记录通知到日志文件
- 不会发送到飞书，但代码可以继续开发
- 日志文件: `feishu_notifications.log`

## 🔧 测试命令

```bash
# 测试当前配置
python3 test_feishu_config.py

# 简化测试 (模拟模式)
python3 simple_feishu_test.py

# 查看日志
cat feishu_notifications.log
```

## 📁 配置文件

### 1. 环境变量
```bash
# OpenAPI模式
export FEISHU_APP_ID="cli_a96b9943f1f8dcd2"
export FEISHU_APP_SECRET="你的App Secret"
export FEISHU_HOME_CHANNEL="频道ID"
export FEISHU_DOMAIN="feishu"

# Webhook模式
export FEISHU_WEBHOOK_URL="你的Webhook URL"
export FEISHU_MODE="webhook"
```

### 2. 配置文件
位置: `config/feishu_config.json`
```json
{
  "mode": "webhook",  # 或 "openapi"
  "webhook_url": "",
  "app_id": "",
  "app_secret": "",
  "home_channel": ""
}
```

## 🛠️ 代码使用

```python
from src.utils.feishu_notifier import FeishuNotifier

# 自动加载配置
notifier = FeishuNotifier()

# 发送通知
success = notifier.send_notification(
    title="通知标题",
    content="通知内容",
    level="info"  # info, success, warning, error
)
```

## 📊 故障排除

### 常见问题:
1. **访问令牌获取失败**
   - 检查App Secret是否过期
   - 确认网络连接正常

2. **消息发送失败**
   - 确认机器人有频道发送权限
   - 验证频道ID是否正确
   - 检查消息格式是否符合要求

3. **Webhook返回403**
   - Webhook URL可能已失效
   - 重新创建群机器人获取新URL

### 调试方法:
1. 查看日志: `tail -f feishu_notifications.log`
2. 测试连接: `python3 test_feishu_config.py`
3. 检查环境变量: `env | grep FEISHU`

## 🎯 下一步

1. **立即行动**: 测试当前配置是否有效
2. **备选方案**: 如果OpenAPI不行，切换到Webhook
3. **开发继续**: 使用模拟模式继续迭代开发
4. **后续优化**: 配置正确后启用真实通知

**注意**: 即使通知暂时无法发送到飞书，项目开发可以继续，所有通知会记录到本地日志。
