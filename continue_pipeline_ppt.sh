#!/bin/bash

#set -e
set -x  # 打印每条执行的命令


# if [ $# -eq 0 ]; then
#     echo "❌ 错误: 请提供输出目录名"
#     echo "📝 使用方法: bash $0 <输出目录名>"
#     echo "📝 示例: bash $0 test_output"
#     exit 1
# fi

# OUTPUT_DIR="$1"

# 【修改】接收 output_dir 和 config_file 两个参数
echo "==============================开始进入脚本"
if [ "$#" -ne 1 ]; then
    echo "❌ 错误: 脚本需要 1 个参数: <输出目录名> "
    exit 1
fi
OUTPUT_DIR="$1"



# 验证输出目录是否存在
FULL_OUTPUT_DIR="Paper2Video/$OUTPUT_DIR"
if [ ! -d "$FULL_OUTPUT_DIR" ]; then
    echo "❌ 错误: 输出目录不存在: $FULL_OUTPUT_DIR"
    exit 1
fi

echo "🔄 继续执行论文处理流程后续步骤"
echo "📁 输出目录: $FULL_OUTPUT_DIR"
echo "=================================="

# Step 9: 视频音频合并与最终输出
echo ""
echo "🎬 执行Step 5: PPT合并与最终输出..."
echo "   合并PPT，生成完整的ppt"
        
if [ -z "$CONDA_SCRIPT" ]; then
    echo "❌ 未找到conda安装，尝试直接使用conda命令..."
    bash -c '
    echo "🔹 执行命令: python3 ppt_merge_fianl.py $1" && \
    python3 ppt_merge_fianl.py "$1"
' bash "$OUTPUT_DIR"

else
    bash -c '
    echo "🔹 执行命令: python3 ppt_merge_fianl.py $1" && \
    python3 ppt_merge_fianl.py "$1"
' bash "$OUTPUT_DIR"

fi

if [ $? -eq 0 ]; then
            echo ""
            echo "🎉 完整流程执行完毕，最终ppt生成完毕"