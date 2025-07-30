import re
import sys

def insert_ppt_background_code(file_path, bg_img_path):
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    # 匹配 slide = prs.slides.add_slide(prs.slide_layouts[6])
    pattern = r'(slide\s*=\s*prs\.slides\.add_slide\(prs\.slide_layouts\[6\]\))'
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

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python insert_ppt_bg.py <ppt代码文件路径> <背景图路径>")
        sys.exit(1)
    insert_ppt_background_code(sys.argv[1], sys.argv[2])