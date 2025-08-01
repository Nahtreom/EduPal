from flask import Flask, render_template, request, jsonify, send_file
import os
from werkzeug.utils import secure_filename
import services
import uuid
from datetime import datetime
import sys
from flask_cors import CORS  # 导入CORS支持
import json
import traceback


app = Flask(__name__)
# 添加CORS支持，允许所有来源
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

# 确保 'downloaded_papers' 文件夹在项目根目录下存在,用于存放上传文件的根目录
UPLOAD_FOLDER = 'downloaded_papers'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# =========================================================
# =================== 企业级 Agent API (V1) =================
# =========================================================

def _handle_api_generation_request(output_format):
    """
    【内部辅助函数V3】根据 options 中的 'mode' 字段，
    分发到单文件处理或文件夹处理逻辑。
    """
    try:
        # 1. 基础参数校验
        if 'pdf_files[]' not in request.files:
            return jsonify({'error': "必需的参数 'pdf_files[]' 未找到"}), 400
        if 'options' not in request.form:
            return jsonify({'error': "必需的参数 'options' (JSON 字符串) 未找到"}), 400

        files = request.files.getlist('pdf_files[]')
        if not files or not files[0].filename:
            return jsonify({'error': "至少需要上传一个PDF文件"}), 400

        try:
            options = json.loads(request.form['options'])
        except json.JSONDecodeError:
            return jsonify({'error': "参数 'options' 必须是合法的JSON格式"}), 400

        # 2. 【核心逻辑】根据 'mode' 分发处理
        mode = options.get('mode')
        if mode not in ['single', 'batch']:
            return jsonify({'error': "参数 'options' 中必须包含 'mode' 字段，其值为 'single' 或 'batch'"}), 400

        result = {}
        
        # --- 情况A: 单文件处理逻辑 ---
        if mode == 'single':
            if len(files) != 1:
                return jsonify({'error': "单文件模式(mode: 'single')下，只能上传一个PDF文件"}), 400
            
            file = files[0]
            pdf_filename = secure_filename(file.filename)
            
            # 为单文件创建一个临时存放位置
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], f"single_{str(uuid.uuid4())}")
            os.makedirs(upload_path, exist_ok=True)
            pdf_path = os.path.join(upload_path, pdf_filename)
            file.save(pdf_path)
            
            # 调用您的单文件处理 service 函数
            result = services.start_paper_processing(
                pdf_path=pdf_path,
                pdf_filename=pdf_filename,
                output_format=output_format,
                video_duration=options.get('video_duration', 'medium'),
                voice_type=options.get('voice_type', 'female'),
                # background_choice=options.get('background_choice', 'default'),
                background_choice=options.get('background_choice', 'background.png'),
                auto_continue=True # 如果是false就可以不写这一行,仅仅在企业配置接口的时候需要
            )

        # --- 情况B: 批量/文件夹处理逻辑 ---
        elif mode == 'batch':
            folder_name = options.get('folder_name', f'api_batch_{output_format}')
            batch_id = str(uuid.uuid4())
            unique_folder_name = f"{secure_filename(folder_name)}_{batch_id}"
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_folder_name)
            os.makedirs(upload_path, exist_ok=True)

            for file in files:
                file_path = os.path.join(upload_path, secure_filename(file.filename))
                file.save(file_path)
            
            # 调用您的文件夹处理 service 函数
            result = services.start_folder_processing(
                folder_path=upload_path,
                folder_name=folder_name,
                unique_base_name=unique_folder_name,
                output_format=output_format,
                video_duration=options.get('video_duration', 'medium'),
                voice_type=options.get('voice_type', 'female'),
                # background_choice=options.get('background_choice', 'default),
                background_choice=options.get('background_choice', 'background.png'),
                auto_continue=True # 如果是false就可以不写这一行
            )

        # 3. 返回标准响应
        task_id = result.get('process_id')
        if not task_id:
            return jsonify({'error': '服务层未能成功创建任务并返回 process_id'}), 500

        return jsonify({
            "task_id": task_id,
            "status": "queued",
            "message": f"{output_format.capitalize()} ({mode} mode) 任务已创建。",
            "status_url": f"/api/v1/status/{task_id}"
        }), 202

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'创建任务时发生内部错误: {str(e)}'}), 500

# --- 公开的API路由 ---

@app.route('/api/v1/paper2video', methods=['POST'])
def api_paper_to_video():
    """【API入口】从论文生成视频"""
    return _handle_api_generation_request('video')

@app.route('/api/v1/paper2markdown', methods=['POST'])
def api_paper_to_markdown():
    """【API入口】从论文生成Markdown文档"""
    return _handle_api_generation_request('markdown')

