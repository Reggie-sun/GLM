# 页面选择器配置指南

## 当前状态: 占位符选择器 ⚠️

当前 `bot/pages/bigmodel.py` 中的所有选择器都是占位符，需要根据实际的 bigmodel.cn 页面结构进行更新。

## 需要配置的选择器

### 1. 库存状态检查 (`check_stock` 方法)

| 占位符 | 说明 | 需要的选择器 |
|--------|------|-------------|
| `#stock-status` | 库存状态元素 | 显示"有货"/"无货"的元素 |
| `.product-name` | 商品名称 | 商品标题元素 |
| `.product-price` | 商品价格 | 价格显示元素 |

### 2. 登录功能 (`login` 方法)

| 占位符 | 说明 | 需要的选择器 |
|--------|------|-------------|
| `#username` | 用户名输入框 | 用户名/手机号输入框 |
| `#password` | 密码输入框 | 密码输入框 |
| `#login-button` | 登录按钮 | 登录提交按钮 |
| `.user-profile` | 用户资料 | 登录成功后显示的元素 |

### 3. 购买功能 (`purchase` 方法)

| 占位符 | 说明 | 需要的选择器 |
|--------|------|-------------|
| `.buy-button` | 购买按钮 | 立即购买/预约按钮 |
| `.confirm-button` | 确认按钮 | 确认购买按钮 |
| `.success-message` | 成功提示 | 购买成功提示 |
| `.order-id` | 订单号 | 订单号显示元素 |

## 如何获取真实选择器

### 方法一: 使用浏览器开发者工具

1. 在 Chrome/Edge 中打开 `https://bigmodel.cn`
2. 按 F12 打开开发者工具
3. 使用元素选择器 (Ctrl+Shift+C) 点击目标元素
4. 在 Elements 面板中查看:
   - `id` 属性 → 使用 `#id`
   - `class` 属性 → 使用 `.classname`
   - 其他属性 → 使用 `[attribute="value"]`

### 方法二: 使用分析脚本 (需要网络访问)

在能够访问 bigmodel.cn 的环境中运行:

```bash
# 分析首页
python analyze_home.py

# 分析 GLM Coding 页面
python analyze_page_full.py
```

脚本会保存:
- 截图: `data/screenshots/bigmodel_home.png`
- HTML: `data/screenshots/bigmodel_home.html`

### 方法三: 手动检查页面

在浏览器中访问页面后，右键 → "查看网页源代码" 或使用开发工具检查。

## 选择器最佳实践

### 优先级:
1. **唯一 ID** → `#submit-button` (最稳定)
2. **特定 data 属性** → `[data-testid="buy-button"]`
3. **特定 class + 文本** → 组合使用
4. **XPath** → 仅作为最后手段

### 稳定性原则:
- ✅ 使用 `data-*` 属性 (如果有)
- ✅ 使用语义化的 class 名称
- ✅ 避免自动生成的 class (如 `css-abc123`)
- ❌ 避免使用位置索引 (如 `:nth-child(3)`)
- ❌ 避免过于复杂的嵌套选择器

## 配置示例

假设通过分析发现了以下选择器:

```python
# 更新 bot/pages/bigmodel.py

class BigModelPage:
    # 选择器常量 (建议添加)
    SELECTORS = {
        "stock_status": ".stock-badge",
        "product_name": "h1.product-title",
        "product_price": ".price-display",
        "username_input": "input[name='phone']",
        "password_input": "input[name='password']",
        "login_button": "button[type='submit']",
        "user_profile": ".user-avatar",
        "buy_button": ".purchase-btn",
        "confirm_button": ".confirm-purchase",
        "success_message": ".order-success",
        "order_id": ".order-number",
    }

    async def check_stock(self):
        selector = self.SELECTORS["stock_status"]
        # ... 使用 selector
```

## 验证配置

配置完成后，运行测试:

```bash
pytest tests/test_purchase.py -v
```

或手动测试:

```python
# 在 Python 中测试
import asyncio
from bot.pages.bigmodel import BigModelPage
from bot.browser import BrowserManager

async def test_selectors():
    manager = BrowserManager()
    await manager.start()
    
    context = await manager.create_context()
    page = await manager.new_page(context)
    
    # 测试导航
    await page.goto("https://bigmodel.cn/glm-coding")
    
    # 测试选择器...
```

## 注意事项

1. **页面可能随时变化** - 选择器需要定期更新
2. **不同页面可能有不同结构** - 首页 vs 商品详情页
3. **动态加载内容** - 一些元素可能需要等待 JavaScript 渲染
4. **反爬虫机制** - 注意访问频率，避免被封禁

## 下一步

一旦获得真实的页面结构，请:
1. 更新 `bot/pages/bigmodel.py` 中的选择器
2. 更新相关测试
3. 运行完整测试验证
