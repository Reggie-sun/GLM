# Current Agent Handoff

## Summary

当前目标：帮助用户在 GLM Coding Plan 补货窗口内自动点击真实购买按钮，进入付款/订单支付页面即可，不完成最终支付。

当前结论：脚本已经能预热、检测按钮、真实点击购买链路、截图保留现场；但本轮窗口已错过。最新一次执行时页面从 `high_demand` 变成 `out_of_stock`，显示下一次补货为 `06月03日 10:00`。

不要在文档或日志里写入 cookie/token 明文。用户已经提供过新的 cookie，并已导入账号 1。

## Latest Runtime State

- Docker 服务：此前确认 `web/postgres/redis/worker` 均在运行，`web` 端口为 `localhost:8001`。
- 容器时间是 `UTC`，购买目标时间必须按 `Asia/Hong_Kong` 处理。
- 账号 1：
  - username: `whdgfr07`
  - status: `active`
  - 最新 cookie 已通过 `scripts/import_cookies.py --stdin 1` 导入。
  - 导入时解析到 15 个 cookies，包含 `bigmodel_token_production`。
- 最新真实执行结果：
  - 目标时间：`2026-06-02T10:15:00+08:00`
  - 状态变化：`high_demand` -> `out_of_stock`
  - 最终结果：
    - `success: false`
    - `stock_status: out_of_stock`
    - `actionable_purchase_button_count: 0`
    - `reason: no_actionable_purchase_button`
    - `restock_time: 暂时售罄 ｜06月03日 10:00 补货`

## Important Evidence

旧 cookie 场景下，脚本曾经点击到真实购买按钮，但站点弹出登录/注册弹窗，截图在：

```text
data/screenshots/payment_page_execute.png
```

这说明购买按钮点击链路本身已触发，但旧登录态不足。导入新 cookie 后不再是登录弹窗问题，而是补货窗口已经进入高并发/售罄状态。

## Code Changes In Progress

主要改动文件：

- `scripts/prewarm_purchase.py`
  - 新增 10 点前预热脚本。
  - 默认 dry-run，不点击购买。
  - `--execute` 才真实点击购买流程。
  - 默认 `--timezone Asia/Hong_Kong`。
  - 支持刚过目标时间的宽限窗口，避免 10 点刚过就排到明天。
  - 支持 `--purchase-timeout-ms`。
  - 支持 `--screenshot-path`，真实点击后保存最终页面截图。
  - 支持 `--wait-login-seconds`，遇到登录弹窗时等待用户扫码/手动登录后继续。

- `bot/pages/bigmodel.py`
  - 新增 `StockStatus.HIGH_DEMAND`。
  - 购买流程新增 `purchase_detailed()`，返回结构化诊断。
  - 对“抢购人数过多，请刷新再试”做高并发窗口识别。
  - 失败后不永久放弃，可在窗口内刷新重试。
  - 确认按钮现在只选择可见且可用的按钮，避免点到隐藏 DOM。
  - 检测到 `支付金额/支付方式/微信支付/支付宝/付款/二维码` 等文本时，判定已到付款页并停止。

- `app/monitor/scheduler.py`
  - `IN_STOCK` 和 `HIGH_DEMAND` 都会触发自动购买。
  - 失败购买不再永久设置 `purchase_attempted=True`，下一轮可继续重试。
  - 补货前后自动加快轮询。

- `scripts/import_cookies.py`
  - 支持安全导入：`--stdin` 和 `--env`。
  - 避免 cookie 出现在命令行参数里。

- `app/api/v1/accounts.py`
  - 响应新增 `has_cookie`，不泄露 cookie 内容。

- `app/api/v1/monitor.py`
  - 手动触发购买接口返回完整诊断结果。

- `app/services/purchase_capture.py`
  - 动态页面导航使用 `domcontentloaded`，避免 `networkidle` 卡住。

新增/更新测试：

- `tests/test_prewarm_purchase.py`
- `tests/test_import_cookies.py`
- `tests/test_browser.py`
- `tests/test_monitor.py`
- `tests/test_purchase.py`
- `tests/test_capture_script.py`

## Verification Already Run

最近一次完整测试，在加入登录等待前运行过：

```bash
docker compose exec -T web pytest -q
```

结果：

```text
89 passed, 3 warnings
```

加入登录等待与截图逻辑后的相关验证：

```bash
docker compose exec -T web pytest -q tests/test_prewarm_purchase.py tests/test_browser.py
```

结果：

```text
36 passed, 3 warnings
```

相关 lint：

```bash
docker compose exec -T web ruff check --select F scripts/prewarm_purchase.py bot/pages/bigmodel.py tests/test_prewarm_purchase.py tests/test_browser.py
```

结果：

```text
All checks passed!
```

## Useful Commands

Dry-run 预热，不点击购买：

```bash
docker compose exec -T web python -u scripts/prewarm_purchase.py \
  --account-id 1 \
  --target-time 10:00 \
  --timezone Asia/Hong_Kong \
  --prewarm-seconds 600 \
  --run-seconds 1200 \
  --refresh-interval 1
```

真实点击到付款页，不完成最终支付：

```bash
docker compose exec -T web python -u scripts/prewarm_purchase.py \
  --account-id 1 \
  --target-time 10:00 \
  --timezone Asia/Hong_Kong \
  --prewarm-seconds 600 \
  --run-seconds 1200 \
  --refresh-interval 1 \
  --purchase-timeout-ms 20000 \
  --execute \
  --screenshot-path data/screenshots/payment_page_execute.png
```

如果担心登录态失效，可让脚本等待扫码登录后继续：

```bash
docker compose exec -T web python -u scripts/prewarm_purchase.py \
  --account-id 1 \
  --target-time 10:00 \
  --timezone Asia/Hong_Kong \
  --prewarm-seconds 600 \
  --run-seconds 1200 \
  --refresh-interval 1 \
  --purchase-timeout-ms 20000 \
  --execute \
  --wait-login-seconds 180 \
  --screenshot-path data/screenshots/payment_page_execute.png
```

安全导入新 cookie：

```bash
docker compose exec -T web python scripts/import_cookies.py --stdin 1
```

然后通过 stdin 输入 cookie 字符串。注意不要把 cookie 写进命令参数或 markdown。

## Next Agent Checklist

1. 先读本文件和 `git status --short`，不要覆盖未提交改动。
2. 确认当前日期/时间和补货时间。用户最近页面显示下一次补货为 `06月03日 10:00`，按 `Asia/Hong_Kong`。
3. 在补货前 10 分钟运行 dry-run，确认：
   - cookie 仍有效
   - `stock_status` 能读到
   - 没有登录弹窗
4. 到点运行 `--execute` 命令。
5. 如果遇到 `logged_out`：
   - 使用 `--wait-login-seconds 180`
   - 查看 `data/screenshots/payment_page_execute.png`
   - 让用户扫码登录后脚本自动重试。
6. 成功标准：进入付款/订单支付页面并保存截图；不要点击最终支付确认。

## Guardrails

- 不要绕过 CAPTCHA、风控或平台限制。
- 不要完成最终支付。
- 不要输出 cookie/token 明文。
- 不要把用户提供的 cookie 写进文件。
- 真实点击购买只在用户授权 `--execute` 的语义下执行。