@app.route('/api/v1/paper2ppt', methods=['POST'])
def api_paper_to_ppt():
    """【API入口】从论文生成PPT"""
    return _handle_api_generation_request('ppt')


# --- 通用的状态和结果查询API (保持不变) ---

@app.route('/api/v1/status/<task_id>', methods=['GET'])
def api_get_status(task_id):
    """【API状态查询】根据任务ID，返回任务的当前状态、进度和结果。"""
    with services.processing_lock:
        if task_id not in services.processing_jobs:
            return jsonify({'error': '未找到指定的任务ID'}), 404
        
        job = services.processing_jobs[task_id]

        if job['status'] == 'failed':
            response = { "task_id": task_id, "status": "failed", "error": job.get('error', '未知错误') }
        elif job['stage'] == 'completed':
            response = {
                "task_id": task_id,
                "status": "completed",
                "progress": 100,
                "result": {
                    "filename": os.path.basename(job.get('final_output_path', '')),
                    "download_url": f"/api/v1/result/{task_id}"
                }
            }
        else:
            response = {
                "task_id": task_id,
                "status": "processing",
                "progress": job.get('progress', 0),
                "details": job.get('current_step', '正在初始化...')
            }
            
    return jsonify(response)


@app.route('/api/v1/result/<task_id>', methods=['GET'])
def api_get_result(task_id):
    """【API结果下载】根据任务ID，提供最终生成文件的下载。"""
    with services.processing_lock:
        if task_id not in services.processing_jobs:
            return jsonify({'error': '未找到指定的任务ID'}), 404
        
        job = services.processing_jobs[task_id]

        if job['stage'] != 'completed' or not job.get('final_output_path'):
            return jsonify({'error': '任务尚未完成或未生成结果文件'}), 404
            
        file_path = job['final_output_path']
        if not os.path.exists(file_path):
            return jsonify({'error': '结果文件在服务器上不存在'}), 404

    return send_file(file_path, as_attachment=True)



# ========================= 核心功能API =========================
@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    """上传PDF文件"""
    # 处理用户上传的PDF文件，进行文件类型和大小检查，并调用服务层函数进行处理。
    try:
        if 'pdf_file' not in request.files:
            return jsonify({'error': '没有选择文件'}), 400
        
        file = request.files['pdf_file']
        
        # 检查文件名是否为空
        if not file.filename or file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        # 检查文件类型
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': '只支持PDF文件'}), 400
        
        # 调用服务函数处理上传
        result = services.upload_pdf_file(file)
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

@app.route('/upload-folder', methods=['POST'])
def upload_folder():
    """
    处理文件夹上传的路由函数。
    """
    import json
    import traceback
    print("开始处理文件夹上传请求...")
    try:
        # 1. 从表单中获取文件夹名和文件列表
        folder_name = request.form.get('folder_name')
        uploaded_files = request.files.getlist('paper_files[]')

        print(f"接收到文件夹: {folder_name}, 包含 {len(uploaded_files)} 个文件")
        
        if not folder_name or not uploaded_files:
            print("错误: 没有提供文件夹名称或文件")
            return jsonify({'success': False, 'error': '没有提供文件夹名称或文件'}), 400

        # 2. 为这次上传创建一个唯一的批处理ID和子文件夹，防止重名
        batch_id = str(uuid.uuid4())
        # 使用 secure_filename 清理文件夹名，并拼接唯一ID
        unique_folder_name = f"{secure_filename(folder_name)}_{batch_id}"
        # 完整的保存路径
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_folder_name)
        os.makedirs(upload_path, exist_ok=True)
        print(f"创建上传目录: {upload_path}")

        # 【新增】将原始文件夹名存入该目录的元数据中
        folder_meta_path = os.path.join(upload_path, 'folder_metadata.json')
        with open(folder_meta_path, 'w', encoding='utf-8') as f:
            json.dump({'original_name': folder_name}, f, ensure_ascii=False, indent=4)

        # 3. 【最关键修改】创建一个列表，用于存储每个文件的信息
        files_info_list = []

        # 4. 遍历所有上传的文件
        for i, file in enumerate(uploaded_files):
            print(f"处理第 {i+1}/{len(uploaded_files)} 个文件: {file.filename}")
            if file and file.filename and file.filename.lower().endswith('.pdf'):
                # 获取原始文件名并清理
                original_filename = file.filename
                saved_filename = secure_filename(original_filename)
                
                # 保存文件到我们创建的唯一子文件夹中
                file_path = os.path.join(upload_path, saved_filename)
                try:
                    file.save(file_path)
                    print(f"成功保存文件: {file_path}")
                    
                    # 构建这个文件在服务器上的相对路径，作为前端使用的 "saved_name"
                    frontend_saved_name = f"{unique_folder_name}/{saved_filename}"

                    # 将文件信息存入列表
                    files_info_list.append({
                        "original_name": original_filename,
                        "saved_name": frontend_saved_name
                    })
                except Exception as e:
                    print(f"保存文件 {original_filename} 时出错: {str(e)}")
        
        if not files_info_list:
            print("错误: 上传的文件中没有有效的PDF")
            return jsonify({'success': False, 'error': '上传的文件中没有有效的PDF'}), 400

        # 5. 构建并返回【正确格式】的JSON响应
        response = {
            'success': True,
            'message': f'文件夹 "{folder_name}" 上传成功, 包含 {len(files_info_list)} 个PDF。',
            'folder_name': folder_name,
            'batch_process_id': batch_id,
            'server_path': upload_path,
            'files': files_info_list  # <--- 将包含所有文件信息的列表返回给前端
        }
        print("文件夹上传成功，返回响应")
        return jsonify(response)

    except Exception as e:
        # 捕获未知错误，返回错误信息
        error_msg = f"上传时发生错误: {e}"
        print(error_msg)
        print(traceback.format_exc())  # 打印完整堆栈信息
        return jsonify({'success': False, 'error': error_msg}), 500

