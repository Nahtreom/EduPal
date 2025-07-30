#!/usr/bin/env python3
"""
交互式文件编辑器
支持查看和编辑指定目录下的Code和Speech文件

使用方法:
python interactive_editor.py <基础地址>

示例:
python interactive_editor.py ./master_output
python interactive_editor.py /path/to/Paper2Video/output
"""

import os
import sys
import subprocess
import argparse
import shutil
from pathlib import Path

def print_separator(char="=", length=80):
    """打印分隔线"""
    print(char * length)

def print_header():
    """打印标题"""
    print_separator("=")
    print("🛠️  交互式文件编辑器 - Code & Speech 文件管理")
    print_separator("=")

def find_files(base_dir):
    """查找Code和Speech目录下的文件"""
    print(f"\n🔍 搜索目录: {base_dir}")
    
    # 可能的路径组合
    possible_paths = [
        # 直接在基础目录下
        (os.path.join(base_dir, "Code"), os.path.join(base_dir, "Speech")),
        # 在final_results子目录下
        (os.path.join(base_dir, "final_results", "Code"), os.path.join(base_dir, "final_results", "Speech")),
        # 在master_output子目录下
        (os.path.join(base_dir, "master_output", "final_results", "Code"), 
         os.path.join(base_dir, "master_output", "final_results", "Speech")),
    ]
    
    code_dir = None
    speech_dir = None
    
    # 查找存在的目录
    for code_path, speech_path in possible_paths:
        if os.path.exists(code_path) or os.path.exists(speech_path):
            if os.path.exists(code_path):
                code_dir = code_path
            if os.path.exists(speech_path):
                speech_dir = speech_path
            break
    
    if not code_dir and not speech_dir:
        print("❌ 未找到Code或Speech目录")
        print("   请确保输入的基础地址包含以下结构之一:")
        print("   • <基础地址>/Code 和 <基础地址>/Speech")
        print("   • <基础地址>/final_results/Code 和 <基础地址>/final_results/Speech")
        print("   • <基础地址>/master_output/final_results/Code 和 <基础地址>/master_output/final_results/Speech")
        return None, None, []
    
    all_files = []
    
    # 收集Code文件
    if code_dir and os.path.exists(code_dir):
        print(f"📁 Code目录: {code_dir}")
        code_files = []
        for file in os.listdir(code_dir):
            if file.endswith('.py'):
                file_path = os.path.join(code_dir, file)
                code_files.append({
                    'type': 'Code',
                    'filename': file,
                    'path': file_path,
                    'size': os.path.getsize(file_path)
                })
        
        if code_files:
            print(f"   找到 {len(code_files)} 个Python代码文件")
            all_files.extend(code_files)
        else:
            print("   未找到Python代码文件")
    else:
        print("📁 未找到Code目录")
    
    # 收集Speech文件
    if speech_dir and os.path.exists(speech_dir):
        print(f"📁 Speech目录: {speech_dir}")
        speech_files = []
        for file in os.listdir(speech_dir):
            if file.endswith('.txt'):
                file_path = os.path.join(speech_dir, file)
                speech_files.append({
                    'type': 'Speech',
                    'filename': file,
                    'path': file_path,
                    'size': os.path.getsize(file_path)
                })
        
        if speech_files:
            print(f"   找到 {len(speech_files)} 个讲稿文件")
            all_files.extend(speech_files)
        else:
            print("   未找到讲稿文件")
    else:
        print("📁 未找到Speech目录")
    
    return code_dir, speech_dir, all_files

def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f}KB"
    else:
        return f"{size_bytes/(1024*1024):.1f}MB"

def display_files(all_files):
    """显示所有文件列表"""
    if not all_files:
        print("❌ 没有找到任何文件")
        return
    
    print(f"\n📋 找到 {len(all_files)} 个文件:")
    print_separator("-")
    print(f"{'序号':<4} {'类型':<8} {'文件名':<40} {'大小':<10}")
    print_separator("-")
    
    for i, file_info in enumerate(all_files, 1):
        size_str = format_file_size(file_info['size'])
        print(f"{i:<4} {file_info['type']:<8} {file_info['filename']:<40} {size_str:<10}")
    
    print_separator("-")

