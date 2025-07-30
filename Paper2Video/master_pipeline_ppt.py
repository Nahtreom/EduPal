#!/usr/bin/env python3
"""
EduAgent Master Pipeline
完整的学术论文到教学视频的自动化处理主流程

使用方法:
python master_pipeline.py path/to/paper.md path/to/images [--output-base-dir output_directory]

流程:
1. 调用document_processor.py切分论文为四个章节
2. 依次调用各个Agent的pipeline处理对应章节
3. 收集整理生成的文件
"""

import os
import sys
import subprocess
import argparse
import time
import shutil
import json
from datetime import datetime
from pathlib import Path

def print_separator(char="=", length=100):
    """打印分隔线"""
    print(char * length)

def print_header():
    """打印标题"""
    print_separator("=")
    print("[EDU] EduAgent Master Pipeline - 学术论文到PPT的完整自动化处理")
    print_separator("=")

def print_step(step_number, step_name, description=""):
    """打印步骤信息"""
    print_separator("-")
    print(f"[STEP] 阶段 {step_number}: {step_name}")
    if description:
        print(f"   {description}")
    print(f"   开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator("-")

def run_command(command, description="", cwd=None, capture_output=False):
    """执行命令并处理错误"""
    return run_command_with_env(command, description, cwd, capture_output, None)

def run_command_with_env(command, description="", cwd=None, capture_output=False, env=None):
    """执行命令并处理错误，支持自定义环境变量"""
    print(f"[PROC] 执行命令: {' '.join(command)}")
    if description:
        print(f"   {description}")
    if cwd:
        print(f"   工作目录: {cwd}")
    
    # 设置环境变量
    if env is None:
        env = os.environ.copy()
    else:
        # 确保包含基本的Python环境变量
        base_env = os.environ.copy()
        base_env.update(env)
        env = base_env
    
    env['PYTHONUNBUFFERED'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    
    try:
        if capture_output:
            result = subprocess.run(command, check=True, capture_output=True, text=True, cwd=cwd, env=env)
            print("[OK] 命令执行成功")
            return result.stdout
        else:
            # 实时输出模式
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True,
                bufsize=0,  # 完全无缓冲，确保进度条实时显示
                env=env,
                cwd=cwd
            )
            
            # 实时读取并打印输出
            current_progress_line = ""  # 记录当前进度条状态
            
            if process.stdout is None:
                print("[ERR] 无法获取子进程输出")
                return False
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    clean_output = output.rstrip()
                    if clean_output:
                        # 检查是否是进度条输出
                        is_progress = any([
                            "总体进度:" in clean_output and "|" in clean_output,
                            "%" in clean_output and "|" in clean_output,
                            clean_output.startswith("进度:"),
                            "Processing:" in clean_output and "%" in clean_output,
                            clean_output.count('█') > 3,  # 进度条字符
                            clean_output.count('▓') > 3,  # 进度条字符
                            clean_output.count('░') > 3,  # 进度条字符
                            clean_output.count('■') > 3,  # 进度条字符
                            clean_output.startswith('\r')
                        ])
                        
                        if is_progress:
                            # 这是进度条，使用回车覆盖显示
                            clean_line = clean_output.lstrip('\r')
                            print(f"\r   {clean_line}", end='', flush=True)
                            current_progress_line = clean_line
                        else:
                            # 普通输出
                            if current_progress_line:
                                # 如果之前有进度条，先换行
                                print()
                                current_progress_line = ""
                            
                            # 过滤重复的前缀
                            if not clean_output.startswith('[PROG]'):
                                print(f"   {clean_output}")
                            sys.stdout.flush()
            
            # 如果最后有进度条，确保换行
            if current_progress_line:
                print()
            
            return_code = process.poll()
            if return_code == 0:
                print("[OK] 命令执行成功")
                return True
            else:
                print(f"[ERR] 命令执行失败，返回码: {return_code}")
                return False
                
    except subprocess.CalledProcessError as e:
        print(f"[ERR] 命令执行失败: {e}")
        if e.stdout:
            print("标准输出:")
            print(e.stdout)
        if e.stderr:
            print("错误输出:")
            print(e.stderr)
        return False
    except Exception as e:
        print(f"[ERR] 命令执行出现异常: {e}")
        return False

def validate_inputs(paper_path, images_dir):
    """验证输入参数"""
    print("[FIND] 验证输入参数...")
    
    # 验证论文文件
    if not os.path.exists(paper_path):
        raise FileNotFoundError(f"论文文件不存在: {paper_path}")
    
    if not paper_path.lower().endswith(('.md', '.markdown')):
        raise ValueError(f"论文文件必须是Markdown格式: {paper_path}")
    
    print(f"[OK] 论文文件验证通过: {paper_path}")
    
    # 验证图片目录
    if not os.path.exists(images_dir):
        raise FileNotFoundError(f"图片目录不存在: {images_dir}")
    
    if not os.path.isdir(images_dir):
        raise ValueError(f"图片路径不是目录: {images_dir}")
    
    print(f"[OK] 图片目录验证通过: {images_dir}")

def setup_master_directories(paper_path, output_base_dir):
    """设置主输出目录结构"""
    paper_name = Path(paper_path).stem
    
    # 创建主目录结构
    dirs = {
        'base': output_base_dir,
        'sections': os.path.join(output_base_dir, 'sections'),
        'intro_output': os.path.join(output_base_dir, 'intro_agent_output'),
        'method_output': os.path.join(output_base_dir, 'method_agent_output'),
        'experiment_output': os.path.join(output_base_dir, 'experiment_agent_output'),
        'conclusion_output': os.path.join(output_base_dir, 'conclusion_agent_output'),
        'final_results': os.path.join(output_base_dir, 'final_results')
    }
    
    # 创建所有目录
    for dir_name, dir_path in dirs.items():
        os.makedirs(dir_path, exist_ok=True)
        print(f"[DIR] 创建目录: {dir_path}")
    
    return dirs

def step1_section_splitting(paper_path, sections_dir):
    """步骤1: 调用document_processor.py切分论文"""
    print_step(1, "论文章节切分", "使用document_processor.py将论文切分为四个主要章节")
    
    # 检查document_processor.py是否存在
    document_processor_path = os.path.join(os.getcwd(), "document_processor.py")
    if not os.path.exists(document_processor_path):
        raise FileNotFoundError("未找到document_processor.py文件")
    
    # 执行切分命令
    command = [sys.executable, "document_processor.py", paper_path, sections_dir]
    success = run_command(command, "切分论文为Introduction、Methods、Experiments、Conclusion四个章节")
    
    if not success:
        raise RuntimeError("论文切分失败")
    
    # 检查切分结果
    paper_name = Path(paper_path).stem
    expected_sections = ['Introduction', 'Methods', 'Experiments', 'Conclusion']
    section_files = {}
    
    for section in expected_sections:
        section_file = os.path.join(sections_dir, f"{paper_name}_{section}.md")
        if os.path.exists(section_file):
            section_files[section] = section_file
            print(f"[OK] 找到章节文件: {section_file}")
        else:
            print(f"[WARN]  未找到章节文件: {section_file}")
    
    if not section_files:
        raise RuntimeError("未找到任何章节文件，切分可能失败")
    
    return section_files

def step2_process_agents(section_files, images_dir, dirs):
    """步骤2: 依次调用Chapter_Agent处理对应章节"""
    print_step(2, "Chapter_Agent处理流程", "使用Chapter_Agent分别处理Introduction、Methods、Experiments、Conclusion章节")
    
    # Agent配置
    agents_config = [
        {
            'name': 'Introduction',
            'folder': 'Chapter_Agent',
            'output_dir': dirs['intro_output'],
            'section_key': 'Introduction',
            'chapter_type': 'Intro'
        },
        {
            'name': 'Methods',
            'folder': 'Chapter_Agent', 
            'output_dir': dirs['method_output'],
            'section_key': 'Methods',
            'chapter_type': 'Method'
        },
        {
            'name': 'Experiments',
            'folder': 'Chapter_Agent',
            'output_dir': dirs['experiment_output'],
            'section_key': 'Experiments',
            'chapter_type': 'Experiment'
        },
        {
            'name': 'Conclusion',
            'folder': 'Chapter_Agent',
            'output_dir': dirs['conclusion_output'],
            'section_key': 'Conclusion',
            'chapter_type': 'Conclusion'
        }
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
        
        # 检查章节文件是否存在
        if section_key not in section_files:
            print(f"[WARN]  跳过 {agent_name} Agent: 未找到对应的章节文件")
            continue
            
        section_file = section_files[section_key]
        
        # 检查Agent目录是否存在
        if not os.path.exists(agent_folder):
            print(f"[WARN]  跳过 {agent_name} Agent: 目录不存在 {agent_folder}")
            continue
            
        pipeline_path = os.path.join(agent_folder, "pipeline_ppt.py")
        if not os.path.exists(pipeline_path):
            print(f"[WARN]  跳过 {agent_name} Agent: pipeline_ppt.py不存在")
            continue
        
        # 构建命令（添加章节参数）
        command = [
            sys.executable, "pipeline_ppt.py", 
            os.path.abspath(section_file),
            "--chapter", chapter_type,
            "--output-base-dir", os.path.abspath(output_dir),
            "--images-dir", os.path.abspath(images_dir)
        ]
        
        print(f"[OPEN] 输入文件: {section_file}")
        print(f"[DIR] 输出目录: {output_dir}")
        print(f"[IMG] 图片目录: {images_dir}")
        
        # 设置环境变量跳过交互式编辑
        env = os.environ.copy()
        env['SKIP_INTERACTIVE'] = '1'
        
        # 执行Agent pipeline，传递修改后的环境变量
        success = run_command_with_env(
            command, 
            f"处理{agent_name}章节",
            cwd=agent_folder,
            env=env
        )
        
        if success:
            processed_results[agent_name] = {
                'section_file': section_file,
                'output_dir': output_dir,
                'status': 'success'
            }
            print(f"[OK] {agent_name} Agent 处理完成")
        else:
            processed_results[agent_name] = {
                'section_file': section_file,
                'output_dir': output_dir,
                'status': 'failed'
            }
            print(f"[ERR] {agent_name} Agent 处理失败")
    
    return processed_results

# def step3_collect_results(processed_results, final_results_dir):
# v-- 修改函数签名，增加 images_dir 参数 --v
def step3_collect_results(processed_results, final_results_dir, images_dir):
# ^-- 修改函数签名，增加 images_dir 参数 --^

    """步骤3: 收集和整理所有生成的文件"""
    print_step(3, "结果收集", "收集所有Agent生成的文件到最终结果目录")
    
    # 创建Code主目录
    code_dir = os.path.join(final_results_dir, 'Code')
    os.makedirs(code_dir, exist_ok=True)
    
    collected_files = {
        'segmentation': [],
        'split_pages': [],
        'code_files': []
    }
    
    for agent_name, result in processed_results.items():
        if result['status'] != 'success':
            continue
            
        output_dir = result['output_dir']
        
        print(f"\n[PKG] 收集 {agent_name} Agent 的结果...")
        
        # 查找生成的文件
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                
                # 确定文件类型和目标目录
                if file.endswith('_code.py'):
                    file_type = 'code_files'
                    target_dir = code_dir
                    # 为代码文件添加章节前缀避免重名
                    new_filename = f"{agent_name}_{file}"
                elif file.endswith('_split.md'):
                    file_type = 'segmentation'
                    continue  # 暂时跳过分割文件
                elif file.endswith('.md') and 'split_pages' in root:
                    file_type = 'split_pages'
                    continue  # 暂时跳过分页文件
                else:
                    continue
                
                # 复制文件到对应的目标目录
                dest_path = os.path.join(target_dir, new_filename)
                shutil.copy2(file_path, dest_path)
                
                collected_files[file_type].append({
                    'agent': agent_name,
                    'original_path': file_path,
                    'final_path': dest_path,
                    'filename': new_filename
                })
                
                print(f"   [FILE] {file_type}: {new_filename}")
    
    # v-- 推荐的写法 --v
    # 复制原始图片文件夹到最终结果目录
    print(f"\n[PKG] 复制图片文件夹...")
    # 使用 os.path.join 连接每一级目录
    dest_images_dir = os.path.join(final_results_dir, 'Code', 'images')
    try:
        # 这里的 os.makedirs 不是必需的，因为 shutil.copytree 会自动创建目标目录
        # 但前提是它的上一级目录 (即 final_results/Code) 必须存在，
        # 而在你之前的代码中已经创建了 code_dir，所以没问题。

        # 如果目标目录已存在，先删除，再复制
        if os.path.exists(dest_images_dir):
            shutil.rmtree(dest_images_dir)
        
        # shutil.copytree 会将 images_dir 的内容复制到新建的 dest_images_dir 中
        shutil.copytree(images_dir, dest_images_dir)
        print(f"   [OK] 成功将 '{images_dir}' 复制到 '{dest_images_dir}'")

    except Exception as e:
        print(f"   [ERR] 复制图片目录失败: {e}")
    # ^-- 推荐的写法结束 --^


    # 打印处理总结
    print("\n[PROG] 处理总结:")
    print_separator("-")
    
    for file_type, files in collected_files.items():
        if files:
            agents = set(file['agent'] for file in files)
            print(f"[DIR] {file_type}: {len(files)} 个文件")
            for agent in sorted(agents):
                agent_files = [f for f in files if f['agent'] == agent]
                print(f"   • {agent}: {len(agent_files)} 个文件")
    
    return collected_files

def print_final_summary(dirs, paper_path, processed_results, start_time):
    """打印最终总结"""
    end_time = time.time()
    duration = end_time - start_time
    
    print_separator("=")
    print("[DONE] EduAgent Master Pipeline 执行完成！")
    print_separator("-")
    print(f"[FILE] 输入论文: {paper_path}")
    print(f"[TIME]  总耗时: {duration:.2f} 秒 ({duration/60:.1f} 分钟)")
    print(f"[DIR] 输出目录: {dirs['base']}")
    
    # 统计处理结果
    success_count = sum(1 for result in processed_results.values() if result['status'] == 'success')
    total_count = len(processed_results)
    
    print(f"\n[PROG] Agent处理统计:")
    print(f"   总计: {total_count} 个Agent")
    print(f"   成功: {success_count} 个")
    print(f"   失败: {total_count - success_count} 个")
    
    for agent_name, result in processed_results.items():
        status = "[OK]" if result['status'] == 'success' else "[ERR]"
        print(f"   {status} {agent_name} Agent")
    
    print(f"\n[OPEN] 生成的文件结构:")
    print(f"   ├── [DIR] sections/ (论文章节切分)")
    print(f"   ├── [DIR] intro_agent_output/ (Introduction章节处理结果)")
    print(f"   ├── [DIR] method_agent_output/ (Methods章节处理结果)")
    print(f"   ├── [DIR] experiment_agent_output/ (Experiments章节处理结果)")
    print(f"   ├── [DIR] conclusion_agent_output/ (Conclusion章节处理结果)")
    print(f"   └── [DIR] final_results/ (整理后的最终结果)")
    print(f"       ├── [DIR] Speech/ (所有讲稿文件 *.txt)")
    print(f"       └── [DIR] Code/ (所有代码文件 *.py)")
    print(f"               ├── (所有代码文件 *.py)")
    print(f"               └── [DIR] images/ (原始图片)")
    
    print_separator("=")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="EduAgent Master Pipeline - 学术论文到教学视频的完整自动化处理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
    python master_pipeline_ppt.py paper/ChatDev.md ./ChatDev_images
    python master_pipeline_ppt.py paper/ChatDev.md ./images --output-base-dir ./output
    python master_pipeline_ppt.py ../MinerU/outputs_clean/ChatDev_short_image/ChatDev_short.md ../MinerU/outputs_clean/ChatDev_short_image/images
        """
    )

    parser.add_argument(
        'paper_path',
        help='输入的学术论文Markdown文件路径'
    )
    
    parser.add_argument(
        'images_dir',
        help='图片目录路径'
    )
    
    parser.add_argument(
        '--output-base-dir',
        default='./master_output',
        help='输出基础目录路径 (默认: ./master_output)'
    )

    # 【新增】增加控制流程的参数
    parser.add_argument(
        '--run-until-step',
        type=int,
        default=999, # 默认一个很大的数，表示执行所有步骤
        help='执行到指定的步骤后停止 (例如: 1 表示只执行章节切分)'
    )
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    try:
        print_header()
        print(f"[FILE] 输入论文: {args.paper_path}")
        print(f"[IMG] 图片目录: {args.images_dir}")
        print(f"[DIR] 输出目录: {args.output_base_dir}")
        print_separator("=")
        
        # 验证输入
        validate_inputs(args.paper_path, args.images_dir)
        
        # 设置目录结构
        dirs = setup_master_directories(args.paper_path, args.output_base_dir)
        
        # # 执行主流程
        # section_files = step1_section_splitting(args.paper_path, dirs['sections'])
        # processed_results = step2_process_agents(section_files, args.images_dir, dirs)
        # # collected_files = step3_collect_results(processed_results, dirs['final_results'])
        # # v-- 修改代码开始 --v
        # # 传入 args.images_dir
        # collected_files = step3_collect_results(processed_results, dirs['final_results'], args.images_dir)
        # # ^-- 修改代码结束 --^

        # v-- 新增代码开始 --v
        # ----------------------------------------------------------------
        # 将原始图片目录完整复制到 sections 目录下，以便后续处理
        # ----------------------------------------------------------------
        print_separator("-")
        print("[COPY] 准备将图片目录复制到章节工作区...")
        
        source_images_dir = args.images_dir
        # 在 sections 目录下创建一个名为 'images' 的子目录作为目标
        dest_images_path = os.path.join(dirs['sections'], 'images')
        
        print(f"   源目录: {source_images_dir}")
        print(f"   目标目录: {dest_images_path}")
        
        try:
            # 如果目标目录已存在，先删除，以确保内容是全新的
            if os.path.exists(dest_images_path):
                shutil.rmtree(dest_images_path)
                print(f"   [INFO] 发现已存在的目标目录，已删除以进行覆盖。")
            
            # 复制整个目录树
            shutil.copytree(source_images_dir, dest_images_path)
            print(f"[OK] 图片目录已成功复制到: {dest_images_path}")
            
        except Exception as e:
            print(f"[ERR] 复制图片目录时发生错误: {e}")
            # 根据需要，您可以决定是否在这里抛出异常以停止流程
            # raise e 
        print_separator("-")
        
        # 执行主流程
        section_files = step1_section_splitting(args.paper_path, dirs['sections'])
        processed_results = step2_process_agents(section_files, args.images_dir, dirs)
        # collected_files = step3_collect_results(processed_results, dirs['final_results'])
        
        # v-- 修改代码开始 --v
        # 传入 args.images_dir
        collected_files = step3_collect_results(processed_results, dirs['final_results'], args.images_dir)
        # ^-- 修改代码结束 --^

        # 打印最终总结
        print_final_summary(dirs, args.paper_path, processed_results, start_time)
        
        print("\n[DONE] Paper2PPT 所有流程完成!")
        
    except KeyboardInterrupt:
        print("\n[WARN] 用户中断了Pipeline执行")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERR] Pipeline执行失败: {str(e)}")
        print("请检查错误信息并重试")
        sys.exit(1)

if __name__ == "__main__":
    main() 