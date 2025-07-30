import re
import requests
import os
import glob
import json
import hashlib
import concurrent.futures
import threading
from bs4 import BeautifulSoup
from exa_py import Exa
from api_call import process_text
import zipfile
import glob
import subprocess
from flask import request # 调用cosyvoice
import shutil # 用于移动文件
from datetime import datetime
from werkzeug.utils import secure_filename # 使用 werkzeug 的 secure_filename 保证安全

# 初始化 Exa API
EXA_API_KEY = '211ed197-9199-401d-9897-a8408526f8b8'
exa = Exa(EXA_API_KEY)

# 下载进度跟踪
download_progress = {
    'total': 0,
    'completed': 0,
    'failed': 0,
    'status': 'idle'  # idle, downloading, completed
}
progress_lock = threading.Lock()

def get_download_progress():
    """获取下载进度"""
    with progress_lock:
        return download_progress.copy()

def update_download_progress(completed=0, failed=0, status=None):
    """更新下载进度"""
    with progress_lock:
        if completed > 0:
            download_progress['completed'] += completed
        if failed > 0:
            download_progress['failed'] += failed
        if status:
            download_progress['status'] = status

def reset_download_progress(total=0):
    """重置下载进度"""
    with progress_lock:
        download_progress['total'] = total
        download_progress['completed'] = 0
        download_progress['failed'] = 0
        download_progress['status'] = 'downloading' if total > 0 else 'idle'

def analyze_user_need(user_input, search_type):
    """分析用户需求，提炼检索关键词"""
    # 根据搜索类型构建不同的提示词
    if search_type == 'web':
        prompt = f"""
请分析用户的搜索需求，并提炼出最适合网页搜索的关键词。

用户需求："{user_input}"

请分析用户的真实意图，提炼出1个最核心的检索关键词。关键词应该：
1. 准确反映用户的核心需求
2. 适合网页搜索引擎使用
3. 简洁明了，可以有定语
4. 使用中文或英文

请以JSON格式返回结果：
{{
    "keyword": "提炼的关键词",
    "reasoning": "选择这个关键词的理由",
    "search_intent": "用户的搜索意图分析"
}}

请只返回JSON格式的结果，不要包含其他文字。
"""
    else:  # paper search
        prompt = f"""
请分析用户的研究需求，并提炼出最适合学术论文搜索的关键词。

用户需求："{user_input}"

请分析用户的研究意图，提炼出1个最核心的学术检索关键词。关键词应该：
1. 准确反映用户的研究领域和方向
2. 适合arXiv等学术数据库搜索
3. 使用学术术语，简洁专业，可以有定语
4. 优先使用英文学术词汇

请以JSON格式返回结果：
{{
    "keyword": "提炼的关键词",
    "reasoning": "选择这个关键词的理由",
    "search_intent": "用户的研究意图分析"
}}

请只返回JSON格式的结果，不要包含其他文字。
"""
    
    # 调用AI API
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        api_key = config.get('api_key')
        model = config.get('model', 'gpt-4.5-preview')
        ai_response = process_text(prompt, api_key, model)
        
        # 解析AI响应
        try:
            # 尝试从响应中提取JSON
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = ai_response[json_start:json_end]
                ai_result = json.loads(json_str)
            else:
                raise ValueError("未找到JSON格式响应")
        except (json.JSONDecodeError, ValueError) as e:
            raise Exception(f'AI响应解析失败: {str(e)}')
        
        return {
            'keyword': ai_result.get('keyword', user_input),
            'reasoning': ai_result.get('reasoning', ''),
            'search_intent': ai_result.get('search_intent', ''),
            'original_input': user_input
        }
        
    except Exception as e:
        # 如果AI分析失败，返回原始输入作为关键词
        return {
            'keyword': user_input,
            'reasoning': '由于AI分析失败，使用原始输入作为关键词',
            'search_intent': '无法分析用户意图',
            'original_input': user_input
        }

def search_web(keyword):
    """搜索网页"""
    result = exa.search_and_contents(keyword, text=True, num_results=20)
    
    web_results = []
    for item in result.results:
        content = clean_web_content(item.text) if item.text else "无内容"
        if len(content) > 800:
            content = content[:800] + "..."
        
        web_results.append({
            'title': item.title or "无标题",
            'url': item.url or "#",
            'content': content
        })
    
    return {
        'total_count': len(result.results),
        'items': web_results
    }

def search_papers(keyword):
    """搜索论文"""
    query = f"site:arxiv.org/abs {keyword}"
    result = exa.search_and_contents(query, text=True, num_results=20)
    
    # 筛选有效的arxiv论文
    valid_results = []
    
    for item in result.results:
        if is_valid_arxiv_url(item.url):
            abstract = extract_abstract(item.text)
            valid_results.append({
                'title': item.title or "无标题",
                'url': item.url or "#",
                'abstract': abstract
            })
    
    return {
        'total_count': len(valid_results),
        'items': valid_results
    }

def smart_filter_papers(original_input, keyword, papers):
    """智能筛选论文"""
    return smart_filter_content(original_input, keyword, papers, 'paper')

def smart_filter_content(original_input, keyword, items, content_type):
    """智能筛选内容（论文或网页）"""
    # 根据内容类型构建不同的提示词
    if content_type == 'paper':
        content_label = "论文"
        item_fields = "摘要"
        content_key = "abstract"
        criteria = """
1. 论文内容与用户需求的匹配度
2. 论文的学术价值和实用性
3. 论文的深度和广度是否适合用户需求"""
    else:  # web
        content_label = "网页"
        item_fields = "内容"
        content_key = "content"
        criteria = """
1. 网页内容与用户需求的匹配度
2. 网页信息的权威性和可靠性
3. 网页信息的实用性和时效性"""
    
    # 构建发送给AI的提示词
    prompt = f"""
请根据用户的原始需求"{original_input}"，从以下{content_label}列表中选择最相关和有价值的{content_label}。

用户的原始需求：{original_input}
提炼的关键词：{keyword}

{content_label}列表：
"""
    
    for i, item in enumerate(items):
        prompt += f"\n{i+1}. 标题: {item.get('title', '无标题')}\n"
        
        # 处理内容字段，网页内容可能很长，需要截取
        content = item.get(content_key, f'无{item_fields}')
        if content_type == 'web' and len(content) > 500:
            content = content[:500] + "..."
        
        prompt += f"   {item_fields}: {content}\n"
        prompt += f"   链接: {item.get('url', '无链接')}\n"
    
    prompt += f"""

请综合考虑用户的原始需求"{original_input}"和提炼的关键词"{keyword}"，分析每个{content_label}与用户真实需求的相关性。
请选择最符合用户需求的{content_label}，考虑以下因素：
{criteria}

请以JSON格式返回结果，包含以下字段：
{{
    "recommended_papers": [内容索引列表，从0开始],
    "reasoning": "基于用户原始需求选择这些{content_label}的理由",
    "total_recommended": 推荐{content_label}数量
}}

请只返回JSON格式的结果，不要包含其他文字。
"""
    
    # 调用API - 从配置文件读取API密钥
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    api_key = config.get('api_key')
    model = config.get('model', 'gpt-4.5-preview')
    ai_response = process_text(prompt, api_key, model)
    
    # 解析AI响应
    try:
        # 尝试从响应中提取JSON
        json_start = ai_response.find('{')
        json_end = ai_response.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            json_str = ai_response[json_start:json_end]
            ai_result = json.loads(json_str)
        else:
            raise ValueError("未找到JSON格式响应")
    except (json.JSONDecodeError, ValueError) as e:
        raise Exception(f'AI响应解析失败: {str(e)}')
    
    # 验证AI返回的索引是否有效
    recommended_indices = ai_result.get('recommended_papers', [])
    valid_indices = [i for i in recommended_indices if 0 <= i < len(items)]
    
    # 构建推荐结果
    recommended_items = []
    for i in valid_indices:
        item = items[i].copy()
        item['original_index'] = i
        recommended_items.append(item)
    
    return {
        'recommended_papers': recommended_items,
        'reasoning': ai_result.get('reasoning', ''),
        'total_recommended': len(recommended_items)
    }

def crawl_papers(urls, titles):
    """爬取论文PDF（并行优化版）"""
    # 创建下载目录
    download_dir = 'downloaded_papers'
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    # 加载或创建元数据文件
    metadata_file = os.path.join(download_dir, 'metadata.json')
    metadata = load_metadata(metadata_file)
    
    # 准备下载任务
    download_tasks = []
    for i, url in enumerate(urls):
        pdf_url = convert_arxiv_url_to_pdf(url)
        if pdf_url:
            title = titles[i] if i < len(titles) else "未知标题"
            download_tasks.append((pdf_url, title))
    
    # 重置下载进度
    reset_download_progress(len(download_tasks))
    
    crawled_count = 0
    failed_urls = []
    
    # 使用线程池并行下载（最多5个并发）
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # 提交所有下载任务
        future_to_task = {
            executor.submit(download_single_pdf, pdf_url, download_dir, title, metadata): 
            (pdf_url, title) for pdf_url, title in download_tasks
        }
        
        # 处理完成的任务
        for future in concurrent.futures.as_completed(future_to_task):
            pdf_url, title = future_to_task[future]
            try:
                success, filename = future.result()
                if success:
                    crawled_count += 1
                    update_download_progress(completed=1)
                else:
                    failed_urls.append(pdf_url)
                    update_download_progress(failed=1)
            except Exception as e:
                print(f"下载任务执行失败: {pdf_url}, 错误: {str(e)}")
                failed_urls.append(pdf_url)
                update_download_progress(failed=1)
    
    # 保存元数据
    save_metadata(metadata_file, metadata)
    
    # 更新完成状态
    update_download_progress(status='completed')
    
    return {
        'crawled_count': crawled_count,
        'total_count': len(urls),
        'failed_count': len(failed_urls),
        'failed_urls': failed_urls if failed_urls else None
    }

def download_single_pdf(pdf_url, download_dir, title, metadata):
    """下载单个PDF文件（线程安全版本）"""
    try:
        # 从URL中提取论文ID作为文件名
        paper_id = pdf_url.split('/')[-1].replace('.pdf', '')
        filename = f"{paper_id}.pdf"
        filepath = os.path.join(download_dir, filename)
        
        # 如果文件已存在，跳过下载但更新元数据
        if os.path.exists(filepath):
            print(f"文件已存在，跳过下载: {filename}")
            with progress_lock:
                metadata[filename] = title
            return True, filename
        
        # 下载PDF
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 减少超时时间并添加重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(pdf_url, headers=headers, timeout=3000)
                response.raise_for_status()
                break
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"下载超时，正在重试 ({attempt + 1}/{max_retries}): {filename}")
                    continue
                else:
                    raise
        
        # 检查响应是否为PDF
        content_type = response.headers.get('content-type', '')
        if 'pdf' not in content_type.lower():
            print(f"响应不是PDF文件: {content_type}")
            return False, None
        
        # 保存文件
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        # 线程安全地保存标题到元数据
        with progress_lock:
            metadata[filename] = title
        
        print(f"成功下载: {filename}")
        return True, filename
        
    except requests.exceptions.RequestException as e:
        print(f"下载失败: {pdf_url}, 错误: {str(e)}")
        return False, None
    except Exception as e:
        print(f"保存文件失败: {str(e)}")
        return False, None

def crawl_webpages(urls, titles):
    """爬取网页内容（并行优化版）"""
    # 创建下载目录
    download_dir = 'downloaded_webpages'
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    # 加载或创建元数据文件
    metadata_file = os.path.join(download_dir, 'metadata.json')
    metadata = load_metadata(metadata_file)
    
    # 准备下载任务
    download_tasks = []
    for i, url in enumerate(urls):
        title = titles[i] if i < len(titles) else "未知标题"
        download_tasks.append((url, title))
    
    # 重置下载进度
    reset_download_progress(len(download_tasks))
    
    crawled_count = 0
    failed_urls = []
    
    # 使用线程池并行下载（最多3个并发，网页下载相对更快）
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # 提交所有下载任务
        future_to_task = {
            executor.submit(download_single_webpage, url, download_dir, title, metadata): 
            (url, title) for url, title in download_tasks
        }
        
        # 处理完成的任务
        for future in concurrent.futures.as_completed(future_to_task):
            url, title = future_to_task[future]
            try:
                success, filename = future.result()
                if success:
                    crawled_count += 1
                    update_download_progress(completed=1)
                else:
                    failed_urls.append(url)
                    update_download_progress(failed=1)
            except Exception as e:
                print(f"下载网页任务执行失败: {url}, 错误: {str(e)}")
                failed_urls.append(url)
                update_download_progress(failed=1)
    
    # 保存元数据
    save_metadata(metadata_file, metadata)
    
    # 更新完成状态
    update_download_progress(status='completed')
    
    return {
        'crawled_count': crawled_count,
        'total_count': len(urls),
        'failed_count': len(failed_urls),
        'failed_urls': failed_urls if failed_urls else None
    }

def download_single_webpage(url, download_dir, title, metadata):
    """下载单个网页（线程安全版本）"""
    try:
        # 生成基于URL的唯一文件名
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:8]
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:50]
        filename = f"{safe_title}_{url_hash}.html"
        filepath = os.path.join(download_dir, filename)
        
        # 如果文件已存在，跳过下载但更新元数据
        if os.path.exists(filepath):
            print(f"网页文件已存在，跳过下载: {filename}")
            with progress_lock:
                metadata[filename] = title
            return True, filename
        
        # 下载网页
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 网页下载超时时间设置为10秒
        response = requests.get(url, headers=headers, timeout=3000)
        response.raise_for_status()
        
        # 检查响应是否为HTML
        content_type = response.headers.get('content-type', '')
        if 'html' not in content_type.lower():
            print(f"响应不是HTML文件: {content_type}")
            return False, None
        
        # 解析HTML并清理
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 移除脚本和样式标签
        for script in soup(["script", "style"]):
            script.decompose()
        
        # 添加基础样式使页面更易读
        if soup.head:
            style_tag = soup.new_tag("style")
            style_tag.string = """
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    line-height: 1.6; 
                    max-width: 800px; 
                    margin: 0 auto; 
                    padding: 20px;
                    background: #fff;
                    color: #333;
                }
                img { max-width: 100%; height: auto; }
                pre { background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; }
                code { background: #f5f5f5; padding: 2px 4px; border-radius: 2px; }
                blockquote { border-left: 3px solid #ddd; margin-left: 0; padding-left: 20px; color: #666; }
            """
            soup.head.append(style_tag)
        
        # 保存HTML文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        
        # 线程安全地保存标题到元数据
        with progress_lock:
            metadata[filename] = title
        
        print(f"成功下载网页: {filename}")
        return True, filename
        
    except requests.exceptions.RequestException as e:
        print(f"下载网页失败: {url}, 错误: {str(e)}")
        return False, None
    except Exception as e:
        print(f"保存网页失败: {str(e)}")
        return False, None

def get_pdf_list():
    """获取已下载的PDF文件列表"""
    download_dir = 'downloaded_papers'
    if not os.path.exists(download_dir):
        return {'pdfs': [], 'count': 0}
    
    # 加载元数据
    metadata_file = os.path.join(download_dir, 'metadata.json')
    metadata = load_metadata(metadata_file)
    
    pdf_files = []
    for filepath in glob.glob(os.path.join(download_dir, '*.pdf')):
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        
        # 从元数据中获取标题，如果没有则使用文件名
        title = metadata.get(filename, filename.replace('.pdf', ''))
        
        pdf_files.append({
            'filename': filename,
            'title': title,
            'size': file_size,
            'path': filepath
        })
    
    # 按标题排序
    pdf_files.sort(key=lambda x: x['title'])
    
    return {'pdfs': pdf_files, 'count': len(pdf_files)}

def get_all_papers_list():
    """
    获取所有论文内容，包括单篇PDF和文件夹。
    """
    download_dir = 'downloaded_papers'
    if not os.path.exists(download_dir):
        return []

    all_content = []
    
    # 1. 首先，获取所有单篇PDF文件 (根目录下的)
    # 这部分逻辑您可能已经有了，可以直接复用
    metadata_file = os.path.join(download_dir, 'metadata.json')
    metadata = load_metadata(metadata_file) # 假设您有 load_metadata 函数
    
    # 使用 glob 找到所有根目录下的 pdf
    for filepath in glob.glob(os.path.join(download_dir, '*.pdf')):
        filename = os.path.basename(filepath)
        # 必须是 "upload_" 开头的，以和文件夹内的文件区分（如果需要）
        if filename.startswith('upload_'):
            all_content.append({
                'type': 'file',  # <--- 标记类型为 "文件"
                'filename': filename,
                'title': metadata.get(filename, filename.replace('.pdf', '')),
                'size': os.path.getsize(filepath)
            })

    # 2. 然后，查找所有子文件夹（即上传的论文集）
    for item in os.scandir(download_dir):
        if item.is_dir():
            folder_path = item.path
            folder_name_full = item.name # 例如 "MyPapers_batch_12345"
            
            # # 从文件夹名中解析出原始名称和 batch_id
            # parts = folder_name_full.rsplit('_', 1)
            # original_folder_name = parts[0]
            # batch_id = parts[1] if len(parts) > 1 else "unknown_id"

            # 【修改】优先从元数据读取文件夹名
            original_folder_name = ''
            folder_meta_path = os.path.join(folder_path, 'folder_metadata.json')
            if os.path.exists(folder_meta_path):
                with open(folder_meta_path, 'r', encoding='utf-8') as f:
                    folder_meta = json.load(f)
                    original_folder_name = folder_meta.get('original_name')
            
            # 如果元数据不存在（为了兼容旧数据），则退回原来的解析方式
            if not original_folder_name:
                parts = folder_name_full.rsplit('_', 1)
                original_folder_name = parts[0]

            batch_id = folder_name_full.rsplit('_', 1)[-1]
            

            folder_files = []
            # 遍历文件夹内部的PDF
            for sub_filepath in glob.glob(os.path.join(folder_path, '*.pdf')):
                sub_filename = os.path.basename(sub_filepath)
                folder_files.append({
                    "original_name": sub_filename,
                    "saved_name": f"{folder_name_full}/{sub_filename}"
                })

            if folder_files: # 只有文件夹不为空时才添加
                all_content.append({
                    'type': 'folder', # <--- 标记类型为 "文件夹"
                    'name': original_folder_name,
                    'batch_id': batch_id,
                    'files': folder_files,
                    'file_count': len(folder_files)
                })

    # 可以根据名称或类型排序，让文件夹总在前面
    all_content.sort(key=lambda x: (x['type'] == 'file', x.get('title', x.get('name'))))

    return all_content

