# app/services/__init__.py

# 从这个包的 main_services.py 模块中，导入所有需要被外部使用的函数
from .main_services import (
    # 核心功能
    upload_pdf_file,
    search_web,
    search_papers,
    analyze_user_need,
    smart_filter_papers,
    smart_filter_content,
    get_download_progress,
    crawl_papers,
    crawl_webpages,

    # 文件管理
    get_all_papers_list,
    get_webpage_list,
    clear_all_content,
    delete_single_content,

    # 内容处理
    start_paper_processing,
    start_folder_processing,
    continue_paper_processing,
    start_preview_and_feedback,
    continue_after_feedback,
    get_processing_status,
    get_processing_results,
    get_result_download_path,

    # Web编辑器
    get_editor_files,
    get_file_content,
    save_file_content,
    upload_background_image,
    apply_background_to_code,
    search_editor_files,
    ai_edit_code,
    get_page_video_associations,
    
    # 别忘了添加您可能自定义的任何其他服务函数
    # processing_lock,  # 如果有全局变量也需要导出
    # processing_jobs
)

# 如果您有全局变量（比如处理任务的字典），也需要在这里定义或导入
# 以确保它们在整个应用中是单例的
processing_jobs = {}
from threading import Lock
processing_lock = Lock()