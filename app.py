import os
import re
import requests
import base64
import time
from io import BytesIO
from PIL import Image
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
from urllib.parse import urlparse
from typing import List, Dict, Tuple

# --- 初始化与配置 ---

# 加载 .env 文件中的环境变量
load_dotenv()

DISABLE_VISION = os.getenv("DISABLE_VISION", "1") == "1"  # 回退：1 时完全禁用图片理解（默认开启）
MAX_IMAGES_PER_BATCH = int(os.getenv("MAX_IMAGES_PER_BATCH", "10"))  # 单批最多图片数
IMAGE_MAX_SIZE = int(os.getenv("IMAGE_MAX_SIZE", "1024"))  # 图片压缩尺寸
IMAGE_QUALITY = int(os.getenv("IMAGE_QUALITY", "85"))  # JPEG 压缩质量
MAX_SECTION_CHARS = int(os.getenv("MAX_SECTION_CHARS", "60000"))  # 单章节文本字符上限

# --- 多模态处理核心函数 ---

def extract_images_from_markdown(markdown_text: str) -> List[Tuple[str, int]]:
    """
    从 Markdown 文本中提取所有图片链接及其位置
    返回: [(image_url, position), ...]
    """
    pattern = r'!\[.*?\]\((.*?)\)'
    matches = []
    for match in re.finditer(pattern, markdown_text):
        url = match.group(1).strip()
        if url:  # 跳过空链接
            matches.append((url, match.start()))
    return matches

def parse_prd_sections(markdown_text: str) -> List[Dict]:
    """
    解析 PRD 为章节结构，建立文本-图片映射
    返回: [{"title": str, "text": str, "images": [url, ...], "start_pos": int, "end_pos": int}, ...]
    """
    sections = []
    lines = markdown_text.split('\n')
    
    current_section = {"title": "前言", "text": "", "images": [], "start_pos": 0, "end_pos": 0}
    current_pos = 0
    
    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        
        # 检测标题（H1 或 H2）
        if line.startswith('# ') or line.startswith('## '):
            # 保存当前章节
            if current_section["text"].strip():
                current_section["end_pos"] = current_pos
                current_section["text"] = current_section["text"].strip()
                sections.append(current_section)
            
            # 开始新章节
            title = line.lstrip('#').strip()
            current_section = {
                "title": title,
                "text": "",
                "images": [],
                "start_pos": current_pos,
                "end_pos": 0
            }
        else:
            current_section["text"] += line + '\n'
        
        current_pos += line_len
    
    # 保存最后一个章节
    if current_section["text"].strip():
        current_section["end_pos"] = current_pos
        current_section["text"] = current_section["text"].strip()
        sections.append(current_section)
    
    # 为每个章节提取图片
    all_images = extract_images_from_markdown(markdown_text)
    for section in sections:
        section["images"] = [
            img_url for img_url, pos in all_images
            if section["start_pos"] <= pos < section["end_pos"]
        ]
    
    return sections

def download_and_process_image(url: str, max_size: int = IMAGE_MAX_SIZE, quality: int = IMAGE_QUALITY) -> str:
    """
    下载图片、压缩并转为 base64
    返回: base64 字符串 或 None（失败时）
    """
    try:
        # 下载图片
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        # 打开图片
        img = Image.open(BytesIO(response.content))
        
        # 转换为 RGB（去除透明通道）
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # 压缩尺寸
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # 转为 base64
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=quality, optimize=True)
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return f"data:image/jpeg;base64,{img_base64}"
    
    except Exception as e:
        print(f"处理图片失败 {url}: {e}")
        return None

def create_batches_from_sections(sections: List[Dict], max_images: int = MAX_IMAGES_PER_BATCH) -> List[Dict]:
    """
    将章节智能分批，确保每批不超过图片数量限制
    返回: [{"sections": [section, ...], "total_images": int, "total_chars": int}, ...]
    """
    batches = []
    current_batch = {"sections": [], "total_images": 0, "total_chars": 0}
    
    for section in sections:
        section_images = len(section["images"])
        section_chars = len(section["text"])
        
        # 检查是否需要开始新批次
        if current_batch["sections"] and (
            current_batch["total_images"] + section_images > max_images or
            current_batch["total_chars"] + section_chars > MAX_SECTION_CHARS
        ):
            batches.append(current_batch)
            current_batch = {"sections": [], "total_images": 0, "total_chars": 0}
        
        # 添加到当前批次
        current_batch["sections"].append(section)
        current_batch["total_images"] += section_images
        current_batch["total_chars"] += section_chars
    
    # 保存最后一批
    if current_batch["sections"]:
        batches.append(current_batch)
    
    return batches

