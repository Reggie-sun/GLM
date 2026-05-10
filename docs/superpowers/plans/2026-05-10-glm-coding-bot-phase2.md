# GLM Coding Bot - 阶段 2：数据库模型 + 数据持久化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立数据库模型和数据持久化层

**Architecture:** 使用 SQLAlchemy 2.0 作为 ORM，Alembic 用于数据库迁移

**Tech Stack:** SQLAlchemy 2.0, Alembic, PostgreSQL

---

## 任务列表

### Task 1: 配置 SQLAlchemy 数据库连接

**Files:**
- Create: `app/database.py`
- Modify: `app/config.py` (add more DB settings if needed)

**Steps:**
1. 创建 `app/database.py` - SQLAlchemy engine, session, base
2. 更新 `app/config.py` 确保数据库配置完整
3. 测试数据库连接
4. 提交 git

### Task 2: 创建数据模型

**Files:**
- Create: `app/models/base.py`
- Create: `app/models/user.py`
- Create: `app/models/account.py`
- Create: `app/models/proxy.py`
- Create: `app/models/snapshot.py`
- Create: `app/models/task.py`

**Models:**
- `User` - 用户
- `Account` - 账号池（bigmodel 账号）
- `Proxy` - 代理 IP
- `Snapshot` - 状态快照
- `Task` - 任务记录

**Steps:**
1. 创建 base.py - Base declarative
2. 创建各个模型文件
3. 创建 `app/models/__init__.py` 导出所有模型
4. 提交 git

### Task 3: 配置 Alembic 数据库迁移

**Files:**
- Create: `alembic.ini`
- Create: `alembic/` directory and contents
- Modify: `alembic/env.py`

**Steps:**
1. 初始化 alembic (or create manually)
2. 配置 alembic.ini
3. 配置 env.py 导入 models
4. 创建初始迁移
5. 提交 git

### Task 4: 创建 CRUD 服务层

**Files:**
- Create: `app/crud/__init__.py`
- Create: `app/crud/base.py`
- Create: `app/crud/user.py`
- Create: `app/crud/account.py`
- Create: `app/crud/proxy.py`
- Create: `app/crud/snapshot.py`
- Create: `app/crud/task.py`

**Steps:**
1. 创建 base CRUD 基类
2. 创建各个模型的 CRUD
3. 提交 git

### Task 5: 添加 API 端点（可选，简单的 CRUD）

**Files:**
- Create: `app/api/__init__.py`
- Create: `app/api/v1/__init__.py`
- Create: `app/api/v1/users.py`
- Create: `app/api/v1/accounts.py`
- Create: `app/api/v1/proxies.py`

**Steps:**
1. 设置 API 路由结构
2. 添加简单的 CRUD 端点
3. 更新 `app/main.py` 包含路由
4. 提交 git

### Task 6: 验证和测试

**Files:**
- Create: `tests/test_models.py`
- Create: `tests/test_crud.py`

**Steps:**
1. 编写模型测试
2. 编写 CRUD 测试
3. 运行测试确保通过
4. 提交 git

---

## 阶段 2 验收标准

- [ ] SQLAlchemy 配置正确，可以连接数据库
- [ ] 数据模型定义完整
- [ ] Alembic 迁移配置正确
- [ ] CRUD 服务层可用
- [ ] 测试运行通过
