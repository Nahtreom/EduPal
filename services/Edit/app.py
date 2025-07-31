from flask import Flask, render_template, send_from_directory, request, jsonify
import os
import magic
import re
import sys
import json
import threading
import base64
from difflib import SequenceMatcher
import time
from typing import Optional
from openai import OpenAI

# 获取脚本文件所在的目录
script_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(script_dir, 'templates')

app = Flask(__name__,
           template_folder=template_dir)  # 使用绝对路径指定模板文件夹

# 配置文件夹路径 - 从命令行参数获取
def get_folder_paths():
    if len(sys.argv) < 5:
        print("使用方法: python app.py <视频文件夹> <代码文件夹> <讲稿文件夹> <预览图片文件夹>")
        print("例如: python app.py ./videos ./code ./scripts ./preview")
        sys.exit(1)
    
    video_folder = sys.argv[1]
    code_folder = sys.argv[2]
    script_folder = sys.argv[3]
    preview_folder = sys.argv[4]
    
    # 验证文件夹是否存在
    if not os.path.exists(video_folder):
        print(f"错误: 视频文件夹不存在: {video_folder}")
        sys.exit(1)
    if not os.path.exists(code_folder):
        print(f"错误: 代码文件夹不存在: {code_folder}")
        sys.exit(1)
    if not os.path.exists(script_folder):
        print(f"错误: 讲稿文件夹不存在: {script_folder}")
        sys.exit(1)
    
    # 预览文件夹如果不存在则创建
    if not os.path.exists(preview_folder):
        print(f"预览文件夹不存在，将创建: {preview_folder}")
        os.makedirs(preview_folder, exist_ok=True)
    
    return video_folder, code_folder, script_folder, preview_folder

VIDEO_FOLDER, CODE_FOLDER, SCRIPT_FOLDER, PREVIEW_FOLDER = get_folder_paths()

# 从配置文件读取API配置
def load_api_config():
    config_path = "../Paper2Video/config.json"  # 修改配置文件路径
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('api_key', ''), config.get('model', 'gpt-4o')
    except FileNotFoundError:
        print(f"警告: 配置文件 {config_path} 不存在，使用默认配置")
        return '', 'gpt-4o'
    except json.JSONDecodeError:
        print(f"错误: 配置文件 {config_path} 格式错误")
        return '', 'gpt-4o'
    except Exception as e:
        print(f"读取配置文件错误: {str(e)}")
        return '', 'gpt-4o'

API_KEY, DEFAULT_MODEL = load_api_config()
API_BASE_URL = "https://yeysai.com/v1/"
MAX_RETRIES = 3

def call_api_with_text(text: str, model: Optional[str] = None) -> str:
    """调用OpenAI API处理文本，模仿api_call.py的实现"""
    try:
        # 使用配置文件中的模型，如果没有指定的话
        if model is None:
            model = DEFAULT_MODEL
        
        # 确保model不为None
        if not model:
            model = "gpt-4o"  # 备用默认值
        
        # 确保有有效的API密钥
        if not API_KEY:
            return "错误：未配置API密钥，请检查Paper2Video/config.json文件"
        
        client = OpenAI(
            api_key=API_KEY,
            base_url=API_BASE_URL,
        )
        
        retry_count = 0
        response_content = None

        while retry_count < MAX_RETRIES:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    max_tokens=2000,
                    temperature=0.3
                )
                
                if response.choices and response.choices[0].message:
                    response_content = response.choices[0].message.content
                else:
                    response_content = f"错误：响应中未找到预期的'content'。响应: {response}"
                break  # 成功，跳出重试循环

            except Exception as e:
                retry_count += 1
                print(f"API调用错误 (尝试 {retry_count}/{MAX_RETRIES}): {e}")
                if retry_count >= MAX_RETRIES:
                    response_content = f"错误：达到最大重试次数后API调用失败。最后错误: {e}"
                    break
                print(f"等待 {5 * retry_count} 秒后重试...")
                time.sleep(5 * retry_count)

        return response_content if response_content else "未能获取模型响应"
        
    except Exception as e:
        return f"API调用失败: {str(e)}"

def similarity(a, b):
    """计算两个字符串的相似度"""
    return SequenceMatcher(None, a, b).ratio()

