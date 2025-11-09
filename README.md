# 测试用例生成智能体 (PRD → Test Cases / Multimodal Vision)

> 基于产品需求文档（PRD）自动生成结构化测试用例，支持多模态图片识别的原型项目。

## 📌 项目简介
本项目旨在提升软件测试准备阶段效率：测试/产品/开发仅需上传新版 PRD（或新旧版本差异文档）即可自动获得标准化的测试用例表格，支持增量模式、**多模态图片识别**、导出 CSV、回退模拟。

## ✅ 核心功能
- **全量用例生成**：上传新版 PRD → 生成覆盖所有功能点的测试用例。
- **🆕 多模态图片识别**：自动识别 PRD 中的图片（`![](url)`）并结合文本生成测试用例。
  - 智能分批处理：按章节和图片数量自动拆分，避免 Token 超限
  - 图片预处理：自动下载、压缩、编码，优化模型输入
  - 结果自动合并：多批次结果智能拼接，去重表头
- **增量用例生成**：上传旧版 + 新版 PRD → 只输出新增或修改点的测试用例。
- **Prompt 模板分离**：`prompt_template.md` 与 `prompt_template_diff.md` 支持独立维护和版本对比。
- **表格数据清洗**：统一将多行内容压缩为单行（使用 `；` 分隔），便于前端渲染与 CSV 导出。
- **CSV 导出**：渲染后的 Markdown 表格一键下载，方便导入 Excel / TestRail 等系统。
- **Mock 回退**：缺少 API Key 时使用本地示例输出，不阻塞前端演示。
- **健康检查**：`/api/health` 返回模型配置与开关状态。

## 🧱 技术栈
| 层级 | 技术 | 用途 |
| --- | --- | --- |
| 后端 | Flask | 提供 API 路由与模型调用封装 |
| AI 接入 | openai (兼容 API) | 调用大语言模型生成用例 |
| 图片处理 | Pillow | 图片下载、压缩、编码 |
| 配置 | python-dotenv | 环境变量加载与开关控制 |
| 前端 | 原生 HTML/CSS/JS + marked.js | 文件上传、模式识别、Markdown 渲染 |
| 数据格式 | Markdown / JSON / CSV | 用例展示与导出 |

## 🚀 快速开始
### 1. 克隆仓库
```bash
git clone <repo-url>
cd Testcase\ Agent
```

### 2. 创建并编辑环境变量文件
复制 `.env.example` 为 `.env` 并填写：
```bash
cp .env.example .env
```
示例内容：
```env
OPENAI_API_KEY=sk-xxxxx            # 必填，若为空则使用 Mock 输出
OPENAI_BASE_URL=                   # 可选：自定义兼容服务地址
TEXT_MODEL_NAME=gpt-4o             # 文本模型
VISION_MODEL_NAME=gpt-4o           # 视觉模型（当前未启用）
DISABLE_VISION=1                   # 1=禁用视觉；0=启用（需后续扩展）
MODEL_NAME=                        # 保底兼容字段（若未指定单独模型名）
```

### 3. 安装依赖
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. 启动服务
```bash
python3 app.py
```
访问：`http://localhost:5001`

### 5. 使用方式
1. 仅上传“新版 PRD” → 自动进入全量模式。
2. 同时上传“旧版 + 新版 PRD” → 自动进入增量模式。
3. 等待生成结果 → 页面展示 Markdown 表格 → 可点击“导出为 CSV”。
4. 若无 API Key：页面仍可显示 Mock 示例（来自 `sample_output.md`）。

## 🛠 目录结构
```
app.py                  # Flask 后端主程序
index.html              # 前端主页面
script.js               # 前端交互逻辑（上传、调用、渲染、导出）
style.css               # 样式
prompt_template.md      # 全量用例生成 Prompt 模板
prompt_template_diff.md # 增量用例生成 Prompt 模板
sample_output.md        # Mock 回退示例输出
requirements.txt        # Python 依赖声明
README.md               # 项目说明文档
.env.example            # 环境变量模板
```

## 📡 API 说明
### `POST /api/generate`
| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `new_prd` | string | 是 | 新版 PRD 文本内容 |
| `old_prd` | string | 否 | 旧版 PRD 文本内容（存在则为增量模式） |

返回：
```json
{
  "test_cases": "| 用例ID | ...",      // Markdown 表格原文
  "meta": {
    "mode": "full-text-fallback | incremental",
    "model_used": "gpt-4o",
    "use_vision": false
  }
}
```

### `GET /api/health`
返回模型配置与开关：
```json
{
  "status": "ok",
  "base_url": "openai-default",
  "text_model": "gpt-4o",
  "api_key_present": true,
  "vision_disabled": true
}
```

