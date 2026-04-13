import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ARK_API_KEY")
BASE_URL = os.getenv("ARK_BASE_URL")
MODEL = os.getenv("ARK_MODEL")

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)
print("--- 已连接到豆包大模型 (输入 'quit' 退出) ---")
while True:
    user_input = input("\n我：")
    
    if user_input.lower() in ['quit', 'exit', '退出']:
        break

    # 发送请求
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": user_input}
            ]
        )
        
        # 打印 AI 的回答
        print(f"\n豆包：{response.choices[0].message.content}")
        
    except Exception as e:
        print(f"\n发生错误：{e}")

print("对话已结束。")