# 20250730更新完整处理流程脚本，原为copy（支持多论文+封面生成）

set -e  

if [ $# -eq 0 ]; then
    echo "❌ 错误: 请提供输入路径"
    echo "📝 使用方法: bash $0 <PDF文件路径 或 包含PDF文件的目录路径>"
    echo "📝 示例："
    echo "   单个文件: bash $0 MinerU/inputs/ChatDev_short.pdf"
    echo "   批量目录: bash $0 MinerU/inputs/multi_papers/"
    exit 1
fi


INPUT_PATH="$1"

# 验证输入路径是否存在（文件或目录）
if [ ! -e "$INPUT_PATH" ]; then
    echo "❌ 错误: 输入路径不存在: $INPUT_PATH"
    exit 1
fi

# 根据输入类型确定输出目录名
if [ -f "$INPUT_PATH" ]; then
    # 单个PDF文件
    if [[ ! "$INPUT_PATH" == *.pdf ]]; then
        echo "❌ 错误: 请提供PDF文件（.pdf扩展名）: $INPUT_PATH"
        exit 1
    fi
    FILENAME=$(basename "$INPUT_PATH" .pdf)
    OUTPUT_DIR="${FILENAME}_output"
    echo "🚀 开始完整的论文处理流程（单文件模式）"
    echo "📄 输入PDF: $INPUT_PATH"
elif [ -d "$INPUT_PATH" ]; then
    # 目录批量处理
    DIR_NAME=$(basename "$INPUT_PATH")
    OUTPUT_DIR="${DIR_NAME}_batch_output" # 输出文件夹命名
    echo "🚀 开始完整的论文处理流程（批量模式）"
    echo "📁 输入目录: $INPUT_PATH"
else
    echo "❌ 错误: 输入路径必须是PDF文件或包含PDF文件的目录: $INPUT_PATH"
    exit 1
fi

echo "📁 输出目录: $OUTPUT_DIR"
echo "=================================="

# Step 1-3: 执行主要流程（包括人机交互）
echo ""
echo "🎯 执行Step 1-3: 主要处理流程..."
python3 all_pipeline_video.py "$INPUT_PATH" --output-dir "$OUTPUT_DIR"

# 检查主流程是否成功
if [ $? -ne 0 ]; then
    echo "❌ 主流程执行失败"
    exit 1
fi

echo ""
echo "✅ 主流程完成"


# 检查是否为批量模式，如果是则给出说明
if [ -d "$INPUT_PATH" ]; then
    echo ""
    echo "📋 注意: 批量模式处理完成！"
    # echo "   批量模式的后续步骤（交互式编辑、视频渲染等）需要针对每个生成的子目录单独执行"
    # echo "   建议检查 Paper2Video/$OUTPUT_DIR/ 目录下的各个子结果"
    # echo ""
    # echo "🎉 批量处理已完成，脚本将在此处结束。"
    # echo "   如需进行视频渲染等后续步骤，请针对单个结果目录使用单文件模式。"
    # exit 0
fi

# Step 3.5: 复制cover文件到Code目录
echo ""
echo "📋 执行Step 3.5: 复制cover文件..."
echo "   将cover目录下的Python场景文件复制到Code目录供编辑和渲染"

CODE_DIR="Paper2Video/$OUTPUT_DIR/final_results/Code"
if [ ! -d "$CODE_DIR" ]; then
    echo "❌ 错误: Code目录不存在: $CODE_DIR"
    echo "💡 请检查主流程是否正确完成"
    exit 1
fi

# 检查cover目录是否存在
if [ ! -d "cover" ]; then
    echo "❌ 错误: cover目录不存在"
    echo "💡 请确保cover目录在当前工作目录下"
    exit 1
fi

echo "📁 源目录: cover/"
echo "📁 目标目录: $CODE_DIR"

# 复制cover目录下的所有Python文件
echo "🔄 复制Python场景文件..."
for py_file in cover/*.py; do
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



############################################################
# Step 3.6: 调用新脚本，生成封面场景的代码和讲稿
############################################################
echo ""
echo "🎯 执行Step 3.6: 生成封面内容..."
bash /home/EduAgent/generate_cover.sh "$INPUT_PATH"

# 检查封面生成脚本是否成功
if [ $? -ne 0 ]; then
    echo "❌ 封面生成脚本执行失败"
    exit 1
fi
echo "✅ 封面内容生成完成！"
echo "🎉 所有流程顺利结束！"




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

# 检查是否设置了SKIP_INTERACTIVE环境变量
if [[ "${SKIP_INTERACTIVE}" == "1" || "${SKIP_INTERACTIVE,,}" == "true" || "${SKIP_INTERACTIVE,,}" == "yes" ]]; then
    echo "🔧 检测到SKIP_INTERACTIVE环境变量，自动跳过交互式编辑模式"
    INTERACTIVE_CHOICE="n"
else
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
PREVIEW_DIR="Paper2Video/$OUTPUT_DIR/final_results/Video_Preview"
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
    # 尝试直接使用conda（可能在PATH中）
    OUTPUT_DIR="$OUTPUT_DIR" bash -c '
    conda activate manim_env && \
    echo "✅ manim_env环境激活成功" && \
    echo "🔹 执行预览渲染: python3 rendervideo_merge.py $OUTPUT_DIR" && \
    python3 rendervideo_merge.py "$OUTPUT_DIR"
    '
else
    # 使用找到的conda脚本
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

# Step 5: 反馈与编辑
echo ""
echo "💬 执行Step 5: 反馈与编辑..."
echo "   基于预览视频进行反馈和进一步编辑"

# 构建参数路径
VIDEO_PREVIEW_DIR="Paper2Video/$OUTPUT_DIR/final_results/Video_Preview/"
CODE_DIR="Paper2Video/$OUTPUT_DIR/final_results/Code/"
SPEECH_DIR="Paper2Video/$OUTPUT_DIR/final_results/Speech/"
PAGE_PREVIEW_DIR="Paper2Video/$OUTPUT_DIR/final_results/Page_Preview/"

echo "📁 预览视频目录: $VIDEO_PREVIEW_DIR"
echo "📁 代码目录: $CODE_DIR"
echo "📁 讲稿目录: $SPEECH_DIR"

echo "🔧 激活edu_env环境并启动反馈编辑应用..."

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
    VIDEO_PREVIEW_DIR="$VIDEO_PREVIEW_DIR" CODE_DIR="$CODE_DIR" SPEECH_DIR="$SPEECH_DIR" PAGE_PREVIEW_DIR="$PAGE_PREVIEW_DIR" bash -c '
    conda activate edu_env && \
    echo "✅ edu_env环境激活成功" && \
    cd Edit && \
    echo "🔹 执行命令: python3 app.py ../$VIDEO_PREVIEW_DIR ../$CODE_DIR ../$SPEECH_DIR ../$PAGE_PREVIEW_DIR" && \
    python3 app.py "../$VIDEO_PREVIEW_DIR" "../$CODE_DIR" "../$SPEECH_DIR" "../$PAGE_PREVIEW_DIR"
    '
else
    # 使用找到的conda脚本
    VIDEO_PREVIEW_DIR="$VIDEO_PREVIEW_DIR" CODE_DIR="$CODE_DIR" SPEECH_DIR="$SPEECH_DIR" PAGE_PREVIEW_DIR="$PAGE_PREVIEW_DIR" CONDA_SCRIPT="$CONDA_SCRIPT" bash -c '
    source "$CONDA_SCRIPT" && \
    conda activate edu_env && \
    echo "✅ edu_env环境激活成功" && \
    cd Edit && \
    echo "🔹 执行命令: python3 app.py ../$VIDEO_PREVIEW_DIR ../$CODE_DIR ../$SPEECH_DIR ../$PAGE_PREVIEW_DIR" && \
    python3 app.py "../$VIDEO_PREVIEW_DIR" "../$CODE_DIR" "../$SPEECH_DIR" "../$PAGE_PREVIEW_DIR"
    '
fi

# 检查反馈编辑是否成功
FEEDBACK_EXIT_CODE=$?
if [ $FEEDBACK_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ 反馈与编辑完成"
else
    echo ""
    echo "⚠️  反馈编辑过程出现错误或被用户中断"
    echo "   继续执行后续步骤..."
fi

# Step 6: 语音合成
echo ""
echo "🎵 执行Step 6: CosyVoice语音合成..."

# 构建路径
SPEECH_DIR="../Paper2Video/$OUTPUT_DIR/final_results/Speech"
AUDIO_OUTPUT_DIR="../Paper2Video/$OUTPUT_DIR/final_results/Speech_Audio"

# 检查讲稿目录是否存在
if [ ! -d "Paper2Video/$OUTPUT_DIR/final_results/Speech" ]; then
    echo "❌ 错误: 讲稿目录不存在: Paper2Video/$OUTPUT_DIR/final_results/Speech"
    echo "💡 请检查主流程是否正确完成"
    exit 1
fi

echo "📁 讲稿目录: $SPEECH_DIR"
echo "🎵 音频输出目录: $AUDIO_OUTPUT_DIR"

# 切换到CosyVoice目录并执行语音合成
echo ""
echo "🔄 切换到CosyVoice目录..."
cd CosyVoice

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

# if [ -z "$CONDA_SCRIPT" ]; then
#     echo "❌ 未找到conda安装，尝试直接使用conda命令..."
#     # 尝试直接使用conda（可能在PATH中）
#     SPEECH_DIR="$SPEECH_DIR" AUDIO_OUTPUT_DIR="$AUDIO_OUTPUT_DIR" bash -c '
#     conda activate cosyvoice && \
#     echo "✅ conda环境激活成功" && \
#     echo "🔹 执行命令: python run_cosyvoice_batch.py $SPEECH_DIR $AUDIO_OUTPUT_DIR" && \
#     python run_cosyvoice_batch.py "$SPEECH_DIR" "$AUDIO_OUTPUT_DIR"
#     '
# else
#     # 使用找到的conda脚本
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
COMMAND_TO_RUN="
    conda activate cosyvoice && \\
    echo '✅ conda环境激活成功' && \\
    echo '🔹 执行命令: python run_cosyvoice_dynamic.py \"$1\" \"$2\" ${@:3}' && \\
    python run_cosyvoice_dynamic.py \"\$1\" \"\$2\" \"\${@:3}\"
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
            FINAL_VIDEO="Paper2Video/$OUTPUT_DIR/final_results/Video_with_voice/Full.mp4"
            if [ -f "$FINAL_VIDEO" ]; then
                FILE_SIZE=$(stat -c%s "$FINAL_VIDEO" 2>/dev/null || echo "0")
                FILE_SIZE_MB=$((FILE_SIZE / 1024 / 1024))
                
                # 显示最终成功结果
                echo ""
                echo "🎊 完整流程执行完毕！"
                echo "=================================="
                echo "📋 处理结果位于:"
                echo "   📁 主要结果: Paper2Video/$OUTPUT_DIR/final_results/"
                echo "   📝 讲稿文件: Paper2Video/$OUTPUT_DIR/final_results/Speech/"
                echo "   💻 代码文件: Paper2Video/$OUTPUT_DIR/final_results/Code/ (包含论文内容+cover场景，已调整时长)"
                echo "   🎵 音频文件: Paper2Video/$OUTPUT_DIR/final_results/Speech_Audio/"
                echo "   📺 预览视频: Paper2Video/$OUTPUT_DIR/final_results/Video_Preview/ (无音频预览)"
                echo "   🎬 视频文件: Paper2Video/$OUTPUT_DIR/final_results/Video/"
                echo "   🎦 完整视频: Paper2Video/$OUTPUT_DIR/final_results/Video_with_voice/"
                echo ""
                echo "🔄 流程概览:"
                echo "   Step 1-3:   论文处理和内容生成 ✅"
                echo "   Step 3.5:   复制cover场景文件 ✅"
                echo "   Step 4:     交互式编辑 ✅"
                echo "   Step 4.5:   视频预览渲染 ✅"
                echo "   Step 5:   反馈与编辑 ✅"
                echo "   Step 6:     语音合成 ✅"
                echo "   Step 7:     音视频对齐 ✅"
                echo "   Step 8:     视频渲染 ✅"
                echo "   Step 9:     视频音频合并 ✅"
                echo ""
                echo "🎊 最终教学视频已生成！"
                echo "   📁 文件路径: $FINAL_VIDEO"
                echo "   📊 文件大小: ${FILE_SIZE_MB} MB"
                echo ""
                echo "✨ 从PDF论文到完整教学视频的端到端处理已全部完成！"
            else
                echo ""
                echo "⚠️  最终视频文件未找到，但处理流程已完成"
                echo "💡 请检查: Paper2Video/$OUTPUT_DIR/final_results/Video_with_voice/ 目录"
            fi
        else
            echo ""
            echo "⚠️  视频音频合并执行出错，但视频渲染已完成"
            
            # 显示部分成功结果
            echo ""
            echo "🎊 主要流程执行完毕！"
            echo "=================================="
            echo "📋 处理结果位于:"
            echo "   📁 主要结果: Paper2Video/$OUTPUT_DIR/final_results/"
            echo "   📝 讲稿文件: Paper2Video/$OUTPUT_DIR/final_results/Speech/"
            echo "   💻 代码文件: Paper2Video/$OUTPUT_DIR/final_results/Code/ (包含论文内容+cover场景，已调整时长)"
            echo "   🎵 音频文件: Paper2Video/$OUTPUT_DIR/final_results/Speech_Audio/"
            echo "   📺 预览视频: Paper2Video/$OUTPUT_DIR/final_results/Video_Preview/ (无音频预览)"
            echo "   🎬 视频文件: Paper2Video/$OUTPUT_DIR/final_results/Video/"
            echo "   ⚠️  完整视频: 合并失败，请手动在 manim_env 环境中执行 python3 video_audio_merge.py $OUTPUT_DIR"
            echo ""
            echo "🔄 流程概览:"
            echo "   Step 1-3:   论文处理和内容生成 ✅"
            echo "   Step 3.5:   复制cover场景文件 ✅"
            echo "   Step 4:     交互式编辑 ✅"
            echo "   Step 4.5:   视频预览渲染 ✅"
            echo "   Step 5:   反馈与编辑 ✅"
            echo "   Step 6:     语音合成 ✅"
            echo "   Step 7:     音视频对齐 ✅"
            echo "   Step 8:     视频渲染 ✅"
            echo "   Step 9:     视频音频合并 ❌"
            echo ""
            echo "⚠️  流程部分完成，最终合并需要手动处理"
        fi
    else
        echo ""
        echo "⚠️  视频渲染执行出错，但其他结果仍然可用"
        
        # 显示部分结果
        echo ""
        echo "🎊 主要流程执行完毕！"
        echo "=================================="
        echo "📋 处理结果位于:"
        echo "   📁 主要结果: Paper2Video/$OUTPUT_DIR/final_results/"
        echo "   📝 讲稿文件: Paper2Video/$OUTPUT_DIR/final_results/Speech/"
        echo "   💻 代码文件: Paper2Video/$OUTPUT_DIR/final_results/Code/ (包含论文内容+cover场景，已调整时长)"
        echo "   🎵 音频文件: Paper2Video/$OUTPUT_DIR/final_results/Speech_Audio/"
        echo "   📺 预览视频: Paper2Video/$OUTPUT_DIR/final_results/Video_Preview/ (无音频预览)"
                    echo "   ⚠️  视频文件: 渲染失败，请手动在 manim_env 环境中执行 python3 rendervideo_merge.py $OUTPUT_DIR"
        echo ""
        echo "🔄 流程概览:"
        echo "   Step 1-3:   论文处理和内容生成 ✅"
        echo "   Step 3.5:   复制cover场景文件 ✅"
        echo "   Step 4:     交互式编辑 ✅"
        echo "   Step 4.5:   视频预览渲染 ✅"
        echo "   Step 5:   反馈与编辑 ✅"
        echo "   Step 6:     语音合成 ✅"
        echo "   Step 7:     音视频对齐 ✅"
        echo "   Step 8:     视频渲染 ❌"
        echo "   Step 9:     视频音频合并 ❌"
        echo ""
        echo "⚠️  流程部分完成，视频渲染和最终合并需要手动处理"
    fi
else
    echo ""
    echo "⚠️  语音合成执行出错，跳过音视频对齐和视频渲染步骤"
    # 回到原目录
    cd ..
    
    # 显示部分结果
    echo ""
    echo "🎊 部分流程执行完毕！"
    echo "=================================="
    echo "📋 处理结果位于:"
    echo "   📁 主要结果: Paper2Video/$OUTPUT_DIR/final_results/"
    echo "   📝 讲稿文件: Paper2Video/$OUTPUT_DIR/final_results/Speech/"
    echo "   💻 代码文件: Paper2Video/$OUTPUT_DIR/final_results/Code/ (包含论文内容+cover场景)"
    echo "   📺 预览视频: Paper2Video/$OUTPUT_DIR/final_results/Video_Preview/ (无音频预览)"
    echo "   ⚠️  音频文件: 语音合成失败"
    echo "   ⚠️  视频文件: 跳过渲染（依赖音频）"
    echo ""
    echo "🔄 流程概览:"
    echo "   Step 1-3:   论文处理和内容生成 ✅"
    echo "   Step 3.5:   复制cover场景文件 ✅"
    echo "   Step 4:     交互式编辑 ✅"
    echo "   Step 4.5:   视频预览渲染 ✅"
    echo "   Step 5:   反馈与编辑 ✅"
    echo "   Step 6:     语音合成 ❌"
    echo "   Step 7:     音视频对齐 ❌"
    echo "   Step 8:     视频渲染 ❌"
    echo "   Step 9:     视频音频合并 ❌"
    echo ""
    echo "⚠️  流程部分完成，需要手动处理语音合成、视频渲染和最终合并"
fi 