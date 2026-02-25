# 上线前修复路径（Pre-Launch Fix Plan）v2

**范围说明**
本文档覆盖当前代码库上线前需要改进的全部问题、修复优先级、改动范围与验收标准。

---

## 批次一：修复 401 认证不可用（阻断性 Bug）✅ 已完成

### 根因分析

认证流程：用户登录 → 服务端 `Set-Cookie: access_token`（HttpOnly）→ 前端 `credentials: 'include'` → 浏览器携带 Cookie → 服务端 `verify_token()` 读取 Cookie。

**断裂点：**
1. `server.py:92` — `CORS_ORIGINS` 默认值为 `"*"`
2. `server.py:276` — `allow_credentials = True if CORS_ORIGINS != ["*"] else False`
3. 当 `CORS_ORIGINS=*` 时 `allow_credentials=False`，浏览器不发送 Cookie
4. `auth.py:84` — Cookie 为空 → 401 "未提供认证令牌"

### 修复清单

| # | 文件 | 修改内容 | 状态 |
|---|------|----------|------|
| 1.1 | `server.py` | CORS 默认值改为本地前端地址列表；始终 `allow_credentials=True`；`allow_headers` 增加 `Authorization` | ✅ |
| 1.2 | `frontend/src/App.jsx` | 新增 `getAuthHeaders()` 工具函数，所有 6 处 fetch 请求增加 `Authorization: Bearer <token>` 头 | ✅ |
| 1.2b | `frontend/src/components/LoginPage.jsx` | 登录/注册成功后将 token 保存到 `localStorage('decopilot_token')` | ✅ |
| 1.3 | `backend/api/middleware/auth.py` | `verify_token` 增加 logger，记录认证来源（Header/Cookie）和结果 | ✅ |

---

## 批次二：安全加固 ✅ 已完成

| # | 问题 | 文件 | 修改内容 | 状态 |
|---|------|------|----------|------|
| 2.1 | JWT 弱默认密钥 | `config_data.py` | 生产环境启动时校验密钥长度 ≥ 32 且非默认值，否则 `raise RuntimeError` | ✅ |
| 2.2 | DEBUG 默认开启 | `server.py` | 默认值改为 `"false"` | ✅ |
| 2.3 | 开发旁路泄漏 | `auth.py` | `_ensure_jwt_ready()` 在生产环境检测到 `ALLOW_DEV_AUTH_BYPASS=true` 时记录警告并忽略 | ✅ |
| 2.4 | CORS 通配符 | `server.py` | 生产环境未配置 CORS 时仅允许同源并记录警告 | ✅ |
| 2.5 | 输入无约束 | `chat.py` | `ChatRequest.message` 增加 `Field(min_length=1, max_length=5000)`；`session_id` 增加正则校验；`user_type` 增加枚举约束 | ✅ |
| 2.6 | 文件上传无类型校验 | `chat.py` | 新增 `ALLOWED_UPLOAD_EXTENSIONS` 白名单，`_read_upload_with_limit` 增加扩展名校验 | ✅ |
| 2.7 | Docker root 运行 | `Dockerfile` | 创建 `appuser` 非特权用户，`chown` 后 `USER appuser` | ✅ |

---

## 批次三：稳定性修复 ✅ 已完成

| # | 问题 | 文件 | 修改内容 | 状态 |
|---|------|------|----------|------|
| 3.1 | 流式响应无超时 | `server.py`, `chat.py` | 所有流式生成器增加 `asyncio.timeout(120)`，超时返回 `TIMEOUT_ERROR` | ✅ |
| 3.2 | 健康检查是假的 | `server.py` | `/health` 检查 ChromaDB heartbeat + DashScope Key 配置状态，不健康时返回 503 | ✅ |
| 3.3 | 安全响应头缺失 | `server.py` | 新增 `security_headers_middleware`：X-Content-Type-Options / X-Frame-Options / X-XSS-Protection / Referrer-Policy；生产环境额外添加 HSTS + CSP | ✅ |

---

## 批次四：代码质量 ✅ 已完成

| # | 问题 | 文件 | 修改内容 | 状态 |
|---|------|------|----------|------|
| 4.1 | 未使用 `import base64` | `chat.py` | 已删除，替换为 `import asyncio` | ✅ |

---

## 变更文件清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `server.py` | 修改 | CORS 配置重写；DEBUG 默认值；安全响应头中间件；流式超时；健康检查增强 |
| `config_data.py` | 修改 | 生产环境启动校验（JWT 密钥 + DashScope Key） |
| `backend/api/middleware/auth.py` | 修改 | 日志系统；verify_token 重构（Header 优先 + Cookie 备用）；生产旁路保护 |
| `backend/api/routes/chat.py` | 修改 | 输入验证增强；文件类型白名单；流式超时；删除未用 import |
| `frontend/src/App.jsx` | 修改 | `getAuthHeaders()` 工具函数；所有 fetch 增加 Authorization 头 |
| `frontend/src/components/LoginPage.jsx` | 修改 | 登录后保存 token 到 localStorage |
| `Dockerfile` | 修改 | 非 root 用户运行 |
| `docs/PRELAUNCH_FIX_PLAN.md` | 修改 | 本文档 |

---

## 验证方法

1. 启动后端 `python server.py` — 无报错
2. 启动前端 `cd frontend && npm run dev` — 无报错
3. 注册新用户 → 登录 → 发送消息 → 无 401
4. `GET /health` → 返回 `checks` 字段含 `chromadb` 和 `dashscope_key` 状态
5. 检查响应头包含 `X-Content-Type-Options: nosniff` 等安全头
6. 发送超长消息（>5000 字符）→ 返回 422
7. 上传 `.exe` 文件 → 返回 400

---

## 后续优化（上线后持续推进）

| 优先级 | 问题 | 建议 |
|--------|------|------|
| P1 | `threading.local` 在 async 中不安全 | 改用 `contextvars.ContextVar` |
| P1 | 用户数据明文存储 | `cryptography.Fernet` 加密 |
| P2 | 全局单例 + 懒加载 | 依赖注入容器 |
| P2 | EnhancedAgent God Class | 拆分为组合模式 |
| P2 | 缺少可观测性 | Prometheus + Grafana + 请求 ID 全链路 |
| P2 | 无数据库迁移 | Alembic |
| P3 | 前端 App.jsx 900+ 行 | 组件拆分 + Zustand + TypeScript |
| P3 | LLM 供应商硬编码 | 抽象层支持多供应商 |
