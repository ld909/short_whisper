#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Z-Library 电子书URL爬虫
支持断点续传、URL去重和自动翻页
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import os
import re
from urllib.parse import urljoin, urlparse
import json
from playwright.sync_api import sync_playwright
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('zlib_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ZLibraryCrawler:
    def __init__(self, base_url="https://zlib.fi/", output_file="book_url.txt"):
        self.base_url = base_url
        self.output_file = output_file
        self.progress_file = "crawler_progress.json"
        self.book_urls = set()
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
            'Upgrade-Insecure-Requests': '1',
        }
        
        # 加载已有的URL和进度
        self.load_existing_data()
    
    def setup_browser(self):
        """设置Playwright浏览器"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,  # 无头模式
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
            
            # 创建新的浏览器上下文，设置用户代理
            context = self.browser.new_context(
                user_agent=self.headers['User-Agent'],
                viewport={'width': 1920, 'height': 1080}
            )
            
            self.page = context.new_page()
            
            # 设置默认超时时间
            self.page.set_default_timeout(30000)  # 30秒
            
            logger.info("🌐 Playwright浏览器设置成功")
        except Exception as e:
            logger.error(f"❌ 设置Playwright浏览器失败: {e}")
            raise
    
    def load_existing_data(self):
        """加载已有的URL数据和爬取进度"""
        # 加载已保存的URL
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    existing_urls = f.read().strip().split('\n')
                    self.book_urls = set(url.strip() for url in existing_urls if url.strip())
                logger.info(f"📥 已加载 {len(self.book_urls)} 个现有URL")
            except Exception as e:
                logger.error(f"❌ 加载现有URL文件失败: {e}")
        
        # 加载爬取进度
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    self.progress = json.load(f)
                logger.info(f"📊 已加载爬取进度: {self.progress}")
            except Exception as e:
                logger.error(f"❌ 加载进度文件失败: {e}")
                self.progress = {"last_page": 0, "total_books": 0}
        else:
            self.progress = {"last_page": 0, "total_books": 0}
    
    def save_progress(self):
        """保存爬取进度"""
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ 保存进度失败: {e}")
    
    def save_urls(self):
        """保存URL到文件"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                for url in sorted(self.book_urls):
                    f.write(url + '\n')
            logger.info(f"💾 已保存 {len(self.book_urls)} 个URL到 {self.output_file}")
        except Exception as e:
            logger.error(f"❌ 保存URL文件失败: {e}")
    
    def extract_book_urls_from_page(self):
        """从当前页面提取电子书URL"""
        try:
            # 等待页面加载完成
            self.page.wait_for_selector("a", timeout=10000)
            
            # 获取页面源码
            content = self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # 查找电子书链接的多种可能选择器
            selectors = [
                'a[href*="/book/"]',  # 包含/book/的链接
                'a[href*="/download/"]',  # 包含/download/的链接
                '.book-item a',  # 书籍项目的链接
                '.book-title a',  # 书籍标题链接
                'h3 a',  # h3标签下的链接
                '.title a'  # 标题类的链接
            ]
            
            new_urls = set()
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href:
                        # 构建完整URL
                        full_url = urljoin(self.base_url, href)
                        
                        # 过滤有效的电子书URL
                        if self.is_valid_book_url(full_url):
                            new_urls.add(full_url)
            
            # 添加到主集合
            old_count = len(self.book_urls)
            self.book_urls.update(new_urls)
            new_count = len(self.book_urls) - old_count
            
            logger.info(f"🔍 本页新发现 {len(new_urls)} 个链接，去重后新增 {new_count} 个URL")
            return len(new_urls)
            
        except Exception as e:
            logger.error(f"❌ 提取页面URL失败: {e}")
            return 0
    
    def is_valid_book_url(self, url):
        """判断是否为有效的电子书URL"""
        if not url or url in self.book_urls:
            return False
        
        # 排除不相关的链接
        exclude_patterns = [
            '/user/', '/login', '/register', '/about', '/contact',
            '/terms', '/privacy', '/dmca', '/faq', '.css', '.js',
            '.png', '.jpg', '.gif', 'javascript:', 'mailto:'
        ]
        
        for pattern in exclude_patterns:
            if pattern in url.lower():
                return False
        
        # 只保留包含书籍相关路径的URL
        include_patterns = ['/book/', '/download/', '/author/', '/search']
        return any(pattern in url for pattern in include_patterns)
    
    def click_load_more(self):
        """点击Load More按钮"""
        try:
            # 多种可能的Load More按钮选择器
            load_more_selectors = [
                '.load-more',
                '#load-more',
                'button[onclick*="load"]',
                'a[onclick*="load"]',
                '.btn-load-more',
                '.load-btn'
            ]
            
            # 使用文本匹配的选择器
            text_selectors = [
                'text="Load more"',
                'text="更多"',
                'text="Load More"',
                'text="Show more"'
            ]
            
            # 先尝试CSS选择器
            for selector in load_more_selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element and element.is_visible() and element.is_enabled():
                        # 滚动到元素位置
                        element.scroll_into_view_if_needed()
                        time.sleep(1)
                        
                        # 点击元素
                        element.click()
                        logger.info(f"👆 成功点击Load More按钮 (选择器: {selector})")
                        
                        # 等待新内容加载
                        time.sleep(random.uniform(2, 4))
                        return True
                        
                except Exception:
                    continue
            
            # 再尝试文本匹配
            for text_selector in text_selectors:
                try:
                    element = self.page.query_selector(f'button:has-text("Load more"), a:has-text("Load more"), button:has-text("更多"), a:has-text("更多")')
                    if element and element.is_visible() and element.is_enabled():
                        # 滚动到元素位置
                        element.scroll_into_view_if_needed()
                        time.sleep(1)
                        
                        # 点击元素
                        element.click()
                        logger.info(f"👆 成功点击Load More按钮 (文本匹配)")
                        
                        # 等待新内容加载
                        time.sleep(random.uniform(2, 4))
                        return True
                        
                except Exception:
                    continue
            
            logger.info("ℹ️ 未找到Load More按钮，可能已加载所有内容")
            return False
            
        except Exception as e:
            logger.error(f"❌ 点击Load More按钮失败: {e}")
            return False
    
    def crawl(self, max_pages=50):
        """主爬取函数"""
        try:
            self.setup_browser()
            logger.info(f"🚀 开始爬取 Z-Library，最大页数: {max_pages}")
            
            # 访问主页
            self.page.goto(self.base_url)
            time.sleep(3)
            
            page_count = 0
            no_more_content_count = 0
            
            while page_count < max_pages:
                logger.info(f"⏳ 正在处理第 {page_count + 1} 页...")
                
                # 提取当前页面的URL
                urls_found = self.extract_book_urls_from_page()
                
                if urls_found == 0:
                    no_more_content_count += 1
                    if no_more_content_count >= 3:
                        logger.info("🔚 连续3次未发现新内容，可能已抓取完毕")
                        break
                else:
                    no_more_content_count = 0
                
                # 保存进度
                self.progress["last_page"] = page_count + 1
                self.progress["total_books"] = len(self.book_urls)
                self.save_progress()
                self.save_urls()
                
                # 尝试点击Load More
                if not self.click_load_more():
                    logger.info("⚠️ 无法继续加载更多内容")
                    break
                
                page_count += 1
                
                # 随机延迟避免被封
                time.sleep(random.uniform(1, 3))
            
            logger.info(f"🎉 爬取完成！总共收集到 {len(self.book_urls)} 个电子书URL")
            
        except Exception as e:
            logger.error(f"❌ 爬取过程中出现错误: {e}")
        finally:
            self.cleanup()
            self.save_urls()
            self.save_progress()
    
    def cleanup(self):
        """清理资源"""
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
    
    def resume_crawl(self, max_pages=50):
        """断点续传爬取"""
        start_page = self.progress.get("last_page", 0)
        logger.info(f"🔄 从第 {start_page + 1} 页开始继续爬取")
        self.crawl(max_pages)

def main():
    """主函数"""
    crawler = ZLibraryCrawler()
    
    print("🕷️ Z-Library 电子书URL爬虫")
    print("1. 🆕 全新开始爬取")
    print("2. 🔄 断点续传")
    
    choice = input("请选择模式 (1/2): ").strip()
    
    try:
        max_pages = int(input("请输入最大爬取页数 (默认50): ") or "50")
    except ValueError:
        max_pages = 50
    
    if choice == "2":
        crawler.resume_crawl(max_pages)
    else:
        crawler.crawl(max_pages)

if __name__ == "__main__":
    main() 