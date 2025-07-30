import sys
import os
import subprocess
import shutil

def main():
    if len(sys.argv) != 2:
        print("用法: python run_mineru.py <待转换PDF路径>")
        sys.exit(1)

    input_path = sys.argv[1]

    if not os.path.exists(input_path):
        print(f"❌ 输入文件 {input_path} 不存在")
        sys.exit(1)

    # 默认输出路径
    output_path = os.path.join(os.getcwd(), "outputs")
    clean_base_path = os.path.join(os.getcwd(), "outputs_clean")

    os.makedirs(output_path, exist_ok=True)

    # 构造 mineru 命令
    cmd = [
        "mineru",
        "-p", input_path,
        "-o", output_path,
        "--source", "local",
        "--device", "cuda:0"  # 可改为 "cpu"
    ]

    print(f"🚀 正在执行命令: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("✅ 执行成功！")

        # 提取文档名，不含扩展名
        docname = os.path.splitext(os.path.basename(input_path))[0]

        # 定位原始输出路径：例如 outputs/2024.acl-long.810/auto/
        auto_dir = os.path.join(output_path, docname, "auto")
        md_file = os.path.join(auto_dir, f"{docname}.md")
        images_dir = os.path.join(auto_dir, "images")

        # 新的精简输出路径：outputs_clean/2024.acl-long.810/
        clean_output = os.path.join(clean_base_path, docname)
        os.makedirs(clean_output, exist_ok=True)

        # 拷贝 .md 文件
        if os.path.exists(md_file):
            shutil.copy(md_file, os.path.join(clean_output, f"{docname}.md"))
        else:
            print(f"⚠️ 未找到 Markdown 文件：{md_file}")

        # 拷贝 images 文件夹
        if os.path.exists(images_dir):
            shutil.copytree(images_dir, os.path.join(clean_output, "images"), dirs_exist_ok=True)
        else:
            print(f"⚠️ 未找到图片文件夹：{images_dir}")

        print(f"✅ 精简输出已保存至: {clean_output}")

    except subprocess.CalledProcessError as e:
        print(f"❌ 执行失败: {e}")

if __name__ == "__main__":
    main()