def get_webpage_list():
    """获取已下载的网页文件列表"""
    download_dir = 'downloaded_webpages'
    if not os.path.exists(download_dir):
        return {'webpages': [], 'count': 0}
    
    # 加载元数据
    metadata_file = os.path.join(download_dir, 'metadata.json')
    metadata = load_metadata(metadata_file)
    
    webpage_files = []
    for filepath in glob.glob(os.path.join(download_dir, '*.html')):
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        
        # 从元数据中获取标题，如果没有则使用文件名
        title = metadata.get(filename, filename.replace('.html', ''))
        
        webpage_files.append({
            'filename': filename,
            'title': title,
            'size': file_size,
            'path': filepath
        })
    
    # 按标题排序
    webpage_files.sort(key=lambda x: x['title'])
    
    return {'webpages': webpage_files, 'count': len(webpage_files)}

def clear_all_content():
    """清除所有已下载的内容（论文和网页）"""
    total_deleted_count = 0
    
    # 清除论文文件
    papers_dir = 'downloaded_papers'
    if os.path.exists(papers_dir):
        # 获取所有PDF文件
        pdf_files = glob.glob(os.path.join(papers_dir, '*.pdf'))
        
        # 删除所有PDF文件
        for filepath in pdf_files:
            try:
                os.remove(filepath)
                total_deleted_count += 1
                print(f"已删除PDF文件: {os.path.basename(filepath)}")
            except Exception as e:
                print(f"删除PDF文件失败: {filepath}, 错误: {str(e)}")
        
        # 删除论文元数据文件
        metadata_file = os.path.join(papers_dir, 'metadata.json')
        if os.path.exists(metadata_file):
            try:
                os.remove(metadata_file)
                print("已删除论文元数据文件")
            except Exception as e:
                print(f"删除论文元数据文件失败: {str(e)}")
        
        # ===========================================================
        # ▼ 【在这里增加以下代码】▼
        # ===========================================================
        # 新增逻辑：查找并删除所有子文件夹（即上传的论文集）
        for item_name in os.listdir(papers_dir):
            item_path = os.path.join(papers_dir, item_name)
            if os.path.isdir(item_path):
                try:
                    # shutil.rmtree 会删除整个文件夹及其所有内容
                    shutil.rmtree(item_path)
                    print(f"已删除文件夹: {item_name}")
                    total_deleted_count += 1 # 将整个文件夹算作一个删除项
                except Exception as e:
                    print(f"删除文件夹 {item_path} 失败: {e}")
        # ===========================================================
        # ▲ 【增加的代码到此结束】▲
        # ===========================================================


        # 如果目录为空，删除目录
        try:
            remaining_files = os.listdir(papers_dir)
            if not remaining_files:
                os.rmdir(papers_dir)
                print("已删除论文目录")
        except Exception as e:
            print(f"删除论文目录失败: {str(e)}")
    
    # 清除网页文件
    webpages_dir = 'downloaded_webpages'
    if os.path.exists(webpages_dir):
        # 获取所有HTML文件
        html_files = glob.glob(os.path.join(webpages_dir, '*.html'))
        
        # 删除所有HTML文件
        for filepath in html_files:
            try:
                os.remove(filepath)
                total_deleted_count += 1
                print(f"已删除网页文件: {os.path.basename(filepath)}")
            except Exception as e:
                print(f"删除网页文件失败: {filepath}, 错误: {str(e)}")
        
        # 删除网页元数据文件
        metadata_file = os.path.join(webpages_dir, 'metadata.json')
        if os.path.exists(metadata_file):
            try:
                os.remove(metadata_file)
                print("已删除网页元数据文件")
            except Exception as e:
                print(f"删除网页元数据文件失败: {str(e)}")
        
        # 如果目录为空，删除目录
        try:
            remaining_files = os.listdir(webpages_dir)
            if not remaining_files:
                os.rmdir(webpages_dir)
                print("已删除网页目录")
        except Exception as e:
            print(f"删除网页目录失败: {str(e)}")
    
    return {
        'deleted_count': total_deleted_count,
        'message': f'成功清除了 {total_deleted_count} 个文件'
    }

def delete_single_content(filename, content_type):
    """删除单个内容文件"""
    if content_type == 'pdf':
        download_dir = 'downloaded_papers'
        file_extension = '.pdf'
    elif content_type == 'webpage':
        download_dir = 'downloaded_webpages'
        file_extension = '.html'
    else:
        raise ValueError(f"不支持的内容类型: {content_type}")
    
    # 检查目录是否存在
    if not os.path.exists(download_dir):
        return {
            'deleted': False,
            'message': '目录不存在'
        }
    
    # 构建文件路径
    filepath = os.path.join(download_dir, filename)
    
    # 检查文件是否存在
    if not os.path.exists(filepath):
        return {
            'deleted': False,
            'message': '文件不存在'
        }
    
    try:
        # 删除文件
        os.remove(filepath)
        
        # 更新元数据
        metadata_file = os.path.join(download_dir, 'metadata.json')
        metadata = load_metadata(metadata_file)
        
        if filename in metadata:
            del metadata[filename]
            save_metadata(metadata_file, metadata)
        
        return {
            'deleted': True,
            'message': f'成功删除 {filename}'
        }
        
    except Exception as e:
        return {
            'deleted': False,
            'message': f'删除失败: {str(e)}'
        }

def upload_pdf_file(file):
    """上传PDF文件"""
    from werkzeug.utils import secure_filename
    import time
    
    # 创建下载目录
    download_dir = 'downloaded_papers'
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    # 安全处理文件名
    original_filename = secure_filename(file.filename)
    
    # 生成唯一的文件名（基于时间戳和原文件名）
    timestamp = int(time.time())
    filename = f"upload_{timestamp}_{original_filename}"
    filepath = os.path.join(download_dir, filename)
    
    # 保存文件
    file.save(filepath)
    
    # 加载或创建元数据文件
    metadata_file = os.path.join(download_dir, 'metadata.json')
    metadata = load_metadata(metadata_file)
    
    # 保存标题到元数据（使用原文件名去除扩展名作为标题）
    title = original_filename.replace('.pdf', '')
    metadata[filename] = title
    
    # 保存元数据
    save_metadata(metadata_file, metadata)
    
    return {
        'filename': filename,
        'title': title,
        'message': f'成功上传PDF文件: {title}'
    }



# ========================= 辅助函数 =========================

def clean_web_content(content):
    """清理网页内容"""
    if not content:
        return ""
    
    # 移除图片和链接
    content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
    content = re.sub(r'<img[^>]*>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\[.*?\]\(https?://[^\)]+\)', '', content)
    content = re.sub(r'https?://[^\s]+', '', content)
    content = re.sub(r'<[^>]+>', '', content)
    
    # 移除无意义内容
    unwanted_patterns = [
        r'阅读量\d+[.\d]*[wk万千]?', r'收藏\d+[.\d]*[wk万千]?', r'点赞\d+[.\d]*[wk万千]?',
        r'已于\s*\d{4}-\d{2}-\d{2}.*?修改', r'\s*原创\s*', r'\s*转载\s*',
        r'©.*?版权.*?', r'版权声明.*?', r'相关推荐.*?', r'猜你喜欢.*?',
        r'广告.*?', r'登录.*?注册', r'订阅.*?关注', r'分享.*?评论'
    ]
    
    for pattern in unwanted_patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)
    
    # 清理空白字符
    content = re.sub(r'\n+', ' ', content)
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'^[^\w\u4e00-\u9fff]*', '', content)
    content = re.sub(r'[^\w\u4e00-\u9fff.!?]*$', '', content)
    
    return content.strip()

def extract_abstract(text):
    """提取论文摘要"""
    if not text:
        return "无摘要"
    
    # 清理文本
    text = re.sub(r'Download PDF.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Authors?:\s*\[.*?\].*?(?=\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Submitted on.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Comments:.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Subjects:.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[.*?\]\(https?://.*?\)', '', text)
    
    # 提取摘要
    abstract_patterns = [
        r'(?i)(?:^|\n)\s*abstract\s*:?\s*(.*?)(?=\n\s*(?:keywords?|introduction|1\.|references|related work|background|\n\s*[A-Z][a-z]+\s*:|\n\s*\d+\s+[A-Z])|$)',
        r'(?i)(?:^|\n)\s*#{1,6}\s*abstract\s*:?\s*(.*?)(?=\n\s*#{1,6}|\n\s*\d+\s+[A-Z]|$)',
        r'(?i)abstract\s*:?\s*(.*?)(?=\n\s*(?:keywords?|introduction|1\.|references)|$)',
    ]
    
    for pattern in abstract_patterns:
        match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
        if match:
            abstract = match.group(1).strip()
            abstract = clean_abstract(abstract)
            if is_valid_abstract(abstract):
                return abstract
    
    return "未找到摘要"

def clean_abstract(abstract):
    """清理摘要文本"""
    if not abstract:
        return ""
    
    abstract = re.sub(r'\n+', ' ', abstract)
    abstract = re.sub(r'\s+', ' ', abstract)
    abstract = abstract.strip()
    
    # 移除Abstract标记
    abstract_lower = abstract.lower()
    if abstract_lower.startswith('abstract:'):
        abstract = abstract[9:].strip()
    elif abstract_lower.startswith('abstract '):
        abstract = abstract[9:].strip()
    elif abstract_lower.startswith('abstract'):
        abstract = abstract[8:].strip()
    
    # 清理无关内容
    unwanted_patterns = [
        r'Download PDF.*?(?=\s|$)', r'Authors?:\s*.*?(?=\s|$)',
        r'Submitted on.*?(?=\s|$)', r'Comments:.*?(?=\s|$)',
        r'Subjects:.*?(?=\s|$)', r'\[.*?\]\(https?://.*?\)',
        r'https?://[^\s]+', r'arXiv:\d+\.\d+', r'^\s*\d+\s*$'
    ]
    
    for pattern in unwanted_patterns:
        abstract = re.sub(pattern, '', abstract, flags=re.IGNORECASE)
    
    abstract = re.sub(r'^[^\w\s]*', '', abstract)
    abstract = re.sub(r'[^\w\s.!?]*$', '', abstract)
    
    return abstract.strip()

def is_valid_abstract(abstract):
    """检查摘要有效性"""
    if not abstract or len(abstract) < 50:
        return False
    
    invalid_indicators = [
        r'(?i)download\s+pdf', r'(?i)authors?:\s*\[', r'(?i)submitted\s+on',
        r'(?i)comments:', r'(?i)subjects:', r'(?i)^\s*\d+\s*$',
        r'(?i)^\s*table\s+of\s+contents', r'(?i)^\s*references\s*$'
    ]
    
    for pattern in invalid_indicators:
        if re.search(pattern, abstract):
            return False
    
    sentences = re.split(r'[.!?]+', abstract)
    valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    return len(valid_sentences) >= 2

def is_valid_arxiv_url(url):
    """检查是否为有效的arxiv URL"""
    if not url:
        return False
    return re.match(r'https://arxiv\.org/abs/\d+\.\d+(v\d+)?', url) is not None

def convert_arxiv_url_to_pdf(abs_url):
    """将arxiv的abs URL转换为pdf URL"""
    if not abs_url:
        return None
    
    # 将 https://arxiv.org/abs/2404.15583v1 转换为 https://arxiv.org/pdf/2404.15583v1.pdf
    if 'arxiv.org/abs/' in abs_url:
        pdf_url = abs_url.replace('/abs/', '/pdf/') + '.pdf'
        return pdf_url
    
    return None

def load_metadata(metadata_file):
    """加载元数据文件"""
    if os.path.exists(metadata_file):
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取元数据文件失败: {str(e)}")
    return {}

def save_metadata(metadata_file, metadata):
    """保存元数据文件"""
    try:
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存元数据文件失败: {str(e)}")

def download_pdf_with_title(pdf_url, download_dir, title, metadata):
    """下载PDF文件并保存标题信息"""
    try:
        # 从URL中提取论文ID作为文件名
        paper_id = pdf_url.split('/')[-1].replace('.pdf', '')
        filename = f"{paper_id}.pdf"
        filepath = os.path.join(download_dir, filename)
        
        # 如果文件已存在，跳过下载但更新元数据
        if os.path.exists(filepath):
            print(f"文件已存在，跳过下载: {filename}")
            metadata[filename] = title
            return True, filename
        
        # 下载PDF
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(pdf_url, headers=headers, timeout=3000)
        response.raise_for_status()
        
        # 检查响应是否为PDF
        content_type = response.headers.get('content-type', '')
        if 'pdf' not in content_type.lower():
            print(f"响应不是PDF文件: {content_type}")
            return False, None
        
        # 保存文件
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        # 保存标题到元数据
        metadata[filename] = title
        
        print(f"成功下载: {filename}")
        return True, filename
        
    except requests.exceptions.RequestException as e:
        print(f"下载失败: {pdf_url}, 错误: {str(e)}")
        return False, None
    except Exception as e:
        print(f"保存文件失败: {str(e)}")
        return False, None

def download_webpage(url, download_dir, title, metadata):
    """下载网页内容并保存为HTML文件"""
    try:
        # 生成基于URL的唯一文件名
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:8]
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:50]
        filename = f"{safe_title}_{url_hash}.html"
        filepath = os.path.join(download_dir, filename)
        
        # 如果文件已存在，跳过下载但更新元数据
        if os.path.exists(filepath):
            print(f"文件已存在，跳过下载: {filename}")
            metadata[filename] = title
            return True, filename
        
        # 下载网页
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=3000)
        response.raise_for_status()
        
        # 检查响应是否为HTML
        content_type = response.headers.get('content-type', '')
        if 'html' not in content_type.lower():
            print(f"响应不是HTML文件: {content_type}")
            return False, None
        
        # 解析HTML并清理
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 移除脚本和样式标签
        for script in soup(["script", "style"]):
            script.decompose()
        
        # 添加基础样式使页面更易读
        if soup.head:
            style_tag = soup.new_tag("style")
            style_tag.string = """
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    line-height: 1.6; 
                    max-width: 800px; 
                    margin: 0 auto; 
                    padding: 20px;
                    background: #fff;
                    color: #333;
                }
                img { max-width: 100%; height: auto; }
                pre { background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; }
                code { background: #f5f5f5; padding: 2px 4px; border-radius: 2px; }
                blockquote { border-left: 3px solid #ddd; margin-left: 0; padding-left: 20px; color: #666; }
            """
            soup.head.append(style_tag)
        
        # 保存HTML文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        
        # 保存标题到元数据
        metadata[filename] = title
        
        print(f"成功下载网页: {filename}")
        return True, filename
        
    except requests.exceptions.RequestException as e:
        print(f"下载网页失败: {url}, 错误: {str(e)}")
        return False, None
    except Exception as e:
        print(f"保存网页失败: {str(e)}")
        return False, None 

# ========================= 论文处理流程相关函数 =========================

import subprocess
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
import time 
# 处理状态跟踪
processing_jobs = {}
processing_results = {}
processing_lock = threading.Lock()

# =================================================================
# ========================= 论文处理核心函数 =========================
# =================================================================

# 单篇论文预处理
def start_paper_processing(pdf_path, pdf_filename, video_duration='medium', voice_type='female', output_format='video', background_choice='default', auto_continue=False):
    """
    启动论文处理流程
    修改函数签名，增加 unique_base_name 参数,增加 background_choice 参数
    使用 FormData 对象来同时提交普通表单数据和文件
    """
    
    # 生成唯一的处理ID
    process_id = str(uuid.uuid4())
    # 获取PDF文件名（不含扩展名）作为输出目录基础名
    base_name = os.path.splitext(pdf_filename)[0]
    

    # 处理自定义音色文件和文本
    custom_voice_path = None
    custom_voice_text = request.form.get('voiceText', '') # 从表单数据中获取文本
    voice_file = request.files.get('voiceFile') # 从上传的文件中获取音色文件

    if voice_type == 'custom' and voice_file:
        # 如果是自定义音色，保存上传的文件
        temp_dir = f'Paper2Video/{base_name}_output/temp'
        os.makedirs(temp_dir, exist_ok=True)

        safe_filename = secure_filename(voice_file.filename)
        custom_voice_path = os.path.join(temp_dir, safe_filename)
        voice_file.save(custom_voice_path)
        print(f"✅ 自定义音色文件已保存至: {custom_voice_path}")
    # 【调试代码】
    # print(f"--- [SERVICE DEBUG] start_paper_processing ---")
    # print(f"  接收到的 voice_type 参数: [{voice_type}]") # 用中括号包起来，防止空格等不可见字符
    # 处理自定义背景文件
    custom_background_path = None
    background_file = request.files.get('backgroundFile') # 从上传的文件中获取背景文件

    if background_choice == 'custom' and background_file:
        # 确保 temp 目录存在（如果前面音色部分已创建，这里会跳过）
        temp_dir = f'Paper2Video/{base_name}_output/temp'
        os.makedirs(temp_dir, exist_ok=True)
        # 安全地保存背景文件
        safe_bg_filename = secure_filename(background_file.filename)
        custom_background_path = os.path.join(temp_dir, safe_bg_filename)
        background_file.save(custom_background_path)
        print(f"✅ 自定义背景文件已保存至: {custom_background_path}")

    # 创建处理记录
    job_info = {
        'process_id': process_id,
        'pdf_path': pdf_path,
        'pdf_filename': pdf_filename,
        'base_name': base_name,
        'video_duration': video_duration,
        'voice_type': voice_type,
        'output_format': output_format,  # <--- 【新增】存储输出格式

        'custom_voice_path': custom_voice_path, # 存储保存后的路径
        'custom_voice_text': custom_voice_text, # 存储文本
        'background_choice': background_choice, # 存储背景选择
        'custom_background_path': custom_background_path, # 存储自定义背景路径

        'auto_continue': auto_continue,

        'status': 'starting',
        'progress': 0,
        'start_time': datetime.now().isoformat(),
        'last_update': datetime.now().isoformat(),
        'current_step': 'Step 0: 准备开始',
        'log_messages': [],
        'output_dir': None,
        'final_video_path': None,
        'final_output_path': None, # 存储最终输出路径（视频或压缩包）
        'error': None,
        'stage': 'initial'  # initial, waiting_for_edit, continuing, completed
    }
    
    print(f"  即将存入 job_info 的 voice_type: [{job_info['voice_type']}]")
    print(f"-------------------------------------------")

    with processing_lock:
        processing_jobs[process_id] = job_info
    
    # 启动异步处理线程 - 只执行到Step 3
    processing_thread = threading.Thread(
        target=run_initial_processing, 
        args=(process_id, pdf_path, base_name)
    )
    processing_thread.daemon = True
    processing_thread.start()
    
    return {
        'process_id': process_id,
        'message': f'开始处理论文: {pdf_filename}',
        'status': 'starting'
    }

