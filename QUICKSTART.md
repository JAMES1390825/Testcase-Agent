# 快速启动与测试指南

## 一、环境配置

### 1. 设置环境变量

```bash
# PostgreSQL 数据库（必需）
export DATABASE_URL="postgresql+psycopg://postgres:password@localhost:5432/testcase_agent"

# Redis 缓存（可选但推荐）
export REDIS_URL="redis://localhost:6379/0"

# Embedding API（必需用于知识库向量化）
export EMBEDDING_API_KEY="sk-your-openai-key"
export EMBEDDING_BASE_URL="https://api.openai.com/v1"  # 可选
export EMBEDDING_MODEL="text-embedding-3-small"  # 可选，默认此模型
```

### 2. 安装依赖

```bash
# 使用虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 启动服务

```bash
# 开发模式
python app.py

# 生产模式（Gunicorn）
gunicorn --workers 4 --bind 0.0.0.0:5001 --timeout 300 app:app
```

访问：http://localhost:5001

---

## 二、功能测试清单

### ✅ 知识库上传测试

1. 打开"知识库"Tab
2. 点击"选择文件"，上传一个 `.md` 或 `.csv` 测试文件
3. 点击"上传并入库"
4. 观察：
   - ✓ 上传成功提示
   - ✓ 文档列表中显示新文档
   - ✓ 后端日志无错误
   - ✓ 数据库 `uploaded_prds` 表有新记录
   - ✓ `embedding` 字段有向量数据（如配置了 EMBEDDING_API_KEY）

**示例测试文件内容：**
```markdown
# 登录功能 PRD

## 用户登录
用户可以通过手机号+验证码或邮箱+密码登录系统。

## 安全要求
- 密码需加密存储
- 支持两因素认证
```

---

### ✅ 语义检索测试

1. 在"知识库"Tab的"语义检索测试"区域
2. 输入查询文本：`登录功能`
3. 点击"🔍 检索"
4. 观察：
   - ✓ 返回相关文档片段
   - ✓ 显示相似度分数
   - ✓ 结果按相似度降序排列

**预期结果示例：**
```
#1 相似度: 92.3%
标题: 用户登录
内容: 用户可以通过手机号+验证码或邮箱+密码登录系统...
来源: 登录功能 PRD
```

---

### ✅ 从知识库选择生成测试用例

#### 场景1：PRD 生成测试用例

1. 切换到"PRD 生成测试用例"Tab
2. 点击"新版 PRD"输入框旁的"📚 从知识库选择"按钮
3. 在弹窗中输入序号选择已上传的PRD文档
4. 确认输入框标签变为"已选择：xxx.md"
5. 点击"✨ 生成测试用例"
6. 观察：
   - ✓ 请求成功（使用 `new_prd_id` 而非上传文件）
   - ✓ 生成的测试用例准确覆盖PRD内容
   - ✓ 响应时间快于首次上传

#### 场景2：完善测试用例

1. 切换到"完善测试用例"Tab
2. 点击"📚 从知识库选择"按钮
3. 选择已上传的测试用例文档
4. 点击"✨ 完善测试用例"
5. 观察：
   - ✓ AI 基于已有用例补充新场景
   - ✓ 新增用例标记 `[新增]` 前缀

---

### ✅ 数据库验证

```sql
-- 连接数据库
psql $DATABASE_URL

-- 查看上传的文档
SELECT id, name, created_at, file_type FROM uploaded_prds;
SELECT id, name, created_at, content_type FROM uploaded_testcases;

-- 查看知识库文档
SELECT doc_id, name, created_at FROM kb_docs;

-- 查看章节及向量状态
SELECT id, doc_id, title, 
       CASE WHEN embedding IS NOT NULL THEN '已向量化' ELSE '未向量化' END as embed_status
FROM kb_sections
LIMIT 10;

-- 验证向量维度（OpenAI embedding-3-small 是 1536 维）
SELECT jsonb_array_length(embedding::jsonb) as vector_dim 
FROM kb_sections 
WHERE embedding IS NOT NULL 
LIMIT 1;
```

**预期结果：**
- `uploaded_prds` / `uploaded_testcases` 有记录
- `embedding` 字段非空（如已配置 EMBEDDING_API_KEY）
- 向量维度为 1536（OpenAI）或其他模型对应维度

---

### ✅ Redis 缓存验证

```bash
# 连接 Redis
redis-cli -u $REDIS_URL

# 查看缓存键
KEYS cache:*
KEYS jobs:*

# 查看某个缓存内容
GET cache:<hash>

