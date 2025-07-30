#!/usr/bin/env python3
"""
调试脚本：检查论文处理流程的当前状态
"""

import subprocess
import psutil
import os
import json
from datetime import datetime

def check_running_processes():
    """检查正在运行的相关进程"""
    print("=" * 60)
    print("🔍 检查正在运行的相关进程")
    print("=" * 60)
    
    relevant_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            if any(keyword in cmdline.lower() for keyword in [
                'complete_pipeline.sh', 'all_pipeline_video.py', 
                'batch_coder.py', 'chapter_brain.py', 'app.py'
            ]):
                relevant_processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cmdline': cmdline,
                    'running_time': datetime.now() - datetime.fromtimestamp(proc.info['create_time'])
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if relevant_processes:
        for proc in relevant_processes:
            print(f"📋 PID: {proc['pid']}")
            print(f"   名称: {proc['name']}")
            print(f"   命令: {proc['cmdline'][:100]}...")
            print(f"   运行时间: {proc['running_time']}")
            print()
    else:
        print("❌ 没有找到相关的处理进程")
    
    return relevant_processes

def check_output_directories():
    """检查输出目录的状态"""
    print("=" * 60)
    print("📁 检查输出目录状态")
    print("=" * 60)
    
    paper2video_dir = "Paper2Video"
    if not os.path.exists(paper2video_dir):
        print("❌ Paper2Video目录不存在")
        return
    
    # 查找所有的输出目录
    output_dirs = []
    for item in os.listdir(paper2video_dir):
        item_path = os.path.join(paper2video_dir, item)
        if os.path.isdir(item_path) and item.endswith('_output'):
            output_dirs.append(item_path)
    
    if not output_dirs:
        print("❌ 没有找到输出目录")
        return
    
    for output_dir in output_dirs:
        print(f"📂 输出目录: {output_dir}")
        
        # 检查各个子目录
        subdirs = ['intro_agent_output', 'final_results']
        for subdir in subdirs:
            subdir_path = os.path.join(output_dir, subdir)
            if os.path.exists(subdir_path):
                print(f"   ✅ {subdir} 存在")
                
                # 如果是intro_agent_output，检查更详细的内容
                if subdir == 'intro_agent_output':
                    for item in os.listdir(subdir_path):
                        item_path = os.path.join(subdir_path, item)
                        if os.path.isdir(item_path):
                            file_count = len(os.listdir(item_path))
                            print(f"      📁 {item}: {file_count} 个文件")
            else:
                print(f"   ❌ {subdir} 不存在")
        print()

def check_log_files():
    """检查可能的日志文件"""
    print("=" * 60)
    print("📝 检查日志文件")
    print("=" * 60)
    
    # 查找最近的日志文件
    log_locations = [
        ".",
        "logs",
        "Paper2Video",
        "Paper2Video/logs"
    ]
    
    for location in log_locations:
        if os.path.exists(location):
            for file in os.listdir(location):
                if file.endswith('.log') or 'log' in file.lower():
                    file_path = os.path.join(location, file)
                    if os.path.isfile(file_path):
                        stat = os.stat(file_path)
                        mtime = datetime.fromtimestamp(stat.st_mtime)
                        size = stat.st_size
                        print(f"📄 {file_path}")
                        print(f"   修改时间: {mtime}")
                        print(f"   文件大小: {size} 字节")
                        
                        # 显示最后几行
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                if lines:
                                    print("   最后几行:")
                                    for line in lines[-3:]:
                                        print(f"     {line.rstrip()}")
                        except Exception as e:
                            print(f"   读取失败: {e}")
                        print()

def main():
    print("🔧 论文处理流程调试工具")
    print(f"⏰ 当前时间: {datetime.now()}")
    print()
    
    # 检查进程
    processes = check_running_processes()
    
    # 检查目录
    check_output_directories()
    
    # 检查日志
    check_log_files()
    
    # 提供建议
    print("=" * 60)
    print("💡 建议")
    print("=" * 60)
    
    if processes:
        print("✅ 有进程正在运行，系统可能在正常工作")
        print("   • 批量代码生成步骤通常需要很长时间（每页30-90秒）")
        print("   • 如果是第一次处理，可能需要等待10-30分钟")
        print("   • 建议继续等待并观察Web界面的日志输出")
    else:
        print("⚠️ 没有找到相关进程，可能已经完成或出现错误")
        print("   • 检查Web界面是否显示完成状态")
        print("   • 查看输出目录是否有生成的文件")
        print("   • 如果需要，可以重新启动处理流程")

if __name__ == "__main__":
    main() 