def extract_base_name(filename):
    """提取文件名的基础部分，去掉扩展名和常见的编号"""
    base = os.path.splitext(filename)[0]
    
    # 去掉常见的后缀模式
    # 去掉 _code, _speech 等后缀
    base = re.sub(r'_(code|speech)$', '', base)
    
    # 去掉split相关的后缀和页码
    base = re.sub(r'_split_页\d+', '', base)
    
    # 去掉常见的编号模式，如 _01, -01, (01), _页1, _页2 等
    base = re.sub(r'[_\-\(\)](\d+|页\d+)$', '', base)
    
    return base.lower()

def extract_chapter_and_section(filename):
    """提取章节和分段信息，用于更精确的匹配"""
    # 匹配模式：Chapter_test_Chapter_split_页X_type.ext
    pattern = r'(\w+)_test_\1_split_页(\d+)'
    match = re.search(pattern, filename)
    
    if match:
        chapter = match.group(1).lower()  # Introduction, Methods, etc.
        section = match.group(2)          # 页码
        return f"{chapter}_page{section}"
    
    # 处理cover文件：Introduction0.py -> introduction_cover
    cover_pattern = r'^(\w+)(\d+)\.(py|mp4)$'
    match = re.search(cover_pattern, filename)
    if match:
        chapter = match.group(1).lower()
        return f"{chapter}_cover"
    
    # 默认返回基础名
    return extract_base_name(filename)

def find_matching_files():
    """查找匹配的文件"""
    matches = []
    
    # 获取所有视频文件
    video_files = []
    if os.path.exists(VIDEO_FOLDER):
        for file in os.listdir(VIDEO_FOLDER):
            file_path = os.path.join(VIDEO_FOLDER, file)
            if os.path.isfile(file_path):
                mime = magic.Magic(mime=True)
                file_type = mime.from_file(file_path)
                if file_type.startswith('video/'):
                    video_files.append(file)
    
    # 获取所有代码文件
    code_files = []
    if CODE_FOLDER and os.path.exists(CODE_FOLDER):
        for file in os.listdir(CODE_FOLDER):
            if file.endswith('.py'):
                code_files.append(file)
    
    # 获取所有讲稿文件
    script_files = []
    if SCRIPT_FOLDER and os.path.exists(SCRIPT_FOLDER):
        for file in os.listdir(SCRIPT_FOLDER):
            if file.endswith('.txt'):
                script_files.append(file)
    
    print(f"[DEBUG] 找到 {len(video_files)} 个视频文件")
    print(f"[DEBUG] 找到 {len(code_files)} 个代码文件")
    print(f"[DEBUG] 找到 {len(script_files)} 个讲稿文件")
    
    # 为每个视频文件寻找匹配的代码和讲稿
    for video in video_files:
        video_key = extract_chapter_and_section(video)
        print(f"[DEBUG] 处理视频: {video} -> 匹配键: {video_key}")
        
        # 寻找精确匹配的代码文件
        best_code = None
        best_code_similarity = 0
        for code in code_files:
            code_key = extract_chapter_and_section(code)
            
            # 精确匹配
            if video_key == code_key:
                best_code = code
                best_code_similarity = 1.0
                print(f"[DEBUG] 代码精确匹配: {code} -> {code_key}")
                break
            
            # 备用相似度匹配
            sim = similarity(video_key, code_key)
            print(f"[DEBUG] 代码匹配: {code} -> {code_key} -> 相似度: {sim:.3f}")
            if sim > best_code_similarity and sim > 0.2:
                best_code_similarity = sim
                best_code = code
        
        # 寻找精确匹配的讲稿文件
        best_script = None
        best_script_similarity = 0
        for script in script_files:
            script_key = extract_chapter_and_section(script)
            
            # 精确匹配
            if video_key == script_key:
                best_script = script
                best_script_similarity = 1.0
                print(f"[DEBUG] 讲稿精确匹配: {script} -> {script_key}")
                break
            
            # 备用相似度匹配
            sim = similarity(video_key, script_key)
            print(f"[DEBUG] 讲稿匹配: {script} -> {script_key} -> 相似度: {sim:.3f}")
            if sim > best_script_similarity and sim > 0.2:
                best_script_similarity = sim
                best_script = script
        
        print(f"[DEBUG] 最佳匹配 - 代码: {best_code} (相似度: {best_code_similarity:.3f})")
        print(f"[DEBUG] 最佳匹配 - 讲稿: {best_script} (相似度: {best_script_similarity:.3f})")
        
        # 生成友好的标题
        title = video_key.replace('_', ' ').replace('page', 'Page ').title()
        if 'cover' in video_key:
            title = title.replace('Cover', 'Introduction')
        
        matches.append({
            'video': video,
            'code': best_code,
            'script': best_script,
            'title': title
        })
    
    return matches

