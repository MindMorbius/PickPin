def select_prompt(message: str) -> str:
    # 根据消息内容选择合适的 prompt
    if "代码" in message or "编程" in message:
        return "你是一个专业的程序员，善于解答编程相关问题。"
    elif "翻译" in message:
        return "你是一个专业的翻译，精通中英文互译。"
    else:
        return "你是一个友好的AI助手，可以帮助用户解答各种问题。" 