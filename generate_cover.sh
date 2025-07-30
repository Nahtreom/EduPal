#!/bin/bash
set -e

# /home/EduAgent/generate_cover.sh
# 功能: 计算所需路径并调用Python脚本来生成封面文件。

echo ""
echo "=================================="
echo "🎬 开始执行封面生成脚本..."
echo "=================================="

if [ $# -eq 0 ]; then
    echo "❌ 错误: 请提供原始输入路径（PDF文件或目录）"
    echo "📝 用法: bash $0 <PDF文件路径 或 包含PDF文件的目录路径>"
    exit 1
fi

INPUT_PATH="$1"
IS_BATCH=false

# 定义基础输出目录
MINERU_BASE_DIR="/home/EduAgent/MinerU/outputs_clean"
P2V_BASE_DIR="/home/EduAgent/Paper2Video"

# 根据输入类型确定 MinerU 和 Paper2Video 的具体输出目录名
if [ -f "$INPUT_PATH" ]; then
    # 单文件模式
    FILENAME=$(basename "$INPUT_PATH" .pdf)
    MINERU_OUTPUT_DIR="$MINERU_BASE_DIR/$FILENAME"
    P2V_OUTPUT_DIR="$P2V_BASE_DIR/${FILENAME}_output"
    echo "ℹ️ 检测到单文件模式。"
elif [ -d "$INPUT_PATH" ]; then
    # 批量模式
    IS_BATCH=true
    DIR_NAME=$(basename "$INPUT_PATH")
    # 注意：这里的命名规则需要和您主脚本中的规则严格保持一致
    MINERU_OUTPUT_DIR="$MINERU_BASE_DIR/$DIR_NAME" 
    P2V_OUTPUT_DIR="$P2V_BASE_DIR/${DIR_NAME}_batch_output"
    echo "ℹ️ 检测到批量模式。"
else
    echo "❌ 错误: 输入路径不存在或类型不支持: $INPUT_PATH"
    exit 1
fi

# 最终确定的代码和语音目录
CODE_DIR="$P2V_OUTPUT_DIR/final_results/Code"
SPEECH_DIR="$P2V_OUTPUT_DIR/final_results/Speech"

echo "   - MinerU .md 目录: $MINERU_OUTPUT_DIR"
echo "   - Paper2Video Code 目录: $CODE_DIR"
echo "   - Paper2Video Speech 目录: $SPEECH_DIR"
echo ""

# 检查目录是否存在
if [ ! -d "$MINERU_OUTPUT_DIR" ] || [ ! -d "$CODE_DIR" ] || [ ! -d "$SPEECH_DIR" ]; then
    echo "❌ 错误: 一个或多个目标目录不存在。请确认主流程已成功运行。"
    echo "   - 检查 MinerU 目录: $MINERU_OUTPUT_DIR"
    echo "   - 检查 Code 目录: $CODE_DIR"
    echo "   - 检查 Speech 目录: $SPEECH_DIR"
    exit 1
fi

# 调用Python脚本来执行核心任务
CMD="python3 /home/EduAgent/cover_generator.py \
    --miner-u-dir \"$MINERU_OUTPUT_DIR\" \
    --p2v-code-dir \"$CODE_DIR\" \
    --p2v-speech-dir \"$SPEECH_DIR\""

if [ "$IS_BATCH" = true ]; then
    CMD="$CMD --is-batch"
fi

# 执行命令
eval $CMD

if [ $? -ne 0 ]; then
    echo "❌ Python脚本执行失败。"
    exit 1
fi

echo ""
echo "✅ 封面生成脚本执行完毕！"