@app.route('/')
def index():
    matches = find_matching_files()
    return render_template('index.html', matches=matches)

@app.route('/video/<filename>')
def serve_video(filename):
    return send_from_directory(VIDEO_FOLDER, filename)

@app.route('/code/<filename>')
def serve_code(filename):
    """提供代码文件服务"""
    print(f"[DEBUG] 请求代码文件: {filename}")
    print(f"[DEBUG] 代码文件夹: {CODE_FOLDER}")
    file_path = os.path.join(CODE_FOLDER, filename)
    print(f"[DEBUG] 完整路径: {file_path}")
    print(f"[DEBUG] 文件存在: {os.path.exists(file_path)}")
    
    if not os.path.exists(file_path):
        print(f"[ERROR] 文件不存在: {file_path}")
        return f"文件不存在: {filename}", 404
    
    return send_from_directory(CODE_FOLDER, filename)

@app.route('/script/<filename>')
def serve_script(filename):
    """提供讲稿文件服务"""
    print(f"[DEBUG] 请求讲稿文件: {filename}")
    print(f"[DEBUG] 讲稿文件夹: {SCRIPT_FOLDER}")
    file_path = os.path.join(SCRIPT_FOLDER, filename)
    print(f"[DEBUG] 完整路径: {file_path}")
    print(f"[DEBUG] 文件存在: {os.path.exists(file_path)}")
    
    if not os.path.exists(file_path):
        print(f"[ERROR] 文件不存在: {file_path}")
        return f"文件不存在: {filename}", 404
    
    return send_from_directory(SCRIPT_FOLDER, filename)

@app.route('/optimize-code', methods=['POST'])
def optimize_code():
    try:
        if not request.json:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        
        original_code = request.json.get('code', '')
        requirement = request.json.get('requirement', '')
        
        if not original_code or not requirement:
            return jsonify({'success': False, 'error': '代码和需求不能为空'}), 400
        
        # 构建优化提示
        prompt = f"""请根据以下需求优化Manim动画代码。

                    **用户需求:**
                    {requirement}

                    **原始Manim代码:**
                    ```python
                    {original_code}
                    ```

                    **重要要求:**
                    1. 这是Manim动画库代码，请保持Manim的语法和结构
                    2. **绝对不能改变或删除动画展示的内容和效果**，只能优化代码结构和性能
                    3. **必须完整保留以下背景设置代码（原代码用的是什么图片路径，你就保留什么路径），不得修改:**
                    ```python
                    bg = ImageMobject("xxx.jpg")
                    bg.scale_to_fit_height(config.frame_height)
                    bg.scale_to_fit_width(config.frame_width)
                    bg.set_opacity(0.2)
                    bg.move_to(ORIGIN)
                    self.add(bg)
                    ```
                    4. 保持所有动画对象、文本内容、数学公式、图形元素完全一致
                    5. 保持动画的时序、效果、持续时间不变
                    6. 确保代码语法正确且能正常运行
                    7. 优化时可以改进代码结构、变量命名、注释等，但不能改变视觉效果
                    8. 只返回Python代码，不要包含markdown格式的代码块标记

                    请直接从第一行开始提供优化后的完整Manim代码："""

        # 调用API
        optimized_code = call_api_with_text(prompt)
        
        if optimized_code.startswith("错误：") or optimized_code.startswith("API调用失败"):
            return jsonify({'success': False, 'error': optimized_code}), 500
        
        # 清理可能存在的markdown代码块标记
        optimized_code = optimized_code.strip()
        if optimized_code.startswith("```python"):
            optimized_code = optimized_code[9:]
        if optimized_code.startswith("```"):
            optimized_code = optimized_code[3:]
        if optimized_code.endswith("```"):
            optimized_code = optimized_code[:-3]
        optimized_code = optimized_code.strip()
        
        return jsonify({
            'success': True, 
            'optimized_code': optimized_code,
            'message': '代码优化完成'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'优化失败: {str(e)}'}), 500

