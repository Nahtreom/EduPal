# 20250730原run_cosyvoice_batch.py

import os
import sys
import torch
import torchaudio
import argparse # 【新增】导入参数解析模块

# 【新增】设置命令行参数解析器
parser = argparse.ArgumentParser(description="使用 CosyVoice 动态合成语音")
parser.add_argument("input_dir", type=str, help="包含待合成 .txt 文件的输入目录路径")
parser.add_argument("output_dir", type=str, help="存放合成后 .wav 文件的输出目录路径")
parser.add_argument("--prompt_wav", type=str, default='./asset/zero_shot_prompt.wav', help="用于音色克隆的提示音频路径 (例如，用户上传的音频)")
parser.add_argument("--prompt_text", type=str, default='希望你以后能够做的比我还好呦。', help="提示音频对应的文本 (例如，用户输入的文本)")
parser.add_argument("--voice_name", type=str, default='default', help="用于区分不同音色的名称，方便调试和管理")

args = parser.parse_args() # 解析传入的命令行参数

# --- 后续代码使用解析后的参数 `args` ---

# 设置 CUDA 设备
os.environ["CUDA_VISIBLE_DEVICES"] = "1"
sys.path.append('third_party/Matcha-TTS')

from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice.utils.file_utils import load_wav

# 使用解析后的参数
input_dir = args.input_dir
output_dir = args.output_dir
os.makedirs(output_dir, exist_ok=True)

# ... (summary_txt_filename 的逻辑保持不变) ...
input_dir_name = os.path.basename(os.path.normpath(input_dir))
summary_txt_filename = f"{input_dir_name}.txt"
summary_path = os.path.join(output_dir, summary_txt_filename)

# 加载 TTS 模型
print("正在加载 CosyVoice 模型...")
cosyvoice = CosyVoice2('pretrained_models/CosyVoice2-0.5B',
                       load_jit=False, load_trt=False, load_vllm=False, fp16=False)

# 【修改】动态加载提示音
print(f"🔊 使用音色: {args.voice_name}")
print(f"   - 提示音文件: {args.prompt_wav}")
print(f"   - 提示音文本: {args.prompt_text}")
prompt_speech_16k = load_wav(args.prompt_wav, 16000) # 使用参数指定的路径
print("✅ 模型加载完成\n")

# ... (summary_lines, txt_files 的逻辑保持不变) ...
# 输出信息记录
summary_lines = []

txt_files = sorted([f for f in os.listdir(input_dir) if f.endswith(".txt")])
total_files = len(txt_files)

# 遍历 txt 文件并生成语音
for idx, fname in enumerate(txt_files, 1):
    print(f"[{idx}/{total_files}] 正在处理文件: {fname}")

    txt_path = os.path.join(input_dir, fname)
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    segments = []
    print("开始合成语音段...")
    for result in cosyvoice.inference_zero_shot(
        text,
        args.prompt_text, # 【修改】使用参数指定的提示文本
        prompt_speech_16k,
        stream=False
    ):
        segments.append(result['tts_speech'])
    print(f"✅ 合成完成，共 {len(segments)} 段")

    # ... (后续合并、保存、写入summary的逻辑保持不变) ...
    if not segments:
        print("⚠️ 无可用语音段，跳过")
        continue

    combined_audio = torch.cat(segments, dim=1)
    output_wav_name = fname.replace(".txt", ".wav")
    output_wav_path = os.path.join(output_dir, output_wav_name)

    torchaudio.save(output_wav_path, combined_audio, cosyvoice.sample_rate)
    duration_sec = combined_audio.shape[1] / cosyvoice.sample_rate
    summary_lines.append(f"{output_wav_name}\t{duration_sec:.2f}s")
    print(f"✅ 合并完成，已保存至: {output_wav_path}（{duration_sec:.2f}s）\n")

with open(summary_path, "w", encoding="utf-8") as f:
    f.write("\n".join(summary_lines))

print("✅ 所有语音合成完成，汇总信息已写入:")
print(summary_path)