# GLM Coding Bot - 阶段 1：项目骨架 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建项目基础结构，配置依赖，让项目可以运行起来

**Architecture:** 使用 Python + FastAPI 作为 Web 框架，采用分层架构设计

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, Poetry/Pip

---

## 任务列表

### Task 1: 创建项目目录结构

**Files:**
- Create: `app/__init__.py`
- Create: `app/api/__init__.py`
- Create: `app/core/__init__.py`
- Create: `app/models/__init__.py`
- Create: `app/services/__init__.py`
- Create: `app/templates/__init__.py`
- Create: `bot/__init__.py`
- Create: `data/snapshots/` (directory)
- Create: `data/logs/` (directory)
- Create: `docker/` (directory)
- Create: `tests/__init__.py`
- Create: `README.md`

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p /home/reggie/vscode_folder/GLM/app/api
mkdir -p /home/reggie/vscode_folder/GLM/app/core
mkdir -p /home/reggie/vscode_folder/GLM/app/models
mkdir -p /home/reggie/vscode_folder/GLM/app/services
mkdir -p /home/reggie/vscode_folder/GLM/app/templates
mkdir -p /home/reggie/vscode_folder/GLM/bot
mkdir -p /home/reggie/vscode_folder/GLM/data/snapshots
mkdir -p /home/reggie/vscode_folder/GLM/data/logs
mkdir -p /home/reggie/vscode_folder/GLM/docker
mkdir -p /home/reggie/vscode_folder/GLM/tests
```

- [ ] **Step 2: 创建空的 __init__.py 文件**

```python
# app/__init__.py
__version__ = "0.1.0"
```

```python
# app/api/__init__.py
```

```python
# app/core/__init__.py
```

```python
# app/models/__init__.py
```

```python
# app/services/__init__.py
```

```python
# app/templates/__init__.py
```

```python
# bot/__init__.py
```

```python
# tests/__init__.py
```

- [ ] **Step 3: 创建 README.md**

```markdown
# GLM Coding Bot

一个用于抓取 bigmodel.cn/glm-coding 购买接口的项目，支持多用户使用，具备被封后快速复活能力。

## 功能

- 库存监控
- 自动抢购
- 代理池管理
- 浏览器指纹轮换
- 秒级快速复活

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
docker-compose up
```
```

- [ ] **Step 4: 验证目录结构**

```bash
ls -la /home/reggie/vscode_folder/GLM/
```

Expected: 看到 app, bot, data, docker, tests, docs 等目录

---

### Task 2: 创建 Python 依赖配置

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml` (optional)

- [ ] **Step 1: 创建 requirements.txt**

```txt
# Web Framework
fastapi>=0.109.0
uvicorn>=0.27.0
jinja2>=3.1.0
python-multipart>=0.0.6

# Database
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
alembic>=1.13.0

# Cache/Queue
redis>=5.0.0
celery>=5.3.0

# Browser Automation
playwright>=1.40.0

# Utilities
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
aiofiles>=23.0.0
httpx>=0.26.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.23.0
pytest-cov>=4.1.0

# Formatting/Linting
black>=24.0.0
ruff>=0.2.0
```

- [ ] **Step 2: 创建 pyproject.toml (可选，用于 black/ruff 配置)**

```toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I", "N", "UP"]
ignore = ["E501"]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 3: 创建 .env.example**

```env
# App
APP_NAME=GLM Coding Bot
APP_ENV=development
DEBUG=true

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/glm_bot

# Redis
REDIS_URL=redis://localhost:6379/0

# Playwright
PLAYWRIGHT_HEADLESS=true

# Snapshots
SNAPSHOT_DIR=data/snapshots
SNAPSHOT_INTERVAL=30
```

- [ ] **Step 4: 创建 .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environment
.env
.env.local

