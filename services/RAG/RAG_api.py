from exa_py import Exa
import re

# 替换为你自己的 Exa API 密钥
EXA_API_KEY = '211ed197-9199-401d-9897-a8408526f8b8'
exa = Exa(EXA_API_KEY)

def main():
    """主函数，提供选择菜单"""
    print("="*50)
    print("          欢迎使用搜索工具")
    print("="*50)
    print("请选择搜索类型：")
    print("(1) 查找网页")
    print("(2) 查找论文")
    print("-"*50)
    
    while True:
        choice = input("请输入选择 (1/2): ").strip()
        if choice in ['1', '2']:
            break
        print("无效选择，请输入 1 或 2")
    
    # 获取查询关键词
    search_keyword = input("请输入要搜索的关键词: ")
    
    if choice == '1':
        search_web(search_keyword)
    else:
        search_papers(search_keyword)

def search_web(search_keyword):
    """搜索网页"""
    print(f"\n正在搜索网页: {search_keyword}")
    print("="*80)
    
    # 调用 search_and_contents 方法进行检索
    result = exa.search_and_contents(
        search_keyword,
        text=True
    )
    
    print(f"搜索结果：{search_keyword}相关网页 (共找到: {len(result.results)}个)")
    print("="*80)
    
    if not result.results:
        print("没有找到相关网页。")
    else:
        for idx, item in enumerate(result.results):
            print(f"\n🌐 网页 {idx+1}")
            print("-" * 60)
            
            # 提取并打印标题
            title = item.title if item.title else "[No Title]"
            print(f"标题: {title}")
            
            # 提取并打印URL
            url = item.url if item.url else "[No URL]"
            print(f"链接: {url}")
            
            # 提取并打印网页内容摘要（清理后显示更多内容）
            content = clean_web_content(item.text) if item.text else "[No Content]"
            if len(content) > 1000:
                content = content[:1000] + "..."
            print(f"内容: {content}")
            
            print("-" * 60)

def search_papers(search_keyword):
    """搜索论文"""
    query = f"site:arxiv.org/abs {search_keyword}"
    print(f"\n正在搜索论文: {search_keyword}")
    print(f"搜索查询: {query}")
    print("="*80)
    
    # 调用 search_and_contents 方法进行检索，并获取正文内容
    result = exa.search_and_contents(
        query,
        text=True
    )
    
    # 筛选结果
    print(f"原始搜索结果: {len(result.results)}篇")
    valid_results = []
    filtered_results = []
    
    for item in result.results:
        if is_valid_arxiv_url(item.url):
            valid_results.append(item)
        else:
            filtered_results.append(item)
    
    print(f"筛选后结果: {len(valid_results)}篇 (过滤掉: {len(filtered_results)}篇)")
    
    # 显示被过滤掉的URL，便于调试
    if filtered_results:
        print(f"\n被过滤的URL示例:")
        for i, item in enumerate(filtered_results[:3]):  # 只显示前3个
            print(f"  {i+1}. {item.url}")
    
    print(f"\n搜索结果：{search_keyword}相关论文")
    print("="*80)
    
    if not valid_results:
        print("没有找到符合条件的arxiv论文。")
    else:
        for idx, item in enumerate(valid_results):
            print(f"\n📄 论文 {idx+1}")
            print("-" * 60)
            
            # 提取并打印标题
            title = item.title if item.title else "[No Title]"
            print(f"标题: {title}")
            
            # 提取并打印URL
            url = item.url if item.url else "[No URL]"
            print(f"链接: {url}")
            
            # 提取并打印摘要
            abstract = extract_abstract(item.text)
            print(f"摘要: {abstract}")
            
            print("-" * 60)

def extract_abstract(text):
    """从文本中提取摘要 - 改进版本"""
    if not text:
        return "[No Abstract Found]"
    
    # 首先清理文本，移除常见的无关内容
    # 移除下载链接、作者信息等
    text = re.sub(r'Download PDF.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Authors?:\s*\[.*?\].*?(?=\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Submitted on.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Comments:.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Subjects:.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[.*?\]\(https?://.*?\)', '', text)  # 移除markdown链接
    
    # 针对arxiv论文格式的改进模式 - 直接排除"Abstract:"
    abstract_patterns = [
        # 匹配标准的Abstract部分，但排除"Abstract:"本身
        r'(?i)(?:^|\n)\s*abstract\s*:?\s*(.*?)(?=\n\s*(?:keywords?|introduction|1\.|references|related work|background|\n\s*[A-Z][a-z]+\s*:|\n\s*\d+\s+[A-Z])|$)',
        # 匹配markdown格式的Abstract标题，排除标题本身
        r'(?i)(?:^|\n)\s*#{1,6}\s*abstract\s*:?\s*(.*?)(?=\n\s*#{1,6}|\n\s*\d+\s+[A-Z]|$)',
        # 更宽泛的模式，匹配Abstract后面的内容
        r'(?i)abstract\s*:?\s*(.*?)(?=\n\s*(?:keywords?|introduction|1\.|references)|$)',
    ]
    
    for pattern in abstract_patterns:
        match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
        if match:
            abstract = match.group(1).strip()
            
            # 清理提取的摘要
            abstract = clean_abstract(abstract)
            
            # 检查摘要质量
            if is_valid_abstract(abstract):
                return abstract
    
    # 如果没有找到标准的Abstract，尝试更智能的提取
    # 寻找可能的摘要段落（通常在开头几段）
    paragraphs = text.split('\n\n')
    for i, paragraph in enumerate(paragraphs[:5]):  # 只检查前5段
        cleaned_para = clean_abstract(paragraph)
        if is_valid_abstract(cleaned_para) and len(cleaned_para) > 100:
            return cleaned_para
    
    return "[Abstract Not Found]"

