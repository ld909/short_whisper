#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍YouTube上传脚本
上传 merge_clips_with_audio.py 产生的MP4文件到YouTube
支持中文和英文书籍上传到不同的YouTube频道

📚 功能说明:
- 支持中文和英文书籍处理（通过 --language 参数选择）
- 读取对应语言的Excel文件，获取待上传的书籍列表
- 从 merge_clips_with_audio.py 的输出中读取MP4视频文件
- 使用 generate_youtube_titles.py 的逻辑生成标题
- 组合描述和hashtags作为视频描述
- 自动选择对应语言的YouTube频道进行上传
- 支持设定视频间隔时间
- 智能Tab管理：每次上传使用新tab，达到限制后等待并清理
- 更新Excel状态

🌍 语言支持:
- 英文 (en): books/en/ 目录，book-en.xlsx 文件
- 中文 (zh): books/zh/ 目录，book-zh.xlsx 文件

📥 输入信息:
- Excel文件: excel/book-{language}.xlsx (列名: UUID | 是否发布 | 发布时间)
- MP4文件: {media_path}/books/{language}/mp4_with_audio/{uuid}.mp4
- 封面文件: {media_path}/books/{language}/ytb_cover/{uuid}.png
- 标题信息: {media_path}/books/{language}/info/{uuid}.json
- 描述文件: {media_path}/books/{language}/youtube_description/{uuid}.txt
- 标签文件: {media_path}/books/{language}/youtube_hashtags/{uuid}.txt

📤 输出信息:
- YouTube视频上传到对应语言的频道
- 更新的Excel状态文件

🔄 处理规则:
1. 支持macOS（Intel和Apple Silicon）和Ubuntu系统
2. 媒体路径配置：
   - Intel Mac: /Volumes/dhl/audio
   - Apple Silicon Mac: /Users/donghaoliu/Documents/audio
   - Ubuntu: /media/dhl/audio
3. 支持断点续传，跳过已上传的视频（是否发布=1）
4. 自动排除以点开头的Mac系统文件
5. 根据语言使用对应的浏览器ID：
   - 英文书籍: k10i5y1s
   - 中文书籍: k10i7fjt
6. 根据语言自动选择对应的YouTube频道：
   - 英文频道: https://studio.youtube.com/channel/UCe4grZMmPMmnMcIoaTJc05w
   - 中文频道: https://studio.youtube.com/channel/UCW0Or8f_oWL2V8QQzob-DQw
7. 可设定视频上传间隔时间

💡 使用示例:
# 上传中文书籍
python upload_books_to_youtube.py --language zh

# 上传英文书籍，设定4小时间隔
python upload_books_to_youtube.py --language en --interval 4

# 中文书籍限制上传数量
python upload_books_to_youtube.py --language zh --max-count 3

# 试运行模式查看待上传的中文书籍
python upload_books_to_youtube.py --language zh --dry-run
"""

import os
import sys
import time
import json
import random
import argparse
import platform
import urllib3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright
from tqdm import tqdm
from typing import Optional, Dict, List, Tuple

# ============ 配置参数 ============
# YouTube频道配置
YOUTUBE_CHANNELS = {
    "en": "https://studio.youtube.com/channel/UCe4grZMmPMmnMcIoaTJc05w",  # 英文频道
    "zh": "https://studio.youtube.com/channel/UCW0Or8f_oWL2V8QQzob-DQw",  # 中文频道
}

# AdsPower浏览器ID配置
ADSPOWER_BROWSER_IDS = {
    "en": "k10i5y1s",  # 英文浏览器
    "zh": "k10i7fjt",  # 中文浏览器
}

# 标题配置
MAX_TITLE_LENGTH = 99
TITLE_SUFFIX = {
    "en": " | Book Summary",
    "zh": " | 书籍总结",
}

# 最小文件大小检查
MIN_MP4_SIZE = 1024 * 1024 * 5  # 5MB
MIN_COVER_SIZE = 1024 * 10  # 10KB
MIN_INFO_SIZE = 100  # 100字节

# 默认发布间隔
DEFAULT_INTERVAL_HOURS = 4

# Excel文件路径配置
EXCEL_FILES = {
    "en": "excel/book-en.xlsx",
    "zh": "excel/book-zh.xlsx",
}


def get_base_media_path():
    """根据操作系统和芯片类型返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        # 检查芯片类型
        arch = platform.machine()
        if arch == "x86_64":  # Intel Mac
            return "/Volumes/dhl/audio"
        else:  # Apple Silicon (arm64)
            return "/Users/donghaoliu/Documents/audio"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/audio"


def get_directories(language="en"):
    """获取所有相关目录路径"""
    base_media_path = get_base_media_path()
    books_path = os.path.join(base_media_path, "books", language)

    return {
        "mp4": os.path.join(books_path, "mp4_with_audio"),
        "covers": os.path.join(books_path, "ytb_cover"),
        "info": os.path.join(books_path, "info"),
        "descriptions": os.path.join(books_path, "youtube_description"),
        "hashtags": os.path.join(books_path, "youtube_hashtags"),
        "excel": EXCEL_FILES[language],
    }


