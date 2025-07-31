#!/bin/bash

set -e

# if [ $# -eq 0 ]; then
#     echo "❌ 错误: 请提供输出目录名"
#     echo "📝 使用方法: bash $0 <输出目录名>"
#     echo "📝 示例: bash $0 test_output"
#     exit 1
# fi

# OUTPUT_DIR="$1"

# 【修改】接收 output_dir 和 config_file 两个参数
if [ "$#" -ne 2 ]; then
    echo "❌ 错误: 脚本需要 2 个参数: <输出目录名> <配置文件绝对路径>"
    exit 1
fi
OUTPUT_DIR="$1"
CONFIG_FILE="$2"



# 验证输出目录是否存在
FULL_OUTPUT_DIR="Paper2Video/$OUTPUT_DIR"
if [ ! -d "$FULL_OUTPUT_DIR" ]; then
    echo "❌ 错误: 输出目录不存在: $FULL_OUTPUT_DIR"
    exit 1
fi

# ==================== 【新增：读取和解析配置文件】 ====================
echo "--- [SHELL DEBUG: Config Read in continue_pipeline.sh] ---"
echo "Reading config file from argument: $CONFIG_FILE"

if [ -f "$CONFIG_FILE" ]; then
    echo "Config file content:"
    cat "$CONFIG_FILE"
    
    VOICE_TYPE=$(jq -r '.voice_type' "$CONFIG_FILE")
    CUSTOM_VOICE_PATH=$(jq -r '.custom_voice_path // ""' "$CONFIG_FILE")
    CUSTOM_VOICE_TEXT=$(jq -r '.custom_voice_text // ""' "$CONFIG_FILE")
    
    echo "Parsed VOICE_TYPE: \"$VOICE_TYPE\""
else
    echo "⚠️ Config file NOT FOUND at path: $CONFIG_FILE. Falling back to default voice."
    VOICE_TYPE="female"
fi
echo "------------------------------------------------------------"
# ========================================================================


echo "🔄 继续执行论文处理流程后续步骤"
echo "📁 输出目录: $FULL_OUTPUT_DIR"
echo "=================================="

# Step 5: 反馈与编辑（已集成到主Web服务中）
# 该阶段已无Web提示，直接进入下一步

# Step 6: 语音合成
echo ""
echo "🎵 执行Step 6: CosyVoice语音合成..."

# 构建路径
SPEECH_DIR="../$FULL_OUTPUT_DIR/final_results/Speech"
AUDIO_OUTPUT_DIR="../$FULL_OUTPUT_DIR/final_results/Speech_Audio"

# 检查讲稿目录是否存在
if [ ! -d "$FULL_OUTPUT_DIR/final_results/Speech" ]; then
    echo "❌ 错误: 讲稿目录不存在: $FULL_OUTPUT_DIR/final_results/Speech"
    echo "💡 请检查主流程是否正确完成"
    exit 1
fi

echo "📁 讲稿目录: $SPEECH_DIR"
echo "🎵 音频输出目录: $AUDIO_OUTPUT_DIR"

# 切换到CosyVoice目录并执行语音合成
# 切换到CosyVoice启动目录并执行语音合成
echo ""
echo "🔄 切换到CosyVoice目录..."
# ================20250731update======================
cd CosyVoice
# cd services/cosyvoice
# ====================================================

# ==================== 【新增：动态构建Python命令】 ====================
if [ "$VOICE_TYPE" = "custom" ] && [ -n "$CUSTOM_VOICE_PATH" ] && [ -n "$CUSTOM_VOICE_TEXT" ]; then
    echo "🎤 使用自定义音色和文本进行合成"
    CMD_ARGS=("--prompt_wav" "$CUSTOM_VOICE_PATH" "--prompt_text" "$CUSTOM_VOICE_TEXT" "--voice_name" "custom")
else
    # PROMPT_WAV="./asset/zero_shot_prompt.wav"
    PROMPT_WAV="/home/EduAgent/CosyVoice/asset/zero_shot_prompt.wav"
    PROMPT_TEXT="希望你以后能够做的比我还好呦。"
    VOICE_NAME="female"
    if [ "$VOICE_TYPE" = "male" ]; then
        # PROMPT_WAV="./asset/cross_lingual_prompt.wav"
        PROMPT_WAV="/home/EduAgent/CosyVoice/asset/cross_lingual_prompt.wav"
        PROMPT_TEXT="在那之后，完全收购那家公司，因此保持管理层的一致性，利益与即将加入家族的资产保持一致。这就是我们有时不买下全部的原因。"
        VOICE_NAME="male"
    elif [ "$VOICE_TYPE" = "child" ]; then
        PROMPT_WAV="./asset/child_prompt.wav"
        PROMPT_TEXT="这是一个示例童声。"
        VOICE_NAME="child"
    fi
    echo "🎧 使用预设音色: ${VOICE_NAME}"
    echo "   - 使用提示音文件: ${PROMPT_WAV}"
    CMD_ARGS=("--prompt_wav" "$PROMPT_WAV" "--prompt_text" "$PROMPT_TEXT" "--voice_name" "$VOICE_NAME")
fi
# =========================================================================


echo "🔧 激活conda环境并执行语音合成..."

# 重新检测conda路径（相对于CosyVoice目录）
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

