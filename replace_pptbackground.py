import os
import sys
import re

def replace_ppt_background_image(file_path, new_image_path, script_path=None):
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    full_image_path = os.path.join(script_path, new_image_path)
    # 正则匹配背景图设置部分（支持 bg_img_path = "xxx" 或直接 add_picture("xxx", ...））
    pattern_img_assignment = re.compile(r'(bg_img_path\s*=\s*[\'"])([^\'"]+)([\'"])')
    #pattern_direct_picture = re.compile(r'(add_picture\(\s*[\'"])([^\'"]+)([\'"])')

    code = pattern_img_assignment.sub(rf'\1{full_image_path}\3', code)
    #new_code = pattern_direct_picture.sub(rf'\1{new_image_path}\3', new_code)

    pattern_other_images = re.compile(r'(\bimage\d+_path\s*=\s*[\'"])([^\'"]+)([\'"])')
    def replace_with_full_path(match):
        orig_path = match.group(2)
        full_path = os.path.join(script_path, orig_path)
        return f'{match.group(1)}{full_path}{match.group(3)}'

    code = pattern_other_images.sub(replace_with_full_path, code)
    pattern_other_images = re.compile(r'(image_path\s*=\s*[\'"])([^\'"]+)([\'"])')
    code = pattern_other_images.sub(replace_with_full_path, code)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code)

    print(f"✅ 已更新背景图为: {new_image_path} -> {file_path}")

def main():
    if len(sys.argv) != 3:
        print("用法: python replace_ppt_background.py <PPT脚本文件路径> <新图片路径>")
        sys.exit(1)

    script_path = sys.argv[1]
    new_bg_image = sys.argv[2]

    if not os.path.exists(script_path):
        print("❌ 错误: 指定的脚本文件不存在")
        sys.exit(1)

    #replace_ppt_background_image(script_path, new_bg_image)
    for filename in os.listdir(script_path):
        if filename.endswith(".py"):
            file_path = os.path.join(script_path, filename)
            replace_ppt_background_image(file_path, new_bg_image, script_path)

if __name__ == "__main__":
    main()
