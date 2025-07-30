from pptx import Presentation
from pptx.util import Inches

# 创建Presentation对象
#prs = Presentation()

# 使用一个空白布局（白底）
slide_layout = prs.slide_layouts[6]  # 空白布局
slide = prs.slides.add_slide(slide_layout)

# 插入照片的路径，需要替换为实际的图片路径
image_path = '/home/EduAgent/pptcover/experiments.jpg'

# 获取幻灯片的宽度和高度
slide_width = prs.slide_width
slide_height = prs.slide_height

# 设置图片位置为幻灯片左上角，大小为幻灯片的宽高
left = top = 0
width = slide_width
height = slide_height

# 在幻灯片中插入图片
slide.shapes.add_picture(image_path, left, top, width=width, height=height)
