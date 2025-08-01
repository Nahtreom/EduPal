import time
from openai import OpenAI
import json
from typing import List, Dict, Any

# 常量定义
MAX_RETRIES = 3
TIMEOUT = 1200

class APITestClient:
    def __init__(self, api_key: str, model: str = "gpt-4.5-preview"):
        self.api_key = api_key
        self.model = model
        # 初始化 OpenAI 客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://yeysai.com/v1/",
        )
    
    def call_api_with_text(self, text: str) -> str:
        """简单的纯文本API调用"""
        content = [
            {
                "type": "text",
                "text": text
            }
        ]
        
        # 调用API
        return self._call_api(content)
    
    def _call_api(self, content: List[Dict[str, Any]]) -> str:
        """发送API请求并处理响应"""
        retry_count = 0
        response_content = None

        while retry_count < MAX_RETRIES:
            try:
                print(f"正在调用API... (尝试 {retry_count + 1}/{MAX_RETRIES})")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": content
                        }
                    ],
                    max_tokens=3200,
                    temperature=1
                )
                
                if response.choices and response.choices[0].message:
                    response_content = response.choices[0].message.content
                    print("API调用成功！")
                else:
                    response_content = f"错误：响应中未找到预期的'content'。响应: {response}"
                break  # 成功，跳出重试循环

            except Exception as e:
                retry_count += 1
                print(f"API调用错误 (尝试 {retry_count}/{MAX_RETRIES}): {e}")
                if retry_count >= MAX_RETRIES:
                    response_content = f"错误：达到最大重试次数后API调用失败。最后错误: {e}"
                    break
                print(f"等待 {5 * retry_count} 秒后重试...")
                time.sleep(5 * retry_count)

        return response_content if response_content else "未能获取模型响应"

def interactive_test():
    """交互式API测试"""
    # 在这里指定你的API key和模型
    API_KEY = "sk-YXuhmY5lA1N1I4mH72F4EdCf9f26493aA1A0Df24C76a0504"  # 请替换为实际的API key
    MODEL = "gpt-4.5-preview"
    
    client = APITestClient(api_key=API_KEY, model=MODEL)
    
    print("="*50)
    print("API测试程序")
    print(f"使用模型: {MODEL}")
    print("输入 'quit' 或 'exit' 退出程序")
    print("="*50)
    
    while True:
        try:
            user_input = input("\n请输入您的问题: ").strip()
            
            if user_input.lower() in ['quit', 'exit', '退出']:
                print("程序已退出。")
                break
            
            if not user_input:
                print("请输入有效的问题。")
                continue
            
            print("\n正在处理您的请求...")
            response = client.call_api_with_text(user_input)
            print(f"\nAI回复: {response}")
            
        except KeyboardInterrupt:
            print("\n\n程序被用户中断。")
            break
        except Exception as e:
            print(f"发生错误: {e}")

if __name__ == "__main__":
    try:
        interactive_test()
    except KeyboardInterrupt:
        print("\n程序已退出。")
    except Exception as e:
        print(f"程序运行出错: {e}")