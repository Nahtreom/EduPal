#!/bin/bash

# final_pipeline.sh - 执行Step 6-9的最终处理步骤
# 使用方法: bash final_pipeline.sh <output_dir>

set -e

if [ $# -eq 0 ]; then
    echo "❌ 错误: 请提供输出目录名"
    echo "📝 使用方法: bash $0 <output_dir>"
    exit 1
fi

OUTPUT_DIR="$1"
FULL_OUTPUT_DIR="Paper2Video/$OUTPUT_DIR"

echo "🎬 开始执行最终处理步骤 (Step 6-9)"
echo "📁 输出目录: $FULL_OUTPUT_DIR"
echo "=================================="

# 检查输出目录是否存在
if [ ! -d "$FULL_OUTPUT_DIR" ]; then
    echo "❌ 错误: 输出目录不存在: $FULL_OUTPUT_DIR"
    exit 1
fi

# Step 6: 语音合成
echo ""
echo "🎵 执行Step 6: CosyVoice语音合成..."

# 构建路径
SPEECH_DIR="../$FULL_OUTPUT_DIR/final_results/Speech"
AUDIO_OUTPUT_DIR="../$FULL_OUTPUT_DIR/final_results/Speech_Audio"


# 【新增】从 job_info 中读取音色配置
# 我们需要一个方法把 services.py 中的 job_info 信息传递给 shell 脚本。
# 一个简单的方法是通过一个临时文件。
# services.py 在调用 final_pipeline.sh 之前，会创建一个 job_config.json 文件。

# CONFIG_FILE="../$FULL_OUTPUT_DIR/temp/job_config.json"
# 【修改】直接从第三个参数获取配置文件的绝对路径
CONFIG_FILE="$2" # <-- $1 是 output_dir, $2 就是我们传入的 config_path_abs

echo "--- [SHELL DEBUG: Config Read] ---"
echo "Reading config file from argument: $CONFIG_FILE"

if [ -f "$CONFIG_FILE" ]; then

    echo "Config file content:"
    cat "$CONFIG_FILE" # 打印文件内容，确认它包含 "voice_type": "male"
    VOICE_TYPE=$(jq -r '.voice_type' "$CONFIG_FILE")
    CUSTOM_VOICE_PATH=$(jq -r '.custom_voice_path // ""' "$CONFIG_FILE")
    CUSTOM_VOICE_TEXT=$(jq -r '.custom_voice_text // ""' "$CONFIG_FILE")
    echo "✅ 读取到配置文件: 音色类型=${VOICE_TYPE}"
    echo "Parsed VOICE_TYPE: \"$VOICE_TYPE\"" # 用引号包起来，防止空值或多余空格难以发现
    echo "Parsed CUSTOM_VOICE_PATH: \"$CUSTOM_VOICE_PATH\""
    echo "Parsed CUSTOM_VOICE_TEXT: \"$CUSTOM_VOICE_TEXT\""
else
    echo "⚠️ 未找到配置文件，使用默认音色"
    VOICE_TYPE="female" # 默认值
fi
echo "---------------------------------"

# 检查讲稿目录是否存在
if [ ! -d "$FULL_OUTPUT_DIR/final_results/Speech" ]; then
    echo "❌ 错误: 讲稿目录不存在: $FULL_OUTPUT_DIR/final_results/Speech"
    echo "💡 请检查主流程是否正确完成"
    exit 1
fi

echo "📁 讲稿目录: $SPEECH_DIR"
echo "🎵 音频输出目录: $AUDIO_OUTPUT_DIR"

# 切换到CosyVoice目录并执行语音合成
echo ""
echo "🔄 切换到CosyVoice目录..."
cd CosyVoice

# 【修改】根据 VOICE_TYPE 构建不同的 python 命令
if [ "$VOICE_TYPE" = "custom" ] && [ -n "$CUSTOM_VOICE_PATH" ] && [ -n "$CUSTOM_VOICE_TEXT" ]; then
    echo "🎤 使用自定义音色和文本进行合成"
    CMD_ARGS=("--prompt_wav" "$CUSTOM_VOICE_PATH" "--prompt_text" "$CUSTOM_VOICE_TEXT" "--voice_name" "custom")
else
    # 根据预设音色选择不同的提示音文件
    PROMPT_WAV="./asset/zero_shot_prompt.wav" # 默认女声
    PROMPT_TEXT="希望你以后能够做的比我还好呦。"
    VOICE_NAME="female"

    if [ "$VOICE_TYPE" = "male" ]; then
        PROMPT_WAV="./asset/cross_lingual_prompt.wav" # 假设男声提示音在这里
        PROMPT_TEXT="在那之后，完全收购那家公司，因此保持管理层的一致性，利益与即将加入家族的资产保持一致。这就是我们有时不买下全部的原因。" # 对应的文本
        VOICE_NAME="male"
    elif [ "$VOICE_TYPE" = "child" ]; then
        PROMPT_WAV="./asset/child_prompt.wav" # 假设童声提示音在这里
        PROMPT_TEXT="这是一个示例童声。" # 对应的文本
        VOICE_NAME="child"
    fi
    echo "🎧 使用预设音色: ${VOICE_NAME}"
    CMD_ARGS=("--prompt_wav" "$PROMPT_WAV" "--prompt_text" "$PROMPT_TEXT" "--voice_name" "$VOICE_NAME")
fi




echo "🔧 激活conda环境并执行语音合成..."

# 自动检测conda路径
CONDA_SCRIPT=""
POSSIBLE_PATHS=(
    "$(pwd)/../miniconda3/etc/profile.d/conda.sh"
    "$(pwd)/../anaconda3/etc/profile.d/conda.sh"
    "~/miniconda3/etc/profile.d/conda.sh"
    "~/anaconda3/etc/profile.d/conda.sh"
    "/opt/miniconda3/etc/profile.d/conda.sh"
    "/opt/anaconda3/etc/profile.d/conda.sh"
)

echo "🔍 正在检测conda安装路径..."
for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -f "$path" ]; then
        CONDA_SCRIPT="$path"
        echo "✅ 找到conda脚本: $CONDA_SCRIPT"
        break
    fi