# if [ -z "$CONDA_SCRIPT" ]; then
#     echo "❌ 未找到conda安装，尝试直接使用conda命令..."
#     SPEECH_DIR="$SPEECH_DIR" AUDIO_OUTPUT_DIR="$AUDIO_OUTPUT_DIR" bash -c '
#     conda activate cosyvoice && \
#     echo "✅ conda环境激活成功" && \
#     echo "🔹 执行命令: python run_cosyvoice_batch.py $SPEECH_DIR $AUDIO_OUTPUT_DIR" && \
#     python run_cosyvoice_batch.py "$SPEECH_DIR" "$AUDIO_OUTPUT_DIR"
#     '
# else
#     SPEECH_DIR="$SPEECH_DIR" AUDIO_OUTPUT_DIR="$AUDIO_OUTPUT_DIR" CONDA_SCRIPT="$CONDA_SCRIPT" bash -c '
#     source "$CONDA_SCRIPT" && \
#     conda activate cosyvoice && \
#     echo "✅ conda环境激活成功" && \
#     echo "🔹 执行命令: python run_cosyvoice_batch.py $SPEECH_DIR $AUDIO_OUTPUT_DIR" && \
#     python run_cosyvoice_batch.py "$SPEECH_DIR" "$AUDIO_OUTPUT_DIR"
#     '
# fi


# ==================== 【核心修改：整合动态调用】 ====================
# 将要执行的命令构建成一个字符串，这样可以避免代码重复
# 注意：我们将 CMD_ARGS 数组安全地传递给这个命令字符串
# COMMAND_TO_RUN="
#     conda activate cosyvoice && \\
#     echo '✅ conda环境激活成功' && \\
#     echo '🔹 执行命令: python run_cosyvoice_dynamic.py \"$1\" \"$2\" ${@:3}' && \\
#     python run_cosyvoice_dynamic.py \"\$1\" \"\$2\" \"\${@:3}\"
# "
COMMAND_TO_RUN="
    conda activate cosyvoice && \\
    echo '✅ conda环境激活成功' && \\
    echo '🔹 执行命令: python （新架构但必须默认CosyVoice在根目录下）../services/cosyvoice/run_cosyvoice_dynamic.py \"$1\" \"$2\" ${@:3}' && \\
    python ../services/cosyvoice/run_cosyvoice_dynamic.py \"\$1\" \"\$2\" \"\${@:3}\"
"

# 解释:
# \"$1\" 是 SPEECH_DIR
# \"$2\" 是 AUDIO_OUTPUT_DIR
# \"\${@:3}\" 是 CMD_ARGS 数组中的所有元素

if [ -z "$CONDA_SCRIPT" ]; then
    echo "❌ 未找到conda安装，尝试直接使用conda命令..."
    # 将所有需要的变量传递给 bash -c
    bash -c "$COMMAND_TO_RUN" -- "$SPEECH_DIR" "$AUDIO_OUTPUT_DIR" "${CMD_ARGS[@]}"
else
    echo "✅ 使用找到的conda脚本: $CONDA_SCRIPT"
    # source conda 脚本，然后执行命令
    bash -c "source \"$CONDA_SCRIPT\" && $COMMAND_TO_RUN" -- "$SPEECH_DIR" "$AUDIO_OUTPUT_DIR" "${CMD_ARGS[@]}"
fi
# ========================================================================


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
    
    if [ -z "$CONDA_SCRIPT" ]; then
        echo "❌ 未找到conda安装，尝试直接使用conda命令..."
        OUTPUT_DIR="$OUTPUT_DIR" bash -c '
        conda activate manim_env && \
        echo "✅ manim_env环境激活成功" && \
        echo "🔹 执行命令: python3 rendervideo_merge.py $OUTPUT_DIR" && \
        python3 rendervideo_merge.py "$OUTPUT_DIR"
        '
    else
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
        
        if [ -z "$CONDA_SCRIPT" ]; then
            echo "❌ 未找到conda安装，尝试直接使用conda命令..."
            OUTPUT_DIR="$OUTPUT_DIR" bash -c '
            conda activate manim_env && \
            echo "✅ manim_env环境激活成功" && \
            echo "🔹 执行命令: python3 video_audio_merge.py $OUTPUT_DIR" && \
            python3 video_audio_merge.py "$OUTPUT_DIR"
            '
        else
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
                
                echo ""
                echo "🎊 后续流程执行完毕！"
                echo "=================================="
                echo "📋 处理结果位于:"
                echo "   📁 主要结果: $FULL_OUTPUT_DIR/final_results/"
                echo "   📝 讲稿文件: $FULL_OUTPUT_DIR/final_results/Speech/"
                echo "   💻 代码文件: $FULL_OUTPUT_DIR/final_results/Code/"
                echo "   🎵 音频文件: $FULL_OUTPUT_DIR/final_results/Speech_Audio/"
                echo "   📺 预览视频: $FULL_OUTPUT_DIR/final_results/Video_Preview/"
                echo "   🎬 视频文件: $FULL_OUTPUT_DIR/final_results/Video/"
                echo "   🎦 完整视频: $FULL_OUTPUT_DIR/final_results/Video_with_voice/"
                echo ""
                echo "🎊 最终教学视频已生成！"
                echo "   📁 文件路径: $FINAL_VIDEO"
                echo "   📊 文件大小: ${FILE_SIZE_MB} MB"
                echo ""
                echo "✨ 完整的论文到教学视频处理流程全部完成！"
            else
                echo ""
                echo "⚠️  最终视频文件未找到，但处理流程已完成"
            fi
        else
            echo ""
            echo "⚠️  视频音频合并执行出错"
        fi
    else
        echo ""
        echo "⚠️  视频渲染执行出错"
    fi
else
    echo ""
    echo "⚠️  语音合成执行出错，跳过后续步骤"
    cd ..
fi 