# 支持多论文和单论文处理的完整流程脚本
# 20250730更新（原all_pipeline.py删除）

import os
import sys
import subprocess
import argparse

def print_step(title):
    print(f"\n{'='*60}")
    print(f"🛠️  {title}")
    print(f"{'='*60}\n")

def run_command(command, cwd=None):
    try:
        print(f"🔹 执行命令: {' '.join(command)}")
        result = subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=True)
        print(result.stdout)
        if result.stderr:
            print("⚠️ stderr:")
            print(result.stderr)
    except subprocess.CalledProcessError as e:
        print("❌ 命令执行失败：", e)
        print("🔻 错误输出：")
        print(e.stderr)
        sys.exit(1)

def run_command_live_output(command, cwd=None):
    print(f"🔹 实时执行命令: {' '.join(command)}\n")
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    try:
        if process.stdout:
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
        
        if process.stderr:
            stderr_output = process.stderr.read()
            if stderr_output:
                print("⚠️ stderr:")
                print(stderr_output)
            
    except Exception as e:
        print("❌ 实时输出错误：", e)

    process.wait()
    if process.returncode != 0:
        print(f"\n❌ 命令失败，退出码：{process.returncode}")
        sys.exit(1)

# --- 新增: 封装单篇论文处理流程 ---
# (此函数内容为原all_pipeline.py的 main 函数)
def run_single_file_workflow(input_pdf_path, output_dir=None):
    """处理单篇PDF文件的完整流程"""
    # 获取文件名（不带扩展名）
    filename = os.path.basename(input_pdf_path).replace(".pdf", "")

    # 构建用于 master_pipeline.py 的路径
    md_path = os.path.join("..", "MinerU", "outputs_clean", filename, f"{filename}.md")
    image_output_dir = os.path.join("..", "MinerU", "outputs_clean", filename, "images")

    # Step 1: Run MinerU
    print_step("Step 1️⃣ 运行 MinerU 提取结构化信息")

    # 修复路径问题：将输入路径转换为相对于 MinerU 的路径
    relative_pdf_path = os.path.relpath(input_pdf_path, start="MinerU")
    run_command_live_output(["python3", "run_mineru.py", relative_pdf_path], cwd="MinerU")

    # Step 2: Run master_pipeline.py
    print_step("Step 2️⃣ 执行 Paper2Video 的主处理流程")
    
    # 构建命令，如果有输出目录则添加参数
    command = ["python3", "master_pipeline.py", md_path, image_output_dir]
    if output_dir:
        command.extend(["--output-base-dir", output_dir])
        
    run_command_live_output(command, cwd="Paper2Video")
    return "单篇论文" # 返回处理模式用于最终输出

# --- 新增: 封装多篇论文处理流程 ---
def run_multi_file_workflow(input_dir_path, output_dir=None):
    """处理包含多个PDF文件的目录的完整流程"""
    # 获取目录名（不带路径）
    dir_name = os.path.basename(os.path.normpath(input_dir_path))

    # 构建用于 multi_paper_master_pipeline.py 的输入路径
    mineru_clean_output_dir = os.path.join("..", "MinerU", "outputs_clean", dir_name)

    # Step 1: Run MinerU (批量模式)
    print_step("Step 1️⃣ 运行 MinerU 批量提取结构化信息")

    # 修复路径问题：将输入目录路径转换为相对于 MinerU 的路径
    relative_input_dir = os.path.relpath(input_dir_path, start="MinerU")
    # 使用新的批量处理脚本 run_mineru_batch.py
    run_command_live_output(["python3", "run_mineru_batch.py", relative_input_dir], cwd="MinerU")

    # Step 2: Run master_pipeline.py (批量模式)
    print_step("Step 2️⃣ 执行 Paper2Video 的批量主处理流程")
    
    # 构建命令，使用新的批量处理脚本 multi_paper_master_pipeline.py
    # 错误-可能是字符问题？python3 multi_paper_master_pipeline.py ../MinerU/outputs_clean/multi_paper_inputs4
    # 正确-python3 multi_paper_master_pipeline​.py ../MinerU/outputs_clean/multi_paper_inputs4
    command = ["python3", "multi_paper_master_pipeline​.py", mineru_clean_output_dir]
    if output_dir:
        command.extend(["--output-base-dir", output_dir])
        
    run_command_live_output(command, cwd="Paper2Video")
    return "多篇论文批量" # 返回处理模式用于最终输出

# --- 重构 原all_pipeline.py的main 函数作为调度器 ---
def main(input_path, output_dir=None):
    processing_mode = ""

    # 核心改动：判断输入路径是文件还是目录
    if os.path.isfile(input_path):
        print("🔍 检测到输入为单个文件，启动单篇处理模式...")
        if not input_path.endswith(".pdf"):
            print("❌ 请提供 PDF 文件路径（以 .pdf 结尾）")
            sys.exit(1)
        # 调用单文件处理流程
        processing_mode = run_single_file_workflow(input_path, output_dir)

    elif os.path.isdir(input_path):
        print("📂 检测到输入为目录，启动批量处理模式...")
        # 调用多文件处理流程
        processing_mode = run_multi_file_workflow(input_path, output_dir)
        
    else:
        print(f"❌ 错误：输入路径 '{input_path}' 不是一个有效的文件或目录。")
        sys.exit(1)

    print_step(f"✅ 所有流程完成！{processing_mode}处理成功 🎉")
    print("\n📋 完整流程总结:")
    print(f"   - 输入路径: {input_path}")
    print(f"   - 处理模式: {processing_mode}")
    print("   ✅ Step 1: MinerU 提取结构化信息")
    print("   ✅ Step 2: Paper2Video 主处理流程")
    print(f"\n🎉 {processing_mode}到教学内容的处理已完成！")

if __name__ == "__main__":
    # 更新命令行参数，支持 单篇pdf 和 多篇pdf 的文件夹输入
    parser = argparse.ArgumentParser(description="运行完整的论文到教学内容处理流程（支持单文件和目录）")
    parser.add_argument("input_path", help="输入的PDF文件路径 或 包含PDF文件的目录路径")
    parser.add_argument("--output-dir", help="输出目录路径（可选）")
    
    args = parser.parse_args()
    main(args.input_path, args.output_dir)