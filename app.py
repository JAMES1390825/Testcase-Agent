import os
import re
import requests
import base64
import time
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

# --- 初始化与配置 ---

DISABLE_VISION = os.getenv("DISABLE_VISION", "1") == "1"  # 回退：1 时完全禁用图片理解（默认开启）

def _sanitize_table_rows(markdown_text: str) -> str:
    """
    强制表格行为单行格式：
    - 将单元格内的换行符替换为中文分号"；"
    - 移除多余空白，确保表格整洁
    """
    lines = []
    for line in markdown_text.splitlines():
        if line.strip().startswith('|'):
            # 表格行：替换单元格内换行为分号
            cells = line.split('|')
            sanitized_cells = []
            for cell in cells:
                # 移除单元格内的换行和多余空格
                clean_cell = cell.replace('\n', '；').replace('\r', '').strip()
                # 压缩连续空格
                clean_cell = ' '.join(clean_cell.split())
                sanitized_cells.append(clean_cell)
            lines.append('|'.join(sanitized_cells))
        else:
            lines.append(line)
    return '\n'.join(lines)

def _merge_markdown_tables(responses):
    """将多段Markdown（可能各自包含表头）合并为一段：仅保留第一段的表头。
    格式保守：
      - 严格以 "|" 开头的行才视为表格行；
      - 仅在首次遇到分隔行时记录表头上一行与分隔行；
      - 过滤掉后续批次的表头、空标题行与空白行。
    """
    combined_lines = []
    header_seen = False
    sep_seen = False
    for chunk in responses:
        if not chunk:
            continue
        lines = chunk.splitlines()
        for i, line in enumerate(lines):
            # 仅处理表格相关行，其他直接跳过，避免把说明文字混入表格导致样式错乱
            if not line.strip().startswith('|'):
                continue
            is_sep = ('|' in line and ('---' in line or '—' in line))
            if not header_seen and is_sep:
                # 收集表头（上一行）与分隔行
                if i-1 >= 0 and lines[i-1].strip().startswith('|'):
                    combined_lines.append(lines[i-1])
                combined_lines.append(line)
                header_seen = True
                sep_seen = True
                continue
            if header_seen and sep_seen and is_sep:
                # 跳过后续批次的分隔行
                continue
            # 普通数据行
            combined_lines.append(line)
        # 不再追加段落空行，保持表格连续
    return "\n".join(combined_lines).strip()

def _call_model_with_retries(model_name, messages, max_retries=2, backoff_base=0.6):
    """带重试和指数退避的模型调用。"""
    attempt = 0
    delay = backoff_base
    last_err = None
    while attempt <= max_retries:
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=4096
            )
            return completion.choices[0].message.content
        except Exception as e:
            last_err = e
            if attempt == max_retries:
                break
            sleep_for = delay * (2 ** attempt)
            print(f"模型调用失败（{e}），{sleep_for:.2f}s 后重试，第 {attempt+1}/{max_retries} 次")
            time.sleep(sleep_for)
            attempt += 1
    raise RuntimeError(f"模型调用在重试后仍失败: {last_err}")


# 加载 .env 文件中的环境变量
load_dotenv()

# 从环境变量中获取配置
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")

# 模型名称：分离文本与视觉模型，若未配置则回退到统一 MODEL_NAME 或默认 gpt-4o
text_model_name = os.getenv("TEXT_MODEL_NAME") or os.getenv("MODEL_NAME", "gpt-4o")
vision_model_name = os.getenv("VISION_MODEL_NAME") or os.getenv("MODEL_NAME", "gpt-4o")

# 初始化 Flask 应用
app = Flask(__name__, static_folder='.', static_url_path='')

# --- AI 客户端配置 ---

# 根据配置初始化 OpenAI 客户端
# 这使得应用可以灵活地连接到 OpenAI、DeepSeek 或任何其他兼容的 API 服务
if api_key:
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url if base_url else None,
        )
        print(
            "AI 客户端已成功配置。\n"
            f"文本模型: {text_model_name}\n"
            f"视觉模型: {vision_model_name}\n"
            f"服务地址: {base_url or '默认 (OpenAI)'}"
        )
    except Exception as e:
        print(f"错误：无法初始化AI客户端: {e}")
        client = None
else:
    print("警告：未在 .env 文件中检测到 OPENAI_API_KEY。")
    client = None

# --- 模拟客户端（提前定义并在上方生效） ---
class MockOpenAIClient:
    """一个模拟的AI客户端，用于在没有API密钥时返回预设的测试用例。"""
    class Chat:
        class Completions:
            def create(self, model, messages, max_tokens=None):
                try:
                    with open('sample_output.md', 'r', encoding='utf-8') as f:
                        content = f.read()
                except FileNotFoundError:
                    content = "| 用例ID | 模块 | 测试项 | 预期结果 |\n| :--- | :--- | :--- | :--- |\n| MOCK-001 | 模拟数据 | 无法加载示例文件 | 返回此默认表格 |"
                
                class MockChoice:
                    def __init__(self, content):
                        self.message = self
                        self.content = content
                
                class MockResponse:
                    def __init__(self, content):
                        self.choices = [MockChoice(content)]

                return MockResponse(content)
        
        def __init__(self):
            self.completions = self.Completions()

    def __init__(self):
        self.chat = self.Chat()