def check_supported_system():
    """检查是否为支持的系统（macOS或Ubuntu）"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return True
    elif system == "Linux":  # Linux/Ubuntu
        return True
    else:
        return False


def is_valid_file(file_path: str, min_size: int = 1024) -> bool:
    """检查文件是否有效"""
    if not os.path.exists(file_path):
        return False

    # 排除Mac系统产生的点开头文件
    filename = os.path.basename(file_path)
    if filename.startswith(".") or filename.startswith("._"):
        return False

    try:
        file_size = os.path.getsize(file_path)
        if file_size < min_size:
            return False
        return True
    except Exception:
        return False


def countdown_timer(total_seconds, description="等待中"):
    """在终端显示倒计时"""
    print(f"\n⏰ {description}...")

    while total_seconds > 0:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            time_str = f"{minutes:02d}:{seconds:02d}"

        print(f"\r⏱️  剩余时间: {time_str}", end="", flush=True)
        time.sleep(1)
        total_seconds -= 1

    print(f"\r✅ {description}完成！" + " " * 20)
    print()


class BookYouTubeUploader:
    def __init__(
        self,
        language="en",
        interval_hours=DEFAULT_INTERVAL_HOURS,
        max_tabs=6,
        wait_minutes=30,
    ):
        self.language = language
        self.interval_hours = interval_hours
        self.directories = get_directories(language)
        self.browser_id = ADSPOWER_BROWSER_IDS[language]
        self.studio_url = YOUTUBE_CHANNELS[language]
        self.max_tabs = max_tabs  # 最大tab数量
        self.wait_minutes = wait_minutes  # tab限制时等待分钟数
        self.http = None

        # tab管理相关
        self.current_tabs = []  # 当前打开的tab列表
        self.context = None  # 浏览器上下文

        # 设置语言配置
        self.setup_language_config()

        print(f"📚 书籍YouTube上传系统初始化")
        print(f"🌍 语言设置: {self.language_name}")
        print(f"⏱️  发布间隔: {self.interval_hours} 小时")
        print(f"🌐 YouTube频道: {self.studio_url}")
        print(f"🖥️  浏览器ID: {self.browser_id}")
        print(f"📁 Excel文件: {self.directories['excel']}")
        print(f"📑 最大tab数量: {self.max_tabs}")
        print(f"⏳ tab限制等待时间: {self.wait_minutes} 分钟")

    def setup_language_config(self):
        """根据语种设置配置"""
        if self.language == "zh":
            # 中文配置
            self.language_name = "中文"
        else:
            # 英文配置（默认）
            self.language_name = "English"

    def load_book_info(self, uuid: str) -> Optional[Dict]:
        """加载书籍基本信息"""
        info_file = os.path.join(self.directories["info"], f"{uuid}.json")

        if not is_valid_file(info_file, MIN_INFO_SIZE):
            return None

        try:
            with open(info_file, "r", encoding="utf-8") as f:
                book_info = json.load(f)

            if not book_info.get("title"):
                print(f"⚠️  [UUID:{uuid[:8]}...] 书籍信息缺少标题")
                return None

            return book_info
        except Exception as e:
            print(f"❌ [UUID:{uuid[:8]}...] 读取书籍信息失败: {e}")
            return None

    def generate_youtube_title(self, book_title: str) -> str:
        """生成YouTube标题（参考generate_youtube_titles.py）"""
        # 清理书名
        book_title = " ".join(book_title.split()).strip()

        # 构建基础标题格式
        title_template = "{}" + TITLE_SUFFIX[self.language]

        # 计算可用于书名的最大字符数
        max_book_title_length = MAX_TITLE_LENGTH - len(title_template.format(""))

        # 如果书名太长，截断并添加...
        if len(book_title) > max_book_title_length:
            truncate_length = max_book_title_length - 3
            book_title = book_title[:truncate_length].rstrip() + "..."

        # 生成最终标题
        final_title = title_template.format(book_title)

        # 最终检查长度
        if len(final_title) > MAX_TITLE_LENGTH:
            final_title = final_title[: MAX_TITLE_LENGTH - 3] + "..."

        return final_title

    def get_book_description(self, uuid: str) -> str:
        """获取书籍描述（描述文件 + 换行 + hashtags文件）"""
        description_parts = []

        # 读取描述文件
        desc_file = os.path.join(self.directories["descriptions"], f"{uuid}.txt")
        if os.path.exists(desc_file):
            try:
                with open(desc_file, "r", encoding="utf-8") as f:
                    description = f.read().strip()
                    if description:
                        description_parts.append(description)
            except Exception as e:
                print(f"⚠️  读取描述文件失败: {e}")

        # 读取hashtags文件
        hashtags_file = os.path.join(self.directories["hashtags"], f"{uuid}.txt")
        if os.path.exists(hashtags_file):
            try:
                with open(hashtags_file, "r", encoding="utf-8") as f:
                    hashtags = f.read().strip()
                    if hashtags:
                        description_parts.append(hashtags)
            except Exception as e:
                print(f"⚠️  读取hashtags文件失败: {e}")

        # 如果没有内容，使用默认描述
        if not description_parts:
            description_parts.append(
                "Explore this captivating book summary that brings literature to life!"
            )

        # 用两个换行符连接
        return "\n\n".join(description_parts)

    def get_book_content(self, book_info):
        """获取书籍的完整内容（标题、描述、封面等）"""
        uuid = book_info["uuid"]
        mp4_path = book_info["mp4_path"]

        print(f"📖 [UUID:{uuid[:8]}...] 获取书籍内容...")

        # 加载书籍基本信息
        info = self.load_book_info(uuid)
        if not info:
            print(f"❌ [UUID:{uuid[:8]}...] 无法加载书籍信息")
            return None

        # 生成标题
        title = self.generate_youtube_title(info["title"])
        print(f"🎬 [UUID:{uuid[:8]}...] 标题: {title}")

        # 获取描述
        description = self.get_book_description(uuid)
        print(f"📝 [UUID:{uuid[:8]}...] 描述长度: {len(description)} 字符")

        # 检查封面文件
        cover_path = os.path.join(self.directories["covers"], f"{uuid}.png")
        cover_exists = is_valid_file(cover_path, MIN_COVER_SIZE)

        if cover_exists:
            print(f"🖼️  [UUID:{uuid[:8]}...] 封面文件: 存在")
        else:
            print(f"⚠️  [UUID:{uuid[:8]}...] 封面文件: 不存在")
            cover_path = None

        return {
            "uuid": uuid,
            "mp4_path": mp4_path,
            "title": title,
            "description": description,
            "thumbnail_path": cover_path,
            "book_title": info["title"],
            "valid": True,
        }

    def get_adspower_info(self):
        """连接AdsPower浏览器"""
        open_url = f"http://local.adspower.net:50325/api/v1/browser/start?user_id={self.browser_id}"

        self.http = urllib3.PoolManager()

        print("🔌 正在连接AdsPower...")
        r = self.http.request("GET", open_url)

        if r.status != 200:
            print(f"❌ API返回状态码 {r.status}")
            return None, None

        resp = json.loads(r.data.decode("utf-8"))

        if resp["code"] != 0:
            print(f"❌ 错误: {resp['msg']}")
            return None, None

        ws_endpoint = resp["data"]["ws"]["puppeteer"]
        debug_port = resp["data"]["debug_port"]
        remote_debugging_url = f"http://localhost:{debug_port}"

        print(f"✅ 成功连接AdsPower")
        return ws_endpoint, remote_debugging_url

    def initialize_browser(self, max_retries=3):
        """初始化浏览器"""
        print("🔄 正在初始化浏览器...")

        for attempt in range(max_retries):
            print(f"📡 尝试连接浏览器 (第 {attempt + 1}/{max_retries} 次)...")

            # 连接AdsPower
            ws_endpoint, remote_debugging_url = self.get_adspower_info()
            if not ws_endpoint:
                if attempt < max_retries - 1:
                    countdown_timer(5, "等待重试")
                    continue
                else:
                    return None, None, None

            playwright = None
            try:
                playwright = sync_playwright().start()
                browser = playwright.chromium.connect_over_cdp(
                    remote_debugging_url, timeout=15000
                )

                if not browser.contexts:
                    context = browser.new_context()
                    print("📝 创建了新的浏览器上下文")
                else:
                    context = browser.contexts[0]
                    print("📝 使用现有的浏览器上下文")

                # 保存上下文引用
                self.context = context

                # 关闭现有tab
                existing_pages = context.pages
                for page in existing_pages:
                    try:
                        page.close()
                    except:
                        pass

                # 创建新tab
                new_page = context.new_page()
                self.current_tabs = [new_page]

                return playwright, browser, new_page

            except Exception as e:
                print(f"❌ 浏览器连接失败 (第 {attempt + 1} 次): {e}")
                if playwright:
                    try:
                        playwright.stop()
                    except:
                        pass

                if attempt < max_retries - 1:
                    countdown_timer(10, "等待重试")
                    continue

        return None, None, None

    def create_new_tab_for_upload(self):
        """为书籍上传创建新tab"""
        if not self.context:
            print("❌ 浏览器上下文不存在，无法创建新tab")
            return None

        try:
            print(f"🆕 正在创建新tab (当前数量: {len(self.current_tabs)})...")
            new_page = self.context.new_page()
            self.current_tabs.append(new_page)
            print(f"✅ 已创建新tab，当前总数: {len(self.current_tabs)}")
            return new_page
        except Exception as e:
            print(f"❌ 创建新tab失败: {e}")
            return None

    def check_and_wait_for_tab_limit(self):
        """检查tab数量，达到限制时等待，然后关闭所有tab并创建新tab"""
        if len(self.current_tabs) >= self.max_tabs:
            print(f"📑 已达到tab数量限制 ({len(self.current_tabs)}/{self.max_tabs})")

            # 使用倒计时功能
            total_seconds = self.wait_minutes * 60
            countdown_timer(total_seconds, f"Tab数量限制等待 {self.wait_minutes} 分钟")

            print("🧹 等待时间结束，开始关闭所有tab...")

            # 关闭所有现有tab（认为上传工作已完成）
            closed_count = 0
            for tab in self.current_tabs:
                try:
                    print(f"❌ 关闭tab: {tab.url[:50]}...")
                    tab.close()
                    closed_count += 1
                except Exception as e:
                    print(f"⚠️  关闭tab时出错: {e}")

            print(f"✅ 已关闭 {closed_count} 个tab")

            # 清空tab列表
            self.current_tabs = []

            # 创建一个新的tab继续工作
            print("🆕 正在创建新的工作tab...")
            new_tab = self.create_new_tab_for_upload()
            if new_tab:
                print("✅ 已创建新的工作tab，继续处理...")
                return new_tab  # 返回新创建的tab
            else:
                print("❌ 创建新tab失败")
                return None

        return False

    def cleanup_closed_tabs(self):
        """清理已关闭的tab"""
        active_tabs = []
        for tab in self.current_tabs:
            try:
                # 尝试访问tab的URL来检查是否仍然有效
                _ = tab.url
                active_tabs.append(tab)
            except Exception:
                # tab已关闭或无效
                pass

        removed_count = len(self.current_tabs) - len(active_tabs)
        if removed_count > 0:
            print(f"🧹 清理了 {removed_count} 个已关闭的tab")

        self.current_tabs = active_tabs
        if len(self.current_tabs) > 0:
            print(f"📑 当前活跃tab数量: {len(self.current_tabs)}")
        else:
            print(f"📑 当前无活跃tab")

    def calculate_next_publish_time(self):
        """计算下一个发布时间"""
        print(f"⏰ 计算下一个发布时间...")

        excel_file = self.directories["excel"]
        current_time = datetime.now()

        try:
            # 读取Excel获取最远发布时间
            df = pd.read_excel(excel_file)

            # 查找已发布的视频（使用中文列名）
            if "是否发布" in df.columns and "发布时间" in df.columns:
                published = df[df["是否发布"] == 1]

                if len(published) > 0:
                    # 获取发布时间列，排除空值
                    publish_times = published["发布时间"].dropna()

                    if len(publish_times) > 0:
                        # 转换为datetime并找到最远时间
                        publish_times_dt = pd.to_datetime(publish_times)
                        max_time = max(publish_times_dt)

                        # 如果最远时间大于当前时间，使用最远时间
                        if max_time > current_time:
                            base_time = max_time
                        else:
                            base_time = current_time
                    else:
                        base_time = current_time
                else:
                    base_time = current_time
            else:
                base_time = current_time

        except Exception as e:
            print(f"⚠️  读取发布时间失败，使用当前时间: {e}")
            base_time = current_time

        # 计算下一个发布时间
        next_time = base_time + timedelta(hours=self.interval_hours)

        print(f"📅 基准时间: {base_time}")
        print(f"➕ 间隔时间: {self.interval_hours} 小时")
        print(f"📅 下一个发布时间: {next_time}")

        return next_time

    def get_pending_books(self):
        """获取待上传的书籍列表"""
        print(f"\n🔍 扫描待上传的书籍...")

        excel_file = self.directories["excel"]
        if not os.path.exists(excel_file):
            print(f"❌ Excel文件不存在: {excel_file}")
            print(f"💡 请先运行: python generate_book_publish_excel.py")
            return []

        try:
            # 读取Excel文件
            df = pd.read_excel(excel_file)
            print(f"📊 Excel文件共 {len(df)} 条记录")

            # 过滤待上传的书籍（使用中文列名）
            if "是否发布" not in df.columns:
                print(f"❌ Excel文件缺少 '是否发布' 列")
                return []

            pending = df[df["是否发布"] == 0]
            print(f"📝 待上传书籍: {len(pending)} 个")

            # 检查对应的MP4文件是否存在
            valid_pending = []
            for _, row in pending.iterrows():
                # 获取UUID (假设第一列为UUID)
                uuid = row.iloc[0] if len(row) > 0 else None
                if not uuid:
                    continue

                # 排除以点开头的UUID（Mac系统文件）
                if str(uuid).startswith("."):
                    continue

                # 检查MP4文件
                mp4_path = os.path.join(self.directories["mp4"], f"{uuid}.mp4")
                if is_valid_file(mp4_path, MIN_MP4_SIZE):
                    book_info = {
                        "uuid": uuid,
                        "mp4_path": mp4_path,
                        "excel_row": row.name,  # 行索引
                    }
                    valid_pending.append(book_info)
                    print(f"✅ 有效书籍: {uuid}")
                else:
                    print(f"❌ MP4文件不存在或无效: {uuid}")

            print(f"✅ 最终有效书籍: {len(valid_pending)} 个")
            return valid_pending

        except Exception as e:
            print(f"❌ 读取Excel文件时出错: {e}")
            return []

    def format_publish_time(self, publish_time):
        """格式化发布时间为YouTube需要的格式"""
        month_names = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]

        # 格式化日期: "Dec 2, 2025"
        date_str = f"{month_names[publish_time.month - 1]} {publish_time.day}, {publish_time.year}"

        # 格式化时间: "12:00 AM" 或 "10:15 PM"
        hour = publish_time.hour
        minute = publish_time.minute

        if hour == 0:
            time_str = f"12:{minute:02d} AM"
        elif hour < 12:
            time_str = f"{hour}:{minute:02d} AM"
        elif hour == 12:
            time_str = f"12:{minute:02d} PM"
        else:
            time_str = f"{hour - 12}:{minute:02d} PM"

        return date_str, time_str

    def upload_video_to_youtube(
        self, video_content, page, publish_time=None, dry_run=False
    ):
        """上传视频到YouTube（参考auto_youtube_publish.py）"""
        if dry_run:
            print(f"[试运行] 将要上传视频:")
            print(f"  文件: {video_content['mp4_path']}")
            print(f"  标题: {video_content['title']}")
            print(f"  描述长度: {len(video_content['description'])} 字符")
            print(f"  封面: {video_content['thumbnail_path'] or '无'}")
            print(f"  计划发布时间: {publish_time}")
            return True

        if not video_content["valid"]:
            print("❌ 视频内容无效，跳过上传")
            return False

        try:
            # 导航到YouTube Studio
            print(f"🌐 正在导航到YouTube Studio: {self.studio_url}")
            page.goto(self.studio_url)

            # 等待页面加载
            print("⏳ 等待页面加载...")
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.wait_for_timeout(5000)

            # 点击上传图标
            print("📤 正在寻找并点击上传图标...")
            upload_selectors = [
                '[test-id="upload-icon-url"]',
                'button[aria-label*="Create"]',
                'button[aria-label*="Upload"]',
                "#upload-icon",
                'ytcp-icon-button[icon="upload"]',
            ]

            upload_clicked = False
            for selector in upload_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        page.wait_for_selector(selector, state="visible", timeout=5000)
                        page.locator(selector).first.click()
                        print(f"✅ 成功点击上传图标")
                        upload_clicked = True
                        break
                except Exception:
                    continue

            if not upload_clicked:
                print("❌ 无法找到上传图标")
                return False

            # 等待文件输入框并上传视频
            print("⏳ 等待文件上传输入框...")
            page.wait_for_selector(
                'input[type="file"][name="Filedata"]', state="attached"
            )

            print(f"📁 正在上传视频: {video_content['mp4_path']}")

            # 优先使用CDP方法上传大文件
            try:
                cdp_session = page.context.new_cdp_session(page)
                dom_snapshot = cdp_session.send("DOM.getDocument")
                node_result = cdp_session.send(
                    "DOM.querySelector",
                    {
                        "nodeId": dom_snapshot["root"]["nodeId"],
                        "selector": 'input[type="file"][name="Filedata"]',
                    },
                )

                if node_result.get("nodeId"):
                    cdp_session.send(
                        "DOM.setFileInputFiles",
                        {
                            "nodeId": node_result["nodeId"],
                            "files": [video_content["mp4_path"]],
                        },
                    )
                    cdp_session.detach()
                    print("✅ 视频文件上传完成（CDP方法）")
                else:
                    raise Exception("CDP方法失败")

            except Exception:
                # 回退到标准方法
                file_input = page.locator('input[type="file"][name="Filedata"]')
                file_input.set_input_files(video_content["mp4_path"])
                print("✅ 视频文件上传完成（标准方法）")

            # 等待上传处理 - 使用固定时间等待，避免无限等待
            print("⏳ 等待视频上传处理...")
            countdown_timer(6, "视频上传后等待页面稳定")

            # 输入标题前强制等待5秒
            print("⏳ 输入标题前强制等待 5 秒...")
            time.sleep(5)

            # 输入标题 (参考 auto_youtube_publish.py 的简化逻辑)
            print("✏️  正在输入标题...")
            title_selector = 'div[id="textbox"][aria-label="Add a title that describes your video (type @ to mention a channel)"]'
            try:
                page.wait_for_selector(title_selector, state="visible", timeout=15000)
                title_input = page.locator(title_selector)
                title_input.click()
                title_input.press("Control+a")
                title_input.fill(video_content["title"])
                print(f"✅ 已输入标题: {video_content['title']}")
            except Exception as e:
                print(f"❌ 输入标题失败: {e}")
                print("⚠️ 无法输入标题，将继续后续流程，但视频标题可能不正确。")

            time.sleep(2)

            # 输入描述
            print("✏️  正在输入描述...")
            desc_selector = 'div[id="textbox"][aria-label="Tell viewers about your video (type @ to mention a channel)"]'
            page.wait_for_selector(desc_selector, state="visible")
            desc_input = page.locator(desc_selector)
            desc_input.click()
            desc_input.press("Control+a")
            desc_input.fill(video_content["description"])
            print("✅ 已输入描述")

            time.sleep(2)

            # 上传封面
            if video_content.get("thumbnail_path") and os.path.exists(
                video_content["thumbnail_path"]
            ):
                print(f"📷 正在上传封面: {video_content['thumbnail_path']}")
                try:
                    page.wait_for_timeout(3000)
                    thumbnail_selectors = [
                        'ytcp-thumbnail-uploader input#file-loader[type="file"]',
                        'input#file-loader[type="file"]',
                        'input[type="file"][accept="image/jpeg,image/png"]',
                    ]

                    for selector in thumbnail_selectors:
                        try:
                            if page.query_selector(selector):
                                # 尝试CDP方法
                                try:
                                    cdp_session = page.context.new_cdp_session(page)
                                    cdp_session.send("DOM.enable")
                                    doc = cdp_session.send(
                                        "DOM.getDocument", {"depth": -1}
                                    )
                                    node_result = cdp_session.send(
                                        "DOM.querySelector",
                                        {
                                            "nodeId": doc["root"]["nodeId"],
                                            "selector": selector,
                                        },
                                    )
                                    if node_result.get("nodeId"):
                                        cdp_session.send(
                                            "DOM.setFileInputFiles",
                                            {
                                                "nodeId": node_result["nodeId"],
                                                "files": [
                                                    video_content["thumbnail_path"]
                                                ],
                                            },
                                        )
                                        cdp_session.detach()
                                        print("✅ 封面上传完成（CDP方法）")
                                        break
                                except Exception:
                                    # 回退到标准方法
                                    page.set_input_files(
                                        selector, video_content["thumbnail_path"]
                                    )
                                    print("✅ 封面上传完成（标准方法）")
                                    break
                        except Exception:
                            continue

                    page.wait_for_timeout(3000)
                except Exception as e:
                    print(f"⚠️  封面上传失败，继续处理: {e}")

            # 点击Next按钮3次
            print("⏭️  正在点击Next按钮...")
            next_button = page.locator('button:has-text("Next")')
            for i in range(3):
                next_button.click()
                print(f"✅ 已点击Next按钮 ({i+1}/3)")
                time.sleep(1.5)

            # 选择Public选项
            print("🌐 正在选择Public选项...")
            public_radio = page.locator('tp-yt-paper-radio-button[name="PUBLIC"]')
            public_radio.click()
            print("✅ 已选择Public选项")

            # 设置发布时间或立即发布
            if publish_time:
                print(f"⏰ 正在设置发布时间: {publish_time}")

                # 展开发布计划选项
                print("📅 正在展开发布计划选项...")
                second_container = page.locator("div#second-container")
                second_container.click()
                print("✅ 已展开发布计划选项")

                page.wait_for_timeout(2000)

                date_str, time_str = self.format_publish_time(publish_time)
                print(f"📅 格式化后 - 日期: {date_str}, 时间: {time_str}")

                # 点击日期选择器激活日期输入框
                print("📅 正在点击日期选择器...")
                try:
                    date_dropdown = page.locator(
                        'div[role="button"].container.style-scope.ytcp-dropdown-trigger'
                    )
                    date_dropdown.click()
                    page.wait_for_timeout(1000)
                    print("✅ 已点击日期选择器")
                except Exception as dropdown_error:
                    print(f"⚠️ 点击日期选择器时出错: {dropdown_error}")
                    print("🔄 继续尝试直接设置日期...")

                # 设置日期
                print(f"📅 正在设置日期: {date_str}")
                date_input = page.get_by_label("Enter date").get_by_label("")
                date_input.click()
                page.keyboard.press("Control+a")  # 全选
                date_input.fill(date_str)

                # 点击两次回车确认日期
                page.keyboard.press("Enter")
                page.wait_for_timeout(500)
                page.keyboard.press("Enter")
                page.wait_for_timeout(1000)
                print("✅ 日期设置完成")

                # 设置时间
                print(f"⏰ 正在设置时间: {time_str}")
                time_input = page.locator("#input-1").get_by_label("")
                time_input.click()
                page.keyboard.press("Control+a")  # 全选
                time_input.fill(time_str)

                # 时间设置完成后连续按两次回车
                page.keyboard.press("Enter")
                page.wait_for_timeout(500)
                page.keyboard.press("Enter")
                page.wait_for_timeout(1000)
                print("✅ 时间设置完成")

                # 添加随机延迟，模拟人工操作
                delay = random.uniform(1.0, 1.5)
                delay_seconds = int(delay)
                if delay_seconds > 0:
                    countdown_timer(delay_seconds, f"人工延迟等待 {delay:.1f} 秒")
                else:
                    print(f"⏰ 等待 {delay:.2f} 秒后点击Schedule按钮...")
                    page.wait_for_timeout(int(delay * 1000))

                # 点击Schedule按钮 - 使用多种选择器尝试
                print("📅 正在点击Schedule按钮...")
                try:
                    # 首先等待按钮元素出现
                    print("⏳ 等待Schedule按钮出现...")
                    page.wait_for_selector(
                        "#done-button", state="visible", timeout=10000
                    )

                    # 尝试多种选择器
                    selectors = [
                        "#done-button",  # 简单ID选择器
                        "ytcp-button#done-button",  # 带标签的ID选择器
                        'button[aria-label="Schedule"]',  # 内部button元素
                        '[aria-label="Schedule"]',  # aria-label选择器
                        'ytcp-button#done-button[role="button"]',  # 完整选择器
                    ]

                    clicked = False
                    for selector in selectors:
                        try:
                            print(f"🔍 尝试选择器: {selector}")
                            schedule_button = page.locator(selector)

                            # 检查元素是否存在
                            if schedule_button.count() > 0:
                                print(f"✅ 找到元素，准备点击...")

                                # 等待元素可点击
                                schedule_button.wait_for(state="visible", timeout=5000)

                                # 尝试点击
                                schedule_button.click()
                                print(
                                    f"✅ 使用选择器 '{selector}' 成功点击Schedule按钮"
                                )
                                clicked = True
                                break
                            else:
                                print(f"❌ 选择器 '{selector}' 未找到元素")
                        except Exception as e:
                            print(f"❌ 选择器 '{selector}' 点击失败: {e}")
                            continue

                    if not clicked:
                        print("⚠️ 所有选择器都失败，尝试使用文本内容点击...")
                        # 最后尝试：使用文本内容点击
                        text_button = page.locator("text=Schedule")
                        if text_button.count() > 0:
                            text_button.click()
                            print("✅ 使用文本内容成功点击Schedule按钮")
                            clicked = True
                        else:
                            print("❌ 无法找到Schedule按钮")
                            return False

                except Exception as e:
                    print(f"❌ 点击Schedule按钮时出错: {e}")
                    return False

                # 如果成功点击了Schedule按钮，认为发布成功
                if clicked:
                    # 等待发布完成
                    countdown_timer(5, "等待发布操作完成")
                    print("✅ Schedule按钮点击成功，视频已安排发布")
                    return True
                else:
                    print("❌ 未能成功点击Schedule按钮")
                    return False
            else:
                # 立即发布
                print("📤 正在立即发布...")
                publish_button = page.locator('button:has-text("Publish")')
                publish_button.click()
                print("✅ 已点击Publish按钮")

                countdown_timer(5, "等待立即发布完成")

                # 改进的立即发布验证逻辑 - 更宽松的判断标准
                try:
                    countdown_timer(3, "验证发布状态")
                    current_url = page.url
                    print(f"📍 当前页面URL: {current_url}")

                    # 方法1: 检查URL是否已经跳转离开上传页面（关键指标）
                    if "upload" not in current_url.lower():
                        print("✅ 已跳转离开上传页面，立即发布成功的强烈指示")
                        print("✅ 立即发布完成且验证成功")
                        return True

                    # 方法2: 如果仍在上传页面，检查页面内容指示
                    print("🔍 仍在upload页面，检查页面内容...")

                    # 检查是否有明确的错误信息
                    error_indicators = [
                        "Error uploading",
                        "Upload failed",
                        "Something went wrong",
                        "Try again",
                        "Retry",
                        "Upload error",
                        "Failed to publish",
                        "Publishing failed",
                    ]

                    page_text = ""
                    try:
                        page_text = page.locator("body").inner_text().lower()
                    except Exception as text_error:
                        print(f"⚠️ 获取页面文本失败: {text_error}")
                        # 如果无法获取页面文本，先假设成功
                        print("✅ 无法验证但未发现错误，暂时标记为成功")
                        return True

                    # 检查是否有错误
                    found_errors = [
                        error
                        for error in error_indicators
                        if error.lower() in page_text
                    ]
                    if found_errors:
                        print(f"❌ 发现错误指示: {found_errors}")
                        print("❌ 立即发布失败")
                        return False

                    # 方法3: 检查是否有成功指示（不作为必需条件）
                    success_indicators = [
                        "published",
                        "video published",
                        "upload complete",
                        "processing",
                        "public",
                        "live now",
                    ]

                    found_success = [
                        indicator
                        for indicator in success_indicators
                        if indicator in page_text
                    ]
                    if found_success:
                        print(f"✅ 发现成功指示: {found_success}")
                        print("✅ 立即发布完成且验证成功")
                        return True

                    # 方法4: 最后的宽松判断 - 如果没有错误信息，就认为成功
                    print("⚠️ 未发现明确的成功或错误指示")
                    print("📝 由于没有发现错误信息，按照宽松标准判断为成功")
                    print("✅ 立即发布完成（宽松验证通过）")
                    return True

                except Exception as verify_error:
                    print(f"❌ 立即发布验证时出错: {verify_error}")
                    print("📝 验证过程出错，但按照宽松标准判断为成功")
                    print("✅ 立即发布完成（异常后默认成功）")
                    return True

        except Exception as e:
            print(f"❌ 上传视频时出错: {e}")
            return False

    def update_excel_status(self, book_info, publish_time):
        """更新Excel中的发布状态"""
        excel_file = self.directories["excel"]
        uuid = book_info["uuid"]

        print(f"📝 开始更新Excel状态: {uuid}")

        try:
            # 读取当前数据
            df = pd.read_excel(excel_file)

            # 查找对应的行
            # 假设第一列是UUID
            mask = df.iloc[:, 0] == uuid

            if not mask.any():
                print(f"❌ 在Excel中未找到UUID记录: {uuid}")
                return False

            # 更新状态（使用中文列名）
            df.loc[mask, "是否发布"] = 1
            df.loc[mask, "发布时间"] = publish_time.strftime("%Y-%m-%d %H:%M:%S")

            # 保存更新后的数据
            df.to_excel(excel_file, index=False)
            print(f"✅ Excel状态更新成功")

            return True

        except Exception as e:
            print(f"❌ 更新Excel状态时出错: {e}")
            return False

    def run(self, max_count=None, dry_run=False):
        """运行书籍上传系统"""
        print(f"\n{'='*60}")
        print(f"🚀 书籍YouTube上传系统启动")
        print(f"{'='*60}")

        # 获取待上传书籍
        pending_books = self.get_pending_books()
        if not pending_books:
            print("❌ 没有待上传的书籍")
            return

        # 限制上传数量
        if max_count:
            books_to_upload = pending_books[:max_count]
            print(
                f"\n📊 将要处理 {len(books_to_upload)} 个书籍 (限制数量: {max_count})"
            )
        else:
            books_to_upload = pending_books
            print(f"\n📊 将要处理所有 {len(books_to_upload)} 个书籍")

        # 显示书籍列表
        for i, book in enumerate(books_to_upload, 1):
            print(f"   {i}. UUID: {book['uuid']}")

        # 初始化浏览器（仅在非试运行模式）
        playwright = None
        browser = None
        initial_page = None

        if not dry_run:
            print(f"\n🚀 正在初始化浏览器...")
            playwright, browser, initial_page = self.initialize_browser()
            if not initial_page:
                print("❌ 浏览器初始化失败，终止运行")
                return
            print("✅ 浏览器初始化完成")

        try:
            # 处理每个书籍
            for i, book_info in enumerate(books_to_upload, 1):
                print(f"\n{'-'*50}")
                print(f"📖 处理书籍 {i}/{len(books_to_upload)}: {book_info['uuid']}")
                print(f"{'-'*50}")

                # 获取书籍内容
                video_content = self.get_book_content(book_info)
                if not video_content:
                    print(f"❌ 无法获取书籍内容，跳过")
                    continue

                # 在非试运行模式下管理tab
                upload_page = None
                if not dry_run:
                    # 清理已关闭的tab
                    self.cleanup_closed_tabs()

                    # 检查是否需要等待（达到tab限制）
                    wait_result = self.check_and_wait_for_tab_limit()

                    # 为当前书籍创建新tab或使用第一个tab
                    if wait_result:
                        # 如果等待限制并返回了新tab，使用这个新tab
                        upload_page = wait_result
                        print("📑 使用等待后创建的新tab进行上传")
                    elif i == 1:
                        # 第一个书籍使用初始tab
                        upload_page = initial_page
                        print("📑 使用初始tab进行上传")
                    else:
                        # 后续书籍创建新tab
                        upload_page = self.create_new_tab_for_upload()
                        if not upload_page:
                            print("❌ 无法创建新tab，跳过当前书籍")
                            continue

                # 🔄 每次重新计算发布时间（基于最新的Excel数据）
                print(f"📅 正在为第 {i} 个书籍重新计算发布时间...")
                publish_time = self.calculate_next_publish_time()
                print(f"📅 计划发布时间: {publish_time}")

                # 上传视频
                print(f"🚀 开始上传第 {i} 个书籍...")
                try:
                    success = self.upload_video_to_youtube(
                        video_content, upload_page, publish_time, dry_run
                    )
                except Exception as upload_error:
                    print(f"❌ 上传视频时发生异常: {upload_error}")
                    success = False

                # 处理上传结果
                if success:
                    print(f"🎉 书籍 {book_info['uuid']} 上传成功！")

                    if not dry_run:
                        # 更新Excel状态
                        update_success = self.update_excel_status(
                            book_info, publish_time
                        )
                        if update_success:
                            print(f"✅✅ 完整成功: 视频发布成功且Excel已更新")
                        else:
                            print(f"❌⚠️ 部分成功: 视频发布成功，但Excel更新失败")
                    else:
                        print(f"✅ [试运行] 书籍处理完成")
                else:
                    print(f"❌ 书籍 {book_info['uuid']} 发布失败")

                # 显示当前tab状态
                if not dry_run:
                    print(f"📑 当前tab状态: {len(self.current_tabs)}/{self.max_tabs}")

                # 视频间隔等待
                if i < len(books_to_upload):
                    wait_time = 20
                    countdown_timer(wait_time, f"书籍间隔等待 {wait_time} 秒")

                    # 备用等待方式（如果页面存在的话）
                    if not dry_run and upload_page:
                        try:
                            # 页面可能已经关闭，所以用简单的延时
                            time.sleep(1)
                        except:
                            pass

        except KeyboardInterrupt:
            print("\n🛑 用户中断操作")
            raise
        except Exception as e:
            print(f"❌ 运行过程中发生错误: {e}")
        finally:
            # 清理资源
            if not dry_run and playwright:
                try:
                    print("\n🧹 正在清理浏览器资源...")
                    print("💡 浏览器将保持打开状态，方便检查上传结果")
                    print(f"📑 最终tab数量: {len(self.current_tabs)}")
                except Exception as cleanup_error:
                    print(f"⚠️ 清理资源时出错: {cleanup_error}")

        print(f"\n{'='*60}")
        print(f"🎉 书籍上传任务完成")
        print(f"📊 总计处理了 {len(books_to_upload)} 个书籍")
        print(f"{'='*60}")


def check_dependencies():
    """检查必要的依赖是否安装"""
    missing_deps = []

    try:
        import pandas as pd
    except ImportError:
        missing_deps.append("pandas")

    try:
        import urllib3
    except ImportError:
        missing_deps.append("urllib3")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        missing_deps.append("playwright")

    if missing_deps:
        print(f"❌ 缺少依赖包: {', '.join(missing_deps)}")
        print("请安装缺少的依赖:")
        for dep in missing_deps:
            print(f"  pip install {dep}")
        if "playwright" in missing_deps:
            print("  playwright install chromium")
        return False

    return True


def show_usage_examples():
    """显示使用示例"""
    print("\n💡 使用示例:")
    print("# 中文书籍试运行模式，查看待上传的书籍")
    print("python upload_books_to_youtube.py --language zh --dry-run")
    print()
    print("# 英文书籍试运行模式")
    print("python upload_books_to_youtube.py --language en --dry-run")
    print()
    print("# 上传所有中文书籍，使用默认配置")
    print("python upload_books_to_youtube.py --language zh")
    print()
    print("# 上传所有英文书籍，使用默认配置")
    print("python upload_books_to_youtube.py --language en")
    print()
    print("# 中文书籍设定6小时间隔上传")
    print("python upload_books_to_youtube.py --language zh --interval 6")
    print()
    print("# 英文书籍限制只上传前3个")
    print("python upload_books_to_youtube.py --language en --max-count 3")
    print()
    print("# 中文书籍设置tab管理：最多5个tab，等待45分钟")
    print(
        "python upload_books_to_youtube.py --language zh --max-tabs 5 --wait-minutes 45"
    )
    print()
    print("# 组合使用：中文书籍，8小时间隔，最多2个书籍，3个tab，等待60分钟")
    print(
        "python upload_books_to_youtube.py --language zh --interval 8 --max-count 2 --max-tabs 3 --wait-minutes 60"
    )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="书籍YouTube上传脚本 - 上传merge_clips_with_audio.py产生的MP4文件",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
功能说明:
  1. 读取对应语言的Excel文件中的书籍列表
  2. 跳过已上传的书籍（是否发布=1）
  3. 获取书籍MP4文件、封面、标题、描述和hashtags
  4. 按设定的时间间隔自动上传到指定YouTube频道
  5. 更新Excel文件中的发布状态

Excel文件格式要求:
  - 列名: UUID | 是否发布 | 发布时间
  - '是否发布' 列: 0=未发布, 1=已发布
  - '发布时间' 列: 日期时间字符串 (YYYY-MM-DD HH:MM:SS)

使用示例:
  python upload_books_to_youtube.py --language zh --dry-run    # 中文书籍试运行
  python upload_books_to_youtube.py --language en             # 英文书籍上传
  python upload_books_to_youtube.py --language zh --interval 6 # 中文书籍6小时间隔

配置信息:
  英文频道: https://studio.youtube.com/channel/UCe4grZMmPMmnMcIoaTJc05w
  中文频道: https://studio.youtube.com/channel/UCW0Or8f_oWL2V8QQzob-DQw
  英文浏览器ID: k10i5y1s
  中文浏览器ID: k10i7fjt
        """,
    )

    parser.add_argument(
        "--language",
        choices=["en", "zh"],
        default="en",
        help="书籍语言 (en=英文, zh=中文) (默认: en)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_HOURS,
        help=f"视频上传间隔小时数 (默认: {DEFAULT_INTERVAL_HOURS})",
    )
    parser.add_argument("--max-count", type=int, help="最大上传数量 (默认: 全部)")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式，不实际上传")
    parser.add_argument(
        "--max-tabs",
        type=int,
        default=6,
        help="最大tab数量，达到此数量时将等待 (默认: 6)",
    )
    parser.add_argument(
        "--wait-minutes",
        type=int,
        default=30,
        help="当tab达到限制时的等待时间（分钟） (默认: 30)",
    )
    parser.add_argument(
        "--help-examples", action="store_true", help="显示详细的使用示例"
    )

    args = parser.parse_args()

    # 如果请求显示示例，则显示并退出
    if args.help_examples:
        show_usage_examples()
        return

    print("📚 书籍YouTube上传系统")
    print("=" * 60)
    print(f"🖥️  操作系统: {platform.system()}")
    print(f"🏗️  架构类型: {platform.machine()}")
    print(f"📅 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 检查依赖
    if not check_dependencies():
        return

    # 检查系统
    if not check_supported_system():
        print("⚠️  此脚本主要为macOS和Ubuntu系统设计，其他系统可能需要调整路径")

    # 显示配置信息
    print(f"\n🔧 配置信息:")
    print(
        f"   语言设置: {args.language} ({'中文' if args.language == 'zh' else 'English'})"
    )
    print(f"   YouTube频道: {YOUTUBE_CHANNELS[args.language]}")
    print(f"   浏览器ID: {ADSPOWER_BROWSER_IDS[args.language]}")
    print(f"   Excel文件: {EXCEL_FILES[args.language]}")
    print(f"   视频间隔: {args.interval} 小时")
    print(f"   最大数量: {args.max_count or '全部'}")
    print(f"   最大tab数量: {args.max_tabs}")
    print(f"   tab等待时间: {args.wait_minutes} 分钟")
    print(f"   运行模式: {'试运行' if args.dry_run else '实际上传'}")
    print(f"   媒体根目录: {get_base_media_path()}")

    # 创建上传器实例
    uploader = BookYouTubeUploader(
        language=args.language,
        interval_hours=args.interval,
        max_tabs=args.max_tabs,
        wait_minutes=args.wait_minutes,
    )

    # 运行上传系统
    try:
        uploader.run(max_count=args.max_count, dry_run=args.dry_run)
        print("\n🎉 程序正常结束")

    except KeyboardInterrupt:
        print("\n\n🛑 用户中断操作")
        print("📝 提示：浏览器连接已断开，AdsPower浏览器实例仍保持打开状态")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ 系统错误: {e}")
        print("\n🔧 故障排除建议:")
        print("   1. 检查AdsPower是否正常运行")
        print("   2. 确认浏览器ID是否正确 (英文: k10i5y1s, 中文: k10i7fjt)")
        print("   3. 检查网络连接")
        print("   4. 确认Excel文件格式正确，列名为：UUID、是否发布、发布时间")
        print("   5. 检查视频文件路径是否正确")
        print("   6. 确认生成的标题、描述、hashtags文件存在")
        print("   7. 检查语言参数是否正确 (--language en 或 --language zh)")
        print(
            "   8. 运行试运行模式检查：python upload_books_to_youtube.py --language zh --dry-run"
        )
        print("   9. 查看详细示例：python upload_books_to_youtube.py --help-examples")
        sys.exit(1)


if __name__ == "__main__":
    main()