done

if [ -z "$CONDA_SCRIPT" ]; then
    echo "❌ 未找到conda安装，尝试直接使用conda命令..."
    # 尝试直接使用conda（可能在PATH中）
    SPEECH_DIR="$SPEECH_DIR" AUDIO_OUTPUT_DIR="$AUDIO_OUTPUT_DIR" bash -c '
    conda activate cosyvoice && \
    echo "✅ conda环境激活成功" && \
    echo "🔹 执行命令: python run_cosyvoice_dynamic.py $SPEECH_DIR $AUDIO_OUTPUT_DIR" && \
    python run_cosyvoice_dynamic.py "$SPEECH_DIR" "$AUDIO_OUTPUT_DIR"
    '
else
    # 使用找到的conda脚本
    SPEECH_DIR="$SPEECH_DIR" AUDIO_OUTPUT_DIR="$AUDIO_OUTPUT_DIR" CONDA_SCRIPT="$CONDA_SCRIPT" bash -c '
    source "$CONDA_SCRIPT" && \
    conda activate cosyvoice && \
    echo "✅ conda环境激活成功" && \
    echo "🔹 执行命令: python run_cosyvoice_dynamic.py $SPEECH_DIR $AUDIO_OUTPUT_DIR" && \
    python run_cosyvoice_dynamic.py "$SPEECH_DIR" "$AUDIO_OUTPUT_DIR"
    '
fi

