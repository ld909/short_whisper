import os
import sys
from google import genai


def test_simple_api():
    """测试简单的Google Gemini API调用"""
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print("错误: 未找到 GEMINI_API_KEY 环境变量")
        sys.exit(1)

    try:
        client = genai.Client(api_key=api_key)
        print("✅ 客户端初始化成功")

        # 简单的文本生成测试
        print("正在测试简单的文本生成...")
        response = client.models.generate_content(
            model="gemini-2.5-pro-preview-06-05",
            contents="请用中文简单介绍一下人工智能",
        )

        print("✅ API调用成功！")
        print("\n--- 响应内容 ---")
        print(response.text)
        print("--- 响应结束 ---")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_simple_api()
