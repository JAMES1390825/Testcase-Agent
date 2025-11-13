# 知识库系统配置与使用说明

## 系统架构

本测试用例生成系统已集成**知识库功能**，支持文档上传、向量化存储、语义检索，并在生成测试用例时自动引入相关上下文，大幅提升生成质量和效率。

### 核心组件

1. **PostgreSQL 数据库**：持久化存储文档内容、元数据、向量
2. **Redis 缓存**：缓存生成结果、任务状态
3. **Embedding API**：生成文档向量，支持语义检索
4. **Flask 后端**：REST API + 异步任务处理
5. **前端 UI**：知识库管理、文档上传、选择复用

---

## 环境变量配置

### 1. PostgreSQL 配置（必需）

```bash
export DATABASE_URL="postgresql+psycopg://username:password@host:port/database"
```

**示例：**
- 本地开发：`postgresql+psycopg://postgres:password@localhost:5432/testcase_agent`
- 阿里云 RDS：`postgresql+psycopg://testuser:yourpassword@pgm-xxx.pg.rds.aliyuncs.com:5432/testcase_kb`

**说明：**
- 系统启动时会自动创建所需表（`kb_docs`, `kb_sections`, `uploaded_testcases`, `uploaded_prds`）
- 如果未配置，系统会降级为文件系统存储（`data/`目录下）

---

### 2. Redis 配置（可选但推荐）

```bash
export REDIS_URL="redis://:password@host:port/db"
```

**示例：**
- 本地：`redis://localhost:6379/0`
- 阿里云 Redis：`redis://:yourpassword@r-xxx.redis.rds.aliyuncs.com:6379/0`

**用途：**
- 缓存生成结果（key: `cache:{hash}`）
- 异步任务状态持久化（key: `jobs:{job_id}`）
- 未配置时会使用进程内存存储

---

### 3. Embedding API 配置（必需，用于知识库向量化）

```bash
export EMBEDDING_API_KEY="sk-xxxxxxxxxxxx"
export EMBEDDING_BASE_URL="https://api.openai.com/v1"  # 可选
export EMBEDDING_MODEL="text-embedding-3-small"  # 可选，默认此模型
```

**支持的 Embedding 服务：**
- OpenAI：`text-embedding-3-small` / `text-embedding-3-large`
- Azure OpenAI：配置 `EMBEDDING_BASE_URL` 为 Azure 端点
- 本地模型（LocalAI/Ollama）：配置相应的 base_url

**说明：**
- 如未配置，文档上传不会进行向量化，语义检索功能不可用
- 仅文本内容会被向量化（前8000字符）

---

### 4. 主模型 API 配置（前端配置）

在前端"模型配置"Tab中填写：
- **API Key**：OpenAI/Azure/其他兼容服务的key
- **API Base URL**：留空使用OpenAI默认，或填自定义地址
- **文本模型**：如 `gpt-4-turbo` / `gpt-3.5-turbo`
- **视觉模型**：如 `gpt-4-vision-preview`（可禁用视觉）

---

## 完整启动命令示例

### 本地开发

```bash
# 设置环境变量
export DATABASE_URL="postgresql+psycopg://postgres:password@localhost:5432/testcase_agent"
export REDIS_URL="redis://localhost:6379/0"
export EMBEDDING_API_KEY="sk-your-embedding-key"
export EMBEDDING_MODEL="text-embedding-3-small"

# 安装依赖（如未安装）
pip install -r requirements.txt

# 启动应用
python app.py
```

访问：http://localhost:5001

---

### 生产部署（阿里云）

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

#### 2. 配置环境变量（systemd 或 supervisor）

创建 `/etc/systemd/system/testcase-agent.service`：

```ini
[Unit]
Description=Testcase Agent Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/testcase-agent
Environment="DATABASE_URL=postgresql+psycopg://user:pass@pgm-xxx.pg.rds.aliyuncs.com:5432/testcase_kb"
Environment="REDIS_URL=redis://:pass@r-xxx.redis.rds.aliyuncs.com:6379/0"
Environment="EMBEDDING_API_KEY=sk-your-key"
Environment="EMBEDDING_MODEL=text-embedding-3-small"
ExecStart=/usr/bin/gunicorn --workers 4 --bind 0.0.0.0:5001 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start testcase-agent
sudo systemctl enable testcase-agent
```

