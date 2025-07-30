#!/bin/bash

# 获取输出目录参数
OUTPUT_DIR=$1

if [ -z "$OUTPUT_DIR" ]; then
    echo "❌ 错误: 请提供输出目录名称"
    echo "使用方法: $0 <输出目录名>"
    exit 1
fi

# 构建完整路径
FULL_OUTPUT_DIR="Paper2Video/$OUTPUT_DIR"

# 检查输出目录是否存在
if [ ! -d "$FULL_OUTPUT_DIR" ]; then
    echo "❌ 错误: 输出目录不存在: $FULL_OUTPUT_DIR"
    exit 1
fi

echo "🔄 开始执行Step 6-9: 语音合成、对齐、视频渲染、合并"
echo "📁 输出目录: $FULL_OUTPUT_DIR"

# 检测conda安装路径
echo "🔍 检测conda安装..."
CONDA_SCRIPT=""
POSSIBLE_PATHS=(
    "$(pwd)/miniconda3/etc/profile.d/conda.sh"
    "$(pwd)/anaconda3/etc/profile.d/conda.sh"
    "~/miniconda3/etc/profile.d/conda.sh"
    "~/anaconda3/etc/profile.d/conda.sh"
    "/opt/conda/etc/profile.d/conda.sh"
    "/usr/local/miniconda3/etc/profile.d/conda.sh"
    "/usr/local/anaconda3/etc/profile.d/conda.sh"
)

for path in "${POSSIBLE_PATHS[@]}"; do
    expanded_path=$(eval echo "$path")
    if [ -f "$expanded_path" ]; then
        CONDA_SCRIPT="$expanded_path"
        echo "✅ 找到conda脚本: $CONDA_SCRIPT"
        break
    fi
done

if [ -z "$CONDA_SCRIPT" ]; then
    echo "⚠️  未找到conda脚本，尝试直接使用conda命令"
fi

# Step 6: 语音合成
echo ""
echo "🎵 执行Step 6: CosyVoice语音合成..."

# 构建路径
SPEECH_DIR="../$FULL_OUTPUT_DIR/final_results/Speech"
AUDIO_OUTPUT_DIR="../$FULL_OUTPUT_DIR/final_results/Speech_Audio"

# 检查讲稿目录是否存在
if [ ! -d "$FULL_OUTPUT_DIR/final_results/Speech" ]; then
    echo "❌ 错误: 讲稿目录不存在: $FULL_OUTPUT_DIR/final_results/Speech"
    echo "💡 请检查反馈编辑是否正确完成"
    exit 1
fi

echo "📁 讲稿目录: $SPEECH_DIR"
echo "🎵 音频输出目录: $AUDIO_OUTPUT_DIR"

# 切换到CosyVoice目录并执行语音合成
echo ""
echo "🔄 切换到CosyVoice目录..."
cd CosyVoice

echo "🔧 激活conda环境并执行语音合成..."

# 重新检测conda路径（相对于CosyVoice目录）
CONDA_SCRIPT=""
POSSIBLE_PATHS=(
    "$(pwd)/../miniconda3/etc/profile.d/conda.sh"
    "$(pwd)/../anaconda3/etc/profile.d/conda.sh"
    "~/miniconda3/etc/profile.d/conda.sh"
    "~/anaconda3/etc/profile.d/conda.sh"
    "/opt/conda/etc/profile.d/conda.sh"
    "/usr/local/miniconda3/etc/profile.d/conda.sh"
    "/usr/local/anaconda3/etc/profile.d/conda.sh"
)

for path in "${POSSIBLE_PATHS[@]}"; do
    expanded_path=$(eval echo "$path")
    if [ -f "$expanded_path" ]; then
        CONDA_SCRIPT="$expanded_path"
        echo "✅ 找到conda脚本: $CONDA_SCRIPT"
        break
    fi
done

