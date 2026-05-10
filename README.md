# GLM Coding Bot

一个用于抓取 bigmodel.cn/glm-coding 购买接口的项目，支持多用户使用，具备被封后快速复活能力。

## 功能特性

- 🕵️ **反检测保护**
  - 浏览器指纹轮换
  - 代理 IP 池管理
  - 会话持久化

- 👀 **库存监控**
  - 定时检测库存状态
  - 状态变化自动通知
  - 支持多种通知渠道

- 🛒 **自动抢购**
  - 有货自动触发购买
  - 支持手动触发
  - 完整任务调度

- ⚡ **快速复活**
  - 状态快照保存
  - 秒级恢复服务
  - Docker 容器化

## 项目结构

```
glm-coding-bot/
├── app/                    # 应用核心
│   ├── api/               # API 端点
│   │   └── v1/            # API v1 版本
│   ├── celery_tasks/      # 异步任务
│   ├── crud/              # 数据操作层
│   ├── models/            # 数据模型
│   ├── monitor/           # 监控调度器
│   └── notifications/     # 通知服务
├── bot/                   # 浏览器自动化
│   ├── pages/             # 页面解析器
│   ├── browser.py         # 浏览器管理
│   ├── fingerprint.py     # 指纹管理
│   ├── session.py         # 会话管理
│   ├── proxy.py           # 代理管理
│   └── navigator.py       # 页面导航
├── data/                  # 数据存储
│   ├── snapshots/         # 状态快照
│   ├── screenshots/       # 页面截图
│   ├── fingerprints/      # 指纹存储
│   ├── sessions/          # 会话存储
│   └── logs/              # 日志文件
├── alembic/               # 数据库迁移
├── tests/                 # 测试文件
├── docker/                # Docker 配置
├── docker-compose.yml     # 服务编排
├── requirements.txt       # Python 依赖
└── pyproject.toml         # 项目配置
```

## 技术栈

- **Web 框架** - FastAPI + Uvicorn
- **浏览器自动化** - Playwright
- **数据库** - PostgreSQL + SQLAlchemy
- **缓存/队列** - Redis + Celery
- **容器化** - Docker + Docker Compose
- **测试** - pytest

## 快速开始

### 1. 环境配置

```bash
# 复制环境变量模板
cp .env.example .env

# 根据需要编辑 .env 文件
```

### 2. Docker 启动（推荐）

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 3. 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium

# 运行数据库迁移
# alembic upgrade head

# 启动应用
uvicorn app.main:app --reload
```

## API 使用

### 基础端点

- `GET /` - 应用信息
- `GET /health` - 健康检查
- `GET /docs` - API 文档 (Swagger)
- `GET /redoc` - API 文档 (ReDoc)

### 监控 API

```bash
# 创建监控任务
curl -X POST http://localhost:8000/api/v1/monitor/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Monitor",
    "target_url": "https://bigmodel.cn/glm-coding",
    "check_interval": 30,
    "auto_purchase": false
  }'

# 列出所有任务
curl http://localhost:8000/api/v1/monitor/tasks

# 启动任务
curl -X POST http://localhost:8000/api/v1/monitor/tasks/{task_id}/start

# 停止任务
curl -X POST http://localhost:8000/api/v1/monitor/tasks/{task_id}/stop

# 手动检查库存
curl -X POST http://localhost:8000/api/v1/monitor/tasks/{task_id}/check
```

## 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `APP_NAME` | 应用名称 | GLM Coding Bot |
| `APP_ENV` | 环境 | development |
| `DEBUG` | 调试模式 | true |
| `DATABASE_URL` | 数据库连接 | postgresql://... |
| `REDIS_URL` | Redis 连接 | redis://... |
| `PLAYWRIGHT_HEADLESS` | 浏览器无界面 | true |
| `CELERY_BROKER_URL` | Celery Broker | redis://... |
| `CELERY_RESULT_BACKEND` | Celery Backend | redis://... |

### 数据模型

- **User** - 用户账户
- **Account** - bigmodel 账号（公共/私有）
- **Proxy** - 代理 IP（公共/私有）
- **Snapshot** - 状态快照
- **Task** - 任务记录

## 开发说明

### 添加新的页面解析器

```python
# bot/pages/my_site.py
from playwright.async_api import Page
from bot.navigator import PageNavigator

class MySitePage:
    async def check_stock(self):
        # 实现库存检测
        pass
```

### 添加新的通知渠道

```python
# app/notifications/my_channel.py
from app.notifications.base import NotificationChannel

class MyNotificationChannel(NotificationChannel):
    async def send(self, notification):
        # 实现通知发送
        pass
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行测试并显示覆盖率
pytest --cov=app

# 运行特定测试
pytest tests/test_monitor.py
```

## 注意事项

⚠️ **重要提示**

1. **合理使用** - 设置合理的检查间隔，避免对目标站点造成过大压力
2. **数据安全** - 妥善保管账号密码，定期备份数据库
3. **法律风险** - 仅用于学习研究，遵守相关法律法规
4. **道德使用** - 尊重他人权益，不滥用技术

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 PR！

## 联系方式

如有问题，请通过 Issue 反馈。
