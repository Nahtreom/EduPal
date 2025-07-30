#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import api_call

def test_text_api():
    """测试纯文本API调用"""
    
    # API配置
    api_key = "sk-YXuhmY5lA1N1I4mH72F4EdCf9f26493aA1A0Df24C76a0504"  # 请替换为您的实际API密钥
    model = "gpt-4.5-preview"
    
    # 测试文本
    test_text = "你好！请简单介绍一下Python编程语言的特点。"
    
    print("=" * 50)
    print("开始测试API调用...")
    print(f"使用模型: {model}")
    print(f"发送文本: {test_text}")
    print("=" * 50)
    
    try:
        # 调用API
        response = api_call.process_text(
            text=test_text,
            api_key=api_key,
            model=model
        )
        
        print("API响应:")
        print("-" * 30)
        print(response)
        print("-" * 30)
        print("测试完成！")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")

def test_interactive():
    """交互式测试"""
    api_key = input("请输入您的API密钥: ").strip()
    if not api_key:
        print("未提供API密钥，退出测试。")
        return
    
    model = "gpt-4o"
    print(f"使用模型: {model}")
    print("输入 'quit' 或 'exit' 退出程序")
    print("=" * 50)
    
    while True:
        user_input = input("\n请输入您的问题: ").strip()
        
        if user_input.lower() in ['quit', 'exit', '退出']:
            print("再见！")
            break
            
        if not user_input:
            print("请输入有效的问题。")
            continue
            
        try:
            print("\n正在处理您的请求...")
            response = api_call.process_text(
                text=user_input,
                api_key=api_key,
                model=model
            )
            
            print("\nAI回复:")
            print("-" * 30)
            print(response)
            print("-" * 30)
            
        except Exception as e:
            print(f"处理请求时出错: {str(e)}")

if __name__ == "__main__":
    print("API测试程序")
    print("1. 简单测试")
    print("2. 交互式测试")
    
    choice = input("请选择测试模式 (1/2): ").strip()
    
    if choice == "1":
        test_text_api()
    elif choice == "2":
        test_interactive()
    else:
        print("无效选择，退出程序。") 