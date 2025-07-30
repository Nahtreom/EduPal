import os
import sys
import argparse
import json
from datetime import datetime
import glob

# 假设 api_call.py 与此脚本在同一目录中
sys.path.append(os.getcwd())

try:
    from api_call import process_text
except ImportError:
    print("[ERR] 错误: 无法导入 'api_call'. 请确保 api_call.py 与此脚本在同一目录中。")
    sys.exit(1)

def print_separator(char="=", length=50):
    """打印分隔线以美化输出。"""
    print(char * length)

def format_time():
    """获取当前格式化时间字符串。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def load_config(config_path: str = "config.json"):
    """
    加载配置文件 (config.json)，主要用于获取 API Key。
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        if not config.get("api_key") or config.get("api_key") in ["", "your-api-key-here"]:
            print(f"[ERR] 错误: 请在 {config_path} 文件中设置有效的 'api_key'")
            sys.exit(1)
        return config
    except FileNotFoundError:
        print(f"[ERR] 错误: 配置文件 '{config_path}' 未找到。请创建一个包含 'api_key' 的 config.json 文件。")
        sys.exit(1)
    except Exception as e:
        raise Exception(f"加载配置文件失败: {str(e)}")

def load_test_profiles(profile_name: str, profiles_path: str = "test_profiles.json"):
    """
    加载试卷配置方案。如果文件不存在，则创建一个包含默认方案的文件。
    """
    if not os.path.exists(profiles_path):
        default_profiles = {
            "default": {
                "num_questions": 10,
                "difficulty": "中等",
                "question_types": "选择题, 简答题",
                "topic_hint": "未提供"
            },
            "advanced_essay": {
                "num_questions": 5,
                "difficulty": "高级-需要深入理解和思辨",
                "question_types": "简答题, 论述题",
                "topic_hint": "关于核心方法和实验结论的深入探讨"
            },
            "quick_quiz": {
                "num_questions": 8,
                "difficulty": "初级",
                "question_types": "单选题, 判断题",
                "topic_hint": "关于论文关键概念和结论的基础测试"
            }
        }
        with open(profiles_path, 'w', encoding='utf-8') as f:
            json.dump(default_profiles, f, indent=4, ensure_ascii=False)
        print(f"[INFO] 已创建默认的试卷配置文件: {profiles_path}")

    with open(profiles_path, 'r', encoding='utf-8') as f:
        profiles = json.load(f)
    
    if profile_name not in profiles:
        print(f"[ERR] 错误: 在 '{profiles_path}' 中未找到名为 '{profile_name}' 的配置方案。")
        print(f"可用方案: {list(profiles.keys())}")
        sys.exit(1)
    
    print(f"已加载配置方案: '{profile_name}'")
    return profiles[profile_name]


