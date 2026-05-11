# GLM Bot Frontend Console Design Spec

> Date: 2026-05-11
> Status: Draft
> Codex Review: Incorporated (session 019e14e9-e45f-7031-a9c0-3650d5634c76)

## 1. Problem

GLM Bot is a FastAPI + Playwright automation tool for monitoring/purchasing GLM Coding from bigmodel.cn. Currently:

- No frontend — all operations via raw API calls
- No authentication — all routes unauthenticated
- Monitor tasks are in-memory only — lost on container restart
- No multi-user support despite `owner_id`/`created_by` fields existing
- Sensitive data (passwords, cookies) stored in plaintext
- API responses are untyped dicts — no Pydantic schemas

This spec defines the transformation from single-user script to multi-user console.

## 2. Architecture

**Monorepo + FastAPI hosting.** Frontend in `/web`, Vite build output served by FastAPI as static files.

```
GLM/
├── app/                          # FastAPI backend (existing, modified)
│   ├── api/v1/
│   │   ├── auth.py               # NEW: login, register, refresh, logout, me
│   │   ├── monitor.py            # MODIFIED: add auth deps, owner filtering
│   │   ├── accounts.py           # MODIFIED: add auth deps, CRUD, owner filtering
│   │   ├── proxies.py            # MODIFIED: add auth deps, CRUD, owner filtering
│   │   ├── notifications.py      # NEW: notification history query
│   │   └── users.py              # MODIFIED: add auth deps, admin-only
│   ├── core/
│   │   ├── security.py           # NEW: JWT, password hash, get_current_user
│   │   └── crypto.py             # NEW: AES encrypt/decrypt for sensitive fields
│   ├── models/
│   │   ├── task.py               # MODIFIED: add monitor task fields
│   │   ├── notification_event.py # NEW: notification history
│   │   └── refresh_token.py      # NEW: refresh token storage
│   ├── schemas/                  # NEW: Pydantic request/response schemas
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── account.py
│   │   ├── proxy.py
│   │   ├── task.py
│   │   └── notification.py
│   ├── monitor/
│   │   ├── scheduler.py          # MODIFIED: DB-backed task persistence
│   │   └── tasks.py              # MODIFIED: registry reads/writes DB
│   └── main.py                   # MODIFIED: static files + SPA catch-all
│
├── web/                          # Frontend (NEW)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx               # React Router config
│       ├── api/
│       │   ├── client.ts         # axios instance + interceptors
│       │   ├── auth.ts
│       │   ├── tasks.ts
│       │   ├── accounts.ts
│       │   ├── proxies.ts
│       │   └── notifications.ts
│       ├── components/
│       │   ├── Layout.tsx        # Sidebar + topbar
│       │   ├── AuthGuard.tsx     # Route guard
│       │   └── AdminGuard.tsx    # Admin route guard
│       ├── pages/
│       │   ├── login.tsx
│       │   ├── register.tsx
│       │   ├── tasks.tsx
│       │   ├── accounts.tsx
│       │   ├── proxies.tsx
│       │   ├── notifications.tsx
│       │   └── admin/
│       │       ├── users.tsx
│       │       ├── all-tasks.tsx
│       │       └── system.tsx
│       ├── store/
│       │   └── auth.ts           # Zustand: user info, is_authenticated
│       └── types/                # TypeScript type definitions
│
├── alembic/versions/             # NEW migrations
├── docker-compose.yml            # MODIFIED: web service build stages
└── Dockerfile                    # MODIFIED: multi-stage (node build → python)
```

## 3. Backend: System Boundary (must complete before frontend)

### 3.1 Monitor Task Persistence

**Current state**: `MonitorTask` is a dataclass in memory. `Task` table exists but unused.

**Change**:
- `Task` model gets new columns: `name`, `target_url`, `check_interval`, `auto_purchase`, `account_id`, `proxy_id`, `webhook_url`, `last_result` (JSON), `last_run_at`
- `MonitorTaskRegistry` becomes a DB-backed layer: `add()` writes to DB, `get()` reads from DB, `list_all()` queries DB
- Runtime state (asyncio.Task references) stays in memory via `_running_tasks` dict
- Scheduler startup: load tasks with `status='running'` from DB and resume monitoring
- Container restart no longer loses task definitions

