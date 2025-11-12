"""Application entrypoint for local development."""

from __future__ import annotations

from backend import create_app


app = create_app()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 测试用例生成器 - 服务已启动")
    print("=" * 60)
    print("📱 访问地址：http://localhost:5001")
    print("=" * 60 + "\n")

    app.run(host="0.0.0.0", debug=True, port=5001, threaded=True)
