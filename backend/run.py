from app import create_app

# 通过应用工厂创建Flask app实例
app = create_app()

if __name__ == '__main__':
    # 从配置中加载主机和端口，或使用默认值
    # 确保 debug=False 和 use_reloader=False 在生产环境中是合适的
    app.run(host='0.0.0.0', port=5050, debug=False, use_reloader=False)