def preview_file(file_path, lines=10):
    """预览文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content_lines = f.readlines()
        
        print(f"\n📄 文件预览 (前{lines}行):")
        print_separator("-")
        
        for i, line in enumerate(content_lines[:lines], 1):
            print(f"{i:3d} | {line.rstrip()}")
        
        if len(content_lines) > lines:
            print(f"... (还有 {len(content_lines) - lines} 行)")
        
        print_separator("-")
        print(f"📊 文件统计: 总共 {len(content_lines)} 行")
        
    except Exception as e:
        print(f"❌ 无法读取文件: {e}")

def edit_file(file_path):
    """使用vim编辑文件"""
    try:
        print(f"📝 使用vim编辑文件: {os.path.basename(file_path)}")
        result = subprocess.run(['vim', file_path], check=True)
        print("✅ 文件编辑完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 编辑失败: {e}")
        return False
    except FileNotFoundError:
        print("❌ 未找到vim编辑器")
        print(f"💡 文件路径: {file_path}")
        print("   您可以手动使用其他编辑器打开此文件")
        return False
    except KeyboardInterrupt:
        print("\n⚠️  编辑被中断")
        return False

def search_files(all_files, search_term):
    """搜索文件"""
    matched_files = []
    
    for file_info in all_files:
        if (search_term.lower() in file_info['filename'].lower() or 
            search_term.lower() in file_info['type'].lower()):
            matched_files.append(file_info)
    
    return matched_files

def interactive_mode(all_files):
    """交互式操作模式"""
    if not all_files:
        print("❌ 没有可操作的文件")
        return
    
    print("\n💡 交互式操作说明:")
    print("   • 输入数字序号 - 选择文件进行操作")
    print("   • 输入 'list' - 重新显示文件列表")
    print("   • 输入 'search <关键词>' - 搜索文件")
    print("   • 输入 'background' - 为manim代码添加背景图")
    print("   • 输入 'help' - 显示帮助信息")
    print("   • 输入 'quit' 或 'exit' - 退出程序")
    print("   • 按 Ctrl+C - 退出程序")
    
    while True:
        try:
            user_input = input("\n🎯 请输入命令: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 退出程序")
                break
            
            if user_input.lower() == 'list':
                display_files(all_files)
                continue
            
            if user_input.lower() == 'help':
                print("\n📖 帮助信息:")
                print("   数字序号      - 选择对应文件进行查看/编辑")
                print("   list          - 显示所有文件")
                print("   search <词>   - 搜索包含关键词的文件")
                print("   background    - 为manim代码添加背景图")
                print("   help          - 显示此帮助")
                print("   quit/exit     - 退出程序")
                continue
            
            if user_input.lower().startswith('search '):
                search_term = user_input[7:].strip()
                if search_term:
                    matched_files = search_files(all_files, search_term)
                    if matched_files:
                        print(f"\n🔍 搜索 '{search_term}' 的结果:")
                        display_files(matched_files)
                    else:
                        print(f"❌ 未找到包含 '{search_term}' 的文件")
                else:
                    print("❌ 请输入搜索关键词")
                continue
            
            if user_input.lower() == 'background':
                handle_background_operation(all_files)
                continue
            
            # 尝试解析为数字序号
            try:
                file_index = int(user_input) - 1
                if 0 <= file_index < len(all_files):
                    selected_file = all_files[file_index]
                    handle_file_operation(selected_file)
                else:
                    print(f"❌ 无效的序号，请输入 1-{len(all_files)} 之间的数字")
            except ValueError:
                print("❌ 无效的命令，请输入数字序号或有效命令")
            print("   输入 'help' 查看帮助信息")
        
        except KeyboardInterrupt:
            print("\n👋 退出程序")
            break
        except EOFError:
            print("\n👋 退出程序")
            break

def handle_file_operation(file_info):
    """处理单个文件的操作"""
    print(f"\n📂 选择的文件: {file_info['filename']}")
    print(f"   类型: {file_info['type']}")
    print(f"   大小: {format_file_size(file_info['size'])}")
    print(f"   路径: {file_info['path']}")
    
    while True:
        try:
            action = input("\n🎯 请选择操作 (1-预览 / 2-编辑 / 3-返回): ").strip()
            
            if action == '1':
                preview_file(file_info['path'])
            elif action == '2':
                edit_file(file_info['path'])
            elif action == '3':
                break
            else:
                print("❌ 请输入 1、2 或 3")
        
        except KeyboardInterrupt:
            print("\n⚠️  操作被中断")
            break
        except EOFError:
            print("\n⚠️  操作被中断")
            break

def handle_background_operation(all_files):
    """处理背景图添加操作"""
    print("\n🖼️  为Manim代码添加背景图功能")
    
    # 查找Code文件
    code_files = [f for f in all_files if f['type'] == 'Code']
    
    if not code_files:
        print("❌ 未找到任何Code文件，无法添加背景图")
        return
    
    # 获取Code目录路径（从第一个Code文件推断）
    code_dir = os.path.dirname(code_files[0]['path'])
    print(f"📁 Manim代码目录: {code_dir}")
    print(f"📊 找到 {len(code_files)} 个Python代码文件")
    
    try:
        # 获取背景图路径
        bg_path = input("\n📂 请输入背景图完整路径: ").strip()
        
        if not bg_path:
            print("❌ 背景图路径不能为空")
            return
        
        # 检查背景图文件是否存在
        if not os.path.exists(bg_path):
            print(f"❌ 背景图文件不存在: {bg_path}")
            return
        
        # 检查是否是图片文件
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')
        if not bg_path.lower().endswith(valid_extensions):
            print("⚠️  警告: 文件可能不是图片格式")
            print(f"   支持的格式: {', '.join(valid_extensions)}")
            confirm = input("是否继续? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes']:
                print("❌ 操作已取消")
                return
        
        # 获取背景图文件名
        bg_filename = os.path.basename(bg_path)
        bg_dest_path = os.path.join(code_dir, bg_filename)
        
        print(f"\n🔧 准备执行背景图添加操作...")
        print(f"   源文件: {bg_path}")
        print(f"   目标位置: {bg_dest_path}")
        
        # 检查目标文件是否已存在
        if os.path.exists(bg_dest_path):
            print(f"⚠️  目标位置已存在同名文件: {bg_filename}")
            overwrite = input("是否覆盖现有文件? (y/N): ").strip().lower()
            if overwrite not in ['y', 'yes']:
                print("❌ 操作已取消")
                return
        
        try:
            # 步骤1: 拷贝背景图到Code文件夹
            print(f"\n📋 步骤1: 拷贝背景图到Code文件夹...")
            shutil.copy2(bg_path, bg_dest_path)
            print(f"✅ 背景图拷贝成功: {bg_filename}")
            
            # 步骤2: 执行background.py，使用相对路径
            print(f"\n📋 步骤2: 修改Manim代码文件...")
            relative_bg_path = bg_filename  # 使用相对路径
            command = ["python", "background.py", code_dir, relative_bg_path]
            
            print(f"🔹 执行命令: {' '.join(command)}")
            
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            print("✅ Manim代码修改成功!")
            
            if result.stdout:
                print("📄 输出信息:")
                print(result.stdout)
            
            if result.stderr:
                print("⚠️  警告信息:")
                print(result.stderr)
            
            print(f"\n🎉 背景图添加完成!")
            print(f"   • 背景图已拷贝到: {bg_dest_path}")
            print(f"   • 所有Python代码文件已更新")
            print(f"   • 可以直接运行manim命令渲染视频")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ background.py执行失败: {e}")
            if e.stdout:
                print("📄 标准输出:")
                print(e.stdout)
            if e.stderr:
                print("📄 错误输出:")
                print(e.stderr)
            
            # 如果background.py失败，询问是否删除已拷贝的文件
            cleanup = input("\n🗑️  是否删除已拷贝的背景图文件? (y/N): ").strip().lower()
            if cleanup in ['y', 'yes']:
                try:
                    os.remove(bg_dest_path)
                    print(f"✅ 已删除: {bg_dest_path}")
                except Exception as cleanup_error:
                    print(f"❌ 删除失败: {cleanup_error}")
            
        except FileNotFoundError:
            print("❌ 未找到 background.py 文件")
            print("   请确保在当前目录或系统PATH中存在 background.py")
            
            # 询问是否删除已拷贝的文件
            cleanup = input("\n🗑️  是否删除已拷贝的背景图文件? (y/N): ").strip().lower()
            if cleanup in ['y', 'yes']:
                try:
                    os.remove(bg_dest_path)
                    print(f"✅ 已删除: {bg_dest_path}")
                except Exception as cleanup_error:
                    print(f"❌ 删除失败: {cleanup_error}")
            
        except IOError as e:
            print(f"❌ 文件拷贝失败: {e}")
        except Exception as e:
            print(f"❌ 执行过程中出现错误: {e}")
            
    except KeyboardInterrupt:
        print(f"\n⚠️  背景图添加被中断")
    except EOFError:
        print(f"\n⚠️  输入被中断")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="交互式文件编辑器 - 查看和编辑Code与Speech文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
    python interactive_editor.py ./master_output
    python interactive_editor.py /path/to/Paper2Video/output
    python interactive_editor.py ./Paper2Video/master_output/final_results
        """
    )
    
    parser.add_argument(
        'base_dir',
        help='基础目录路径，包含Code和Speech文件夹'
    )
    
    args = parser.parse_args()
    
    # 检查基础目录是否存在
    if not os.path.exists(args.base_dir):
        print(f"❌ 目录不存在: {args.base_dir}")
        sys.exit(1)
    
    if not os.path.isdir(args.base_dir):
        print(f"❌ 不是有效的目录: {args.base_dir}")
        sys.exit(1)
    
    try:
        print_header()
        
        # 查找文件
        code_dir, speech_dir, all_files = find_files(args.base_dir)
        
        if not all_files:
            print("\n❌ 未找到任何可编辑的文件")
            print("请检查目录结构是否正确")
            sys.exit(1)
        
        # 显示文件列表
        display_files(all_files)
        
        # 询问是否进入交互模式
        while True:
            try:
                choice = input("\n🤔 是否进入交互模式进行查看/编辑? (y/N): ").strip().lower()
                if choice in ['y', 'yes']:
                    interactive_mode(all_files)
                    break
                elif choice in ['n', 'no', '']:
                    print("👋 程序结束")
                    break
                else:
                    print("❌ 请输入 y 或 n")
            except KeyboardInterrupt:
                print("\n👋 程序被中断")
                break
            except EOFError:
                print("\n👋 程序结束")
                break
    
    except Exception as e:
        print(f"\n❌ 程序执行出错: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 