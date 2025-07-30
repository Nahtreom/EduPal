import os
import subprocess
import glob
import sys
import shutil

# python run_mineru_batch.py multi_paper_inputs01
# 针对文件夹
# 所有输出在outputs/multi_paper_inputs01/下
# 精简输出在outputs_clean/multi_paper_inputs01/下

def main():
    # if len(sys.argv) != 2:
    #     print("用法: python run_mineru_batch.py <待转换PDF文件夹>")
    #     sys.exit(1)

    input_folder = sys.argv[1]


    # 1. 获取输入文件夹的基本名称 (例如, 从 "/path/to/multi_paper_inputs01/" 获取 "multi_paper_inputs01")
    #    os.path.normpath 会处理末尾的斜杠，确保 basename 能正确工作
    input_folder_basename = os.path.basename(os.path.normpath(input_folder))

    # 2. 基于输入文件夹名称，构建新的、更具体的输出路径
    #    例如: /path/to/cwd/outputs/multi_paper_inputs01
    output_folder = os.path.join(os.getcwd(), "outputs", input_folder_basename)
    #    例如: /path/to/cwd/outputs_clean/multi_paper_inputs01
    clean_folder = os.path.join(os.getcwd(), "outputs_clean", input_folder_basename)


    if not os.path.exists(input_folder):
        print(f"输入文件夹 {input_folder} 不存在")
        sys.exit(1)

    # 创建新的、带有子目录的输出文件夹，例如 "outputs/multi_paper_inputs01"
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(clean_folder, exist_ok=True)

    pdf_files = sorted(glob.glob(os.path.join(input_folder, "*.pdf")))
    if not pdf_files:
        print(f"输入文件夹中没有找到 PDF 文件")
        sys.exit(1)

    print(f"检测到 {len(pdf_files)} 个 PDF 文件，将输出到 '{output_folder}'")
    print("开始处理...\n")

    for idx, pdf_path in enumerate(pdf_files, start=1):
        print(f"[{idx}/{len(pdf_files)}] 正在处理: {os.path.basename(pdf_path)}")

        # 3. 使MinerU的-o参数指向我们新创建的、更具体的输出文件夹
        cmd = [
            "mineru",
            "-p", pdf_path,
            "-o", output_folder,  # 该变量目前包含了正确的子目录路径
            "--source", "local",
            "--device", "cuda:1"  # 可改为 "cpu"
        ]

        print(f"正在执行命令: {' '.join(cmd)}")
        try:
            # 恢复到原始版本，去掉 capture_output=True, text=True
            # 使 mineru 的输出实时显示在终端上，否则不会显示
            subprocess.run(cmd, check=True) 
            # subprocess.run(cmd, check=True, capture_output=True, text=True) # 添加capture_output和text是为了更好地捕获错误
            print(f"✅ mineru 解析成功: {os.path.basename(pdf_path)}")
        except subprocess.CalledProcessError as e:
            # 这里的错误信息会比较简单
            print(f"❌ 处理失败: {os.path.basename(pdf_path)}, 错误代码: {e.returncode}")
            # print(f"   错误输出: {e.stderr}") 如果想要DEBUG，对应这一行也需要加
            continue
        except FileNotFoundError:
            print("❌ 命令 'mineru' 未找到。请确保它已安装并且在系统的 PATH 中。")
            sys.exit(1)
            


        # === 精简拷贝部分 ===
        # output_folder 和 clean_folder 变量已在前面被正确设置
        docname = os.path.splitext(os.path.basename(pdf_path))[0]
        
        # 源路径现在会自动指向正确的子目录，例如：outputs/muti_paper_inputs01/2024.acl-long.810/auto
        auto_dir = os.path.join(output_folder, docname, "auto")
        md_file = os.path.join(auto_dir, f"{docname}.md")
        images_dir = os.path.join(auto_dir, "images")

        # 目标路径现在也会自动指向正确的子目录，例如：outputs_clean/muti_paper_inputs01/2024.acl-long.810
        target_clean_dir = os.path.join(clean_folder, docname)

        os.makedirs(target_clean_dir, exist_ok=True)

        # 复制 Markdown 文件
        if os.path.exists(md_file):
            shutil.copy(md_file, os.path.join(target_clean_dir, f"{docname}.md"))
            print(f"   -> 已拷贝 Markdown 文件")
        else:
            print(f"⚠️ 未找到 Markdown 文件：{md_file}")

        # 复制 images 目录
        if os.path.exists(images_dir):
            shutil.copytree(images_dir, os.path.join(target_clean_dir, "images"), dirs_exist_ok=True)
            print(f"   -> 已拷贝 images 目录")
        else:
            print(f"⚠️ 未找到图片目录：{images_dir}")

        print(f"精简输出已保存至: {target_clean_dir}\n")

    print(f"🎉 所有 PDF 文件处理完毕！输出文件位于 '{output_folder}' 和 '{clean_folder}'")

if __name__ == "__main__":
    main()