def run_initial_processing(process_id, pdf_path, base_name):
    """
    运行初始处理流程。
    根据用户选择的输出格式，调用不同的预处理脚本 (all_pipeline_video.py 或 all_pipeline_markdown.py)。
    """
    # 内部辅助函数，保持不变
    def update_job_status(status=None, progress=None, step=None, log_msg=None, error=None, output_dir=None, stage=None):
        with processing_lock:
            if process_id in processing_jobs:
                job = processing_jobs[process_id]
                if status: job['status'] = status
                if progress is not None: job['progress'] = progress
                if step: job['current_step'] = step
                if log_msg: job['log_messages'].append({'time': datetime.now().isoformat(), 'message': log_msg})
                if error: job['error'] = error
                if output_dir: job['output_dir'] = output_dir
                if stage: job['stage'] = stage
                job['last_update'] = datetime.now().isoformat()
    
    try:
        # 1. 根据用户选择，确定要执行的脚本和初始步骤信息
        with processing_lock:
            job = processing_jobs[process_id]
            chosen_format = job.get('output_format', 'video')

        script_to_run = ''
        initial_step_message = ''
        
        if chosen_format == 'video':
            script_to_run = 'all_pipeline_video.py'
            initial_step_message = '🚀 开始执行视频预处理流程 (调用 all_pipeline_video.py)'
            update_job_status(progress=10, step='💻 Step 1-3: 视频内容生成')
        elif chosen_format == 'markdown':
            script_to_run = 'all_pipeline_markdown.py'
            initial_step_message = '🚀 开始执行Markdown预处理流程 (调用 all_pipeline_markdown.py)'
            update_job_status(progress=10, step='💻 Step 1: 论文章节切分')
        elif chosen_format == 'ppt':
            # 为PPT预留的接口，目前是报告"未实现"并退出
            # update_job_status(
            #     status='failed',
            #     progress=10,
            #     step='功能未实现',
            #     error='PPT生成功能暂未开放，敬请期待。',
            #     stage='completed'
            # )
            # return # 直接退出函数
            script_to_run = 'all_pipeline_ppt.py'
            initial_step_message = '🚀 开始执行PPT预处理流程 (调用 all_pipeline_ppt.py)'
            update_job_status(progress=10, step='💻 Step 1-3: PPT内容生成')
        else:
            # 处理未知格式
            raise ValueError(f"不支持的输出格式: {chosen_format}")

        # 2. 准备并执行动态构建的命令
        update_job_status(status='running', progress=5, step='📋 准备执行初始流程', 
                         log_msg=f'🔧 准备处理PDF文件: {pdf_path}')
        
        # 【重要】动态构建命令
        cmd = ['python3', script_to_run, pdf_path, '--output-dir', f'{base_name}_output']
        
        update_job_status(log_msg=initial_step_message)
        update_job_status(log_msg=f'⚙️ 将要执行命令: {" ".join(cmd)}') # 增加日志方便调试
        
        # 执行处理脚本
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            universal_newlines=True,
            bufsize=1, # 使用行缓冲
            encoding='utf-8',
            env=env
        )
        
        # 实时读取输出
        current_progress = 10
        if process.stdout:
            for line in process.stdout:
                line = line.strip()
                if line:
                    update_job_status(log_msg=line)
                    # 简化的进度更新
                    if 'Step' in line and current_progress < 65:
                         current_progress += 5
                         update_job_status(progress=min(current_progress, 65))
        
        process.wait()
        
        # 3. 预处理脚本执行完毕后，根据格式选择下一步操作
        if process.returncode == 0:
            update_job_status(progress=70, log_msg=f'✅ {script_to_run} 执行成功!')
            
            # 后续任务的二次分流
            if chosen_format == 'markdown':
                # 如果是Markdown，则调用文档生成和打包函数
                update_job_status(status='running', step='📝 Step 2: 生成并打包Markdown文档')
                # 这个 run_markdown_generation 函数是我们之前已经写好的
                run_markdown_generation(process_id, base_name)

            elif chosen_format == 'video':
                # 如果是视频，则继续执行视频独有的后续步骤
                update_job_status(progress=70, step='📁 Step 3.5: 复制cover场景文件',
                                log_msg='🔄 开始复制cover文件到Code目录...')
                
                output_dir = f"Paper2Video/{base_name}_output"
                code_dir = f"{output_dir}/final_results/Code"
                try:
                    if os.path.exists("cover") and os.path.exists(code_dir):
                        import shutil
                        for py_file in glob.glob("cover/*.py"):
                            filename = os.path.basename(py_file)
                            shutil.copy2(py_file, os.path.join(code_dir, filename))
                            update_job_status(log_msg=f'✅ 复制: {filename}')
                        
                        logo_source = "/home/EduAgent/static/template_images/EDUPAL_logo.png"
                        if os.path.exists(logo_source):
                            shutil.copy2(logo_source, os.path.join(code_dir, "EDUPAL_logo.png"))
                            update_job_status(log_msg=f'✅ 复制logo文件: EDUPAL_logo.png')
                        else:
                            update_job_status(log_msg='⚠️ 未找到logo文件，跳过复制')
                        
                    else:
                        update_job_status(log_msg='⚠️ cover目录或Code目录不存在，跳过复制步骤')
                    
                except Exception as e:
                    update_job_status(log_msg=f'⚠️ 复制cover文件时出错: {str(e)}，但不影响后续步骤')
                
                update_job_status(progress=75, step='🎬 Step 3.6: 生成封面内容',
                                log_msg='🔄 开始生成封面内容...',
                                output_dir=output_dir)
                
                try:
                    cover_result = generate_cover_content(process_id)
                    if cover_result.get('status') == 'success':
                        update_job_status(log_msg=f'✅ 封面内容生成成功: {cover_result.get("title", "无标题")}')
                    else:
                        update_job_status(log_msg=f'⚠️ 封面生成问题: {cover_result.get("note", cover_result.get("error", "未知错误"))}')
                except Exception as e:
                    update_job_status(log_msg=f'⚠️ 封面生成失败: {str(e)}，但不影响后续步骤')
                
                # 插入自动应用背景图的逻辑
                try:
                    with processing_lock:
                        job = processing_jobs[process_id]
                        # 从 job_info 中获取之前存储的背景设置
                        choice = job.get('background_choice', 'default')
                        custom_path = job.get('custom_background_path')

                    # code_dir 变量在之前的代码中已经定义
                    background_to_apply = None

                    # 检查是否需要应用背景
                    if choice and choice != 'default':
                        update_job_status(log_msg=f'🎨 检测到用户选择背景: {choice}，开始应用...')
                        
                        # 情况一：用户上传了自定义背景
                        if choice == 'custom' and custom_path and os.path.exists(custom_path):
                            filename = os.path.basename(custom_path)
                            destination_path = os.path.join(code_dir, filename)
                            
                            update_job_status(log_msg=f'    -> 正在复制自定义背景: {filename} 到Code目录')
                            shutil.copy2(custom_path, destination_path)
                            background_to_apply = filename

                        # 情况二：用户选择了预设背景 (例如 'SJTU.png')
                        elif choice != 'custom':
                            # 预设背景图存放在 static/backgrounds/
                            preset_source_path = os.path.join('static', 'backgrounds', choice)
                            if os.path.exists(preset_source_path):
                                destination_path = os.path.join(code_dir, choice)
                                update_job_status(log_msg=f'    -> 正在复制预设背景: {choice} 到Code目录')
                                shutil.copy2(preset_source_path, destination_path)
                                background_to_apply = choice
                            else:
                                update_job_status(log_msg=f'    ⚠️ 预设背景文件不存在: {preset_source_path}，跳过应用')
                        
                        # 如果成功复制了背景文件，则调用脚本应用它
                        if background_to_apply:
                            update_job_status(log_msg=f'    -> 调用脚本以应用背景: {background_to_apply}')
                            # apply_background_to_code 是之前写好的函数，可以直接调用
                            try:
                                # 注意：apply_background_to_code 函数需要 process_id 和文件名
                                apply_result = apply_background_to_code(process_id, background_to_apply)
                                update_job_status(log_msg=f'    ✅ 背景应用完成: {apply_result.get("message", "无返回信息")}')
                            except Exception as apply_error:
                                update_job_status(log_msg=f'    ❌ 应用背景脚本时出错: {str(apply_error)}')
                        else:
                             update_job_status(log_msg='    -> 未能定位到有效背景文件，跳过应用。')

                    else:
                        update_job_status(log_msg='🎨 用户未指定特殊背景，使用默认背景。')

                except Exception as e:
                    update_job_status(log_msg=f'⚠️ 应用背景图时发生严重错误: {str(e)}，处理将继续但背景可能不会生效。')

                update_job_status(progress=80, step='🎥 Step 4.5: 开始预览视频渲染',
                                log_msg='🎉 初始处理完成！开始生成预览视频...',
                                output_dir=output_dir,
                                status='rendering_preview',
                                stage='rendering_preview')
                
                render_preview_video(process_id, base_name)


                # 【新增逻辑】根据 job_info 中的设置，决定是否自动执行后续步骤
                try:
                    with processing_lock:
                        job = processing_jobs[process_id]
                        auto_continue = job.get('auto_continue', False) # 从任务状态中读取

                    if auto_continue:
                        update_job_status(log_msg='⚙️ 自动模式已启用，无缝衔接后续处理...')
                        # 为了兼容 continue_paper_processing，需要手动设置它期望的 stage
                        with processing_lock:
                            processing_jobs[process_id]['stage'] = 'waiting_for_edit'
                        
                        continue_paper_processing(process_id)
                except Exception as e:
                    update_job_status(
                        status='failed', 
                        step='❌ 自动衔接失败', 
                        error=f'调用 continue_paper_processing 时出错: {str(e)}'
                    )


            elif chosen_format == 'ppt':
                update_job_status(progress=70, step='📁 Step 3.5: 复制cover场景文件',
                                log_msg='🔄 开始复制cover文件到Code目录...')
                
                output_dir = f"Paper2Video/{base_name}_output"
                code_dir = f"{output_dir}/final_results/Code"
                try:
                    if os.path.exists("pptcover") and os.path.exists(code_dir):
                        import shutil
                        for py_file in glob.glob("pptcover/*.py"):
                            filename = os.path.basename(py_file)
                            shutil.copy2(py_file, os.path.join(code_dir, filename))
                            update_job_status(log_msg=f'✅ 复制: {filename}')
                        
                        logo_source = "/home/EduAgent/pptcover/logo_test.png"
                        if os.path.exists(logo_source):
                            shutil.copy2(logo_source, os.path.join(code_dir, "logo_test.png"))
                            update_job_status(log_msg=f'✅ 复制logo文件: logo_test.png')
                        else:
                            update_job_status(log_msg='⚠️ 未找到logo文件，跳过复制')
                        
                    else:
                        update_job_status(log_msg='⚠️ cover目录或Code目录不存在，跳过复制步骤')
                    
                except Exception as e:
                    update_job_status(log_msg=f'⚠️ 复制cover文件时出错: {str(e)}，但不影响后续步骤')
                
                update_job_status(progress=75, step='🎬 Step 3.6: 生成封面内容',
                                log_msg='🔄 开始生成封面内容...',
                                output_dir=output_dir)
                
                try:
                    cover_result = generate_pptcover_content(process_id)
                    subprocess.run(['echo', '开始开始生成PPT封面内容...'], check=True)
                    #subprocess.run(['echo', cover_result])
                    if cover_result.get('status') == 'success':
                        update_job_status(log_msg=f'✅ 封面内容生成成功: {cover_result.get("title", "无标题")}')
                        subprocess.run(['echo', '成功生成封面内容'], check=True)
                    else:
                        update_job_status(log_msg=f'⚠️ 封面生成问题: {cover_result.get("note", cover_result.get("error", "未知错误"))}')
                except Exception as e:
                    update_job_status(log_msg=f'⚠️ 封面生成失败: {str(e)}，但不影响后续步骤')
                    subprocess.run(['echo', '封面生成失败失败失败'], check=True)
                

                update_job_status(progress=80, step='🎥 Step 4.5: 开始预览PPT',
                                log_msg='🎉 初始处理完成！开始生成预览PPT...',
                                output_dir=output_dir,
                                status='rendering_preview',
                                stage='rendering_preview')
                
                render_preview_ppt(process_id, base_name)
                
                # 【新增逻辑】根据 job_info 中的设置，决定是否自动执行后续步骤
                try:
                    with processing_lock:
                        job = processing_jobs[process_id]
                        auto_continue = job.get('auto_continue', False) # 从任务状态中读取

                    if auto_continue:
                        update_job_status(log_msg='⚙️ 自动模式已启用，无缝衔接后续处理...')
                        # 为了兼容 continue_paper_processing，需要手动设置它期望的 stage
                        with processing_lock:
                            processing_jobs[process_id]['stage'] = 'waiting_for_edit'
                        
                        continue_paper_processing(process_id)
                except Exception as e:
                    update_job_status(
                        status='failed', 
                        step='❌ 自动衔接失败', 
                        error=f'调用 continue_paper_processing 时出错: {str(e)}'
                    )
        else:
            # 预处理失败的逻辑
            update_job_status(
                status='failed', 
                step='❌ 预处理失败', 
                error=f'脚本 {script_to_run} 执行失败，退出码: {process.returncode}',
                log_msg=f'预处理过程中出现错误，请检查日志。'
            )
    
    except Exception as e:
        # 异常处理逻辑
        update_job_status(
            status='failed', 
            step='❌ 处理异常', 
            error=str(e),
            log_msg=f'初始处理过程中发生异常: {str(e)}'
        )

# 论文集预处理
def start_folder_processing(folder_path, folder_name, unique_base_name, video_duration='medium', voice_type='female', output_format='video', background_choice='default', auto_continue=False):
    """
    启动整个文件夹的处理流程。
    这个函数接收的是一个文件夹路径。
    修改函数签名，增加 unique_base_name 参数,增加 background_choice 参数
    使用 FormData 对象来同时提交普通表单数据和文件
    包含与单篇处理完全一致的自定义音色处理逻辑
    """
    # 与单篇处理，添加完全相同的入口日志，确认函数被调用且参数正确
    print(f"--- [SERVICE DEBUG] start_FOLDER_processing ---")
    print(f"  接收到的 folder_path 参数: [{folder_path}]")
    print(f"  接收到的 folder_name 参数: [{folder_name}]")
    print(f"  接收到的 voice_type 参数: [{voice_type}]")

    process_id = str(uuid.uuid4()) # 为整个批次创建一个总的 process_id
    base_name = unique_base_name # 【核心】直接使用从路由层传递过来的唯一基础名
    # 完全复用单篇处理中的自定义音色文件和文本处理逻辑
    custom_voice_path = None 
    custom_voice_text = request.form.get('voiceText', '')
    voice_file = request.files.get('voiceFile')
    output_dir = f"Paper2Video/{base_name}_output"   # 定义输出目录，用于存放临时音色文件

    if voice_type == 'custom' and voice_file:
        temp_dir = f'{output_dir}/temp' # 将临时文件存放在该批次任务的输出目录下
        os.makedirs(temp_dir, exist_ok=True)
        safe_filename = secure_filename(voice_file.filename)
        custom_voice_path = os.path.join(temp_dir, safe_filename)
        voice_file.save(custom_voice_path)
        print(f"✅ 文件夹处理任务 {process_id}: 自定义音色文件已保存至: {custom_voice_path}")

    # 处理自定义背景文件
    custom_background_path = None
    background_file = request.files.get('backgroundFile')

    if background_choice == 'custom' and background_file:
        temp_dir = f'{output_dir}/temp'  # output_dir 在这之前已经定义
        os.makedirs(temp_dir, exist_ok=True)
        safe_bg_filename = secure_filename(background_file.filename)
        custom_background_path = os.path.join(temp_dir, safe_bg_filename)
        background_file.save(custom_background_path)
        print(f"✅ 文件夹处理任务: 自定义背景文件已保存至: {custom_background_path}")

    # 创建处理记录，注意这里记录的是 folder_path
    # 创建处理记录，现在包含了所有必要的字段
    job_info = {
        'process_id': process_id,
        'folder_path': folder_path,       # 区别：记录文件夹路径
        'folder_name': folder_name,       # 区别：记录文件夹名
        'base_name': base_name,
        'video_duration': video_duration,
        'voice_type': voice_type,
        'output_format': output_format,

        'custom_voice_path': custom_voice_path, 
        'custom_voice_text': custom_voice_text, 
        'background_choice': background_choice,
        'custom_background_path': custom_background_path,

        'auto_continue': auto_continue,

        'status': 'starting',
        'progress': 0,
        'start_time': datetime.now().isoformat(),
        'last_update': datetime.now().isoformat(),
        'current_step': 'Step 0: 准备开始',
        'log_messages': [],
        'output_dir': None,
        'final_video_path': None,
        'final_output_path': None,
        'error': None,
        'stage': 'initial'
    }

    # --- [调试点2] ---
    # print(f"  即将为文件夹处理创建 job_info，voice_type 为: [{job_info['voice_type']}]")
    # print(f"-------------------------------------------")


    with processing_lock:
        processing_jobs[process_id] = job_info

    # 启动异步处理线程，调用一个新的运行函数
    processing_thread = threading.Thread(
        target=run_folder_processing, # <-- 调用为文件夹设计的运行函数
        args=(process_id, folder_path, base_name)
    )
    processing_thread.daemon = True
    processing_thread.start()

    return {
        'process_id': process_id,
        'message': f'开始处理文件夹: {folder_name}',
        'status': 'starting'
    }