# 检查语音合成是否成功
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 语音合成完成！"
    
    # Step 7: 音视频对齐
    echo ""
    echo "🎬 执行Step 7: 音视频对齐..."
    echo "   根据音频时长调整对应的代码文件"
    
    # 回到原目录进行音视频对齐
    cd ..
    
    # 调用音视频对齐脚本
    echo "🔧 调用音视频对齐脚本..."
    if python3 audio_video_sync.py "$OUTPUT_DIR"; then
        echo "✅ 音视频对齐完成！"
    else
        echo "⚠️  音视频对齐过程出现错误，但不影响其他结果"
    fi
    
    # Step 8: 视频渲染
    echo ""
    echo "🎬 执行Step 8: Manim视频渲染..."
    echo "   使用manim渲染生成教学视频"
    
    echo "🔧 激活manim_env环境并执行视频渲染..."
    
    # 自动检测conda路径（复用之前的检测结果）
    if [ -z "$CONDA_SCRIPT" ]; then
        echo "🔍 重新检测conda安装路径..."
        for path in "${POSSIBLE_PATHS[@]}"; do
            if [ -f "$path" ]; then
                CONDA_SCRIPT="$path"
                echo "✅ 找到conda脚本: $CONDA_SCRIPT"
                break
            fi
        done
    fi
    
    if [ -z "$CONDA_SCRIPT" ]; then
        echo "❌ 未找到conda安装，尝试直接使用conda命令..."
        # 尝试直接使用conda（可能在PATH中）
        OUTPUT_DIR="$OUTPUT_DIR" bash -c '
        conda activate manim_env && \
        echo "✅ manim_env环境激活成功" && \
        echo "🔹 执行命令: python3 rendervideo_merge.py $OUTPUT_DIR" && \
        python3 rendervideo_merge.py "$OUTPUT_DIR"
        '
    else
        # 使用找到的conda脚本
        OUTPUT_DIR="$OUTPUT_DIR" CONDA_SCRIPT="$CONDA_SCRIPT" bash -c '
        source "$CONDA_SCRIPT" && \
        conda activate manim_env && \
        echo "✅ manim_env环境激活成功" && \
        echo "🔹 执行命令: python3 rendervideo_merge.py $OUTPUT_DIR" && \
        python3 rendervideo_merge.py "$OUTPUT_DIR"
        '
    fi
    
    # 检查视频渲染是否成功
    if [ $? -eq 0 ]; then
        echo ""
        echo "🎉 视频渲染完成！"
        
        # Step 9: 视频音频合并与最终输出
        echo ""
        echo "🎬 执行Step 9: 视频音频合并与最终输出..."
        echo "   合并视频和音频，生成完整的教学视频"
        
        # 执行视频音频合并脚本
        echo "🔧 激活manim_env环境并执行视频音频合并..."
        
        if [ -z "$CONDA_SCRIPT" ]; then
            echo "❌ 未找到conda安装，尝试直接使用conda命令..."
            # 尝试直接使用conda（可能在PATH中）
            OUTPUT_DIR="$OUTPUT_DIR" bash -c '
            conda activate manim_env && \
            echo "✅ manim_env环境激活成功" && \
            echo "🔹 执行命令: python3 video_audio_merge.py $OUTPUT_DIR" && \
            python3 video_audio_merge.py "$OUTPUT_DIR"
            '
        else
            # 使用找到的conda脚本
            OUTPUT_DIR="$OUTPUT_DIR" CONDA_SCRIPT="$CONDA_SCRIPT" bash -c '
            source "$CONDA_SCRIPT" && \
            conda activate manim_env && \
            echo "✅ manim_env环境激活成功" && \
            echo "🔹 执行命令: python3 video_audio_merge.py $OUTPUT_DIR" && \
            python3 video_audio_merge.py "$OUTPUT_DIR"
            '
        fi
        
        # 检查视频音频合并是否成功
        if [ $? -eq 0 ]; then
            echo ""
            echo "🎉 视频音频合并完成！"
            
            # 检查最终视频是否生成
            FINAL_VIDEO="$FULL_OUTPUT_DIR/final_results/Video_with_voice/Full.mp4"
            if [ -f "$FINAL_VIDEO" ]; then
                FILE_SIZE=$(stat -c%s "$FINAL_VIDEO" 2>/dev/null || echo "0")
                FILE_SIZE_MB=$((FILE_SIZE / 1024 / 1024))
                
                # 显示最终成功结果
                echo ""
                echo "🎊 完整流程执行完毕！"
                echo "=================================="
                echo "📋 最终处理结果:"
                echo "   🎵 音频文件: $FULL_OUTPUT_DIR/final_results/Speech_Audio/"
                echo "   🎬 视频文件: $FULL_OUTPUT_DIR/final_results/Video/"
                echo "   🎦 完整视频: $FULL_OUTPUT_DIR/final_results/Video_with_voice/"
                echo ""
                echo "🎊 最终教学视频已生成！"
                echo "   📁 文件路径: $FINAL_VIDEO"
                echo "   📊 文件大小: ${FILE_SIZE_MB} MB"
                echo ""
                echo "✨ 完整的论文处理流程全部完成！"
            else
                echo ""
                echo "⚠️  最终视频文件未找到，但处理流程已完成"
                echo "💡 请检查: $FULL_OUTPUT_DIR/final_results/Video_with_voice/ 目录"
            fi
        else
            echo ""
            echo "⚠️  视频音频合并执行出错"
            exit 1
        fi
    else
        echo ""
        echo "⚠️  视频渲染执行出错"
        exit 1
    fi
else
    echo ""
    echo "⚠️  语音合成执行出错"
    # 回到原目录
    cd ..
    exit 1
fi 