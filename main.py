# main.py
# 职责：程序入口，负责对话循环和工具调用编排
# 把"和模型对话"与"执行工具"两件事串联起来

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

from tool_define import TOOLS        # 工具结构定义，传给模型告知它有哪些工具可用
from tool_func import execute_tool       # 工具调度器，负责实际执行工具并返回结果
from system_prompt import SYSTEM_PROMPT 

load_dotenv()

# 从环境变量读取配置，避免硬编码敏感信息
API_KEY  = os.getenv("ARK_API_KEY")   # 豆包 API 密钥
BASE_URL = os.getenv("ARK_BASE_URL")  # 豆包兼容 OpenAI 格式的接口地址
MODEL    = os.getenv("ARK_MODEL")     # 使用的模型名称

# 初始化 OpenAI 客户端，指向豆包的接口地址
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def chat_with_tools(user_input: str) -> str:
    """
    支持工具调用的单轮对话函数。

    工作流程：
      1. 把用户输入发给模型
      2. 若模型决定调用工具 → 执行工具 → 把结果追加到消息历史 → 再次请求模型
      3. 若模型直接返回文本 → 结束循环，返回最终答案

    用 while 循环是因为模型可能连续调用多个工具（例如同时查天气和位置）。

    Args:
        user_input: 用户输入的文本

    Returns:
        模型最终生成的回复文本
    """
    # 初始化消息历史，先注入系统提示词，再加入用户消息
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]

    # 循环直到模型不再调用工具、直接返回最终回复为止
    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,   # 每次都把完整的消息历史传给模型，保持上下文
            tools=TOOLS,         # 告诉模型有哪些工具可以调用
            tool_choice="auto",  # auto：让模型自己判断是否需要调用工具
        )

        choice = response.choices[0]
        message = choice.message  # 模型本轮的回复

        # ── 情况1：模型没有调用任何工具，直接给出了最终回答 ──
        if not message.tool_calls:
            return message.content

        # ── 情况2：模型决定调用一个或多个工具 ──

        # 第一步：把模型的回复（含工具调用意图）追加到消息历史
        # 这一步必须做，否则下一轮请求时模型不知道自己之前说了什么
        messages.append({
            "role": "assistant",
            "content": message.content,  # 模型在调用工具之前可能会有一段说明文字
            "tool_calls": [
                {
                    "id": tc.id,          # 工具调用的唯一 ID，后续 tool 消息需要对应
                    "type": "function",
                    "function": {
                        "name": tc.function.name,           # 工具名称
                        "arguments": tc.function.arguments, # 模型提取的参数（JSON 字符串）
                    },
                }
                for tc in message.tool_calls
            ],
        })

        # 第二步：逐个执行工具，把每个工具的结果追加到消息历史
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name                      # 工具名称
            tool_args = json.loads(tool_call.function.arguments)     # 参数字符串 → 字典

            # 打印调用信息，方便调试时观察模型的决策过程
            # print(f"\n  [工具调用] {tool_name}({tool_args})")
            tool_result = execute_tool(tool_name, tool_args)         # 实际执行工具
            # print(f"  [工具结果] {tool_result}")

            # 把工具结果以 "tool" 角色追加到历史
            # tool_call_id 必须和上面 assistant 消息中的 id 对应，模型靠它匹配结果
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result,   # 工具返回的 JSON 字符串
            })

        # 第三步：带着更新后的消息历史再次请求模型
        # 模型会基于工具结果继续推理，可能再次调用工具，也可能直接给出最终回答
        # （由 while 循环顶部的请求处理）


# ══════════════════════════════════════════════
#  程序入口
# ══════════════════════════════════════════════
if __name__ == "__main__":
    print("--- 已连接到豆包大模型（支持天气 + 位置查询，输入 'quit' 退出）---")
    print("    示例：北京今天天气怎么样？ / 故宫在哪里？ / 上海外滩的位置和天气？")

    while True:
        user_input = input("\n我：").strip()

        # 忽略空输入，等待用户重新输入
        if not user_input:
            continue

        # 检测退出指令
        if user_input.lower() in ["quit", "exit", "退出"]:
            break

        try:
            answer = chat_with_tools(user_input)
            print(f"\n豆包：{answer}")
        except Exception as e:
            # 捕获网络错误、API 错误等异常，打印后继续对话而不是崩溃退出
            print(f"\n发生错误：{e}")

    print("对话已结束。")