def run_folder_processing(process_id, folder_path, base_name):
    """
    运行基于文件夹的初始处理流程。
    逻辑与 run_initial_processing 非常相似，但传递给脚本的是文件夹路径。
    """
    # 内部辅助函数，保持不变
    def update_job_status(status=None, progress=None, step=None, log_msg=None, error=None, output_dir=None, stage=None):
        with processing_lock:
            if process_id in processing_jobs:
                job = processing_jobs[process_id]
                if status: job['status'] = status
                if progress is not None: job['progress'] = progress
                if step: job['current_step'] = step
                if log_msg: job['log_messages'].append({'time': datetime.now().isoformat(), 'message': log_msg})
                if error: job['error'] = error
                if output_dir: job['output_dir'] = output_dir
                if stage: job['stage'] = stage
                job['last_update'] = datetime.now().isoformat()
    # --- [调试点 3] ---
    # 判断线程是否成功启动
    # print(f"\n--- [BACKGROUND THREAD] 文件夹处理线程 {process_id} 已成功启动！ ---\n")
    update_job_status(status='running', progress=5, step='准备环境') # <--- 初始状态更新
    try:
        with processing_lock:
            job = processing_jobs[process_id]
            chosen_format = job.get('output_format', 'video')

        # 选择要执行的脚本 (这部分逻辑和单文件处理完全一样)
        script_to_run = ''
        if chosen_format == 'video':
            script_to_run = 'all_pipeline_video.py'
        elif chosen_format == 'markdown':
            script_to_run = 'all_pipeline_markdown.py'
        elif chosen_format == 'ppt':
            script_to_run = 'all_pipeline_ppt.py'
        else:
            raise ValueError(f"不支持的输出格式: {chosen_format}")

        script_path = os.path.abspath(script_to_run)
        output_dir_path = os.path.abspath(f"Paper2Video/{base_name}_output")
        
        # 【重要】在启动前，就将最终的输出目录保存到job_info中
        update_job_status(output_dir=output_dir_path)
        
        cmd = ['python3', script_path, folder_path, '--output-dir', output_dir_path]

        update_job_status(log_msg=f'🚀 开始执行批量处理流程 (调用 {script_to_run})')
        update_job_status(log_msg=f'⚙️ 将要执行命令: {" ".join(cmd)}')

        # 执行处理脚本 (这部分代码保持不变)
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            universal_newlines=True,
            bufsize=1, # 使用行缓冲
            encoding='utf-8',
            env=env
        )
        
        # 实时读取输出 (这部分代码保持不变)
        current_progress = 10
        update_job_status(progress=current_progress, step='Step 1: 论文解析')

        if process.stdout:
            for line in process.stdout:
                line = line.strip()
                if line:
                    # all_pipeline_video.py 内部在干什么
                    # print(f"  [SUBPROCESS OUTPUT] > {line}") 
                    update_job_status(log_msg=line)
                    # 简化的进度更新
                    if 'Step' in line and current_progress < 65:
                         current_progress += 5
                         update_job_status(progress=min(current_progress, 65))
        
        process.wait()
        # 判断子进程是成功还是失败
        # print(f"\n--- [BACKGROUND THREAD] 子进程处理完毕，返回码: {process.returncode} ---\n")
        # 3. 预处理脚本执行完毕后，根据格式选择下一步操作
        if process.returncode == 0:
            update_job_status(log_msg=f'✅ {script_to_run} 对文件夹处理成功!')
            # 后续任务的二次分流
            if chosen_format == 'markdown':
                # 如果是Markdown，则调用文档生成和打包函数
                update_job_status(status='running', step='📝 Step 2: 生成并打包Markdown文档')
                # 这个 run_markdown_generation 函数是我们之前已经写好的
                run_folder_markdown_generation(process_id, base_name)

            elif chosen_format == 'video':
                # 如果是视频，则继续执行视频独有的后续步骤
                update_job_status(progress=70, step='📁 Step 3.5: 复制cover场景文件',
                                log_msg='🔄 开始复制cover文件到Code目录...')
                
                output_dir = f"Paper2Video/{base_name}_output"
                code_dir = f"{output_dir}/final_results/Code"
                try:
                    if os.path.exists("cover") and os.path.exists(code_dir):
                        import shutil
                        for py_file in glob.glob("cover/*.py"):
                            filename = os.path.basename(py_file)
                            shutil.copy2(py_file, os.path.join(code_dir, filename))
                            update_job_status(log_msg=f'✅ 复制: {filename}')
                        
                        logo_source = "/home/EduAgent/static/template_images/EDUPAL_logo.png"
                        if os.path.exists(logo_source):
                            shutil.copy2(logo_source, os.path.join(code_dir, "EDUPAL_logo.png"))
                            update_job_status(log_msg=f'✅ 复制logo文件: EDUPAL_logo.png')
                        else:
                            update_job_status(log_msg='⚠️ 未找到logo文件，跳过复制')
                        
                    else:
                        update_job_status(log_msg='⚠️ cover目录或Code目录不存在，跳过复制步骤')
                    
                except Exception as e:
                    update_job_status(log_msg=f'⚠️ 复制cover文件时出错: {str(e)}，但不影响后续步骤')
                
                update_job_status(progress=75, step='🎬 Step 3.6: 生成封面内容',
                                log_msg='🔄 开始生成封面内容...',
                                output_dir=output_dir)
                
                try:
                    cover_result = generate_cover_content(process_id)
                    if cover_result.get('status') == 'success':
                        update_job_status(log_msg=f'✅ 封面内容生成成功: {cover_result.get("title", "无标题")}')
                    else:
                        update_job_status(log_msg=f'⚠️ 封面生成问题: {cover_result.get("note", cover_result.get("error", "未知错误"))}')
                except Exception as e:
                    update_job_status(log_msg=f'⚠️ 封面生成失败: {str(e)}，但不影响后续步骤')
                
                # 自动应用背景图
                try:
                    with processing_lock:
                        job = processing_jobs[process_id]
                        # 从 job_info 中获取之前存储的背景设置
                        choice = job.get('background_choice', 'default')
                        custom_path = job.get('custom_background_path')

                    # code_dir 变量在之前的代码中已经定义
                    background_to_apply = None

                    # 检查是否需要应用背景
                    if choice and choice != 'default':
                        update_job_status(log_msg=f'🎨 检测到用户选择背景: {choice}，开始应用...')
                        
                        # 情况一：用户上传了自定义背景
                        if choice == 'custom' and custom_path and os.path.exists(custom_path):
                            filename = os.path.basename(custom_path)
                            destination_path = os.path.join(code_dir, filename)
                            
                            update_job_status(log_msg=f'    -> 正在复制自定义背景: {filename} 到Code目录')
                            shutil.copy2(custom_path, destination_path)
                            background_to_apply = filename

                        # 情况二：用户选择了预设背景 (例如 'SJTU.png')
                        elif choice != 'custom':
                            # 预设背景图存放在 static/backgrounds/
                            preset_source_path = os.path.join('static', 'backgrounds', choice)
                            if os.path.exists(preset_source_path):
                                destination_path = os.path.join(code_dir, choice)
                                update_job_status(log_msg=f'    -> 正在复制预设背景: {choice} 到Code目录')
                                shutil.copy2(preset_source_path, destination_path)
                                background_to_apply = choice
                            else:
                                update_job_status(log_msg=f'    ⚠️ 预设背景文件不存在: {preset_source_path}，跳过应用')
                        
                        # 如果成功复制了背景文件，则调用脚本应用它
                        if background_to_apply:
                            update_job_status(log_msg=f'    -> 调用脚本以应用背景: {background_to_apply}')
                            # apply_background_to_code 是之前写好函数，可以直接调用
                            try:
                                # 注意：apply_background_to_code 函数需要 process_id 和文件名
                                apply_result = apply_background_to_code(process_id, background_to_apply)
                                update_job_status(log_msg=f'    ✅ 背景应用完成: {apply_result.get("message", "无返回信息")}')
                            except Exception as apply_error:
                                update_job_status(log_msg=f'    ❌ 应用背景脚本时出错: {str(apply_error)}')
                        else:
                             update_job_status(log_msg='    -> 未能定位到有效背景文件，跳过应用。')

                    else:
                        update_job_status(log_msg='🎨 用户未指定特殊背景，使用默认背景。')

                except Exception as e:
                    update_job_status(log_msg=f'⚠️ 应用背景图时发生严重错误: {str(e)}，处理将继续但背景可能不会生效。')

                update_job_status(progress=80, step='🎥 Step 4.5: 开始预览视频渲染',
                                log_msg='🎉 初始处理完成！开始生成预览视频...',
                                output_dir=output_dir,
                                status='rendering_preview',
                                stage='rendering_preview')
                
                render_preview_video(process_id, base_name)

                # 【新增逻辑】根据 job_info 中的设置，决定是否自动执行后续步骤
                try:
                    with processing_lock:
                        job = processing_jobs[process_id]
                        auto_continue = job.get('auto_continue', False) # 从任务状态中读取

                    if auto_continue:
                        update_job_status(log_msg='⚙️ 自动模式已启用，无缝衔接后续处理...')
                        # 为了兼容 continue_paper_processing，需要手动设置它期望的 stage
                        with processing_lock:
                            processing_jobs[process_id]['stage'] = 'waiting_for_edit'
                        
                        continue_paper_processing(process_id)
                except Exception as e:
                    update_job_status(
                        status='failed', 
                        step='❌ 自动衔接失败', 
                        error=f'调用 continue_paper_processing 时出错: {str(e)}'
                    )

            elif chosen_format == 'ppt':
                # 如果是视频，则继续执行视频独有的后续步骤
                update_job_status(progress=70, step='📁 Step 3.5: 复制cover场景文件',
                                log_msg='🔄 开始复制cover文件到Code目录...')
                
                output_dir = f"Paper2Video/{base_name}_output"
                code_dir = f"{output_dir}/final_results/Code"
                try:
                    if os.path.exists("pptcover") and os.path.exists(code_dir):
                        import shutil
                        for py_file in glob.glob("pptcover/*.py"):
                            filename = os.path.basename(py_file)
                            shutil.copy2(py_file, os.path.join(code_dir, filename))
                            update_job_status(log_msg=f'✅ 复制: {filename}')
                        
                        logo_source = "/home/EduAgent/logo_test.png"
                        if os.path.exists(logo_source):
                            shutil.copy2(logo_source, os.path.join(code_dir, "logo_test.png"))
                            update_job_status(log_msg=f'✅ 复制logo文件: logo_test.png')
                        else:
                            update_job_status(log_msg='⚠️ 未找到logo文件，跳过复制')
                        
                    else:
                        update_job_status(log_msg='⚠️ cover目录或Code目录不存在，跳过复制步骤')
                    
                except Exception as e:
                    update_job_status(log_msg=f'⚠️ 复制cover文件时出错: {str(e)}，但不影响后续步骤')
                
                update_job_status(progress=75, step='🎬 Step 3.6: 生成封面内容',
                                log_msg='🔄 开始生成封面内容...',
                                output_dir=output_dir)
                
                try:
                    cover_result = generate_pptcover_content(process_id)
                    subprocess.run(['echo', '开始开始生成PPT封面内容...'], check=True)
                    #subprocess.run(['echo', cover_result])
                    if cover_result.get('status') == 'success':
                        update_job_status(log_msg=f'✅ 封面内容生成成功: {cover_result.get("title", "无标题")}')
                        subprocess.run(['echo', '成功生成封面内容'], check=True)
                    else:
                        update_job_status(log_msg=f'⚠️ 封面生成问题: {cover_result.get("note", cover_result.get("error", "未知错误"))}')
                except Exception as e:
                    update_job_status(log_msg=f'⚠️ 封面生成失败: {str(e)}，但不影响后续步骤')
                    subprocess.run(['echo', '封面生成失败失败失败'], check=True)
                
                update_job_status(progress=80, step='🎥 Step 4.5: 开始预览PPT渲染',
                                log_msg='🎉 初始处理完成！开始生成预览PPT...',
                                output_dir=output_dir,
                                status='rendering_preview',
                                stage='rendering_preview')
                
                render_preview_ppt(process_id, base_name)
                
                # 【新增逻辑】根据 job_info 中的设置，决定是否自动执行后续步骤
                try:
                    with processing_lock:
                        job = processing_jobs[process_id]
                        auto_continue = job.get('auto_continue', False) # 从任务状态中读取

                    if auto_continue:
                        update_job_status(log_msg='⚙️ 自动模式已启用，无缝衔接后续处理...')
                        # 为了兼容 continue_paper_processing，需要手动设置它期望的 stage
                        with processing_lock:
                            processing_jobs[process_id]['stage'] = 'waiting_for_edit'
                        
                        continue_paper_processing(process_id)
                except Exception as e:
                    update_job_status(
                        status='failed', 
                        step='❌ 自动衔接失败', 
                        error=f'调用 continue_paper_processing 时出错: {str(e)}'
                    )
        else:
            # 预处理失败的逻辑
            update_job_status(
                status='failed', 
                step='❌ 预处理失败', 
                error=f'脚本 {script_to_run} 执行失败，退出码: {process.returncode}',
                log_msg=f'预处理过程中出现错误，请检查日志。'
            )
            print(f'退出码：{process.returncode}')
    
    except Exception as e:
        import traceback
        print(f"\n--- [CRITICAL THREAD ERROR] 文件夹处理线程 {process_id} 发生崩溃！ ---\n")
        traceback.print_exc()
        # 异常处理逻辑
        update_job_status(
            status='failed', 
            step='❌ 处理异常', 
            error=str(e),
            log_msg=f'初始处理过程中发生异常: {str(e)}'
        )


# 单论文&论文集后续处理步骤
# 后处理总入口
def continue_paper_processing(process_id):
    """继续论文处理流程（Step 4.5-9）"""
    import os # 【新增】
    import json # 【新增】

    with processing_lock:
        if process_id not in processing_jobs:
            raise Exception('处理任务不存在')
        
        job = processing_jobs[process_id]
        if job['stage'] != 'waiting_for_edit':
            raise Exception(f'当前阶段不支持继续处理: {job["stage"]}')
        
        # 更新状态为继续处理
        job['stage'] = 'continuing'
        job['status'] = 'running'
        base_name = job['base_name']
    
    # 启动继续处理线程
    print('开始启动处理')
    job = processing_jobs[process_id]
    chosen_format = job.get('output_format', 'video')
    if chosen_format == 'video':
        processing_thread = threading.Thread(
            target=run_continue_processing, 
            # target=run_final_processing, 
            args=(process_id, base_name)
        )
    elif chosen_format == 'ppt':
        processing_thread = threading.Thread(
            target=run_continue_processing_ppt, 
            # target=run_final_processing, 
            args=(process_id, base_name)
        )
    processing_thread.daemon = True
    processing_thread.start()
    
    return {
        'process_id': process_id,
        'message': '开始继续处理后续步骤',
        'status': 'running'
    }

