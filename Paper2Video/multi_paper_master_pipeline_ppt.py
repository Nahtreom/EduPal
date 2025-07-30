#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EduAgent Master Pipeline (Multi-Paper Fusion Version)
完整的学术论文融合到教学视频的自动化处理主流程

使用方法:
python multi_paper_master_pipeline.py path/to/multi_paper_input_dir [--output-base-dir output_directory]

例如：
python multi_paper_master_pipeline​.py ../MinerU/outputs_clean/multi_paper_inputs03
python multi_paper_master_pipeline​.py ../MinerU/outputs_clean/multi_paper_inputs02 --output-base-dir multi_test_output01

流程:
1. 调用 muti_paper_document_processor.py 进行多论文融合与切分
2. 依次调用各个Agent的pipeline处理融合后的章节
3. 收集整理生成的文件
"""

# 0718 20:08 增加 --run-until-step 参数，并根据它来控制执行流程。

import os
import sys
import subprocess
import argparse
import time
import shutil
import json
import glob
from datetime import datetime
from pathlib import Path

# --- Helper functions ---
def print_separator(char="=", length=100):
    """打印分隔线"""
    print(char * length)

def print_header():
    """打印标题"""
    print_separator("=")
    print("[EDU] EduAgent Master Pipeline - 多论文融合到教学视频的完整自动化处理")
    print_separator("=")

def print_step(step_number, step_name, description=""):
    """打印步骤信息"""
    print_separator("-")
    print(f"[STEP] 阶段 {step_number}: {step_name}")
    if description:
        print(f"   {description}")
    print(f"   开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator("-")

def run_command_with_env(command, description="", cwd=None, capture_output=False, env=None):
    """
    执行命令并处理错误，支持自定义环境变量和实时进度条显示
    """
    print(f"[PROC] 执行命令: {' '.join(command)}")
    if description:
        print(f"   {description}")
    if cwd:
        print(f"   工作目录: {cwd}")
    
    if env is None:
        env = os.environ.copy()
    else:
        base_env = os.environ.copy()
        base_env.update(env)
        env = base_env
    
    env['PYTHONUNBUFFERED'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    
    try:
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            universal_newlines=True,
            bufsize=1,
            env=env,
            cwd=cwd
        )
        
        if process.stdout is None:
            raise RuntimeError("无法获取子进程的输出流。")

        for line in iter(process.stdout.readline, ''):
            print(f"   {line.strip()}", flush=True)

        process.stdout.close()
        return_code = process.wait()
        
        if return_code == 0:
            print("[OK] 命令执行成功")
            return True
        else:
            print(f"[ERR] 命令执行失败，返回码: {return_code}")
            return False
            
    except Exception as e:
        print(f"[ERR] 命令执行出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False

# --- 流程函数 ---

def validate_inputs(input_dir):
    """验证输入目录"""
    print("[FIND] 验证输入参数...")
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"输入目录不存在或不是一个目录: {input_dir}")
    print(f"[OK] 输入目录验证通过: {input_dir}")

def setup_master_directories(final_base_path):
    """
    <-- 原master_pipeline​.py函数简化 -->
    此函数现在只接收最终的输出路径，并在此路径下创建所有子目录。
    """
    # 确保基础路径存在
    final_output_base = Path(final_base_path)
    os.makedirs(final_output_base, exist_ok=True)

    dirs = {
        'base': str(final_output_base),
        'sections': str(final_output_base / 'sections'),
        'intro_output': str(final_output_base / 'intro_agent_output'),
        'method_output': str(final_output_base / 'method_agent_output'),
        'experiment_output': str(final_output_base / 'experiment_agent_output'),
        'conclusion_output': str(final_output_base / 'conclusion_agent_output'),
        'final_results': str(final_output_base / 'final_results')
    }
    
    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)
    
    print(f"[DIR] 所有输出目录已在 '{final_output_base}' 下准备就绪。")
    return dirs

def step1_fuse_and_split_papers(input_dir, sections_dir):
    """步骤1: 调用 multi_paper_document_processor.py 进行论文融合与切分"""
    print_step(1, "多论文融合与切分", "使用 multi_paper_document_processor.py 进行处理")
    
    processor_path = Path.cwd() / "multi_paper_document_processor.py"
    if not processor_path.exists():
        raise FileNotFoundError(f"未找到融合处理脚本: {processor_path}")

    absolute_input_dir = Path(input_dir).resolve()
    absolute_sections_dir = Path(sections_dir).resolve()
    script_working_dir = processor_path.parent
    
    print(f"[INFO] 子脚本工作目录将设置为: {script_working_dir}")
    print(f"[INFO] 传递的绝对输入目录: {absolute_input_dir}")
    print(f"[INFO] 传递的绝对输出目录: {absolute_sections_dir}")

    command = [sys.executable, str(processor_path), str(absolute_input_dir), str(absolute_sections_dir)]
    
    success = run_command_with_env(
        command, 
        "融合多篇论文并切分为Introduction、Methods、Experiments、Conclusion四个章节",
        cwd=str(script_working_dir)
    )

    if not success:
        raise RuntimeError("多论文融合与切分失败")
    
    expected_sections = ['Introduction', 'Methods', 'Experiments', 'Conclusion']
    section_files = {}
    print("\n[FIND] 查找融合后的章节文件...")
    for section in expected_sections:
        search_pattern = str(absolute_sections_dir / f"*_{section}.md")
        found_files = glob.glob(search_pattern)
        if found_files:
            section_files[section] = found_files[0]
            print(f"[OK] 找到章节文件: {Path(found_files[0]).name}")
        else:
            print(f"[WARN] 未找到章节文件，模式: {search_pattern}")
    
    if not section_files:
        raise RuntimeError("未找到任何融合后的章节文件，处理失败")
    
    combined_images_dir = absolute_sections_dir / 'combined_images'
    if not combined_images_dir.is_dir():
        temp_img_dir = absolute_sections_dir / 'temp_processing' / 'temp_concatenated' / 'combined_images'
        if temp_img_dir.is_dir():
            combined_images_dir = temp_img_dir
        else:
             raise FileNotFoundError(f"未找到融合后的图片目录 'combined_images' in {absolute_sections_dir} or its temp subdirectories")
    
    print(f"[OK] 找到融合图片目录: {combined_images_dir}")
    
    return section_files, str(combined_images_dir)

def step2_process_agents(section_files, combined_images_dir, dirs):
    """步骤2: 依次调用Chapter_Agent处理融合后的章节"""
    print_step(2, "Chapter_Agent处理流程", "使用Chapter_Agent分别处理融合后的章节")
    
    agents_config = [
        {'name': 'Introduction', 'folder': 'Chapter_Agent', 'output_dir': dirs['intro_output'], 'section_key': 'Introduction', 'chapter_type': 'Intro'},
        {'name': 'Methods', 'folder': 'Chapter_Agent', 'output_dir': dirs['method_output'], 'section_key': 'Methods', 'chapter_type': 'Method'},
        {'name': 'Experiments', 'folder': 'Chapter_Agent', 'output_dir': dirs['experiment_output'], 'section_key': 'Experiments', 'chapter_type': 'Experiment'},
        {'name': 'Conclusion', 'folder': 'Chapter_Agent', 'output_dir': dirs['conclusion_output'], 'section_key': 'Conclusion', 'chapter_type': 'Conclusion'}
    ]
    
    processed_results = {}
    
    for i, agent_config in enumerate(agents_config, 1):
        agent_name = agent_config['name']
        agent_folder = agent_config['folder']
        output_dir = agent_config['output_dir']
        section_key = agent_config['section_key']
        chapter_type = agent_config['chapter_type']

        print(f"\n[BOT] 处理 {agent_name} Agent ({i}/4)")
        print(f"   章节类型: {chapter_type}")
        
        if section_key not in section_files:
            print(f"[WARN] 跳过 {agent_name} Agent: 未找到对应的融合章节文件")
            continue
            
        section_file = section_files[section_key]
        
        pipeline_script_name = "pipeline_ppt.py"
        pipeline_path_for_check = Path(agent_folder) / pipeline_script_name
        if not pipeline_path_for_check.exists():
            print(f"[WARN] 跳过 {agent_name} Agent: {pipeline_path_for_check} 不存在")
            continue
        
        command = [
            sys.executable, 
            pipeline_script_name,
            os.path.abspath(section_file),
            "--chapter", chapter_type,
            "--output-base-dir", os.path.abspath(output_dir),
            "--images-dir", os.path.abspath(combined_images_dir)
        ]

        print(f"[OPEN] 输入文件: {Path(section_file).name}")
        print(f"[DIR] 输出目录: {output_dir}")
        print(f"[IMG] 图片目录: {combined_images_dir}")
        
        env = os.environ.copy()
        env['SKIP_INTERACTIVE'] = '1'
        
        success = run_command_with_env(
            command, 
            f"处理融合后的{agent_name}章节",
            cwd=agent_folder,
            env=env
        )
        
        status = 'success' if success else 'failed'
        processed_results[agent_name] = {'status': status, 'output_dir': output_dir}
        print(f"[{'OK' if success else 'ERR'}] {agent_name} Agent 处理{'完成' if success else '失败'}")
    
    return processed_results

# def step3_collect_results(processed_results, final_results_dir):
# v-- 新增/修改的代码开始 --v
def step3_collect_results(processed_results, final_results_dir, combined_images_dir):
# ^-- 新增/修改的代码结束 --^
    """步骤3: 收集和整理所有生成的文件"""
    print_step(3, "结果收集", "收集所有Agent生成的文件到最终结果目录")
    
    speech_dir = os.path.join(final_results_dir, 'Speech')
    code_dir = os.path.join(final_results_dir, 'Code')
    os.makedirs(speech_dir, exist_ok=True)
    os.makedirs(code_dir, exist_ok=True)
    
    collected_files_count = 0
    for agent_name, result in processed_results.items():
        if result['status'] != 'success':
            continue
        
        output_dir = result['output_dir']
        print(f"\n[PKG] 收集 {agent_name} Agent 的结果 (来自: {output_dir})...")
        
        if not os.path.isdir(output_dir):
            print(f"  [WARN] 输出目录不存在，跳过: {output_dir}")
            continue

        for root, _, files in os.walk(output_dir):
            for file in files:
                src_path = os.path.join(root, file)
                if file.endswith('_code.py'):
                    new_filename = f"{agent_name}_{file}"
                    dest_path = os.path.join(code_dir, new_filename)
                    shutil.copy2(src_path, dest_path)
                    print(f"   [FILE] Code: {new_filename}")
                    collected_files_count += 1
                elif file.endswith('_speech.txt'):
                    new_filename = f"{agent_name}_{file}"
                    dest_path = os.path.join(speech_dir, new_filename)
                    shutil.copy2(src_path, dest_path)
                    print(f"   [FILE] Speech: {new_filename}")
                    collected_files_count += 1
    
    # v-- 新增/修改的代码开始 --v
    # 复制融合后的图片文件夹到最终结果目录
    print(f"\n[PKG] 复制融合后的图片文件夹...")
    dest_images_dir = os.path.join(final_results_dir, 'Code', 'combined_images')
    try:
        if not os.path.isdir(combined_images_dir):
            print(f"   [WARN] 源图片目录不存在，跳过复制: {combined_images_dir}")
        else:
            # 如果目标目录已存在，先删除，再复制，确保内容最新
            if os.path.exists(dest_images_dir):
                shutil.rmtree(dest_images_dir)
            shutil.copytree(combined_images_dir, dest_images_dir)
            print(f"   [OK] 成功将 '{combined_images_dir}' 复制到 '{dest_images_dir}'")
    except Exception as e:
        print(f"   [ERR] 复制图片目录失败: {e}")
    # ^-- 新增/修改的代码结束 --^
    
    
    print(f"\n[PROG] 总共收集了 {collected_files_count} 个最终文件。")

def print_final_summary(dirs, input_dir, processed_results, start_time):
    """打印最终总结"""
    duration = time.time() - start_time
    print_separator("=")
    print("[DONE] EduAgent Master Pipeline (多论文融合模式) 执行完成！")
    print_separator("-")
    print(f"[FILE] 输入目录: {input_dir}")
    print(f"[TIME] 总耗时: {duration:.2f} 秒 ({duration/60:.1f} 分钟)")
    print(f"[DIR] 最终输出根目录: {dirs['base']}") # 使用 'base' 键
    
    success_count = sum(1 for result in processed_results.values() if result['status'] == 'success')
    total_count = len(processed_results)
    
    print("\n[PROG] Agent处理统计:")
    print(f"   成功: {success_count}/{total_count} 个Agent")
    for agent_name, result in processed_results.items():
        print(f"   {'[OK]' if result['status'] == 'success' else '[ERR]'} {agent_name} Agent")
    
    # print(f"\n[OPEN] 生成的文件结构:")
    # print(f"   └── {Path(dirs['base']).name}/")
    # print(f"       ├── sections/ (融合后的章节和图片)")
    # print(f"       ├── ...agent_output/ (各Agent的中间过程文件)")
    # print(f"       └── final_results/ (整理后的最终结果)")
    # print(f"           ├── Speech/ (所有讲稿文件 *.txt)")
    # print(f"           └── Code/ (所有代码文件 *.py)")
    # print_separator("=")

    print(f"\n[OPEN] 生成的文件结构:")
    print(f"   └── {Path(dirs['base']).name}/")
    print(f"       ├── [DIR] sections/ (论文章节切分)")
    print(f"       ├── [DIR] intro_agent_output/ (Introduction章节处理结果)")
    print(f"       ├── [DIR] method_agent_output/ (Methods章节处理结果)")
    print(f"       ├── [DIR] experiment_agent_output/ (Experiments章节处理结果)")
    print(f"       ├── [DIR] conclusion_agent_output/ (Conclusion章节处理结果)")
    print(f"       └── [DIR] final_results/ (整理后的最终结果)")
    print(f"           ├── [DIR] Speech/ (所有讲稿文件 *.txt)")
    print(f"           └── [DIR] Code/ (所有代码文件和图片)")
    print(f"               ├── (所有代码文件 *.py)")
    print(f"               └── [DIR] combined_images/ (融合后的图片)")
    print_separator("=")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="EduAgent Master Pipeline (Multi-Paper Fusion) - 学术论文融合到教学视频的完整自动化处理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  默认输出: python multi_paper_master_pipeline.py ../MinerU/outputs_clean/muti_paper_inputs01
  指定输出: python multi_paper_master_pipeline.py ../MinerU/outputs_clean/muti_paper_inputs01 --output-base-dir ./my_project
        """
    )
    # <-- 修改 2: 调整命令行参数定义 -->
    parser.add_argument('input_dir', help='包含多篇已处理论文的输入目录路径')
    parser.add_argument(
        '--output-base-dir', 
        # 移除 default，这样如果用户不提供，它的值就是 None
        help='指定最终输出的根目录。如果未指定，将根据输入目录名自动生成 (例如: muti_paper_inputs01_output)'
    )
    
    # v-- 在这里新增/修改的代码开始 --v
    parser.add_argument(
        '--run-until-step',
        type=int,
        default=999, # 默认一个很大的数，表示执行所有步骤
        help='执行到指定的步骤后停止 (例如: 1 表示只执行章节切分)'
    )
    # ^-- 新增/修改的代码结束 --^

    args = parser.parse_args()
    start_time = time.time()
    
    try:
        print_header()
        
        # <-- 修改 3: 在 main 函数中决定最终的输出路径 -->
        if args.output_base_dir:
            # 如果用户指定了 --output-base-dir，就直接使用它
            final_output_path = args.output_base_dir
        else:
            # 如果用户未指定，则根据输入目录名生成默认路径
            input_dir_name = Path(args.input_dir).name
            final_output_path = f"{input_dir_name}_output"

        print(f"[DIR] 输入目录: {args.input_dir}")
        print(f"[DIR] 最终输出根目录将是: {final_output_path}")
        
        validate_inputs(args.input_dir)
        
        # 将决定好的最终路径传递给 setup_master_directories
        dirs = setup_master_directories(final_output_path)
        


        # section_files, combined_images_dir = step1_fuse_and_split_papers(args.input_dir, dirs['sections'])
        # processed_results = step2_process_agents(section_files, combined_images_dir, dirs)
        # # step3_collect_results(processed_results, dirs['final_results'])
        # # v-- 新增/修改的代码开始 --v
        # step3_collect_results(processed_results, dirs['final_results'], combined_images_dir)
        # # ^-- 新增/修改的代码结束 --^


        
        # v-- 在这里新增/修改的代码开始 --v
        # --- 流程控制 ---

        # 步骤1: 融合与切分
        section_files, combined_images_dir = step1_fuse_and_split_papers(args.input_dir, dirs['sections'])
        if args.run_until_step == 1:
            print("\n[INFO] 流程按 --run-until-step=1 的指示，在步骤1后停止。")
            print_final_summary(dirs, args.input_dir, {}, start_time)
            sys.exit(0) # 正常退出

        # 步骤2: Agent处理
        processed_results = step2_process_agents(section_files, combined_images_dir, dirs)
        if args.run_until_step == 2:
            print("\n[INFO] 流程按 --run-until-step=2 的指示，在步骤2后停止。")
            print_final_summary(dirs, args.input_dir, processed_results, start_time)
            sys.exit(0)

        # 步骤3: 结果收集
        step3_collect_results(processed_results, dirs['final_results'], combined_images_dir)
        # 注意：这里的 `print_final_summary` 需要 `processed_results`，所以我们在它后面检查
        if args.run_until_step == 3:
            print("\n[INFO] 流程按 --run-until-step=3 的指示，在步骤3后停止。")
            print_final_summary(dirs, args.input_dir, processed_results, start_time)
            sys.exit(0)
            
        # --- 流程控制结束 ---
        # ^-- 新增/修改的代码结束 --^


        print_final_summary(dirs, args.input_dir, processed_results, start_time)
        print("\n[DONE] Paper2Video 所有流程完成!")
        
    except KeyboardInterrupt:
        print("\n[WARN] 用户中断了Pipeline执行")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERR] Pipeline执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()