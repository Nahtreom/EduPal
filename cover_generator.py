# /home/EduAgent/cover_generator.py

import os
import re
import argparse
import json
from pathlib import Path
from typing import List, Dict
import shutil

# 导入您提供的API客户端
from api_call import APIClient

CONFIG_FILE_PATH = Path("/home/EduAgent/config.json")
# --- 新增：定义Manim代码模板的源文件路径 ---
SOURCE_MANIM_TEMPLATE_PATH = Path("/home/EduAgent/assets/video/cover/1Introduction_code.py")


def load_config() -> Dict:
    """
    从 config.json 文件加载 API 密钥和模型配置。
    """
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        if "api_key" not in config or "model" not in config:
            raise KeyError("配置文件中必须包含 'api_key' 和 'model' 字段。")
        return config
    except FileNotFoundError:
        print(f"❌ 错误: 配置文件不存在于 {CONFIG_FILE_PATH}")
        raise
    except json.JSONDecodeError:
        print(f"❌ 错误: 配置文件 {CONFIG_FILE_PATH} 格式不正确，无法解析为JSON。")
        raise
    except KeyError as e:
        print(f"❌ 错误: {e}")
        raise

def get_paper_info_with_llm(md_path: Path, api_client: APIClient) -> dict:
    """
    使用LLM从Markdown文件的开头部分提取标题、作者和单位。 # <--- 修改
    """
    if not md_path.exists():
        print(f"❌ 错误: Markdown文件不存在: {md_path}")
        return None

    # 读取文件开头的一小部分，通常包含标题和作者
    content_chunk = md_path.read_text(encoding='utf-8').strip()[:1500] # <--- 修改 (略微增加读取量以确保单位信息被捕获)
    
    # --- Prompt for LLM ---
    # <--- 修改: 更新Prompt以提取单位信息 ---
    prompt = f"""
    你是一个信息提取助手。请从下面的论文文本片段中提取'标题'、'所有作者'和'所有单位'。（注意要严格按照原论文的作者和单位顺序）
    请严格按照以下JSON格式至多返回前三个作者和最后三个作者（至多六位作者），至多返回前三个单位。作者和单位之间都用英文逗号","分隔，不要添加任何额外的解释。

    JSON格式示例:
    {{
      "title": "提取出的论文标题",
      "authors": "作者一,作者二,作者三",
      "affiliations": "单位一,单位二"
    }}

    待处理的文本片段如下:
    ---
    {content_chunk}
    ---
    """
    
    print(f"🤖 调用LLM从 {md_path.name} 提取标题、作者和单位...") # <--- 修改
    response_str = api_client.call_api_with_text(prompt)
    
    try:
        # 清理并解析JSON响应
        if "```json" in response_str:
            response_str = re.search(r"```json\n(.*)\n```", response_str, re.DOTALL).group(1)
        
        info = json.loads(response_str)
        # <--- 修改: 检查新增的affiliations字段 ---
        if "title" not in info or "authors" not in info or "affiliations" not in info:
            raise KeyError("响应JSON中缺少'title'、'authors'或'affiliations'字段。")

        print(f"   - ✅ 提取成功 - 标题: {info['title']}")
        print(f"   - ✅ 提取成功 - 作者: {info['authors']}")
        print(f"   - ✅ 提取成功 - 单位: {info['affiliations']}") # <--- 新增
        return info

    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        print(f"❌ 解析LLM响应失败: {e}")
        print(f"   - 原始响应: {response_str}")
        # 失败时的备用方案：使用简单的正则提取
        title_match = re.search(r"^#\s+(.*)", content_chunk, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else "备用提取：未找到标题"
        # <--- 修改: 备用方案中增加单位信息 ---
        return {"title": title, "authors": "备用提取：未找到作者", "affiliations": "备用提取：未找到单位"}


def fuse_titles_with_llm(titles: List[str], api_client: APIClient) -> str:
    """
    使用LLM将多个论文标题融合成一个总标题。
    """
    print("🤖 调用LLM来融合标题...")
    print(f"   - 原始标题: {titles}")
    
    titles_str = "\n- ".join(titles)
    
    # --- Prompt for LLM ---
    prompt = f"""
    你是一位专业的学术视频制作人。请将以下多个论文标题融合成一个精炼、全面且吸引人的总结性英文标题。
    这个标题将用作一个视频的封面，该视频会同时讲解这些论文。
    请只返回最终的标题文本，不要包含任何其他说明或引导词。

    原始标题列表:
    - {titles_str}
    """
    
    fused_title = api_client.call_api_with_text(prompt).strip()
    fused_title = fused_title.strip('"\'')

    print(f"   - ✅ 融合后的标题: {fused_title}")
    return fused_title


def create_manim_script_from_template(source_template_path: Path, destination_script_path: Path, title: str, authors: str, affiliations: str): # <--- 修改: 增加affiliations参数
    """
    从源模板读取内容，更新标题、作者和单位，然后写入到目标路径。 # <--- 修改
    """
    if not source_template_path.exists():
        print(f"❌ 错误: Manim模板文件不存在: {source_template_path}")
        return

    # 从源模板文件读取内容
    content = source_template_path.read_text(encoding='utf-8')
    
    # 替换标题、作者和单位
    content = re.sub(r'title_text = ".*"', f'title_text = "{title}"', content)
    content = re.sub(r'author_text = ".*"', f'author_text = "{authors}"', content)
    content = re.sub(r'affiliation_text = ".*"', f'affiliation_text = "{affiliations}"', content) # <--- 新增: 替换单位信息
    
    # 将修改后的内容写入最终的目标文件
    destination_script_path.write_text(content, encoding='utf-8')
    print(f"✅ 成功根据模板创建Manim脚本: {destination_script_path}")

def generate_speech_file(speech_dir: Path, title: str, is_batch: bool):
    """生成封面场景对应的讲稿文件。"""
    speech_file = speech_dir / "1Introduction_speech.txt"
    template = "今天我们来讲解一下以【{title}】为主题的几篇论文" if is_batch else "今天我们来讲解一下【{title}】这篇论文"
    speech_content = template.format(title=title)
        
    speech_dir.mkdir(parents=True, exist_ok=True)
    speech_file.write_text(speech_content, encoding='utf-8')
    print(f"✅ 成功生成讲稿文件: {speech_file}")

def main():
    parser = argparse.ArgumentParser(description="使用LLM根据论文信息生成封面代码和讲稿。")
    parser.add_argument("--miner-u-dir", required=True, type=Path, help="MinerU的输出目录（包含.md文件）。")
    parser.add_argument("--p2v-code-dir", required=True, type=Path, help="Paper2Video的Code输出目录。")
    parser.add_argument("--p2v-speech-dir", required=True, type=Path, help="Paper2Video的Speech输出目录。")
    parser.add_argument("--is-batch", action='store_true', help="是否为批量模式。")
    args = parser.parse_args()

    try:
        # 从JSON文件加载配置
        config = load_config()
        api_client = APIClient(api_key=config['api_key'], model=config['model'])
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        # 错误已在load_config中打印，直接退出
        exit(1)

    all_titles = []
    all_authors = []
    all_affiliations = [] # <--- 新增: 用于存储所有单位信息的列表

    if args.is_batch:
        print("🔍 批量模式: 正在查找并处理所有论文的.md文件...")
        md_files = sorted(list(args.miner_u_dir.glob('*/*.md')))
    else:
        print("🔍 单文件模式: 正在查找.md文件...")
        md_files = sorted(list(args.miner_u_dir.glob('*.md')))

    if not md_files:
        print(f"❌ 致命错误: 在目录 {args.miner_u_dir} 中未找到任何.md文件。")
        exit(1)

    for md_file in md_files:
        info = get_paper_info_with_llm(md_file, api_client)
        if info:
            all_titles.append(info["title"])
            all_authors.append(info["authors"])
            all_affiliations.append(info["affiliations"]) # <--- 新增: 收集单位信息

    if not all_titles:
        print("❌ 致命错误: 未能从任何.md文件中提取有效信息。")
        exit(1)

    # --- 新增: 单位信息去重逻辑 ---
    print("\n🔬 正在处理和去重单位信息...")
    unique_affiliations = set()
    for aff_group in all_affiliations:
        # 按逗号分割，并去除每个单位前后的空格
        affs = [aff.strip() for aff in aff_group.split(',') if aff.strip()]
        unique_affiliations.update(affs)
    
    # 将去重后的单位排序并合并成一个字符串
    final_affiliations = ", ".join(sorted(list(unique_affiliations)))
    print(f"   - ✅ 去重后的单位: {final_affiliations}")
    # --- 去重逻辑结束 ---

    # 准备最终的标题和作者
    if args.is_batch and len(all_titles) > 1:
        final_title = fuse_titles_with_llm(all_titles, api_client)
        final_authors = ", ".join(all_authors)
    else:
        # final_title = all_titles if all_titles else ""
        # final_authors = all_authors if all_authors else ""
        final_title = all_titles[0] if all_titles else ""
        final_authors = all_authors[0] if all_authors else ""
        
    # 替换脚本中的特殊字符（主要是双引号），防止代码语法错误
    final_title_escaped = final_title.replace('"', '\\"')
    final_authors_escaped = final_authors.replace('"', '\\"')
    final_affiliations_escaped = final_affiliations.replace('"', '\\"') # <--- 新增: 转义单位信息

    
    # 执行文件更新和创建
    destination_manim_path = args.p2v_code_dir / "1Introduction_code.py"
    # <--- 修改: 调用函数时传入处理好的单位信息 ---
    create_manim_script_from_template(SOURCE_MANIM_TEMPLATE_PATH, destination_manim_path, final_title_escaped, final_authors_escaped, final_affiliations_escaped)
    
    generate_speech_file(args.p2v_speech_dir, final_title, args.is_batch)

    # --- 新增步骤：复制logo文件 ---
    print("\n📋 开始复制logo文件...")
    source_logo_path = Path("/home/EduAgent/logo_test.png")
    destination_dir = args.p2v_code_dir

    if source_logo_path.exists():
        try:
            shutil.copy(source_logo_path, destination_dir)
            print(f"   - ✅ 成功复制logo: {source_logo_path} -> {destination_dir / source_logo_path.name}")
        except Exception as e:
            print(f"   - ❌ 复制logo时出错: {e}")
    else:
        print(f"   - ⚠️ 警告: 未找到源logo文件，跳过复制: {source_logo_path}")
    # --- 复制步骤结束 ---

    # --- 新增功能：复制其余的py文件 (除了1Introduction_code.py) ---这一步其实不需要，之前步骤已经实现了
    # print("\n📋 开始复制其余的code.py文件...")
    # source_cover_dir = Path("/home/EduAgent/cover/")
    # dest_code_dir = args.p2v_code_dir

    # try:
    #     # 查找所有py文件，并排除1Introduction_code.py
    #     py_files_to_copy = [f for f in source_cover_dir.glob('*.py') if f.name != '1Introduction_code.py']
    #     if not py_files_to_copy:
    #         print("   - ⚠️ 警告: 在源目录中没有找到其他需要复制的.py文件。")
    #     else:
    #         for source_file in py_files_to_copy:
    #             destination_file = dest_code_dir / source_file.name
    #             shutil.copy(source_file, destination_file)
    #             print(f"   - ✅ 成功复制: {source_file.name} -> {destination_file}")
    # except Exception as e:
    #     print(f"   - ❌ 复制.py文件时出错: {e}")
    # --- py文件复制结束 ---

    # --- 新增功能：复制所有的txt文件 ---
    print("\n📋 开始复制所有的speech.txt文件...")
    dest_speech_dir = args.p2v_speech_dir

    try:
        txt_files_to_copy = list(source_cover_dir.glob('*.txt'))
        if not txt_files_to_copy:
            print("   - ⚠️ 警告: 在源目录中没有找到需要复制的.txt文件。")
        else:
            for source_file in txt_files_to_copy:
                # 跳过已经由generate_speech_file函数生成的介绍讲稿
                if source_file.name == '1Introduction_speech.txt':
                    continue
                destination_file = dest_speech_dir / source_file.name
                shutil.copy(source_file, destination_file)
                print(f"   - ✅ 成功复制: {source_file.name} -> {destination_file}")
    except Exception as e:
        print(f"   - ❌ 复制.txt文件时出错: {e}")
    # --- txt文件复制结束 ---


    print("\n🎉 封面生成任务完成！")

if __name__ == "__main__":
    main()