# app/routes/processing.py (已修正)

from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from .. import services  # 确保这里的导入是正确的
import os
import sys
import traceback
import zipfile
import tempfile
import base64

# 创建一个名为'processing'的蓝图
processing_bp = Blueprint('processing', __name__)

# ========================= 内容处理与生成API =========================
@processing_bp.route('/analyze-need', methods=['POST'])
def analyze_need():
    """分析用户需求并提炼关键词"""
    # ... (内部代码不变) ...
    data = request.get_json()
    user_input = data.get('user_input', '')
    search_type = data.get('search_type', 'web')
    if not user_input: return jsonify({'error': '请输入您的需求'}), 400
    try:
        result = services.analyze_user_need(user_input, search_type)
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'error': f'需求分析失败: {str(e)}'}), 500

@processing_bp.route('/smart-filter', methods=['POST'])
def smart_filter():
    """智能筛选API"""
    # ... (内部代码不变) ...
    data = request.get_json()
    original_input = data.get('original_input', '')
    keyword = data.get('keyword', '')
    items = data.get('papers', [])
    search_type = data.get('search_type', 'paper')
    if not original_input or not items: return jsonify({'error': '缺少必要参数'}), 400
    try:
        if search_type == 'paper':
            result = services.smart_filter_papers(original_input, keyword, items)
        else:
            result = services.smart_filter_content(original_input, keyword, items, 'web')
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'error': f'智能筛选失败: {str(e)}'}), 500

@processing_bp.route('/download-progress')
def get_download_progress():
    """获取下载进度"""
    # ... (内部代码不变) ...
    try:
        progress = services.get_download_progress()
        return jsonify({'success': True, 'progress': progress})
    except Exception as e:
        return jsonify({'error': f'获取下载进度失败: {str(e)}'}), 500

@processing_bp.route('/crawl', methods=['POST'])
def crawl_papers():
    """爬取论文PDF"""
    # ... (内部代码不变) ...
    data = request.get_json()
    urls, titles = data.get('urls', []), data.get('titles', [])
    if not urls: return jsonify({'error': '未选择要爬取的论文'}), 400
    try:
        result = services.crawl_papers(urls, titles)
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'error': f'爬取失败: {str(e)}'}), 500

@processing_bp.route('/crawl-webpages', methods=['POST'])
def crawl_webpages():
    """爬取网页内容"""
    # ... (内部代码不变) ...
    data = request.get_json()
    urls, titles = data.get('urls', []), data.get('titles', [])
    if not urls: return jsonify({'error': '未选择要爬取的网页'}), 400
    try:
        result = services.crawl_webpages(urls, titles)
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'error': f'网页爬取失败: {str(e)}'}), 500

# 【已修正】恢复您原始的路由地址
@processing_bp.route('/start-processing', methods=['POST'])
def start_processing():
    """开始论文处理流程"""
    # ... (内部代码不变) ...
    pdf_filename = request.form.get('filename')
    video_duration = request.form.get('video_duration', 'medium')
    voice_type = request.form.get('voice_type', 'female')
    output_format = request.form.get('output_format', 'video')
    if not pdf_filename: return jsonify({'error': '请提供PDF文件名'}), 400
    pdf_path = os.path.join('downloaded_papers', pdf_filename)
    if not os.path.exists(pdf_path): return jsonify({'error': 'PDF文件不存在'}), 404
    try:
        result = services.start_paper_processing(
            pdf_path, pdf_filename, video_duration, voice_type, output_format)
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'error': f'启动处理失败: {str(e)}'}), 500

