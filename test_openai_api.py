import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
# 优先读取 OPENAI_API_KEY，也兼容 API_KEY


def main_openai():
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "请用一句话说明你是谁"}
        ],
        temperature=0.7,
    )

    print("==== Response ====")
    print(response.choices[0].message.content)

import os
from dotenv import load_dotenv
from google import genai

# 加载环境变量
load_dotenv()

def test_gemini():
    # 确保 API_KEY 已正确配置在 .env 文件中
    api_key = os.getenv("API_KEY")
    client = genai.Client(api_key=api_key)

    try:
        # 修正模型名称为 gemini-2.0-flash
        stream = client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents="请写一段关于人工智能的介绍"
        )

        for chunk in stream:
            print(chunk.text, end="", flush=True)
    except Exception as e:
        print(f"\n调用失败: {e}")

if __name__ == "__main__":
    test_gemini()
