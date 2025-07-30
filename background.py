import os
import sys
import re

def is_color(value: str) -> bool:
    return value.startswith("#") or value.isupper()

def build_background_code(bg_input: str) -> str:
    if is_color(bg_input):
        if bg_input.startswith("#"):
            return f'self.camera.background_color = Color("{bg_input}")  # 自定义颜色\n'
        else:
            return f'self.camera.background_color = {bg_input}  # 内置颜色\n'
    else:
        return (
            f'bg = ImageMobject("{bg_input}")\n'
            f'bg.scale_to_fit_height(config.frame_height)\n'
            f'bg.scale_to_fit_width(config.frame_width)\n'
            f'bg.set_opacity(0.2)\n'
            f'bg.move_to(ORIGIN)\n'
            f'self.add(bg)\n'
        )

def insert_background_code(file_path: str, bg_code: str):
    with open(file_path, "r") as f:
        lines = f.readlines()

    new_lines = []
    inserted = False
    for line in lines:
        new_lines.append(line)
        if not inserted and re.match(r"\s*def construct\(self\):", line):
            indent = re.match(r"(\s*)", line).group(1) + "    "  # 四空格缩进
            bg_code_indented = "".join(indent + line for line in bg_code.splitlines(True))
            new_lines.append(bg_code_indented)
            inserted = True

    if inserted:
        with open(file_path, "w") as f:
            f.writelines(new_lines)
        print(f"插入成功: {file_path}")
    else:
        print(f"未找到 construct(self): 跳过: {file_path}")

def main():
    if len(sys.argv) != 3:
        print("用法: python background.py <Manim代码文件夹路径> <背景图路径|颜色>")
        sys.exit(1)

    target_dir = sys.argv[1]
    bg_input = sys.argv[2]
    bg_code = build_background_code(bg_input)

    for filename in os.listdir(target_dir):
        if filename.endswith(".py"):
            file_path = os.path.join(target_dir, filename)
            insert_background_code(file_path, bg_code)

if __name__ == "__main__":
    main()