def build_vision_messages(batch: Dict, prompt_template: str, batch_index: int, total_batches: int) -> List[Dict]:
    """
    构建多模态消息（包含文本和图片）
    """
    # 合并批次内所有章节文本
    combined_text = "\n\n".join([
        f"## {section['title']}\n{section['text']}"
        for section in batch["sections"]
    ])
    
    # 构建 Prompt（添加批次信息）
    batch_info = ""
    if total_batches > 1:
        batch_info = f"\n\n【注意】这是第 {batch_index + 1}/{total_batches} 批次的 PRD 内容，请基于本批次内容生成测试用例。用例 ID 从 TC-{(batch_index * 100 + 1):03d} 开始编号。"
    
    final_prompt = prompt_template.format(prd_content=combined_text) + batch_info
    
    # 收集所有图片
    all_image_urls = []
    for section in batch["sections"]:
        all_image_urls.extend(section["images"])
    
    # 构建消息内容
    content = [{"type": "text", "text": final_prompt}]
    
    # 添加图片
    for img_url in all_image_urls:
        img_base64 = download_and_process_image(img_url)
        if img_base64:
            content.append({
                "type": "image_url",
                "image_url": {"url": img_base64}
            })
        else:
            print(f"跳过无法处理的图片: {img_url}")
    
    messages = [
        {"role": "system", "content": "你是一名资深SQA工程师。请严格基于以下PRD（包含文本和图片）生成测试用例，使用简体中文，不得编造无关场景。"},
        {"role": "user", "content": content}
    ]
    
    return messages

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
            # --- 全量生成（支持多模态图片识别） ---
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
                # 启用多模态处理
                print("正在执行全量图文生成（多模态已启用）...")
                
                # 1. 解析 PRD 结构
                sections = parse_prd_sections(new_prd_content)
                total_images = sum(len(s["images"]) for s in sections)
                print(f"解析完成：{len(sections)} 个章节，共 {total_images} 张图片")
                
                # 2. 检查是否有图片
                if total_images == 0:
                    # 无图片，降级为纯文本模式
                    print("未检测到图片，使用文本模型处理")
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
                        "mode": "full-no-images",
                        "model_used": text_model_name,
                        "use_vision": False
                    }
                    resp = {"test_cases": ai_response, "meta": meta}
                    return jsonify(resp)
                
                # 3. 创建批次
                batches = create_batches_from_sections(sections, MAX_IMAGES_PER_BATCH)
                print(f"分批策略：共 {len(batches)} 批次")
                
                # 4. 逐批调用视觉模型
                all_responses = []
                for i, batch in enumerate(batches):
                    print(f"处理第 {i+1}/{len(batches)} 批（{batch['total_images']} 张图片，{batch['total_chars']} 字符）...")
                    
                    # 构建多模态消息
                    messages = build_vision_messages(batch, prompt_template_full, i, len(batches))
                    
                    # 调用视觉模型（带重试）
                    try:
                        response = _call_model_with_retries(vision_model_name, messages)
                        all_responses.append(response)
                        print(f"第 {i+1} 批完成")
                    except Exception as e:
                        print(f"第 {i+1} 批失败: {e}")
                        all_responses.append("")  # 添加空响应继续处理
                
                # 5. 合并结果
                print("合并所有批次结果...")
                merged_response = _merge_markdown_tables(all_responses)
                final_response = _sanitize_table_rows(merged_response)
                
                meta = {
                    "mode": "full-vision-multimodal",
                    "model_used": vision_model_name,
                    "use_vision": True,
                    "total_batches": len(batches),
                    "total_images": total_images,
                    "total_sections": len(sections)
                }
                
                resp = {"test_cases": final_response, "meta": meta}
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

