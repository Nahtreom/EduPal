'''
Author: Yuzhe Guo
Date: 2025-07-17 21:06:23
FilePath: /VScodeProjects/Manim/end/Demo05.py
Descripttion: 
'''
from manim import *

class EndingScene(Scene):
    def construct(self):
        # 主要文字内容（上半部分）
        thanks = Text("Thanks for watching!", font_size=48)

        # 三行信息：contact、github、homepage
        contact = MarkupText(
            'Contact: <span foreground="#00C19A">qianc@sjtu.edu.cn</span>', font_size=24
        ).next_to(thanks, DOWN, buff=0.6)

        github = MarkupText(
            'GitHub: <span foreground="#00C19A">https://github.com/OpenBMB</span>', font_size=24
        ).next_to(contact, DOWN, buff=0.3)

        homepage = MarkupText(
            'Homepage: <span foreground="#00C19A">https://soai.sjtu.edu.cn</span>', font_size=24
        ).next_to(github, DOWN, buff=0.3)

        # 下半部分（版权信息）
        copyright_text = Text("© 2025 SJTU-SAI rights reserved.", font_size=20)
        license_text = Text("Licensed under CC BY-NC 4.0", font_size=20).next_to(copyright_text, DOWN)
        copyright_group = VGroup(copyright_text, license_text)
        copyright_group.to_edge(DOWN, buff=0.8)

        # ✅ 注意这里加了 homepage
        upper_group = VGroup(thanks, contact, github, homepage)
        upper_group.move_to(UP * 0.3)

        # logo
        logo = ImageMobject("EDUPAL_logo.png")
        logo.scale(0.12)
        logo.to_corner(UP + RIGHT, buff=0.5)

        # 动画显示
        self.play(
            FadeIn(upper_group, shift=UP),
            FadeIn(copyright_group, shift=UP),
            FadeIn(logo, shift=IN),
            run_time=2
        )
        self.wait(3)
        self.play(
            FadeOut(upper_group),
            FadeOut(copyright_group),
            FadeOut(logo)
        )