@app.route('/multimodal-feedback', methods=['POST'])
def multimodal_feedback():
    """多模态反馈：同时处理截图和文字需求"""
    try:
        if not request.json:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        
        # 获取数据
        image_data = request.json.get('imageData', '')
        requirement = request.json.get('requirement', '')
        current_code = request.json.get('currentCode', '')  # 可选：当前代码内容
        
        print(f"[DEBUG] 多模态反馈 - 需求长度: {len(requirement)}")
        print(f"[DEBUG] 多模态反馈 - 图片数据长度: {len(image_data)}")
        print(f"[DEBUG] 多模态反馈 - 代码长度: {len(current_code)}")
        
        if not image_data or not requirement:
            return jsonify({'success': False, 'error': '缺少图片数据或反馈需求'}), 400
        
        # 移除base64头部信息
        if image_data.startswith('data:image/png;base64,'):
            image_data = image_data[22:]
        elif image_data.startswith('data:image/jpeg;base64,'):
            image_data = image_data[23:]
        
        # 构建多模态提示
        if current_code:
            prompt = f"""请根据截图和用户需求，分析并优化以下Manim动画代码。

**用户需求:**
{requirement}

**当前代码:**
```python
{current_code}
```

**分析要求:**
1. 仔细观察截图中的动画效果和页面布局
2. 结合用户的具体需求进行分析
3. 保持Manim动画的核心功能不变
4. 提供具体的优化建议和改进代码
5. 如果截图显示了问题，请明确指出并提供解决方案
6. 保持背景设置不变（如果存在的话）
7. 直接返回优化后的完整代码，不要包含markdown格式

请基于截图和需求提供优化建议："""
        else:
            prompt = f"""请根据截图和用户需求，提供相关的分析和建议。

**用户需求:**
{requirement}

**分析要求:**
1. 仔细观察截图中的内容和布局
2. 结合用户的具体需求进行分析
3. 提供具体的建议和解决方案
4. 如果是关于动画效果的问题，请提供Manim相关的代码建议
5. 如果截图显示了问题，请明确指出问题所在

请基于截图和需求提供分析："""
        
        # 准备API调用 - 使用类似api_call.py的方式
        try:
            # 确保有有效的API密钥
            if not API_KEY:
                return jsonify({'success': False, 'error': '未配置API密钥，请检查Paper2Video/config.json文件'}), 500
            
            client = OpenAI(
                api_key=API_KEY,
                base_url=API_BASE_URL,
            )
            
            # 构建多模态消息内容
            content = [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_data}"
                    }
                }
            ]
            
            retry_count = 0
            response_content = None

            while retry_count < MAX_RETRIES:
                try:
                    response = client.chat.completions.create(
                        model=DEFAULT_MODEL or "gpt-4o",
                        messages=[
                            {
                                "role": "user",
                                "content": content
                            }
                        ],
                        max_tokens=3000,  # 增加token限制，因为需要处理图片
                        temperature=0.3
                    )
                    
                    if response.choices and response.choices[0].message:
                        response_content = response.choices[0].message.content
                    else:
                        response_content = f"错误：响应中未找到预期的'content'。响应: {response}"
                    break  # 成功，跳出重试循环

                except Exception as e:
                    retry_count += 1
                    print(f"多模态API调用错误 (尝试 {retry_count}/{MAX_RETRIES}): {e}")
                    if retry_count >= MAX_RETRIES:
                        response_content = f"错误：达到最大重试次数后API调用失败。最后错误: {e}"
                        break
                    print(f"等待 {5 * retry_count} 秒后重试...")
                    time.sleep(5 * retry_count)

            if response_content and (response_content.startswith("错误：") or response_content.startswith("API调用失败")):
                return jsonify({'success': False, 'error': response_content}), 500
            
            # 清理可能存在的markdown代码块标记
            if response_content:
                response_content = response_content.strip()
                if response_content.startswith("```python"):
                    response_content = response_content[9:]
                if response_content.startswith("```"):
                    response_content = response_content[3:]
                if response_content.endswith("```"):
                    response_content = response_content[:-3]
                response_content = response_content.strip()
            
            return jsonify({
                'success': True, 
                'feedback': response_content or "未能获取模型响应",
                'message': '多模态反馈完成'
            })
            
        except Exception as api_error:
            print(f"[ERROR] 多模态API调用失败: {str(api_error)}")
            return jsonify({'success': False, 'error': f'API调用失败: {str(api_error)}'}), 500
        
    except Exception as e:
        print(f"[ERROR] 多模态反馈处理失败: {str(e)}")
        return jsonify({'success': False, 'error': f'处理失败: {str(e)}'}), 500

