# GLM Coding Bot - 验证状态

## 当前状态: 部分验证通过 ✅

### 已完成:

1. **Docker 服务运行正常**
   - ✅ Postgres 数据库: 运行中 (端口 5432)
   - ✅ Redis: 运行中
   - ✅ Web API: 运行中 (端口 8001, 健康检查通过)
   - ✅ Celery Worker: 运行中

2. **数据库初始化**
   - ✅ 数据库表创建成功: accounts, proxies, snapshots, tasks, users
   - ✅ 测试账户已添加 (ID: 1, username: test_user)

3. **API 端点验证**
   - ✅ 根端点: `http://localhost:8001/`
   - ✅ 账户 API: `http://localhost:8001/api/v1/accounts/`
   - ✅ 监控任务 API: `http://localhost:8001/api/v1/monitor/monitor/tasks`
   - ✅ 监控任务已创建并运行中

4. **代码测试**
   - ✅ 所有 46 个测试通过 (`pytest tests/ -v`)

### 待完成 (需要网络访问):

1. **页面选择器配置**
   - ❌ 无法访问 `https://bigmodel.cn` (网络问题)
   - ❌ 需要分析页面结构并更新 `bot/pages/bigmodel.py` 中的选择器

2. **真实购买测试**
   - ❌ 需要有效的 bigmodel.cn 账户 cookies
   - ❌ 需要能够访问目标网站

## 下一步操作指南

### 1. 配置页面选择器

在能够访问 `https://bigmodel.cn` 的环境中:

```bash
# 运行页面分析脚本
python analyze_page_full.py

# 或运行首页分析
python analyze_home.py
```

然后根据分析结果更新 `bot/pages/bigmodel.py` 中的选择器。

### 2. 添加真实账户信息

通过 API 更新测试账户的 cookies:

```bash
# 或直接在数据库中更新
docker compose exec postgres psql -U glm_user glm_bot
```

### 3. 测试完整流程

```bash
# 查看任务状态
curl http://localhost:8001/api/v1/monitor/monitor/tasks

# 手动触发一次库存检查
curl -X POST http://localhost:8001/api/v1/monitor/monitor/tasks/{task_id}/check

# 手动触发购买尝试
curl -X POST http://localhost:8001/api/v1/monitor/monitor/tasks/{task_id}/trigger-purchase
```

## API 端点参考

注意: monitor 路径有重复的 `/monitor` 前缀 (已知问题)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务状态 |
| `/health` | GET | 健康检查 |
| `/api/v1/accounts/` | GET | 账户列表 |
| `/api/v1/accounts/{id}` | GET | 账户详情 |
| `/api/v1/monitor/monitor/tasks` | GET | 监控任务列表 |
| `/api/v1/monitor/monitor/tasks` | POST | 创建监控任务 |
| `/api/v1/monitor/monitor/tasks/{id}` | GET | 任务详情 |
| `/api/v1/monitor/monitor/tasks/{id}/start` | POST | 启动任务 |
| `/api/v1/monitor/monitor/tasks/{id}/stop` | POST | 停止任务 |
| `/api/v1/monitor/monitor/tasks/{id}/check` | POST | 手动检查库存 |
| `/api/v1/monitor/monitor/tasks/{id}/trigger-purchase` | POST | 手动触发购买 |
| `/api/v1/monitor/monitor/status` | GET | 调度器状态 |
| `/api/v1/monitor/monitor/scheduler/start` | POST | 启动调度器 |
| `/api/v1/monitor/monitor/scheduler/stop` | POST | 停止调度器 |

## 查看日志

```bash
# 查看 Web 服务日志
docker compose logs -f web

# 查看 Worker 日志
docker compose logs -f worker

# 查看所有服务日志
docker compose logs -f
```
