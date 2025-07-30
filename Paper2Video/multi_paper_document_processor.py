#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多文档智能处理与融合程序

功能：
1.  输入一个包含多篇已处理论文的目录 (来自 MinerU 的 outputs_clean)。
2.  (Phase 1) 对每篇论文进行物理分割，切分为 Abstract, Introduction, Methods, Experiments, Conclusion 五个部分。
3.  (Phase 2) 对分割后的章节进行物理拼接，并智能处理图片路径，为融合做准备。
4.  (Phase 3) 调用大模型对拼接后的章节进行智能融合，输出最终的四个核心章节。

使用方法: python multi_paper_document_processor.py <待处理论文总目录> <最终输出目录>
python multi_paper_document_processor.py ../MinerU/outputs_clean/muti_paper_inputs01 test_sections
"""

import os
import sys
import json
import re
import shutil
import glob
from pathlib import Path

# <--- CHANGE HERE: 导入两个函数
try:
    from api_call import process_text, process_text_with_images
except ImportError:
    print("错误: 未找到 'api_call.py' 文件。请确保它与本脚本在同一目录下。")
    sys.exit(1)

# --- 全局配置 ---
SECTIONS_TO_SPLIT = ["Abstract", "Introduction", "Methods", "Experiments", "Conclusion"]
SECTIONS_TO_FUSE = ["Introduction", "Methods", "Experiments", "Conclusion"]
FUSION_PROMPT_MAP = {
    'Introduction': 'Intro_Integration.txt',
    'Methods': 'Method_Integration.txt',
    'Experiments': 'Experiment_Integration.txt',
    'Conclusion': 'Conclusion_Integration.txt',
}


# --- 1. 配置与模板加载 ---

def load_config():
    """从config.json加载配置"""
    config_file = Path("config.json")
    if not config_file.exists():
        # <--- 不用base_url，在 api_call.py 中是硬编码
        default_config = {
            "api_key": "your-api-key-here",
            "model": "gpt-4o"
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        print(f"已创建默认配置文件 {config_file}，请修改其中的 api_key")
        sys.exit(1)
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    if config.get("api_key") == "your-api-key-here":
        print("请在 config.json 中设置正确的 api_key")
        sys.exit(1)
    return config

# ... (prepare_prompt_templates, load_prompt_template, read_file_content, parse_section_mapping 函数保持不变) ...
def prepare_prompt_templates():
    """检查并创建所有需要的prompt模板文件"""
    prompt_dir = Path("prompt_template")
    prompt_dir.mkdir(exist_ok=True)

    # 1. 分割用的模板
    split_prompt_path = prompt_dir / "Central.txt"
    if not split_prompt_path.exists():
        split_prompt_content = """你是一名学术写作助理，请你阅读以下完整文章内容，识别出其中属于以下五个部分的章节标题：

1. Abstract
2. Introduction
3. 方法 (Methods / Methodology)
4. 实验 (Experiments / Experimental Setup / Evaluation)
5. 结论 (Conclusion / Discussion / Summary)

请你以如下格式输出每个部分对应的章节标题（只给出大标题即可）：

Abstract: <对应章节标题>
Introduction: <对应章节标题>
Methods: <对应章节标题>
Experiments: <对应章节标题>
Conclusion: <对应章节标题>

以下是文章内容："""
        split_prompt_path.write_text(split_prompt_content, encoding='utf-8')
        print(f"已创建分割prompt模板: {split_prompt_path}")

    # 2. 融合用的模板
    fusion_prompts = {
        "Intro_Integration.txt": "融合以下多篇论文的引言(Introduction)部分...",
        "Method_Integration.txt": "融合以下多篇论文的方法(Method)部分...",
        "Experiment_Integration.txt": "融合以下多篇论文的实验(Experiment)部分...",
        "Conclusion_Integration.txt": "融合以下多篇论文的结论(Conclusion)部分...",
    }
    
    base_fusion_prompt = """你是一位顶级的学术研究员，擅长整合和提炼多篇论文的核心思想。
