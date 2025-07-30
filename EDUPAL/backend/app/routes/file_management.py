# 文件管理 (列表, 预览, 删除)
# app/routes/file_management.py
from flask import Blueprint, jsonify, request, send_file, current_app
from .. import services
import os
import shutil

# 创建一个名为'file_management'的蓝图
file_management_bp = Blueprint('file_management', __name__)


@file_management_bp.route('/pdf-list')
def pdf_list_route():
    papers = services.get_all_papers_list()
    return jsonify({'success': True, 'pdfs': papers})

@file_management_bp.route('/webpage-list')
def get_webpage_list():
    """获取已下载的网页文件列表"""
    try:
        result = services.get_webpage_list()
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'获取网页列表失败: {str(e)}'}), 500

@file_management_bp.route('/pdf-preview/<filename>')
def preview_pdf(filename):
    """提供PDF文件预览服务"""
    try:
        download_dir = 'downloaded_papers'
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': '非法的文件名'}), 400
        
        if not filename.lower().endswith('.pdf'):
            return jsonify({'error': '非PDF文件'}), 400
        
        filepath = os.path.join(download_dir, filename)
        if not os.path.exists(filepath):
            return jsonify({'error': '文件不存在'}), 404
        
        abs_download_dir = os.path.abspath(download_dir)
        abs_filepath = os.path.abspath(filepath)
        
        if not abs_filepath.startswith(abs_download_dir + os.sep):
            return jsonify({'error': '文件路径不安全'}), 400
        
        return send_file(abs_filepath, mimetype='application/pdf')
    
    except Exception as e:
        return jsonify({'error': f'预览PDF失败: {str(e)}'}), 500

@file_management_bp.route('/webpage-preview/<filename>')
def preview_webpage(filename):
    """提供网页文件预览服务"""
    try:
        download_dir = 'downloaded_webpages'
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': '非法的文件名'}), 400
        
        if not filename.lower().endswith('.html'):
            return jsonify({'error': '非HTML文件'}), 400
        
        filepath = os.path.join(download_dir, filename)
        if not os.path.exists(filepath):
            return jsonify({'error': '文件不存在'}), 404
        
        abs_download_dir = os.path.abspath(download_dir)
        abs_filepath = os.path.abspath(filepath)
        
        if not abs_filepath.startswith(abs_download_dir + os.sep):
            return jsonify({'error': '文件路径不安全'}), 400
        
        return send_file(abs_filepath, mimetype='text/html')
    
    except Exception as e:
        return jsonify({'error': f'预览网页失败: {str(e)}'}), 500

@file_management_bp.route('/clear-papers', methods=['POST'])
def clear_papers():
    """清除所有已下载的内容（论文和网页）"""
    try:
        result = services.clear_all_content()
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'清除内容失败: {str(e)}'}), 500

@file_management_bp.route('/delete-content', methods=['POST'])
def delete_content():
    """删除单个内容文件"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        content_type = data.get('type')
        
        if not filename or not content_type:
            return jsonify({'error': '缺少文件名或类型参数'}), 400
        
        result = services.delete_single_content(filename, content_type)
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'删除内容失败: {str(e)}'}), 500

@file_management_bp.route('/delete-folder', methods=['POST'])
def delete_folder_route():
    """【新增的路由】根据前端传来的 batch_process_id 删除整个文件夹"""
    data = request.get_json()
    if not data or 'batch_process_id' not in data:
        return jsonify({'success': False, 'error': '请求无效, 缺少 batch_process_id'}), 400
    
    batch_id = data['batch_process_id']
    papers_dir = current_app.config['UPLOAD_FOLDER']
    folder_found_and_deleted = False

    for item_name in os.listdir(papers_dir):
        item_path = os.path.join(papers_dir, item_name)
        if os.path.isdir(item_path) and item_name.endswith(f"_{batch_id}"):
            try:
                shutil.rmtree(item_path)
                folder_found_and_deleted = True
                print(f"已通过API请求删除文件夹: {item_path}")
                break
            except Exception as e:
                print(f"API删除文件夹 {item_path} 时出错: {e}")
                return jsonify({'success': False, 'error': f'服务器删除文件夹时出错: {e}'}), 500

    if folder_found_and_deleted:
        return jsonify({'success': True, 'message': '文件夹已成功删除'})
    else:
        return jsonify({'success': False, 'error': '未在服务器上找到需要删除的文件夹'}), 404

