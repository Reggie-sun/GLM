# GLM Coding Bot - 阶段 4：库存监控和自动抢购 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现库存监控和自动抢购功能，这是项目的核心业务逻辑

**Architecture:** 后台任务持续监控目标页面，发现库存变化时触发通知和抢购流程

**Tech Stack:** Celery, APScheduler, Playwright, FastAPI background tasks

---

## 任务列表

### Task 1: 创建页面分析器 - bigmodel.cn 页面解析

**Files:**
- Create: `bot/pages/__init__.py`
- Create: `bot/pages/bigmodel.py`

**Steps:**
1. 创建 bot/pages 目录结构
2. 创建 bot/pages/bigmodel.py - bigmodel.cn 页面解析逻辑
3. 实现库存检测函数
4. 实现登录流程封装
5. 实现购买流程封装
6. 提交 git

### Task 2: 创建监控任务调度器

**Files:**
- Create: `app/monitor/__init__.py`
- Create: `app/monitor/scheduler.py`
- Create: `app/monitor/tasks.py`

**Steps:**
1. 创建监控模块结构
2. 创建监控任务定义
3. 创建任务调度器
4. 提交 git

### Task 3: 集成 Celery 异步任务

**Files:**
- Create: `app/celery_app.py`
- Update: `app/config.py`
- Update: `requirements.txt` (if needed)

**Steps:**
1. 创建 Celery 应用配置
2. 创建异步任务
3. 集成到现有项目
4. 提交 git

### Task 4: 创建通知服务

**Files:**
- Create: `app/notifications/__init__.py`
- Create: `app/notifications/base.py`
- Create: `app/notifications/console.py`
- Create: `app/notifications/webhook.py`

**Steps:**
1. 创建通知模块结构
2. 创建基础通知接口
3. 实现控制台通知
4. 实现 Webhook 通知
5. 提交 git

### Task 5: 添加监控和抢购相关的 API 端点

**Files:**
- Create: `app/api/v1/monitor.py`
- Update: `app/api/__init__.py`

**Steps:**
1. 创建监控 API
2. 添加启动/停止监控端点
3. 添加任务状态查询端点
4. 添加手动触发抢购端点
5. 更新路由聚合
6. 提交 git

### Task 6: 添加测试

**Files:**
- Create: `tests/test_monitor.py`

**Steps:**
1. 创建监控相关测试
2. 验证任务调度逻辑
3. 提交 git

---

## 阶段 4 验收标准

- [ ] 可以解析目标页面并检测库存状态
- [ ] 监控任务可以定时执行
- [ ] 库存变化时可以发送通知
- [ ] 可以触发自动抢购流程
- [ ] API 可以控制监控任务