# =========================================================
# 【重要】文件预览服务路由
# 这个路由是前端“预览”功能正常工作所必需的。
# 它会拦截所有 /uploads/ 开头的请求，并从服务器的文件夹中寻找相应文件。
# =========================================================
from flask import send_from_directory
@app.route('/uploads/<path:filepath>')
def serve_upload(filepath):
    """
    提供对上传文件的访问，用于前端预览。
    例如：前端请求 /uploads/folder1/doc1.pdf
    此函数会从 UPLOAD_FOLDER (即 downloaded_papers/) 中寻找 folder1/doc1.pdf 并返回。
    """
    print(f"尝试提供文件: {filepath} 从目录: {app.config['UPLOAD_FOLDER']}")
    return send_from_directory(app.config['UPLOAD_FOLDER'], filepath)

@app.route('/search', methods=['POST'])
def search():
    """搜索API"""
    # 根据用户指定的类型（网页或论文）和关键词，调用相应的服务层函数执行搜索。
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

@app.route('/analyze-need', methods=['POST'])
def analyze_need():
    """分析用户需求并提炼关键词"""
    # 接收用户的自然语言输入，通过AI分析，提炼出核心搜索关键词。
    data = request.get_json()
    user_input = data.get('user_input', '')
    search_type = data.get('search_type', 'web')
    
    if not user_input:
        return jsonify({'error': '请输入您的需求'}), 400
    
    try:
        result = services.analyze_user_need(user_input, search_type)
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        return jsonify({'error': f'需求分析失败: {str(e)}'}), 500

@app.route('/smart-filter', methods=['POST'])
def smart_filter():
    """智能筛选API"""
    # 根据用户的原始需求和搜索关键词，对初步搜索到的结果（网页或论文）进行智能筛选和排序。
    data = request.get_json()
    original_input = data.get('original_input', '')
    keyword = data.get('keyword', '')
    items = data.get('papers', [])  # 兼容论文搜索的参数名
    search_type = data.get('search_type', 'paper')  # 默认为论文
    
    if not original_input or not items:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        # 根据搜索类型调用相应的筛选函数
        if search_type == 'paper':
            result = services.smart_filter_papers(original_input, keyword, items)
        else:  # web
            result = services.smart_filter_content(original_input, keyword, items, 'web')
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        return jsonify({'error': f'智能筛选失败: {str(e)}'}), 500

@app.route('/download-progress')
def get_download_progress():
    """获取下载进度"""
    # 查询并返回当前文件（论文/网页）的下载进度。
    try:
        progress = services.get_download_progress()
        return jsonify({
            'success': True,
            'progress': progress
        })
    except Exception as e:
        return jsonify({'error': f'获取下载进度失败: {str(e)}'}), 500

@app.route('/crawl', methods=['POST'])
def crawl_papers():
    """爬取论文PDF"""
    # 接收论文的URL和标题列表，启动后台任务爬取并保存PDF文件。
    data = request.get_json()
    urls = data.get('urls', [])
    titles = data.get('titles', [])
    
    if not urls:
        return jsonify({'error': '未选择要爬取的论文'}), 400
    
    try:
        result = services.crawl_papers(urls, titles)
        response_data = {
            'success': True,
            **result
        }
        
        return jsonify(response_data)
    
    except Exception as e:
        return jsonify({'error': f'爬取失败: {str(e)}'}), 500