#### 3. Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 支持大文件上传
        client_max_body_size 50M;
        proxy_read_timeout 300s;
    }
}
```

---

## 使用流程

### 1. 上传文档到知识库

**前端操作：**
1. 打开"知识库"Tab
2. 选择 `.md` / `.csv` / `.txt` 文件
3. 点击"上传并入库"
4. 系统会自动读取文件内容并生成向量

**后端处理：**
- 文件内容存入 `uploaded_prds` 或 `uploaded_testcases` 表
- 自动调用 Embedding API 生成向量存储
- 支持后续语义检索

---

### 2. 从知识库选择文档生成测试用例

**在"PRD 生成测试用例"Tab：**
1. 点击"旧版PRD"或"新版PRD"输入框旁的"📚 从知识库选择"按钮
2. 在弹窗中选择已上传的PRD文档
3. 点击"生成测试用例"，系统会自动使用选中文档内容

**在"完善测试用例"Tab：**
1. 点击"上传测试用例文档"旁的"📚 从知识库选择"按钮
2. 选择已上传的测试用例文档
3. 点击"完善测试用例"

**优势：**
- 无需重复上传大文件
- 复用已向量化的文档（更快）
- 知识库统一管理，方便版本追溯

---

### 3. 语义检索测试

**前端操作：**
1. 在"知识库"Tab的"语义检索测试"区域
2. 输入查询文本，如"登录功能测试"
3. 点击"🔍 检索"
4. 查看返回的相关文档片段及相似度得分

**后端处理：**
- 查询文本向量化
- 与知识库中所有文档片段计算余弦相似度
- 返回 Top-K 最相关结果

---

## 数据库表结构

### kb_docs
- `doc_id`：文档唯一ID
- `name`：文档名称
- `created_at`：创建时间戳

### kb_sections
- `id`：自增主键
- `doc_id`：关联文档ID
- `idx`：章节顺序
- `title`：章节标题
- `text`：章节文本内容
- `images`：图片URL数组（JSON）
- `embedding`：向量（JSON数组，float列表）

### uploaded_testcases
- `id`：文件ID
- `name`：文件名
- `content`：文件内容
- `content_type`：文件类型（csv/md/txt）
- `embedding`：向量
- `created_at`：上传时间

### uploaded_prds
- `id`：文件ID
- `name`：文件名
- `content`：文件内容
- `file_type`：文件类型（md/csv/txt）
- `embedding`：向量
- `created_at`：上传时间

---

## API 接口清单

### 知识库相关

#### POST /api/uploads/prds
上传PRD文档（multipart/form-data 或 JSON）

**请求：**
- multipart: `file=<文件>`
- JSON: `{"name": "xxx.md", "content": "文本内容"}`

**响应：**
```json
{
  "id": "abc123",
  "name": "prd.md",
  "created_at": 1699999999
}
```

#### GET /api/uploads/prds
列出所有已上传PRD

**响应：**
```json
{
  "items": [
    {"id": "abc123", "name": "prd.md", "created_at": 1699999999, "file_type": "md"}
  ]
}
```

#### GET /api/uploads/prds/{id}
获取单个PRD详情（含完整content）

#### POST /api/uploads/testcases
上传测试用例文档

#### GET /api/uploads/testcases
列出所有已上传测试用例

#### GET /api/uploads/testcases/{id}
获取单个测试用例详情

#### POST /api/kb/search
语义检索知识库

**请求：**
```json
{
  "query": "登录功能",
  "top_k": 5,
  "doc_id": "optional-doc-id"
}
```

**响应：**
```json
{
  "results": [
    {
      "doc_id": "xxx",
      "doc_name": "PRD v1.2",
      "title": "登录模块",
      "text": "文档片段内容...",
      "images": [],
      "similarity": 0.85
    }
  ]
}
```

---

### 测试用例生成相关

#### POST /api/generate
同步生成测试用例

**请求（支持ID引用）：**
```json
{
  "new_prd": "文本内容",
  "old_prd": "旧版文本",
  "new_prd_id": "可选，使用知识库文档ID",
  "old_prd_id": "可选",
  "config": {...}
}
```

#### POST /api/generate_async
异步生成（推荐大批量）

#### POST /api/enhance
同步完善测试用例

**请求（支持ID引用）：**
```json
{
  "test_cases": "现有测试用例内容",
  "test_cases_id": "可选，使用知识库文档ID",
  "config": {...}
}
```

#### POST /api/enhance_async
异步完善

#### GET /api/job_status/{job_id}
查询异步任务状态与进度

---

## 常见问题

### 1. Embedding API 调用失败

**症状：** 上传文档后提示"Failed to embed..."

**排查：**
- 检查 `EMBEDDING_API_KEY` 是否正确
- 检查 `EMBEDDING_BASE_URL` 是否可访问
- 检查模型名称是否正确（`EMBEDDING_MODEL`）
- 查看后端日志中的详细错误

### 2. 知识库检索无结果

**原因：**
- Embedding API 未配置或未成功向量化
- 上传的文档内容与查询不匹配
- 相似度阈值过高

**解决：**
- 确保 `EMBEDDING_API_KEY` 已配置
- 尝试更具体或更相关的查询词
- 检查数据库中 `embedding` 字段是否为 NULL

### 3. 数据库连接失败

**症状：** 启动报错 "DATABASE_URL not configured" 或连接超时

**排查：**
- 检查环境变量是否正确设置
- 测试数据库连通性：`psql $DATABASE_URL`
- 检查防火墙/安全组规则
- 确认数据库用户权限

### 4. Redis 缓存未生效

**症状：** 重复生成相同内容仍需等待

**排查：**
- 检查 `REDIS_URL` 是否配置
- 测试 Redis 连接：`redis-cli -u $REDIS_URL ping`
- 查看后端日志中是否有 Redis 连接错误

---

## 性能优化建议

1. **Embedding 模型选择：**
   - 小型项目：`text-embedding-3-small`（速度快，成本低）
   - 高精度需求：`text-embedding-3-large`

2. **数据库索引：**
   - PostgreSQL 自动为主键和外键创建索引
   - 可为 `created_at` 添加索引提升列表查询速度

3. **Redis 缓存策略：**
   - 缓存过期时间默认24小时
   - 可在 `backend/services/cache.py` 中调整 `ex=60*60*24`

4. **并发控制：**
   - Gunicorn workers 数量建议：`CPU核心数 * 2 + 1`
   - 调整 `MAX_CONCURRENT_MODEL_CALLS` 控制并发模型调用

---

## 联系与支持

- **GitHub Issues**：https://github.com/JAMES1390825/Testcase-Agent/issues
- **文档更新**：本README会随功能迭代持续更新

---

© 2025 Testcase Agent Team
