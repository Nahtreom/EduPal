from manim import *

class ConclusionScene(Scene):
    def construct(self):
        title = Text("Conclusion", font_size=72)
        self.play(Write(title))
        self.wait(3)  # 等待3秒
        self.play(FadeOut(title))  # 渐渐消散
        self.wait()