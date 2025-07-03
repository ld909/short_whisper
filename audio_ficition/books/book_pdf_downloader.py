#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍PDF下载自动化脚本

功能说明：
基于 book_info_scraper.py 产生的书籍信息，使用 Playwright 独立浏览器自动下载书籍PDF文件

主要特性：
1. 📚 批量PDF下载
   - 从书籍信息JSON文件中读取UUID和URL
   - 智能判断PDF下载方式（直接下载 / 格式转换）
   - 支持多种下载场景处理

2. 🌐 独立浏览器自动化
   - 使用Playwright启动独立Chrome浏览器
   - 避免AdsPower CDP连接的下载问题
   - 直接指定下载目录，文件正确保存

3. 📥 智能下载策略
   - 情况1：直接下载PDF文件（优先选择）
   - 情况2：通过格式转换获得PDF
   - 情况3：跳过标记为低质量的PDF
   - 情况4：无PDF可用时跳过

4. 💾 简化文件管理
   - 自动保存到指定目录：/Volumes/dhl/audio/books/{语言}/pdf/
   - 支持多语言主题：en(英文)、zh(中文)等
   - 直接命名策略：下载时直接使用UUID.pdf作为文件名，无需重命名
   - 避免重复下载：自动跳过已存在的PDF文件
   - 安全可靠：避免文件混乱和重命名错误

5. 🍪 Cookie管理
   - 支持保存和加载登录状态
   - Cookie保存在项目内部目录
   - 支持多站点、多语种Cookie管理
   - Cookie文件名格式：{站点}_{语言}_cookies.json

6. 🔄 智能重试机制
   - 自动重试失败的下载，针对不同错误类型使用不同重试次数:
     * 没有下载按钮：最多重试2次后永久跳过
     * 没有PDF格式：最多重试2次后永久跳过
     * 其他错误：最多重试5次
   - 重试记录保存在项目根目录的download_json目录，支持断点续传
   - 下载后等待76秒确认文件是否成功保存
   - 达到对应的最大重试次数后自动跳过，避免无限循环
   - 下载成功后自动清除重试记录

7. 📊 断点续传支持
   - 程序重启后自动加载之前的重试记录
   - 智能跳过已达最大重试次数的文件
   - 支持查看重试状态和错误历史
   - JSON格式存储，便于查看和管理

使用方法：
python book_pdf_downloader.py --count 10
python book_pdf_downloader.py --all --headless
python book_pdf_downloader.py --count 10 --lang zh  # 中文主题
python book_pdf_downloader.py --count 10 --lang en  # 英文主题
python book_pdf_downloader.py --login --site zlib --lang zh  # 为中文主题登录并保存cookies
python book_pdf_downloader.py --count 10 --load-cookies zlib --lang zh  # 使用中文cookies下载

依赖组件：
- Playwright：网页自动化和独立浏览器启动
- book_info_scraper.py的输出数据