**Alembic migration**: Add columns to `tasks` table, with nullable defaults for existing rows.

### 3.2 Auth Infrastructure

**New dependencies** (requirements.txt):
- `python-jose[cryptography]>=3.3.0` — JWT encode/decode
- `passlib[bcrypt]>=1.7.4` — password hashing

**`app/core/security.py`**:
- `hash_password(plain) -> str`
- `verify_password(plain, hashed) -> bool`
- `create_access_token(user_id, expires_delta) -> str`
- `create_refresh_token(user_id, expires_delta) -> str`
- `decode_token(token) -> dict`
- `get_current_user(token=Cookie('access_token'), db=Depends(get_db)) -> User` — FastAPI dependency

**`app/models/refresh_token.py`**:
```python
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(500), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Auth API** (`app/api/v1/auth.py`):
- `POST /auth/register` — create user, return access+refresh cookies
- `POST /auth/login` — verify credentials, set HttpOnly cookies
- `POST /auth/refresh` — read refresh_token from cookie, validate against DB, issue new access_token
- `POST /auth/logout` — clear cookies, delete refresh_token from DB
- `GET /auth/me` — return current user info

**Cookie settings**:
- `HttpOnly=True, Secure=True, SameSite=Strict, Path=/`
- Access token: 30 min expiry
- Refresh token: 7 day expiry, stored in DB for revocation

**CSRF protection**: `SameSite=Strict` + CSRF middleware in `app/main.py` that validates `X-Requested-With: XMLHttpRequest` header on all POST/PUT/PATCH/DELETE requests. Rejects requests missing this header with 403.

### 3.3 Multi-Tenant Data Model

**Changes to existing models**:

```python
# Account
owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

# Proxy
owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

# Task
created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
```

**Ownership rules**:
- `owner_id` is always set to the creator's user_id (even for public resources). It is NOT nullable for new records.
- Public resources (`is_public=True`): visible to all authenticated users in list queries (non-owner gets read-only access — cannot edit/delete)
- Private resources (`is_public=False`): only visible to owner and admin
- All single-resource endpoints: verify `owner_id == current_user.id` or `is_superuser`, else 403
- Task creation: auto-set `created_by = current_user.id`
- Account/Proxy creation: auto-set `owner_id = current_user.id`, `is_public` defaults to False
- Existing rows with `owner_id=NULL` (legacy public resources): treat as system-owned, visible to all authenticated users, editable only by admin

**Admin (`is_superuser`)**:
- View all resources across users
- Manage users (activate/deactivate, delete)
- Operate any task (start/stop/purchase)
- Cannot view decrypted sensitive fields of other users' accounts (only see masked values)

### 3.4 Notification History

**New model**:
```python
class NotificationEvent(Base):
    __tablename__ = "notification_events"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # stock_change, purchase_success, purchase_failed, login_failed
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    level = Column(String(20), nullable=False)  # success, warning, error, info
    data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
```

**Integration**: Every `notification_service.send()` call also writes to `notification_events` table with `user_id` from the associated task's `created_by`.

**New API**: `GET /api/v1/notifications?event_type=&since=&limit=&offset=`

### 3.5 Sensitive Data Protection

**New dependency**: `cryptography>=42.0.0`

**`app/core/crypto.py`**:
- `encrypt_field(plain_text) -> str` — AES-256-GCM encryption
- `decrypt_field(cipher_text) -> str`
- Encryption key from `settings.encryption_key` (env var, 32 bytes base64)

**Fields to encrypt at rest**:
- `Account.password`
- `Account.cookie`
- `Proxy.password`

**API response masking** (in Pydantic schemas):
- `password` → never included in response
- `cookie` → first 10 chars + `...` (e.g., `session_id=abc...`)
- `proxy.password` → `***`

**Migration**: Add alembic migration to encrypt existing plaintext values. Requires `encryption_key` env var set during migration.

### 3.6 API Schema Standardization

**New directory**: `app/schemas/`

Each resource gets:
- `*Create` schema — for POST requests (input validation)
- `*Update` schema — for PUT/PATCH requests (all optional)
- `*Response` schema — for API responses (excludes sensitive fields)
- `*ListResponse` schema — paginated list with `total`, `items`

**Example** (`app/schemas/account.py`):
```python
class AccountCreate(BaseModel):
    username: str
    password: str
    email: str | None = None
    phone: str | None = None
    is_public: bool = True

class AccountUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    email: str | None = None
    phone: str | None = None
    cookie: str | None = None
    is_public: bool | None = None

class AccountResponse(BaseModel):
    id: int
    username: str
    email: str | None
    phone: str | None
    status: str
    cookie_masked: str | None  # first 10 chars + "..."
    user_agent: str | None
    last_used_at: datetime | None
    is_public: bool
    owner_id: int | None
    created_at: datetime
    updated_at: datetime | None
```

All API endpoints updated to use these schemas instead of raw dicts.

## 4. Frontend

### 4.1 Tech Stack

- React 18 + TypeScript
- Vite 6
- Ant Design 5 — component library
- TanStack Query v5 — server state management (caching, invalidation, retry)
- Zustand — client-only state (sidebar collapse, theme)
- React Router v6 — routing
- Axios — HTTP client with interceptors
- Day.js — date formatting (Ant Design dependency)

### 4.2 State Management

**TanStack Query** for all server state:
- `useQuery(['tasks'], fetchTasks, { refetchInterval: 10000 })` — auto-refresh every 10s
- `useMutation(createTask, { onSuccess: () => queryClient.invalidateQueries(['tasks']) })`
- Optimistic updates for start/stop: `onMutate` updates cache, `onError` rolls back

**Zustand** for client-only state:
- `useAuthStore`: `user`, `isAuthenticated`, `login()`, `logout()`
- Does NOT store tokens — tokens are in HttpOnly cookies, managed by browser

### 4.3 Auth Flow

1. User submits login form → `POST /api/v1/auth/login` (with credentials in body)
2. Backend sets `access_token` + `refresh_token` as HttpOnly cookies
3. Frontend reads `GET /api/v1/auth/me` to get user info → stores in Zustand
4. All subsequent requests: browser auto-sends cookies (no manual header)
5. Axios response interceptor: 401 → clear Zustand auth → redirect to `/login?redirect=...`
6. Logout: `POST /api/v1/auth/logout` → backend clears cookies + deletes DB refresh token

### 4.4 Error Handling

| Status | Frontend Behavior |
|--------|-------------------|
| 401 | Clear auth state, redirect to `/login?redirect=current_path` |
| 403 | Show Ant Design `Result 403` page |
| 404 | API: JSON error in `message.error`; SPA: React Router `*` catch-all page |
| 409 | `message.warning` with conflict detail |
| 422 | Form inline validation errors |
| 500 | `message.error` with generic message |

### 4.5 Task State Sync

- **Primary**: TanStack Query `refetchInterval: 10000` on task list
- **After mutation**: `useMutation` `onSuccess` invalidates task queries immediately
- **Future**: SSE endpoint `GET /api/v1/events` for real-time stock change/purchase result push

### 4.6 Pages

**User side (4 pages)**:
- **Monitor Tasks** — Ant Design Table with columns: name, account, status, stock, last check, actions (start/stop/purchase/check/delete). Modal form for create. Filters: status dropdown, search input.
- **Account Management** — Card grid layout. Each card shows username, email, status, last used. Actions: edit, test login, update cookie, delete. Add account button + import cookie button.
- **Proxy Management** — Table with type, host:port, status, latency. CRUD operations.
- **Notifications & History** — Timeline layout. Filter tabs: all, purchase success, stock change, errors. Color-coded by level.

**Admin side (3 pages)**:
- **User Management** — User list table. Actions: activate/deactivate, delete, view user's resources.
- **All Tasks** — All users' tasks overview. Same table as user tasks but with user column.
- **System Status** — Scheduler status, worker health, Redis connectivity, active task count.

**Auth pages (2)**:
- **Login** — Email/username + password form. Link to register.
- **Register** — Username + email + password form.

### 4.7 Sensitive Fields in UI

- Password fields: `type="password"`, placeholder "Enter new password (leave blank to keep)"
- Cookie display: masked value from API (first 10 chars + `...`)
- Import cookie: `textarea` for paste, value cleared after successful submit
- Never show decrypted values in frontend

## 5. Deployment

### 5.1 Dockerfile (multi-stage)

```dockerfile
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 2: Python app
FROM mcr.microsoft.com/playwright/python:v1.59.0-noble
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
COPY app/ ./app/
COPY bot/ ./bot/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY --from=frontend-build /web/dist ./static/
RUN mkdir -p data/snapshots data/logs
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 5.2 docker-compose.yml