# 如果AI客户端未成功配置，则使用模拟客户端（在应用启动前确保 client 可用）
if not client:
    print("警告：将使用模拟AI客户端返回预设数据。")
    client = MockOpenAIClient()


# --- 工具函数 ---

def load_prompt_template(file_path):
    """从文件加载提示模板"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "错误：找不到提示模板文件。"

# 加载所有提示模板
prompt_template_full = load_prompt_template('prompt_template.md')
prompt_template_diff = load_prompt_template('prompt_template_diff.md')


# --- API 路由 ---

@app.route('/')
def index():
    """服务于主页面"""
    return app.send_static_file('index.html')

@app.route('/api/generate', methods=['POST'])
def generate_test_cases():
    """处理测试用例生成请求"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "无效的请求，缺少JSON数据"}), 400

        new_prd_content = data.get('new_prd')
        old_prd_content = data.get('old_prd')

        if not new_prd_content:
            return jsonify({"error": "新版PRD内容不能为空"}), 400

        # 判断是全量生成还是增量生成
        if old_prd_content and old_prd_content.strip():
            # --- 增量生成 (暂未实现多模态) ---
            print("正在执行增量生成...")
            final_prompt = prompt_template_diff.format(
                old_prd_content=old_prd_content,
                new_prd_content=new_prd_content
            )
            messages = [
                {"role": "system", "content": "你是一名顶级的、经验丰富的软件测试保证（SQA）工程师。请始终使用简体中文输出。"},
                {"role": "user", "content": final_prompt}
            ]
            # 增量模式：不处理图片
            found_count = 0
            skipped_images = []
            # 调用文本模型生成用例
            print(f"本次请求使用模型: 文本 -> {text_model_name}")
            completion = client.chat.completions.create(
                model=text_model_name,
                messages=messages,
                max_tokens=4096
            )
            ai_response = completion.choices[0].message.content
            
            # 应用表格单行化处理
            ai_response = _sanitize_table_rows(ai_response)

            meta = {
                "mode": "incremental",
                "model_used": text_model_name,
                "use_vision": False
            }

            resp = {"test_cases": ai_response, "meta": meta}
            return jsonify(resp)
        else:
            # --- 全量生成（回退：如果禁用视觉则走纯文本路径） ---
            if DISABLE_VISION:
                print("已启用回退：忽略图片，多模态关闭，执行纯文本全量生成。")
                final_prompt = prompt_template_full.format(prd_content=new_prd_content)
                messages = [
                    {"role": "system", "content": "你是一名资深SQA工程师。请严格基于以下PRD生成测试用例，使用简体中文，不得编造无关场景。"},
                    {"role": "user", "content": final_prompt}
                ]
                completion = client.chat.completions.create(
                    model=text_model_name,
                    messages=messages,
                    max_tokens=4096
                )
                ai_response = completion.choices[0].message.content
                ai_response = _sanitize_table_rows(ai_response)
                meta = {
                    "mode": "full-text-fallback",
                    "model_used": text_model_name,
                    "use_vision": False
                }
                resp = {"test_cases": ai_response, "meta": meta}
                return jsonify(resp)
            else:
                print("正在执行全量图文生成...(未禁用视觉)")
                # 若仍需视觉分析请将 DISABLE_VISION 设为0，这里保留原逻辑但已被用户请求回退，代码逻辑已精简。
                final_prompt = prompt_template_full.format(prd_content=new_prd_content)
                messages = [
                    {"role": "system", "content": "你是一名资深SQA工程师。请基于PRD生成测试用例（当前视觉已暂时停用）。"},
                    {"role": "user", "content": final_prompt}
                ]
                completion = client.chat.completions.create(
                    model=text_model_name,
                    messages=messages,
                    max_tokens=4096
                )
                ai_response = completion.choices[0].message.content
                ai_response = _sanitize_table_rows(ai_response)
                meta = {
                    "mode": "full-text-no-vision",
                    "model_used": text_model_name,
                    "use_vision": False
                }
                resp = {"test_cases": ai_response, "meta": meta}
                return jsonify(resp)

    # 不会到达：增量路径已提前 return
    except Exception as e:
        print(f"API调用时发生严重错误: {e}")
        return jsonify({"error": f"处理请求时发生内部错误: {str(e)}"}), 500


# --- 健康检查 ---
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "base_url": base_url or "openai-default",
        "text_model": text_model_name,
        "api_key_present": bool(api_key),
        "vision_disabled": DISABLE_VISION
    })

# --- 启动应用 ---
if __name__ == '__main__':
    app.run(debug=True, port=5001)