if [ -z "$CONDA_SCRIPT" ]; then
    echo "❌ 未找到conda安装，尝试直接使用conda命令..."
    SPEECH_DIR="$SPEECH_DIR" AUDIO_OUTPUT_DIR="$AUDIO_OUTPUT_DIR" bash -c '
    conda activate cosyvoice && \
    echo "✅ cosyvoice环境激活成功" && \
    echo "🔹 执行命令: python3 process_speech.py $SPEECH_DIR $AUDIO_OUTPUT_DIR" && \
    python3 process_speech.py "$SPEECH_DIR" "$AUDIO_OUTPUT_DIR"
    '
else
    SPEECH_DIR="$SPEECH_DIR" AUDIO_OUTPUT_DIR="$AUDIO_OUTPUT_DIR" CONDA_SCRIPT="$CONDA_SCRIPT" bash -c '
    source "$CONDA_SCRIPT" && \
    conda activate cosyvoice && \
    echo "✅ cosyvoice环境激活成功" && \
    echo "🔹 执行命令: python3 process_speech.py $SPEECH_DIR $AUDIO_OUTPUT_DIR" && \
    python3 process_speech.py "$SPEECH_DIR" "$AUDIO_OUTPUT_DIR"
    '
fi

# 检查语音合成是否成功
SPEECH_EXIT_CODE=$?
if [ $SPEECH_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ 语音合成完成"
else
    echo ""
    echo "❌ 语音合成失败，退出码: $SPEECH_EXIT_CODE"
    exit 1
fi

# 返回到主目录
cd ..

# Step 7: 音视频时间对齐
echo ""
echo "🔄 执行Step 7: 音视频时间对齐..."

# 构建路径
VIDEO_DIR="$FULL_OUTPUT_DIR/final_results/Video_Preview"
AUDIO_DIR="$FULL_OUTPUT_DIR/final_results/Speech_Audio"
ALIGNED_OUTPUT_DIR="$FULL_OUTPUT_DIR/final_results/Aligned_Video"

# 检查必要目录
if [ ! -d "$VIDEO_DIR" ]; then
    echo "❌ 错误: 视频预览目录不存在: $VIDEO_DIR"
    exit 1
fi

if [ ! -d "$AUDIO_DIR" ]; then
    echo "❌ 错误: 音频目录不存在: $AUDIO_DIR"
    exit 1
fi

echo "📁 视频目录: $VIDEO_DIR"
echo "📁 音频目录: $AUDIO_DIR"
echo "🎬 对齐输出目录: $ALIGNED_OUTPUT_DIR"

# 创建对齐输出目录
mkdir -p "$ALIGNED_OUTPUT_DIR"

# 执行音视频对齐
echo "🔧 执行音视频时间对齐..."
python3 align_audio_video.py "$VIDEO_DIR" "$AUDIO_DIR" "$ALIGNED_OUTPUT_DIR"

# 检查对齐是否成功
ALIGN_EXIT_CODE=$?
if [ $ALIGN_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ 音视频对齐完成"
else
    echo ""
    echo "❌ 音视频对齐失败，退出码: $ALIGN_EXIT_CODE"
    exit 1
fi

# Step 8: 视频渲染
echo ""
echo "🎬 执行Step 8: 视频渲染..."

# 构建路径
ALIGNED_VIDEO_DIR="$FULL_OUTPUT_DIR/final_results/Aligned_Video"
RENDERED_OUTPUT_DIR="$FULL_OUTPUT_DIR/final_results/Rendered_Video"

# 检查对齐视频目录
if [ ! -d "$ALIGNED_VIDEO_DIR" ]; then
    echo "❌ 错误: 对齐视频目录不存在: $ALIGNED_VIDEO_DIR"
    exit 1
fi

echo "📁 对齐视频目录: $ALIGNED_VIDEO_DIR"
echo "🎬 渲染输出目录: $RENDERED_OUTPUT_DIR"

# 创建渲染输出目录
mkdir -p "$RENDERED_OUTPUT_DIR"

# 切换到Manim目录并执行视频渲染
echo ""
echo "🔄 切换到Manim目录..."
cd manim

echo "🔧 激活conda环境并执行视频渲染..."

# 重新检测conda路径（相对于manim目录）
CONDA_SCRIPT=""
POSSIBLE_PATHS=(
    "$(pwd)/../miniconda3/etc/profile.d/conda.sh"
    "$(pwd)/../anaconda3/etc/profile.d/conda.sh"
    "~/miniconda3/etc/profile.d/conda.sh"
    "~/anaconda3/etc/profile.d/conda.sh"
    "/opt/conda/etc/profile.d/conda.sh"
    "/usr/local/miniconda3/etc/profile.d/conda.sh"
    "/usr/local/anaconda3/etc/profile.d/conda.sh"
)

for path in "${POSSIBLE_PATHS[@]}"; do
    expanded_path=$(eval echo "$path")
    if [ -f "$expanded_path" ]; then
        CONDA_SCRIPT="$expanded_path"
        echo "✅ 找到conda脚本: $CONDA_SCRIPT"
        break
    fi
done

if [ -z "$CONDA_SCRIPT" ]; then
    echo "❌ 未找到conda安装，尝试直接使用conda命令..."
    ALIGNED_VIDEO_DIR="../$ALIGNED_VIDEO_DIR" RENDERED_OUTPUT_DIR="../$RENDERED_OUTPUT_DIR" bash -c '
    conda activate manim_env && \
    echo "✅ manim_env环境激活成功" && \
    echo "🔹 执行命令: python3 render_video.py $ALIGNED_VIDEO_DIR $RENDERED_OUTPUT_DIR" && \
    python3 render_video.py "$ALIGNED_VIDEO_DIR" "$RENDERED_OUTPUT_DIR"
    '
else
    ALIGNED_VIDEO_DIR="../$ALIGNED_VIDEO_DIR" RENDERED_OUTPUT_DIR="../$RENDERED_OUTPUT_DIR" CONDA_SCRIPT="$CONDA_SCRIPT" bash -c '
    source "$CONDA_SCRIPT" && \
    conda activate manim_env && \
    echo "✅ manim_env环境激活成功" && \
    echo "🔹 执行命令: python3 render_video.py $ALIGNED_VIDEO_DIR $RENDERED_OUTPUT_DIR" && \
    python3 render_video.py "$ALIGNED_VIDEO_DIR" "$RENDERED_OUTPUT_DIR"
    '
fi

# 检查视频渲染是否成功
RENDER_EXIT_CODE=$?
if [ $RENDER_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ 视频渲染完成"
else
    echo ""
    echo "❌ 视频渲染失败，退出码: $RENDER_EXIT_CODE"
    exit 1
fi

# 返回到主目录
cd ..

# Step 9: 视频合并
echo ""
echo "🔀 执行Step 9: 视频合并..."

# 构建路径
RENDERED_VIDEO_DIR="$FULL_OUTPUT_DIR/final_results/Rendered_Video"
FINAL_OUTPUT_FILE="$FULL_OUTPUT_DIR/final_results/final_video.mp4"

# 检查渲染视频目录
if [ ! -d "$RENDERED_VIDEO_DIR" ]; then
    echo "❌ 错误: 渲染视频目录不存在: $RENDERED_VIDEO_DIR"
    exit 1
fi

echo "📁 渲染视频目录: $RENDERED_VIDEO_DIR"
echo "🎬 最终输出文件: $FINAL_OUTPUT_FILE"

# 执行视频合并
echo "🔧 执行视频合并..."
python3 merge_videos.py "$RENDERED_VIDEO_DIR" "$FINAL_OUTPUT_FILE"

# 检查视频合并是否成功
MERGE_EXIT_CODE=$?
if [ $MERGE_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ 视频合并完成"
    echo "🎉 最终视频已生成: $FINAL_OUTPUT_FILE"
else
    echo ""
    echo "❌ 视频合并失败，退出码: $MERGE_EXIT_CODE"
    exit 1
fi

echo ""
echo "🎉 所有步骤完成！最终视频已生成: $FINAL_OUTPUT_FILE"
echo "📁 完整输出目录: $FULL_OUTPUT_DIR"

exit 0 