## 🔐 环境变量说明
| 变量 | 作用 | 备注 |
| --- | --- | --- |
| `OPENAI_API_KEY` | 模型调用密钥 | 为空则走 Mock |
| `OPENAI_BASE_URL` | 自定义服务地址 | 可接代理或第三方兼容接口 |
| `TEXT_MODEL_NAME` | 文本模型名称 | 用于纯文本和增量模式 |
| `VISION_MODEL_NAME` | 视觉模型名称 | 用于多模态图片识别（需支持 Vision） |
| `MODEL_NAME` | 统一模型兜底 | 当未指定单独文本/视觉模型生效 |
| `DISABLE_VISION` | 是否禁用视觉 | 1=只文本（默认）；0=启用多模态 |
| `MAX_IMAGES_PER_BATCH` | 单批最多图片数 | 默认 10，避免 Token 超限 |
| `IMAGE_MAX_SIZE` | 图片压缩尺寸 | 默认 1024 像素 |
| `IMAGE_QUALITY` | JPEG 压缩质量 | 默认 85 (0-100) |
| `MAX_SECTION_CHARS` | 单章节字符上限 | 默认 60000 |

## 🖼️ 多模态使用说明
### 启用多模态图片识别
1. 在 `.env` 文件中设置：
   ```env
   DISABLE_VISION=0
   VISION_MODEL_NAME=gpt-4o-vision  # 或其他支持 Vision 的模型
   ```
2. 上传包含图片的 PRD（Markdown 格式，图片使用 `![](url)` 语法）
3. 系统自动：
   - 按章节解析 PRD 结构
   - 提取图片并建立文本-图片映射
   - 智能分批（避免单次请求图片过多）
   - 下载图片、压缩、编码为 base64
   - 调用视觉模型生成用例
   - 自动合并多批次结果

### 工作流程示例
```
PRD 输入（含 20 张图片）
    ↓
按章节解析（5 个章节）
    ↓
智能分批（每批最多 10 张图片）
    - 批次 1：章节 1-3（8 张图片）
    - 批次 2：章节 4-5（12 张图片 → 自动拆分）
    ↓
并行/串行调用视觉模型
    ↓
合并结果 + 去重表头
    ↓
返回完整测试用例表格
```

## 🧪 用例生成规则（后端约束）
- 表格首行必须是 `| 用例ID |`。
- 单元格内容全部单行；多项用 `；` 分隔。
- 用例 ID 规范：`TC-[模块]-[功能]-[序号]`。
- 不允许生成与 PRD 无关的抽象或凭空补充的场景。

## 🧩 典型扩展路线图
| 阶段 | 目标 | 说明 |
| --- | --- | --- |
| 短期 | 长文档分片与合并 | 减少超 Token 失败；并行分段汇总测试点 |
| 中期 | 多模态图片解析 | 抓取 PRD 中 `![](url)` 图片并传入视觉模型 |
| 中期 | 结构化 JSON 输出 | 后端解析 Markdown → JSON 列表（便于入库） |
| 中期 | 缓存与复用 | 对相同文档内容做结果缓存 |
| 长期 | 鉴权与速率限制 | 防止滥用与成本失控 |
| 长期 | 测试管理平台对接 | 推送到内部 TestCase 管理系统 |

## ⚠️ 常见问题 (FAQ)
| 问题 | 说明 |
| --- | --- |
| 返回为空表格？ | 检查是否传入 `new_prd`；或增量模式下差异检测结果为空。 |
| CSV 导出错位？ | 可能模型返回了多行单元格，确认 `_sanitize_table_rows` 是否生效。 |
| 模型未调用而出现示例？ | 未配置 `OPENAI_API_KEY`，处于 Mock 回退。 |
| 视觉模型未启用？ | 默认 `DISABLE_VISION=1`，需手动改为 `0` 后再扩展图片处理代码。 |

## 🛡 安全与合规（未来）
- 计划增加：请求签名、速率限制、异常分级、敏感信息过滤、模型响应校验。
- 视觉模式启用后需注意外链图片下载的时效与隐私合规。

## 🧭 贡献指南
欢迎提出 Issue / PR：
1. Fork 仓库
2. 创建分支：`feature/<name>`
3. 提交并发起 PR，描述修改目的与影响

## 📜 许可证
暂未指定，可在根目录新增 `LICENSE` 文件（推荐 MIT 或 Apache-2.0）。

## 🏁 总结
该项目聚焦将“文档 → 可执行测试资产”流程自动化，当前处于快速验证阶段。后续通过增强差异检测、结构化输出、视觉理解与其他扩展功能，可逐步演进为测试准备协作平台。

---
