#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import re

def parse_speech_txt(speech_txt_path):
    """
    解析Speech.txt文件，提取音频文件信息
    
    Args:
        speech_txt_path (str): Speech.txt文件路径
    
    Returns:
        list: 包含(音频文件名, 时长)的元组列表
    """
    audio_info = []
    
    try:
        with open(speech_txt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 解析格式：filename.wav	duration
            parts = line.split('\t')
            if len(parts) != 2:
                print(f"⚠️  警告：跳过格式不正确的行: {line}")
                continue
            
            audio_file = parts[0].strip()
            duration_str = parts[1].strip()
            
            # 提取时长数字（去掉's'后缀）
            duration_match = re.match(r'([\d.]+)s?', duration_str)
            if duration_match:
                duration = float(duration_match.group(1))
                audio_info.append((audio_file, duration))
            else:
                print(f"⚠️  警告：无法解析时长: {duration_str}")
    
    except FileNotFoundError:
        print(f"❌ 错误：找不到文件 {speech_txt_path}")
        return []
    except Exception as e:
        print(f"❌ 错误：读取文件时发生错误: {str(e)}")
        return []
    
    return audio_info

def get_corresponding_code_file(audio_filename):
    """
    根据音频文件名生成对应的代码文件名
    
    Args:
        audio_filename (str): 音频文件名，如 "Conclusion_ChatDev_short_Conclusion_split_页1_speech.wav"
    
    Returns:
        str: 对应的代码文件名，如 "Conclusion_ChatDev_short_Conclusion_split_页1_code.py"
    """
    # 移除.wav扩展名
    base_name = os.path.splitext(audio_filename)[0]
    
    # 将_speech替换为_code，并添加.py扩展名
    if base_name.endswith('_speech'):
        code_filename = base_name[:-7] + '_code.py'  # 移除'_speech'，添加'_code.py'
    else:
        # 如果不以_speech结尾，直接添加_code.py
        code_filename = base_name + '_code.py'
    
    return code_filename

def run_wait_time_calculator(duration, code_file_path):
    """
    运行wait_time_calculator.py脚本
    
    Args:
        duration (float): 目标时长
        code_file_path (str): 代码文件路径
    
    Returns:
        bool: 是否成功执行
    """
    try:
        cmd = ['python3', 'Paper2Video/wait_time_calculator.py', str(duration), code_file_path]
        print(f"🔧 执行命令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"⚠️  stderr: {result.stderr}")
        
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败，退出码: {e.returncode}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ 执行过程中发生错误: {str(e)}")
        return False

def main():
    if len(sys.argv) != 2:
        print("❌ 错误: 请提供输出目录名")
        print("📝 使用方法: python3 audio_video_sync.py <OUTPUT_DIR>")
        print("📝 示例: python3 audio_video_sync.py ChatDev_short_output")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    
    # 构建路径
    speech_txt_path = f"Paper2Video/{output_dir}/final_results/Speech_Audio/Speech.txt"
    code_dir = f"Paper2Video/{output_dir}/final_results/Code"
    
    print("🎬 开始音视频对齐处理")
    print(f"📄 Speech.txt路径: {speech_txt_path}")
    print(f"📁 Code目录: {code_dir}")
    print("=" * 50)
    
    # 检查必要的文件和目录是否存在
    if not os.path.exists(speech_txt_path):
        print(f"❌ 错误：Speech.txt文件不存在: {speech_txt_path}")
        sys.exit(1)
    
    if not os.path.exists(code_dir):
        print(f"❌ 错误：Code目录不存在: {code_dir}")
        sys.exit(1)
    
    # 解析Speech.txt文件
    print("📖 解析Speech.txt文件...")
    audio_info = parse_speech_txt(speech_txt_path)
    
    if not audio_info:
        print("❌ 没有找到有效的音频信息")
        sys.exit(1)
    
    print(f"✅ 找到 {len(audio_info)} 个音频文件")
    
    # 处理每个音频文件
    success_count = 0
    total_count = len(audio_info)
    
    for i, (audio_file, duration) in enumerate(audio_info, 1):
        print(f"\n🎵 [{i}/{total_count}] 处理: {audio_file}")
        print(f"   时长: {duration}s")
        
        # 生成对应的代码文件名
        code_filename = get_corresponding_code_file(audio_file)
        code_file_path = os.path.join(code_dir, code_filename)
        
        print(f"   对应代码文件: {code_filename}")
        
        # 检查代码文件是否存在
        if not os.path.exists(code_file_path):
            print(f"   ❌ 代码文件不存在: {code_file_path}")
            continue
        
        # 运行wait_time_calculator.py
        print(f"   🔧 调整代码文件以匹配音频时长...")
        if run_wait_time_calculator(duration, code_file_path):
            print(f"   ✅ 处理完成")
            success_count += 1
        else:
            print(f"   ❌ 处理失败")
    
    print("\n" + "=" * 50)
    print(f"🎊 音视频对齐处理完成！")
    print(f"📊 处理结果: {success_count}/{total_count} 个文件成功处理")
    
    if success_count == total_count:
        print("✨ 所有文件都已成功对齐！")
    elif success_count > 0:
        print(f"⚠️  部分文件处理失败，请检查错误信息")
    else:
        print("❌ 所有文件处理都失败了，请检查配置和文件路径")

if __name__ == "__main__":
    main() 