@app.route('/crawl-webpages', methods=['POST'])
def crawl_webpages():
    """爬取网页内容"""
    # 接收网页的URL和标题列表，启动后台任务爬取并保存为HTML文件。
    data = request.get_json()
    urls = data.get('urls', [])
    titles = data.get('titles', [])
    
    if not urls:
        return jsonify({'error': '未选择要爬取的网页'}), 400
    
    try:
        result = services.crawl_webpages(urls, titles)
        response_data = {
            'success': True,
            **result
        }
        
        return jsonify(response_data)
    
    except Exception as e:
        return jsonify({'error': f'网页爬取失败: {str(e)}'}), 500


# ========================= 文件管理与预览API =========================
@app.route('/pdf-list')
def pdf_list_route():
    papers = services.get_all_papers_list()
    return jsonify({'success': True, 'pdfs': papers})

@app.route('/webpage-list')
def get_webpage_list():
    """获取已下载的网页文件列表"""
    # 查询并返回服务器上所有已下载的网页HTML文件列表。
    try:
        result = services.get_webpage_list()
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'获取网页列表失败: {str(e)}'}), 500

@app.route('/pdf-preview/<filename>')
def preview_pdf(filename):
    """提供PDF文件预览服务"""
    # 根据文件名，安全地定位并以文件流形式返回PDF，供浏览器内联预览。
    try:
        download_dir = 'downloaded_papers'
        
        # 安全检查：确保文件名不包含路径遍历字符
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': '非法的文件名'}), 400
        
        # 检查文件扩展名
        if not filename.lower().endswith('.pdf'):
            return jsonify({'error': '非PDF文件'}), 400
        
        filepath = os.path.join(download_dir, filename)
        
        # 检查文件是否存在
        if not os.path.exists(filepath):
            return jsonify({'error': '文件不存在'}), 404
        
        # 获取绝对路径进行最终安全检查
        abs_download_dir = os.path.abspath(download_dir)
        abs_filepath = os.path.abspath(filepath)
        
        if not abs_filepath.startswith(abs_download_dir + os.sep):
            return jsonify({'error': '文件路径不安全'}), 400
        
        return send_file(abs_filepath, mimetype='application/pdf')
    
    except Exception as e:
        return jsonify({'error': f'预览PDF失败: {str(e)}'}), 500

@app.route('/webpage-preview/<filename>')
def preview_webpage(filename):
    """提供网页文件预览服务"""
    # 根据文件名，安全地定位并以文件流形式返回HTML文件，供浏览器预览。
    try:
        download_dir = 'downloaded_webpages'
        
        # 安全检查：确保文件名不包含路径遍历字符
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': '非法的文件名'}), 400
        
        # 检查文件扩展名
        if not filename.lower().endswith('.html'):
            return jsonify({'error': '非HTML文件'}), 400
        
        filepath = os.path.join(download_dir, filename)
        
        # 检查文件是否存在
        if not os.path.exists(filepath):
            return jsonify({'error': '文件不存在'}), 404
        
        # 获取绝对路径进行最终安全检查
        abs_download_dir = os.path.abspath(download_dir)
        abs_filepath = os.path.abspath(filepath)
        
        if not abs_filepath.startswith(abs_download_dir + os.sep):
            return jsonify({'error': '文件路径不安全'}), 400
        
        return send_file(abs_filepath, mimetype='text/html')
    
    except Exception as e:
        return jsonify({'error': f'预览网页失败: {str(e)}'}), 500

@app.route('/clear-papers', methods=['POST'])
def clear_papers():
    """清除所有已下载的内容（论文和网页）"""
    # 调用服务层函数，删除所有已下载的PDF和网页文件。
    try:
        result = services.clear_all_content()
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'清除内容失败: {str(e)}'}), 500

@app.route('/delete-content', methods=['POST'])
def delete_content():
    """删除单个内容文件"""
    # 根据文件名和类型（PDF或网页），删除指定的单个文件。
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

