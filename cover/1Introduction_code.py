# cover
from manim import *
import textwrap

# 参数
# 作者参数需","分割开
MAX_WIDTH = config.frame_width - 1.0
TITLE_BASE_SIZE = 45
AUTHOR_BASE_SIZE = 20
AFFILIATION_BASE_SIZE = 18  # <--- 新增 (单位字号)
TITLE_WRAP_WIDTH = 40  # 标题每行最多字符数（换行控制）

class PaperTitleScene(Scene):
    def construct(self):
        # ✅ 固定标题、作者与单位（可自行修改） # <--- 修改
        title_text = "(可替换)标题信息"
        author_text = "(可替换)作者信息"
        affiliation_text = "(可替换)单位信息, 例如：大学A, 研究所B" # <--- 新增

        author_text = author_text.replace(",", ", ")  # 逗号后统一加一个空格

        # ==== 处理标题：固定字号 + 自动换行 ====
        title_lines = textwrap.wrap(title_text, width=TITLE_WRAP_WIDTH)
        title_mobjects = []
        for line in title_lines:
            mobj = Text(line, font_size=TITLE_BASE_SIZE)
            mobj.move_to(ORIGIN)
            title_mobjects.append(mobj)
        title_group = VGroup(*title_mobjects).arrange(DOWN, buff=0.3)

        # ====== 处理作者：固定字号 + 自动换行 + 不拆作者，按逗号分隔后智能换行 ====
        authors_list = [a.strip() for a in author_text.replace("\n", "").split(",") if a.strip()]

        lines = []
        current_line = ""

        for author in authors_list:
            candidate = (current_line + ", " if current_line else "") + author
            test_text = Text(candidate, font_size=AUTHOR_BASE_SIZE)
            if test_text.width > MAX_WIDTH:
                if current_line:
                    lines.append(current_line)
                current_line = author
            else:
                current_line = candidate
        if current_line:
            lines.append(current_line)

        author_mobjects = []
        for line in lines:
            mobj = Text(line, font_size=AUTHOR_BASE_SIZE)
            mobj.move_to(ORIGIN)
            author_mobjects.append(mobj)
        # 处理作者字体颜色为 DARK_GRAY
        # for line in lines:
        #     mobj = Text(line, font_size=AUTHOR_BASE_SIZE, color="#333333")
        #     mobj.move_to(ORIGIN)
        #     author_mobjects.append(mobj)
        author_group = VGroup(*author_mobjects).arrange(DOWN, buff=0.2)

        

        # ====== 处理单位：固定字号 + 自动换行 + 不拆单位，按逗号分隔后智能换行 ==== # <--- 新增代码块
        affiliations_list = [a.strip() for a in affiliation_text.replace("\n", "").split(",") if a.strip()]

        aff_lines = []
        aff_current_line = ""

        for affiliation in affiliations_list:
            aff_candidate = (aff_current_line + ", " if aff_current_line else "") + affiliation
            aff_test_text = Text(aff_candidate, font_size=AFFILIATION_BASE_SIZE)
            if aff_test_text.width > MAX_WIDTH:
                if aff_current_line:
                    aff_lines.append(aff_current_line)
                aff_current_line = affiliation
            else:
                aff_current_line = aff_candidate
        if aff_current_line:
            aff_lines.append(aff_current_line)

        affiliation_mobjects = []
        for line in aff_lines:
            mobj = Text(line, font_size=AFFILIATION_BASE_SIZE)
            mobj.move_to(ORIGIN)
            affiliation_mobjects.append(mobj)

        # 处理单位字体颜色为 DARK_GRAY
        # "#333333"非常深的灰（几乎黑）
        # # "#444444"深灰色，略比黑柔和
        # "#2E2E2E"极低亮度深灰（推荐）
        # "#1A1A1A"
        # for line in aff_lines:
        #     mobj = Text(line, font_size=AFFILIATION_BASE_SIZE, color="#333333")
        #     mobj.move_to(ORIGIN)
        #     affiliation_mobjects.append(mobj)
        
        affiliation_group = VGroup(*affiliation_mobjects).arrange(DOWN, buff=0.2)
        # <--- 新增代码块结束

        # ==== 合并整体并居中 ====
        # 您可以调整这里的 buff 来控制作者与单位之间的距离，以及标题与作者之间的距离
        all_group = VGroup(title_group, author_group, affiliation_group).arrange(DOWN, buff=0.6) # <--- 修改
        all_group.move_to(ORIGIN)

        # 加入 logo 图片（右上角）
        logo = ImageMobject("EDUPAL_logo.png")
        logo.scale(0.12)  # 根据图片大小适当缩放
        logo.to_corner(UP + RIGHT, buff=0.5)

        # ==== 动画 ====

        # 1. 先播放 logo 和第一行 title
        self.play(Write(title_mobjects[0]), FadeIn(logo, shift=IN), run_time=2)

        # 2. 后续 title 行正常写入
        for line in title_mobjects[1:]:
            self.play(Write(line), run_time=2)

        self.wait(0.5)

        # 3. 作者依次淡入
        for line in author_mobjects:
            self.play(FadeIn(line), run_time=0.5)
        
        self.wait(0.3) # <--- 新增

        # 4. 单位依次淡入 # <--- 新增
        for line in affiliation_mobjects:
            self.play(FadeIn(line), run_time=0.5)

        self.wait(2)