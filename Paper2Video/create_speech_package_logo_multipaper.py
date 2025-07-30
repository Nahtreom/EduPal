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
    # 添加更详细的错误输出
    print("[ERR] 错误: 无法导入 'api_call'.")
    print("      请确保 api_call.py 与此脚本在同一目录中。")
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
        # 这是您的“多论文”新Prompt
        default_prompt = """
你是一位顶级的学术分析师和内容整合专家。
你的任务是将一份已经【融合了多篇论文】的核心内容，与一个“可用图片路径列表”，智能地融合成一份【综合性】的图文并茂讲解稿。请务必使用中文！

你的输入包含两部分：
1. **论文纯文本内容**：已经融合了多篇论文精华的文本。
2. **可用图片路径列表**：一个Markdown列表，列出了所有可用的图片。

你的任务要求如下：
1. **识别与整合**：
   - 首先，从融合的文本中**识别出不同论文的核心观点或主题**。
   - 在你的讲解稿中，对这些观点进行**对比、总结或按主题重新组织**，以创造一个有深度、有逻辑的全新叙述结构。
   - 在讲解时，可以推断并使用“一些研究者提出...”或“另一种主流方法是...”这样的句式来区分不同的思想流派。

2. **智能图文匹配**：理解融合内容和图片之间的关系。当讲解到某个特定主题或方法时，从图片列表中选择最相关的图片，并将其Markdown引用插入到最恰当的位置。
3. **使用正确路径**：**必须**使用“可用图片路径列表”中提供的完整路径来引用图片。
4. **内容与格式**：
   - 使用一级标题（`#`）来定义整个讲解稿的总主题。
   - 使用二级标题（`##`）来组织不同的主题、方法或对比分析。
   - 讲解风格需口语化、流畅自然，同时保持学术严谨性。
5. **学术深度要求**：
   - 对融合内容中的不同方法、实验结果进行**比较分析**。
   - 突出整个主题领域的**核心挑战、不同方案的优劣以及未来的发展方向**。
6. **输出**：只输出最终的、结构清晰的、包含综合分析和图文引用的单一Markdown讲解稿。

"""
        prompt_dir = os.path.dirname(template_path)
        if prompt_dir: os.makedirs(prompt_dir, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f: f.write(default_prompt)
        print(f"[INFO] 已创建默认提示词模板: {template_path}")
    with open(template_path, 'r', encoding='utf-8') as f: return f.read().strip()

def apply_watermark_to_content(content: str, watermark_src_path: str, output_package_dir: str, images_dir_name_in_package: str) -> str:
    print_separator('-')
    print("[后续处理] 正在应用右上角水印...")
    if not os.path.exists(watermark_src_path):
        print(f"[警告] 水印图片源文件未找到: {watermark_src_path}。跳过添加水印。")
        return content

    watermark_filename = os.path.basename(watermark_src_path)
    dest_images_dir = os.path.join(output_package_dir, images_dir_name_in_package)
    watermark_dest_path = os.path.join(dest_images_dir, watermark_filename)
    
    os.makedirs(dest_images_dir, exist_ok=True)
    shutil.copy(watermark_src_path, watermark_dest_path)
    print(f"水印图片已复制到: {watermark_dest_path}")

    markdown_image_path = os.path.join(images_dir_name_in_package, watermark_filename).replace('\\', '/')
    
    # 这里使用了您要求的小尺寸 width="80"
    watermark_html = f"""
<div style="position: fixed; top: 20px; right: 20px; z-index: 9999; opacity: 0.5; pointer-events: none;">
  <img src="{markdown_image_path}" alt="Watermark" width="40">
</div>

"""
    print("水印HTML代码已生成。")
    return watermark_html + content


def create_package(sections_dir: str, images_dir: str, output_package_dir: str, prompt_path: str, watermark_path: str = None):
    # ▲▲▲ 修改点：增加了 watermark_path 参数 ▲▲▲
    section_order = ['Intro', 'Method', 'Experiment', 'Conclusion']
    try:
        print_separator(); print(f"[{format_time()}] 开始创建讲解稿包...")
        if os.path.exists(output_package_dir):
            print(f"[警告] 输出目录 '{output_package_dir}' 已存在。")
        else:
            os.makedirs(output_package_dir)
            print(f"已创建输出目录: {output_package_dir}")

        print_separator(); print("[步骤 1/4] 正在合并章节文件...")
        if not os.path.isdir(sections_dir): raise FileNotFoundError(f"章节目录 '{sections_dir}' 不存在。")
        all_section_files = glob.glob(os.path.join(sections_dir, '*.md'))
        sorted_files = []
        for section in section_order:
            found_file = next((f for f in all_section_files if section.lower() in os.path.basename(f).lower()), None)
            if found_file: sorted_files.append(found_file)
        full_paper_text = "\n\n".join([open(f, 'r', encoding='utf-8').read() for f in sorted_files])
        print("章节文本合并完成。")

        print_separator(); print("[步骤 2/4] 正在准备提供给AI的图片列表...")
        if not os.path.isdir(images_dir): raise FileNotFoundError(f"图片目录 '{images_dir}' 不存在。")
        
        images_dir_name = os.path.basename(images_dir.rstrip('/\\'))
        images_dir_in_package = images_dir_name if images_dir_name in ['images', 'combined_images'] else 'images'
        
        # ▼▼▼ 核心修正点：排除水印图片，不让AI看到它 ▼▼▼
        watermark_filename_to_exclude = os.path.basename(watermark_path) if watermark_path else None
        if watermark_filename_to_exclude:
            print(f"[INFO] 水印图片 '{watermark_filename_to_exclude}' 将不会被送入AI模型，仅用于后期处理。")

        image_files_for_ai = []
        for root, _, files in os.walk(images_dir):
            for file in files:
                if file == watermark_filename_to_exclude:
                    continue
                
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg')):
                    rel_path = os.path.relpath(os.path.join(root, file), images_dir)
                    image_files_for_ai.append(rel_path.replace('\\', '/'))
    

        if not image_files_for_ai:
            print("[警告] 在图片目录中未找到可用的内容图片。")
            image_references_md = "本文档无可用图片。"
        else:
            print(f"找到 {len(image_files_for_ai)} 张内容图片提供给AI。")
            image_markdown_paths_for_ai = [f"![](%s)" % os.path.join(images_dir_in_package, f) for f in image_files_for_ai]
            image_references_md = "**可用图片路径列表:**\n" + "\n".join(image_markdown_paths_for_ai)

        print_separator(); print("[步骤 3/4] 正在调用AI生成讲解稿...")
        config = load_config()
        prompt_template = load_prompt_template(prompt_path)
        final_prompt = (f"{prompt_template}\n{image_references_md}\n\n---\n\n**论文纯文本内容：**\n{full_paper_text}")

        print("调用AI进行智能图文生成...")
        api_key = config['api_key']
        model = config.get('model', 'gpt-4.5-preview')
        full_speech_script = process_text(final_prompt, api_key, model).strip()
        
        print_separator(); print("[步骤 4/4] 正在整合最终包...")
        
        # 4a. 复制所有源图片（包括水印）到输出目录
        dest_images_dir = os.path.join(output_package_dir, images_dir_in_package)
        if os.path.exists(dest_images_dir):
            shutil.rmtree(dest_images_dir)
        shutil.copytree(images_dir, dest_images_dir)
        print(f"所有源图片已成功复制到: {dest_images_dir}")

        # 4b. 对内容应用水印（如果需要）
        final_content_to_write = full_speech_script
        if watermark_path:
            final_content_to_write = apply_watermark_to_content(
                full_speech_script, 
                watermark_path, 
                output_package_dir, 
                images_dir_in_package
            )
        
        # 4c. 将最终内容写入文件
        speech_md_path = os.path.join(output_package_dir, "speech.md")
        with open(speech_md_path, 'w', encoding='utf-8') as f:
            f.write(final_content_to_write)
        print(f"最终讲解稿已保存到: {speech_md_path}")
        
        print_separator(); print(f"🎉 全部流程成功完成！"); print(f"✨ 讲解稿包已创建在: {output_package_dir}"); print_separator()

    except Exception as e:
        print(f"\n[ERR] 处理过程中发生错误: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="将【多篇】章节文本和图片文件夹，打包生成一个包含【综合性】讲解稿和图片的独立输出文件夹。",
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
        #加水印
    parser.add_argument(
        "--watermark",
        help="可选：指定要添加为水印的图片路径。\n如果提供，该图片将被复制到输出包并固定在 .md 文件的右上角。"
    )
    
    args = parser.parse_args()
    
    create_package(args.sections_dir, args.images_dir, args.output_package_dir, args.prompt, args.watermark)


if __name__ == "__main__":
    main()