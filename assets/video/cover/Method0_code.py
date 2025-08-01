from manim import *
class MethodScene(Scene):
    def construct(self):
        title = Text("Method", font_size=72)
        self.play(Write(title))
        self.wait(3)
        self.play(FadeOut(title))
        self.wait()