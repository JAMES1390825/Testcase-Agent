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