# video分流
def run_continue_processing(process_id, base_name):
    """运行继续处理流程（Step 4.5-9）- 跳过反馈编辑"""
    import os
    import json
    import traceback
    import subprocess
    def update_job_status(status=None, progress=None, step=None, log_msg=None, error=None, final_video=None, stage=None):
        with processing_lock:
            if process_id in processing_jobs:
                job = processing_jobs[process_id]
                if status: job['status'] = status
                if progress is not None: job['progress'] = progress
                if step: job['current_step'] = step
                if log_msg: job['log_messages'].append({'time': datetime.now().isoformat(), 'message': log_msg})
                if error: job['error'] = error
                if final_video: job['final_video_path'] = final_video
                if stage: job['stage'] = stage
                
                job['last_update'] = datetime.now().isoformat()
    
    try:
        update_job_status(progress=85, step='📹 Step 4.5: 开始后续处理',
                         log_msg='🔄 继续执行Step 4.5-9...')
        
        # output_dir = f"{base_name}_output"
        project_root = os.path.abspath(os.path.dirname(__file__))
        output_dir_name = f"{base_name}_output"
                # === 创建配置文件 (这是您缺失的关键逻辑) ===
        with processing_lock:
            job = processing_jobs[process_id]
            custom_voice_path_rel = job.get("custom_voice_path")
            custom_voice_path_abs = None
            if custom_voice_path_rel:
                custom_voice_path_abs = os.path.join(project_root, custom_voice_path_rel)
            config_to_pass = {
                "voice_type": job.get("voice_type"),
                "custom_voice_path": custom_voice_path_abs,
                "custom_voice_text": job.get("custom_voice_text"),
            }
        
        print(f"--- [SERVICE DEBUG] run_continue_processing ---")
        print(f"  为 {process_id} 创建 job_config.json")
        print(f"  内容: {config_to_pass}")
        print(f"---------------------------------------------")
        
        temp_dir_abs = os.path.join(project_root, 'Paper2Video', output_dir_name, 'temp')
        os.makedirs(temp_dir_abs, exist_ok=True)
        config_path_abs = os.path.join(temp_dir_abs, 'job_config.json')
        with open(config_path_abs, 'w', encoding='utf-8') as f:
            json.dump(config_to_pass, f, ensure_ascii=False)
        
        # === 构建 cmd，将配置文件的绝对路径作为参数传递 ===
        print('到了这一步')
        job = processing_jobs[process_id]
        chosen_format = job.get('output_format', 'video')
        if chosen_format == 'video':
            script_path = os.path.join(project_root, 'continue_pipeline.sh')
        elif chosen_format == 'ppt':
            script_path = os.path.join(project_root, 'continue_pipeline_ppt.sh')
        cmd = ['bash', script_path, output_dir_name, config_path_abs]

        # # 构建继续处理命令 - 使用特殊的脚本只执行后续步骤
        # cmd = ['bash', 'continue_pipeline.sh', output_dir]
        
        # 执行处理脚本
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            universal_newlines=True,
            bufsize=0,
            encoding='utf-8',
            env=env
        )
        
        current_progress = 85
        
        if process.stdout:
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line:
                    line = line.rstrip()
                    if line:
                        update_job_status(log_msg=line)
                        
                        # 根据输出更新进度
                        if "Step 4.5" in line:
                            current_progress = max(current_progress, 87)
                            update_job_status(progress=current_progress, step="📹 Step 4.5: 视频预览渲染")
                        elif "Step 5" in line:
                            current_progress = max(current_progress, 89)
                            update_job_status(progress=current_progress, step="💬 Step 5: 反馈与编辑")
                        elif "Step 6" in line:
                            current_progress = max(current_progress, 91)
                            update_job_status(progress=current_progress, step="🎵 Step 6: 语音合成")
                        elif "Step 7" in line:
                            current_progress = max(current_progress, 94)
                            update_job_status(progress=current_progress, step="🔄 Step 7: 音视频对齐")
                        elif "Step 8" in line:
                            current_progress = max(current_progress, 97)
                            update_job_status(progress=current_progress, step="🎬 Step 8: 视频渲染")
                        elif "Step 9" in line:
                            current_progress = max(current_progress, 99)
                            update_job_status(progress=current_progress, step="🎦 Step 9: 视频音频合并")
                        elif "完整流程执行完毕" in line or "教学视频已生成" in line:
                            current_progress = 100
                            update_job_status(progress=current_progress, step="✅ 完成: 处理流程结束")
        process.wait()
        return_code = process.returncode

        if return_code == 0:
        # if process.returncode == 0:
            # 查找最终输出文件
            if chosen_format == 'video':
                final_output = f"Paper2Video/{base_name}_output/final_results/Video_with_voice/Full.mp4"
                update_job_status(
                    status='completed', 
                    progress=100, 
                    step='✅ 处理完成', 
                    log_msg='🎉 完整的论文处理流程全部完成！',
                    final_video=final_output if os.path.exists(final_output) else None,
                    stage='completed'
                )
                # 设置 final_output_path
                with processing_lock:
                    if process_id in processing_jobs:
                        processing_jobs[process_id]['final_output_path'] = final_output if os.path.exists(final_output) else None
            elif chosen_format == 'ppt':
                final_output = f"Paper2Video/{base_name}_output/final_results/full_presentation.pptx"
                update_job_status(
                    status='completed', 
                    progress=100, 
                    step='✅ 处理完成', 
                    log_msg='🎉 完整的PPT生成流程全部完成！',
                    stage='completed'
                )
                # 对于PPT，设置 final_output_path 而不是 final_video_path
                with processing_lock:
                    if process_id in processing_jobs:
                        processing_jobs[process_id]['final_output_path'] = final_output if os.path.exists(final_output) else None
        else:
            update_job_status(
                status='failed', 
                step='❌ 后续处理失败', 
                error=f'处理脚本退出码: {process.returncode}',
                log_msg='后续处理过程中出现错误'
            )
    
    except Exception as e:
        update_job_status(
            status='failed', 
            step='❌ 处理异常', 
            error=str(e),
            log_msg=f'后续处理过程中发生异常: {str(e)}'
        )

# ppt分流
def run_continue_processing_ppt(process_id, base_name):
    """运行继续处理流程（Step 4.5-9）- 跳过反馈编辑"""
    import os
    import json
    import traceback
    import subprocess
    def update_job_status(status=None, progress=None, step=None, log_msg=None, error=None, final_video=None, stage=None):
        with processing_lock:
            if process_id in processing_jobs:
                job = processing_jobs[process_id]
                if status: job['status'] = status
                if progress is not None: job['progress'] = progress
                if step: job['current_step'] = step
                if log_msg: job['log_messages'].append({'time': datetime.now().isoformat(), 'message': log_msg})
                if error: job['error'] = error
                if final_video: job['final_video_path'] = final_video
                if stage: job['stage'] = stage
                
                job['last_update'] = datetime.now().isoformat()
    
    try:
        update_job_status(progress=85, step='📹 Step 4.5: 开始后续处理',
                         log_msg='🔄 继续执行Step 4.5-5...')
        
        # output_dir = f"{base_name}_output"
        project_root = os.path.abspath(os.path.dirname(__file__))
        output_dir_name = f"{base_name}_output"
        
        # === 构建 cmd，将配置文件的绝对路径作为参数传递 ===
        print('到了ppt中这一步')
        job = processing_jobs[process_id]
        chosen_format = job.get('output_format', 'video')
        script_path = os.path.join(project_root, 'continue_pipeline_ppt.sh')
        output_dir = f"{base_name}_output"
        
        # 构建预览视频渲染命令
        cmd = ['bash', 'render_ppt_final.sh', output_dir_name]
        
        # 执行预览渲染脚本
        import os
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            universal_newlines=True,
            bufsize=0,
            env=env
        )
        
        current_progress = 82
        
        if process.stdout:
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line:
                    line = line.strip()
                    print(f"[{process_id}] {line}")
                    
                    # 根据输出更新进度
                    if "Step 4.5" in line:
                        current_progress = min(current_progress + 2, 88)
                        update_job_status(progress=current_progress, log_msg=line)
                    elif "预览PPT" in line:
                        current_progress = min(current_progress + 1, 88)
                        update_job_status(progress=current_progress, log_msg=line)
                    else:
                        update_job_status(log_msg=line)
        
        # 等待进程完成
        return_code = process.wait()
        
        # cmd = ['bash', script_path, output_dir_name]

        # # # 构建继续处理命令 - 使用特殊的脚本只执行后续步骤
        # # cmd = ['bash', 'continue_pipeline.sh', output_dir]
        
        # # 执行处理脚本
        # env = os.environ.copy()
        # env['PYTHONUNBUFFERED'] = '1'
        # env['PYTHONIOENCODING'] = 'utf-8'
        # print(f"执行命令: {cmd}")
        
        # process = subprocess.Popen(
        #     cmd, 
        #     stdout=subprocess.PIPE, 
        #     stderr=subprocess.STDOUT, 
        #     universal_newlines=True,
        #     bufsize=0,
        #     encoding='utf-8',
        #     env=env
        # )
        # print(f"启动成功process: {process}")
        
        # current_progress = 85
        
        # if process.stdout:
        #     while True:
        #         line = process.stdout.readline()
        #         if not line and process.poll() is not None:
        #             break
                
        #         if line:
        #             line = line.rstrip()
        #             if line:
        #                 update_job_status(log_msg=line)
                        
        #                 # 根据输出更新进度
        #                 if "Step 4.5" in line:
        #                     current_progress = max(current_progress, 87)
        #                     update_job_status(progress=current_progress, step="📹 Step 4.5: 视频预览渲染")
        #                 elif "Step 5" in line:
        #                     current_progress = max(current_progress, 89)
        #                     update_job_status(progress=current_progress, step="💬 Step 5: 反馈与编辑")
        #                 elif "Step 6" in line:
        #                     current_progress = max(current_progress, 91)
        #                     update_job_status(progress=current_progress, step="🎵 Step 6: 语音合成")
        #                 elif "Step 7" in line:
        #                     current_progress = max(current_progress, 94)
        #                     update_job_status(progress=current_progress, step="🔄 Step 7: 音视频对齐")
        #                 elif "Step 8" in line:
        #                     current_progress = max(current_progress, 97)
        #                     update_job_status(progress=current_progress, step="🎬 Step 8: 视频渲染")
        #                 elif "Step 9" in line:
        #                     current_progress = max(current_progress, 99)
        #                     update_job_status(progress=current_progress, step="🎦 Step 9: 视频音频合并")
        #                 elif "完整流程执行完毕" in line or "教学视频已生成" in line:
        #                     current_progress = 100
        #                     update_job_status(progress=current_progress, step="✅ 完成: 处理流程结束")
        # process.wait()
        # return_code = process.returncode
        # print(f"处理脚本返回码: {return_code}")

        if return_code == 0:
        # if process.returncode == 0:
            # 查找最终PPT文件
            final_output = f"Paper2Video/{base_name}_output/final_results/full_presentation.pptx"
            update_job_status(
                status='completed', 
                progress=100, 
                step='✅ 处理完成', 
                log_msg='🎉 完整的PPT生成流程全部完成！',
                stage='completed'
            )
            # 设置 final_output_path
            with processing_lock:
                if process_id in processing_jobs:
                    processing_jobs[process_id]['final_output_path'] = final_output if os.path.exists(final_output) else None
        else:
            update_job_status(
                status='failed', 
                step='❌ 后续处理失败', 
                error=f'处理脚本退出码: {process.returncode}',
                log_msg='后续处理过程中出现错误'
            )
    
    except Exception as e:
        update_job_status(
            status='failed', 
            step='❌ 处理异常', 
            error=str(e),
            log_msg=f'后续处理过程中发生异常: {str(e)}'
        )

# =================================================================
# ========================= 论文处理核心函数 =========================
# =================================================================


def generate_cover_content(process_id):
    """生成封面内容（替代generate_cover.sh脚本功能）"""
    from pathlib import Path
    import shutil
    import re
    import json
    import sys
    
    # 导入cover_generator.py的功能
    sys.path.append('/home/EduAgent')
    try:
        # 尝试导入cover_generator.py中的功能
        from cover_generator import load_config, get_paper_info_with_llm, fuse_titles_with_llm
        from api_call import APIClient
    except ImportError as e:
        return {
            'error': f'导入cover_generator.py失败: {str(e)}',
            'status': 'failed'
        }
    
    with processing_lock:
        if process_id not in processing_jobs:
            return {
                'error': '处理任务不存在',
                'status': 'failed'
            }
        
        job = processing_jobs[process_id]
        pdf_path = job.get('pdf_path')
        base_name = job.get('base_name')
        
        # 更新状态
        job['log_messages'].append({
            'time': datetime.now().isoformat(), 
            'message': '🎬 开始执行Step 3.6: 生成封面内容...'
        })
    
    try:
        # 设置路径
        source_manim_template_path = Path("/home/EduAgent/cover/1Introduction_code.py")
        mineru_output_dir = Path(f"/home/EduAgent/MinerU/outputs_clean/{base_name}")
        p2v_output_dir = Path(f"/home/EduAgent/Paper2Video/{base_name}_output")
        code_dir = p2v_output_dir / "final_results" / "Code"
        speech_dir = p2v_output_dir / "final_results" / "Speech"
        
        # 检查必要的目录和文件是否存在
        if not source_manim_template_path.exists():
            raise FileNotFoundError(f"Manim模板文件不存在: {source_manim_template_path}")
        
        if not code_dir.exists():
            raise FileNotFoundError(f"Code目录不存在: {code_dir}")
            
        if not speech_dir.exists():
            speech_dir.mkdir(parents=True, exist_ok=True)
            
        # 检查MinerU输出目录
        if not mineru_output_dir.exists():
            # 尝试创建或查找其他可能的目录
            alt_mineru_dir = Path(f"/home/EduAgent/MinerU/outputs/{base_name}")
            if alt_mineru_dir.exists():
                mineru_output_dir = alt_mineru_dir
            else:
                # 如果找不到MinerU输出，使用默认内容
                with processing_lock:
                    if process_id in processing_jobs:
                        job = processing_jobs[process_id]
                        job['log_messages'].append({
                            'time': datetime.now().isoformat(), 
                            'message': f'⚠️ 警告: MinerU输出目录不存在: {mineru_output_dir}，将使用默认标题'
                        })
                
                # 使用默认模板创建封面
                create_default_cover(code_dir, speech_dir, base_name)
                
                return {
                    'message': '使用默认内容生成封面成功',
                    'status': 'success',
                    'note': 'MinerU输出目录不存在，使用了默认标题'
                }
        
        # 加载配置
        config = load_config()
        api_client = APIClient(api_key=config['api_key'], model=config['model'])
        
        # 查找md文件
        md_files = list(mineru_output_dir.glob('*.md'))
        if not md_files:
            # 检查子目录
            for subdir in mineru_output_dir.iterdir():
                if subdir.is_dir():
                    md_files.extend(subdir.glob('*.md'))
        
        if not md_files:
            # 如果找不到md文件，使用默认内容
            with processing_lock:
                if process_id in processing_jobs:
                    job = processing_jobs[process_id]
                    job['log_messages'].append({
                        'time': datetime.now().isoformat(), 
                        'message': f'⚠️ 警告: 在MinerU输出目录中未找到任何.md文件: {mineru_output_dir}，将使用默认标题'
                    })
            
            # 使用默认模板创建封面
            create_default_cover(code_dir, speech_dir, base_name)
            
            return {
                'message': '使用默认内容生成封面成功',
                'status': 'success',
                'note': 'MinerU输出目录中未找到.md文件，使用了默认标题'
            }
        
        # 提取所有论文信息
        all_titles = []
        all_authors = []
        all_affiliations = []
        
        for md_file in md_files:
            info = get_paper_info_with_llm(md_file, api_client)
            if info:
                all_titles.append(info["title"])
                all_authors.append(info["authors"])
                all_affiliations.append(info["affiliations"])
                
        if not all_titles:
            # 如果提取失败，使用默认内容
            with processing_lock:
                if process_id in processing_jobs:
                    job = processing_jobs[process_id]
                    job['log_messages'].append({
                        'time': datetime.now().isoformat(), 
                        'message': '⚠️ 警告: 未能从MD文件中提取标题，将使用默认标题'
                    })
            
            # 使用默认模板创建封面
            create_default_cover(code_dir, speech_dir, base_name)
            
            return {
                'message': '使用默认内容生成封面成功',
                'status': 'success',
                'note': '从MD文件提取标题失败，使用了默认标题'
            }
        
        # 是否为批量模式
        is_batch = len(all_titles) > 1
        
        # 处理单位信息去重
        unique_affiliations = set()
        for aff_group in all_affiliations:
            if aff_group:  # 确保不是空字符串
                # 按逗号分割，并去除每个单位前后的空格
                affs = [aff.strip() for aff in aff_group.split(',') if aff.strip()]
                unique_affiliations.update(affs)
        
        # 将去重后的单位排序并合并成一个字符串
        final_affiliations = ", ".join(sorted(list(unique_affiliations))) if unique_affiliations else "未知单位"
        
        # 记录单位处理日志
        with processing_lock:
            if process_id in processing_jobs:
                job = processing_jobs[process_id]
                job['log_messages'].append({
                    'time': datetime.now().isoformat(), 
                    'message': f'📋 单位信息处理: 原始{len(all_affiliations)}个 -> 去重后{len(unique_affiliations)}个'
                })
        
        # 准备最终的标题和作者
        if is_batch:
            final_title = fuse_titles_with_llm(all_titles, api_client)
            final_authors = ", ".join(all_authors)
        else:
            final_title = all_titles[0] if all_titles else ""
            final_authors = all_authors[0] if all_authors else ""
        
        # 替换特殊字符，防止代码语法错误
        final_title_escaped = final_title.replace('"', '\\"')
        final_authors_escaped = final_authors.replace('"', '\\"')
        final_affiliations_escaped = final_affiliations.replace('"', '\\"')
        
        # 创建封面场景代码文件
        destination_manim_path = code_dir / "1Introduction_code.py"
        
        # 从源模板读取内容
        content = source_manim_template_path.read_text(encoding='utf-8')
        
        # 替换标题、作者和单位
        content = re.sub(r'title_text = ".*"', f'title_text = "{final_title_escaped}"', content)
        content = re.sub(r'author_text = ".*"', f'author_text = "{final_authors_escaped}"', content)
        content = re.sub(r'affiliation_text = ".*"', f'affiliation_text = "{final_affiliations_escaped}"', content)
        
        # 将修改后的内容写入最终的目标文件
        destination_manim_path.write_text(content, encoding='utf-8')
        
        # 生成讲稿文件
        speech_file = speech_dir / "1Introduction_speech.txt"
        template = "今天我们来讲解一下以【{title}】为主题的几篇论文" if is_batch else "今天我们来讲解一下【{title}】这篇论文"
        speech_content = template.format(title=final_title)
        speech_file.write_text(speech_content, encoding='utf-8')
        
        # 复制logo文件
        source_logo_path = Path("/home/EduAgent/logo_test.png")
        if source_logo_path.exists():
            try:
                shutil.copy(source_logo_path, code_dir)
                with processing_lock:
                    if process_id in processing_jobs:
                        job = processing_jobs[process_id]
                        job['log_messages'].append({
                            'time': datetime.now().isoformat(), 
                            'message': f'✅ 成功复制logo文件: {source_logo_path} -> {code_dir}'
                        })
            except Exception as e:
                with processing_lock:
                    if process_id in processing_jobs:
                        job = processing_jobs[process_id]
                        job['log_messages'].append({
                            'time': datetime.now().isoformat(), 
                            'message': f'⚠️ 警告: 复制logo文件时出错: {str(e)}，但不影响后续步骤'
                        })
        else:
            with processing_lock:
                if process_id in processing_jobs:
                    job = processing_jobs[process_id]
                    job['log_messages'].append({
                        'time': datetime.now().isoformat(), 
                        'message': f'⚠️ 警告: 未找到源logo文件: {source_logo_path}'
                    })
        
        # --- 新增功能：复制其余的py文件和所有txt文件 ---
        source_cover_dir = Path("/home/EduAgent/cover/")
        # 1. 复制其余的py文件 (除了1Introduction_code.py)
        # with processing_lock:
        #     job['log_messages'].append({'time': datetime.now().isoformat(), 'message': '📋 开始复制其余的code.py文件...'})
        # try:
        #     py_files_to_copy = [f for f in source_cover_dir.glob('*.py') if f.name != '1Introduction_code.py']
        #     if not py_files_to_copy:
        #         with processing_lock:
        #             job['log_messages'].append({'time': datetime.now().isoformat(), 'message': '   - ⚠️ 在源目录中没有找到其他需要复制的.py文件。'})
        #     else:
        #         for source_file in py_files_to_copy:
        #             destination_file = code_dir / source_file.name
        #             shutil.copy(source_file, destination_file)
        #             with processing_lock:
        #                 job['log_messages'].append({'time': datetime.now().isoformat(), 'message': f'   - ✅ 成功复制: {source_file.name} -> {destination_file}'})
        # except Exception as e:
        #     with processing_lock:
        #         job['log_messages'].append({'time': datetime.now().isoformat(), 'message': f'   - ❌ 复制其余.py文件时出错: {str(e)}'})

        # 2. 复制所有的txt文件 (除了1Introduction_speech.txt)
        with processing_lock:
            job['log_messages'].append({'time': datetime.now().isoformat(), 'message': '📋 开始复制所有的speech.txt文件...'})
        try:
            txt_files_to_copy = [f for f in source_cover_dir.glob('*.txt') if f.name != '1Introduction_speech.txt']
            if not txt_files_to_copy:
                with processing_lock:
                    job['log_messages'].append({'time': datetime.now().isoformat(), 'message': '   - ⚠️ 在源目录中没有找到需要复制的.txt文件。'})
            else:
                for source_file in txt_files_to_copy:
                    destination_file = speech_dir / source_file.name
                    shutil.copy(source_file, destination_file)
                    with processing_lock:
                        job['log_messages'].append({'time': datetime.now().isoformat(), 'message': f'   - ✅ 成功复制: {source_file.name} -> {destination_file}'})
        except Exception as e:
            with processing_lock:
                job['log_messages'].append({'time': datetime.now().isoformat(), 'message': f'   - ❌ 复制.txt文件时出错: {str(e)}'})
        # --- 新增功能结束 ---

        # 更新状态
        with processing_lock:
            if process_id in processing_jobs:
                job = processing_jobs[process_id]
                job['log_messages'].append({
                    'time': datetime.now().isoformat(), 
                    'message': '✅ 封面内容生成完成！'
                })
        
        return {
            'message': '封面内容生成成功',
            'title': final_title,
            'authors': final_authors,
            'affiliations': final_affiliations,
            'is_batch': is_batch,
            'status': 'success'
        }
        
    except Exception as e:
        # 发生错误，使用默认内容
        with processing_lock:
            if process_id in processing_jobs:
                job = processing_jobs[process_id]
                job['log_messages'].append({
                    'time': datetime.now().isoformat(), 
                    'message': f'❌ 错误: 封面生成失败: {str(e)}，尝试使用默认模板'
                })
        
        try:
            # 使用默认模板创建封面
            create_default_cover(code_dir, speech_dir, base_name)
            
            return {
                'message': '使用默认内容生成封面成功',
                'status': 'success',
                'error': str(e),
                'note': '封面生成失败，已使用默认标题'
            }
        except Exception as e2:
            return {
                'error': f'封面生成失败，且默认模板也失败: {str(e2)}',
                'original_error': str(e),
                'status': 'failed'
            }
        
