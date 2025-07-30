from manim import *

class ExperimentScene(Scene):
    def construct(self):
        title = Text("Experiment", font_size=72)
        self.play(Write(title))
        self.wait(3)
        self.play(FadeOut(title))  # 渐渐消散
        self.wait()

