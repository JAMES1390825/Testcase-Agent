<<<<<<< HEAD
# Testcase Agent

一个基于 Flask 的“PRD → 测试用例”智能体，支持全量/增量生成、用例完善、图文多模态解析、并发批处理、结果自动修复与缓存，并提供前端可视化界面与阿里云一键部署模板。

## 功能特性
- 全量/增量生成测试用例：根据新版/旧版 PRD 自动生成完整或差异用例
- 用例完善：对现有用例进行场景补充、异常覆盖与步骤/期望优化
- 多模态：自动识别 PRD 中的图片链接并纳入生成（可关闭）
- 并发与限流：批次并发、图片并发、全局模型调用限流
- 结果鲁棒：严格 CSV 校验的“自动修复”策略；现已默认“宽松模式”（不再因非标准 CSV 报错）
- 进度与 ETA：异步生成接口，前端显示批次进度和预计剩余时间
- 缓存：相同 PRD+配置命中缓存直接返回结果
- 部署模板：内置 Nginx + Gunicorn systemd 与 Docker 可选方案

## 目录结构（核心）
```
backend/
	__init__.py             # Flask 应用工厂
	config.py               # 配置与默认值（并发、图片处理、限流等）
	routes/
		__init__.py
		generate.py           # 生成测试用例（全量/增量/多模态），并发批处理、降级与缓存
		enhance.py            # 完善测试用例
		health.py             # 健康检查
		jobs.py               # 异步任务：/api/generate_async、/api/job_status
	services/
		client_factory.py     # OpenAI 兼容客户端 + 全局速率限制器
		parsing.py            # PRD 解析与分批（严格图片上限）
		postprocess.py        # CSV 合并、严格校验、自动修复
		vision.py             # 图片下载/压缩 + 并发
		prompts.py            # Prompt 加载
		cache.py              # 简单内存缓存
		jobs.py               # 异步任务执行器（进度/ETA/缓存）
frontend（静态根）
	index.html
	script.js
	style.css
app.py                    # 本地开发入口（threaded=True）
requirements.txt
prompt_template.md / prompt_template_diff.md
```

## 快速开始（本地）
1. 安装依赖
```
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -r requirements.txt
```
2. 运行
```
python3 app.py
# 浏览器访问 http://localhost:5001
```

## 重要配置
前端“模型配置”面板可直接填写并持久化（保存在浏览器）：
- API Key / Base URL / 文本模型 / 视觉模型
- 禁用图片识别（仅文本）
- 每批最大图片数、图片压缩尺寸与质量、章节字符上限
- 并发：
	- 批次并发数（batch_inference_concurrency）：默认 2（建议 2–4）
	- 图片下载并发数（image_download_concurrency）：默认 4（建议 4–8）

后端全局限流（环境变量，可选）：
- MAX_CONCURRENT_MODEL_CALLS：默认 3（小机建议 2）
- MIN_CALL_INTERVAL_MS：默认 0（如遇 429 可设 50–100）

CSV 输出策略：
- 已启用“宽松模式”。若模型输出非标准 CSV，会尝试自动修复；修复失败也直接返回原始内容，不再 500 拦截。

## API（节选）
- POST /api/generate：同步生成（仍集成缓存）
- POST /api/generate_async：启动异步生成任务（命中缓存直接返回）
- GET  /api/job_status/<job_id>：轮询任务状态，包含 progress 和 eta_seconds
- POST /api/enhance：完善测试用例
- GET  /api/health：健康检查

## 生产部署
推荐使用 Nginx + Gunicorn（仅对内 127.0.0.1:5001），外层 Nginx 提供静态资源与 /api 反代。
- 部署文档：deploy/README_ALIYUN.md（含阿里云示例）
- systemd 模板：deploy/systemd/testcase-agent.service
- Nginx 模板：deploy/nginx/testcase-agent.conf

## 性能建议（2C2G 机器）
- MAX_CONCURRENT_MODEL_CALLS=2
- 批次并发=2、图片并发=3–4
- 图片尺寸 640–768、质量 65–75、每批图片 6–8

## 常见问题
- 429/限流：降低 MAX_CONCURRENT_MODEL_CALLS 或增加 MIN_CALL_INTERVAL_MS
- 图片加载慢：调低图片尺寸/质量、降低图片并发；确保服务器到图片源站的网络畅通
- 输出杂乱：宽松模式仍会回传，但可在前端导出后自行清洗；或再切回严格校验

## 许可证
当前项目用于内部验证与演示，许可证待定。
=======
# 测试用例生成器

> 上传 PRD 文档，AI 自动生成测试用例表格。支持图片识别，一键导出 CSV。

## 这个工具能做什么？

📄 **自动生成测试用例**
- 上传产品需求文档（PRD），AI 自动生成结构化的测试用例表格
- 支持全量生成（完整文档）和增量生成（只看改动部分）

🖼️ **识别文档中的图片**
- PRD 里的流程图、原型图、UI 截图都能识别
- AI 会结合图片和文字内容生成更准确的测试用例

📊 **导出和使用**
- 一键导出 CSV 文件
- 可以直接导入 Excel、TestRail 等测试管理工具

## 功能清单

✅ 支持 Markdown 格式的 PRD 文档  
✅ 全量模式：上传新 PRD → 生成完整测试用例  
✅ 增量模式：上传新旧 PRD → 只生成变化部分的用例  
✅ 图片识别：自动识别文档中的图片（`![图片](url)` 格式）  
✅ 智能分批：文档太大或图片太多时自动分批处理  
✅ CSV 导出：生成的表格可直接下载为 CSV 格式  
✅ 多模型支持：Sealos AI Proxy、OpenAI、DeepSeek 等

