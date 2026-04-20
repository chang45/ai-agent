# main.py
# 职责：程序入口，负责对话循环和工具调用编排
# 把"和模型对话"与"执行工具"两件事串联起来

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

from tool_define import TOOLS        # 工具结构定义，传给模型告知它有哪些工具可用
from tool_func import execute_tool   # 工具调度器，负责实际执行工具并返回结果
from system_prompt import SYSTEM_PROMPT

load_dotenv()

# 从环境变量读取配置，避免硬编码敏感信息
API_KEY = os.getenv("ARK_API_KEY")      # 豆包 API 密钥
BASE_URL = os.getenv("ARK_BASE_URL")    # 豆包兼容 OpenAI 格式的接口地址
MODEL = os.getenv("ARK_MODEL")          # 使用的模型名称

# 初始化 OpenAI 客户端，指向豆包的接口地址
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def trim_messages(messages: list, max_messages: int = 20) -> list:
    """裁剪历史消息，保留 system 提示词和最近若干条消息。"""
    if len(messages) <= max_messages + 1:
        return messages
    return [messages[0]] + messages[-max_messages:]


def chat_with_tools(messages: list) -> str:
    """
    支持工具调用的多轮对话函数。

    工作流程：
      1. 使用完整历史消息请求模型
      2. 若模型决定调用工具 → 执行工具 → 把结果追加到消息历史 → 再次请求模型
      3. 若模型直接返回文本 → 结束循环，返回最终答案
    """
    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=trim_messages(messages),
            tools=TOOLS,
            tool_choice="auto",
        )

        choice = response.choices[0]
        message = choice.message

        # 情况1：模型没有调用任何工具，直接给出最终回答
        if not message.tool_calls:
            final_content = message.content or ""
            messages.append({"role": "assistant", "content": final_content})
            return final_content

        # 情况2：模型决定调用一个或多个工具
        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            }
        )

        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            tool_result = execute_tool(tool_name, tool_args)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                }
            )


# ══════════════════════════════════════════════
#  程序入口
# ══════════════════════════════════════════════
if __name__ == "__main__":
    print("--- 已连接到豆包大模型（支持天气决策 + 位置查询，输入 'quit' 退出）---")
    print("    示例：今天适合晒被子吗？ / 我现在在哪里？ / 上海这周适合旅游吗？")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    while True:
        user_input = input("\n我：").strip()

        # 忽略空输入，等待用户重新输入
        if not user_input:
            continue

        # 检测退出指令
        if user_input.lower() in ["quit", "exit", "退出"]:
            break

        try:
            messages.append({"role": "user", "content": user_input})
            answer = chat_with_tools(messages)
            print(f"\n豆包：{answer}")
        except Exception as e:
            # 捕获网络错误、API 错误等异常，打印后继续对话而不是崩溃退出
            print(f"\n发生错误：{e}")

    print("对话已结束。")