@app.route('/delete-folder', methods=['POST'])
def delete_folder_route():
    import shutil
    """【新增的路由】根据前端传来的 batch_process_id 删除整个文件夹"""
    
    data = request.get_json()
    if not data or 'batch_process_id' not in data:
        return jsonify({'success': False, 'error': '请求无效, 缺少 batch_process_id'}), 400
    
    batch_id = data['batch_process_id']
    papers_dir = app.config['UPLOAD_FOLDER']
    folder_found_and_deleted = False

    # 在上传目录中扫描，找到与 batch_id 匹配的文件夹
    # 我们的文件夹命名规则是 "原始名_batch_id"
    for item_name in os.listdir(papers_dir):
        item_path = os.path.join(papers_dir, item_name)
        if os.path.isdir(item_path) and item_name.endswith(f"_{batch_id}"):
            try:
                # 找到匹配的文件夹，使用 shutil.rmtree 递归删除
                shutil.rmtree(item_path)
                folder_found_and_deleted = True
                print(f"已通过API请求删除文件夹: {item_path}")
                break  # 找到并删除后即可退出循环
            except Exception as e:
                print(f"API删除文件夹 {item_path} 时出错: {e}")
                return jsonify({'success': False, 'error': f'服务器删除文件夹时出错: {e}'}), 500

    if folder_found_and_deleted:
        return jsonify({'success': True, 'message': '文件夹已成功删除'})
    else:
        return jsonify({'success': False, 'error': '未在服务器上找到需要删除的文件夹'}), 404

# ========================= 内容处理与生成API =========================
@app.route('/start-processing', methods=['POST'])
def start_processing():
    """开始论文处理流程"""
    import subprocess
    import threading
    
    # 【修改】使用 request.form 来获取表单字段，而不是 request.get_json()
    # 这些键名 ('filename', 'video_duration' 等) 必须与前端 FormData.append() 中的键名完全一致
    pdf_filename = request.form.get('filename')
    video_duration = request.form.get('video_duration', 'medium')
    voice_type = request.form.get('voice_type', 'female')
    output_format = request.form.get('output_format', 'video')
    # background_choice = request.form.get('background_choice', 'default') # 'default'表示不选择
    background_choice = request.form.get('background_choice', 'background.png')

    if not pdf_filename:
        return jsonify({'error': '请提供PDF文件名'}), 400
    
    # 构建PDF文件的完整路径
    pdf_path = os.path.join('downloaded_papers', pdf_filename)
    
    if not os.path.exists(pdf_path):
        return jsonify({'error': 'PDF文件不存在'}), 404
    
    try:
        # 调用服务层函数。
        # 注意：services.start_paper_processing 内部已经设计为会从 request 对象中
        # 提取文件和文本，所以我们这里只需要把主要的参数传递过去即可。
        # 上一步在 services.py 中做的修改现在就派上用场了。
        result = services.start_paper_processing(
            pdf_path, 
            pdf_filename, 
            video_duration, 
            voice_type, 
            output_format,
            background_choice=background_choice # <-- 新增
        )
        
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'启动处理失败: {str(e)}'}), 500
        
