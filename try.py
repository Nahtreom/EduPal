from openai import OpenAI
MAX_RETRIES=3
client = OpenAI(
    api_key="sk-CKjoEtkZn_JPlxwOicqgQA",
    base_url="http://10.119.14.104:9000/v1/",
)
retry_count = 0
response_content = None

while retry_count < MAX_RETRIES:
    try:
        response = client.chat.completions.create(
                    model="deepseek",
                    messages=[
                        {
                            "role": "user",
                            "content": "你好吗"
                        }
                    ],
                    max_tokens=3200,
                    temperature=1
                )
        
        # 添加调试输出：打印完整响应结构
        print("API响应结构:", dir(response))
        if hasattr(response, 'choices'):
            print("Choices结构:", dir(response.choices[0]) if response.choices else "空Choices")
                
        # 修复1：完善响应内容检查（增加对content非空的验证）
        if response.choices and response.choices[0].message:
            message = response.choices[0].message
            if message.content and message.content.strip():  # 检查content是否存在且非空
                response_content = message.content
                # 修复2：成功获取内容后跳出循环，避免重复调用
                break  
            else:
                response_content = "错误：响应message中content为空"
        else:
            response_content = f"错误：响应中未找到预期的'content'。响应: {response}"

        # 若未触发break（如content为空），仍允许重试
        retry_count += 1
        print(f"响应内容异常，将重试 (尝试 {retry_count}/{MAX_RETRIES})")

    except Exception as e:
        retry_count += 1
        print(f"API调用错误 (尝试 {retry_count}/{MAX_RETRIES}): {e}")
        if retry_count >= MAX_RETRIES:
            response_content = f"错误：达到最大重试次数后API调用失败。最后错误: {e}"
            break

# 添加调试输出：检查最终response_content状态
print("最终响应内容状态:", "已获取" if response_content else "未获取")
if response_content:
    print(response_content)
else:
    print("未能获取模型响应")