## 快速开始

### 第一步：下载项目
```bash
git clone https://github.com/JAMES1390825/Testcase-Agent.git
cd Testcase-Agent
```

### 第二步：安装依赖
```bash
pip install -r requirements.txt
```

### 第三步：配置 AI 模型

复制配置文件：
```bash
cp .env.example .env
```

然后编辑 `.env` 文件，选择以下任一方案：

#### 🌟 方案一：Sealos AI Proxy

**优点：** 无需 OpenAI 账号，国内可用，按量付费

1. 访问 [Sealos Cloud](https://cloud.sealos.run/) 注册账号
2. 打开「AI Proxy」应用
3. 点击「新建」创建 API Key
4. 配置文件：

```env
OPENAI_API_KEY=sk-xxxxx                              # 粘贴你的 Sealos Key
OPENAI_BASE_URL=https://aiproxy.hzh.sealos.run/v1/

TEXT_MODEL_NAME=
VISION_MODEL_NAME=

DISABLE_VISION=0                  # 0=开启图片识别
```

#### 方案二：OpenAI 官方

**需要：** OpenAI 账号 + API Key

```env
OPENAI_API_KEY=sk-xxxxx           # 你的 OpenAI Key
OPENAI_BASE_URL=                  # 留空

TEXT_MODEL_NAME=
VISION_MODEL_NAME=

DISABLE_VISION=0
```

#### 方案三：DeepSeek（经济实惠）

**优点：** 价格便宜，中文友好

```env
OPENAI_API_KEY=sk-xxxxx
OPENAI_BASE_URL=https://api.deepseek.com/v1/

TEXT_MODEL_NAME=
VISION_MODEL_NAME=

DISABLE_VISION=0
```

### 第四步：启动服务
```bash
python3 app.py
```

浏览器打开：http://localhost:5001

## 使用方法

### 全量生成
1. 点击「新版 PRD」上传你的需求文档
2. 点击「生成测试用例」
3. 等待几秒，测试用例表格就生成了
4. 点击「导出为 CSV」保存

### 增量生成
1. 上传「旧版 PRD」和「新版 PRD」
2. 点击「生成测试用例」
3. 只会生成变化部分的测试用例

### 图片识别功能
- 确保 `.env` 中 `DISABLE_VISION=0`
- 使用支持图片的模型（如 `gpt-4o`）
- PRD 中的图片用 Markdown 格式：`![描述](图片链接)`
- 系统会自动识别图片并生成相关测试用例

## 配置说明

### 主要环境变量

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `OPENAI_API_KEY` | AI 服务的密钥 | `sk-xxxxx` |
| `OPENAI_BASE_URL` | API 服务地址 | Sealos: `https://aiproxy.hzh.sealos.run/v1/`<br>DeepSeek: `https://api.deepseek.com/v1/`<br>OpenAI: 留空 |
| `TEXT_MODEL_NAME` | 文本模型名称 | `Doubao-lite-4k`、`gpt-4o` |
| `VISION_MODEL_NAME` | 图片识别模型 | `gpt-4o`、`claude-3-sonnet` |
| `DISABLE_VISION` | 是否关闭图片识别 | `0`=开启，`1`=关闭 |

### 高级参数（可选）

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `MAX_IMAGES_PER_BATCH` | 单批最多处理多少张图片 | 10 |
| `IMAGE_MAX_SIZE` | 图片压缩尺寸（像素） | 1024 |
| `IMAGE_QUALITY` | 图片压缩质量 | 85 |
| `MAX_SECTION_CHARS` | 单章节最大字符数 | 60000 |

## 常见问题

### 没有 API Key 怎么办？
- 工具会使用内置的示例数据进行演示
- 但无法生成真实的测试用例
- 建议使用 Sealos（免费注册，按量付费）

### 提示"Model Not Exist"错误？
检查模型名称是否正确：
- Sealos：`Doubao-lite-4k`、`gpt-4o`
- DeepSeek：`deepseek-chat`、`deepseek-reasoner`
- OpenAI：`gpt-4o`、`gpt-4o-mini`

### API 调用失败？
1. 检查 API Key 是否正确
2. 确认账户余额充足
3. 验证 `OPENAI_BASE_URL` 格式（末尾要有 `/v1/`）

### 图片识别不工作？
1. 确认 `DISABLE_VISION=0`（开启）
2. 使用支持图片的模型（如 `gpt-4o`）
3. 检查图片链接是否可访问
4. 确认 PRD 中图片格式为 `![描述](链接)`

### Sealos 如何充值？
登录 [Sealos Cloud](https://cloud.sealos.run/) → 费用中心 → 充值

## 项目结构

```
Testcase-Agent/
├── app.py                    # 后端服务（Flask）
├── index.html                # 网页界面
├── script.js                 # 前端逻辑
├── style.css                 # 页面样式
├── prompt_template.md        # 全量生成提示词
├── prompt_template_diff.md   # 增量生成提示词
├── requirements.txt          # Python 依赖
├── .env                      # 配置文件（需自己创建）
├── .env.example              # 配置模板
└── README.md                 # 项目说明
```

## 技术栈

- **后端：** Flask + Python
- **AI 接入：** OpenAI SDK（兼容多种 AI 服务）
- **图片处理：** Pillow
- **前端：** HTML + JavaScript + marked.js


**需要帮助？** 
- 提交问题：[GitHub Issues](https://github.com/JAMES1390825/Testcase-Agent/issues)
>>>>>>> f156254110d35ad82e816a0657c10b05407536e7