# 【新增】启动整个文件夹处理的路由
@app.route('/start-folder-processing', methods=['POST'])
def start_folder_processing():
    """根据文件夹路径，开始处理整个文件夹中的论文"""
    import traceback
    print("开始处理文件夹批量处理请求...")
    try:
        folder_name = request.form.get('folder_name')
        batch_id = request.form.get('batch_process_id') # 获取从前端传来的ID
        output_format = request.form.get('output_format', 'video')
        # ... 获取其他处理参数 ...

        # 【新增】从请求中获取音色相关的参数，与单篇处理的路由保持一致
        video_duration = request.form.get('video_duration', 'medium')
        voice_type = request.form.get('voice_type', 'female')
        # background_choice = request.form.get('background_choice', 'default')
        background_choice = request.form.get('background_choice', 'background.png')

        print(f"接收到文件夹处理请求: 文件夹={folder_name}, 批次ID={batch_id}, 格式={output_format}, "
              f"时长={video_duration}, 音色={voice_type}, 背景={background_choice}")

        if not folder_name or not batch_id:
            print("错误: 缺少文件夹信息或批次ID")
            return jsonify({'error': '缺少文件夹信息'}), 400
        
        # 重新构建服务器上的文件夹路径
        safe_folder_name = secure_filename(folder_name)
        # 【核心修改】创建一个能代表本次任务的、唯一的 "基础名"
        # 格式：文件夹名 + batch_id的前8位
        # 例如：test_0bd5b411
        # unique_base_name = f"{safe_folder_name}_{batch_id[:8]}"
        unique_base_name = f"{safe_folder_name}_{batch_id}"
        folder_path = os.path.join('downloaded_papers', f"{safe_folder_name}_{batch_id}")
        
        print(f"构建文件夹路径: {folder_path}")

        if not os.path.isdir(folder_path):
            error_msg = f"服务器上找不到对应的文件夹: {folder_path}"
            print(f"错误: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 404
        
        # 检查文件夹中是否有PDF文件
        pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
        if not pdf_files:
            error_msg = f"文件夹中没有PDF文件"
            print(f"错误: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 400
            
        print(f"文件夹中包含 {len(pdf_files)} 个PDF文件")
        
        # 【核心】调用一个新的服务层函数来处理文件夹
        # 注意：这里传递的是文件夹路径 folder_path
        # 【核心修改】调用服务层函数时，将所有相关参数都传递过去
        # services.py 中的函数会处理 request.files.get('voiceFile') 和 request.form.get('voiceText')
        result = services.start_folder_processing(
            folder_path=folder_path,
            folder_name=folder_name,
            # 将 unique_base_name 作为新的参数传递
            unique_base_name=unique_base_name, 
            video_duration=video_duration,
            voice_type=voice_type,
            output_format=output_format,
            background_choice=background_choice # <-- 新增
            # video_duration=request.form.get('video_duration', 'medium'),
            # voice_type=request.form.get('voice_type', 'female'),
            # output_format=request.form.get('output_format', 'video')
        )

        # 【核心修改点 2】确保返回给前端的JSON中，包含了这个主任务ID
        # 前端将使用这个ID来轮询进度
        # 即使 services.start_folder_processing 返回的 result 里已经有其他信息，
        # 我们也要确保 process_id 被正确设置。
        response_data = {
            'success': True,
            'process_id': unique_base_name,  # <--- 这是关键！
            'message': f"文件夹 '{folder_name}' 的处理任务已启动。"
        }
        # 如果 service 返回了其他需要给前端的信息，可以合并
        if isinstance(result, dict):
            response_data.update(result)

        print(f"文件夹处理任务已成功启动，process_id={unique_base_name}")
        return jsonify(response_data)
    

    except Exception as e:
        # 为了更好地调试，打印出详细的错误信息
        error_msg = f"启动文件夹处理失败: {str(e)}"
        print(error_msg, file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return jsonify({'success': False, 'error': error_msg}), 500

@app.route('/continue-processing', methods=['POST'])
def continue_processing():
    """继续论文处理流程（Step 4.5-9）"""
    # 在某个中间步骤后（例如封面生成后），继续执行后续的内容处理步骤。
    data = request.get_json()
    process_id = data.get('process_id')
    
    if not process_id:
        return jsonify({'error': '请提供处理任务ID'}), 400
    
    try:
        result = services.continue_paper_processing(process_id)
        
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'继续处理失败: {str(e)}'}), 500

@app.route('/start-preview-feedback', methods=['POST'])
def start_preview_feedback():
    """检查预览和编辑状态（预览已集成到初始流程中）"""
    # 为指定的处理任务启动预览和反馈流程，准备好可供用户编辑的文件。
    data = request.get_json()
    process_id = data.get('process_id')
    
    if not process_id:
        return jsonify({'error': '请提供处理任务ID'}), 400
    
    try:
        result = services.start_preview_and_feedback(process_id)
        
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'启动预览和反馈失败: {str(e)}'}), 500

@app.route('/continue-after-feedback', methods=['POST'])
def continue_after_feedback():
    """交互编辑完成后继续处理（Step 6-9）"""
    # 在用户完成交互式编辑并保存后，接收继续处理的指令，完成最终内容的生成。
    data = request.get_json()
    process_id = data.get('process_id')
    
    if not process_id:
        return jsonify({'error': '请提供处理任务ID'}), 400
    
    try:
        result = services.continue_after_feedback(process_id)
        
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'继续处理失败: {str(e)}'}), 500


# ========================= 获取进度或结果   =========================
@app.route('/processing-status/<process_id>')
def get_processing_status(process_id):
    """获取处理状态"""
    # 根据处理ID，查询并返回特定任务的当前状态和进度。
    try:
        result = services.get_processing_status(process_id)
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'获取状态失败: {str(e)}'}), 500

@app.route('/processing-results')
def get_processing_results():
    """获取所有处理结果列表"""
    # 查询并返回所有已完成的内容处理任务及其结果。
    try:
        result = services.get_processing_results()
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'获取结果失败: {str(e)}'}), 500

@app.route('/download-result/<result_id>')
def download_processing_result(result_id):
    """下载处理结果"""
    # 根据结果ID，提供最终生成的文件（如视频、Markdown压缩包）给用户下载。
    try:
        file_path = services.get_result_download_path(result_id)
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': '结果文件不存在'}), 404
        
        return send_file(file_path, as_attachment=True)
    
    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 500