def generate_pptcover_content(process_id):
    """生成封面内容（替代generate_cover.sh脚本功能）"""
    from pathlib import Path
    import shutil
    import re
    import json
    import sys
    
    # 导入cover_generator.py的功能
    sys.path.append('/home/EduAgent')
    try:
        # 尝试导入cover_generator.py中的功能
        from cover_generator import load_config, get_paper_info_with_llm, fuse_titles_with_llm
        from api_call import APIClient
    except ImportError as e:
        return {
            'error': f'导入cover_generator.py失败: {str(e)}',
            'status': 'failed'
        }
    
    with processing_lock:
        if process_id not in processing_jobs:
            return {
                'error': '处理任务不存在',
                'status': 'failed'
            }
        
        job = processing_jobs[process_id]
        pdf_path = job.get('pdf_path')
        base_name = job.get('base_name')
        
        # 更新状态
        job['log_messages'].append({
            'time': datetime.now().isoformat(), 
            'message': '🎬 开始执行Step 3.6: 生成封面内容...'
        })
    
    try:
        # 设置路径
        source_manim_template_path = Path("/home/EduAgent/pptcover/beginpage.py")
        mineru_output_dir = Path(f"/home/EduAgent/MinerU/outputs_clean/{base_name}")
        p2v_output_dir = Path(f"/home/EduAgent/Paper2Video/{base_name}_output")
        code_dir = p2v_output_dir / "final_results" / "Code"
        
        # 检查必要的目录和文件是否存在
        if not source_manim_template_path.exists():
            raise FileNotFoundError(f"PPT模板文件不存在: {source_manim_template_path}")
        
        if not code_dir.exists():
            raise FileNotFoundError(f"Code目录不存在: {code_dir}")
            
        # 检查MinerU输出目录
        if not mineru_output_dir.exists():
            # 尝试创建或查找其他可能的目录
            alt_mineru_dir = Path(f"/home/EduAgent/MinerU/outputs/{base_name}")
            if alt_mineru_dir.exists():
                mineru_output_dir = alt_mineru_dir
            else:
                # 如果找不到MinerU输出，使用默认内容
                with processing_lock:
                    if process_id in processing_jobs:
                        job = processing_jobs[process_id]
                        job['log_messages'].append({
                            'time': datetime.now().isoformat(), 
                            'message': f'⚠️ 警告: MinerU输出目录不存在: {mineru_output_dir}，将使用默认标题'
                        })
                
                # 使用默认模板创建封面
                # create_default_cover(code_dir, speech_dir, base_name)
                
                return {
                    'message': '不生成封面',
                    'status': 'success',
                    'note': 'MinerU输出目录不存在，使用了默认标题'
                }
        
        # 加载配置
        config = load_config()
        api_client = APIClient(api_key=config['api_key'], model=config['model'])
        
        # 查找md文件
        md_files = list(mineru_output_dir.glob('*.md'))
        if not md_files:
            # 检查子目录
            for subdir in mineru_output_dir.iterdir():
                if subdir.is_dir():
                    md_files.extend(subdir.glob('*.md'))
        
        if not md_files:
            # 如果找不到md文件，使用默认内容
            with processing_lock:
                if process_id in processing_jobs:
                    job = processing_jobs[process_id]
                    job['log_messages'].append({
                        'time': datetime.now().isoformat(), 
                        'message': f'⚠️ 警告: 在MinerU输出目录中未找到任何.md文件: {mineru_output_dir}，将使用默认标题'
                    })
            
            # 使用默认模板创建封面
            #create_default_cover(code_dir, speech_dir, base_name)
            
            return {
                'message': '不生成封面',
                'status': 'success',
                'note': 'MinerU输出目录中未找到.md文件，使用了默认标题'
            }
        
        # 提取所有论文信息
        all_titles = []
        all_authors = []
        all_affiliations = []
        subprocess.run(['echo', 'aaaaaaaaaaaaaaaaaaa'])
        
        for md_file in md_files:
            info = get_paper_info_with_llm(md_file, api_client)
            if info:
                all_titles.append(info["title"])
                all_authors.append(info["authors"])
                all_affiliations.append(info["affiliations"])
                
        if not all_titles:
            # 如果提取失败，使用默认内容
            with processing_lock:
                if process_id in processing_jobs:
                    job = processing_jobs[process_id]
                    job['log_messages'].append({
                        'time': datetime.now().isoformat(), 
                        'message': '⚠️ 警告: 未能从MD文件中提取标题，将使用默认标题'
                    })
            
            # 使用默认模板创建封面
            # create_default_cover(code_dir, speech_dir, base_name)
            
            return {
                'message': '不生成封面',
                'status': 'success',
                'note': '从MD文件提取标题失败，使用了默认标题'
            }
        
        # 是否为批量模式
        is_batch = len(all_titles) > 1
        
        # 处理单位信息去重
        unique_affiliations = set()
        for aff_group in all_affiliations:
            if aff_group:  # 确保不是空字符串
                # 按逗号分割，并去除每个单位前后的空格
                affs = [aff.strip() for aff in aff_group.split(',') if aff.strip()]
                unique_affiliations.update(affs)
        
        # 将去重后的单位排序并合并成一个字符串
        final_affiliations = ", ".join(sorted(list(unique_affiliations))) if unique_affiliations else "未知单位"
        
        # 记录单位处理日志
        with processing_lock:
            if process_id in processing_jobs:
                job = processing_jobs[process_id]
                job['log_messages'].append({
                    'time': datetime.now().isoformat(), 
                    'message': f'📋 单位信息处理: 原始{len(all_affiliations)}个 -> 去重后{len(unique_affiliations)}个'
                })
        
        # 准备最终的标题和作者
        if is_batch:
            final_title = fuse_titles_with_llm(all_titles, api_client)
            final_authors = ", ".join(all_authors)
        else:
            final_title = all_titles[0] if all_titles else ""
            final_authors = all_authors[0] if all_authors else ""
        
        # 替换特殊字符，防止代码语法错误
        final_title_escaped = final_title.replace('"', '\\"')
        final_authors_escaped = final_authors.replace('"', '\\"')
        final_affiliations_escaped = final_affiliations.replace('"', '\\"')
        
        # 创建封面场景代码文件
        subprocess.run(['echo', '创建封面创建封面创建封面创建封面创建封面创建封面创建封面创建封面'])
        destination_manim_path = code_dir / "pptcover_页0_code.py"
        print("创建封面创建封面创建封面创建封面创建封面创建封面创建封面创建封面")
        # 从源模板读取内容
        content = source_manim_template_path.read_text(encoding='utf-8')
        
        # 替换标题、作者和单位
        content = re.sub(r'title_text = ".*"', f'title_text = "{final_title_escaped}"', content)
        content = re.sub(r'author_text = ".*"', f'author_text = "{final_authors_escaped}"', content)
        content = re.sub(r'affiliation_text = ".*"', f'affiliation_text = "{final_affiliations_escaped}"', content)
        
        # 将修改后的内容写入最终的目标文件
        destination_manim_path.write_text(content, encoding='utf-8')
        print("创建封面创建封面创建封面创建封面创建封面创建封面创建封面创建封面成功成功成功成功")
        subprocess.run(['echo', '成功成功成功成功成功成功成功成功'])
        
        # 复制logo文件
        source_logo_path = Path("/home/EduAgent/logo_test.png")
        if source_logo_path.exists():
            try:
                shutil.copy(source_logo_path, code_dir)
                with processing_lock:
                    if process_id in processing_jobs:
                        job = processing_jobs[process_id]
                        job['log_messages'].append({
                            'time': datetime.now().isoformat(), 
                            'message': f'✅ 成功复制logo文件: {source_logo_path} -> {code_dir}'
                        })
            except Exception as e:
                with processing_lock:
                    if process_id in processing_jobs:
                        job = processing_jobs[process_id]
                        job['log_messages'].append({
                            'time': datetime.now().isoformat(), 
                            'message': f'⚠️ 警告: 复制logo文件时出错: {str(e)}，但不影响后续步骤'
                        })
        else:
            with processing_lock:
                if process_id in processing_jobs:
                    job = processing_jobs[process_id]
                    job['log_messages'].append({
                        'time': datetime.now().isoformat(), 
                        'message': f'⚠️ 警告: 未找到源logo文件: {source_logo_path}'
                    })
        
        # 更新状态
        with processing_lock:
            if process_id in processing_jobs:
                job = processing_jobs[process_id]
                job['log_messages'].append({
                    'time': datetime.now().isoformat(), 
                    'message': '✅ 封面内容生成完成！'
                })
        
        return {
            'message': '封面内容生成成功',
            'title': final_title,
            'authors': final_authors,
            'affiliations': final_affiliations,
            'is_batch': is_batch,
            'status': 'success'
        }
        
    except Exception as e:
        # 发生错误，使用默认内容
        with processing_lock:
            if process_id in processing_jobs:
                job = processing_jobs[process_id]
                job['log_messages'].append({
                    'time': datetime.now().isoformat(), 
                    'message': f'❌ 错误: 封面生成失败: {str(e)}，尝试使用默认模板'
                })
        
            return {
                'error': f'封面生成失败: {str(e)}',
                'original_error': str(e),
                'status': 'failed'
            }

def create_default_cover(code_dir, speech_dir, base_name):
    """创建默认的封面内容（当无法提取论文信息时）"""
    from pathlib import Path
    import re
    import shutil
    
    # 默认标题、作者和单位
    default_title = f"论文《{base_name}》详解"
    default_authors = "未知作者"
    default_affiliations = "未知单位"
    
    # 创建封面场景代码文件
    source_manim_template_path = Path("/home/EduAgent/cover/1Introduction_code.py")
    destination_manim_path = code_dir / "1Introduction_code.py"
    
    # 从源模板读取内容
    if source_manim_template_path.exists():
        content = source_manim_template_path.read_text(encoding='utf-8')
        
        # 替换标题、作者和单位
        content = re.sub(r'title_text = ".*"', f'title_text = "{default_title}"', content)
        content = re.sub(r'author_text = ".*"', f'author_text = "{default_authors}"', content)
        content = re.sub(r'affiliation_text = ".*"', f'affiliation_text = "{default_affiliations}"', content)
        
        # 将修改后的内容写入最终的目标文件
        destination_manim_path.write_text(content, encoding='utf-8')
    
    # 生成讲稿文件
    speech_dir.mkdir(parents=True, exist_ok=True)
    speech_file = speech_dir / "1Introduction_speech.txt"
    speech_content = f"今天我们来讲解一下【{default_title}】这篇论文"
    speech_file.write_text(speech_content, encoding='utf-8')
    
    # 复制logo文件
    source_logo_path = Path("/home/EduAgent/logo_test.png")
    if source_logo_path.exists():
        try:
            shutil.copy(source_logo_path, code_dir)
            print(f"✅ 成功复制logo文件: {source_logo_path} -> {code_dir}")
        except Exception as e:
            print(f"⚠️ 复制logo文件时出错: {str(e)}")
    else:
        print(f"⚠️ 未找到源logo文件: {source_logo_path}")

def render_preview_video(process_id, base_name):
    """渲染预览视频，完成后进入等待交互编辑状态"""
    def update_job_status(status=None, progress=None, step=None, log_msg=None, error=None, final_video=None, stage=None):
        with processing_lock:
            if process_id in processing_jobs:
                job = processing_jobs[process_id]
                if status: job['status'] = status
                if progress is not None: job['progress'] = progress
                if step: job['current_step'] = step
                if log_msg: job['log_messages'].append({'time': datetime.now().isoformat(), 'message': log_msg})
                if error: job['error'] = error
                if final_video: job['final_video_path'] = final_video
                if stage: job['stage'] = stage
                
                job['last_update'] = datetime.now().isoformat()
    
    try:
        update_job_status(progress=82, step='🎥 Step 4.5: 执行预览视频渲染',
                         log_msg='🔄 开始生成预览视频...')
        
        output_dir = f"{base_name}_output"
        
        # 构建预览视频渲染命令
        cmd = ['bash', 'render_preview.sh', output_dir]
        
        # 执行预览渲染脚本
        import os
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            universal_newlines=True,
            bufsize=0,
            env=env
        )
        
        current_progress = 82
        
        if process.stdout:
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line:
                    line = line.strip()
                    print(f"[{process_id}] {line}")
                    
                    # 根据输出更新进度
                    if "Step 4.5" in line:
                        current_progress = min(current_progress + 2, 88)
                        update_job_status(progress=current_progress, log_msg=line)
                    elif "预览视频" in line:
                        current_progress = min(current_progress + 1, 88)
                        update_job_status(progress=current_progress, log_msg=line)
                    else:
                        update_job_status(log_msg=line)
        
        # 等待进程完成
        return_code = process.wait()
        
        if return_code == 0:
            # 预览视频渲染成功，进入等待交互编辑状态
            update_job_status(
                status='waiting_for_edit',
                progress=90,
                step='💬 预览完成: 等待交互编辑',
                log_msg='🎬 预览视频已生成！现在可以查看预览效果并进行交互式编辑',
                stage='waiting_for_edit'
            )
        else:
            # 预览视频渲染失败，但可以继续编辑
            update_job_status(
                status='waiting_for_edit',
                progress=90,
                step='⚠️ 预览失败但可继续编辑',
                log_msg='⚠️ 预览视频渲染失败，但您仍可以进行交互式编辑',
                stage='waiting_for_edit'
            )
    
    except Exception as e:
        # 预览失败，但可以继续编辑
        update_job_status(
            status='waiting_for_edit',
            progress=90,
            step='⚠️ 预览异常但可继续编辑',
            log_msg=f'⚠️ 预览视频渲染异常: {str(e)}，但您仍可以进行交互式编辑',
            stage='waiting_for_edit'
        )




def start_preview_and_feedback(process_id):
    """检查预览和编辑状态（预览已集成到初始流程中）"""
    with processing_lock:
        if process_id not in processing_jobs:
            raise Exception('处理任务不存在')
        
        job = processing_jobs[process_id]
        if job['stage'] != 'waiting_for_edit':
            raise Exception(f'当前阶段不支持预览和反馈: {job["stage"]}')
    
    return {
        'process_id': process_id,
        'message': '预览视频已生成，现在可以进行交互式编辑',
        'status': 'waiting_for_edit'
    }




def render_preview_ppt(process_id, base_name):
    """渲染预览视频，完成后进入等待交互编辑状态"""
    def update_job_status(status=None, progress=None, step=None, log_msg=None, error=None, final_video=None, stage=None):
        with processing_lock:
            if process_id in processing_jobs:
                job = processing_jobs[process_id]
                if status: job['status'] = status
                if progress is not None: job['progress'] = progress
                if step: job['current_step'] = step
                if log_msg: job['log_messages'].append({'time': datetime.now().isoformat(), 'message': log_msg})
                if error: job['error'] = error
                if final_video: job['final_video_path'] = final_video
                if stage: job['stage'] = stage
                
                job['last_update'] = datetime.now().isoformat()
    
    try:
        update_job_status(progress=82, step='🎥 Step 4.5: 执行预览PPT渲染',
                         log_msg='🔄 开始生成预览PPT...')
        
        output_dir = f"{base_name}_output"
        
        # 构建预览视频渲染命令
        cmd = ['bash', 'render_preview_ppt.sh', output_dir]
        
        # 执行预览渲染脚本
        import os
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            universal_newlines=True,
            bufsize=0,
            env=env
        )
        
        current_progress = 82
        
        if process.stdout:
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line:
                    line = line.strip()
                    print(f"[{process_id}] {line}")
                    
                    # 根据输出更新进度
                    if "Step 4.5" in line:
                        current_progress = min(current_progress + 2, 88)
                        update_job_status(progress=current_progress, log_msg=line)
                    elif "预览PPT" in line:
                        current_progress = min(current_progress + 1, 88)
                        update_job_status(progress=current_progress, log_msg=line)
                    else:
                        update_job_status(log_msg=line)
        
        # 等待进程完成
        return_code = process.wait()
        
        if return_code == 0:
            # 预览视频渲染成功，进入等待交互编辑状态
            update_job_status(
                status='waiting_for_edit',
                progress=90,
                step='💬 预览完成: 等待交互编辑',
                log_msg='🎬 预览PPT已生成！现在可以查看预览效果并进行交互式编辑',
                stage='waiting_for_edit'
            )
        else:
            # 预览视频渲染失败，但可以继续编辑
            update_job_status(
                status='waiting_for_edit',
                progress=90,
                step='⚠️ 预览失败但可继续编辑',
                log_msg='⚠️ 预览PPT渲染失败，但您仍可以进行交互式编辑',
                stage='waiting_for_edit'
            )
    
    except Exception as e:
        # 预览失败，但可以继续编辑
        update_job_status(
            status='waiting_for_edit',
            progress=90,
            step='⚠️ 预览异常但可继续编辑',
            log_msg=f'⚠️ 预览PPT渲染异常: {str(e)}，但您仍可以进行交互式编辑',
            stage='waiting_for_edit'
        )

