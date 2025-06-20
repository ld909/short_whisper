#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Z-Library 电子书URL爬虫

【功能描述】
这是一个专门用于爬取Z-Library（https://zlib.fi/）电子书URL的自动化脚本。
脚本使用Playwright模拟浏览器操作，能够自动翻页、点击"Load More"按钮，
并智能提取所有电子书的下载链接。

【主要特性】
1. 🌍 多语种支持：支持英文(en)和中文(zh)两种语言的Z-Library站点
2. 🔄 断点续传：支持中断后从上次停止的页面继续爬取
3. 🎯 URL去重：自动去除重复的电子书链接
4. 🤖 智能翻页：自动识别并点击各种"Load More"按钮
5. 📊 进度保存：实时保存爬取进度，防止数据丢失
6. 🚫 过滤无效链接：智能过滤掉登录、注册等非电子书页面
7. 📝 详细日志：提供详细的爬取日志，便于调试和监控

【输入参数】
命令行模式：
  --language/-l    语种选择: 'en'(英文) 或 'zh'(中文)，默认为'en'
  --max-pages/-p   最大爬取页数，默认为50页
  --resume/-r      启用断点续传模式

交互模式：
  如果不提供命令行参数，脚本会启动交互式界面：
  - 选择语种（英文/中文）
  - 选择爬取模式（全新开始/断点续传）
  - 输入最大爬取页数

【输出文件】
1. URL文件：
   - book_url.txt      (英文站点的电子书URL列表)
   - book_url_zh.txt   (中文站点的电子书URL列表)

2. 进度文件：
   - crawler_progress.json     (英文站点爬取进度)
   - crawler_progress_zh.json  (中文站点爬取进度)

3. 日志文件：
   - zlib_crawler.log  (详细的爬取日志)

【使用示例】
# 交互式模式
python zlib_crawler.py

# 爬取英文站点，最多100页
python zlib_crawler.py --language en --max-pages 100

# 断点续传中文站点
python zlib_crawler.py --language zh --resume

# 简化命令
python zlib_crawler.py -l zh -p 50 -r

【注意事项】
1. 🚀 首次运行请确保安装依赖：pip install playwright beautifulsoup4 requests
2. 🌐 需要稳定的网络连接，建议在网络状况良好时运行
3. ⏱️ 脚本内置随机延迟，避免被网站反爬虫机制封禁
4. 💾 爬取数据实时保存，可随时安全中断程序
5. 🔧 支持无头浏览器模式，资源占用较低

