# GLM Coding Bot - 使用示例

## 快速开始

### 1. 启动服务

```bash
docker compose up -d
```

### 2. 验证服务状态

```bash
python scripts/full_verification.py
```

## API 使用示例

### 获取服务状态

```bash
curl http://localhost:8001/
curl http://localhost:8001/health
```

### 账户管理

#### 查看所有账户

```bash
curl http://localhost:8001/api/v1/accounts/
```

#### 查看公共账户

```bash
curl http://localhost:8001/api/v1/accounts/public
```

#### 查看特定账户

```bash
curl http://localhost:8001/api/v1/accounts/1
```

### 监控任务管理

#### 创建监控任务

```bash
curl -X POST http://localhost:8001/api/v1/monitor/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GLM Coding Monitor",
    "target_url": "https://bigmodel.cn/glm-coding",
    "check_interval": 30,
    "auto_purchase": true,
    "account_id": 1
  }'
```

#### 查看所有任务

```bash
curl http://localhost:8001/api/v1/monitor/tasks
```

#### 查看特定任务

```bash
curl http://localhost:8001/api/v1/monitor/tasks/{task_id}
```

#### 启动/停止任务

```bash
curl -X POST http://localhost:8001/api/v1/monitor/tasks/{task_id}/start
curl -X POST http://localhost:8001/api/v1/monitor/tasks/{task_id}/stop
```

#### 删除任务

```bash
curl -X DELETE http://localhost:8001/api/v1/monitor/tasks/{task_id}
```

#### 手动触发检查

```bash
curl -X POST http://localhost:8001/api/v1/monitor/tasks/{task_id}/check
```

#### 手动触发购买

```bash
curl -X POST http://localhost:8001/api/v1/monitor/tasks/{task_id}/trigger-purchase
```

#### 查看调度器状态

```bash
curl http://localhost:8001/api/v1/monitor/status
```

#### 启动/停止调度器

```bash
curl -X POST http://localhost:8001/api/v1/monitor/scheduler/start
curl -X POST http://localhost:8001/api/v1/monitor/scheduler/stop
```

## Python SDK 使用示例

### 使用 requests 库

```python
import requests

BASE_URL = "http://localhost:8001"

# 创建监控任务
def create_monitor_task(name, url, interval=30, auto_purchase=False, account_id=None):
    payload = {
        "name": name,
        "target_url": url,
        "check_interval": interval,
        "auto_purchase": auto_purchase,
        "account_id": account_id
    }
    response = requests.post(f"{BASE_URL}/api/v1/monitor/tasks", json=payload)
    return response.json()

# 列出所有任务
def list_tasks():
    response = requests.get(f"{BASE_URL}/api/v1/monitor/tasks")
    return response.json()

# 获取任务状态
def get_task_status(task_id):
    response = requests.get(f"{BASE_URL}/api/v1/monitor/tasks/{task_id}")
    return response.json()

# 使用示例
if __name__ == "__main__":
    # 创建任务
    task = create_monitor_task(
        name="My Monitor",
        url="https://bigmodel.cn/glm-coding",
        interval=60,
        auto_purchase=True,
        account_id=1
    )
    print(f"Task created: {task['task_id']}")

    # 列出所有任务
    tasks = list_tasks()
    for t in tasks:
        print(f"{t['name']} - {t['status']}")
```

## 完整工作流示例

### 场景：设置自动购买监控

```bash
#!/bin/bash

# 1. 确保服务运行
docker compose ps

# 2. 验证账户存在
curl http://localhost:8001/api/v1/accounts/

# 3. 创建监控任务（启用自动购买）
TASK_ID=$(curl -s -X POST http://localhost:8001/api/v1/monitor/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GLM Coding Auto-Buy",
    "target_url": "https://bigmodel.cn/glm-coding",
    "check_interval": 30,
    "auto_purchase": true,
    "account_id": 1
  }' | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])")

echo "Created task: $TASK_ID"

# 4. 查看任务状态
curl "http://localhost:8001/api/v1/monitor/tasks/$TASK_ID" | python3 -m json.tool

# 5. 启动调度器
curl -X POST http://localhost:8001/api/v1/monitor/scheduler/start

echo "Setup complete! Monitor is running."
```

### 场景：手动测试购买流程

```python
import requests
import time

BASE_URL = "http://localhost:8001"

# 1. 创建测试任务
task_data = {
    "name": "Manual Purchase Test",
    "target_url": "https://bigmodel.cn/glm-coding",
    "check_interval": 60,
    "auto_purchase": False,
    "account_id": 1
}

response = requests.post(f"{BASE_URL}/api/v1/monitor/tasks", json=task_data)
task = response.json()
task_id = task['task_id']
print(f"Task ID: {task_id}")

# 2. 手动触发库存检查
print("\nChecking stock...")
check_response = requests.post(f"{BASE_URL}/api/v1/monitor/tasks/{task_id}/check")
print(check_response.json())

# 3. 如果有货，手动触发购买（可选）
# purchase_response = requests.post(f"{BASE_URL}/api/v1/monitor/tasks/{task_id}/trigger-purchase")
# print(purchase_response.json())
```

## Web 界面访问

### API 文档

访问 Swagger UI：`http://localhost:8001/docs`

访问 OpenAPI JSON：`http://localhost:8001/openapi.json`

## 日志查看

```bash
# 查看所有服务日志
docker compose logs -f

# 查看 Web 服务日志
docker compose logs -f web

# 查看 Worker 日志
docker compose logs -f worker

# 查看最近 50 行
docker compose logs --tail=50 web
```

## 数据库操作

### 直接连接数据库

```bash
docker compose exec postgres psql -U glm_user glm_bot
```

### 常用 SQL 查询

```sql
-- 查看所有账户
SELECT id, username, status, is_public, created_at FROM accounts;

-- 查看任务（需要先让任务持久化）
-- 未来版本将支持任务持久化
```

## 测试

### 运行所有测试

```bash
pytest tests/ -v
```

### 运行特定测试

```bash
pytest tests/test_purchase.py -v
pytest tests/test_monitor.py -v
```

### 生成覆盖率报告

```bash
pytest tests/ --cov=app --cov=bot --cov-report=html
```

## 故障排除

### 服务无法启动

```bash
# 检查端口是否被占用
lsof -i :8001

# 查看详细日志
docker compose logs

# 重启服务
docker compose restart
```

### 数据库连接问题

```bash
# 检查数据库容器状态
docker compose ps postgres

# 重启数据库
docker compose restart postgres

# 等待数据库启动
sleep 5
```

### API 返回错误

```bash
# 检查 Web 服务日志
docker compose logs web

# 验证服务状态
curl http://localhost:8001/health
```

## 开发模式

### 本地开发（不使用 Docker）

```bash
# 安装依赖
pip install -r requirements.txt

# 只启动数据库和 Redis
docker compose up -d postgres redis

# 配置环境变量
export DATABASE_URL=postgresql://glm_user:glm_pass@localhost:5432/glm_bot
export REDIS_URL=redis://localhost:6379/0

# 运行服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 代码变更后重建容器

```bash
# 重新构建并启动
docker compose up -d --build

# 或者只重建特定服务
docker compose build web
docker compose up -d
```
