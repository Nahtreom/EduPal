# 创建应用工厂 backend/app/__init__.py。
# 这是新架构的核心，它负责创建app、加载配置、注册所有路由蓝图。
# /home/EduAgent/backend/app/__init__.py
from flask import Flask
from flask_cors import CORS
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 添加CORS支持
    CORS(app)

    # 从 app.routes 模块中导入并注册蓝图
    from .routes.api_v1 import bp as api_v1_bp
    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')

    from .routes.main import bp as main_bp
    app.register_blueprint(main_bp)

    from .routes.file_management import bp as file_management_bp
    app.register_blueprint(file_management_bp)

    from .routes.content_processing import bp as content_processing_bp
    app.register_blueprint(content_processing_bp)

    from .routes.search import bp as search_bp
    app.register_blueprint(search_bp)

    from .routes.editor import bp as editor_bp
    app.register_blueprint(editor_bp, url_prefix='/editor')

    return app