def run_preview_only(process_id, base_name):
    """只运行Step 4.5预览视频渲染，然后进入等待反馈编辑状态"""
    def update_job_status(status=None, progress=None, step=None, log_msg=None, error=None, final_video=None, stage=None):
        with processing_lock:
            if process_id in processing_jobs:
                job = processing_jobs[process_id]
                if status: job['status'] = status
                if progress is not None: job['progress'] = progress
                if step: job['current_step'] = step
                if log_msg: job['log_messages'].append({'time': datetime.now().isoformat(), 'message': log_msg})
                if error: job['error'] = error
                if final_video: job['final_video_path'] = final_video
                if stage: job['stage'] = stage
                
                job['last_update'] = datetime.now().isoformat()
    
    try:
        update_job_status(progress=50, step='🎥 Step 4.5: 开始预览视频渲染',
                         log_msg='🔄 开始生成预览视频...')
        
        output_dir = f"{base_name}_output"
        
        # 构建预览视频渲染命令
        cmd = ['bash', 'render_preview.sh', output_dir]
        
        # 执行预览渲染脚本
        import os
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            universal_newlines=True,
            bufsize=0,
            env=env
        )
        
        current_progress = 50
        
        if process.stdout:
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line:
                    line = line.strip()
                    print(f"[{process_id}] {line}")
                    
                    # 根据输出更新进度
                    if "Step 4.5" in line:
                        current_progress = min(current_progress + 5, 55)
                        update_job_status(progress=current_progress, log_msg=line)
                    elif "预览视频" in line:
                        current_progress = min(current_progress + 2, 55)
                        update_job_status(progress=current_progress, log_msg=line)
                    else:
                        update_job_status(log_msg=line)
        
        return_code = process.wait()
        
        if return_code == 0:
            # 预览视频渲染成功，进入等待反馈编辑状态
            update_job_status(
                status='waiting_feedback',
                progress=55,
                step='💬 等待反馈编辑',
                log_msg='🎬 预览视频已生成，等待反馈编辑',
                stage='waiting_feedback'
            )
        else:
            # 预览视频渲染失败
            update_job_status(
                status='failed',
                error=f'预览视频渲染失败，退出码: {return_code}',
                log_msg='❌ 预览视频渲染过程中出现错误'
            )
    
    except Exception as e:
        update_job_status(
            status='failed',
            error=str(e),
            log_msg=f'❌ 预览视频渲染异常: {str(e)}'
        )

def continue_after_feedback(process_id):
    """交互编辑完成后继续处理（Step 6-9）"""
    with processing_lock:
        if process_id not in processing_jobs:
            raise Exception('处理任务不存在')
        
        job = processing_jobs[process_id]
        if job['stage'] != 'waiting_for_edit':
            raise Exception(f'当前阶段不支持继续处理: {job["stage"]}')
        
        # 更新状态为继续处理
        job['stage'] = 'final_processing'
        job['status'] = 'running'
        base_name = job['base_name']
    
    # 启动最终处理线程
    processing_thread = threading.Thread(
        target=run_final_processing, 
        args=(process_id, base_name)
    )
    processing_thread.daemon = True
    processing_thread.start()
    
    return {
        'process_id': process_id,
        'message': '开始最终处理步骤（语音合成和视频渲染）',
        'status': 'running'
    }

def run_final_processing(process_id, base_name):
    """运行最终处理流程（Step 6-9），包含动态音色配置"""
    import os # 【新增】在函数开头导入 os 模块
    import json # 【新增】同时导入 json 模块，以防万一
    
    # 内部的 update_job_status 辅助函数保持不变
    """运行最终处理流程（Step 6-9）"""
    def update_job_status(status=None, progress=None, step=None, log_msg=None, error=None, output_dir=None, stage=None):
        with processing_lock:
            if process_id in processing_jobs:
                job = processing_jobs[process_id]
                if status: job['status'] = status
                if progress is not None: job['progress'] = progress
                if step: job['current_step'] = step
                if log_msg: job['log_messages'].append({'time': datetime.now().isoformat(), 'message': log_msg})
                if error: job['error'] = error
                if output_dir: job['output_dir'] = output_dir
                if stage: job['stage'] = stage
                job['last_update'] = datetime.now().isoformat()
    
    try:
        update_job_status(progress=10, step='🎵 Step 6: 开始最终处理',
                         log_msg='🔄 开始执行Step 6-9: 语音合成和视频渲染...')
        
        output_dir = f"{base_name}_output"
        # 【新增】在调用脚本前，创建包含 job 配置的 JSON 文件
        # with processing_lock:
        #     job = processing_jobs[process_id]
        #     config_to_pass = {
        #         "voice_type": job.get("voice_type"),
        #         "custom_voice_path": job.get("custom_voice_path"),
        #         "custom_voice_text": job.get("custom_voice_text"),
        #     }
        
        #         # 打印调试信息，确认配置是否正确
        # print(f"--- [SERVICE DEBUG] run_final_processing ---")
        # print(f"  为 {process_id} 创建 job_config.json")
        # print(f"  内容: {config_to_pass}")
        # print(f"--------------------------------------------")

        
        # temp_dir = f'Paper2Video/{base_name}_output/temp'
        # os.makedirs(temp_dir, exist_ok=True)
        # config_path = os.path.join(temp_dir, 'job_config.json')
        # with open(config_path, 'w', encoding='utf-8') as f:
        #     json.dump(config_to_pass, f)

        # 【修改】使用绝对路径
        # ==================== 【核心修复逻辑：使用绝对路径】 ====================
        with processing_lock:
            job = processing_jobs[process_id]
            # 获取项目根目录的绝对路径
            # os.path.abspath(os.path.dirname(__file__)) 会得到 services.py 所在的目录
            project_root = os.path.abspath(os.path.dirname(__file__))

            # 如果 job 中保存的 custom_voice_path 是相对路径，也转换为绝对路径
            custom_voice_path_rel = job.get("custom_voice_path")
            custom_voice_path_abs = None
            if custom_voice_path_rel:
                custom_voice_path_abs = os.path.join(project_root, custom_voice_path_rel)

            config_to_pass = {
                "voice_type": job.get("voice_type"),
                # 【修改】传递绝对路径给配置文件
                "custom_voice_path": custom_voice_path_abs, 
                "custom_voice_text": job.get("custom_voice_text"),
            }
        
        print(f"--- [SERVICE DEBUG] run_final_processing ---")
        print(f"  内容 (使用绝对路径): {config_to_pass}")
        print(f"--------------------------------------------")
        
        # 使用绝对路径创建临时目录和配置文件
        temp_dir_abs = os.path.join(project_root, f'Paper2Video/{base_name}_output/temp')
        os.makedirs(temp_dir_abs, exist_ok=True)
        config_path_abs = os.path.join(temp_dir_abs, 'job_config.json')
        
        # 【修改】将配置文件的绝对路径也保存到 job_info 中，供 shell 脚本使用
        with processing_lock:
            processing_jobs[process_id]['job_config_path'] = config_path_abs

        with open(config_path_abs, 'w', encoding='utf-8') as f:
            json.dump(config_to_pass, f, ensure_ascii=False) # 增加 ensure_ascii=False
        # =================================================================


        # # 创建一个专门用于最终处理的脚本调用
        # cmd = ['bash', 'final_pipeline.sh', output_dir]
        # 【修改】将配置文件的绝对路径作为参数传递给 shell 脚本
        cmd = ['bash', 'final_pipeline.sh', output_dir, config_path_abs]

        # 执行处理脚本
        import os
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            universal_newlines=True,
            bufsize=0,
            env=env
        )
        
        current_progress = 10
        
        if process.stdout:
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                
                if line:
                    line = line.rstrip()
                    if line:
                        update_job_status(log_msg=line)
                        
                        # 根据输出更新进度
                        if 'Step 6' in line:
                            current_progress = max(current_progress, 30)
                            update_job_status(progress=current_progress, step='🎵 Step 6: 语音合成')
                        elif 'Step 7' in line:
                            current_progress = max(current_progress, 50)
                            update_job_status(progress=current_progress, step='🔄 Step 7: 音视频对齐')
                        elif 'Step 8' in line:
                            current_progress = max(current_progress, 70)
                            update_job_status(progress=current_progress, step='🎬 Step 8: 视频渲染')
                        elif 'Step 9' in line:
                            current_progress = max(current_progress, 90)
                            update_job_status(progress=current_progress, step='🎦 Step 9: 视频音频合并')
                        elif '完整流程执行完毕' in line or '教学视频已生成' in line:
                            current_progress = 100
                            update_job_status(progress=current_progress, step='✅ 完成: 处理流程结束')
        
        process.wait()
        
        if process.returncode == 0:
            # 查找最终视频
            final_video = f"Paper2Video/{base_name}_output/final_results/Video_with_voice/Full.mp4"
            
            update_job_status(
                status='completed', 
                progress=100, 
                step='✅ 处理完成', 
                log_msg='🎉 完整的论文处理流程全部完成！',
                final_video=final_video if os.path.exists(final_video) else None,
                stage='completed'
            )
        else:
            update_job_status(
                status='failed', 
                step='❌ 最终处理失败', 
                error=f'处理脚本退出码: {process.returncode}',
                log_msg='最终处理过程中出现错误'
            )
    
    # ...
    except Exception as e:
        # 【新增】导入 traceback 模块以获取详细的错误堆栈
        import traceback
        
        # 【修改】打印更详细的错误信息到后端终端
        print(f"!!!!!!!!!!!!!! [FATAL ERROR] in run_final_processing !!!!!!!!!!!!!!")
        print(f"  Process ID: {process_id}")
        print(f"  Exception Type: {type(e).__name__}")
        print(f"  Exception Message: {e}")
        print(f"  Traceback:")
        # 打印完整的错误堆栈，这会告诉我们是哪一行代码出的错
        traceback.print_exc()
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

        # 将详细错误信息也更新到 job 状态中，方便前端查看
        error_details = traceback.format_exc()
        update_job_status(
            status='failed', 
            step='❌ 最终处理异常', 
            error=str(e),
            log_msg=f'最终处理过程中发生严重异常: {error_details}'
        )

def get_processing_status(process_id):
    """获取处理状态"""
    with processing_lock:
        if process_id not in processing_jobs:
            return {'error': '处理任务不存在'}
        
        job = processing_jobs[process_id].copy()
        
        # 添加调试信息
        print(f"[DEBUG] 获取处理状态 - Process ID: {process_id}")
        print(f"[DEBUG] 状态: {job['status']}, 进度: {job['progress']}")
        print(f"[DEBUG] 当前步骤: {job['current_step']}")
        print(f"[DEBUG] 处理阶段: {job.get('stage', 'unknown')}")
        print(f"[DEBUG] 日志消息数量: {len(job['log_messages'])}")
        
        result = {
            'process_id': process_id,
            'status': job['status'],
            'progress': job['progress'],
            'current_step': job['current_step'],
            'start_time': job['start_time'],
            # 'pdf_filename': job['pdf_filename'],
            # 【核心修正】
            # 使用 .get() 方法安全地获取值。
            # 如果 'pdf_filename' 不存在，它会尝试获取 'folder_name'。
            # 如果两者都不存在，则返回 '未知任务'。
            'pdf_filename': job.get('pdf_filename', job.get('folder_name', '未知任务')),

            'output_dir': job['output_dir'],
            'final_video_path': job['final_video_path'],
            'error': job['error'],
            'stage': job.get('stage', 'unknown'),  # 新增stage字段
            'recent_logs': job['log_messages'][-30:] if job['log_messages'] else []  # 最近30条日志
        }
        # 别忘了在最外层也加上 success 标志
        result['success'] = True
        print(f"[DEBUG] 返回的recent_logs数量: {len(result['recent_logs'])}")
        return result

def get_processing_results():
    """获取所有处理结果列表"""
    with processing_lock:
        results = []
        for process_id, job in processing_jobs.items():
            if job['status'] in ['completed', 'failed']:
                result_info = {
                    'process_id': process_id,
                    'pdf_filename': job['pdf_filename'],
                    'status': job['status'],
                    'start_time': job['start_time'],
                    'output_dir': job['output_dir'],
                    'final_video_path': job['final_video_path'],
                    'error': job['error']
                }
                results.append(result_info)
        
        return {'results': results}

def get_result_download_path(result_id):
    """获取结果下载路径"""
    with processing_lock:
        if result_id not in processing_jobs:
            print(f"[DEBUG] 下载失败：processing_jobs中找不到result_id: {result_id}")
            return None
        
        job = processing_jobs[result_id]
        if job['status'] != 'completed':
            print(f"[DEBUG] 下载失败：任务状态不是completed: {job['status']}")
            return None
        
        # 【修改点】优先使用我们新添加的、通用的 final_output_path 字段
        # 这个字段既可以存视频路径，也可以存文档的.zip路径
        file_path = job.get('final_output_path')
        print(f"[DEBUG] 检查final_output_path: {file_path}")
        
        if file_path and os.path.exists(file_path):
            print(f"[DEBUG] 找到文件: {file_path}")
            return file_path
        elif file_path:
            print(f"[DEBUG] final_output_path存在但文件不存在: {file_path}")
        
        # 【为了兼容旧数据】如果上面的新字段找不到，再尝试检查旧的 final_video_path
        # 这可以保证您之前只生成了视频的任务也能正常下载
        file_path_legacy = job.get('final_video_path')
        print(f"[DEBUG] 检查final_video_path: {file_path_legacy}")
        
        if file_path_legacy and os.path.exists(file_path_legacy):
            print(f"[DEBUG] 找到兼容文件: {file_path_legacy}")
            return file_path_legacy
        elif file_path_legacy:
            print(f"[DEBUG] final_video_path存在但文件不存在: {file_path_legacy}")
        
        print(f"[DEBUG] 所有路径都不可用")
        return None 

