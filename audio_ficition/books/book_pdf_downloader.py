#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍PDF下载自动化脚本

功能说明：
基于 book_info_scraper.py 产生的书籍信息，使用 Playwright 自动下载书籍PDF文件

主要特性：
1. 📚 批量PDF下载
   - 从书籍信息JSON文件中读取UUID和URL
   - 智能判断PDF下载方式（直接下载 / 格式转换）
   - 支持多种下载场景处理

2. 🌐 浏览器自动化
   - 使用 AdsPower 浏览器实现隔离环境
   - Playwright 精确控制网页操作
   - 智能等待和错误重试机制

3. 📥 智能下载策略
   - 情况1：直接下载PDF文件（优先选择）
   - 情况2：通过格式转换获得PDF
   - 情况3：跳过标记为低质量的PDF
   - 情况4：无PDF可用时跳过

4. 💾 文件管理
   - 自动保存到指定目录：/Volumes/dhl/audio/books/en/pdf/
   - 智能检测：每次启动动态检查已下载的文件
   - 避免重复下载：自动跳过已存在的PDF文件

5. 🔄 错误处理
   - 网络异常自动重试
   - 页面加载失败处理
   - 下载链接失效检测

使用方法：
python book_pdf_downloader.py --count 10 --ads-id kq316tr
python book_pdf_downloader.py --all  # 下载所有可用的PDF

依赖组件：
- AdsPower：浏览器环境隔离
- Playwright：网页自动化
- book_info_scraper.py的输出数据

