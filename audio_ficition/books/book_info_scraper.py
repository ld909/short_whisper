#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Z-Library 电子书信息抓取工具
支持断点续传、自动重试和智能错误处理
"""

import os
import json
import uuid
import time
import random
import platform
import logging
import argparse
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin, urlparse
from tqdm import tqdm

# 配置日志，但不保存到books文件夹
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/audio"
    else:  # 默认为Linux/Ubuntu
        return "/mnt/dhl/audio"


class BookInfoScraper:
    def __init__(self, urls_file="book_url.txt"):
        self.urls_file = urls_file
        self.base_media_path = get_base_media_path()
        self.base_path = os.path.join(self.base_media_path, "books", "en")
        
        # 设置目录结构
        self.thumbnails_dir = os.path.join(self.base_path, "thumbnails")
        self.info_dir = os.path.join(self.base_path, "info")
        self.uuid_mapping_file = os.path.join(self.base_path, "uuid_mapping.json")
        self.progress_file = os.path.join(self.base_path, "scraper_progress.json")
        
        # 创建目录
        self._create_directories()
        
        # 加载现有数据
        self.uuid_mapping = self._load_uuid_mapping()
        self.progress = self._load_progress()
        
        # Playwright 相关
        self.playwright = None
        self.browser = None
        self.page = None
        
        # 设置请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
    
    def _create_directories(self):
        """创建必要的目录结构"""
        for directory in [self.thumbnails_dir, self.info_dir]:
            Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 目录结构已创建: {self.base_path}")
    
    def _load_uuid_mapping(self):
        """加载UUID映射关系"""
        if os.path.exists(self.uuid_mapping_file):
            try:
                with open(self.uuid_mapping_file, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                logger.info(f"📥 已加载 {len(mapping)} 个URL-UUID映射")
                return mapping
            except Exception as e:
                logger.error(f"❌ 加载UUID映射失败: {e}")
        return {}
    
    def _save_uuid_mapping(self):
        """保存UUID映射关系"""
        try:
            with open(self.uuid_mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.uuid_mapping, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 已保存UUID映射: {len(self.uuid_mapping)} 条记录")
        except Exception as e:
            logger.error(f"❌ 保存UUID映射失败: {e}")
    
    def _load_progress(self):
        """加载爬取进度"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                logger.info(f"📊 已加载进度: 已处理 {progress.get('processed', 0)}/{progress.get('total', 0)} 个URL")
                return progress
            except Exception as e:
                logger.error(f"❌ 加载进度失败: {e}")
        return {"processed": 0, "total": 0, "failed": [], "completed": []}
    
    def _save_progress(self):
        """保存爬取进度"""
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ 保存进度失败: {e}")
    
    def _get_or_create_uuid(self, url):
        """获取或创建URL对应的UUID"""
        if url in self.uuid_mapping:
            return self.uuid_mapping[url]
        
        book_uuid = str(uuid.uuid4())
        self.uuid_mapping[url] = book_uuid
        return book_uuid
    
    def setup_browser(self):
        """设置Playwright浏览器"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
            
            context = self.browser.new_context(
                user_agent=self.headers['User-Agent'],
                viewport={'width': 1920, 'height': 1080}
            )
            
            self.page = context.new_page()
            self.page.set_default_timeout(60000)  # 60秒
            
            logger.info("🌐 浏览器已准备就绪")
        except Exception as e:
            logger.error(f"❌ 设置浏览器失败: {e}")
            raise
    
    def cleanup(self):
        """清理浏览器资源"""
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("🧹 浏览器资源已清理")
        except Exception as e:
            logger.error(f"❌ 清理资源时出错: {e}")
    
    def download_cover_image(self, image_url, save_path, max_retries=3):
        """下载封面图片 - 改进版，处理防盗链和各种错误"""
        for attempt in range(max_retries):
            try:
                logger.info(f"🖼️ 尝试下载封面 (第{attempt + 1}次): {image_url}")
                
                # 使用不同的headers策略
                download_headers = self.headers.copy()
                if attempt == 1:
                    # 第二次尝试，模拟从页面访问
                    download_headers['Referer'] = image_url.split('/')[0] + '//' + image_url.split('/')[2]
                elif attempt == 2:
                    # 第三次尝试，更换User-Agent
                    download_headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                
                response = requests.get(
                    image_url, 
                    headers=download_headers, 
                    timeout=30,
                    stream=True,
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # 检查响应内容类型
                content_type = response.headers.get('content-type', '').lower()
                if not any(img_type in content_type for img_type in ['image', 'jpeg', 'png', 'webp', 'gif']):
                    logger.warning(f"⚠️ 疑似非图片内容: {content_type}")
                    if attempt < max_retries - 1:
                        continue
                
                # 检查文件大小
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) < 1000:  # 小于1KB可能是占位符
                    logger.warning(f"⚠️ 文件太小 ({content_length} bytes)，可能是占位符")
                    if attempt < max_retries - 1:
                        continue
                
                # 保存文件
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # 验证保存的文件
                if os.path.exists(save_path) and os.path.getsize(save_path) > 1000:
                    logger.info(f"✅ 封面已保存: {os.path.basename(save_path)} ({os.path.getsize(save_path)} bytes)")
                    return True
                else:
                    logger.warning(f"⚠️ 保存的文件太小或不存在")
                    if os.path.exists(save_path):
                        os.remove(save_path)
                    if attempt < max_retries - 1:
                        continue
                
            except Exception as e:
                logger.warning(f"⚠️ 第{attempt + 1}次下载失败: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # 等待2秒后重试
                    continue
        
        logger.error(f"❌ 所有下载尝试失败: {image_url}")
        return False
    
    def extract_book_info(self, url, max_retries=3):
        """从页面提取电子书信息"""
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 尝试访问页面 (第{attempt + 1}次): {url}")
                
                # 访问页面，使用多种等待策略
                self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
                
                # 等待网络空闲
                try:
                    self.page.wait_for_load_state('networkidle', timeout=30000)
                except:
                    logger.warning("⚠️ 网络空闲等待超时，继续处理...")
                
                # 等待关键元素出现（标题或内容）
                try:
                    self.page.wait_for_selector('h1, .book-title, [data-testid="title"], .title', timeout=20000)
                except:
                    logger.warning("⚠️ 关键元素等待超时，继续处理...")
                
                # 额外等待确保异步内容加载
                time.sleep(random.uniform(3, 6))
                
                break  # 成功访问，跳出重试循环
                
            except Exception as e:
                logger.warning(f"⚠️ 第{attempt + 1}次访问失败: {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5  # 递增等待时间
                    logger.info(f"⏳ 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ 所有重试失败，跳过此URL: {url}")
                    return None
        
        try:
            book_info = {
                'url': url,
                'title': '',
                'author': '',
                'description': '',
                'publication_year': '',
                'cover_url': '',
                'extracted_at': time.time()
            }
            
            # 提取标题
            title_selectors = [
                'h1',
                '.book-title',
                '[data-testid="title"]',
                '.title',
                'h2'
            ]
            
            for selector in title_selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element and element.text_content().strip():
                        book_info['title'] = element.text_content().strip()
                        break
                except:
                    continue
            
            # 提取作者 - 根据参考网页，作者可能在多个位置
            author_selectors = [
                'a[href*="/author/"]',
                '.author',
                '[data-testid="author"]',
                '.book-author',
                'span:has-text("作者")',
                'div:has-text("Author")'
            ]
            
            for selector in author_selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element and element.text_content().strip():
                        author_text = element.text_content().strip()
                        # 清理作者文本
                        if '作者' in author_text:
                            author_text = author_text.replace('作者:', '').replace('作者：', '').strip()
                        if 'Author' in author_text:
                            author_text = author_text.replace('Author:', '').replace('Author：', '').strip()
                        book_info['author'] = author_text
                        break
                except:
                    continue
            
            # 提取描述/简介 - 专门等待bookDescriptionBox元素
            try:
                # 首先尝试等待bookDescriptionBox元素加载
                logger.info("🔍 等待描述元素加载...")
                desc_element = self.page.wait_for_selector('#bookDescriptionBox', timeout=15000)
                if desc_element:
                    desc_text = desc_element.text_content().strip()
                    if desc_text and len(desc_text) > 20:
                        # 清理文本，移除多余的空白字符
                        desc_text = ' '.join(desc_text.split())
                        book_info['description'] = desc_text[:800]  # 增加长度限制
                        logger.info(f"✅ 成功提取描述: {len(desc_text)} 字符")
                    else:
                        logger.warning("⚠️ bookDescriptionBox元素存在但内容为空")
                else:
                    logger.warning("⚠️ 未找到bookDescriptionBox元素")
            except Exception as e:
                logger.warning(f"⚠️ 等待bookDescriptionBox失败: {e}")
            
            # 如果上面没有成功，尝试其他选择器
            if not book_info.get('description'):
                description_selectors = [
                    '.book-description',
                    '.description',
                    '[data-testid="description"]',
                    '.summary',
                    '.book-summary',
                    'p:has-text("描述")',
                    'div:has-text("简介")'
                ]
                
                for selector in description_selectors:
                    try:
                        element = self.page.query_selector(selector)
                        if element and element.text_content().strip():
                            desc_text = element.text_content().strip()
                            if len(desc_text) > 50:  # 确保是有意义的描述
                                desc_text = ' '.join(desc_text.split())  # 清理空白字符
                                book_info['description'] = desc_text[:800]  # 增加长度限制
                                logger.info(f"✅ 备用选择器成功提取描述: {selector}")
                                break
                    except:
                        continue
            
            # 提取出版年份
            year_selectors = [
                '.publication-year',
                '.year',
                '[data-testid="year"]',
                'span:has-text("年")',
                'div:has-text("Year")'
            ]
            
            for selector in year_selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element:
                        year_text = element.text_content().strip()
                        # 提取4位数字年份
                        import re
                        year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
                        if year_match:
                            book_info['publication_year'] = year_match.group()
                            break
                except:
                    continue
            
            # 提取封面图片URL - 改进版，处理动态加载和防盗链
            logger.info("🖼️ 开始提取封面图片...")
            
            # 等待图片加载完成
            try:
                self.page.wait_for_load_state('networkidle', timeout=10000)
            except:
                pass
            
            cover_found = False
            cover_selectors = [
                'img[src*="cover"]',
                'img[alt*="cover"]', 
                '.book-cover img',
                '.cover img',
                'img[src*="book"]',
                'img[alt*="book"]',
                'img[class*="cover"]',
                'img[class*="book"]',
                '.bookcover img',
                '#bookcover img'
            ]
            
            for selector in cover_selectors:
                try:
                    elements = self.page.query_selector_all(selector)
                    for element in elements:
                        # 检查多个可能的属性
                        for attr in ['src', 'data-src', 'data-lazy-src', 'data-original']:
                            cover_src = element.get_attribute(attr)
                            if cover_src and cover_src.strip():
                                # 过滤掉明显的占位符和无效URL
                                if not any(placeholder in cover_src.lower() for placeholder in [
                                    'placeholder', 'loading', 'blank', 'default', 'no-image', 
                                    'data:image', 'base64', '1x1', 'pixel'
                                ]):
                                    # 构建完整的图片URL
                                    if cover_src.startswith('//'):
                                        cover_src = 'https:' + cover_src
                                    elif cover_src.startswith('/'):
                                        base_url = f"https://{urlparse(url).netloc}"
                                        cover_src = urljoin(base_url, cover_src)
                                    
                                    # 验证URL格式
                                    if cover_src.startswith('http') and any(ext in cover_src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                                        book_info['cover_url'] = cover_src
                                        logger.info(f"✅ 找到封面URL: {cover_src}")
                                        cover_found = True
                                        break
                        
                        if cover_found:
                            break
                    
                    if cover_found:
                        break
                        
                except Exception as e:
                    logger.warning(f"⚠️ 选择器 {selector} 失败: {e}")
                    continue
            
            if not cover_found:
                logger.warning("⚠️ 未找到有效的封面图片URL")
            
            return book_info
            
        except Exception as e:
            logger.error(f"❌ 提取书籍信息失败: {e}")
            return None
    
    def process_book(self, url):
        """处理单本电子书"""
        try:
            # 获取UUID
            book_uuid = self._get_or_create_uuid(url)
            
            # 检查是否已处理
            info_file = os.path.join(self.info_dir, f"{book_uuid}.json")
            if os.path.exists(info_file):
                logger.info(f"⏭️ 书籍已处理，跳过: {book_uuid}")
                return True
            
            logger.info(f"📖 正在处理: {url}")
            
            # 提取书籍信息
            book_info = self.extract_book_info(url)
            if not book_info:
                return False
            
            # 添加UUID到信息中
            book_info['uuid'] = book_uuid
            
            # 下载封面图片
            if book_info.get('cover_url'):
                cover_path = os.path.join(self.thumbnails_dir, f"{book_uuid}.png")
                if self.download_cover_image(book_info['cover_url'], cover_path):
                    book_info['cover_path'] = cover_path
            
            # 保存书籍信息
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(book_info, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 书籍信息已保存: {book_info.get('title', 'Unknown Title')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 处理书籍失败 {url}: {e}")
            return False
    
    def load_urls(self):
        """加载URL列表"""
        try:
            with open(self.urls_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            logger.info(f"📚 已加载 {len(urls)} 个书籍URL")
            return urls
        except Exception as e:
            logger.error(f"❌ 加载URL文件失败: {e}")
            return []
    
    def scrape_all_books(self, max_books=None, resume=True):
        """批量抓取所有书籍信息"""
        try:
            # 加载URL列表
            urls = self.load_urls()
            if not urls:
                logger.error("❌ 未找到任何URL")
                return
            
            # 限制处理数量
            if max_books:
                urls = urls[:max_books]
            
            # 更新总数
            self.progress['total'] = len(urls)
            
            # 断点续传：跳过已处理的URL
            if resume:
                completed_urls = set(self.progress.get('completed', []))
                urls = [url for url in urls if url not in completed_urls]
                logger.info(f"🔄 断点续传: 跳过已完成的 {len(completed_urls)} 个URL，剩余 {len(urls)} 个")
            
            if not urls:
                logger.info("🎉 所有书籍已处理完成！")
                return
            
            # 设置浏览器
            self.setup_browser()
            
            logger.info(f"🚀 开始抓取 {len(urls)} 本电子书信息...")
            
            success_count = 0
            failed_count = 0
            
            # 使用进度条处理
            for i, url in enumerate(tqdm(urls, desc="📖 抓取进度")):
                try:
                    if self.process_book(url):
                        success_count += 1
                        self.progress['completed'].append(url)
                    else:
                        failed_count += 1
                        self.progress['failed'].append(url)
                    
                    # 更新进度
                    self.progress['processed'] = len(self.progress['completed']) + len(self.progress['failed'])
                    
                    # 定期保存进度和UUID映射
                    if (i + 1) % 10 == 0:
                        self._save_progress()
                        self._save_uuid_mapping()
                        logger.info(f"💾 进度已保存: {self.progress['processed']}/{self.progress['total']}")
                    
                    # 随机延迟避免被封
                    time.sleep(random.uniform(1, 3))
                    
                except KeyboardInterrupt:
                    logger.info("⏹️ 用户中断，正在保存进度...")
                    break
                except Exception as e:
                    logger.error(f"❌ 处理URL时出错 {url}: {e}")
                    failed_count += 1
                    self.progress['failed'].append(url)
            
            # 最终统计
            logger.info(f"🎯 抓取完成!")
            logger.info(f"✅ 成功: {success_count} 本")
            logger.info(f"❌ 失败: {failed_count} 本")
            logger.info(f"📊 总进度: {self.progress['processed']}/{self.progress['total']}")
            
        except Exception as e:
            logger.error(f"❌ 批量抓取出错: {e}")
        finally:
            # 保存最终状态
            self._save_progress()
            self._save_uuid_mapping()
            self.cleanup()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="📚 Z-Library 电子书信息抓取工具")
    parser.add_argument('-f', '--file', default='book_url.txt', help='URL文件路径')
    parser.add_argument('-m', '--max', type=int, help='最大处理数量')
    parser.add_argument('-r', '--resume', action='store_true', default=True, help='断点续传')
    parser.add_argument('--no-resume', action='store_false', dest='resume', help='重新开始')
    
    args = parser.parse_args()
    
    print("🕷️ Z-Library 电子书信息抓取工具")
    print(f"📁 媒体路径: {get_base_media_path()}")
    print(f"📄 URL文件: {args.file}")
    
    if args.max:
        print(f"🔢 限制数量: {args.max}")
    
    if args.resume:
        print("🔄 模式: 断点续传")
    else:
        print("🆕 模式: 重新开始")
    
    try:
        scraper = BookInfoScraper(args.file)
        scraper.scrape_all_books(max_books=args.max, resume=args.resume)
    except KeyboardInterrupt:
        print("👋 程序已停止")
    except Exception as e:
        print(f"❌ 程序出错: {e}")


if __name__ == "__main__":
    main()