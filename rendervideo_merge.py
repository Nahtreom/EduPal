#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import subprocess
import shutil
import ast
import glob
import tempfile
from collections import defaultdict


def find_manim_files(code_dir):
    """在 code_dir 下查找所有 .py 文件。"""
    files = []
    for fn in os.listdir(code_dir):
        if fn.endswith(".py"):
            files.append(os.path.join(code_dir, fn))
    return files


def extract_class_name(py_file):
    """从 .py 文件中解析第一个 class 定义的名称。"""
    with open(py_file, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=py_file)
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            return node.name
    return None


def render_file(py_file, class_name, media_dir):
    """调用 Manim 将指定 Scene 渲染到 media_dir 下。"""
    cmd = [
        "manim",
        py_file,
        class_name,
        "--media_dir", media_dir,
        "-q", "l"     # 使用低质量加快渲染，按需调整质量参数
    ]
    print(f"🔹 Rendering {os.path.basename(py_file)} → class {class_name}")
    try:
        # 设置工作目录为 .py 文件所在目录
        # 修复图片路径无法读取的bug
        py_dir = os.path.dirname(os.path.abspath(py_file))
        subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=py_dir)
        
        # subprocess.run(cmd, check=True, capture_output=True, text=True)

        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 渲染失败: {os.path.basename(py_file)} - {e}")
        return False


def merge_videos(video_list, output_path):
    """使用ffmpeg合并多个视频文件"""
    if len(video_list) == 1:
        # 只有一个视频，直接移动
        shutil.move(video_list[0], output_path)
        print(f"📦 移动单个视频: {os.path.basename(output_path)}")
        return True
    
    try:
        # 创建临时文件列表
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for video in sorted(video_list):  # 确保按顺序合并
                f.write(f"file '{video}'\n")
            filelist_path = f.name
        
        # 使用ffmpeg合并视频
        cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0', 
            '-i', filelist_path, '-c', 'copy', output_path, '-y'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # 清理临时文件
        os.unlink(filelist_path)
        
        if result.returncode == 0:
            print(f"✅ 合并完成: {os.path.basename(output_path)} (来自 {len(video_list)} 个片段)")
            # 删除原始片段文件
            for video in video_list:
                os.remove(video)
            return True
        else:
            print(f"❌ 合并失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 合并过程出错: {str(e)}")
        return False


def collect_and_merge_videos(media_dir, video_dir):
    """递归搜索media_dir下的所有mp4文件，按原始文件名分组并合并"""
    if not os.path.exists(media_dir):
        print(f"❌ 媒体目录不存在: {media_dir}")
        return
    
    os.makedirs(video_dir, exist_ok=True)
    
    # 递归搜索所有mp4文件
    video_pattern = os.path.join(media_dir, "**", "*.mp4")
    video_files = glob.glob(video_pattern, recursive=True)
    
    if not video_files:
        print("❌ 未找到任何视频文件")
        return
    
    # 按原始Python文件名分组
    video_groups = defaultdict(list)
    
    for video_file in video_files:
        try:
            # 从路径中提取信息: .../videos/filename/480p15/classname.mp4
            path_parts = video_file.split(os.sep)
            videos_index = path_parts.index("videos") if "videos" in path_parts else -1
            
            if videos_index >= 0 and videos_index + 1 < len(path_parts):
                # 使用Python文件名作为分组键
                python_filename = path_parts[videos_index + 1]
                # 移除_code后缀
                if python_filename.endswith("_code"):
                    python_filename = python_filename[:-5]
                
                video_groups[python_filename].append(video_file)
            else:
                # 备用方案：使用原文件名
                base_name = os.path.splitext(os.path.basename(video_file))[0]
                video_groups[base_name].append(video_file)
                
        except Exception as e:
            print(f"⚠️ 处理视频文件失败 {video_file}: {e}")
    
    print(f"📊 找到 {len(video_groups)} 个视频组，共 {len(video_files)} 个片段")
    
    # 为每个组合并视频
    success_count = 0
    for group_name, videos in video_groups.items():
        output_path = os.path.join(video_dir, f"{group_name}.mp4")
        
        print(f"\n🎬 处理组: {group_name} ({len(videos)} 个片段)")
        
        if merge_videos(videos, output_path):
            success_count += 1
        else:
            print(f"❌ 合并失败: {group_name}")
    
    print(f"\n✅ 成功处理 {success_count}/{len(video_groups)} 个视频组")
    
    # 清理临时目录
    if success_count > 0:
        try:
            shutil.rmtree(media_dir)
            print(f"🗑️ 已清理临时目录")
        except Exception as e:
            print(f"⚠️ 清理临时目录失败: {e}")


def check_ffmpeg():
    """检查ffmpeg是否可用"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def main():
    parser = argparse.ArgumentParser(
        description="渲染 Paper2Video/<OUTPUT_DIR>/final_results/Code 下所有 Manim Scene 并合并同名视频到 Video。"
    )
    parser.add_argument(
        "output_dir",
        help="指定子目录名称：脚本会去 Paper2Video/<output_dir>/final_results/Code 查找 .py 并输出到 Video。"
    )
    args = parser.parse_args()

    # 检查ffmpeg
    if not check_ffmpeg():
        print("❌ 错误: 未找到ffmpeg，请先安装ffmpeg")
        print("💡 安装方法: sudo apt install ffmpeg")
        sys.exit(1)

    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(script_dir, "Paper2Video", args.output_dir, "final_results")
    code_dir = os.path.join(base_dir, "Code")
    media_dir = os.path.join(base_dir, ".manim_media")
    video_dir = os.path.join(base_dir, "Video")

    if not os.path.isdir(code_dir):
        print(f"❌ 未找到代码目录: {code_dir}")
        sys.exit(1)

    print(f"🗂️ 搜索 `{code_dir}` 下的 .py 文件...")
    py_files = find_manim_files(code_dir)
    if not py_files:
        print("⚠️ 未找到任何 .py 文件，退出。")
        sys.exit(1)

    print(f"📦 找到 {len(py_files)} 个Python文件")
    
    success_count = 0
    total_count = len(py_files)

    for i, py_file in enumerate(py_files, 1):
        cls = extract_class_name(py_file)
        if not cls:
            print(f"⚠️ [{i}/{total_count}] 跳过 {os.path.basename(py_file)}: 未找到类定义")
            continue
        
        print(f"🎬 [{i}/{total_count}] 渲染 {os.path.basename(py_file)} → {cls}")
        if render_file(py_file, cls, media_dir):
            success_count += 1
        else:
            print(f"❌ 渲染失败: {os.path.basename(py_file)}")

    print(f"\n📊 渲染完成: {success_count}/{total_count} 成功")

    if success_count > 0:
        print(f"\n📁 收集并合并视频到 `{video_dir}`...")
        collect_and_merge_videos(media_dir, video_dir)
        print("🎉 所有视频已合并并保存到Video目录！")
    else:
        print("❌ 没有成功渲染的视频")


if __name__ == "__main__":
    main() 