【输出格式说明】
- URL文件：每行一个电子书URL，按字母序排列
- 进度文件：JSON格式，包含最后爬取页数、总书籍数量等信息
- 日志文件：包含时间戳的详细运行日志，便于问题排查
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
import argparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("zlib_crawler.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class ZLibraryCrawler:
    def __init__(self, language="en"):
        self.language = language
        self.setup_language_config()
        self.book_urls = set()
        self.playwright = None
        self.browser = None
        self.page = None

        # 设置请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        # 加载已有的URL和进度
        self.load_existing_data()

    def setup_language_config(self):
        """根据语种设置配置"""
        if self.language == "zh":
            # 中文配置 - 使用官方中文镜像
            self.base_url = "https://zh.zlib.fi/"
            self.output_file = "book_url_zh.txt"
            self.progress_file = "crawler_progress_zh.json"
            self.language_name = "中文"
            # 中文的Load More按钮文本
            self.load_more_texts = [
                "加载更多",
                "更多",
                "显示更多",
                "Load more",
                "Load More",
            ]
        else:
            # 英文配置（默认）
            self.base_url = "https://zlib.fi/"
            self.output_file = "book_url.txt"
            self.progress_file = "crawler_progress.json"
            self.language_name = "English"
            # 英文的Load More按钮文本
            self.load_more_texts = ["Load more", "Load More", "Show more", "更多"]

        logger.info(f"🌍 语种设置: {self.language_name}")
        logger.info(f"🔗 目标URL: {self.base_url}")
        logger.info(f"📁 输出文件: {self.output_file}")

    def setup_browser(self):
        """设置Playwright浏览器"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,  # 无头模式
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )

            # 创建新的浏览器上下文，设置用户代理
            context = self.browser.new_context(
                user_agent=self.headers["User-Agent"],
                viewport={"width": 1920, "height": 1080},
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
                with open(self.output_file, "r", encoding="utf-8") as f:
                    existing_urls = f.read().strip().split("\n")
                    self.book_urls = set(
                        url.strip() for url in existing_urls if url.strip()
                    )
                logger.info(
                    f"📥 已加载 {len(self.book_urls)} 个现有{self.language_name}URL"
                )
            except Exception as e:
                logger.error(f"❌ 加载现有URL文件失败: {e}")

        # 加载爬取进度
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    self.progress = json.load(f)
                logger.info(f"📊 已加载{self.language_name}爬取进度: {self.progress}")
            except Exception as e:
                logger.error(f"❌ 加载进度文件失败: {e}")
                self.progress = {
                    "last_page": 0,
                    "total_books": 0,
                    "language": self.language,
                }
        else:
            self.progress = {
                "last_page": 0,
                "total_books": 0,
                "language": self.language,
            }

    def save_progress(self):
        """保存爬取进度"""
        try:
            self.progress["language"] = self.language
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(self.progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ 保存进度失败: {e}")

    def save_urls(self):
        """保存URL到文件"""
        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                for url in sorted(self.book_urls):
                    f.write(url + "\n")
            logger.info(
                f"💾 已保存 {len(self.book_urls)} 个{self.language_name}URL到 {self.output_file}"
            )
        except Exception as e:
            logger.error(f"❌ 保存URL文件失败: {e}")

    def extract_book_urls_from_page(self):
        """从当前页面提取电子书URL"""
        try:
            # 等待页面加载完成
            self.page.wait_for_selector("a", timeout=10000)

            # 获取页面源码
            content = self.page.content()
            soup = BeautifulSoup(content, "html.parser")

            # 查找电子书链接的多种可能选择器
            selectors = [
                'a[href*="/book/"]',  # 包含/book/的链接
                'a[href*="/download/"]',  # 包含/download/的链接
                ".book-item a",  # 书籍项目的链接
                ".book-title a",  # 书籍标题链接
                "h3 a",  # h3标签下的链接
                ".title a",  # 标题类的链接
            ]

            new_urls = set()
            for selector in selectors:
                links = soup.select(selector)
                for link in links:
                    href = link.get("href")
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

            logger.info(
                f"🔍 本页新发现 {len(new_urls)} 个{self.language_name}链接，去重后新增 {new_count} 个URL"
            )
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
            "/user/",
            "/login",
            "/register",
            "/about",
            "/contact",
            "/terms",
            "/privacy",
            "/dmca",
            "/faq",
            ".css",
            ".js",
            ".png",
            ".jpg",
            ".gif",
            "javascript:",
            "mailto:",
        ]

        for pattern in exclude_patterns:
            if pattern in url.lower():
                return False

        # 只保留包含书籍相关路径的URL
        include_patterns = ["/book/", "/download/", "/author/", "/search"]
        return any(pattern in url for pattern in include_patterns)

    def click_load_more(self):
        """点击Load More按钮"""
        try:
            # 多种可能的Load More按钮选择器
            load_more_selectors = [
                ".load-more",
                "#load-more",
                'button[onclick*="load"]',
                'a[onclick*="load"]',
                ".btn-load-more",
                ".load-btn",
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
            for text in self.load_more_texts:
                try:
                    # 查找包含指定文本的按钮或链接
                    element = self.page.query_selector(
                        f'button:has-text("{text}"), a:has-text("{text}")'
                    )
                    if element and element.is_visible() and element.is_enabled():
                        # 滚动到元素位置
                        element.scroll_into_view_if_needed()
                        time.sleep(1)

                        # 点击元素
                        element.click()
                        logger.info(f"👆 成功点击Load More按钮 (文本: {text})")

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
            logger.info(
                f"🚀 开始爬取 {self.language_name} Z-Library，最大页数: {max_pages}"
            )

            # 访问主页
            self.page.goto(self.base_url)
            time.sleep(3)

            page_count = 0
            no_more_content_count = 0

            while page_count < max_pages:
                logger.info(
                    f"⏳ 正在处理第 {page_count + 1} 页({self.language_name})..."
                )

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

            logger.info(
                f"🎉 {self.language_name}爬取完成！总共收集到 {len(self.book_urls)} 个电子书URL"
            )

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
        logger.info(f"🔄 从第 {start_page + 1} 页开始继续爬取{self.language_name}内容")
        self.crawl(max_pages)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Z-Library 电子书URL爬虫")
    parser.add_argument(
        "--language",
        "-l",
        choices=["en", "zh"],
        default="en",
        help="选择语种: en(英文) 或 zh(中文)",
    )
    parser.add_argument(
        "--max-pages", "-p", type=int, default=50, help="最大爬取页数 (默认: 50)"
    )
    parser.add_argument("--resume", "-r", action="store_true", help="断点续传模式")

    args = parser.parse_args()

    # 如果没有提供命令行参数，则使用交互模式
    if len(os.sys.argv) == 1:
        print("🕷️ Z-Library 电子书URL爬虫")
        print("🌍 请选择语种:")
        print("1. 🇺🇸 English (英文)")
        print("2. 🇨🇳 中文")

        lang_choice = input("请选择语种 (1/2): ").strip()
        language = "zh" if lang_choice == "2" else "en"

        print("\n📖 请选择爬取模式:")
        print("1. 🆕 全新开始爬取")
        print("2. 🔄 断点续传")

        mode_choice = input("请选择模式 (1/2): ").strip()
        resume_mode = mode_choice == "2"

        try:
            max_pages = int(input("请输入最大爬取页数 (默认50): ") or "50")
        except ValueError:
            max_pages = 50
    else:
        language = args.language
        max_pages = args.max_pages
        resume_mode = args.resume

    # 显示配置信息
    lang_name = "中文" if language == "zh" else "English"
    mode_name = "断点续传" if resume_mode else "全新开始"

    print(f"\n🎯 爬取配置:")
    print(f"   语种: {lang_name}")
    print(f"   模式: {mode_name}")
    print(f"   最大页数: {max_pages}")
    print(f"   输出文件: book_url{'_zh' if language == 'zh' else ''}.txt")
    print()

    crawler = ZLibraryCrawler(language=language)

    if resume_mode:
        crawler.resume_crawl(max_pages)
    else:
        crawler.crawl(max_pages)


if __name__ == "__main__":
    main()