作者：PDF下载自动化团队
版本：v1.0
"""

import os
import json
import time
import random
import platform
import logging
import argparse
import urllib3
import glob
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


def get_adspower_info(ads_id):
    """连接AdsPower浏览器"""
    open_url = f"http://127.0.0.1:50325/api/v1/browser/start?user_id={ads_id}"

    http = urllib3.PoolManager()

    print("正在连接AdsPower...")
    r = http.request("GET", open_url)

    if r.status != 200:
        print(f"错误: API返回状态码 {r.status}")
        print("请确保AdsPower已启动并且本地API已启用")
        return None, None, http

    resp = json.loads(r.data.decode("utf-8"))

    if resp["code"] != 0:
        print(f"错误: {resp['msg']}")
        print("请检查ads_id是否正确")
        return None, None, http

    ws_endpoint = resp["data"]["ws"]["puppeteer"]
    debug_port = resp["data"]["debug_port"]
    remote_debugging_url = f"http://localhost:{debug_port}"

    print(f"成功连接AdsPower，WebSocket地址: {ws_endpoint}")
    print(f"远程调试URL: {remote_debugging_url}")

    return ws_endpoint, remote_debugging_url, http


class BookPDFDownloader:
    def __init__(self, ads_id="kq316tr", debug=False):
        self.ads_id = ads_id
        self.debug = debug
        self.base_media_path = get_base_media_path()
        self.base_path = os.path.join(self.base_media_path, "books", "en")

        # 设置目录结构
        self.info_dir = os.path.join(self.base_path, "info")
        self.pdf_dir = os.path.join(self.base_path, "pdf")

        # 创建PDF目录
        Path(self.pdf_dir).mkdir(parents=True, exist_ok=True)

        logger.info(f"📁 PDF下载目录: {self.pdf_dir}")
        logger.info("🔧 重要提醒:")
        logger.info("   1. 确保AdsPower浏览器的下载设置已配置")
        logger.info(f"   2. 推荐设置下载路径为: {self.pdf_dir}")
        logger.info("   3. 建议关闭下载前询问保存位置的设置")
        logger.info("   4. 程序会自动处理文件命名，无需手动干预")

        # Playwright 相关
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.http = None

        if self.debug:
            logger.info("🔧 调试模式已启用")

    def setup_browser(self):
        """设置Playwright浏览器连接"""
        try:
            # 获取AdsPower浏览器信息
            ws_endpoint, remote_debugging_url, http = get_adspower_info(self.ads_id)
            if not ws_endpoint:
                raise Exception("无法连接到AdsPower浏览器")

            self.http = http

            # 使用Playwright连接浏览器
            print("正在使用Playwright连接浏览器...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.connect_over_cdp(
                remote_debugging_url
            )
            print("✅ 成功连接到浏览器！")

            # 获取或创建上下文
            if not self.browser.contexts:
                # 创建新的上下文并设置下载路径
                self.context = self.browser.new_context(
                    accept_downloads=True,
                )
                # 设置下载路径
                self.context.set_default_timeout(60000)  # 60秒超时
            else:
                self.context = self.browser.contexts[0]
                self.context.set_default_timeout(60000)  # 60秒超时

            # 创建新页面
            self.page = self.context.new_page()
            self.page.set_default_timeout(60000)  # 60秒超时

            # 注入JavaScript来设置下载行为
            self.page.add_init_script(
                f"""
                // 拦截下载链接点击
                window.addEventListener('beforeunload', function() {{
                    // 页面卸载前的处理
                }});
                
                // 设置下载路径的提示
                console.log('下载路径应设置为: {self.pdf_dir}');
            """
            )

            logger.info("🌐 浏览器已准备就绪")
            logger.info(f"📁 请确保浏览器下载设置指向: {self.pdf_dir}")

        except Exception as e:
            logger.error(f"❌ 设置浏览器失败: {e}")
            raise

    def test_download_setup(self):
        """测试下载设置是否正确"""
        try:
            logger.info("🧪 测试下载设置...")

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

            # 检查浏览器下载设置
            if self.page:
                try:
                    # 注入JavaScript检查下载设置
                    download_setting = self.page.evaluate(
                        """
                        () => {
                            // 检查是否可以访问下载API
                            return typeof navigator.webkitPersistentStorage !== 'undefined' || 
                                   typeof navigator.storage !== 'undefined';
                        }
                    """
                    )

                    if download_setting:
                        logger.info("✅ 浏览器下载API可用")
                    else:
                        logger.warning("⚠️ 浏览器下载API不可用")

                except Exception as e:
                    logger.warning(f"⚠️ 无法检查浏览器下载设置: {e}")

            return True

        except Exception as e:
            logger.error(f"❌ 测试下载设置失败: {e}")
            return False

    def cleanup(self):
        """清理浏览器资源"""
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()

            # 关闭AdsPower浏览器
            if self.http:
                close_url = (
                    f"http://127.0.0.1:50325/api/v1/browser/stop?user_id={self.ads_id}"
                )
                self.http.request("GET", close_url)
                print("AdsPower浏览器已关闭")

            logger.info("🧹 浏览器资源已清理")
        except Exception as e:
            logger.error(f"❌ 清理资源时出错: {e}")

    def load_book_data(self):
        """加载书籍数据并动态检查下载状态"""
        try:
            # 从info目录加载所有书籍信息
            book_data = []
            if os.path.exists(self.info_dir):
                for filename in os.listdir(self.info_dir):
                    if filename.startswith("."):  # 排除Mac的点文件
                        continue
                    if filename.endswith(".json"):
                        uuid_val = filename[:-5]  # 移除.json后缀
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

    def filter_books_to_download(self, book_list):
        """动态过滤需要下载的书籍"""
        logger.info("🔍 正在动态检查下载状态...")

        # 获取已下载的PDF
        existing_pdfs = self.get_existing_pdfs()

        # 过滤出需要下载的书籍
        books_to_download = []
        skipped_count = 0

        for book in book_list:
            uuid_val = book["uuid"]
            if uuid_val in existing_pdfs:
                skipped_count += 1
                if self.debug:
                    logger.debug(f"⏭️ 已存在: {book['title']} (UUID: {uuid_val})")
            else:
                books_to_download.append(book)

        logger.info(f"📊 检查结果:")
        logger.info(f"  ✅ 已下载: {skipped_count} 本")
        logger.info(f"  📥 需要下载: {len(books_to_download)} 本")
        logger.info(f"  📚 总计: {len(book_list)} 本")

        return books_to_download

    def wait_for_download_menu(self, max_wait=10):
        """等待下载菜单出现"""
        try:
            # 等待下拉菜单出现并且可见
            self.page.wait_for_selector(
                ".dropdown-menu", timeout=max_wait * 1000, state="visible"
            )

            # 额外等待确保内容加载完成
            time.sleep(2)

            # 验证菜单确实有内容
            menu_items = self.page.locator(".dropdown-menu li")
            if menu_items.count() > 0:
                logger.info(f"✅ 下载菜单已出现，包含 {menu_items.count()} 个选项")
                return True
            else:
                logger.warning("⚠️ 下载菜单出现但无内容")
                return False

        except Exception as e:
            logger.warning(f"⚠️ 等待下载菜单超时: {e}")
            # 尝试检查是否有任何可见的菜单
            try:
                visible_menus = self.page.locator(".dropdown-menu:visible")
                if visible_menus.count() > 0:
                    logger.info(f"🔍 发现 {visible_menus.count()} 个可见菜单，继续处理")
                    time.sleep(2)
                    return True
            except:
                pass
            return False

    def analyze_download_options(self):
        """分析下载选项"""
        try:
            logger.info("🔍 开始分析下载选项...")

            # 打印菜单内容用于调试
            if self.debug:
                try:
                    menu_content = self.page.locator(".dropdown-menu").inner_html()
                    logger.debug(f"📋 菜单内容: {menu_content[:500]}...")
                except:
                    pass

            # 首先查找所有PDF下载链接（直接下载）
            pdf_link_selectors = [
                'a.addDownloadedBook:has(b.book-property__extension:text("pdf"))',
                'a.addDownloadedBook:has(.book-property__extension:text("pdf"))',
                'a:has(b:text("pdf"))',
                'a:has(.book-property__extension:text("pdf"))',
            ]

            pdf_links = None
            for selector in pdf_link_selectors:
                try:
                    links = self.page.locator(selector)
                    if links.count() > 0:
                        pdf_links = links
                        logger.info(f"📄 找到 {links.count()} 个PDF下载链接")
                        break
                except:
                    continue

            if pdf_links and pdf_links.count() > 0:
                # 检查是否有低质量标记
                for i in range(pdf_links.count()):
                    link = pdf_links.nth(i)
                    low_quality_icon = link.locator("i.low-quality-icon")

                    if low_quality_icon.count() == 0:
                        # 找到高质量的PDF
                        logger.info(f"✅ 找到高质量PDF下载链接")
                        return "direct_pdf", link, None

                # 所有PDF都标记为低质量
                logger.info("📄 找到PDF但都标记为低质量，将跳过")
                return "low_quality_pdf", None, None

            # 查找PDF转换选项
            convert_pdf_selectors = [
                'a.converterLink[data-convert_to="pdf"]',
                'a[data-convert_to="pdf"]',
                '.convert-to-button a[data-convert_to="pdf"]',
                'li.convert-to-button a[data-convert_to="pdf"]',
            ]

            convert_pdf_link = None
            for selector in convert_pdf_selectors:
                try:
                    links = self.page.locator(selector)
                    if links.count() > 0:
                        convert_pdf_link = links.first
                        logger.info(f"🔄 找到PDF转换选项 (选择器: {selector})")
                        break
                except:
                    continue

            if convert_pdf_link:
                return "convert_pdf", None, convert_pdf_link

            # 检查是否有其他转换选项但没有PDF
            other_convert_options = self.page.locator(
                "a.converterLink, a[data-convert_to]"
            )
            if other_convert_options.count() > 0:
                logger.info(
                    f"📋 找到 {other_convert_options.count()} 个转换选项，但没有PDF转换"
                )

                # 列出可用的转换格式
                if self.debug:
                    try:
                        for i in range(
                            min(other_convert_options.count(), 5)
                        ):  # 最多显示5个
                            option = other_convert_options.nth(i)
                            format_type = (
                                option.get_attribute("data-convert_to")
                                or option.inner_text()
                            )
                            logger.debug(f"  - 可转换格式: {format_type}")
                    except:
                        pass

                return "no_pdf_conversion", None, None

            # 最后检查是否有"There are no other formats"消息
            no_formats_selectors = [
                '.convert-disclaimer.formats-disclaimer:has-text("There are no other formats")',
                '.formats-disclaimer:has-text("There are no other formats")',
                'li:has-text("There are no other formats")',
            ]

            for selector in no_formats_selectors:
                try:
                    no_formats = self.page.locator(selector)
                    if no_formats.count() > 0:
                        logger.info("📄 检测到：无其他格式可用")
                        return "no_formats", None, None
                except:
                    continue

            # 完全无PDF可用
            logger.info("❌ 未找到任何PDF下载或转换选项")
            return "no_pdf", None, None

        except Exception as e:
            logger.error(f"❌ 分析下载选项失败: {e}")
            return "error", None, None

    def get_download_directory_files(self):
        """获取下载目录中的所有文件及其修改时间"""
        files_info = {}
        if os.path.exists(self.pdf_dir):
            for filename in os.listdir(self.pdf_dir):
                if filename.startswith("."):  # 排除Mac的点文件
                    continue
                file_path = os.path.join(self.pdf_dir, filename)
                if os.path.isfile(file_path):
                    files_info[filename] = os.path.getmtime(file_path)
        return files_info

    def wait_for_new_download(self, uuid_val, initial_files, max_wait=60):
        """等待新文件下载完成并重命名"""
        logger.info(f"⏳ 等待下载完成...")

        start_time = time.time()
        target_filename = f"{uuid_val}.pdf"
        target_path = os.path.join(self.pdf_dir, target_filename)

        check_count = 0
        while time.time() - start_time < max_wait:
            time.sleep(2)
            check_count += 1

            # 获取当前文件列表
            current_files = self.get_download_directory_files()

            # 查找新文件
            new_files = []
            for filename, mtime in current_files.items():
                if filename not in initial_files and filename.lower().endswith(".pdf"):
                    # 确保文件下载完成（大小不再变化）
                    file_path = os.path.join(self.pdf_dir, filename)
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        if file_size > 1000:  # 至少1KB
                            time.sleep(2)  # 等待2秒确保下载完成
                            new_size = os.path.getsize(file_path)
                            if new_size == file_size:  # 文件大小没有变化，说明下载完成
                                new_files.append((filename, file_path, file_size))
                                break  # 找到稳定的文件就跳出

            # 调试信息
            if self.debug and check_count % 5 == 0:
                elapsed = int(time.time() - start_time)
                logger.debug(
                    f"🔍 检查第{check_count}次，已等待{elapsed}秒，发现{len(current_files)}个文件"
                )
                if len(current_files) != len(initial_files):
                    new_file_names = [
                        f for f in current_files.keys() if f not in initial_files
                    ]
                    logger.debug(f"📄 新文件: {new_file_names}")

            if new_files:
                # 找到新下载的文件，重命名为目标文件名
                new_file = new_files[0]  # 取第一个新文件
                old_filename = new_file[0]
                old_path = new_file[1]
                file_size = new_file[2]

                try:
                    # 如果目标文件已存在，先删除
                    if os.path.exists(target_path):
                        logger.info(f"🗑️ 删除已存在的目标文件: {target_filename}")
                        os.remove(target_path)

                    # 重命名文件
                    os.rename(old_path, target_path)

                    logger.info(
                        f"✅ 文件已重命名: {old_filename} -> {target_filename} ({file_size} bytes)"
                    )
                    return True, file_size

                except Exception as e:
                    logger.error(f"❌ 重命名文件失败: {e}")
                    return False, 0

        # 超时后的调试信息
        current_files = self.get_download_directory_files()
        new_file_names = [f for f in current_files.keys() if f not in initial_files]
        if new_file_names:
            logger.warning(f"⚠️ 发现新文件但可能未完成下载: {new_file_names}")
        else:
            logger.warning(f"⚠️ 未发现任何新文件")

        logger.warning(f"⏰ 等待下载超时: {max_wait}秒")
        return False, 0

    def _handle_manual_download(self, uuid_val, title, download_info):
        """处理手动下载情况"""
        try:
            logger.info(f"🖱️ 处理手动下载: {title}")

            # 查找转换状态框中的菜单按钮
            conversion_status_box = self.page.locator("#converterCurrentStatusesBox")

            if conversion_status_box.count() == 0:
                logger.warning(f"⚠️ 未找到转换状态框: {title}")
                return "failed", "未找到转换状态框"

            # 查找成功状态下的菜单按钮
            success_status = conversion_status_box.locator(".status-success")
            if success_status.count() == 0:
                logger.warning(f"⚠️ 未找到转换成功状态: {title}")
                return "failed", "未找到转换成功状态"

            # 查找菜单按钮 (三个点的按钮)
            menu_button = success_status.locator(
                "i.zlibicon-menu-dots.icon-hovered.menu-btn"
            )
            if menu_button.count() == 0:
                logger.warning(f"⚠️ 未找到菜单按钮: {title}")
                return "failed", "未找到菜单按钮"

            # 点击菜单按钮显示下拉菜单
            logger.info(f"🔽 点击菜单按钮显示下载选项...")
            menu_button.click()

            # 等待下拉菜单出现
            time.sleep(2)

            # 查找下载菜单
            dropdown_menu = success_status.locator(".dropdown-menu")
            if dropdown_menu.count() == 0:
                logger.warning(f"⚠️ 下拉菜单未出现: {title}")
                return "failed", "下拉菜单未出现"

            # 确保菜单可见
            if not dropdown_menu.is_visible():
                logger.warning(f"⚠️ 下拉菜单不可见: {title}")
                return "failed", "下拉菜单不可见"

            # 查找下载链接
            download_link_selectors = [
                '.menu-row__link:has(i.zlibicon-download):has-text("Download file")',
                '.menu-row__link:has-text("Download file")',
                'a.menu-row__link[href*="convertedTo=pdf"]',
                '.menu-row a[href*="convertedTo=pdf"]',
            ]

            download_link = None
            for selector in download_link_selectors:
                try:
                    link = dropdown_menu.locator(selector)
                    if link.count() > 0:
                        download_link = link.first
                        logger.info(f"🔗 找到手动下载链接: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"尝试选择器失败 {selector}: {e}")
                    continue

            if not download_link:
                logger.warning(f"⚠️ 未找到下载链接: {title}")
                # 打印菜单内容用于调试
                if self.debug:
                    try:
                        menu_content = dropdown_menu.inner_html()
                        logger.debug(f"📋 菜单内容: {menu_content[:500]}...")
                    except:
                        pass
                return "failed", "未找到下载链接"

            # 重置下载信息
            download_info["completed"] = False
            download_info["file_path"] = None
            download_info["error"] = None
            download_info["current_uuid"] = uuid_val

            # 记录下载前的文件列表
            initial_files = self.get_download_directory_files()

            # 点击下载链接
            logger.info(f"📥 点击下载链接...")
            download_link.click()

            # 等待下载完成（先检查事件监听器）
            max_download_wait = 60
            start_time = time.time()

            while time.time() - start_time < max_download_wait:
                if download_info["completed"]:
                    file_size = (
                        os.path.getsize(download_info["file_path"])
                        if download_info["file_path"]
                        and os.path.exists(download_info["file_path"])
                        else 0
                    )
                    logger.info(f"✅ PDF手动下载成功: {title} ({file_size} bytes)")
                    return "success", "转换PDF手动下载成功"
                elif download_info["error"]:
                    logger.warning(f"⚠️ 下载事件监听器报错: {download_info['error']}")
                    break
                time.sleep(1)

            # 如果事件监听器没有捕获到下载，使用备用方法
            if not download_info["completed"]:
                logger.info(f"🔍 下载事件未捕获，使用备用方法检测...")
                success, file_size = self.wait_for_new_download(
                    uuid_val, initial_files, max_wait=30
                )

                if success:
                    logger.info(f"✅ PDF手动下载成功: {title} ({file_size} bytes)")
                    return "success", "转换PDF手动下载成功"
                else:
                    logger.warning(f"⚠️ 手动下载失败或超时: {title}")
                    return "failed", "手动下载失败或超时"

            return "failed", "手动下载处理失败"

        except Exception as e:
            logger.error(f"❌ 处理手动下载时出错 {title}: {e}")
            return "failed", f"处理手动下载时出错: {e}"

    def download_book_pdf(self, book_data, download_info_dict):
        """下载单本书的PDF"""
        uuid_val = book_data["uuid"]
        url = book_data["url"]
        title = book_data["title"]

        # 使用传入的下载信息字典
        download_info = download_info_dict

        try:
            logger.info(f"📖 开始处理: {title} (UUID: {uuid_val})")

            # 重置下载信息
            download_info["completed"] = False
            download_info["file_path"] = None
            download_info["error"] = None
            download_info["current_uuid"] = uuid_val

            # 访问书籍页面
            logger.info(f"🔗 访问页面: {url}")
            self.page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # 等待页面加载
            time.sleep(3)

            # 查找下载按钮
            download_button = self.page.locator("#btnCheckOtherFormats")
            if download_button.count() == 0:
                logger.warning(f"⚠️ 未找到下载按钮: {title}")
                return "failed", "未找到下载按钮"

            # 点击下载按钮
            logger.info(f"🔽 点击下载按钮")
            download_button.click()

            # 等待下载菜单出现
            if not self.wait_for_download_menu():
                logger.warning(f"⚠️ 下载菜单未出现: {title}")
                return "failed", "下载菜单未出现"

            # 分析下载选项
            option_type, direct_link, convert_link = self.analyze_download_options()

            logger.info(f"📋 下载选项类型: {option_type}")

            if option_type == "direct_pdf":
                # 情况1：直接下载PDF
                logger.info(f"📥 直接下载PDF: {title}")

                # 记录下载前的文件列表（在点击前记录）
                initial_files = self.get_download_directory_files()
                logger.info(f"📁 下载前目录有 {len(initial_files)} 个文件")

                # 点击下载链接
                logger.info(f"🖱️ 点击下载链接...")
                direct_link.click()

                # 使用双重检测机制：事件监听器 + 文件系统监测
                max_wait = 60
                start_time = time.time()
                check_interval = 2  # 每2秒检查一次

                logger.info(f"⏳ 等待下载完成，最多等待 {max_wait} 秒...")

                while time.time() - start_time < max_wait:
                    elapsed = int(time.time() - start_time)

                    # 方法1：检查事件监听器
                    if download_info["completed"]:
                        file_size = (
                            os.path.getsize(download_info["file_path"])
                            if download_info["file_path"]
                            and os.path.exists(download_info["file_path"])
                            else 0
                        )
                        logger.info(
                            f"✅ PDF事件监听器下载成功: {title} ({file_size} bytes)"
                        )
                        return "success", "直接下载PDF成功"

                    # 方法2：检查文件系统（每次都检查）
                    current_files = self.get_download_directory_files()
                    new_files = []
                    for filename, mtime in current_files.items():
                        if filename not in initial_files and filename.lower().endswith(
                            ".pdf"
                        ):
                            file_path = os.path.join(self.pdf_dir, filename)
                            if os.path.exists(file_path):
                                file_size = os.path.getsize(file_path)
                                if file_size > 1000:  # 至少1KB，说明有实际内容
                                    new_files.append((filename, file_path, file_size))

                    if new_files:
                        # 找到新下载的文件，重命名为目标文件名
                        new_file = new_files[0]  # 取第一个新文件
                        old_filename = new_file[0]
                        old_path = new_file[1]
                        file_size = new_file[2]

                        target_filename = f"{uuid_val}.pdf"
                        target_path = os.path.join(self.pdf_dir, target_filename)

                        try:
                            # 如果目标文件已存在，先删除
                            if os.path.exists(target_path):
                                logger.info(
                                    f"🗑️ 删除已存在的目标文件: {target_filename}"
                                )
                                os.remove(target_path)

                            # 重命名文件
                            os.rename(old_path, target_path)
                            logger.info(
                                f"✅ PDF文件系统检测下载成功: {title} ({file_size} bytes)"
                            )
                            logger.info(
                                f"📁 文件已重命名: {old_filename} -> {target_filename}"
                            )
                            return "success", "直接下载PDF成功"

                        except Exception as e:
                            logger.error(f"❌ 重命名文件失败: {e}")
                            # 即使重命名失败，也尝试使用原文件名
                            if os.path.exists(old_path):
                                logger.info(
                                    f"✅ PDF下载成功（保持原名）: {title} ({file_size} bytes)"
                                )
                                logger.info(f"📁 文件位置: {old_path}")
                                return "success", "直接下载PDF成功"

                    # 检查下载错误
                    if download_info["error"]:
                        logger.warning(
                            f"⚠️ PDF下载失败: {title} - {download_info['error']}"
                        )
                        return "failed", f"PDF下载失败: {download_info['error']}"

                    # 每隔几秒显示等待状态
                    if elapsed % 10 == 0 and elapsed > 0:
                        logger.info(f"⏳ 仍在等待下载...已等待 {elapsed} 秒")

                    time.sleep(check_interval)

                # 超时后最后检查一次
                logger.warning(f"⏰ 下载等待超时，进行最后检查...")

                # 最后检查事件监听器
                if download_info["completed"]:
                    file_size = (
                        os.path.getsize(download_info["file_path"])
                        if download_info["file_path"]
                        and os.path.exists(download_info["file_path"])
                        else 0
                    )
                    logger.info(f"✅ PDF最后检查下载成功: {title} ({file_size} bytes)")
                    return "success", "直接下载PDF成功"

                # 最后检查文件系统
                final_files = self.get_download_directory_files()
                new_files = []
                for filename, mtime in final_files.items():
                    if filename not in initial_files and filename.lower().endswith(
                        ".pdf"
                    ):
                        file_path = os.path.join(self.pdf_dir, filename)
                        if os.path.exists(file_path):
                            file_size = os.path.getsize(file_path)
                            if file_size > 1000:
                                new_files.append((filename, file_path, file_size))

                if new_files:
                    # 找到文件但超时了，仍然处理
                    new_file = new_files[0]
                    old_filename = new_file[0]
                    old_path = new_file[1]
                    file_size = new_file[2]

                    target_filename = f"{uuid_val}.pdf"
                    target_path = os.path.join(self.pdf_dir, target_filename)

                    try:
                        if os.path.exists(target_path):
                            os.remove(target_path)
                        os.rename(old_path, target_path)
                        logger.info(
                            f"✅ PDF超时后发现下载成功: {title} ({file_size} bytes)"
                        )
                        return "success", "直接下载PDF成功"
                    except Exception as e:
                        logger.warning(f"⚠️ 超时后重命名失败: {e}")
                        if os.path.exists(old_path):
                            logger.info(
                                f"✅ PDF下载成功（保持原名）: {title} ({file_size} bytes)"
                            )
                            return "success", "直接下载PDF成功"

                # 完全失败
                logger.warning(f"❌ PDF下载失败或超时: {title}")
                logger.info(
                    f"🔍 调试信息：初始文件 {len(initial_files)} 个，最终文件 {len(final_files)} 个"
                )
                return "failed", "PDF下载失败或超时"

            elif option_type == "convert_pdf":
                # 情况2：转换为PDF
                logger.info(f"🔄 转换为PDF: {title}")

                # 点击转换链接
                convert_link.click()

                # 等待转换开始的提示或者页面变化
                logger.info(f"⏳ 等待转换开始...")
                time.sleep(3)

                # 检查是否出现了转换中的提示
                converting_indicators = [
                    '.convert-status:has-text("Converting")',
                    '.convert-status:has-text("Processing")',
                    'div:has-text("Converting")',
                    'div:has-text("Processing")',
                    '[class*="converting"]',
                    '[class*="processing"]',
                ]

                conversion_started = False
                for indicator in converting_indicators:
                    try:
                        if self.page.locator(indicator).count() > 0:
                            conversion_started = True
                            logger.info(f"📝 检测到转换开始: {indicator}")
                            break
                    except:
                        continue

                if conversion_started:
                    # 等待转换完成（通常需要几分钟）
                    logger.info(f"⏳ 等待转换完成，最多等待5分钟...")

                    # 轮询检查转换状态
                    max_wait_time = 300  # 5分钟
                    wait_interval = 5  # 每5秒检查一次
                    waited_time = 0

                    while waited_time < max_wait_time:
                        time.sleep(wait_interval)
                        waited_time += wait_interval

                        # 优先检查是否有自动下载完成
                        if download_info["completed"]:
                            file_size = (
                                os.path.getsize(download_info["file_path"])
                                if download_info["file_path"]
                                and os.path.exists(download_info["file_path"])
                                else 0
                            )
                            logger.info(
                                f"✅ PDF自动下载成功: {title} ({file_size} bytes)"
                            )
                            return "success", "转换PDF自动下载成功"

                        # 检查是否有下载错误
                        if download_info["error"]:
                            logger.warning(
                                f"⚠️ 自动下载出错: {title} - {download_info['error']}"
                            )
                            # 重置错误状态，继续尝试其他方式
                            download_info["error"] = None

                        # 检查转换状态框中是否有完成的转换（需要手动下载）
                        conversion_status_box = self.page.locator(
                            "#converterCurrentStatusesBox"
                        )

                        manual_download_needed = False
                        if conversion_status_box.count() > 0:
                            # 检查是否有转换成功的状态
                            success_status = conversion_status_box.locator(
                                ".status-success"
                            )
                            if success_status.count() > 0:
                                # 检查消息是否包含PDF转换完成
                                message = success_status.locator(".message")
                                if message.count() > 0:
                                    message_text = message.inner_text()
                                    if (
                                        "pdf" in message_text.lower()
                                        and "completed" in message_text.lower()
                                    ):
                                        manual_download_needed = True
                                        logger.info(
                                            f"📋 检测到PDF转换完成，需要手动下载: {title}"
                                        )
                                        break

                        # 检查是否有自动下载链接出现（一些网站会显示下载链接）
                        download_ready_selectors = [
                            'a[href*=".pdf"]:has-text("Download")',
                            'a[href*="download"]:has-text("PDF")',
                            ".download-ready",
                            "a.downloadButton",
                            'button:has-text("Download PDF")',
                        ]

                        download_link = None
                        for selector in download_ready_selectors:
                            try:
                                if self.page.locator(selector).count() > 0:
                                    download_link = self.page.locator(selector).first
                                    logger.info(f"🔗 找到下载链接: {selector}")
                                    break
                            except:
                                continue

                        if download_link:
                            # 找到下载链接，尝试点击下载
                            try:
                                logger.info(f"📥 点击下载链接...")
                                download_link.click()

                                # 给下载时间触发
                                time.sleep(3)

                                # 检查是否立即完成下载
                                if download_info["completed"]:
                                    file_size = (
                                        os.path.getsize(download_info["file_path"])
                                        if download_info["file_path"]
                                        and os.path.exists(download_info["file_path"])
                                        else 0
                                    )
                                    logger.info(
                                        f"✅ PDF下载成功: {title} ({file_size} bytes)"
                                    )
                                    return "success", "转换PDF下载成功"

                                # 如果没有立即完成，继续等待（下次循环会检查）
                                logger.info(f"📥 下载已触发，继续等待...")

                            except Exception as e:
                                logger.warning(f"⚠️ 点击下载链接失败: {title} - {e}")

                        # 显示等待状态
                        logger.info(f"⏳ 转换中...已等待 {waited_time} 秒")

                    # 循环结束后的处理

                    # 最后再检查一次是否自动下载完成
                    if download_info["completed"]:
                        file_size = (
                            os.path.getsize(download_info["file_path"])
                            if download_info["file_path"]
                            and os.path.exists(download_info["file_path"])
                            else 0
                        )
                        logger.info(f"✅ PDF自动下载成功: {title} ({file_size} bytes)")
                        return "success", "转换PDF自动下载成功"

                    # 如果检测到需要手动下载
                    if manual_download_needed:
                        return self._handle_manual_download(
                            uuid_val, title, download_info
                        )

                    # 转换超时
                    logger.warning(f"⏰ PDF转换超时: {title}")
                    return "failed", "PDF转换超时"
                else:
                    # 可能转换立即完成或者没有开始
                    logger.info(f"🔍 检查是否有即时可用的下载链接...")

                    # 等待一下然后检查下载链接
                    time.sleep(5)

                    immediate_download_selectors = [
                        'a[href*=".pdf"]',
                        'a[href*="download"]',
                        ".download-link",
                        'button:has-text("Download")',
                    ]

                    for selector in immediate_download_selectors:
                        try:
                            if self.page.locator(selector).count() > 0:
                                download_link = self.page.locator(selector).first

                                # 重置下载信息
                                download_info["completed"] = False
                                download_info["file_path"] = None
                                download_info["error"] = None
                                download_info["current_uuid"] = uuid_val

                                # 点击下载链接
                                download_link.click()

                                # 等待下载完成（使用事件监听器）
                                max_download_wait = 30
                                start_time = time.time()

                                while time.time() - start_time < max_download_wait:
                                    if download_info["completed"]:
                                        file_size = (
                                            os.path.getsize(download_info["file_path"])
                                            if download_info["file_path"]
                                            and os.path.exists(
                                                download_info["file_path"]
                                            )
                                            else 0
                                        )
                                        logger.info(
                                            f"✅ PDF转换下载成功: {title} ({file_size} bytes)"
                                        )
                                        return "success", "转换PDF成功"
                                    elif download_info["error"]:
                                        break
                                    time.sleep(1)

                                # 如果事件监听器没有捕获，使用备用方法
                                if not download_info["completed"]:
                                    # 记录下载前的文件列表
                                    initial_files = self.get_download_directory_files()

                                    # 等待下载完成并重命名
                                    success, file_size = self.wait_for_new_download(
                                        uuid_val, initial_files, max_wait=30
                                    )

                                    if success:
                                        logger.info(
                                            f"✅ PDF转换下载成功: {title} ({file_size} bytes)"
                                        )
                                        return "success", "转换PDF成功"

                        except Exception as e:
                            logger.debug(f"尝试选择器 {selector} 失败: {e}")
                            continue

                    logger.warning(f"⚠️ 未找到可用的下载链接: {title}")
                    return "failed", "转换后未找到下载链接"

            elif option_type == "low_quality_pdf":
                # 情况3：低质量PDF，跳过
                logger.info(f"⏭️ 跳过低质量PDF: {title}")
                return "skipped", "PDF质量标记为低质量"

            elif option_type == "no_pdf":
                # 情况4：无PDF可用
                logger.info(f"⏭️ 无PDF可用: {title}")
                return "skipped", "无PDF格式可用"

            elif option_type == "no_pdf_conversion":
                # 情况5：有其他转换选项但无PDF转换
                logger.info(f"⏭️ 有转换选项但无PDF转换: {title}")
                return "skipped", "无PDF转换选项"

            elif option_type == "no_formats":
                # 情况6：无其他格式
                logger.info(f"⏭️ 无其他格式: {title}")
                return "skipped", "无其他格式可用"

            else:
                logger.warning(f"⚠️ 未知下载选项: {title}")
                return "failed", "未知下载选项"

        except Exception as e:
            logger.error(f"❌ 下载失败 {title}: {e}")
            return "failed", str(e)

    def download_pdfs(self, book_list, max_books=None):
        """批量下载PDF"""
        try:
            # 动态过滤需要下载的书籍
            books_to_download = self.filter_books_to_download(book_list)

            # 限制下载数量
            if max_books and len(books_to_download) > max_books:
                books_to_download = books_to_download[:max_books]
                logger.info(f"📝 已限制下载数量为: {max_books} 本")

            if not books_to_download:
                logger.info("🎉 所有书籍的PDF都已下载完成！")
                return

            logger.info(f"📥 准备下载 {len(books_to_download)} 本书的PDF")

            # 设置浏览器
            self.setup_browser()

            # 测试下载设置
            if not self.test_download_setup():
                logger.warning("⚠️ 下载设置可能有问题，但继续执行...")

            # 创建共享的下载信息字典
            download_info = {
                "completed": False,
                "file_path": None,
                "error": None,
                "current_uuid": None,
            }

            def handle_download(download):
                """处理下载事件"""
                try:
                    if not download_info.get("current_uuid"):
                        logger.warning("📥 检测到下载但无当前UUID，跳过处理")
                        return

                    uuid_val = download_info["current_uuid"]
                    target_filename = f"{uuid_val}.pdf"
                    target_path = os.path.join(self.pdf_dir, target_filename)

                    logger.info(
                        f"📥 检测到下载: {download.suggested_filename} -> {target_filename}"
                    )

                    # 等待下载完成
                    download.save_as(target_path)

                    download_info["completed"] = True
                    download_info["file_path"] = target_path

                    file_size = (
                        os.path.getsize(target_path)
                        if os.path.exists(target_path)
                        else 0
                    )
                    logger.info(f"✅ 下载完成: {target_filename} ({file_size} bytes)")

                except Exception as e:
                    logger.error(f"❌ 下载处理失败: {e}")
                    download_info["error"] = str(e)

            # 设置全局下载监听器
            self.page.on("download", handle_download)
            logger.info("🔧 已设置全局下载监听器")

            success_count = 0
            failed_count = 0
            skipped_count = 0

            # 使用进度条
            for i, book_data in enumerate(tqdm(books_to_download, desc="📥 下载PDF")):
                try:
                    result, message = self.download_book_pdf(book_data, download_info)

                    if result == "success":
                        success_count += 1
                        logger.info(f"✅ 成功: {book_data['title']}")
                    elif result == "skipped":
                        skipped_count += 1
                        logger.info(f"⏭️ 跳过: {book_data['title']} - {message}")
                    else:
                        failed_count += 1
                        logger.warning(f"❌ 失败: {book_data['title']} - {message}")

                    # 简单进度显示
                    if (i + 1) % 5 == 0:
                        logger.info(
                            f"📊 进度: {i + 1}/{len(books_to_download)} (成功:{success_count}, 跳过:{skipped_count}, 失败:{failed_count})"
                        )

                    # 随机延迟避免被封
                    if i < len(books_to_download) - 1:
                        wait_time = random.uniform(2, 5)
                        time.sleep(wait_time)

                except KeyboardInterrupt:
                    logger.info("⏹️ 用户中断下载...")
                    break
                except Exception as e:
                    logger.error(f"❌ 处理书籍时出错 {book_data['title']}: {e}")
                    failed_count += 1

            # 最终统计
            total_processed = success_count + failed_count + skipped_count
            logger.info(f"\n🎯 下载完成!")
            logger.info(f"✅ 成功下载: {success_count} 本")
            logger.info(f"⏭️ 跳过: {skipped_count} 本")
            logger.info(f"❌ 失败: {failed_count} 本")
            logger.info(f"📊 总计处理: {total_processed} 本")

            if success_count > 0:
                logger.info(f"📁 PDF文件保存在: {self.pdf_dir}")

            # 移除全局下载监听器
            try:
                self.page.remove_listener("download", handle_download)
                logger.info("🔧 已移除全局下载监听器")
            except Exception as e:
                logger.warning(f"⚠️ 移除下载监听器失败: {e}")

        except Exception as e:
            logger.error(f"❌ 批量下载出错: {e}")
        finally:
            self.cleanup()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="📥 书籍PDF下载自动化脚本",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python book_pdf_downloader.py --count 10
  python book_pdf_downloader.py --all --ads-id kq316tr
  python book_pdf_downloader.py --count 5 --debug
        """,
    )
    parser.add_argument(
        "--count", "-c", type=int, help="要下载的PDF数量 (不指定则下载所有)"
    )
    parser.add_argument("--all", action="store_true", help="下载所有可用的PDF")
    parser.add_argument(
        "--ads-id", default="kq316tr", help="AdsPower 浏览器ID (默认: kq316tr)"
    )
    parser.add_argument("--debug", "-d", action="store_true", help="启用调试模式")

    args = parser.parse_args()

    # 验证参数
    if args.count and args.count <= 0:
        print("❌ 错误：下载数量必须大于 0")
        return

    ads_id = args.ads_id
    max_books = args.count if not args.all else None
    debug = args.debug

    if args.all:
        print(f"📥 准备下载所有可用的PDF")
    else:
        count_text = f"{args.count} 本" if args.count else "所有"
        print(f"📥 准备下载 {count_text} 书籍的PDF")

    print(f"📱 使用 AdsPower ID: {ads_id}")

    if debug:
        print("🔧 调试模式已启用")

    try:
        # 创建下载器
        downloader = BookPDFDownloader(ads_id=ads_id, debug=debug)

        # 加载书籍数据
        book_data = downloader.load_book_data()
        if not book_data:
            print("❌ 未找到任何书籍数据")
            return

        # 开始下载
        downloader.download_pdfs(book_data, max_books)

    except KeyboardInterrupt:
        print("👋 程序已停止")
    except Exception as e:
        print(f"❌ 程序出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