@app.route('/save-code/<filename>', methods=['POST'])
def save_code(filename):
    try:
        if not request.json:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        content = request.json.get('content', '')
        
        # 确保文件名安全（只允许字母、数字、下划线、点和连字符）
        import re
        if not re.match(r'^[\w\.-]+\.py$', filename):
            return jsonify({'success': False, 'error': '无效的文件名'}), 400
        
        file_path = os.path.join(CODE_FOLDER, filename)
        
        # 确保文件路径在代码文件夹内
        abs_code_folder = os.path.abspath(CODE_FOLDER)
        abs_file_path = os.path.abspath(file_path)
        
        if not abs_file_path.startswith(abs_code_folder + os.sep) and abs_file_path != abs_code_folder:
            return jsonify({'success': False, 'error': '文件路径不在允许的目录内'}), 400
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({'success': True, 'message': '代码保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'保存失败: {str(e)}'}), 500

@app.route('/save-script/<filename>', methods=['POST'])
def save_script(filename):
    try:
        if not request.json:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        content = request.json.get('content', '')
        
        # 确保文件名安全（只允许字母、数字、下划线、点和连字符）
        import re
        if not re.match(r'^[\w\.-]+\.txt$', filename):
            return jsonify({'success': False, 'error': '无效的文件名'}), 400
        
        file_path = os.path.join(SCRIPT_FOLDER, filename)
        
        # 确保文件路径在讲稿文件夹内
        abs_script_folder = os.path.abspath(SCRIPT_FOLDER)
        abs_file_path = os.path.abspath(file_path)
        
        if not abs_file_path.startswith(abs_script_folder + os.sep) and abs_file_path != abs_script_folder:
            return jsonify({'success': False, 'error': '文件路径不在允许的目录内'}), 400
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({'success': True, 'message': '讲稿保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'保存失败: {str(e)}'}), 500

@app.route('/create-code/<lesson_title>', methods=['POST'])
def create_code(lesson_title):
    try:
        if not request.json:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        content = request.json.get('content', '# 新建代码文件\n\n')
        
        # 创建安全的文件名
        import re
        safe_filename = re.sub(r'[^\w\s-]', '', lesson_title.lower())
        safe_filename = re.sub(r'[-\s]+', '_', safe_filename)
        filename = f"{safe_filename}.py"
        
        file_path = os.path.join(CODE_FOLDER, filename)
        
        # 确保文件路径在代码文件夹内
        abs_code_folder = os.path.abspath(CODE_FOLDER)
        abs_file_path = os.path.abspath(file_path)
        
        if not abs_file_path.startswith(abs_code_folder + os.sep) and abs_file_path != abs_code_folder:
            return jsonify({'success': False, 'error': '文件路径不在允许的目录内'}), 400
        
        # 确保文件不存在
        if os.path.exists(file_path):
            return jsonify({'success': False, 'error': '文件已存在'}), 400
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({'success': True, 'message': '代码文件创建成功', 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': f'创建失败: {str(e)}'}), 500

@app.route('/create-script/<lesson_title>', methods=['POST'])
def create_script(lesson_title):
    try:
        if not request.json:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        content = request.json.get('content', '新建讲稿内容\n\n')
        
        # 创建安全的文件名
        import re
        safe_filename = re.sub(r'[^\w\s-]', '', lesson_title.lower())
        safe_filename = re.sub(r'[-\s]+', '_', safe_filename)
        filename = f"{safe_filename}.txt"
        
        file_path = os.path.join(SCRIPT_FOLDER, filename)
        
        # 确保文件路径在讲稿文件夹内
        abs_script_folder = os.path.abspath(SCRIPT_FOLDER)
        abs_file_path = os.path.abspath(file_path)
        
        if not abs_file_path.startswith(abs_script_folder + os.sep) and abs_file_path != abs_script_folder:
            return jsonify({'success': False, 'error': '文件路径不在允许的目录内'}), 400
        
        # 确保文件不存在
        if os.path.exists(file_path):
            return jsonify({'success': False, 'error': '文件已存在'}), 400
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({'success': True, 'message': '讲稿文件创建成功', 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': f'创建失败: {str(e)}'}), 500

@app.route('/save-screenshot', methods=['POST'])
def save_screenshot():
    try:
        if not request.json:
            return jsonify({'success': False, 'error': '无效的请求数据'}), 400
        
        # 获取base64图片数据和文件名
        image_data = request.json.get('imageData', '')
        filename = request.json.get('filename', '')
        
        # 调试信息
        print(f"[DEBUG] 接收到的原始文件名: '{filename}'")
        
        if not image_data or not filename:
            return jsonify({'success': False, 'error': '缺少图片数据或文件名'}), 400
        
        # URL解码文件名
        import urllib.parse
        filename = urllib.parse.unquote(filename)
        print(f"[DEBUG] URL解码后的文件名: '{filename}'")
        print(f"[DEBUG] PREVIEW_FOLDER: {PREVIEW_FOLDER}")
        
        # 移除base64头部信息
        if image_data.startswith('data:image/png;base64,'):
            image_data = image_data[22:]  # 移除 "data:image/png;base64," 
        
        # 确保文件名安全（允许更多字符，包括中文）
        import re
        # 更宽松的文件名验证：允许字母、数字、下划线、连字符、点、加号、中文字符
        if not re.match(r'^[a-zA-Z0-9_\-\+\u4e00-\u9fff\.]+\.png$', filename):
            print(f"[DEBUG] 文件名验证失败: '{filename}'")
            return jsonify({'success': False, 'error': f'无效的文件名: {filename}'}), 400
        
        # 使用传入的预览文件夹路径
        save_dir = PREVIEW_FOLDER
        
        # 确保目录存在（虽然在启动时已经创建，但这里再次确保）
        os.makedirs(save_dir, exist_ok=True)
        
        # 完整文件路径
        file_path = os.path.join(save_dir, filename)
        
        # 解码base64并保存文件
        try:
            image_bytes = base64.b64decode(image_data)
            with open(file_path, 'wb') as f:
                f.write(image_bytes)
        except Exception as decode_error:
            return jsonify({'success': False, 'error': f'图片解码失败: {str(decode_error)}'}), 500
        
        return jsonify({
            'success': True, 
            'message': f'截图已保存到 {file_path}',
            'filepath': file_path
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'保存失败: {str(e)}'}), 500

@app.route('/shutdown', methods=['POST'])
def shutdown():
    try:
        print("收到退出请求，正在关闭应用...")
        
        # 返回成功响应
        response = jsonify({'success': True, 'message': '应用程序正在退出'})
        
        # 在响应发送后异步关闭服务器
        def shutdown_server():
            time.sleep(0.5)  # 等待响应发送完成
            print("应用程序已退出")
            os._exit(0)  # 强制退出程序
        
        # 启动退出线程
        shutdown_thread = threading.Thread(target=shutdown_server)
        shutdown_thread.daemon = True
        shutdown_thread.start()
        
        return response
    except Exception as e:
        return jsonify({'success': False, 'error': f'退出失败: {str(e)}'}), 500

if __name__ == '__main__':
    print(f"视频文件夹: {VIDEO_FOLDER}")
    print(f"代码文件夹: {CODE_FOLDER}")
    print(f"讲稿文件夹: {SCRIPT_FOLDER}")
    print(f"预览图片文件夹: {PREVIEW_FOLDER}")
    print("服务启动在 http://0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080, debug=True) 