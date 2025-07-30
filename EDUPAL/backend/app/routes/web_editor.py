# Web编辑器API
# app/routes/web_editor.py
from flask import Blueprint, request, jsonify, send_file
from .. import services
import os

# 创建一个名为'web_editor'的蓝图
# 注意：我们将在app工厂中为它添加url_prefix='/editor'
web_editor_bp = Blueprint('web_editor', __name__)

# ========================= Web版交互编辑器API =========================

@web_editor_bp.route('/files/<process_id>')
def get_editor_files(process_id):
    """获取指定处理任务的可编辑文件列表"""
    try:
        result = services.get_editor_files(process_id)
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'获取文件列表失败: {str(e)}'}), 500

@web_editor_bp.route('/file-content', methods=['POST'])
def get_file_content():
    """获取文件内容"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        
        if not file_path:
            return jsonify({'error': '缺少文件路径'}), 400
        
        result = services.get_file_content(file_path)
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'读取文件失败: {str(e)}'}), 500

@web_editor_bp.route('/save-file', methods=['POST'])
def save_file_content():
    """保存文件内容"""
    try:
        data = request.get_json()
        file_path = data.get('file_path')
        content = data.get('content')
        
        if not file_path or content is None:
            return jsonify({'error': '缺少文件路径或内容'}), 400
        
        result = services.save_file_content(file_path, content)
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'保存文件失败: {str(e)}'}), 500

@web_editor_bp.route('/upload-background', methods=['POST'])
def upload_background_image():
    """上传背景图片"""
    try:
        if 'background_file' not in request.files:
            return jsonify({'error': '没有选择文件'}), 400
        
        file = request.files['background_file']
        process_id = request.form.get('process_id')
        
        if not file.filename or file.filename == '' or not process_id:
            return jsonify({'error': '缺少文件或处理任务ID'}), 400
        
        result = services.upload_background_image(file, process_id)
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

@web_editor_bp.route('/apply-background', methods=['POST'])
def apply_background():
    """应用背景图到所有代码文件"""
    try:
        data = request.get_json()
        process_id = data.get('process_id')
        background_file = data.get('background_file')
        
        if not process_id or not background_file:
            return jsonify({'error': '缺少必要参数'}), 400
        
        result = services.apply_background_to_code(process_id, background_file)
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'应用背景失败: {str(e)}'}), 500

@web_editor_bp.route('/search-files', methods=['POST'])
def search_editor_files():
    """搜索编辑器文件"""
    try:
        data = request.get_json()
        process_id = data.get('process_id')
        search_term = data.get('search_term', '')
        
        if not process_id:
            return jsonify({'error': '缺少处理任务ID'}), 400
        
        result = services.search_editor_files(process_id, search_term)
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'搜索失败: {str(e)}'}), 500

@web_editor_bp.route('/page-video/<process_id>/<filename>')
def preview_page_video(process_id, filename):
    """提供视频预览服务"""
    try:
        with services.processing_lock:
            if process_id not in services.processing_jobs:
                return jsonify({'error': '处理任务不存在'}), 404
            
            job = services.processing_jobs[process_id]
            if not job['output_dir']:
                return jsonify({'error': '处理任务尚未生成输出目录'}), 400
        
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': '非法的文件名'}), 400
        
        if not filename.lower().endswith('.mp4'):
            return jsonify({'error': '非视频文件'}), 400
        
        video_preview_dir = os.path.join(job['output_dir'], 'final_results', 'Video_Preview')
        filepath = os.path.join(video_preview_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': '视频文件不存在'}), 404
        
        abs_preview_dir = os.path.abspath(video_preview_dir)
        abs_filepath = os.path.abspath(filepath)
        
        if not abs_filepath.startswith(abs_preview_dir + os.sep):
            return jsonify({'error': '文件路径不安全'}), 400
        
        return send_file(abs_filepath, mimetype='video/mp4')
    
    except Exception as e:
        return jsonify({'error': f'预览视频失败: {str(e)}'}), 500

@web_editor_bp.route('/ai-edit', methods=['POST'])
def ai_edit_code():
    """智能体编辑代码"""
    try:
        data = request.get_json()
        original_code = data.get('original_code')
        edit_request = data.get('edit_request')
        filename = data.get('filename')
        
        if not original_code or not edit_request:
            return jsonify({'error': '缺少原始代码或修改需求'}), 400
        
        result = services.ai_edit_code(original_code, edit_request, filename)
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'智能体编辑失败: {str(e)}'}), 500

@web_editor_bp.route('/page-associations/<process_id>')
def get_page_associations(process_id):
    """获取页面与视频的关联关系"""
    try:
        associations = services.get_page_video_associations(process_id)
        return jsonify({
            'success': True,
            'associations': associations
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500