作者：PDF下载自动化团队
版本：v2.2 (智能重试策略版本)
"""

import os
import json
import time
import random
import platform
import logging
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
from tqdm import tqdm

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/audio"
    else:  # 默认为Linux/Ubuntu
        return "/mnt/dhl/audio"


class BookPDFDownloader:
    """独立浏览器PDF下载器"""

    def __init__(self, debug=False, headless=False, lang="en"):
        self.debug = debug
        self.headless = headless
        self.lang = lang
        self.base_media_path = get_base_media_path()
        self.base_path = os.path.join(self.base_media_path, "books", lang)

        # 设置目录结构
        self.info_dir = os.path.join(self.base_path, "info")
        self.pdf_dir = os.path.join(self.base_path, "pdf")

        # Cookie保存在项目内部，不保存在外部硬盘
        script_dir = os.path.dirname(os.path.abspath(__file__))  # 当前脚本目录
        self.cookie_dir = os.path.join(script_dir, "download_cookie")

        # 重试记录系统 - 保存在项目根目录的download_json目录
        project_root = os.path.dirname(os.path.dirname(script_dir))  # 项目根目录
        self.retry_json_dir = os.path.join(project_root, "download_json")
        self.retry_json_file = os.path.join(
            self.retry_json_dir, f"pdf_download_retry_{lang}.json"
        )
        self.max_retry_count = 5  # 普通错误的最大重试次数
        self.max_retry_count_no_button = 2  # "没有下载按钮"错误的最大重试次数
        self.max_retry_count_no_pdf = 2  # "没有PDF格式"错误的最大重试次数
        self.confirmation_wait_time = 76  # 下载确认等待时间（秒）

        # 创建必要目录
        Path(self.pdf_dir).mkdir(parents=True, exist_ok=True)
        Path(self.cookie_dir).mkdir(parents=True, exist_ok=True)
        Path(self.retry_json_dir).mkdir(parents=True, exist_ok=True)

        logger.info(f"📁 PDF下载目录: {self.pdf_dir}")
        logger.info(f"🍪 Cookie保存目录: {self.cookie_dir}")
        logger.info(f"🔄 重试记录文件: {self.retry_json_file}")
        logger.info(f"🌐 语言主题: {self.lang}")
        logger.info("🔧 独立浏览器模式:")
        logger.info("   1. 使用Playwright启动独立Chrome实例")
        logger.info("   2. 直接指定下载目录，文件会正确保存")
        logger.info("   3. Cookie保存在项目内部，不占用外部硬盘空间")
        logger.info(f"   4. 无头模式: {'是' if headless else '否'}")
        logger.info(f"   5. 智能重试策略:")
        logger.info(f"      - 没有下载按钮: 最多{self.max_retry_count_no_button}次")
        logger.info(f"      - 没有PDF格式: 最多{self.max_retry_count_no_pdf}次")
        logger.info(f"      - 其他错误: 最多{self.max_retry_count}次")
        logger.info(f"   6. 下载确认等待时间: {self.confirmation_wait_time}秒")

        # Playwright 相关
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        if self.debug:
            logger.info("🔧 调试模式已启用")

    def setup_browser(self, load_cookies_for_site=None):
        """设置独立Playwright浏览器"""
        try:
            print("正在启动独立Chrome浏览器...")
            self.playwright = sync_playwright().start()

            # 启动独立的Chrome浏览器，不指定downloads_path避免重复下载
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-extensions",
                    "--disable-plugins-discovery",
                    "--disable-default-apps",
                ],
            )

            # 创建上下文，设置下载行为
            self.context = self.browser.new_context(
                accept_downloads=True,
                # 可以设置用户代理等
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )

            # 创建页面
            self.page = self.context.new_page()
            self.page.set_default_timeout(60000)  # 60秒超时

            logger.info("✅ 独立浏览器启动成功！")
            logger.info(f"📁 下载目录已设置为: {self.pdf_dir}")

            # 如果指定了要加载的cookies，尝试加载
            if load_cookies_for_site:
                logger.info(f"🍪 尝试加载cookies: {load_cookies_for_site}")
                if self.load_cookies(load_cookies_for_site):
                    logger.info("✅ Cookies加载成功")
                else:
                    logger.warning("⚠️ Cookies加载失败，将以未登录状态运行")

        except Exception as e:
            logger.error(f"❌ 启动独立浏览器失败: {e}")
            raise

    def test_download_setup(self):
        """测试下载设置"""
        try:
            logger.info("🧪 测试独立浏览器下载设置...")

            # 检查目录是否可写
            test_file = os.path.join(self.pdf_dir, "test_download.txt")
            try:
                with open(test_file, "w", encoding="utf-8") as f:
                    f.write("测试文件")
                os.remove(test_file)
                logger.info("✅ 下载目录可写")
            except Exception as e:
                logger.error(f"❌ 下载目录不可写: {e}")
                return False

            logger.info("✅ 独立浏览器下载设置正常")
            return True

        except Exception as e:
            logger.error(f"❌ 测试下载设置失败: {e}")
            return False

    def cleanup(self):
        """清理浏览器资源"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()

            logger.info("🧹 独立浏览器资源已清理")
        except Exception as e:
            logger.error(f"❌ 清理资源时出错: {e}")

    def load_retry_records(self):
        """加载重试记录"""
        try:
            if os.path.exists(self.retry_json_file):
                with open(self.retry_json_file, "r", encoding="utf-8") as f:
                    retry_data = json.load(f)
                logger.info(f"📖 已加载重试记录: {len(retry_data)} 条记录")
                return retry_data
            else:
                logger.info("📝 创建新的重试记录文件")
                return {}
        except Exception as e:
            logger.error(f"❌ 加载重试记录失败: {e}")
            return {}

    def save_retry_records(self, retry_data):
        """保存重试记录"""
        try:
            with open(self.retry_json_file, "w", encoding="utf-8") as f:
                json.dump(retry_data, f, indent=2, ensure_ascii=False)
            if self.debug:
                logger.debug(f"💾 已保存重试记录: {len(retry_data)} 条记录")
        except Exception as e:
            logger.error(f"❌ 保存重试记录失败: {e}")

    def get_max_retry_count_for_error(self, error_message):
        """根据错误消息返回对应的最大重试次数"""
        if "未找到下载按钮" in error_message or "没有下载按钮" in error_message:
            return self.max_retry_count_no_button
        elif (
            "无PDF格式可用" in error_message
            or "没有PDF" in error_message
            or "无PDF可用" in error_message
        ):
            return self.max_retry_count_no_pdf
        else:
            return self.max_retry_count

    def get_retry_count(self, uuid_val, retry_data):
        """获取指定UUID的重试次数"""
        return retry_data.get(uuid_val, {}).get("retry_count", 0)

    def get_max_retry_count_for_uuid(self, uuid_val, retry_data):
        """获取指定UUID对应的最大重试次数（根据历史错误类型）"""
        if uuid_val in retry_data:
            last_error = retry_data[uuid_val].get("last_error", "")
            return self.get_max_retry_count_for_error(last_error)
        else:
            return self.max_retry_count  # 如果没有历史记录，使用默认值

    def increment_retry_count(self, uuid_val, retry_data, error_message=""):
        """增加指定UUID的重试次数"""
        if uuid_val not in retry_data:
            retry_data[uuid_val] = {
                "retry_count": 0,
                "last_error": "",
                "last_attempt": "",
            }

        retry_data[uuid_val]["retry_count"] += 1
        retry_data[uuid_val]["last_error"] = error_message
        retry_data[uuid_val]["last_attempt"] = time.strftime("%Y-%m-%d %H:%M:%S")

        return retry_data[uuid_val]["retry_count"]

    def reset_retry_count(self, uuid_val, retry_data):
        """重置指定UUID的重试次数（下载成功时调用）"""
        if uuid_val in retry_data:
            del retry_data[uuid_val]
            if self.debug:
                logger.debug(f"🔄 已重置UUID {uuid_val} 的重试记录")

    def confirm_download_success(self, uuid_val, target_path, wait_time=None):
        """确认下载是否成功，等待指定时间后检查文件"""
        if wait_time is None:
            wait_time = self.confirmation_wait_time

        logger.info(f"⏳ 等待 {wait_time} 秒确认下载结果...")

        # 分段等待，每10秒检查一次文件
        total_waited = 0
        check_interval = 10  # 每10秒检查一次

        while total_waited < wait_time:
            remaining_time = min(check_interval, wait_time - total_waited)
            time.sleep(remaining_time)
            total_waited += remaining_time

            # 检查文件是否存在
            if os.path.exists(target_path):
                file_size = os.path.getsize(target_path)
                if file_size > 0:  # 文件大小大于0表示下载成功
                    logger.info(f"✅ 下载确认成功: {uuid_val} ({file_size} bytes)")
                    return True, f"文件确认成功 ({file_size} bytes)"

            # 显示剩余等待时间
            remaining_wait = wait_time - total_waited
            if remaining_wait > 0:
                logger.info(f"⏳ 继续等待... 剩余 {remaining_wait} 秒")

        # 最终检查
        if os.path.exists(target_path):
            file_size = os.path.getsize(target_path)
            if file_size > 0:
                logger.info(f"✅ 下载确认成功: {uuid_val} ({file_size} bytes)")
                return True, f"文件确认成功 ({file_size} bytes)"
            else:
                logger.warning(f"⚠️ 文件存在但大小为0: {target_path}")
                return False, "文件大小为0"
        else:
            logger.warning(f"⚠️ 等待 {wait_time} 秒后文件仍未出现: {target_path}")
            return False, f"等待 {wait_time} 秒后文件未出现"

    def get_cookie_file_path(self, site_name="zlib"):
        """获取cookie文件路径，支持多语种主题"""
        cookie_filename = f"{site_name}_{self.lang}_cookies.json"
        return os.path.join(self.cookie_dir, cookie_filename)

    def save_cookies(self, site_name="zlib"):
        """保存当前页面的cookies"""
        try:
            if not self.context:
                logger.error("❌ 浏览器上下文未初始化")
                return False

            # 获取所有cookies
            cookies = self.context.cookies()
            cookie_file = self.get_cookie_file_path(site_name)

            # 保存cookies到文件
            with open(cookie_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)

            logger.info(f"✅ Cookies已保存到: {cookie_file}")
            logger.info(f"📊 保存了 {len(cookies)} 个cookie")
            return True

        except Exception as e:
            logger.error(f"❌ 保存cookies失败: {e}")
            return False

    def load_cookies(self, site_name="zlib"):
        """加载cookies到浏览器"""
        try:
            cookie_file = self.get_cookie_file_path(site_name)

            if not os.path.exists(cookie_file):
                logger.warning(f"⚠️ Cookie文件不存在: {cookie_file}")
                return False

            # 读取cookies
            with open(cookie_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            if not self.context:
                logger.error("❌ 浏览器上下文未初始化")
                return False

            # 添加cookies到浏览器
            self.context.add_cookies(cookies)

            logger.info(f"✅ Cookies已加载: {cookie_file}")
            logger.info(f"📊 加载了 {len(cookies)} 个cookie")
            return True

        except Exception as e:
            logger.error(f"❌ 加载cookies失败: {e}")
            return False

    def list_cookie_files(self, show_details=True):
        """列出所有可用的cookie文件"""
        try:
            if not os.path.exists(self.cookie_dir):
                if show_details:
                    logger.info("📁 Cookie目录不存在")
                return []

            cookie_files = []
            for filename in os.listdir(self.cookie_dir):
                if filename.startswith("."):  # 排除Mac的点文件
                    continue
                if filename.endswith("_cookies.json"):
                    # 解析文件名格式：{site_name}_{lang}_cookies.json
                    name_part = filename[:-13]  # 移除_cookies.json后缀
                    if "_" in name_part:
                        # 新格式：包含语言信息
                        parts = name_part.rsplit("_", 1)  # 从右侧分割，最多分割1次
                        if len(parts) == 2:
                            site_name, lang = parts
                            display_name = f"{site_name}({lang})"
                        else:
                            # 兼容性处理
                            site_name = name_part
                            lang = "unknown"
                            display_name = site_name
                    else:
                        # 旧格式：不包含语言信息
                        site_name = name_part
                        lang = "legacy"
                        display_name = f"{site_name}(legacy)"

                    file_path = os.path.join(self.cookie_dir, filename)
                    file_size = os.path.getsize(file_path)
                    mtime = os.path.getmtime(file_path)
                    cookie_files.append(
                        {
                            "site_name": site_name,
                            "lang": lang,
                            "display_name": display_name,
                            "filename": filename,
                            "file_path": file_path,
                            "size": file_size,
                            "mtime": mtime,
                        }
                    )

            # 按修改时间排序（最新的在前）
            cookie_files.sort(key=lambda x: x["mtime"], reverse=True)

            if show_details:
                if cookie_files:
                    logger.info(f"📊 找到 {len(cookie_files)} 个cookie文件:")
                    for i, cookie_file in enumerate(cookie_files, 1):
                        mtime_str = time.strftime(
                            "%Y-%m-%d %H:%M:%S", time.localtime(cookie_file["mtime"])
                        )
                        logger.info(
                            f"  {i}. {cookie_file['display_name']} - {mtime_str} ({cookie_file['size']} bytes)"
                        )
                else:
                    logger.info("📁 未找到任何cookie文件")

            return cookie_files

        except Exception as e:
            logger.error(f"❌ 列出cookie文件失败: {e}")
            return []

    def login_and_save_cookies(self, site_name="zlib"):
        """登录并保存cookies - 随机打开一个书籍页面进行登录"""
        try:
            logger.info(f"🔐 开始登录流程...")
            logger.info(f"📝 Cookie将保存为: {site_name}_{self.lang}_cookies.json")
            logger.info(f"🌐 当前语言主题: {self.lang}")

            if not self.page:
                logger.error("❌ 浏览器页面未初始化")
                return False

            # 加载书籍数据，随机选择一个
            book_data = self.load_book_data()
            if not book_data:
                logger.error("❌ 未找到任何书籍数据，无法进行登录")
                return False

            # 随机选择一本书
            import random

            random_book = random.choice(book_data)
            login_url = random_book["url"]
            book_title = random_book["title"]

            logger.info(f"📚 随机选择书籍进行登录: {book_title}")
            logger.info(f"🔗 访问页面: {login_url}")

            # 访问随机选择的书籍页面
            self.page.goto(login_url, wait_until="domcontentloaded", timeout=60000)

            # 等待页面完全加载
            time.sleep(3)

            logger.info("=" * 60)
            logger.info("🔐 请在浏览器中完成登录")
            logger.info("📋 操作步骤:")
            logger.info("   1. 在当前页面输入用户名和密码登录")
            logger.info("   2. 登录完成后，回到命令行按 Enter 键")
            logger.info(f"   3. 当前页面: {book_title}")
            logger.info("=" * 60)

            # 等待用户输入
            input("👆 登录完成后，请按 Enter 键继续...")

            # 检查是否成功登录
            current_url = self.page.url
            logger.info(f"📍 当前页面: {current_url}")

            # 保存cookies
            if self.save_cookies(site_name):
                logger.info("✅ 登录和保存cookies完成！")

                # 测试cookies是否有效
                cookie_file = self.get_cookie_file_path(site_name)
                with open(cookie_file, "r", encoding="utf-8") as f:
                    cookies = json.load(f)

                # 检查重要的认证cookie
                auth_cookies = []
                for cookie in cookies:
                    if any(
                        keyword in cookie["name"].lower()
                        for keyword in ["session", "auth", "login", "token", "user"]
                    ):
                        auth_cookies.append(cookie["name"])

                if auth_cookies:
                    logger.info(
                        f"🔑 检测到认证相关cookies: {', '.join(auth_cookies[:3])}{'...' if len(auth_cookies) > 3 else ''}"
                    )
                else:
                    logger.warning("⚠️ 未检测到明显的认证cookies，请确认登录是否成功")

                return True
            else:
                logger.error("❌ 保存cookies失败")
                return False

        except Exception as e:
            logger.error(f"❌ 登录流程失败: {e}")
            return False

    def load_book_data(self):
        """加载书籍数据"""
        try:
            book_data = []
            if os.path.exists(self.info_dir):
                for filename in os.listdir(self.info_dir):
                    if filename.startswith("."):  # 排除Mac的点文件
                        continue
                    if filename.endswith(".json"):
                        uuid_val = filename[:-5]
                        info_file = os.path.join(self.info_dir, filename)

                        try:
                            with open(info_file, "r", encoding="utf-8") as f:
                                book_info = json.load(f)

                            if book_info.get("url") and book_info.get("title"):
                                book_data.append(
                                    {
                                        "uuid": uuid_val,
                                        "url": book_info["url"],
                                        "title": book_info.get("title", "Unknown"),
                                        "author": book_info.get("author", "Unknown"),
                                    }
                                )
                        except Exception as e:
                            logger.warning(f"⚠️ 读取书籍信息失败 {filename}: {e}")
                            continue

            logger.info(f"📚 已加载 {len(book_data)} 本书籍信息")
            return book_data

        except Exception as e:
            logger.error(f"❌ 加载书籍数据失败: {e}")
            return []

    def get_existing_pdfs(self):
        """获取已下载的PDF文件列表"""
        existing_pdfs = set()
        if os.path.exists(self.pdf_dir):
            for filename in os.listdir(self.pdf_dir):
                if filename.startswith("."):  # 排除Mac的点文件
                    continue
                if filename.endswith(".pdf"):
                    uuid_val = filename[:-4]  # 移除.pdf后缀
                    existing_pdfs.add(uuid_val)

        logger.info(f"📁 已存在 {len(existing_pdfs)} 个PDF文件")
        return existing_pdfs

    def cleanup_orphaned_files(self):
        """清理孤儿文件（没有扩展名的UUID文件）"""
        try:
            if not os.path.exists(self.pdf_dir):
                return

            orphaned_files = []
            pdf_uuids = set()

            # 先收集所有PDF文件的UUID
            for filename in os.listdir(self.pdf_dir):
                if filename.startswith("."):
                    continue
                if filename.endswith(".pdf"):
                    uuid_val = filename[:-4]
                    pdf_uuids.add(uuid_val)

            # 检查是否有对应的无扩展名文件
            for filename in os.listdir(self.pdf_dir):
                if filename.startswith("."):
                    continue
                # 检查是否是UUID格式但没有扩展名的文件
                if (
                    len(filename) == 36
                    and filename.count("-") == 4
                    and not "." in filename
                    and filename in pdf_uuids
                ):
                    file_path = os.path.join(self.pdf_dir, filename)
                    if os.path.isfile(file_path):
                        orphaned_files.append((filename, file_path))

            if orphaned_files:
                logger.info(f"🧹 发现 {len(orphaned_files)} 个孤儿文件，准备清理...")
                for filename, file_path in orphaned_files:
                    try:
                        os.remove(file_path)
                        logger.info(f"  ✅ 已删除: {filename}")
                    except Exception as e:
                        logger.warning(f"  ❌ 删除失败 {filename}: {e}")
                logger.info("🎯 孤儿文件清理完成")
            else:
                logger.info("✨ 未发现孤儿文件")

        except Exception as e:
            logger.error(f"❌ 清理孤儿文件时出错: {e}")

    def filter_books_to_download(self, book_list):
        """过滤需要下载的书籍"""
        logger.info("🔍 正在检查下载状态...")

        existing_pdfs = self.get_existing_pdfs()
        retry_data = self.load_retry_records()
        books_to_download = []
        skipped_count = 0
        retry_exhausted_count = 0

        for book in book_list:
            uuid_val = book["uuid"]
            if uuid_val in existing_pdfs:
                skipped_count += 1
                if self.debug:
                    logger.debug(f"⏭️ 已存在: {book['title']} (UUID: {uuid_val})")
            else:
                # 检查重试次数
                retry_count = self.get_retry_count(uuid_val, retry_data)
                max_retry_for_this_uuid = self.get_max_retry_count_for_uuid(
                    uuid_val, retry_data
                )

                if retry_count >= max_retry_for_this_uuid:
                    retry_exhausted_count += 1
                    if self.debug:
                        last_error = retry_data[uuid_val].get("last_error", "未知错误")
                        last_attempt = retry_data[uuid_val].get(
                            "last_attempt", "未知时间"
                        )
                        logger.debug(
                            f"🚫 重试次数已达上限: {book['title']} (UUID: {uuid_val})"
                        )
                        logger.debug(
                            f"   重试次数: {retry_count}/{max_retry_for_this_uuid}"
                        )
                        logger.debug(f"   最后错误: {last_error}")
                        logger.debug(f"   最后尝试: {last_attempt}")
                else:
                    books_to_download.append(book)
                    if retry_count > 0:
                        logger.info(
                            f"🔄 需要重试: {book['title']} (已尝试 {retry_count}/{max_retry_for_this_uuid} 次)"
                        )

        logger.info(f"📊 检查结果:")
        logger.info(f"  ✅ 已下载: {skipped_count} 本")
        logger.info(f"  🚫 重试次数已达上限: {retry_exhausted_count} 本")
        logger.info(f"  📥 需要下载: {len(books_to_download)} 本")
        logger.info(f"  📚 总计: {len(book_list)} 本")

        if retry_exhausted_count > 0:
            logger.warning(
                f"⚠️ 有 {retry_exhausted_count} 本书籍已达到最大重试次数，将被跳过"
            )
            logger.info(f"   📊 重试策略:")
            logger.info(f"      - 没有下载按钮: 最多{self.max_retry_count_no_button}次")
            logger.info(f"      - 没有PDF格式: 最多{self.max_retry_count_no_pdf}次")
            logger.info(f"      - 其他错误: 最多{self.max_retry_count}次")
            logger.info(
                f"💡 如需重新尝试这些书籍，请删除重试记录文件: {self.retry_json_file}"
            )

        return books_to_download

    def download_book_pdf(self, book_data):
        """下载单本书的PDF"""
        uuid_val = book_data["uuid"]
        url = book_data["url"]
        title = book_data["title"]
        target_filename = f"{uuid_val}.pdf"
        target_path = os.path.join(self.pdf_dir, target_filename)

        try:
            logger.info(f"📖 开始处理: {title} (UUID: {uuid_val})")

            # 访问书籍页面
            logger.info(f"🔗 访问页面: {url}")
            self.page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # 等待页面加载
            time.sleep(3)

            # 查找并点击下载按钮
            download_button = self.page.locator("#btnCheckOtherFormats")
            if download_button.count() == 0:
                logger.warning(f"⚠️ 未找到下载按钮: {title}")
                return "failed", "未找到下载按钮"

            logger.info(f"🔽 点击下载按钮")
            download_button.click()

            # 等待下载菜单
            time.sleep(3)

            # 查找PDF下载链接
            pdf_link_selectors = [
                'a.addDownloadedBook:has(b.book-property__extension:text("pdf"))',
                'a:has(.book-property__extension:text("pdf"))',
                'a:has(b:text("pdf"))',
            ]

            pdf_link = None
            for selector in pdf_link_selectors:
                try:
                    links = self.page.locator(selector)
                    if links.count() > 0:
                        # 检查是否有低质量标记
                        for i in range(links.count()):
                            link = links.nth(i)
                            low_quality_icon = link.locator("i.low-quality-icon")
                            if low_quality_icon.count() == 0:
                                pdf_link = link
                                break
                        if pdf_link:
                            break
                except:
                    continue

            if pdf_link:
                logger.info(f"📥 准备直接下载PDF...")

                # 使用 expect_download 模式捕获下载
                with self.page.expect_download(timeout=60000) as download_info:
                    logger.info(f"🖱️ 点击PDF下载链接...")
                    pdf_link.click()

                download = download_info.value

                logger.info(f"📥 下载事件已捕获: {download.suggested_filename}")

                # 保存文件到目标路径
                download.save_as(target_path)

                # 删除原始下载文件（避免重复文件）
                try:
                    original_path = download.path()
                    if (
                        original_path
                        and os.path.exists(original_path)
                        and original_path != target_path
                    ):
                        os.remove(original_path)
                        logger.info(
                            f"🧹 已删除临时下载文件: {os.path.basename(original_path)}"
                        )
                except Exception as e:
                    if self.debug:
                        logger.debug(f"清理临时文件时出错: {e}")

                # 使用确认等待机制验证下载是否真正成功
                logger.info(f"📥 开始确认下载结果...")
                success, confirmation_message = self.confirm_download_success(
                    uuid_val, target_path
                )

                if success:
                    return "success", confirmation_message
                else:
                    return "failed", f"下载确认失败: {confirmation_message}"

            else:
                # 查找转换选项
                convert_link = self.page.locator(
                    'a.converterLink[data-convert_to="pdf"]'
                )
                if convert_link.count() > 0:
                    logger.info(f"🔄 准备转换并下载PDF...")

                    # 使用 expect_download 模式捕获下载
                    with self.page.expect_download(
                        timeout=300000
                    ) as download_info:  # 转换可能需要更长时间
                        logger.info(f"🖱️ 点击PDF转换选项...")
                        convert_link.click()

                    download = download_info.value

                    logger.info(
                        f"📥 转换后下载事件已捕获: {download.suggested_filename}"
                    )

                    # 保存文件
                    download.save_as(target_path)

                    # 删除原始下载文件（避免重复文件）
                    try:
                        original_path = download.path()
                        if (
                            original_path
                            and os.path.exists(original_path)
                            and original_path != target_path
                        ):
                            os.remove(original_path)
                            logger.info(
                                f"🧹 已删除临时下载文件: {os.path.basename(original_path)}"
                            )
                    except Exception as e:
                        if self.debug:
                            logger.debug(f"清理临时文件时出错: {e}")

                    # 使用确认等待机制验证转换下载是否真正成功
                    logger.info(f"📥 开始确认转换下载结果...")
                    success, confirmation_message = self.confirm_download_success(
                        uuid_val, target_path
                    )

                    if success:
                        return "success", f"PDF转换下载成功: {confirmation_message}"
                    else:
                        return "failed", f"转换下载确认失败: {confirmation_message}"

                else:
                    logger.warning(f"❌ 无PDF可用: {title}")
                    return "failed", "无PDF格式可用"

        except Exception as e:
            logger.error(f"❌ 下载失败 {title}: {e}")
            import traceback

            traceback.print_exc()
            return "failed", str(e)

    def download_pdfs(self, book_list, max_books=None, load_cookies_for_site=None):
        """批量下载PDF"""
        try:
            # 清理孤儿文件
            self.cleanup_orphaned_files()

            # 过滤需要下载的书籍
            books_to_download = self.filter_books_to_download(book_list)

            # 限制下载数量
            if max_books and len(books_to_download) > max_books:
                books_to_download = books_to_download[:max_books]
                logger.info(f"📝 已限制下载数量为: {max_books} 本")

            if not books_to_download:
                logger.info("🎉 所有书籍的PDF都已下载完成！")
                return

            logger.info(f"📥 准备下载 {len(books_to_download)} 本书的PDF")

            # 如果没有指定cookies，检查是否有可用的cookies并自动使用最新的
            if load_cookies_for_site is None:
                cookie_files = self.list_cookie_files(show_details=False)
                if cookie_files:
                    # 优先选择匹配当前语言的cookies
                    matching_lang_cookies = [
                        cf for cf in cookie_files if cf.get("lang") == self.lang
                    ]

                    if matching_lang_cookies:
                        # 使用匹配语言的最新cookie文件
                        latest_cookie = matching_lang_cookies[0]  # 已按时间排序
                        load_cookies_for_site = latest_cookie["site_name"]
                        logger.info(
                            f"🍪 自动检测到匹配语言({self.lang})的cookies，将使用: {latest_cookie['display_name']}"
                        )
                    else:
                        # 如果没有匹配语言的，使用最新的任何cookie
                        latest_cookie = cookie_files[0]  # 已按时间排序，第一个是最新的
                        load_cookies_for_site = latest_cookie["site_name"]
                        logger.info(
                            f"🍪 未找到匹配语言({self.lang})的cookies，使用最新的: {latest_cookie['display_name']}"
                        )
                        logger.warning(
                            f"⚠️ 该cookie可能不适用于当前语言主题，建议重新登录"
                        )

                    logger.info(
                        f"   文件修改时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(latest_cookie['mtime']))}"
                    )
                else:
                    logger.warning("⚠️ 未找到任何已保存的cookies")
                    logger.info(
                        f"💡 提示: 如需登录状态下载，请先运行: python book_pdf_downloader.py --login --site zlib --lang {self.lang}"
                    )

            # 设置浏览器并加载cookies
            self.setup_browser(load_cookies_for_site=load_cookies_for_site)

            # 测试下载设置
            if not self.test_download_setup():
                logger.warning("⚠️ 下载设置可能有问题，但继续执行...")

            success_count = 0
            failed_count = 0
            skipped_count = 0

            # 加载重试记录
            retry_data = self.load_retry_records()

            # 使用进度条
            for i, book_data in enumerate(tqdm(books_to_download, desc="📥 下载PDF")):
                uuid_val = book_data["uuid"]
                current_retry_count = self.get_retry_count(uuid_val, retry_data)

                try:
                    if current_retry_count > 0:
                        logger.info(
                            f"🔄 重试下载 (第{current_retry_count + 1}次尝试): {book_data['title']}"
                        )

                    result, message = self.download_book_pdf(book_data)

                    if result == "success":
                        success_count += 1
                        logger.info(f"✅ 成功: {book_data['title']}")
                        # 下载成功，重置重试记录
                        self.reset_retry_count(uuid_val, retry_data)
                        self.save_retry_records(retry_data)
                    elif result == "skipped":
                        skipped_count += 1
                        logger.info(f"⏭️ 跳过: {book_data['title']} - {message}")
                    else:
                        failed_count += 1
                        # 下载失败，增加重试次数
                        new_retry_count = self.increment_retry_count(
                            uuid_val, retry_data, message
                        )
                        self.save_retry_records(retry_data)

                        # 根据错误类型获取对应的最大重试次数
                        max_retry_for_this_error = self.get_max_retry_count_for_error(
                            message
                        )

                        if new_retry_count >= max_retry_for_this_error:
                            logger.error(
                                f"🚫 达到最大重试次数: {book_data['title']} ({new_retry_count}/{max_retry_for_this_error})"
                            )
                            logger.error(f"   最后错误: {message}")
                            if (
                                max_retry_for_this_error
                                == self.max_retry_count_no_button
                            ):
                                logger.error(f"   错误类型: 没有下载按钮 (永久跳过)")
                            elif (
                                max_retry_for_this_error == self.max_retry_count_no_pdf
                            ):
                                logger.error(f"   错误类型: 没有PDF格式 (永久跳过)")
                        else:
                            logger.warning(f"❌ 失败: {book_data['title']} - {message}")
                            logger.warning(
                                f"   重试记录: {new_retry_count}/{max_retry_for_this_error}"
                            )

                    # 进度显示
                    if (i + 1) % 5 == 0:
                        logger.info(
                            f"📊 进度: {i + 1}/{len(books_to_download)} (成功:{success_count}, 跳过:{skipped_count}, 失败:{failed_count})"
                        )

                    # 随机延迟
                    if i < len(books_to_download) - 1:
                        wait_time = random.uniform(2, 5)
                        time.sleep(wait_time)

                except KeyboardInterrupt:
                    logger.info("⏹️ 用户中断下载...")
                    # 保存当前的重试记录
                    self.save_retry_records(retry_data)
                    break
                except Exception as e:
                    logger.error(f"❌ 处理书籍时出错 {book_data['title']}: {e}")
                    failed_count += 1
                    # 记录异常错误
                    error_message = f"异常错误: {str(e)}"
                    new_retry_count = self.increment_retry_count(
                        uuid_val, retry_data, error_message
                    )
                    self.save_retry_records(retry_data)

                    # 根据错误类型获取对应的最大重试次数
                    max_retry_for_this_error = self.get_max_retry_count_for_error(
                        error_message
                    )
                    logger.error(
                        f"   重试记录: {new_retry_count}/{max_retry_for_this_error}"
                    )

            # 最终统计
            total_processed = success_count + failed_count + skipped_count
            logger.info(f"\n🎯 下载完成!")
            logger.info(f"✅ 成功下载: {success_count} 本")
            logger.info(f"⏭️ 跳过: {skipped_count} 本")
            logger.info(f"❌ 失败: {failed_count} 本")
            logger.info(f"📊 总计处理: {total_processed} 本")

            if success_count > 0:
                logger.info(f"📁 PDF文件保存在: {self.pdf_dir}")

        except Exception as e:
            logger.error(f"❌ 批量下载出错: {e}")
        finally:
            self.cleanup()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="📥 书籍PDF下载自动化脚本 (独立浏览器版本)",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  # 基本下载
  python book_pdf_downloader.py --count 10
  python book_pdf_downloader.py --all
  python book_pdf_downloader.py --count 5 --debug
  python book_pdf_downloader.py --all --headless
  
  # 指定语言主题
  python book_pdf_downloader.py --count 10 --lang zh  # 中文主题
  python book_pdf_downloader.py --count 10 --lang en  # 英文主题
  
  # Cookie管理  
  python book_pdf_downloader.py --login --site zlib --lang zh  # 为中文主题登录并保存cookies
  python book_pdf_downloader.py --login --site zlib --lang en  # 为英文主题登录并保存cookies
  python book_pdf_downloader.py --list-cookies                 # 列出已保存的cookies
  python book_pdf_downloader.py --count 10 --load-cookies zlib --lang zh  # 使用中文cookies下载
  
  # 文件清理
  python book_pdf_downloader.py --cleanup            # 清理孤儿文件（无扩展名的UUID文件）
  python book_pdf_downloader.py --clear-retry --lang zh  # 清除中文主题的重试记录
  
  # 智能重试机制说明
  # - 每次下载失败后会自动记录重试次数到项目根目录的download_json目录
  # - 智能重试策略，针对不同错误类型使用不同重试次数:
  #   * 没有下载按钮：最多重试2次后永久跳过
  #   * 没有PDF格式：最多重试2次后永久跳过
  #   * 其他错误：最多重试5次
  # - 下载成功后等待76秒确认文件是否正确保存
  # - 支持断点续传，程序重启后会自动加载重试记录
  # - 重试记录文件格式：pdf_download_retry_{语言}.json
        """,
    )
    parser.add_argument(
        "--count", "-c", type=int, help="要下载的PDF数量 (不指定则下载所有)"
    )
    parser.add_argument("--all", action="store_true", help="下载所有可用的PDF")
    parser.add_argument("--debug", "-d", action="store_true", help="启用调试模式")
    parser.add_argument("--headless", action="store_true", help="无头模式运行")
    parser.add_argument(
        "--lang", "-l", default="en", help="语言主题 (en: 英文, zh: 中文) (默认: en)"
    )
    # Cookie管理参数
    parser.add_argument("--login", action="store_true", help="登录并保存cookies")
    parser.add_argument(
        "--list-cookies", action="store_true", help="列出已保存的cookie文件"
    )
    parser.add_argument(
        "--site", default="zlib", help="网站名称，用于保存cookies (默认: zlib)"
    )
    parser.add_argument("--load-cookies", help="加载指定网站的cookies进行下载")
    parser.add_argument(
        "--cleanup", action="store_true", help="清理孤儿文件（无扩展名的UUID文件）"
    )
    parser.add_argument(
        "--clear-retry", action="store_true", help="清除重试记录，重新开始重试计数"
    )

    args = parser.parse_args()

    # 验证参数
    if args.count and args.count <= 0:
        print("❌ 错误：下载数量必须大于 0")
        return

    debug = args.debug
    lang = args.lang

    # 处理列出cookies的请求
    if args.list_cookies:
        print("📋 列出已保存的cookie文件...")
        try:
            # 创建临时下载器实例来列出cookies
            temp_downloader = BookPDFDownloader(debug=debug, lang=lang)
            temp_downloader.list_cookie_files(show_details=True)
        except Exception as e:
            print(f"❌ 列出cookie文件失败: {e}")
        return

    # 处理清理孤儿文件的请求
    if args.cleanup:
        print("🧹 清理孤儿文件...")
        try:
            temp_downloader = BookPDFDownloader(debug=debug, lang=lang)
            temp_downloader.cleanup_orphaned_files()
            print("✅ 清理完成")
        except Exception as e:
            print(f"❌ 清理失败: {e}")
        return

    # 处理清除重试记录的请求
    if args.clear_retry:
        print("🔄 清除重试记录...")
        try:
            temp_downloader = BookPDFDownloader(debug=debug, lang=lang)
            if os.path.exists(temp_downloader.retry_json_file):
                os.remove(temp_downloader.retry_json_file)
                print(f"✅ 已删除重试记录文件: {temp_downloader.retry_json_file}")
            else:
                print("📝 重试记录文件不存在，无需清理")
        except Exception as e:
            print(f"❌ 清除重试记录失败: {e}")
        return

    # 处理登录请求
    if args.login:
        print("🔐 开始登录流程...")
        print(f"🌐 网站: {args.site}")
        print("📚 将随机打开一个书籍页面供你登录")

        try:
            downloader = BookPDFDownloader(
                debug=debug, headless=False, lang=lang
            )  # 登录时不能使用无头模式
            downloader.setup_browser()

            if downloader.login_and_save_cookies(site_name=args.site):
                print("✅ 登录和保存cookies完成！")
            else:
                print("❌ 登录失败")

            downloader.cleanup()
        except Exception as e:
            print(f"❌ 登录过程出错: {e}")
        return

    # 下载相关的逻辑
    max_books = args.count if not args.all else None

    if args.all:
        print(f"📥 准备下载所有可用的PDF")
    else:
        count_text = f"{args.count} 本" if args.count else "所有"
        print(f"📥 准备下载 {count_text} 书籍的PDF")

    if debug:
        print("🔧 调试模式已启用")

    if args.load_cookies:
        print(f"🍪 将使用cookies: {args.load_cookies}")

    print(f"🌐 语言主题: {lang}")

    try:
        print("🚀 使用独立浏览器模式")
        print("💡 启动独立Chrome浏览器实例")

        downloader = BookPDFDownloader(debug=debug, headless=args.headless, lang=lang)

        # 加载书籍数据
        book_data = downloader.load_book_data()
        if not book_data:
            print("❌ 未找到任何书籍数据")
            return

        # 开始下载
        downloader.download_pdfs(
            book_data, max_books, load_cookies_for_site=args.load_cookies
        )

    except KeyboardInterrupt:
        print("👋 程序已停止")
    except Exception as e:
        print(f"❌ 程序出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