# 【已修正】恢复您原始的路由地址
@processing_bp.route('/start-folder-processing', methods=['POST'])
def start_folder_processing():
    """根据文件夹路径，开始处理整个文件夹中的论文"""
    # ... (内部代码不变) ...
    try:
        folder_name = request.form.get('folder_name')
        batch_id = request.form.get('batch_process_id')
        output_format = request.form.get('output_format', 'video')
        video_duration = request.form.get('video_duration', 'medium')
        voice_type = request.form.get('voice_type', 'female')
        if not folder_name or not batch_id: return jsonify({'error': '缺少文件夹信息'}), 400
        safe_folder_name = secure_filename(folder_name)
        unique_base_name = f"{safe_folder_name}_{batch_id}"
        folder_path = os.path.join('downloaded_papers', unique_base_name)
        if not os.path.isdir(folder_path): return jsonify({'error': '服务器上找不到对应的文件夹'}), 404
        result = services.start_folder_processing(
            folder_path=folder_path, folder_name=folder_name, unique_base_name=unique_base_name, 
            video_duration=video_duration, voice_type=voice_type, output_format=output_format)
        response_data = {'success': True, 'process_id': unique_base_name,
                         'message': f"文件夹 '{folder_name}' 的处理任务已启动。"}
        if isinstance(result, dict): response_data.update(result)
        return jsonify(response_data)
    except Exception as e:
        print(f"Error in start_folder_processing: {e}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({'error': f'启动文件夹处理失败: {str(e)}'}), 500

# 【已修正】恢复您原始的路由地址
@processing_bp.route('/continue-processing', methods=['POST'])
def continue_processing():
    """继续论文处理流程（Step 4.5-9）"""
    # ... (内部代码不变) ...
    data = request.get_json()
    process_id = data.get('process_id')
    if not process_id: return jsonify({'error': '请提供处理任务ID'}), 400
    try:
        result = services.continue_paper_processing(process_id)
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'error': f'继续处理失败: {str(e)}'}), 500

@processing_bp.route('/start-preview-feedback', methods=['POST'])
def start_preview_feedback():
    """检查预览和编辑状态"""
    # ... (内部代码不变) ...
    data = request.get_json()
    process_id = data.get('process_id')
    if not process_id: return jsonify({'error': '请提供处理任务ID'}), 400
    try:
        result = services.start_preview_and_feedback(process_id)
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'error': f'启动预览和反馈失败: {str(e)}'}), 500

@processing_bp.route('/continue-after-feedback', methods=['POST'])
def continue_after_feedback():
    """交互编辑完成后继续处理（Step 6-9）"""
    # ... (内部代码不变) ...
    data = request.get_json()
    process_id = data.get('process_id')
    if not process_id: return jsonify({'error': '请提供处理任务ID'}), 400
    try:
        result = services.continue_after_feedback(process_id)
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'error': f'继续处理失败: {str(e)}'}), 500

# ========================= 获取进度或结果   =========================
# 【已修正】恢复您原始的路由地址
@processing_bp.route('/processing-status/<process_id>')
def get_processing_status(process_id):
    """获取处理状态"""
    # ... (内部代码不变) ...
    try:
        result = services.get_processing_status(process_id)
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'error': f'获取状态失败: {str(e)}'}), 500

# 【已修正】恢复您原始的路由地址
@processing_bp.route('/processing-results')
def get_processing_results():
    """获取所有处理结果列表"""
    # ... (内部代码不变) ...
    try:
        result = services.get_processing_results()
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'error': f'获取结果失败: {str(e)}'}), 500

@processing_bp.route('/download-result/<result_id>')
def download_processing_result(result_id):
    """下载处理结果"""
    # ... (内部代码不变) ...
    try:
        file_path = services.get_result_download_path(result_id)
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': '结果文件不存在'}), 404
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 500

# ========================= Markdown预览 =========================
@processing_bp.route('/markdown-preview/<process_id>')
def preview_markdown(process_id):
    """预览markdown文档内容"""
    # ... (内部代码不变) ...
    try:
        with services.processing_lock:
            if process_id not in services.processing_jobs:
                return jsonify({'success': False, 'error': '未找到处理任务'}), 404
            job = services.processing_jobs[process_id]
            if 'final_output_path' not in job or not job['final_output_path']:
                return jsonify({'success': False, 'error': 'Markdown文档尚未生成完成'}), 404
            zip_path = job['final_output_path']
            if not os.path.exists(zip_path):
                return jsonify({'success': False, 'error': 'Markdown文档文件不存在'}), 404
            markdown_content, images = "", []
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith('.md'):
                            md_path = os.path.join(root, file)
                            with open(md_path, 'r', encoding='utf-8') as f: markdown_content = f.read()
                            break
                    if markdown_content: break
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                            img_path = os.path.join(root, file)
                            try:
                                with open(img_path, 'rb') as img_file:
                                    img_data = base64.b64encode(img_file.read()).decode()
                                    ext = os.path.splitext(file)[1][1:].lower()
                                    mime_type = f'image/{ext}' if ext != 'svg' else 'image/svg+xml'
                                    images.append({'filename': file, 'data': f'data:{mime_type};base64,{img_data}'})
                            except Exception as e:
                                print(f"处理图片 {file} 时出错: {e}")
            return jsonify({'success': True, 'markdown_content': markdown_content, 'images': images,
                            'filename': os.path.basename(zip_path)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500