你的任务是阅读下面提供的、来自多篇论文的同一章节内容，以及它们的摘要作为上下文。请将这些内容融合、重写并总结成一个全新的、连贯流畅的章节。

要求：
1.  **逻辑清晰**：确保最终的文本结构合理，逻辑递进。
2.  **保留核心**：保留每篇论文最关键的观点、方法或发现。
3.  **识别异同**：在融合时，可以 subtly 指出不同论文间的共通之处或独特方法。
4.  **处理图片**：文中的图片引用格式为 `![图片描述](路径/图片文件名)`。在你的输出中，必须完整地保留这些图片引用，并确保它们在行文逻辑中被恰当地提及。不要省略任何图片！
5.  **提供上下文**：下面提供了每篇论文的摘要，帮助你理解各篇论文的整体贡献。

---
[论文摘要上下文]
{abstracts_content}
---

---
[待融合的章节内容]
{section_content}
---

请现在开始你的融合写作："""

    for filename, description in fusion_prompts.items():
        prompt_path = prompt_dir / filename
        if not prompt_path.exists():
            prompt_path.write_text(base_fusion_prompt, encoding='utf-8')
            print(f"已创建融合prompt模板: {prompt_path}")

def load_prompt_template(filename: str) -> str:
    template_file = Path("prompt_template") / filename
    if not template_file.exists():
        raise FileNotFoundError(f"Prompt模板文件未找到: {template_file}")
    return template_file.read_text(encoding='utf-8')

def read_file_content(file_path: Path) -> str:
    return file_path.read_text(encoding='utf-8')

def parse_section_mapping(model_output: str) -> dict:
    sections = {}
    for line in model_output.strip().split('\n'):
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2 and parts[0].strip() in SECTIONS_TO_SPLIT:
                sections[parts[0].strip()] = parts[1].strip()
    return sections

# v-- 代码移植开始 --v
# 注释：以下三个函数 (extract_section_number, is_subsection, find_section_content) 
# 从能够正确处理子章节的 "document_processor.py" 脚本中完整移植而来，
# 以替换原有脚本中功能不完善的 find_section_content 函数。
def extract_section_number(title_line: str) -> str:
    """从标题行中提取章节编号"""
    # 移除开头的#号和空格
    title_text = re.sub(r'^#+\s*', '', title_line).strip()
    # 提取开头的数字部分（可能包含小数点）
    match = re.match(r'^(\d+(?:\.\d+)*)', title_text)
    return match.group(1) if match else ""

def is_subsection(parent_num: str, current_num: str) -> bool:
    """判断current_num是否是parent_num的子章节"""
    if not parent_num or not current_num:
        return False
    
    # 如果current_num以parent_num开头且后面跟着小数点，则是子章节
    return current_num.startswith(parent_num + ".")

def find_section_content(markdown_content: str, section_identifier: str) -> str:
    """在markdown中找到指定章节的内容（移植自单篇处理脚本的完善版本）"""
    lines = markdown_content.split('\n')
    content_lines = []
    in_section = False
    found_line = None
    
    # 不再打印详细搜索过程，以保持多论文处理流程的输出整洁
    # print(f"  正在搜索章节: '{section_identifier}'")
    
    # 创建多种可能的标题模式
    pattern1 = rf'^#+\s*{re.escape(section_identifier)}\s*$'
    pattern2 = rf'^#+\s*.*{re.escape(section_identifier)}.*$'
    section_text_only = re.sub(r'^\d+(\.\d+)*\s*', '', section_identifier).strip()
    pattern3 = rf'^#+\s*[\d.]*\s*{re.escape(section_text_only)}\s*$' if section_text_only else None
    
    patterns = [p for p in [pattern1, pattern2, pattern3] if p]
    
    # 搜索匹配的标题行
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if line_stripped.startswith('#'):
            for pattern in patterns:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    found_line = i
                    in_section = True
                    content_lines.append(line)
                    break
            if found_line is not None:
                break
    
    if found_line is None:
        print(f"  [警告] 未能找到章节标题: '{section_identifier}'")
        return ""
    
    # 获取起始标题的级别和章节号
    start_title_level_match = re.match(r'^(#+)', lines[found_line])
    if not start_title_level_match:
        # 如果匹配的行不是有效的标题行（虽然理论上不会发生），则返回空
        return ""
    start_title_level = len(start_title_level_match.group(1))
    start_section_number = extract_section_number(lines[found_line])
    
    # 从找到的行开始，收集内容直到下一个非子章节标题
    for i in range(found_line + 1, len(lines)):
        line = lines[i]
        
        # 检查是否是标题行
        if re.match(r'^#+\s*\S', line):
            current_level_match = re.match(r'^(#+)', line)
            if not current_level_match: continue
            
            current_level = len(current_level_match.group(1))
            current_section_number = extract_section_number(line)
            
            # 判断是否应该停止收集
            should_stop = False
            if current_level <= start_title_level:
                # 遇到同级或更高级标题
                if start_section_number and current_section_number and is_subsection(start_section_number, current_section_number):
                    # 是子章节的特殊情况（例如 2. vs 2.1），虽然级别相同但应继续
                    pass
                else:
                    # 不是子章节，停止
                    should_stop = True

            if should_stop:
                break
        
        content_lines.append(line)
    
    result = '\n'.join(content_lines)
    return result.strip()
# ^-- 代码移植结束 --^


# --- Phase 1: 物理分割 ---
def split_single_paper(paper_dir: Path, temp_split_dir: Path, config: dict):
    paper_name = paper_dir.name
    print(f"\n--- [Phase 1] 正在分割论文: {paper_name} ---")
    
    md_files = list(paper_dir.glob("*.md"))
    if not md_files:
        print(f"  [错误] 在 {paper_dir} 中未找到.md文件，跳过。")
        return False

    markdown_path = md_files[0]
    paper_content = read_file_content(markdown_path)
    
    split_prompt_template = load_prompt_template("Central.txt")
    full_prompt = f"{split_prompt_template}\n\n{paper_content}"
    
    print("  正在调用LLM分析章节结构...")
    sections_map = {}
    try:
        mapping_result = process_text(
            full_prompt, 
            config["api_key"], 
            config["model"]
        )
        sections_map = parse_section_mapping(mapping_result)
        print("  LLM章节映射解析完成:")
        for sec, title in sections_map.items():
            print(f"    - {sec}: {title}")
    except Exception as e:
        print(f"  [错误] LLM调用失败: {e}")
        return False
    
    # ++++++++++++++++++++++++++++++++
    # +++    增加Abstract：启发式后备规则   +++
    # ++++++++++++++++++++++++++++++++
    if 'Abstract' not in sections_map:
        print("  [信息] LLM未返回Abstract，启动启发式规则进行查找...")
        # 使用正则表达式查找 '# ABSTRACT' (不区分大小写, 独占一行)
        abstract_match = re.search(r'^#\s+ABSTRACT\s*$', paper_content, re.IGNORECASE | re.MULTILINE)
        
        if abstract_match:
            # 从匹配到的文本中提取出干净的标题 (例如 "ABSTRACT")
            found_title = abstract_match.group(0).strip('#').strip()
            sections_map['Abstract'] = found_title
            print(f"  [成功] 启发式规则找到Abstract，标题为: '{found_title}'")
        else:
            print("  [警告] 启发式规则也未能找到Abstract。")
    # ++++++++++++++++++++++++++++++++
    # +++        修改结束           +++
    # ++++++++++++++++++++++++++++++++

    # 检查所有必需章节是否都被识别
    missing_sections = [sec for sec in SECTIONS_TO_SPLIT if sec not in sections_map]
    if missing_sections:
        print(f"  [警告] LLM或启发式规则未能识别出以下必需章节: {', '.join(missing_sections)}。分割可能不完整。")
    else:
        print("  [成功] 已识别所有必需章节。")


    paper_output_dir = temp_split_dir / paper_name
    paper_output_dir.mkdir(exist_ok=True)
    
    for section_name in SECTIONS_TO_SPLIT:
        if section_name in sections_map:
            section_title = sections_map[section_name]
            content = find_section_content(paper_content, section_title)
            if content:
                out_path = paper_output_dir / f"{paper_name}_{section_name}.md"
                out_path.write_text(content, encoding='utf-8')
                print(f"  已保存: {out_path.name}")
            else:
                # 如果找到了标题但没找到内容，也创建空文件并警告
                print(f"  [警告] 找到了标题 '{section_title}' 但未能提取内容。")
                out_path = paper_output_dir / f"{paper_name}_{section_name}.md"
                out_path.write_text(f"# {section_name}\n\n(未能提取到内容)", encoding='utf-8')
    return True

# ... (后续原代码concatenate_sections, fuse_all_sections, main 等保持不变) ...
# --- Phase 2: 物理拼接 ---
def concatenate_sections(paper_dirs: list, temp_split_dir: Path, temp_concat_dir: Path):
    paper_names = [p.name for p in paper_dirs]
    print(f"\n--- [Phase 2] 正在拼接 {len(paper_names)} 篇论文的章节 ---")
    
    combined_images_dir_name = "combined_images"
    
    for section_name in SECTIONS_TO_FUSE:
        print(f"  正在处理章节: {section_name}")
        
        all_content = []
        for paper_dir in paper_dirs:
            paper_name = paper_dir.name
            section_file = temp_split_dir / paper_name / f"{paper_name}_{section_name}.md"
            
            if section_file.exists():
                content = section_file.read_text(encoding='utf-8')
                
                # 将 ![...](images/...) 替换为 ![...](combined_images/PaperName_images/...)
                rewritten_content = re.sub(
                    r"!\[(.*?)\]\((images/.*?)\)",
                    lambda m: f"![{m.group(1)}]({combined_images_dir_name}/{paper_name}_{m.group(2)})",
                    content
                )
                
                header = f"\n\n---\n\n# 原文: {paper_name}\n\n"
                all_content.append(header + rewritten_content)

                original_images_dir = paper_dir / "images"
                if original_images_dir.is_dir():
                    target_images_dir = temp_concat_dir / combined_images_dir_name / f"{paper_name}_images"
                    if not target_images_dir.exists():
                        shutil.copytree(original_images_dir, target_images_dir)
                        print(f"    - 已拷贝图片: {original_images_dir} -> {target_images_dir}")
            
        if all_content:
            concat_filename = f"{'+'.join(paper_names)}_{section_name}_CONCAT.md"
            concat_filepath = temp_concat_dir / concat_filename
            concat_filepath.write_text('\n'.join(all_content), encoding='utf-8')
            print(f"  已拼接保存至: {concat_filepath.name}")

# --- Phase 3: 智能融合 ---
def fuse_all_sections(paper_names: list, temp_concat_dir: Path, final_output_dir: Path, config: dict):
    print(f"\n--- [Phase 3] 正在智能融合章节 ---")
    
    temp_split_dir = temp_concat_dir.parent / "temp_split_sections"
    abstracts_content = []
    for paper_name in paper_names:
        abstract_file = temp_split_dir / paper_name / f"{paper_name}_Abstract.md"
        if abstract_file.exists():
            abstracts_content.append(f"摘要 ({paper_name}):\n{abstract_file.read_text(encoding='utf-8')}\n")
    
    full_abstracts_context = "---\n".join(abstracts_content)

    for section_name in SECTIONS_TO_FUSE:
        print(f"  正在融合章节: {section_name}")
        
        concat_filename = f"{'+'.join(paper_names)}_{section_name}_CONCAT.md"
        concat_filepath = temp_concat_dir / concat_filename
        
        if not concat_filepath.exists():
            print(f"    [警告] 找不到拼接文件 {concat_filename}，跳过融合。")
            continue
            
        section_content = concat_filepath.read_text(encoding='utf-8')
        
        prompt_filename = FUSION_PROMPT_MAP.get(section_name)
        if not prompt_filename:
            print(f"    [警告] 找不到 {section_name} 的融合prompt，跳过。")
            continue
            
        fusion_prompt_template = load_prompt_template(prompt_filename)
        final_prompt = fusion_prompt_template.replace("{abstracts_content}", full_abstracts_context)
        final_prompt = final_prompt.replace("{section_content}", section_content)
        
        print(f"    调用 {config['model']} (多模态) 进行融合...")
        try:
            fused_content = process_text_with_images(
                text=final_prompt,
                api_key=config["api_key"],
                model=config["model"],
                base_path=str(temp_concat_dir) 
            )
            
            final_filename = f"{'+'.join(paper_names)}_{section_name}.md"
            final_filepath = final_output_dir / final_filename
            final_filepath.write_text(fused_content, encoding='utf-8')
            print(f"  🎉 融合成功! 已保存至: {final_filepath}")

        except Exception as e:
            print(f"    [错误] 融合API调用失败: {e}")
            
    combined_images_dir = temp_concat_dir / "combined_images"
    if combined_images_dir.exists():
        final_images_dir = final_output_dir / combined_images_dir.name
        if final_images_dir.exists():
            shutil.rmtree(final_images_dir)
        shutil.copytree(combined_images_dir, final_images_dir)
        print(f"\n已将所有图片拷贝至: {final_images_dir}")

# --- 主函数 ---
def main():
    if len(sys.argv) != 3:
        print("使用方法: python multi_paper_document_processor.py <待处理论文总目录> <最终输出目录>")
        print("示例: python multi_paper_document_processor.py ../MinerU/outputs_clean/muti_paper_inputs01 ./fused_sections")
        sys.exit(1)
        
    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    
    if not input_dir.is_dir():
        print(f"错误: 输入目录 '{input_dir}' 不存在或不是一个目录。")
        sys.exit(1)
        
    paper_dirs = [d for d in input_dir.iterdir() if d.is_dir()]
    if not paper_dirs:
        print(f"错误: 在 '{input_dir}' 中没有找到任何论文子目录。")
        sys.exit(1)
        
    print(f"检测到 {len(paper_dirs)} 篇论文待处理: {[p.name for p in paper_dirs]}")

    try:
        config = load_config()
        prepare_prompt_templates()

        temp_dir = output_dir / "temp_processing"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_split_dir = temp_dir / "temp_split_sections"
        temp_concat_dir = temp_dir / "temp_concatenated"
        temp_split_dir.mkdir(parents=True, exist_ok=True)
        temp_concat_dir.mkdir(parents=True, exist_ok=True)
        
        successful_splits = []
        for paper_dir in paper_dirs:
            if split_single_paper(paper_dir, temp_split_dir, config):
                successful_splits.append(paper_dir)
        
        if not successful_splits:
            print("\n所有论文分割失败，程序终止。")
            sys.exit(1)

        concatenate_sections(successful_splits, temp_split_dir, temp_concat_dir)

        output_dir.mkdir(exist_ok=True)
        fuse_all_sections(
            [p.name for p in successful_splits], 
            temp_concat_dir, 
            output_dir, 
            config
        )

        print(f"\n处理完成！临时文件保留在 {temp_dir} 供调试。可手动删除。")
        print(f"最终融合结果已保存在: {output_dir}")

    except Exception as e:
        print(f"\n程序发生严重错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()