# create_speech_package.py
import os
import sys
import argparse
import json
from datetime import datetime
import glob
import shutil

sys.path.append(os.getcwd())

try:
    from api_call import process_text
except ImportError as e:
    # 添加更详细的错误输出，帮助我们看到Python实际的搜索路径
    print("[ERR] 错误: 无法导入 'api_call'.")
    print("      请确保 api_call.py 与此脚本在同一目录中。")
    print("      当前的Python搜索路径 (sys.path) 是:")
    for path in sys.path:
        print(f"      - {path}")
    print(f"      ImportError: {e}")
    sys.exit(1)

def print_separator(char="=", length=50):
    print(char * length)

def format_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def load_config(config_path: str = "config.json"):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        if not config.get("api_key") or config.get("api_key") in ["", "your-api-key-here"]:
            print(f"[ERR] 错误: 请在 {config_path} 文件中设置有效的 'api_key'")
            sys.exit(1)
        return config
    except FileNotFoundError:
        print(f"[ERR] 错误: 配置文件 '{config_path}' 未找到。"); sys.exit(1)
    except Exception as e:
        raise Exception(f"加载配置文件失败: {str(e)}")

# 这个函数现在只加载一个指定的提示词，由命令行参数决定是哪个
def load_prompt_template(template_path: str):
    if not os.path.exists(template_path):
        default_prompt = """
你是一位顶级的学术讲解员和多媒体内容制作专家。
你的任务是将一份纯文本的学术论文，与一个“可用图片路径列表”，智能地融合成一份图文并茂的口语化讲解稿。首先，使用中文！
你的输入包含两部分：
1. **论文纯文本内容**：完整的论文文本。
2. **可用图片路径列表**：一个Markdown列表，列出了所有可用的图片及其在最终稿中应使用的路径。
你的任务要求如下：
1. **智能图文匹配**：请通读论文全文，理解上下文。当你讲解到的内容与某张图片的主题（可以从路径的文件名中推断）高度相关时，将该图片的完整Markdown引用插入到讲解稿中最恰当的位置。
2. **使用正确路径**：**必须**使用“可用图片路径列表”中提供的完整路径来引用图片。
3. **内容与格式**：
   - 用二级标题（`##`）来组织章节。
   - 讲解风格需口语化、流畅自然，但是又不失学术性和严谨性。

4. **输出**：只输出最终的、包含文本和图片引用的单一Markdown讲解稿。
5. **学术性要求**: 讲解稿中需包含对论文具体方法、实验设计和结果的详细描述和分析，确保读者能够充分理解论文的思路、贡献和创新点。

6. 不要在开头加入```markdown
7. 不要在结尾加入```
"""
        # (函数的其余部分保持不变)
        prompt_dir = os.path.dirname(template_path)
        if prompt_dir: os.makedirs(prompt_dir, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f: f.write(default_prompt)
        print(f"[INFO] 已创建默认提示词模板: {template_path}")
    with open(template_path, 'r', encoding='utf-8') as f: return f.read().strip()



def create_package(sections_dir: str, images_dir: str, output_package_dir: str, prompt_path: str):
    section_order = ['Intro', 'Method', 'Experiment', 'Conclusion']
    try:
        # --- 步骤 0: 准备输出目录 ---
        print_separator(); print(f"[{format_time()}] 开始创建讲解稿包...")
        print(f"输出包目录: {output_package_dir}")
        if os.path.exists(output_package_dir):
            # 提供一个简单的安全检查，防止意外覆盖
            print(f"[警告] 输出目录 '{output_package_dir}' 已存在。其中的内容可能会被覆盖。")
        else:
            os.makedirs(output_package_dir)
            print(f"已创建输出目录: {output_package_dir}")

        # --- 步骤 1: 合并文本 ---
        print_separator(); print("[步骤 1/4] 正在合并章节文件...")
        if not os.path.isdir(sections_dir): raise FileNotFoundError(f"章节目录 '{sections_dir}' 不存在。")
        all_section_files = glob.glob(os.path.join(sections_dir, '*.md'))
        sorted_files = []
        for section in section_order:
            found_file = next((f for f in all_section_files if section.lower() in os.path.basename(f).lower()), None)
            if found_file: sorted_files.append(found_file)
        full_paper_text = "\n\n".join([open(f, 'r', encoding='utf-8').read() for f in sorted_files])
        print("章节文本合并完成。")

        # --- 步骤 2: 准备图片路径列表 ---
        print_separator(); print("[步骤 2/4] 正在扫描图片文件夹...")
        if not os.path.isdir(images_dir): raise FileNotFoundError(f"图片目录 '{images_dir}' 不存在。")
        
        # # 我们将假设输出包内的图片目录就叫 'images'
        # images_dir_in_package = 'images'
        # ✅ 修改开始：我们将允许输出包内的图片目录是 images 或 combined_images
        images_dir_name = os.path.basename(images_dir.rstrip('/\\'))
        images_dir_in_package = images_dir_name if images_dir_name in ['images', 'combined_images'] else 'images'
        # ✅ 修改结束
        
        # image_files = [f for f in os.listdir(images_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg'))]
        
        # ✅ 修改：递归获取所有图片文件（相对于 images_dir 的相对路径）
        image_files = []
        for root, _, files in os.walk(images_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg')):
                    rel_path = os.path.relpath(os.path.join(root, file), images_dir)
                    image_files.append(rel_path)
                    
        if not image_files:
            print("[警告] 在图片目录中未找到图片。")
            image_references_md = "本文档无可用图片。"
        else:
            print(f"找到 {len(image_files)} 张图片。")
            # 构建提供给AI的、简单的、可移植的路径
            image_markdown_paths_for_ai = [f"![](%s)" % os.path.join(images_dir_in_package, f) for f in image_files]
            image_references_md = "**可用图片路径列表:**\n" + "\n".join(image_markdown_paths_for_ai)

        # --- 步骤 3: 调用AI生成讲解稿 ---
        print_separator(); print("[步骤 3/4] 正在调用AI生成讲解稿...")
        config = load_config()
        prompt_template = load_prompt_template(prompt_path)
        final_prompt = (
            f"{prompt_template}\n"
            f"{image_references_md}\n\n"
            f"---\n\n"
            f"**论文纯文本内容：**\n{full_paper_text}"
        )

        print("调用AI进行智能图文生成...")
        api_key = config['api_key']
        model = config.get('model', 'gpt-4.5-preview')
        full_speech_script = process_text(final_prompt, api_key, model)
        
        # 将生成的讲解稿保存到输出包目录中
        speech_md_path = os.path.join(output_package_dir, "speech.md")
        with open(speech_md_path, 'w', encoding='utf-8') as f: f.write(full_speech_script.strip())
        print(f"讲解稿已保存到: {speech_md_path}")

        # --- 步骤 4: 复制图片文件夹 ---
        print_separator(); print("[步骤 4/4] 正在复制图片到包目录...")
        # 目标路径是输出包里的 'images' 文件夹
        dest_images_dir = os.path.join(output_package_dir, images_dir_in_package)
        
        # 如果目标已存在，先删除再复制，确保内容最新
        if os.path.exists(dest_images_dir):
            shutil.rmtree(dest_images_dir)
        
        shutil.copytree(images_dir, dest_images_dir)
        print(f"图片已成功复制到: {dest_images_dir}")
        
        print_separator(); print(f"🎉 全部流程成功完成！"); print(f"✨ 讲解稿包已创建在: {output_package_dir}"); print_separator()

    except Exception as e:
        print(f"\n[ERR] 处理过程中发生错误: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="将章节文本和图片文件夹，打包生成一个包含讲解稿和图片的独立输出文件夹。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("sections_dir", help="包含已分割章节.md文件的输入文件夹路径。")
    parser.add_argument("images_dir", help="包含相关图片的文件夹路径。")
    parser.add_argument("output_package_dir", help="最终输出的、自包含的包文件夹的路径。")
    parser.add_argument(
        "--prompt",
        default="prompt_template/Speech_with_Text_Paths.txt",
        help="指定用于图文生成的提示词模板文件路径。\n(默认: prompt_template/Speech_with_Text_Paths.txt)"
    )
    args = parser.parse_args()
    create_package(args.sections_dir, args.images_dir, args.output_package_dir, args.prompt)


if __name__ == "__main__":
    main()