# GLM Coding Bot - 测试环境搭建指南

## 快速启动

### 方式一：Docker Compose (推荐)

```bash
# 1. 启动所有服务
docker-compose up -d

# 2. 查看服务状态
docker-compose ps

# 3. 查看日志
docker-compose logs -f web

# 4. 访问应用
# 打开浏览器访问: http://localhost:8001
# API文档: http://localhost:8001/docs
```

### 方式二：本地开发

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 安装 Playwright 浏览器
playwright install chromium

# 3. 启动 PostgreSQL 和 Redis (可选，使用 Docker)
docker-compose up -d postgres redis

# 4. 更新 .env 文件中的数据库连接
DATABASE_URL=postgresql://glm_user:glm_pass@localhost:5432/glm_bot
REDIS_URL=redis://localhost:6379/0

# 5. 启动应用
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 验证安装

### 1. 运行验证脚本

```bash
python scripts/verify_purchase_setup.py
```

### 2. 运行测试

```bash
pytest tests/ -v
```

## 添加测试账户

### 通过 API 添加账户

1. 访问 API 文档: http://localhost:8001/docs
2. 找到账户相关的 API 端点
3. 添加测试账户

### 或者直接在数据库中添加

```bash
# 连接到数据库
docker-compose exec postgres psql -U glm_user glm_bot
```

## 创建监控任务

### 使用 curl

```bash
# 创建自动购买任务
curl -X POST http://localhost:8001/api/v1/monitor/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GLM Coding Auto Buy",
    "target_url": "https://bigmodel.cn/glm-coding",
    "check_interval": 30,
    "auto_purchase": true,
    "account_id": 1
  }'

# 查看所有任务
curl http://localhost:8001/api/v1/monitor/tasks
```

## 页面选择器配置

注意：当前 `bot/pages/bigmodel.py` 中的选择器是占位符，需要根据实际页面更新。

需要配置的选择器：
1. **库存状态选择器** - 检测商品是否有货
2. **登录表单选择器** - 用户名、密码输入框，登录按钮
3. **购买按钮选择器** - 点击购买的按钮
4. **确认按钮选择器** - 确认购买的按钮
5. **成功提示选择器** - 购买成功的提示元素
6. **订单号选择器** - 获取订单号的元素

## 故障排除

### 容器无法启动

```bash
# 查看详细日志
docker-compose logs

# 重启服务
docker-compose restart
```

### 数据库连接问题

```bash
# 检查数据库容器状态
docker-compose ps postgres

# 查看数据库日志
docker-compose logs postgres
```

### 网络访问问题

如果无法访问 bigmodel.cn:
- 检查网络连接
- 尝试使用代理
- 在可以访问的环境下分析页面结构

## 开发流程

1. 在本地开发环境修改代码
2. 运行测试: `pytest tests/ -v`
3. 如果修改了页面选择器，先在浏览器中测试
4. 提交代码
5. 重新构建容器（如需要）: `docker-compose build`