# ========================= Web版交互编辑器API =========================
@app.route('/editor/files/<process_id>')
def get_editor_files(process_id):
    """获取指定处理任务的可编辑文件列表"""
    # 为Web编辑器提供指定任务ID下所有可编辑文件的树状列表（如代码、脚本、文本文件）。
    try:
        result = services.get_editor_files(process_id)
        return jsonify({
            'success': True,
            **result
        })
    
    except Exception as e:
        return jsonify({'error': f'获取文件列表失败: {str(e)}'}), 500

@app.route('/editor/file-content', methods=['POST'])
def get_file_content():
    """获取文件内容"""
    # 根据文件路径，读取并返回其文本内容，供在Web编辑器中显示。
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

@app.route('/editor/save-file', methods=['POST'])
def save_file_content():
    """保存文件内容"""
    # 接收从Web编辑器传来的文件路径和修改后的内容，并将其保存到服务器。
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

@app.route('/editor/upload-background', methods=['POST'])
def upload_background_image():
    """上传背景图片"""
    # 处理用户为特定处理任务上传的背景图片。
    try:
        if 'background_file' not in request.files:
            return jsonify({'error': '没有选择文件'}), 400
        
        file = request.files['background_file']
        process_id = request.form.get('process_id')
        
        if not file.filename or file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        if not process_id:
            return jsonify({'error': '缺少处理任务ID'}), 400
        
        result = services.upload_background_image(file, process_id)
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

@app.route('/editor/apply-background', methods=['POST'])
def apply_background():
    """应用背景图到所有代码文件"""
    # 将用户上传的背景图片应用到指定处理任务的所有相关代码文件中。
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

@app.route('/editor/search-files', methods=['POST'])
def search_editor_files():
    """搜索编辑器文件"""
    # 在指定处理任务的文件中，根据搜索词查找匹配的文件。
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

@app.route('/editor/page-video/<process_id>/<filename>')
def preview_page_video(process_id, filename):
    """提供视频预览服务"""
    # 为Web编辑器提供分页视频的预览功能，根据任务ID和文件名安全地返回视频流。
    try:
        # 获取处理任务信息
        with services.processing_lock:
            if process_id not in services.processing_jobs:
                return jsonify({'error': '处理任务不存在'}), 404
            
            job = services.processing_jobs[process_id]
            if not job['output_dir']:
                return jsonify({'error': '处理任务尚未生成输出目录'}), 400
        
        # 安全检查：确保文件名不包含路径遍历字符
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': '非法的文件名'}), 400
        
        # 检查文件扩展名
        if not filename.lower().endswith('.mp4'):
            return jsonify({'error': '非视频文件'}), 400
        
        # 构建文件路径
        video_preview_dir = os.path.join(job['output_dir'], 'final_results', 'Video_Preview')
        filepath = os.path.join(video_preview_dir, filename)
        
        # 检查文件是否存在
        if not os.path.exists(filepath):
            return jsonify({'error': '视频文件不存在'}), 404
        
        # 获取绝对路径进行最终安全检查
        abs_preview_dir = os.path.abspath(video_preview_dir)
        abs_filepath = os.path.abspath(filepath)
        
        if not abs_filepath.startswith(abs_preview_dir + os.sep):
            return jsonify({'error': '文件路径不安全'}), 400
        
        return send_file(abs_filepath, mimetype='video/mp4')
    
    except Exception as e:
        return jsonify({'error': f'预览视频失败: {str(e)}'}), 500

@app.route('/editor/ai-edit', methods=['POST'])
def ai_edit_code():
    """智能体编辑代码"""
    # 接收原始代码和用户的编辑需求，调用AI服务自动修改代码，并返回修改后的结果。
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

@app.route('/editor/page-associations/<process_id>')
def get_page_associations(process_id):
    """获取页面与视频的关联关系"""
    # 查询并返回特定任务中，每个可编辑页面（如代码文件）与其对应的预览视频文件的关联信息。
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

