# app/__init__.py (最终修正版)

from flask import Flask
import os
import sys

def create_app():
    """
    应用工厂函数，用于创建和配置Flask应用实例。
    """
    app = Flask(__name__)

    # --- 【核心修正】计算项目的绝对根路径 ---
    # `os.path.dirname(__file__)` 会得到当前文件所在的目录 (app/)
    # 再取一次 dirname 就会得到项目的根目录 (backend/)
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    # --- 使用绝对路径进行配置 ---
    app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024
    
    # 将上传文件夹的路径设置为绝对路径
    UPLOAD_FOLDER = os.path.join(basedir, 'downloaded_papers')
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    
    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 【推荐】将其他路径也改为绝对路径，更加健壮
    webpages_folder = os.path.join(basedir, 'downloaded_webpages')
    os.makedirs(webpages_folder, exist_ok=True)


    # --- 注册蓝图 (这部分保持不变) ---
    with app.app_context():
        from .routes.core import core_bp
        from .routes.file_management import file_management_bp
        from .routes.processing import processing_bp
        from .routes.web_editor import web_editor_bp

        app.register_blueprint(core_bp)
        app.register_blueprint(file_management_bp)
        app.register_blueprint(processing_bp) 
        app.register_blueprint(web_editor_bp, url_prefix='/editor')

    return app