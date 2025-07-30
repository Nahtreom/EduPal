#!/bin/bash

set -e

if [ $# -eq 0 ]; then
    echo "❌ 错误: 请提供输出目录名"
    echo "📝 使用方法: bash $0 <输出目录名>"
    echo "📝 示例: bash $0 test_output"
    exit 1
fi

OUTPUT_DIR="$1"

# 验证输出目录是否存在
FULL_OUTPUT_DIR="Paper2Video/$OUTPUT_DIR"
if [ ! -d "$FULL_OUTPUT_DIR" ]; then
    echo "❌ 错误: 输出目录不存在: $FULL_OUTPUT_DIR"
    exit 1
fi

echo "🎥 Step 4.5: 预览视频渲染"
echo "📁 输出目录: $FULL_OUTPUT_DIR"
echo "=================================="

# 创建预览视频目录
PREVIEW_DIR="$FULL_OUTPUT_DIR/final_results/Video_Preview"
echo "🔧 创建预览视频目录: $PREVIEW_DIR"
mkdir -p "$PREVIEW_DIR"

echo "🎬 激活manim_env环境并执行预览渲染..."

# 自动检测conda路径
CONDA_SCRIPT=""
POSSIBLE_PATHS=(
    "$(pwd)/miniconda3/etc/profile.d/conda.sh"
    "$(pwd)/anaconda3/etc/profile.d/conda.sh"
    "~/miniconda3/etc/profile.d/conda.sh"
    "~/anaconda3/etc/profile.d/conda.sh"
    "/opt/miniconda3/etc/profile.d/conda.sh"
    "/opt/anaconda3/etc/profile.d/conda.sh"
)

echo "🔍 检测conda安装路径..."
for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -f "$path" ]; then
        CONDA_SCRIPT="$path"
        echo "✅ 找到conda脚本: $CONDA_SCRIPT"
        break
    fi
done

if [ -z "$CONDA_SCRIPT" ]; then
    echo "❌ 未找到conda安装，尝试直接使用conda命令..."
    OUTPUT_DIR="$OUTPUT_DIR" bash -c '
    conda activate manim_env && \
    echo "✅ manim_env环境激活成功" && \
    echo "🔹 执行预览渲染: python3 rendervideo_merge.py $OUTPUT_DIR" && \
    python3 rendervideo_merge.py "$OUTPUT_DIR"
    '
else
    OUTPUT_DIR="$OUTPUT_DIR" CONDA_SCRIPT="$CONDA_SCRIPT" bash -c '
    source "$CONDA_SCRIPT" && \
    conda activate manim_env && \
    echo "✅ manim_env环境激活成功" && \
    echo "🔹 执行预览渲染: python3 rendervideo_merge.py $OUTPUT_DIR" && \
python3 rendervideo_merge.py "$OUTPUT_DIR"
    '
fi

# 检查预览渲染是否成功
if [ $? -eq 0 ]; then
    echo ""
    echo "🔄 移动视频文件到预览目录..."
    
    # 检查Video目录是否存在
    VIDEO_DIR="$FULL_OUTPUT_DIR/final_results/Video"
    if [ -d "$VIDEO_DIR" ] && [ "$(ls -A "$VIDEO_DIR" 2>/dev/null)" ]; then
        # 复制视频文件到预览目录
        echo "📁 复制 $VIDEO_DIR/* 到 $PREVIEW_DIR/"
        cp "$VIDEO_DIR"/* "$PREVIEW_DIR/" 2>/dev/null || true
        
        # 删除原Video目录中的文件
        echo "🗑️  清空 $VIDEO_DIR/ 目录"
        rm -f "$VIDEO_DIR"/* 2>/dev/null || true
        
        echo "✅ 预览视频文件移动完成"
        echo "🎬 预览视频已生成，位于: $PREVIEW_DIR"
    else
        echo "⚠️  Video目录为空或不存在，跳过文件移动"
    fi
    
    echo ""
    echo "🎊 预览视频渲染完成！"
    echo "📁 预览视频位置: $PREVIEW_DIR"
    echo "💡 现在可以进行交互式编辑，然后继续后续处理步骤"
    
else
    echo ""
    echo "⚠️  预览视频渲染失败，但不影响后续编辑"
    exit 1
fi