def load_prompt_template(template_path: str):
    """
    加载用于根据论文生成试卷的提示词模板。如果模板不存在，则创建一个默认模板。
    """
    if not os.path.exists(template_path):
        default_prompt = """你是一位顶级的学术出题专家和考官。
你的核心任务是根据一份完整的学术论文文本，设计一份高质量的考卷，用以检验读者对该论文的理解深度。

**基本要求:**
1.  **出题依据:** 所有问题的设计和答案都必须严格基于我提供给你的“论文全文内容”。禁止引入外部知识或超出论文范围的信息。
2.  **考察重点:** 题目应覆盖论文的关键部分，包括：
    - **引言 (Intro):** 论文试图解决的问题、背景和核心贡献。
    - **方法 (Method):** 论文提出的模型、算法或框架的具体细节。
    - **实验 (Experiment):** 实验设置、所用数据集、评估指标以及关键的实验结果。
    - **结论 (Conclusion):** 论文的主要发现、局限性和未来展望。
3.  **格式要求:**
    - 严格使用 Markdown 格式。
    - 试卷分为 `## 试题部分` 和 `## 答案与解析` 两大块。
    - 在“答案与解析”部分，为每道题提供明确的“正确答案”和“详细解析”，解析需要解释答案为何正确，并引用论文中的相关论据。
4.  **严格遵守输出格式:** 最终的输出内容应当是一个完整的 Markdown 文档，不要在文档前后添加任何解释性文字或将其放入代码块（例如 ```markdown ... ```）。

---
**待填充的试卷生成指令:**
*   **试卷主题 (可选的上下文提示):** {topic_hint}
*   **试卷难度:** {difficulty}
*   **题目数量:** {num_questions}
*   **题目类型:** {question_types}

---
**论文全文内容:**
{paper_full_text}

请严格按照以上要求，基于提供的论文全文内容，开始生成试卷。
"""
        prompt_dir = os.path.dirname(template_path)
        if prompt_dir:
            os.makedirs(prompt_dir, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(default_prompt)
        print(f"[INFO] 已创建默认的试卷提示词模板: {template_path}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def create_test_paper(paper_sections_dir: str, output_dir: str, output_filename: str, prompt_path: str, profile_params: dict):
    """
    核心函数，负责整个试卷生成流程。
    """
    try:
        # --- 步骤 0: 准备输出目录 ---
        print_separator()
        print(f"[{format_time()}] 开始根据论文内容创建试卷...")
        print(f"输出目录: {output_dir}")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"已创建输出目录: {output_dir}")

        # --- 步骤 1: 合并论文章节文本 ---
        print_separator()
        print("[步骤 1/4] 正在合并论文章节文件...")
        
        section_order = ['Intro', 'Method', 'Experiment', 'Conclusion']
        if not os.path.isdir(paper_sections_dir):
            raise FileNotFoundError(f"指定的论文章节目录 '{paper_sections_dir}' 不存在。")
            
        all_section_files = glob.glob(os.path.join(paper_sections_dir, '*.md')) + \
                            glob.glob(os.path.join(paper_sections_dir, '*.txt'))
        
        sorted_files = []
        for section_name in section_order:
            found_file = next((f for f in all_section_files if section_name.lower() in os.path.basename(f).lower()), None)
            if found_file:
                sorted_files.append(found_file)
                print(f"  - 找到章节: {os.path.basename(found_file)}")
            else:
                print(f"  - [警告] 未找到与 '{section_name}' 相关的章节文件。")

        if not sorted_files:
            raise FileNotFoundError(f"在目录 '{paper_sections_dir}' 中未能找到任何有效的章节文件。")

        paper_full_text = "\n\n---\n\n".join([open(f, 'r', encoding='utf-8').read() for f in sorted_files])
        print("论文章节文本合并完成。")


        # --- 步骤 2: 加载配置和模板 ---
        print_separator()
        print("[步骤 2/4] 正在加载 API 配置和提示词模板...")
        config = load_config()
        prompt_template = load_prompt_template(prompt_path)
        print("配置和模板加载成功。")

        # --- 步骤 3: 构建最终的 Prompt ---
        print_separator()
        print("[步骤 3/4] 正在构建生成指令...")
        
        # 使用从 profile 中获取的参数
        final_prompt = prompt_template.format(
            topic_hint=profile_params['topic_hint'],
            difficulty=profile_params['difficulty'],
            num_questions=profile_params['num_questions'],
            question_types=profile_params['question_types'],
            paper_full_text=paper_full_text
        )
        print("生成指令构建完成。")

        # --- 步骤 4: 调用 AI 生成试卷并保存 ---
        print_separator()
        print("[步骤 4/4] 正在调用 AI 生成试卷内容...")
        
        api_key = config['api_key']
        model = config.get('model', 'gpt-4-turbo')
        
        test_paper_content = process_text(final_prompt, api_key, model)
        
        # 使用指定的输出文件名
        test_paper_path = os.path.join(output_dir, output_filename)
        with open(test_paper_path, 'w', encoding='utf-8') as f:
            f.write(test_paper_content.strip())
        print(f"试卷已成功保存到: {test_paper_path}")
        
        print_separator()
        print(f"🎉 全部流程成功完成！")
        print(f"✨ 基于论文的专属试卷已创建在: {output_dir}")
        print_separator()

    except Exception as e:
        print(f"\n[ERR] 处理过程中发生严重错误: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """
    主函数，用于解析命令行参数并启动试卷生成流程。
    """
    parser = argparse.ArgumentParser(
        description="根据指定的论文章节文件夹，使用大语言模型智能生成 Markdown 格式的考卷。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # --- 位置参数 ---
    parser.add_argument("paper_sections_dir", help="包含论文章节文件 (如 intro.md, method.md 等) 的输入文件夹路径。")
    parser.add_argument("output_dir", help="最终输出的试卷文件夹路径。")

    # --- 可选参数 ---
    parser.add_argument(
        "--output_filename",
        default="test_paper.md",
        help="指定输出的试卷文件名。\n(默认: test_paper.md)"
    )
    parser.add_argument(
        "--profile",
        default="default",
        help="指定在 'test_profiles.json' 中定义的试卷配置方案名称。\n(默认: 'default')"
    )
    parser.add_argument(
        "--prompt",
        default="prompt_template/Test_From_Paper_Generator.txt",
        help="指定用于生成试卷的提示词模板文件路径。\n(默认: prompt_template/Test_From_Paper_Generator.txt)"
    )
    
    args = parser.parse_args()
    
    # 加载指定的配置方案
    profile_params = load_test_profiles(args.profile)
    
    create_test_paper(
        paper_sections_dir=args.paper_sections_dir,
        output_dir=args.output_dir,
        output_filename=args.output_filename,
        prompt_path=args.prompt,
        profile_params=profile_params
    )

if __name__ == "__main__":
    main()