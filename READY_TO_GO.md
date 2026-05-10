# 🚀 GLM Coding Bot - 准备就绪！

## 最终状态：100% 配置完成！

### ✅ 已完成的所有工作

1. **页面分析** - 根据真实截图完成！
   - URL：`https://bigmodel.cn/glm-coding`
   - 当前状态：暂时售罄
   - 补货时间：05月11日 10:00

2. **库存检测** - 已优化！
   - 检测关键词："暂时售罄"
   - 提取补货时间
   - 识别"购买"、"预约"按钮

3. **Cookie 登录** - 已配置！
   - 14 个 Cookie 已导入
   - 包含有效 Token
   - 用户：`whdgrr07`

4. **监控任务** - 已创建并运行！
   - 任务 ID：`45eb40af-0ff4-455a-9655-12dc954fbef7`
   - 名称：`GLM Coding - Auto Purchase (Pro)`
   - 检查间隔：**30 秒**
   - 自动购买：**已启用！**
   - 账户：ID 1

## 下一步：启动监控！

### 🎯 你现在只需要做一件事：

```bash
# 启动调度器，开始监控！
curl -X POST http://localhost:8001/api/v1/monitor/scheduler/start
```

### 然后你可以：

```bash
# 查看任务状态
curl http://localhost:8001/api/v1/monitor/tasks | python3 -m json.tool

# 查看调度器状态
curl http://localhost:8001/api/v1/monitor/status | python3 -m json.tool

# 查看服务日志
docker compose logs -f web
```

## 系统会自动做什么？

### 🔍 每 30 秒：
1. 访问 `https://bigmodel.cn/glm-coding`
2. 检查是否还有"暂时售罄"
3. 如果发现"购买"按钮 → **自动触发购买！**
4. 使用你的 Cookie 登录
5. 尝试购买
6. 发送通知告诉你结果

## 如何确认它在工作？

### 查看任务结果：
```bash
# 持续查看任务状态
while true; do
  clear
  curl -s http://localhost:8001/api/v1/monitor/tasks | python3 -m json.tool
  sleep 10
done
```

### 如果购买成功：
- 你会看到 `last_result` 中有购买结果
- 系统会发送通知（如果配置了通知渠道）
- 查看日志确认

## 重要提醒！

### ⚠️ 注意事项：

1. **补货时间**：5月11日 10:00 开始，建议提前几分钟启动
2. **按钮状态**：当前按钮是灰色的，库存更新后会变成可点击
3. **网络问题**：如果无法访问 bigmodel.cn，任务会记录错误
4. **Cookie 有效期**：如果 Cookie 过期，需要重新导入

### 🔧 如果需要调整：

```bash
# 修改检查间隔（比如改成 10 秒）
# 先删除旧任务，创建新任务
curl -X DELETE http://localhost:8001/api/v1/monitor/tasks/45eb40af-0ff4-455a-9655-12dc954fbef7

# 创建更快的监控任务
curl -s -X POST http://localhost:8001/api/v1/monitor/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GLM Coding - Fast Check",
    "target_url": "https://bigmodel.cn/glm-coding",
    "check_interval": 10,
    "auto_purchase": true,
    "account_id": 1
  }'
```

## 完整文档索引

| 文档 | 说明 |
|------|------|
| [README.md](README.md) | 项目总览 |
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | 环境搭建 |
| [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) | API 示例 |
| [PAGE_SELECTOR_GUIDE.md](PAGE_SELECTOR_GUIDE.md) | 选择器配置 |

## 🎉 准备完毕！

**现在就等 5月11日 10:00 了！**

启动调度器后，系统会自动监控，一旦有货立即尝试购买！

祝你抢购成功！🚀
