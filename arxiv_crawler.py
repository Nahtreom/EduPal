#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arxiv爬虫程序
用于搜索和下载arxiv上的PDF文档
"""

import os
import time
import requests
import arxiv
import urllib.parse
from datetime import datetime
from typing import List, Dict, Optional
import argparse
import json
import logging
from pathlib import Path
import re

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arxiv_crawler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ArxivCrawler:
    """Arxiv爬虫类"""
    
    def __init__(self, download_dir: str = "./arxiv_papers"):
        """
        初始化爬虫
        
        Args:
            download_dir: 下载目录
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 设置连接池和重试策略
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 创建元数据文件
        self.metadata_file = self.download_dir / "metadata.json"
        self.downloaded_papers = self.load_metadata()
        
    def load_metadata(self) -> Dict:
        """加载已下载论文的元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载元数据失败: {e}")
                return {}
        return {}
    
    def save_metadata(self):
        """保存元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.downloaded_papers, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存元数据失败: {e}")
    
    def sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符"""
        # 移除非法字符
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # 限制长度
        if len(filename) > 100:
            filename = filename[:100]
        return filename.strip()
    
    def search_papers(self, query: str, max_results: int = 10, 
                     sort_by: arxiv.SortCriterion = arxiv.SortCriterion.SubmittedDate,
                     sort_order: arxiv.SortOrder = arxiv.SortOrder.Descending) -> List[arxiv.Result]:
        """
        搜索论文
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数
            sort_by: 排序方式
            sort_order: 排序顺序
            
        Returns:
            搜索结果列表
        """
        try:
            logger.info(f"搜索论文: {query}")
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            results = []
            for result in search.results():
                results.append(result)
                
            logger.info(f"找到 {len(results)} 篇论文")
            return results
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []
    
    def download_paper(self, paper: arxiv.Result, max_retries: int = 3) -> bool:
        """
        下载单篇论文
        
        Args:
            paper: 论文对象
            max_retries: 最大重试次数
            
        Returns:
            是否下载成功
        """
        try:
            # 检查是否已经下载
            paper_id = paper.entry_id.split('/')[-1]
            if paper_id in self.downloaded_papers:
                logger.info(f"论文 {paper_id} 已存在，跳过下载")
                return True
            
            # 生成文件名
            title = self.sanitize_filename(paper.title)
            filename = f"{paper_id}_{title}.pdf"
            filepath = self.download_dir / filename
            
            # 下载PDF
            for attempt in range(max_retries):
                try:
                    logger.info(f"正在下载: {paper.title}")
                    logger.info(f"PDF链接: {paper.pdf_url}")
                    
                    response = self.session.get(paper.pdf_url, timeout=120, stream=True)
                    response.raise_for_status()
                    
                    # 保存文件 (流式下载)
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded_size = 0
                    last_progress = 0
                    
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded_size += len(chunk)
                                if total_size > 0:
                                    progress = (downloaded_size / total_size) * 100
                                    # 每25%显示一次进度
                                    if progress - last_progress >= 25:
                                        logger.info(f"下载进度: {progress:.1f}%")
                                        last_progress = progress
                    
                    logger.info(f"下载完成，文件大小: {downloaded_size} bytes")
                    
                    # 保存元数据
                    self.downloaded_papers[paper_id] = {
                        'title': paper.title,
                        'authors': [author.name for author in paper.authors],
                        'published': paper.published.isoformat(),
                        'updated': paper.updated.isoformat(),
                        'summary': paper.summary,
                        'categories': paper.categories,
                        'pdf_url': paper.pdf_url,
                        'entry_id': paper.entry_id,
                        'filename': filename,
                        'download_time': datetime.now().isoformat(),
                        'file_size': os.path.getsize(filepath)
                    }
                    
                    self.save_metadata()
                    logger.info(f"成功下载: {filename}")
                    return True
                    
                except requests.exceptions.RequestException as e:
                    logger.warning(f"下载失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 10)  # 指数退避，最大等待10秒
                        logger.info(f"等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"多次重试后仍然失败: {paper.title}")
                        return False
                        
        except Exception as e:
            logger.error(f"下载论文时发生错误: {e}")
            return False
    
    def download_by_query(self, query: str, max_results: int = 10, 
                         delay: float = 1.0) -> Dict:
        """
        根据查询关键词下载论文
        
        Args:
            query: 搜索关键词
            max_results: 最大下载数量
            delay: 下载间隔（秒）
            
        Returns:
            下载统计信息
        """
        results = self.search_papers(query, max_results)
        
        stats = {
            'total_found': len(results),
            'downloaded': 0,
            'skipped': 0,
            'failed': 0
        }
        
        for i, paper in enumerate(results, 1):
            logger.info(f"处理论文 {i}/{len(results)}")
            
            paper_id = paper.entry_id.split('/')[-1]
            if paper_id in self.downloaded_papers:
                stats['skipped'] += 1
                continue
                
            if self.download_paper(paper):
                stats['downloaded'] += 1
            else:
                stats['failed'] += 1
                
            # 避免过于频繁的请求
            if i < len(results):
                time.sleep(delay)
        
        return stats
    
    def download_by_ids(self, paper_ids: List[str], delay: float = 1.0) -> Dict:
        """
        根据论文ID列表下载论文
        
        Args:
            paper_ids: 论文ID列表
            delay: 下载间隔（秒）
            
        Returns:
            下载统计信息
        """
        stats = {
            'total_requested': len(paper_ids),
            'downloaded': 0,
            'skipped': 0,
            'failed': 0
        }
        
        for i, paper_id in enumerate(paper_ids, 1):
            try:
                logger.info(f"处理论文 {i}/{len(paper_ids)}: {paper_id}")
                
                if paper_id in self.downloaded_papers:
                    stats['skipped'] += 1
                    continue
                
                # 通过ID搜索论文
                search = arxiv.Search(id_list=[paper_id])
                paper = next(search.results())
                
                if self.download_paper(paper):
                    stats['downloaded'] += 1
                else:
                    stats['failed'] += 1
                    
            except Exception as e:
                logger.error(f"处理论文 {paper_id} 时发生错误: {e}")
                stats['failed'] += 1
            
            # 避免过于频繁的请求
            if i < len(paper_ids):
                time.sleep(delay)
        
        return stats
    
    def list_downloaded_papers(self) -> List[Dict]:
        """列出已下载的论文"""
        return list(self.downloaded_papers.values())
    
    def search_downloaded_papers(self, keyword: str) -> List[Dict]:
        """在已下载的论文中搜索"""
        results = []
        keyword_lower = keyword.lower()
        
        for paper_data in self.downloaded_papers.values():
            if (keyword_lower in paper_data['title'].lower() or
                keyword_lower in paper_data['summary'].lower() or
                any(keyword_lower in author.lower() for author in paper_data['authors'])):
                results.append(paper_data)
        
        return results
    
    def get_stats(self) -> Dict:
        """获取下载统计信息"""
        total_papers = len(self.downloaded_papers)
        total_size = sum(paper['file_size'] for paper in self.downloaded_papers.values())
        
        categories = {}
        for paper in self.downloaded_papers.values():
            for category in paper['categories']:
                categories[category] = categories.get(category, 0) + 1
        
        return {
            'total_papers': total_papers,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'categories': categories,
            'download_dir': str(self.download_dir)
        }
    
    def test_connection(self) -> bool:
        """测试与arxiv的连接"""
        try:
            logger.info("测试与arxiv的连接...")
            
            # 测试搜索API
            test_search = arxiv.Search(query="test", max_results=1)
            test_result = next(test_search.results())
            logger.info(f"API连接正常，测试论文: {test_result.title}")
            
            # 测试PDF下载
            test_response = self.session.head(test_result.pdf_url, timeout=30)
            if test_response.status_code == 200:
                logger.info("PDF下载服务正常")
                return True
            else:
                logger.warning(f"PDF下载测试失败，状态码: {test_response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Arxiv爬虫程序')
    parser.add_argument('--query', '-q', type=str, help='搜索关键词')
    parser.add_argument('--ids', '-i', nargs='+', help='论文ID列表')
    parser.add_argument('--max-results', '-m', type=int, default=10, help='最大结果数')
    parser.add_argument('--download-dir', '-d', type=str, default='./arxiv_papers', help='下载目录')
    parser.add_argument('--delay', type=float, default=1.0, help='下载间隔（秒）')
    parser.add_argument('--list', '-l', action='store_true', help='列出已下载的论文')
    parser.add_argument('--stats', '-s', action='store_true', help='显示统计信息')
    parser.add_argument('--search-local', type=str, help='在本地已下载论文中搜索')
    parser.add_argument('--test', '-t', action='store_true', help='测试与arxiv的连接')
    
    args = parser.parse_args()
    
    # 创建爬虫实例
    crawler = ArxivCrawler(args.download_dir)
    
    if args.list:
        # 列出已下载的论文
        papers = crawler.list_downloaded_papers()
        print(f"\n已下载论文数量: {len(papers)}")
        print("=" * 50)
        for paper in papers:
            print(f"标题: {paper['title']}")
            print(f"作者: {', '.join(paper['authors'])}")
            print(f"发表时间: {paper['published']}")
            print(f"文件名: {paper['filename']}")
            print("-" * 50)
    
    elif args.stats:
        # 显示统计信息
        stats = crawler.get_stats()
        print(f"\n下载统计信息:")
        print(f"总论文数: {stats['total_papers']}")
        print(f"总大小: {stats['total_size_mb']} MB")
        print(f"下载目录: {stats['download_dir']}")
        print("\n分类统计:")
        for category, count in sorted(stats['categories'].items()):
            print(f"  {category}: {count}")
    
    elif args.search_local:
        # 在本地搜索
        results = crawler.search_downloaded_papers(args.search_local)
        print(f"\n本地搜索结果 (关键词: {args.search_local}):")
        print(f"找到 {len(results)} 篇论文")
        print("=" * 50)
        for paper in results:
            print(f"标题: {paper['title']}")
            print(f"作者: {', '.join(paper['authors'])}")
            print(f"文件名: {paper['filename']}")
            print("-" * 50)
    
    elif args.test:
        # 测试连接
        print("正在测试与arxiv的连接...")
        if crawler.test_connection():
            print("✅ 连接测试成功！可以正常下载论文。")
        else:
            print("❌ 连接测试失败！可能存在网络问题。")
            print("建议：")
            print("1. 检查网络连接")
            print("2. 稍后再试")
            print("3. 使用更长的延迟时间 (--delay 参数)")
            print("4. 检查防火墙设置")
    
    elif args.query:
        # 根据关键词搜索并下载
        print(f"搜索关键词: {args.query}")
        print(f"最大结果数: {args.max_results}")
        print(f"下载目录: {args.download_dir}")
        
        stats = crawler.download_by_query(args.query, args.max_results, args.delay)
        
        print(f"\n下载完成!")
        print(f"找到论文: {stats['total_found']}")
        print(f"成功下载: {stats['downloaded']}")
        print(f"已存在跳过: {stats['skipped']}")
        print(f"下载失败: {stats['failed']}")
    
    elif args.ids:
        # 根据ID列表下载
        print(f"下载论文ID: {args.ids}")
        print(f"下载目录: {args.download_dir}")
        
        stats = crawler.download_by_ids(args.ids, args.delay)
        
        print(f"\n下载完成!")
        print(f"请求下载: {stats['total_requested']}")
        print(f"成功下载: {stats['downloaded']}")
        print(f"已存在跳过: {stats['skipped']}")
        print(f"下载失败: {stats['failed']}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 