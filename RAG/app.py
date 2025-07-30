from flask import Flask, render_template, request, jsonify, send_file
from exa_py import Exa
import re
import requests
import os
from urllib.parse import urlparse
import glob
import json
import sys
import hashlib
from bs4 import BeautifulSoup
import html2text
sys.path.append('..')
from api_call import process_text

app = Flask(__name__)

# 替换为你自己的 Exa API 密钥
EXA_API_KEY = '211ed197-9199-401d-9897-a8408526f8b8'
exa = Exa(EXA_API_KEY)

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """搜索API"""
    data = request.get_json()
    search_type = data.get('search_type')
    keyword = data.get('keyword')
    
    if not keyword:
        return jsonify({'error': '请输入搜索关键词'}), 400
    
    try:
        if search_type == 'web':
            results = search_web(keyword)
        elif search_type == 'paper':
            results = search_papers(keyword)
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

@app.route('/smart-filter', methods=['POST'])
def smart_filter():
    """智能筛选API"""
    data = request.get_json()
    keyword = data.get('keyword', '')
    papers = data.get('papers', [])
    
    if not keyword or not papers:
        return jsonify({'error': '缺少必要参数'}), 400
    
    try:
        # 构建发送给AI的提示词
        prompt = f"""
请根据用户的搜索需求"{keyword}"，从以下论文列表中选择最相关和有价值的论文。

论文列表：
"""
        
        for i, paper in enumerate(papers):
            prompt += f"\n{i+1}. 标题: {paper.get('title', '无标题')}\n"
            prompt += f"   摘要: {paper.get('abstract', '无摘要')}\n"
            prompt += f"   链接: {paper.get('url', '无链接')}\n"
        
        prompt += f"""

请分析每篇论文与用户需求"{keyword}"的相关性，选择最合适的论文。请以JSON格式返回结果，包含以下字段：
{{
    "recommended_papers": [论文索引列表，从0开始],
    "reasoning": "选择这些论文的理由",
    "total_recommended": 推荐论文数量
}}

请只返回JSON格式的结果，不要包含其他文字。
"""
        
        # 调用API - 从配置文件读取API密钥
        with open('../config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        api_key = config.get('api_key')
        model = config.get('model', 'gpt-4o')
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
            # 如果解析失败，返回错误
            return jsonify({
                'error': f'AI响应解析失败: {str(e)}',
                'raw_response': ai_response
            }), 500
        
        # 验证AI返回的索引是否有效
        recommended_indices = ai_result.get('recommended_papers', [])
        valid_indices = [i for i in recommended_indices if 0 <= i < len(papers)]
        
        # 构建推荐结果
        recommended_papers = []
        for i in valid_indices:
            paper = papers[i].copy()
            paper['original_index'] = i
            recommended_papers.append(paper)
        
        return jsonify({
            'success': True,
            'recommended_papers': recommended_papers,
            'reasoning': ai_result.get('reasoning', ''),
            'total_recommended': len(recommended_papers)
        })
        
    except Exception as e:
        return jsonify({'error': f'智能筛选失败: {str(e)}'}), 500

@app.route('/crawl', methods=['POST'])
def crawl_papers():
    """爬取论文PDF"""
    data = request.get_json()
    urls = data.get('urls', [])
    titles = data.get('titles', [])  # 添加标题参数
    
    if not urls:
        return jsonify({'error': '未选择要爬取的论文'}), 400
    
    try:
        crawled_count = 0
        failed_urls = []
        
        # 创建下载目录
        download_dir = 'downloaded_papers'
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        # 加载或创建元数据文件
        metadata_file = os.path.join(download_dir, 'metadata.json')
        metadata = load_metadata(metadata_file)
        
        for i, url in enumerate(urls):
            pdf_url = convert_arxiv_url_to_pdf(url)
            if pdf_url:
                title = titles[i] if i < len(titles) else "未知标题"
                success, filename = download_pdf_with_title(pdf_url, download_dir, title, metadata)
                if success:
                    crawled_count += 1
                else:
                    failed_urls.append(url)
            else:
                failed_urls.append(url)
        
        # 保存元数据
        save_metadata(metadata_file, metadata)
        
        response_data = {
            'success': True,
            'crawled_count': crawled_count,
            'total_count': len(urls),
            'failed_count': len(failed_urls)
        }
        
        if failed_urls:
            response_data['failed_urls'] = failed_urls
        
        return jsonify(response_data)
    
    except Exception as e:
        return jsonify({'error': f'爬取失败: {str(e)}'}), 500

@app.route('/crawl-webpages', methods=['POST'])
def crawl_webpages():
    """爬取网页内容"""
    data = request.get_json()
    urls = data.get('urls', [])
    titles = data.get('titles', [])
    
    if not urls:
        return jsonify({'error': '未选择要爬取的网页'}), 400
    
    try:
        crawled_count = 0
        failed_urls = []
        
        # 创建下载目录
        download_dir = 'downloaded_webpages'
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        # 加载或创建元数据文件
        metadata_file = os.path.join(download_dir, 'metadata.json')
        metadata = load_metadata(metadata_file)
        
        for i, url in enumerate(urls):
            title = titles[i] if i < len(titles) else "未知标题"
            success, filename = download_webpage(url, download_dir, title, metadata)
            if success:
                crawled_count += 1
            else:
                failed_urls.append(url)
        
        # 保存元数据
        save_metadata(metadata_file, metadata)
        
        response_data = {
            'success': True,
            'crawled_count': crawled_count,
            'total_count': len(urls),
            'failed_count': len(failed_urls)
        }
        
        if failed_urls:
            response_data['failed_urls'] = failed_urls
        
        return jsonify(response_data)
    
    except Exception as e:
        return jsonify({'error': f'网页爬取失败: {str(e)}'}), 500

@app.route('/pdf-list')
def get_pdf_list():
    """获取已下载的PDF文件列表"""
    try:
        download_dir = 'downloaded_papers'
        if not os.path.exists(download_dir):
            return jsonify({'success': True, 'pdfs': []})
        
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
        
        return jsonify({
            'success': True,
            'pdfs': pdf_files,
            'count': len(pdf_files)
        })
    
    except Exception as e:
        return jsonify({'error': f'获取PDF列表失败: {str(e)}'}), 500

@app.route('/webpage-list')
def get_webpage_list():
    """获取已下载的网页文件列表"""
    try:
        download_dir = 'downloaded_webpages'
        if not os.path.exists(download_dir):
            return jsonify({'success': True, 'webpages': []})
        
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
        
        return jsonify({
            'success': True,
            'webpages': webpage_files,
            'count': len(webpage_files)
        })
    
    except Exception as e:
        return jsonify({'error': f'获取网页列表失败: {str(e)}'}), 500

@app.route('/pdf-preview/<filename>')
def preview_pdf(filename):
    """提供PDF文件预览服务"""
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
    try:
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
        
        return jsonify({
            'success': True,
            'deleted_count': total_deleted_count,
            'message': f'成功清除了 {total_deleted_count} 个文件'
        })
    
    except Exception as e:
        return jsonify({'error': f'清除内容失败: {str(e)}'}), 500

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
        
        response = requests.get(pdf_url, headers=headers, timeout=30)
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

def download_pdf(pdf_url, download_dir):
    """下载PDF文件（兼容性保留）"""
    try:
        # 从URL中提取论文ID作为文件名
        paper_id = pdf_url.split('/')[-1].replace('.pdf', '')
        filename = f"{paper_id}.pdf"
        filepath = os.path.join(download_dir, filename)
        
        # 如果文件已存在，跳过下载
        if os.path.exists(filepath):
            print(f"文件已存在，跳过下载: {filename}")
            return True
        
        # 下载PDF
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(pdf_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 检查响应是否为PDF
        content_type = response.headers.get('content-type', '')
        if 'pdf' not in content_type.lower():
            print(f"响应不是PDF文件: {content_type}")
            return False
        
        # 保存文件
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        print(f"成功下载: {filename}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"下载失败: {pdf_url}, 错误: {str(e)}")
        return False
    except Exception as e:
        print(f"保存文件失败: {str(e)}")
        return False

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
        
        response = requests.get(url, headers=headers, timeout=30)
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

if __name__ == '__main__':
    app.run(debug=True) 