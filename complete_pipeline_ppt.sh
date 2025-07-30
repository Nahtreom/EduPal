set -e  

if [ $# -eq 0 ]; then
    echo "❌ 错误: 请提供PDF文件路径"
    echo "📝 使用方法: bash $0 <PDF文件路径>"
    echo "📝 示例: bash $0 MinerU/inputs/ChatDev_short.pdf"
    exit 1
fi

PDF_PATH="$1"

if [ ! -f "$PDF_PATH" ]; then
    echo "❌ 错误: PDF文件不存在: $PDF_PATH"
    exit 1
fi

PDF_FILENAME=$(basename "$PDF_PATH" .pdf)
OUTPUT_DIR="${PDF_FILENAME}_1_output"

echo "🚀 开始完整的论文处理流程"
echo "📄 输入PDF: $PDF_PATH"
echo "📁 输出目录: $OUTPUT_DIR"
echo "=================================="

# Step 1-3: 执行主要流程（包括人机交互）
echo ""
echo "🎯 执行Step 1-3: 主要处理流程..."
python3 all_pipeline_ppt.py "$PDF_PATH" --output-dir "$OUTPUT_DIR"

# 检查主流程是否成功
if [ $? -ne 0 ]; then
    echo "❌ 主流程执行失败"
    exit 1
fi

echo ""
echo "✅ 主流程完成"

# Step 3.5: 复制cover文件到Code目录
echo ""
echo "📋 执行Step 3.5: 复制pptcover文件..."
echo "   将pptcover目录下的Python场景文件复制到Code目录供编辑和渲染"

CODE_DIR="Paper2Video/$OUTPUT_DIR/final_results/Code"
if [ ! -d "$CODE_DIR" ]; then
    echo "❌ 错误: Code目录不存在: $CODE_DIR"
    echo "💡 请检查主流程是否正确完成"
    exit 1
fi

# 检查cover目录是否存在
if [ ! -d "pptcover" ]; then
    echo "❌ 错误: cover目录不存在"
    echo "💡 请确保cover目录在当前工作目录下"
    exit 1
fi

echo "📁 源目录: pptcover/"
echo "📁 目标目录: $CODE_DIR"

# 复制cover目录下的所有Python文件
echo "🔄 复制Python场景文件..."
for py_file in pptcover/*.py; do
    if [ -f "$py_file" ]; then
        filename=$(basename "$py_file")
        echo "   📝 复制: $filename"
        cp "$py_file" "$CODE_DIR/"
        
        # 检查复制是否成功
        if [ -f "$CODE_DIR/$filename" ]; then
            echo "      ✅ 成功复制到: $CODE_DIR/$filename"
        else
            echo "      ❌ 复制失败: $filename"
        fi
    fi
done

echo ""
echo "✅ cover文件复制完成！"
echo "   这些文件可以在交互式编辑中修改，但不会生成配音"
echo "   在后续视频渲染阶段将一起渲染"

# Step 4: 交互式编辑
echo ""
echo "🖊️  执行Step 4: 交互式编辑..."
echo "   可以在此步骤中查看和编辑生成的代码和讲稿文件"

EDIT_DIR="Paper2Video/$OUTPUT_DIR/final_results"
if [ ! -d "$EDIT_DIR" ]; then
    echo "❌ 错误: 结果目录不存在: $EDIT_DIR"
    echo "💡 请检查主流程是否正确完成"
    exit 1
fi

echo "📁 编辑目录: $EDIT_DIR"
echo ""
echo "⏸️  即将进入交互式编辑模式..."
echo "   在这个阶段，您可以查看和编辑生成的代码和讲稿文件"
echo ""

# 询问用户是否要进入交互式编辑
echo ""
echo "🤔 是否进入交互式编辑模式?"
echo "   输入 y 或 yes 进入编辑模式"
echo "   输入其他任何内容或直接回车跳过"
echo "   ⏰ 30秒内无输入将自动跳过"
echo -n "请选择 (y/N): "

# 直接从终端读取用户输入，使用简单可靠的方法
echo ""
echo "⏰ 请在30秒内做出选择，或直接回车跳过"
echo -n "正在等待输入: "

# 设置30秒超时的read
if read -t 30 -r INTERACTIVE_CHOICE; then
    echo ""
    echo "✅ 收到输入: '$INTERACTIVE_CHOICE'"
else
    echo ""
    echo "⏰ 30秒超时，自动跳过交互式编辑"
    INTERACTIVE_CHOICE="n"
fi

case "$INTERACTIVE_CHOICE" in
    [Yy]|[Yy][Ee][Ss])
        echo ""
        echo "🔧 启动交互式编辑器..."
        # 直接运行交互式编辑器
        python3 interactive_editor.py "$EDIT_DIR"
        
        # 检查交互式编辑是否成功完成
        INTERACTIVE_EXIT_CODE=$?
        if [ $INTERACTIVE_EXIT_CODE -ne 0 ]; then
            echo ""
            echo "⚠️  交互式编辑过程出现错误或被用户中断"
            echo "   继续执行后续步骤..."
        else
            echo ""
            echo "✅ 交互式编辑完成"
        fi
        ;;
    *)
        echo ""
        echo "⏭️  跳过交互式编辑，继续执行后续步骤..."
        ;;
esac

# Step 4.5: 视频预览渲染
echo ""
echo "📹 执行Step 4.5: 视频预览渲染..."
echo "   渲染代码文件生成预览视频，无需音频"

# 创建预览视频目录
PREVIEW_DIR="Paper2Video/$OUTPUT_DIR/final_results/ppt_Preview"
echo "🔧 创建预览视频目录: $PREVIEW_DIR"
mkdir -p "$PREVIEW_DIR"

echo "🎬 激活manim_env环境并执行预览渲染..."

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
    echo "✅ manim_env环境激活成功" && \
    echo "🔹 执行预览渲染: python3 ppt_merge.py $OUTPUT_DIR" && \
    python3 ppt_merge.py "$OUTPUT_DIR"
    '
else
    # 使用找到的conda脚本
    OUTPUT_DIR="$OUTPUT_DIR" CONDA_SCRIPT="$CONDA_SCRIPT" bash -c '
    source "$CONDA_SCRIPT" && \
    # conda activate manim_env && \
    echo "✅ manim_env环境激活成功" && \
    echo "🔹 执行预览渲染: python3 ppt_merge.py $OUTPUT_DIR" && \
    python3 ppt_merge.py "$OUTPUT_DIR"
    '
fi

# 检查预览渲染是否成功
if [ $? -eq 0 ]; then
    echo ""
    echo "🔄 移动视频文件到预览目录..."
    
    # 检查Video目录是否存在
    VIDEO_DIR="Paper2Video/$OUTPUT_DIR/final_results/Video"
    if [ -d "$VIDEO_DIR" ] && [ "$(ls -A "$VIDEO_DIR" 2>/dev/null)" ]; then
        # 复制视频文件到预览目录
        echo "📁 复制 $VIDEO_DIR/* 到 $PREVIEW_DIR/"
        cp "$VIDEO_DIR"/* "$PREVIEW_DIR/" 2>/dev/null || true
        
        # 删除原Video目录中的文件
        echo "🗑️  清空 $VIDEO_DIR/ 目录"
        rm -f "$VIDEO_DIR"/* 2>/dev/null || true
        
        echo "✅ 预览视频文件移动完成"
    else
        echo "⚠️  Video目录为空或不存在，跳过文件移动"
    fi
fi

# 检查预览渲染是否成功
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 预览视频渲染完成！"
    echo "📁 预览视频位于: Paper2Video/$OUTPUT_DIR/final_results/Video_Preview/"
    echo "   您可以检查视频效果，如有需要可返回Step 4编辑代码"
else
    echo ""
    echo "⚠️  预览渲染出现错误，但不影响后续流程"
    echo "💡 您仍然可以继续进行语音合成和最终渲染"
fi