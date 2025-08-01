#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import glob
import subprocess
import shutil
from pathlib import Path

def check_ffmpeg():
    """检查ffmpeg是否安装"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def copy_cover_audio_files(audio_dir):
    """将cover目录下的.wav文件复制到Speech_Audio目录"""
    cover_dir = "assets/video/cover"
    
    print("🎵 开始复制cover音频文件...")
    
    # 检查cover目录是否存在
    if not os.path.exists(cover_dir):
        print(f"⚠️  cover目录不存在: {cover_dir}")
        print("   跳过cover音频文件复制")
        return True
    
    # 查找cover目录下的所有.wav文件
    cover_audio_files = glob.glob(os.path.join(cover_dir, "*.wav"))
    
    if not cover_audio_files:
        print("⚠️  cover目录下未找到.wav文件")
        print("   跳过cover音频文件复制")
        return True
    
    print(f"📁 源目录: {cover_dir}")
    print(f"📁 目标目录: {audio_dir}")
    print(f"🔍 找到 {len(cover_audio_files)} 个音频文件")
    
    # 逐个复制文件
    success_count = 0
    for audio_file in cover_audio_files:
        filename = os.path.basename(audio_file)
        target_file = os.path.join(audio_dir, filename)
        
        try:
            print(f"   📝 复制: {filename}")
            shutil.copy2(audio_file, target_file)
            
            # 验证复制是否成功
            if os.path.exists(target_file):
                file_size = os.path.getsize(target_file) / 1024  # KB
                print(f"      ✅ 成功复制: {filename} ({file_size:.1f} KB)")
                success_count += 1
            else:
                print(f"      ❌ 复制失败: {filename}")
                
        except Exception as e:
            print(f"      ❌ 复制失败: {filename} - {e}")
    
    print()
    print("🎵 cover音频文件复制完成！")
    print(f"📊 复制结果:")
    print(f"   ✅ 成功: {success_count} 个文件")
    print(f"   ❌ 失败: {len(cover_audio_files) - success_count} 个文件")
    
    if success_count > 0:
        print("   💡 这些音频文件对应cover场景，将与对应的视频文件进行合并")
    
    return success_count > 0

def find_matching_files(video_dir, audio_dir):
    """查找匹配的视频和音频文件"""
    matches = []
    
    # 获取所有mp4文件
    video_files = glob.glob(os.path.join(video_dir, "*.mp4"))
    
    for video_file in video_files:
        # 提取视频文件的基础名称（不含扩展名）
        video_basename = os.path.splitext(os.path.basename(video_file))[0]
        
        # 构建对应的音频文件名：基础名称_speech.wav
        audio_filename = f"{video_basename}_speech.wav"
        audio_file = os.path.join(audio_dir, audio_filename)
        
        # 检查音频文件是否存在
        if os.path.exists(audio_file):
            matches.append((video_file, audio_file, video_basename))
            print(f"✅ 找到匹配: {video_basename}.mp4 <-> {audio_filename}")
        else:
            print(f"⚠️  未找到匹配的音频文件: {audio_filename}")
    
    return matches

def merge_video_audio(video_file, audio_file, output_file):
    """使用ffmpeg合并视频和音频"""
    cmd = [
        'ffmpeg',
        '-i', video_file,
        '-i', audio_file,
        '-map', '0:v',
        '-map', '1:a',
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-strict', 'experimental',
        '-y',  # 覆盖输出文件
        output_file
    ]
    
    try:
        print(f"🔧 正在合并: {os.path.basename(video_file)} + {os.path.basename(audio_file)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ 合并成功: {os.path.basename(output_file)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 合并失败: {e}")
        print(f"   错误输出: {e.stderr}")
        return False

def pad_video(input_file, output_file):
    """对视频进行填充处理"""
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-af', 'apad',
        '-shortest',
        '-y',  # 覆盖输出文件
        output_file
    ]
    
    try:
        print(f"🔧 正在填充: {os.path.basename(input_file)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ 填充成功: {os.path.basename(output_file)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 填充失败: {e}")
        print(f"   错误输出: {e.stderr}")
        return False

def categorize_videos(video_files):
    """按照Introduction、Method、Experiment、Conclusion分类视频文件"""
    categories = {
        'Introduction': [],
        'Method': [],
        'Experiment': [],
        'Conclusion': []
    }
    
    for video_file in video_files:
        basename = os.path.splitext(os.path.basename(video_file))[0]
        basename_lower = basename.lower()
        
        # 分类逻辑
        if 'introduction' in basename_lower or 'intro' in basename_lower:
            categories['Introduction'].append(video_file)
        elif 'method' in basename_lower or 'approach' in basename_lower or 'methodology' in basename_lower:
            categories['Method'].append(video_file)
        elif 'experiment' in basename_lower or 'result' in basename_lower or 'evaluation' in basename_lower:
            categories['Experiment'].append(video_file)
        elif 'conclusion' in basename_lower or 'summary' in basename_lower or 'end' in basename_lower:
            categories['Conclusion'].append(video_file)
        else:
            # 默认归类到Method
            categories['Method'].append(video_file)
    
    # 对每个分类内的文件按字母顺序排序
    for category in categories:
        categories[category].sort(key=lambda x: os.path.basename(x).lower())
    
    return categories

def generate_filelist(categories, output_dir):
    """生成file.txt文件"""
    filelist_path = os.path.join(output_dir, "file.txt")
    
    try:
        with open(filelist_path, 'w', encoding='utf-8') as f:
            for category in ['Introduction', 'Method', 'Experiment', 'Conclusion']:
                # 直接添加该分类的视频文件（包含cover和内容文件）
                if categories[category]:
                    print(f"📝 添加 {category} 内容: {len(categories[category])} 个文件")
                    
                    for video_file in categories[category]:
                        basename = os.path.basename(video_file)
                        # 去掉引号，避免中文字符处理问题
                        f.write(f'file {basename}\n')
                else:
                    print(f"⚠️  {category} 部分无任何文件")
        
        print(f"✅ 文件列表生成成功: {filelist_path}")
        return True
    except Exception as e:
        print(f"❌ 文件列表生成失败: {e}")
        return False

def concat_videos(filelist_path, output_dir):
    """使用ffmpeg串联所有视频"""
    output_file = os.path.join(output_dir, "Full.mp4")
    
    # 使用相对路径，避免路径问题
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', 'file.txt',  # 使用相对路径
        '-c', 'copy',
        '-y',  # 覆盖输出文件
        'Full.mp4'  # 使用相对路径
    ]
    
    try:
        print(f"🔧 正在串联视频...")
        print(f"   使用文件列表: {os.path.basename(filelist_path)}")
        print(f"   输出文件: Full.mp4")
        print(f"   工作目录: {output_dir}")
        
        # 在输出目录下执行命令，避免路径问题
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=output_dir)
        
        # 检查输出文件是否成功生成
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
            print(f"✅ 视频串联成功: Full.mp4 ({file_size:.1f} MB)")
            return True
        else:
            print(f"❌ 视频串联失败: 输出文件未生成")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ 视频串联失败: {e}")
        print(f"   错误输出: {e.stderr}")
        return False

def main():
    # 检查参数
    if len(sys.argv) != 2:
        print("❌ 错误: 请提供输出目录名称")
        print("📝 使用方法: python3 video_audio_merge.py <OUTPUT_DIR>")
        print("📝 示例: python3 video_audio_merge.py ChatDev_short_output")
        print()
        print("🎯 功能说明:")
        print("   0. 复制cover目录下的音频文件到Speech_Audio目录")
        print("   1. 合并视频和音频文件")
        print("   2. 对合并后的视频进行填充处理")
        print("   3. 按Introduction/Method/Experiment/Conclusion分类生成file.txt")
        print("      (每个部分前面会先添加对应的cover场景视频)")
        print("   4. 串联所有视频为完整的教学视频 (Full.mp4)")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    
    # 构建路径
    base_path = f"Paper2Video/{output_dir}/final_results"
    video_dir = os.path.join(base_path, "Video")
    audio_dir = os.path.join(base_path, "Speech_Audio")
    output_base_dir = f"Paper2Video/{output_dir}/final_results"
    output_video_dir = os.path.join(output_base_dir, "Video_with_voice")
    
    print("🎬 视频音频处理工具")
    print("=" * 50)
    print(f"📁 视频目录: {video_dir}")
    print(f"🎵 音频目录: {audio_dir}")
    print(f"📤 输出目录: {output_video_dir}")
    print()
    print("🔄 处理流程:")
    print("   Step 0: 复制cover音频文件到Speech_Audio目录")
    print("   Step 1: 视频音频合并")
    print("   Step 2: 视频填充处理 (apad)")
    print("   Step 3: 生成文件列表 (file.txt，cover场景在各部分前面)")
    print("   Step 4: 视频串联 (Full.mp4)")
    print()
    
    # 检查ffmpeg
    if not check_ffmpeg():
        print("❌ 错误: 未找到ffmpeg，请先安装ffmpeg")
        print("💡 安装命令: sudo apt-get install ffmpeg")
        sys.exit(1)
    
    # 检查目录是否存在
    if not os.path.exists(video_dir):
        print(f"❌ 错误: 视频目录不存在: {video_dir}")
        sys.exit(1)
    
    if not os.path.exists(audio_dir):
        print(f"❌ 错误: 音频目录不存在: {audio_dir}")
        sys.exit(1)
    
    # 创建输出目录
    os.makedirs(output_video_dir, exist_ok=True)
    print(f"📁 创建输出目录: {output_video_dir}")
    print()
    
    # 步骤0: 复制cover音频文件
    print("🎵 执行预处理步骤: 复制cover音频文件...")
    copy_cover_audio_files(audio_dir)
    print()
    
    # 查找匹配的文件
    print("🔍 正在查找匹配的视频和音频文件...")
    matches = find_matching_files(video_dir, audio_dir)
    
    if not matches:
        print("❌ 未找到任何匹配的文件对")
        print()
        print("💡 请检查文件命名是否正确:")
        print("   视频文件: <名称>.mp4")
        print("   音频文件: <名称>_speech.wav")
        print("   例如: 1.mp4 对应 1_speech.wav")
        sys.exit(1)
    
    print(f"✅ 找到 {len(matches)} 对匹配文件")
    print()
    
    # 逐个合并文件
    success_count = 0
    total_count = len(matches)
    
    print("🎬 开始合并视频和音频...")
    for i, (video_file, audio_file, basename) in enumerate(matches, 1):
        print(f"\n[{i}/{total_count}] 处理文件: {basename}")
        
        # 构建输出文件路径
        output_file = os.path.join(output_video_dir, f"{basename}.mp4")
        
        # 合并文件
        if merge_video_audio(video_file, audio_file, output_file):
            success_count += 1
        else:
            print(f"⚠️  跳过文件: {basename}")
    
    # 显示合并结果
    print()
    print("🎉 视频音频合并完成！")
    print("=" * 50)
    print(f"📊 合并结果:")
    print(f"   ✅ 成功: {success_count} 个文件")
    print(f"   ❌ 失败: {total_count - success_count} 个文件")
    print(f"   📁 输出位置: {output_video_dir}")
    
    if success_count == 0:
        print()
        print("❌ 没有成功合并的文件，跳过后续处理")
        return
    
    # Step 2: 视频填充处理
    print()
    print("🔧 开始视频填充处理...")
    
    merged_videos = glob.glob(os.path.join(output_video_dir, "*.mp4"))
    padded_videos = []
    pad_success_count = 0
    
    for i, video_file in enumerate(merged_videos, 1):
        basename = os.path.splitext(os.path.basename(video_file))[0]
        padded_filename = f"{basename}-padded.mp4"
        padded_filepath = os.path.join(output_video_dir, padded_filename)
        
        print(f"\n[{i}/{len(merged_videos)}] 填充处理: {basename}")
        
        if pad_video(video_file, padded_filepath):
            padded_videos.append(padded_filepath)
            pad_success_count += 1
        else:
            print(f"⚠️  跳过填充: {basename}")
    
    print()
    print("🔧 视频填充处理完成！")
    print(f"📊 填充结果:")
    print(f"   ✅ 成功: {pad_success_count} 个文件")
    print(f"   ❌ 失败: {len(merged_videos) - pad_success_count} 个文件")
    
    if pad_success_count == 0:
        print()
        print("❌ 没有成功填充的文件，跳过文件列表生成")
        return
    
    # Step 3: 生成文件列表
    print()
    print("📝 开始生成文件列表...")
    print("   将在每个部分前面添加对应的cover场景视频")
    
    # 按类别分类视频文件
    categories = categorize_videos(padded_videos)
    
    # 显示分类结果
    print()
    print("📋 视频分类结果:")
    for category, files in categories.items():
        if files:
            print(f"   📂 {category}: {len(files)} 个文件")
            for file in files:
                print(f"      - {os.path.basename(file)}")
        else:
            print(f"   📂 {category}: 无文件")
    
    # 生成file.txt
    if generate_filelist(categories, output_video_dir):
        print()
        print("✅ 文件列表生成成功！")
        
        # Step 4: 视频串联
        print()
        print("🎬 执行Step 4: 视频串联...")
        
        filelist_path = os.path.join(output_video_dir, "file.txt")
        
        # 显示file.txt内容预览并验证文件存在性
        if os.path.exists(filelist_path):
            print()
            print("📄 即将串联的视频列表:")
            with open(filelist_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines:
                    print(f"   {line.strip()}")
                    # 验证文件是否存在
                    if line.strip().startswith('file '):
                        filename = line.strip()[5:]  # 去掉 'file '
                        full_path = os.path.join(output_video_dir, filename)
                        if not os.path.exists(full_path):
                            print(f"      ⚠️  文件不存在: {filename}")
                        else:
                            file_size = os.path.getsize(full_path) / (1024 * 1024)  # MB
                            print(f"      ✅ 文件存在: {file_size:.1f} MB")
            print()
        
        # 执行视频串联
        if concat_videos(filelist_path, output_video_dir):
            print()
            print("🎉 所有处理完成！")
            print("=" * 80)
            print("📋 最终结果:")
            print(f"   🎬 合并视频: {success_count} 个")
            print(f"   🔧 填充视频: {pad_success_count} 个")
            print(f"   📝 文件列表: file.txt")
            print(f"   🎦 完整视频: Full.mp4")
            print(f"   📁 位置: {output_video_dir}")
            
            # 显示最终的完整视频信息
            full_video_path = os.path.join(output_video_dir, "Full.mp4")
            if os.path.exists(full_video_path):
                file_size = os.path.getsize(full_video_path) / (1024 * 1024)  # MB
                print()
                print("🎊 成功生成完整教学视频！")
                print(f"   📁 文件路径: {full_video_path}")
                print(f"   📊 文件大小: {file_size:.1f} MB")
                print()
                print("✨ 从论文到教学视频的完整转换已完成！")
            
        else:
            print()
            print("⚠️  视频串联失败，但其他处理已完成")
            print("=" * 50)
            print("📋 部分结果:")
            print(f"   🎬 合并视频: {success_count} 个")
            print(f"   🔧 填充视频: {pad_success_count} 个")
            print(f"   📝 文件列表: file.txt")
            print(f"   ❌ 完整视频: 串联失败")
            print(f"   📁 位置: {output_video_dir}")
            print()
            print("💡 可手动执行串联命令:")
            print(f"   cd {output_video_dir}")
            print(f"   ffmpeg -f concat -safe 0 -i file.txt -c copy Full.mp4")
            
    else:
        print()
        print("⚠️  文件列表生成失败，跳过视频串联")

if __name__ == "__main__":
    main() 