"""/api/enhance endpoint blueprint."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from backend.services import create_openai_client, validate_strict_csv, coerce_to_strict_csv


bp = Blueprint("enhance", __name__, url_prefix="/api")


@bp.route("/enhance", methods=["POST"])
def enhance_test_cases():
	data = request.get_json() or {}
	test_cases = data.get("test_cases", "")
	user_config: dict = data.get("config") or {}

	if not test_cases.strip():
		return jsonify({"error": "测试用例内容不能为空"}), 400

	user_api_key = user_config.get("api_key")
	user_base_url = user_config.get("base_url")
	user_text_model = user_config.get("text_model")

	if not user_api_key or not user_text_model:
		return jsonify({"error": "缺少必要配置：请在模型配置中填写 API Key 和 文本模型名称。"}), 400

	try:
		user_client = create_openai_client(user_api_key, user_base_url)
	except Exception as exc:  # noqa: BLE001
		return jsonify({"error": f"配置 AI 客户端失败: {exc}"}), 400

	enhance_prompt = f"""你是一位专业的测试工程师。请分析以下测试用例，并进行完善和补充：

【现有测试用例（原文）】
{test_cases}

【完善目标】
1. 用户场景补充：添加更多正向流程、边界条件
2. 异常场景补充：错误处理、异常输入、网络异常等
3. 测试步骤完善：步骤清晰、可执行
4. 预期结果优化：明确具体、可验证
5. 覆盖度提升：识别遗漏并补充

【输出格式（严格）】
- 仅输出 CSV 文本，不要输出 Markdown、代码块或其它说明。
- 第一行必须是表头，列为：用例ID,模块,子模块,测试项,前置条件,操作步骤,预期结果,用例类型
- 新增的测试用例在“用例ID”列以“[新增] ”前缀标注，例如：[新增] TC-登录-密码错误-0007
- 使用英文逗号分隔；如单元格内含逗号或换行，请用双引号包裹，并将内部双引号转义为两个双引号。

请直接输出完善后的完整 CSV 内容。"""

	try:
		completion = user_client.chat.completions.create(
			model=user_text_model,
			messages=[
				{
					"role": "system",
					"content": "你是一位经验丰富的测试工程师，擅长设计全面的测试用例。",
				},
				{"role": "user", "content": enhance_prompt},
			],
			max_tokens=4096,
			temperature=0.7,
		)
	except Exception as exc:  # noqa: BLE001
		return jsonify({"error": f"AI 调用失败: {exc}"}), 500

	enhanced_cases = completion.choices[0].message.content
	# 宽松模式：尽量修复，不再拦截
	ok, _ = validate_strict_csv(enhanced_cases)
	if not ok:
		repaired = coerce_to_strict_csv(enhanced_cases)
		ok2, _ = validate_strict_csv(repaired)
		if ok2:
			enhanced_cases = repaired

	return jsonify(
		{
			"enhanced_cases": enhanced_cases,
			"meta": {
				"model_used": user_text_model,
				"original_length": len(test_cases),
				"enhanced_length": len(enhanced_cases),
			},
		}
	)
