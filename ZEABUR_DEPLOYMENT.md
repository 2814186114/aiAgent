# Zeabur 部署指南

## 项目架构

本项目已简化为**两层架构**：

```
前端 (Nginx + React)
    ↓
后端 (Python FastAPI)
```

**已删除**：Node.js 中间层（Socket.IO 服务）

---

## 部署方式

### 方式一：使用 Zeabur 模板（推荐）

1. **Fork 本项目到你的 GitHub**

2. **在 Zeabur 上创建新项目**
   - 选择"从 GitHub 导入"
   - 选择你的仓库
   - 选择 `zeabur.json` 作为配置文件

3. **配置环境变量**

   在 Zeabur 控制台为 `python-server` 服务配置以下环境变量：

   | 变量名 | 说明 | 示例值 |
   |--------|------|---------|
   | `LLM_PROVIDER` | LLM 提供商 | `deepseek` 或 `openai` |
   | `DEEPSEEK_API_KEY` | DeepSeek API Key | `sk-xxx` |
   | `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com` |
   | `OPENAI_API_KEY` | OpenAI API Key | `sk-xxx` |
   | `OPENAI_BASE_URL` | OpenAI API 地址 | `https://api.openai.com/v1` |

4. **部署完成**

   Zeabur 会自动：
   - 构建前端（使用 `Dockerfile.frontend`）
   - 构建后端（使用 `Dockerfile.python`）
   - 启动两个服务
   - 自动配置域名和 HTTPS

---

### 方式二：手动部署

#### 1. 部署后端

在 Zeabur 上创建一个服务：

- **服务类型**：Prebuilt Service
- **源码**：选择 GitHub 仓库
- **Dockerfile**：`Dockerfile.python`
- **环境变量**：
  ```
  LLM_PROVIDER=deepseek
  DEEPSEEK_API_KEY=your_api_key
  DEEPSEEK_BASE_URL=https://api.deepseek.com
  ```

部署后，记下后端服务的 URL（例如：`https://your-backend.zeabur.app`）

#### 2. 部署前端

在 Zeabur 上创建另一个服务：

- **服务类型**：Prebuilt Service
- **源码**：选择 GitHub 仓库
- **Dockerfile**：`Dockerfile.frontend`
- **环境变量**：无需额外配置

#### 3. 配置前端连接后端

前端需要知道后端的 WebSocket 地址。修改前端代码：

```typescript
// src/UnifiedAssistant.tsx
const wsUrl = 'wss://your-backend.zeabur.app/ws/chat'
```

或者使用环境变量：

```typescript
const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/chat'
```

然后在 Zeabur 前端服务中添加环境变量：
```
VITE_WS_URL=wss://your-backend.zeabur.app/ws/chat
```

---

### 方式三：使用 Docker Compose（本地测试）

```bash
# 克隆项目
git clone https://github.com/your-username/AgentPaper.git
cd AgentPaper

# 创建 .env 文件
cat > .env << EOF
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
EOF

# 启动服务
docker-compose up -d

# 访问
# 前端：http://localhost
# 后端：http://localhost:8000
```

---

## 文件说明

| 文件 | 用途 |
|------|------|
| `zeabur.json` | Zeabur 模板配置（推荐使用） |
| `docker-compose.yml` | Docker Compose 配置（本地测试） |
| `Dockerfile.python` | Python 后端 Docker 镜像 |
| `Dockerfile.frontend` | 前端 Docker 镜像 |
| `nginx.conf` | Nginx 配置（前端反向代理） |

---

## 常见问题

### 1. WebSocket 连接失败

**问题**：前端无法连接到 WebSocket

**解决**：
- 确保后端服务已启动
- 检查前端配置的 WebSocket URL 是否正确
- Zeabur 上使用 `wss://` 而不是 `ws://`

### 2. API Key 未生效

**问题**：提示"LLM 未配置"

**解决**：
- 检查环境变量是否正确配置
- 确认 API Key 格式正确
- 重启服务

### 3. 前端无法访问后端

**问题**：跨域错误或连接失败

**解决**：
- 检查 `ALLOWED_ORIGINS` 环境变量
- 确保前端和后端在同一个网络中
- 检查 Nginx 配置

### 4. ChromaDB 数据丢失

**问题**：重启后记忆丢失

**解决**：
- 配置持久化存储卷
- Zeabur 上使用 PostgreSQL 或 MySQL 替代 SQLite

---

## 性能优化建议

1. **使用 CDN 加速静态资源**
2. **启用 Gzip 压缩**（已在 nginx.conf 中配置）
3. **配置 WebSocket 心跳检测**
4. **使用 Redis 缓存热点数据**
5. **配置负载均衡**（多实例部署）

---

## 成本估算

| 资源 | Zeabur 价格 |
|--------|-------------|
| 前端（512MB） | ~$0.5/月 |
| 后端（1GB） | ~$2/月 |
| 域名 | 免费（.zeabur.app） |

**总计**：约 $2.5/月

---

## 技术支持

- Zeabur 文档：https://zeabur.com/docs
- 项目 Issues：https://github.com/your-username/AgentPaper/issues
