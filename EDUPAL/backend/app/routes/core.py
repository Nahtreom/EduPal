# 核心功能 (主页, 上传, 搜索等)# app/routes/core.py
from flask import Blueprint, render_template, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from .. import services
import uuid
import os
import json
import sys

# 创建一个名为'core'的蓝图
core_bp = Blueprint('core', __name__)

# ========================= 核心功能API =========================
@core_bp.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@core_bp.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    """上传PDF文件"""
    # 处理用户上传的PDF文件，进行文件类型和大小检查，并调用服务层函数进行处理。
    try:
        if 'pdf_file' not in request.files:
            return jsonify({'error': '没有选择文件'}), 400
        
        file = request.files['pdf_file']
        
        if not file.filename or file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': '只支持PDF文件'}), 400
        
        result = services.upload_pdf_file(file)
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

@core_bp.route('/upload-folder', methods=['POST'])
def upload_folder():
    """处理文件夹上传的路由函数。"""
    try:
        folder_name = request.form.get('folder_name')
        uploaded_files = request.files.getlist('paper_files[]')

        if not folder_name or not uploaded_files:
            return jsonify({'success': False, 'error': '没有提供文件夹名称或文件'}), 400

        batch_id = str(uuid.uuid4())
        unique_folder_name = f"{secure_filename(folder_name)}_{batch_id}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_folder_name)
        os.makedirs(upload_path, exist_ok=True)

        folder_meta_path = os.path.join(upload_path, 'folder_metadata.json')
        with open(folder_meta_path, 'w', encoding='utf-8') as f:
            json.dump({'original_name': folder_name}, f, ensure_ascii=False, indent=4)

        files_info_list = []
        for file in uploaded_files:
            if file and file.filename.lower().endswith('.pdf'):
                original_filename = file.filename
                saved_filename = secure_filename(original_filename)
                
                file_path = os.path.join(upload_path, saved_filename)
                file.save(file_path)

                frontend_saved_name = f"{unique_folder_name}/{saved_filename}"

                files_info_list.append({
                    "original_name": original_filename,
                    "saved_name": frontend_saved_name
                })
        
        if not files_info_list:
            return jsonify({'success': False, 'error': '上传的文件中没有有效的PDF'}), 400

        return jsonify({
            'success': True,
            'message': f'文件夹 "{folder_name}" 上传成功, 包含 {len(files_info_list)} 个PDF。',
            'folder_name': folder_name,
            'batch_process_id': batch_id,
            'server_path': upload_path,
            'files': files_info_list
        })

    except Exception as e:
        print(f"上传时发生错误: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@core_bp.route('/search', methods=['POST'])
def search():
    """搜索API"""
    data = request.get_json()
    search_type = data.get('search_type')
    keyword = data.get('keyword')
    
    if not keyword:
        return jsonify({'error': '请输入搜索关键词'}), 400
    
    try:
        if search_type == 'web':
            results = services.search_web(keyword)
        elif search_type == 'paper':
            results = services.search_papers(keyword)
        else:
            return jsonify({'error': '无效的搜索类型'}), 400
        
        return jsonify({
            'success': True,
            'search_type': search_type,
            'keyword': keyword,
            'results': results
        })
    
    except Exception as e:
        return jsonify({'error': f'搜索失败: {str(e)}'}), 500

# =========================================================
# 【重要】文件预览服务路由
# 这个路由是前端“预览”功能正常工作所必需的。
# 它会拦截所有 /uploads/ 开头的请求，并从服务器的文件夹中寻找相应文件。
# =========================================================
@core_bp.route('/uploads/<path:filepath>')
def serve_upload(filepath):
    """
    提供对上传文件的访问，用于前端预览。
    例如：前端请求 /uploads/folder1/doc1.pdf
    此函数会从 UPLOAD_FOLDER (即 downloaded_papers/) 中寻找 folder1/doc1.pdf 并返回。
    """
    print(f"尝试提供文件: {filepath} 从目录: {current_app.config['UPLOAD_FOLDER']}")
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filepath)