# Data
data/snapshots/*
data/logs/*
!data/snapshots/.gitkeep
!data/logs/.gitkeep

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Docker
.dockerignore
```

- [ ] **Step 5: 创建 .gitkeep 文件**

```bash
touch /home/reggie/vscode_folder/GLM/data/snapshots/.gitkeep
touch /home/reggie/vscode_folder/GLM/data/logs/.gitkeep
```

---

### Task 3: 创建 FastAPI 应用入口

**Files:**
- Create: `app/main.py`
- Create: `app/config.py`
- Test: `tests/test_main.py`

- [ ] **Step 1: 创建配置文件 app/config.py**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "GLM Coding Bot"
    app_env: str = "development"
    debug: bool = True
    
    database_url: str = "postgresql://user:pass@localhost:5432/glm_bot"
    redis_url: str = "redis://localhost:6379/0"
    
    playwright_headless: bool = True
    
    snapshot_dir: str = "data/snapshots"
    snapshot_interval: int = 30
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
```

- [ ] **Step 2: 创建 FastAPI 应用 app/main.py**

```python
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

templates = Jinja2Templates(directory="app/templates")


@app.get("/")
async def root():
    return {"message": "GLM Coding Bot is running!", "status": "ok"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

- [ ] **Step 3: 创建测试 tests/test_main.py**

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "GLM Coding Bot is running!"
    assert data["status"] == "ok"


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
```

- [ ] **Step 4: 测试运行（可选，先不安装依赖）**

先不运行，因为依赖还没安装，等下一个任务

---

### Task 4: 创建 Docker 配置

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `docker/Dockerfile.playwright` (optional)
- Create: `.dockerignore`

- [ ] **Step 1: 创建 .dockerignore**

```dockerignore
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.git
.gitignore
.github
.vscode
.idea
*.swp
*.swo
*~
data/snapshots/*
data/logs/*
.env
.env.local
docs/
tests/
```

- [ ] **Step 2: 创建 Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps chromium

# Copy application
COPY . .

# Create data directories
RUN mkdir -p data/snapshots data/logs

# Expose port
EXPOSE 8000

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 3: 创建 docker-compose.yml**

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://glm_user:glm_pass@postgres:5432/glm_bot
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./data:/app/data
      - .:/app
    depends_on:
      - postgres
      - redis
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=glm_user
      - POSTGRES_PASSWORD=glm_pass
      - POSTGRES_DB=glm_bot
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: always

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: always

volumes:
  postgres_data:
  redis_data:
```

---

### Task 5: 验证项目可以运行

**Files:**
- N/A（验证用）

- [ ] **Step 1: 创建简单测试脚本 verify.py**

```python
import sys
from pathlib import Path

# Add project root to path
root = Path(__file__).parent
sys.path.insert(0, str(root))

print("Checking project structure...")

# Check required directories
required_dirs = [
    "app",
    "app/api",
    "app/core",
    "app/models",
    "app/services",
    "app/templates",
    "bot",
    "data/snapshots",
    "data/logs",
    "docker",
    "tests",
    "docs",
]

for d in required_dirs:
    dir_path = root / d
    if dir_path.exists():
        print(f"✓ {d}/")
    else:
        print(f"✗ {d}/ - MISSING")

# Check required files
required_files = [
    "requirements.txt",
    "app/main.py",
    "app/config.py",
    "docker-compose.yml",
    "Dockerfile",
    ".gitignore",
]

for f in required_files:
    file_path = root / f
    if file_path.exists():
        print(f"✓ {f}")
    else:
        print(f"✗ {f} - MISSING")

print("\nProject structure check complete!")
```

- [ ] **Step 2: 运行验证脚本**

```bash
cd /home/reggie/vscode_folder/GLM
python verify.py
```

Expected: 所有目录和文件都显示 ✓

- [ ] **Step 3: 清理临时验证脚本（可选）**

```bash
rm /home/reggie/vscode_folder/GLM/verify.py
```

---

## 阶段 1 验收

- [ ] 项目目录结构完整
- [ ] 依赖配置文件创建完成
- [ ] FastAPI 应用可以导入
- [ ] Docker 配置文件齐全
- [ ] 验证脚本运行通过

---

## 下一步

阶段 1 完成后，继续阶段 2：数据库模型 + 数据持久化