def clean_web_content(content):
    """清理网页内容，移除无关元素"""
    if not content:
        return ""
    
    # 移除图片相关内容
    content = re.sub(r'!\[.*?\]\(.*?\)', '', content)  # markdown图片
    content = re.sub(r'<img[^>]*>', '', content, flags=re.IGNORECASE)  # HTML图片标签
    
    # 移除链接
    content = re.sub(r'\[.*?\]\(https?://[^\)]+\)', '', content)  # markdown链接
    content = re.sub(r'https?://[^\s]+', '', content)  # 直接的URL
    
    # 移除HTML标签
    content = re.sub(r'<[^>]+>', '', content)
    
    # 移除特殊符号和无意义的内容
    unwanted_patterns = [
        r'阅读量\d+[.\d]*[wk万千]?',  # 阅读量信息
        r'收藏\d+[.\d]*[wk万千]?',   # 收藏信息
        r'点赞\d+[.\d]*[wk万千]?',   # 点赞信息
        r'已于\s*\d{4}-\d{2}-\d{2}.*?修改',  # 修改时间
        r'![^!]*![^!]*',  # 连续的感叹号内容
        r'\s*原创\s*',  # 原创标记
        r'\s*转载\s*',  # 转载标记
        r'©.*?版权.*?',  # 版权信息
        r'版权声明.*?',  # 版权声明
        r'相关推荐.*?',  # 相关推荐
        r'猜你喜欢.*?',  # 推荐内容
        r'广告.*?',     # 广告内容
        r'登录.*?注册', # 登录注册提示
        r'订阅.*?关注', # 订阅关注
        r'分享.*?评论', # 分享评论
    ]
    
    for pattern in unwanted_patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)
    
    # 清理多余的空白字符
    content = re.sub(r'\n+', '\n', content)  # 多个换行合并为一个
    content = re.sub(r'\s+', ' ', content)   # 多个空格合并为一个
    content = re.sub(r'\s*\n\s*', ' ', content)  # 换行符周围的空格处理
    
    # 移除开头和结尾的特殊字符
    content = re.sub(r'^[^\w\u4e00-\u9fff]*', '', content)  # 移除开头非字母数字汉字
    content = re.sub(r'[^\w\u4e00-\u9fff.!?]*$', '', content)  # 移除结尾特殊字符
    
    # 去掉过短的片段（可能是无意义内容）
    sentences = content.split('。')
    meaningful_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 10:  # 只保留足够长的句子
            meaningful_sentences.append(sentence)
    
    if meaningful_sentences:
        content = '。'.join(meaningful_sentences)
        if not content.endswith('。') and not content.endswith('！') and not content.endswith('？'):
            content += '。'
    
    return content.strip()

def clean_abstract(abstract):
    """清理摘要文本"""
    if not abstract:
        return ""
    
    # 移除多余的空白字符
    abstract = re.sub(r'\n+', ' ', abstract)
    abstract = re.sub(r'\s+', ' ', abstract)
    abstract = abstract.strip()
    
    # 移除开头的"Abstract:"标记 - 使用最简单的方法
    # 先转为小写检查，但保持原文本进行替换
    abstract_lower = abstract.lower()
    if abstract_lower.startswith('abstract:'):
        abstract = abstract[9:].strip()  # 移除"abstract:"
    elif abstract_lower.startswith('abstract '):
        abstract = abstract[9:].strip()  # 移除"abstract "
    elif abstract_lower.startswith('abstract'):
        abstract = abstract[8:].strip()  # 移除"abstract"
    
    # 移除不应该出现在摘要中的内容
    unwanted_patterns = [
        r'Download PDF.*?(?=\s|$)',
        r'Authors?:\s*.*?(?=\s|$)',
        r'Submitted on.*?(?=\s|$)',
        r'Comments:.*?(?=\s|$)',
        r'Subjects:.*?(?=\s|$)',
        r'\[.*?\]\(https?://.*?\)',  # markdown链接
        r'https?://[^\s]+',  # 普通链接
        r'arXiv:\d+\.\d+',  # arXiv ID
        r'^\s*\d+\s*$',  # 纯数字行
    ]
    
    for pattern in unwanted_patterns:
        abstract = re.sub(pattern, '', abstract, flags=re.IGNORECASE)
    
    # 移除开头和结尾的特殊字符
    abstract = re.sub(r'^[^\w\s]*', '', abstract)
    abstract = re.sub(r'[^\w\s.!?]*$', '', abstract)
    
    return abstract.strip()

def is_valid_abstract(abstract):
    """检查是否是有效的摘要"""
    if not abstract or len(abstract) < 50:
        return False
    
    # 检查是否包含不应该出现在摘要中的内容
    invalid_indicators = [
        r'(?i)download\s+pdf',
        r'(?i)authors?:\s*\[',
        r'(?i)submitted\s+on',
        r'(?i)comments:',
        r'(?i)subjects:',
        r'(?i)^\s*\d+\s*$',  # 纯数字
        r'(?i)^\s*table\s+of\s+contents',
        r'(?i)^\s*references\s*$',
    ]
    
    for pattern in invalid_indicators:
        if re.search(pattern, abstract):
            return False
    
    # 检查是否包含足够的实际内容（至少包含一些完整的句子）
    sentences = re.split(r'[.!?]+', abstract)
    valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    return len(valid_sentences) >= 2

def is_valid_arxiv_url(url):
    """检查是否是有效的arxiv.org/abs/格式URL"""
    if not url:
        return False
    # 支持带版本号的URL格式，如 https://arxiv.org/abs/2402.01680v1
    return re.match(r'https://arxiv\.org/abs/\d+\.\d+(v\d+)?', url) is not None

if __name__ == "__main__":
    main()

