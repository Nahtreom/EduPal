import re
import sys
import os

def insert_ppt_background_code(file_path, bg_img_path):
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    # 匹配 slide = prs.slides.add_slide(prs.slide_layouts[6])
    pattern = r'(slide\s*=\s*prs\.slides\.add_slide\([^\)]*\))'
    bg_code = f'''bg_img_path = "{bg_img_path}"  #此行不要改动

# 添加背景图（现在它确实在底层）
slide.shapes.add_picture(
    bg_img_path,
    left=Inches(0),
    top=Inches(0),
    width=prs.slide_width,
    height=prs.slide_height
)
'''

    # 在每个匹配后插入背景代码
    new_code = re.sub(pattern, r'\1\n' + bg_code, code)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_code)

def replace_ppt_background_image(file_path, script_path=None):
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    #full_image_path = os.path.join(script_path, new_image_path)
    # 正则匹配背景图设置部分（支持 bg_img_path = "xxx" 或直接 add_picture("xxx", ...））
    #pattern_img_assignment = re.compile(r'(bg_img_path\s*=\s*[\'"])([^\'"]+)([\'"])')
    #pattern_direct_picture = re.compile(r'(add_picture\(\s*[\'"])([^\'"]+)([\'"])')

    #code = pattern_img_assignment.sub(rf'\1{full_image_path}\3', code)
    #new_code = pattern_direct_picture.sub(rf'\1{new_image_path}\3', new_code)

    pattern_other_images = re.compile(r'(\bimage\d+_path\s*=\s*[\'"])([^\'"]+)([\'"])')
    def replace_with_full_path(match):
        orig_path = match.group(2)
        full_path = os.path.join(script_path, orig_path)
        return f'{match.group(1)}{full_path}{match.group(3)}'

    code = pattern_other_images.sub(replace_with_full_path, code)
    pattern_img_assignment = re.compile(r'(bg_img_path\s*=\s*[\'"])([^\'"]+)([\'"])')
    code = pattern_img_assignment.sub(replace_with_full_path, code)
    pattern_other_images = re.compile(r'(image_path\s*=\s*[\'"])([^\'"]+)([\'"])')
    code = pattern_other_images.sub(replace_with_full_path, code)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(code)

    print(f"✅ 已更新背景图和插入图片路径")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python insert_ppt_bg.py <ppt代码文件路径> <背景图路径>")
        sys.exit(1)
    target_dir = sys.argv[1]
    #insert_ppt_background_code(sys.argv[1], sys.argv[2])
    for filename in os.listdir(target_dir):
        if filename.endswith(".py"):
            file_path = os.path.join(target_dir, filename)
            insert_ppt_background_code(file_path, sys.argv[2])
    for filename in os.listdir(target_dir):
        if filename.endswith(".py"):
            file_path = os.path.join(target_dir, filename)
            replace_ppt_background_image(file_path, target_dir)
