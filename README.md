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