def run_folder_markdown_generation(process_id, base_name):
    """运行Markdown文档生成和打包流程"""
    def update_job_status(status=None, progress=None, step=None, log_msg=None, error=None, final_output=None, stage=None):
        with processing_lock:
            if process_id in processing_jobs:
                job = processing_jobs[process_id]
                if status: job['status'] = status
                if progress is not None: job['progress'] = progress
                if step: job['current_step'] = step
                if log_msg: job['log_messages'].append({'time': datetime.now().isoformat(), 'message': log_msg})
                if error: job['error'] = error
                if final_output: job['final_output_path'] = final_output
                if stage: job['stage'] = stage
                job['last_update'] = datetime.now().isoformat()

    try:
        update_job_status(progress=75, step='📝 Step 4.1: 准备文档生成', log_msg='🚀 开始执行文档生成脚本...')
        
        output_base_dir = f"Paper2Video/{base_name}_output"
        input_sections_dir = os.path.join(output_base_dir, 'sections')
        output_md_dir_name = f"{base_name}_markdown"
        output_md_path = os.path.join(output_base_dir, output_md_dir_name)

        # ------------------- 【核心修改点：动态查找图片路径】 -------------------
        update_job_status(log_msg=f'🔍 正在搜索图片文件夹于: {output_base_dir}')
        
        # 使用 glob 递归搜索名为 'images' 的文件夹
        # `**` 表示匹配任意层级的子目录
        # search_pattern = os.path.join(output_base_dir, '**', 'images')
        # found_images_dirs = glob.glob(search_pattern, recursive=True)

        # 使用 glob 递归搜索名为 'images' 的文件夹
        # `**` 表示匹配任意层级的子目录
        search_pattern_images = os.path.join(output_base_dir, '**', 'images')  # ✅ 修改
        search_pattern_combined = os.path.join(output_base_dir, '**', 'combined_images')  # ✅ 新增

        found_images_dirs = glob.glob(search_pattern_images, recursive=True)
        found_combined_dirs = glob.glob(search_pattern_combined, recursive=True)  # ✅ 新增

        all_candidate_dirs = found_combined_dirs + found_images_dirs  # ✅ 优先使用 combined_images

        images_dir = None
        # if found_images_dirs:
        if all_candidate_dirs:  # ✅ 修改原来的 found_images_dirs 为 all_candidate_dirs
            # 通常我们期望只找到一个。如果找到多个，默认取第一个。
            # images_dir = found_images_dirs[0]
            images_dir = all_candidate_dirs[0]
            update_job_status(log_msg=f'✅ 成功找到图片文件夹: {images_dir}')
        else:
            # 【备用方案】如果找不到，创建一个空的临时图片文件夹，让脚本可以继续执行
            # 这对应了您提供的正常输出中的 "[警告] 在图片目录中未找到图片" 的情况
            update_job_status(log_msg='⚠️ 未找到图片文件夹，将创建一个空目录以继续流程。')
            images_dir = os.path.join(output_base_dir, 'temp_empty_images')
            os.makedirs(images_dir, exist_ok=True)
        # ------------------- 图片路径查找结束 -------------------
        
        os.makedirs(output_md_path, exist_ok=True)

        cmd = [
            'python3',
            '/home/EduAgent/Paper2Video/create_speech_package_multipaper.py',
            input_sections_dir,
            images_dir,# <--- 【修改】使用我们动态找到的正确路径
            output_md_path
        ]

        update_job_status(log_msg=f'⚙️ 执行命令: {" ".join(cmd)}') # 增加日志，方便调试

        # ... (函数余下的 subprocess.Popen 和打包逻辑保持不变)
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
            universal_newlines=True, bufsize=1, encoding='utf-8'
        )

        if process.stdout:
            for line in process.stdout:
                update_job_status(log_msg=line.strip())
        
        process.wait()

        if process.returncode == 0:
            update_job_status(progress=90, step='📦 Step 4.2: 打包文档文件', log_msg='✅ 文档生成成功，开始压缩文件...')

            # 打包成ZIP文件
            zip_filename = f"{output_md_dir_name}.zip"
            zip_filepath = os.path.join(output_base_dir, zip_filename)

            with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(output_md_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # 创建在zip文件中的相对路径
                        archive_name = os.path.relpath(file_path, output_md_path)
                        zipf.write(file_path, archive_name)
            
            update_job_status(log_msg=f'📦 成功创建压缩包: {zip_filepath}')

            update_job_status(
                status='completed',
                progress=100,
                step='✅ 文档已生成',
                log_msg='🎉 Markdown文档处理流程全部完成！',
                final_output=zip_filepath,
                stage='completed'
            )
        else:
            raise Exception(f"文档生成脚本执行失败，退出码: {process.returncode}")

    except Exception as e:
        update_job_status(
            status='failed',
            step='❌ 文档生成失败',
            error=str(e),
            log_msg=f'处理过程中发生异常: {str(e)}',
            stage='completed'
        )


def run_markdown_generation(process_id, base_name):
    """运行Markdown文档生成和打包流程"""
    def update_job_status(status=None, progress=None, step=None, log_msg=None, error=None, final_output=None, stage=None):
        with processing_lock:
            if process_id in processing_jobs:
                job = processing_jobs[process_id]
                if status: job['status'] = status
                if progress is not None: job['progress'] = progress
                if step: job['current_step'] = step
                if log_msg: job['log_messages'].append({'time': datetime.now().isoformat(), 'message': log_msg})
                if error: job['error'] = error
                if final_output: job['final_output_path'] = final_output
                if stage: job['stage'] = stage
                job['last_update'] = datetime.now().isoformat()

    try:
        update_job_status(progress=75, step='📝 Step 4.1: 准备文档生成', log_msg='🚀 开始执行文档生成脚本...')
        
        output_base_dir = f"Paper2Video/{base_name}_output"
        input_sections_dir = os.path.join(output_base_dir, 'sections')
        output_md_dir_name = f"{base_name}_markdown"
        output_md_path = os.path.join(output_base_dir, output_md_dir_name)

        # ------------------- 【核心修改点：动态查找图片路径】 -------------------
        update_job_status(log_msg=f'🔍 正在搜索图片文件夹于: {output_base_dir}')
        
        # 使用 glob 递归搜索名为 'images' 的文件夹
        # `**` 表示匹配任意层级的子目录
        # search_pattern = os.path.join(output_base_dir, '**', 'images')
        # found_images_dirs = glob.glob(search_pattern, recursive=True)

        # 使用 glob 递归搜索名为 'images' 的文件夹
        # `**` 表示匹配任意层级的子目录
        search_pattern_images = os.path.join(output_base_dir, '**', 'images')  # ✅ 修改
        search_pattern_combined = os.path.join(output_base_dir, '**', 'combined_images')  # ✅ 新增

        found_images_dirs = glob.glob(search_pattern_images, recursive=True)
        found_combined_dirs = glob.glob(search_pattern_combined, recursive=True)  # ✅ 新增

        all_candidate_dirs = found_combined_dirs + found_images_dirs  # ✅ 优先使用 combined_images

        images_dir = None
        # if found_images_dirs:
        if all_candidate_dirs:  # ✅ 修改原来的 found_images_dirs 为 all_candidate_dirs
            # 通常我们期望只找到一个。如果找到多个，默认取第一个。
            # images_dir = found_images_dirs[0]
            images_dir = all_candidate_dirs[0]
            update_job_status(log_msg=f'✅ 成功找到图片文件夹: {images_dir}')
        else:
            # 【备用方案】如果找不到，创建一个空的临时图片文件夹，让脚本可以继续执行
            # 这对应了您提供的正常输出中的 "[警告] 在图片目录中未找到图片" 的情况
            update_job_status(log_msg='⚠️ 未找到图片文件夹，将创建一个空目录以继续流程。')
            images_dir = os.path.join(output_base_dir, 'temp_empty_images')
            os.makedirs(images_dir, exist_ok=True)
        # ------------------- 图片路径查找结束 -------------------
        
        os.makedirs(output_md_path, exist_ok=True)

        cmd = [
            'python3',
            '/home/EduAgent/Paper2Video/create_speech_package.py',
            input_sections_dir,
            images_dir,# <--- 【修改】使用我们动态找到的正确路径
            output_md_path
        ]

        update_job_status(log_msg=f'⚙️ 执行命令: {" ".join(cmd)}') # 增加日志，方便调试

        # ... (函数余下的 subprocess.Popen 和打包逻辑保持不变)
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
            universal_newlines=True, bufsize=1, encoding='utf-8'
        )

        if process.stdout:
            for line in process.stdout:
                update_job_status(log_msg=line.strip())
        
        process.wait()

        if process.returncode == 0:
            update_job_status(progress=90, step='📦 Step 4.2: 打包文档文件', log_msg='✅ 文档生成成功，开始压缩文件...')

            # 打包成ZIP文件
            zip_filename = f"{output_md_dir_name}.zip"
            zip_filepath = os.path.join(output_base_dir, zip_filename)

            with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(output_md_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # 创建在zip文件中的相对路径
                        archive_name = os.path.relpath(file_path, output_md_path)
                        zipf.write(file_path, archive_name)
            
            update_job_status(log_msg=f'📦 成功创建压缩包: {zip_filepath}')

            update_job_status(
                status='completed',
                progress=100,
                step='✅ 文档已生成',
                log_msg='🎉 Markdown文档处理流程全部完成！',
                final_output=zip_filepath,
                stage='completed'
            )
        else:
            raise Exception(f"文档生成脚本执行失败，退出码: {process.returncode}")

    except Exception as e:
        update_job_status(
            status='failed',
            step='❌ 文档生成失败',
            error=str(e),
            log_msg=f'处理过程中发生异常: {str(e)}',
            stage='completed'
        )

# ========================= Web版交互编辑器功能 =========================

def get_editor_files(process_id):
    """获取指定处理任务的可编辑文件列表"""
    with processing_lock:
        if process_id not in processing_jobs:
            raise Exception('处理任务不存在')
        
        job = processing_jobs[process_id]
        if not job['output_dir']:
            raise Exception('处理任务尚未生成输出目录')
    
    # 构建文件路径
    code_dir = os.path.join(job['output_dir'], 'final_results', 'Code')
    speech_dir = os.path.join(job['output_dir'], 'final_results', 'Speech')
    video_preview_dir = os.path.join(job['output_dir'], 'final_results', 'Video_Preview')
    
    all_files = []
    
    # 收集Code文件
    if os.path.exists(code_dir):
        for file in os.listdir(code_dir):
            if file.endswith('.py'):
                file_path = os.path.join(code_dir, file)
                all_files.append({
                    'type': 'Code',
                    'filename': file,
                    'path': file_path,
                    'relative_path': os.path.join('Code', file),
                    'size': os.path.getsize(file_path)
                })
    
    # 收集Speech文件
    if os.path.exists(speech_dir):
        for file in os.listdir(speech_dir):
            if file.endswith('.txt'):
                file_path = os.path.join(speech_dir, file)
                all_files.append({
                    'type': 'Speech',
                    'filename': file,
                    'path': file_path,
                    'relative_path': os.path.join('Speech', file),
                    'size': os.path.getsize(file_path)
                })
    
    # 收集Video Preview视频文件
    page_videos = []
    if os.path.exists(video_preview_dir):
        for file in os.listdir(video_preview_dir):
            if file.endswith('.mp4'):
                file_path = os.path.join(video_preview_dir, file)
                page_videos.append({
                    'type': 'VideoPreview',
                    'filename': file,
                    'path': file_path,
                    'relative_path': os.path.join('Video_Preview', file),
                    'size': os.path.getsize(file_path)
                })
    
    # 按文件名排序
    all_files.sort(key=lambda x: x['filename'])
    page_videos.sort(key=lambda x: x['filename'])
    
    return {
        'files': all_files,
        'page_videos': page_videos,
        'code_dir': code_dir,
        'speech_dir': speech_dir,
        'video_preview_dir': video_preview_dir,
        'total_count': len(all_files),
        'video_count': len(page_videos)
    }

def get_file_content(file_path):
    """获取文件内容"""
    # 安全检查
    if not os.path.exists(file_path):
        raise Exception('文件不存在')
    
    if '..' in file_path or not (file_path.endswith('.py') or file_path.endswith('.txt')):
        raise Exception('不支持的文件类型或路径不安全')
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 获取文件统计信息
        lines = content.split('\n')
        
        return {
            'content': content,
            'filename': os.path.basename(file_path),
            'file_path': file_path,
            'line_count': len(lines),
            'size': len(content.encode('utf-8'))
        }
    
    except Exception as e:
        raise Exception(f'读取文件失败: {str(e)}')

def save_file_content(file_path, content):
    """保存文件内容"""
    # 安全检查
    if '..' in file_path or not (file_path.endswith('.py') or file_path.endswith('.txt')):
        raise Exception('不支持的文件类型或路径不安全')
    
    if not os.path.exists(os.path.dirname(file_path)):
        raise Exception('目标目录不存在')
    
    try:
        # 备份原文件
        backup_path = file_path + '.backup'
        if os.path.exists(file_path):
            import shutil
            shutil.copy2(file_path, backup_path)
        
        # 保存新内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 验证保存结果
        with open(file_path, 'r', encoding='utf-8') as f:
            saved_content = f.read()
        
        if saved_content != content:
            # 如果保存失败，恢复备份
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, file_path)
            raise Exception('文件保存验证失败')
        
        # 清理备份文件
        if os.path.exists(backup_path):
            os.remove(backup_path)
        
        return {
            'message': '文件保存成功',
            'filename': os.path.basename(file_path),
            'size': len(content.encode('utf-8'))
        }
    
    except Exception as e:
        raise Exception(f'保存文件失败: {str(e)}')

def upload_background_image(file, process_id):
    """上传背景图片"""
    from werkzeug.utils import secure_filename
    
    with processing_lock:
        if process_id not in processing_jobs:
            raise Exception('处理任务不存在')
        
        job = processing_jobs[process_id]
        if not job['output_dir']:
            raise Exception('处理任务尚未生成输出目录')
    
    # 构建目标目录
    code_dir = os.path.join(job['output_dir'], 'final_results', 'Code')
    if not os.path.exists(code_dir):
        raise Exception('Code目录不存在')
    
    # 安全处理文件名
    filename = secure_filename(file.filename)
    if not filename:
        raise Exception('无效的文件名')
    
    # 检查文件类型
    valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')
    if not filename.lower().endswith(valid_extensions):
        raise Exception(f'不支持的图片格式，支持的格式: {", ".join(valid_extensions)}')
    
    # 保存文件
    file_path = os.path.join(code_dir, filename)
    try:
        file.save(file_path)
        
        # 验证文件保存
        if not os.path.exists(file_path):
            raise Exception('文件保存失败')
        
        file_size = os.path.getsize(file_path)
        
        return {
            'message': '背景图片上传成功',
            'filename': filename,
            'file_path': file_path,
            'size': file_size
        }
    
    except Exception as e:
        raise Exception(f'上传背景图片失败: {str(e)}')

def apply_background_to_code(process_id, background_file):
    """应用背景图到所有代码文件"""
    import subprocess
    
    with processing_lock:
        if process_id not in processing_jobs:
            raise Exception('处理任务不存在')
        
        job = processing_jobs[process_id]
        if not job['output_dir']:
            raise Exception('处理任务尚未生成输出目录')
    
    # 构建目录路径
    code_dir = os.path.join(job['output_dir'], 'final_results', 'Code')
    if not os.path.exists(code_dir):
        raise Exception('Code目录不存在')
    
    # 检查背景文件是否存在
    bg_file_path = os.path.join(code_dir, background_file)
    if not os.path.exists(bg_file_path):
        raise Exception('背景图片文件不存在')
    
    try:
        # 调用background.py脚本
        job = processing_jobs[process_id]
        chosen_format = job.get('output_format', 'video')
        if chosen_format == 'video':
            command = ['python3', 'background.py', code_dir, background_file]
        elif chosen_format == 'ppt':
            command = ['python3', 'replace_pptbackground.py', code_dir, background_file]
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=30  # 30秒超时
        )
        
        # 统计修改的文件数量
        code_files = [f for f in os.listdir(code_dir) if f.endswith('.py')]
        
        return {
            'message': '背景图应用成功',
            'modified_files': len(code_files),
            'background_file': background_file,
            'output': result.stdout if result.stdout else '执行完成',
            'warnings': result.stderr if result.stderr else None
        }
    
    except subprocess.TimeoutExpired:
        raise Exception('背景图应用超时')
    except subprocess.CalledProcessError as e:
        error_msg = f'background.py执行失败: {e}'
        if e.stderr:
            error_msg += f'\n错误详情: {e.stderr}'
        raise Exception(error_msg)
    except Exception as e:
        raise Exception(f'应用背景图失败: {str(e)}')

def search_editor_files(process_id, search_term):
    """搜索编辑器文件"""
    # 获取所有文件
    files_result = get_editor_files(process_id)
    all_files = files_result['files']
    page_videos = files_result['page_videos']
    
    if not search_term:
        return files_result
    
    # 搜索匹配的文件
    search_term_lower = search_term.lower()
    matched_files = []
    matched_videos = []
    
    for file_info in all_files:
        if (search_term_lower in file_info['filename'].lower() or 
            search_term_lower in file_info['type'].lower()):
            matched_files.append(file_info)
    
    for video_info in page_videos:
        if (search_term_lower in video_info['filename'].lower() or 
            search_term_lower in video_info['type'].lower()):
            matched_videos.append(video_info)
    
    return {
        'files': matched_files,
        'page_videos': matched_videos,
        'search_term': search_term,
        'total_count': len(matched_files),
        'video_count': len(matched_videos),
        'original_count': len(all_files),
        'original_video_count': len(page_videos)
    }

def get_page_video_associations(process_id):
    """获取视频预览与对应文件的关联关系"""
    with processing_lock:
        if process_id not in processing_jobs:
            raise Exception('处理任务不存在')
        
        job = processing_jobs[process_id]
        if not job['output_dir']:
            raise Exception('处理任务尚未生成输出目录')
    
    # 构建文件路径
    code_dir = os.path.join(job['output_dir'], 'final_results', 'Code')
    speech_dir = os.path.join(job['output_dir'], 'final_results', 'Speech')
    video_preview_dir = os.path.join(job['output_dir'], 'final_results', 'Video_Preview')
    
    associations = []
    
    # 如果视频预览目录存在
    if os.path.exists(video_preview_dir):
        for video_file in os.listdir(video_preview_dir):
            if video_file.endswith('.mp4'):
                # 提取基础名称（去掉扩展名）
                base_name = os.path.splitext(video_file)[0]
                
                # 查找对应的代码文件和讲稿文件
                code_file = f"{base_name}_code.py"
                speech_file = f"{base_name}_speech.txt"
                
                code_path = os.path.join(code_dir, code_file)
                speech_path = os.path.join(speech_dir, speech_file)
                video_path = os.path.join(video_preview_dir, video_file)
                
                association = {
                    'base_name': base_name,
                    'video_file': video_file,
                    'video_path': video_path,
                    'video_size': os.path.getsize(video_path),
                    'code_file': code_file if os.path.exists(code_path) else None,
                    'speech_file': speech_file if os.path.exists(speech_path) else None,
                    'code_exists': os.path.exists(code_path),
                    'speech_exists': os.path.exists(speech_path)
                }
                
                associations.append(association)
    
    # 按基础名称排序
    associations.sort(key=lambda x: x['base_name'])
    
    return {
        'associations': associations,
        'total_count': len(associations),
        'video_preview_dir': video_preview_dir
    } 

def ai_edit_code(original_code: str, edit_request: str, filename: str = None) -> dict:
    """
    使用AI智能体编辑代码
    
    Args:
        original_code: 原始代码
        edit_request: 用户的修改需求
        filename: 文件名（可选）
    
    Returns:
        dict: 包含修改后代码的结果
    """
    try:
        # 读取配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        api_key = config.get('api_key')
        model = config.get('model', 'gpt-4.5-preview')
        
        if not api_key:
            raise Exception("未配置API密钥")
        
        # 构建提示词
        file_info = f"文件名: {filename}\n\n" if filename else ""
        
        prompt = f"""你是一个专业的代码编辑助手。请根据用户的修改需求，对给定的代码进行修改。

{file_info}用户修改需求：
{edit_request}

原始代码：
```
{original_code}
```

请提供修改后的完整代码。你的回答应该只包含修改后的代码，不需要任何解释或说明。确保：
1. 保持代码的基本结构和功能
2. 只修改需要修改的部分
3. 确保修改后的代码语法正确
4. 保持代码风格一致

修改后的代码："""

        # 调用API获取修改后的代码
        ai_response = process_text(prompt, api_key, model)
        
        # 清理响应，提取代码部分
        modified_code = ai_response.strip()
        
        # 如果响应被代码块包裹，提取其中的代码
        if modified_code.startswith('```'):
            lines = modified_code.split('\n')
            # 去掉第一行的```和可能的语言标识
            if len(lines) > 1:
                lines = lines[1:]
            # 去掉最后一行的```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            modified_code = '\n'.join(lines)
        
        return {
            'original_code': original_code,
            'modified_code': modified_code,
            'edit_request': edit_request,
            'filename': filename
        }
        
    except Exception as e:
        raise Exception(f"AI编辑代码失败: {str(e)}")