from manim import *
class IntroductionScene(Scene):
    def construct(self):
        title = Text("Introduction", font_size=72)
        self.play(Write(title))
        self.wait(3)
        self.play(FadeOut(title))
        self.wait()