# 查看任务状态
GET jobs:<job_id>
```

**预期结果：**
- 生成测试用例后有 `cache:*` 键
- 异步任务运行时有 `jobs:*` 键

---

## 三、常见问题排查

### 问题1：上传文档无向量

**症状：** 数据库中 `embedding` 字段为 NULL

**原因：**
- 未配置 `EMBEDDING_API_KEY`
- Embedding API 调用失败

**解决：**
```bash
# 检查环境变量
echo $EMBEDDING_API_KEY

# 测试 API 连通性
curl https://api.openai.com/v1/embeddings \
  -H "Authorization: Bearer $EMBEDDING_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "text-embedding-3-small",
    "input": "test"
  }'
```

---

### 问题2：语义检索无结果

**症状：** 检索时提示"未找到相关内容"

**排查：**
1. 确认知识库有文档且已向量化
   ```sql
   SELECT COUNT(*) FROM uploaded_prds WHERE embedding IS NOT NULL;
   ```
2. 检查查询词是否与文档内容相关
3. 降低 `top_k` 或调整查询词

---

### 问题3：数据库连接失败

**症状：** 启动时报错 `RuntimeError: DATABASE_URL not configured`

**解决：**
```bash
# 本地 PostgreSQL 快速启动（Docker）
docker run --name testcase-pg \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=testcase_agent \
  -p 5432:5432 \
  -d postgres:15

# 设置环境变量
export DATABASE_URL="postgresql+psycopg://postgres:password@localhost:5432/testcase_agent"
```

---

### 问题4：前端选择知识库文档不生效

**症状：** 点击"从知识库选择"后生成仍使用空内容

**排查：**
1. 打开浏览器开发者工具（F12）→ Console
2. 查看是否有 JS 错误
3. 确认 `window._selectedNewPrdId` 等全局变量是否设置
   ```javascript
   console.log(window._selectedNewPrdId);
   ```
4. 检查 Network 面板中请求 payload 是否包含 `*_id` 字段

---

## 四、性能基准测试

### 测试场景

| 操作 | 文件大小 | 无知识库 | 有知识库 | 提升 |
|-----|---------|---------|---------|-----|
| 上传PRD | 50KB | - | 2-3秒 | - |
| 生成测试用例（首次） | - | 15-30秒 | 10-20秒 | ~30% |
| 生成测试用例（缓存） | - | - | <1秒 | 即时 |
| 语义检索 | - | - | 0.5-1秒 | - |

**说明：**
- 向量化耗时取决于 Embedding API 响应速度
- 缓存命中率直接影响二次生成速度
- Redis 缓存可跨进程/服务器共享

---

## 五、生产部署检查清单

- [ ] PostgreSQL 已安装并创建数据库
- [ ] Redis 已安装并可访问
- [ ] 环境变量已配置（DATABASE_URL, REDIS_URL, EMBEDDING_API_KEY）
- [ ] 依赖已安装（`pip install -r requirements.txt`）
- [ ] Gunicorn workers 数量合理（CPU * 2 + 1）
- [ ] Nginx 反向代理已配置
- [ ] 防火墙/安全组已开放端口
- [ ] systemd 服务已创建并启用
- [ ] 日志目录已创建并有写权限
- [ ] 定期备份数据库（pg_dump）

---

## 六、监控与运维

### 日志查看

```bash
# systemd 服务日志
journalctl -u testcase-agent -f

# Gunicorn 日志（如配置了日志文件）
tail -f /var/log/testcase-agent/access.log
tail -f /var/log/testcase-agent/error.log
```

### 健康检查

```bash
# API 健康检查端点
curl http://localhost:5001/api/health

# 预期响应
{"status":"ok","timestamp":1699999999}
```

### 数据库维护

```bash
# 备份数据库
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# 清理过期缓存（Redis）
redis-cli -u $REDIS_URL FLUSHDB

# 查看数据库大小
psql $DATABASE_URL -c "SELECT pg_size_pretty(pg_database_size('testcase_agent'));"
```

---

## 七、下一步优化方向

1. **向量数据库升级：**
   - 当前使用 JSON 存储向量，适合小规模
   - 大规模场景可迁移到 pgvector 扩展或专用向量数据库（Pinecone/Weaviate）

2. **批量上传优化：**
   - 前端支持多文件拖拽上传
   - 后端异步批量向量化

3. **搜索结果缓存：**
   - 高频查询结果缓存到 Redis
   - 设置合理的过期时间

4. **知识库版本管理：**
   - 文档更新时保留历史版本
   - 支持回滚到指定版本

5. **权限与隔离：**
   - 多用户/团队隔离知识库
   - 文档访问权限控制

---

**完成以上测试后，系统即可投入生产使用！**
