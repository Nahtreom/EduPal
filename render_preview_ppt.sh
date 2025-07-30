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

# Step 4.5: 视频预览渲染
echo ""
echo "📹 执行Step 4.5: PPT预览渲染..."
echo "   渲染代码文件生成预览PPT"

# 创建预览视频目录
PREVIEW_DIR="Paper2Video/$OUTPUT_DIR/final_results/ppt_Preview"
echo "🔧 创建预览PPT目录: $PREVIEW_DIR"
mkdir -p "$PREVIEW_DIR"

# 自动检测conda路径
# CONDA_SCRIPT=""
# POSSIBLE_PATHS=(
#     "$(pwd)/miniconda3/etc/profile.d/conda.sh"
#     "$(pwd)/anaconda3/etc/profile.d/conda.sh"
#     "~/miniconda3/etc/profile.d/conda.sh"
#     "~/anaconda3/etc/profile.d/conda.sh"
#     "/opt/miniconda3/etc/profile.d/conda.sh"
#     "/opt/anaconda3/etc/profile.d/conda.sh"
# )

# echo "🔍 检测conda安装路径..."
# for path in "${POSSIBLE_PATHS[@]}"; do
#     if [ -f "$path" ]; then
#         CONDA_SCRIPT="$path"
#         echo "✅ 找到conda脚本: $CONDA_SCRIPT"
#         break
#     fi
# done

if [ -z "$CONDA_SCRIPT" ]; then
    echo "❌ 未找到conda安装，尝试直接使用conda命令..."
    # 尝试直接使用conda（可能在PATH中）
    OUTPUT_DIR="$OUTPUT_DIR" bash -c '
    # conda activate manim_env && \
    echo "🔹 执行预览渲染: python3 ppt_merge.py $OUTPUT_DIR" && \
    python3 ppt_merge.py "$OUTPUT_DIR"
    '
else
    # 使用找到的conda脚本
    OUTPUT_DIR="$OUTPUT_DIR" CONDA_SCRIPT="$CONDA_SCRIPT" bash -c '
    source "$CONDA_SCRIPT" && \
    # conda activate manim_env && \
    echo "🔹 执行预览渲染: python3 ppt_merge.py $OUTPUT_DIR" && \
    python3 ppt_merge.py "$OUTPUT_DIR"
    '
fi

# 检查预览渲染是否成功
if [ $? -eq 0 ]; then
    echo ""
    echo "🔄 移动视频文件到预览目录..."
    
    # # 检查Video目录是否存在
    # VIDEO_DIR="Paper2Video/$OUTPUT_DIR/final_results/Video"
    # if [ -d "$VIDEO_DIR" ] && [ "$(ls -A "$VIDEO_DIR" 2>/dev/null)" ]; then
    #     # 复制视频文件到预览目录
    #     echo "📁 复制 $VIDEO_DIR/* 到 $PREVIEW_DIR/"
    #     cp "$VIDEO_DIR"/* "$PREVIEW_DIR/" 2>/dev/null || true
        
    #     # 删除原Video目录中的文件
    #     echo "🗑️  清空 $VIDEO_DIR/ 目录"
    #     rm -f "$VIDEO_DIR"/* 2>/dev/null || true
        
    #     echo "✅ 预览视频文件移动完成"
    # else
    #     echo "⚠️  Video目录为空或不存在，跳过文件移动"
    # fi
    FINAL_DIR="Paper2Video/$OUTPUT_DIR/final_results"
    PREVIEW_DIR="Paper2Video/$OUTPUT_DIR/preview"

    # 创建预览目录（如果不存在）
    mkdir -p "$PREVIEW_DIR"

    # 移动所有 .pptx 文件
    mv "$FINAL_DIR"/*.pptx "$PREVIEW_DIR/" 2>/dev/null || echo "⚠️ 没有找到 PPT 文件"
fi

# 检查预览渲染是否成功
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 预览PPT渲染完成！"
    echo "📁 预览PPT位于: Paper2Video/$OUTPUT_DIR/preview/"
    echo "   您可以检查PPT效果，如有需要可返回Step 4编辑代码"
else
    echo ""
    echo "⚠️  预览渲染出现错误，但不影响后续流程"
    echo "💡 您仍然可以继续进行语音合成和最终渲染"
fi