# ========================= Markdown预览 =========================
@app.route('/markdown-preview/<process_id>')
def preview_markdown(process_id):
    """预览markdown文档内容"""
    # 当输出格式为Markdown时，解压最终的zip文件，提取.md内容和图片（转为base64），返回给前端进行预览。
    import zipfile
    import tempfile
    import base64
    import re
    
    try:
        with services.processing_lock:
            if process_id not in services.processing_jobs:
                return jsonify({
                    'success': False,
                    'error': '未找到处理任务'
                }), 404
            
            job = services.processing_jobs[process_id]
            if 'final_output_path' not in job or not job['final_output_path']:
                return jsonify({
                    'success': False,
                    'error': 'Markdown文档尚未生成完成'
                }), 404
            
            zip_path = job['final_output_path']
            if not os.path.exists(zip_path):
                return jsonify({
                    'success': False,
                    'error': 'Markdown文档文件不存在'
                }), 404
            
            # 提取zip文件并读取markdown内容
            markdown_content = ""
            images = []
            image_mapping = {}  # 用于存储原始图片路径到base64数据的映射
            
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # 查找markdown文件
                md_path = None
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith('.md'):
                            md_path = os.path.join(root, file)
                            with open(md_path, 'r', encoding='utf-8') as f:
                                markdown_content = f.read()
                            break
                    if markdown_content:
                        break
                
                if not md_path:
                    return jsonify({
                        'success': False,
                        'error': 'Markdown文件未找到'
                    }), 404
                
                # 查找并处理所有图片文件
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                            # 将图片转换为base64编码
                            img_path = os.path.join(root, file)
                            try:
                                with open(img_path, 'rb') as img_file:
                                    img_data = base64.b64encode(img_file.read()).decode()
                                    ext = os.path.splitext(file)[1][1:].lower()
                                    if ext == 'svg':
                                        mime_type = 'image/svg+xml'
                                    else:
                                        mime_type = f'image/{ext}'
                                    
                                    # 存储图片信息
                                    image_data = f'data:{mime_type};base64,{img_data}'
                                    images.append({
                                        'filename': file,
                                        'data': image_data
                                    })
                                    
                                    # 计算图片相对于markdown文件的路径
                                    rel_path = os.path.relpath(img_path, os.path.dirname(md_path))
                                    # 替换Windows路径分隔符为Linux风格
                                    rel_path = rel_path.replace('\\', '/')
                                    # 同时存储不同可能的路径形式以增加匹配概率
                                    image_mapping[rel_path] = image_data
                                    image_mapping[file] = image_data
                                    
                                    # 处理combined_images路径格式
                                    if 'combined_images/' in rel_path:
                                        image_mapping[rel_path.split('combined_images/')[1]] = image_data
                                        
                            except Exception as e:
                                print(f"处理图片 {file} 时出错: {e}")
                
                # 替换Markdown中的图片引用为base64数据
                def replace_image_path(match):
                    alt_text = match.group(1)
                    img_path = match.group(2)
                    
                    # 尝试不同的路径格式进行匹配
                    if img_path in image_mapping:
                        return f'![{alt_text}]({image_mapping[img_path]})'
                    
                    # 尝试提取文件名作为回退方案
                    img_filename = os.path.basename(img_path)
                    if img_filename in image_mapping:
                        return f'![{alt_text}]({image_mapping[img_filename]})'
                    
                    # 如果都找不到，保留原始路径
                    return match.group(0)
                
                # 使用正则表达式替换Markdown中的图片引用
                markdown_content = re.sub(r'!\[(.*?)\]\((.*?)\)', replace_image_path, markdown_content)
            
            return jsonify({
                'success': True,
                'markdown_content': markdown_content,
                'images': images,
                'filename': os.path.basename(zip_path)
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 添加一个新的路由来提供Markdown中引用的图片访问
@app.route('/markdown-images/<process_id>/<path:image_path>')
def serve_markdown_image(process_id, image_path):
    """为Markdown预览提供图片服务"""
    import os
    
    try:
        with services.processing_lock:
            if process_id not in services.processing_jobs:
                return jsonify({'error': '处理任务不存在'}), 404
            
            job = services.processing_jobs[process_id]
            if not job.get('output_dir'):
                return jsonify({'error': '处理任务尚未生成输出目录'}), 400
        
        # 处理图片路径中的特殊字符
        image_path = image_path.replace('..', '')  # 防止路径遍历攻击
        
        # 构建可能的图片路径
        output_dir = job.get('output_dir')
        possible_paths = [
            os.path.join(output_dir, image_path),
            os.path.join(output_dir, 'final_results', image_path),
            os.path.join(output_dir, 'combined_images', image_path)
        ]
        
        # 尝试查找图片
        for path in possible_paths:
            if os.path.exists(path) and os.path.isfile(path):
                # 获取文件扩展名，确定正确的MIME类型
                ext = os.path.splitext(path)[1][1:].lower()
                if ext == 'svg':
                    mime_type = 'image/svg+xml'
                elif ext in ['jpg', 'jpeg']:
                    mime_type = 'image/jpeg'
                elif ext == 'png':
                    mime_type = 'image/png'
                elif ext == 'gif':
                    mime_type = 'image/gif'
                else:
                    mime_type = 'application/octet-stream'
                
                return send_file(path, mimetype=mime_type)
        
        # 如果图片未找到
        return jsonify({'error': '图片未找到'}), 404
    
    except Exception as e:
        return jsonify({'error': f'获取图片失败: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5010, debug=False, use_reloader=False) 