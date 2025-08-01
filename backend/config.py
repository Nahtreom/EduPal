# 配置文件 (数据库URI, 密钥等)
# /home/EduAgent/backend/config.py
import os

class Config:
    # 确保 'downloaded_papers' 文件夹在项目根目录下存在
    # 我们使用 os.path.join(os.path.dirname(__file__), '..', '..', 'downloaded_papers') 来可靠地找到项目根目录下的文件夹
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, '..', 'downloaded_papers')
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024