No structural change. `web` service gets the updated Dockerfile. `worker` service same as before.

```
web:    FastAPI + static frontend + Playwright  (port 8001:8000)
worker: Celery worker                           (no external port)
postgres: PostgreSQL 15                         (persistent volume)
redis:   Redis 7                                (persistent volume)
```

### 5.3 FastAPI Static File Mounting

**Route priority** (in `app/main.py`):
1. `/api/v1/*` — API routes (highest priority, registered first)
2. `/docs`, `/redoc` — Swagger UI
3. `/health` — health check
4. `/assets/*` — static files (JS/CSS/images from Vite build)
5. `/*` — SPA catch-all (return `index.html` for any unmatched path)

SPA catch-all only triggers after all API and static routes fail. API 404s return JSON; frontend 404s handled by React Router.

### 5.4 Development Setup

- Frontend: `cd web && npm run dev` (Vite dev server on port 5173)
- Backend: `uvicorn app.main:app --reload` (port 8000)
- Vite proxy config: `/api` → `http://localhost:8000`
- Hot reload on both sides independently

## 6. New Dependencies

**Backend** (requirements.txt additions):
- `python-jose[cryptography]>=3.3.0`
- `passlib[bcrypt]>=1.7.4`
- `cryptography>=42.0.0`

**Frontend** (package.json):
- `react`, `react-dom`, `react-router-dom`
- `antd`, `@ant-design/icons`
- `@tanstack/react-query`
- `zustand`
- `axios`
- `dayjs`
- TypeScript + Vite + related type packages

## 7. Database Migrations

Required Alembic migrations (in order):

1. **Add auth tables**: `refresh_tokens` table
2. **Add notification_events table**
3. **Extend tasks table**: add `name`, `target_url`, `check_interval`, `auto_purchase`, `account_id`, `proxy_id`, `webhook_url`, `last_result`, `last_run_at` columns (all nullable for existing rows)
4. **Add foreign keys**: `accounts.owner_id → users.id`, `proxies.owner_id → users.id`, `tasks.created_by → users.id` (with `ondelete=CASCADE`). For existing rows with NULL owner_id, leave as-is (treated as system-owned legacy resources).
5. **Add indexes**: on `owner_id`, `created_by`, `notification_events.user_id`, `notification_events.created_at`
6. **Encrypt sensitive fields**: migrate plaintext `accounts.password`, `accounts.cookie`, `proxies.password` to encrypted values (requires `ENCRYPTION_KEY` env var)

## 8. Testing Strategy

- **Backend**: pytest for auth endpoints (register, login, refresh, logout, token revocation), ownership enforcement (cross-user access returns 403), pagination, notification history
- **Frontend**: Vitest + React Testing Library for auth flow, task list rendering, form validation, error states
- **Integration**: Manual verification of full flow (login → create task → start monitor → view notification)

## 9. Implementation Order

Phase 1 — Backend foundation (no frontend yet):
1. Auth infrastructure (security.py, auth API, refresh_tokens model)
2. Pydantic schemas for all existing resources
3. Task persistence (extend Task model, refactor registry)
4. Multi-tenant ownership (FK constraints, ownership enforcement)
5. Sensitive data encryption (crypto.py, migration)
6. Notification history (model, API, integration with scheduler)
7. Alembic migrations for all above

Phase 2 — Frontend:
1. Vite + React + Ant Design + TanStack Query setup
2. Auth pages (login, register) + auth store + route guards
3. Monitor tasks page (list, create, start/stop/purchase/check)
4. Account management page
5. Proxy management page
6. Notifications & history page
7. Admin pages (users, all tasks, system status)
8. Docker multi-stage build + FastAPI static file mounting

Phase 3 — Polish:
1. SSE for real-time events (optional, future)
2. Error boundaries, loading states, empty states
3. Mobile-responsive layout
