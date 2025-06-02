#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自动发布系统

功能说明:
1. 从mp4_publish_tracker.xlsx获取待发布视频列表（包含频道信息）
2. 过滤条件：是否发布=1 且 是否已经发布=0 且 频道名称列不为空
3. 优先使用Excel中的频道信息定位视频文件和相关资源
4. 从title_shorten_multi_lang和multi_lang_desc目录获取标题和描述
5. 计算发布时间：基于已发布视频的最远时间+6小时
6. 自动发布视频到YouTube（支持大文件上传）
7. 更新Excel表格，标记为已发布并记录发布时间

大文件上传支持:
- 小文件（≤50MB）: 直接使用Playwright标准方法
- 大文件（>50MB）: 自动使用CDP session绕过限制
- 备选方案: pyautogui系统级自动化
- 最后备选: 手动上传（30秒超时）

Excel必需列:
- MP4名称: 视频文件名
- 频道名称: 频道文件夹名称（新增列）
- 是否发布: 1表示需要发布
- 是否已经发布: 0表示未发布，1表示已发布
- 发布时间: 发布后自动填入

依赖:
- pandas, openpyxl (Excel操作)
- playwright (浏览器自动化)
- urllib3 (AdsPower API)
- pyautogui, pyperclip (系统级自动化，可选)

使用方法:
python auto_publish_system.py [选项]

选项:
-l, --language      指定语言 (en/ko, 默认en)
-n, --max-count     最大发布数量 (默认1)
-d, --dry-run       试运行模式，不实际发布
--ads-id           AdsPower浏览器ID (默认kq316tr)
--studio-url       YouTube Studio URL
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

# 尝试导入pyautogui用于系统级自动化
try:
    import pyautogui
    import pyperclip

    HAS_PYAUTOGUI = True
    print("已导入pyautogui，支持大文件自动上传")
except ImportError:
    HAS_PYAUTOGUI = False
    print("未安装pyautogui，大文件需要手动上传")


def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # Mac OS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 全局配置
BASE_PATH = get_base_path()
MP4_DIR = f"{BASE_PATH}/mp4_with_audio"
TITLE_DIR = f"{BASE_PATH}/title_shorten_multi_lang"
DESC_DIR = f"{BASE_PATH}/multi_lang_desc"
TRACKER_FILE = "mp4_publish_tracker.xlsx"

# 语言映射
LANGUAGE_NAMES = {"en": "English", "ko": "Korean"}


class AutoPublishSystem:
    def __init__(self, language="en", ads_id="kq316tr", studio_url=None):
        self.language = language
        self.ads_id = ads_id
        self.studio_url = (
            studio_url or "https://studio.youtube.com/channel/UCiCMH2ZdFy3vNqa6X0NVsoA"
        )
        self.http = None
        self.close_url = f"http://127.0.0.1:50325/api/v1/browser/stop?user_id={ads_id}"

    def get_pending_videos(self):
        """从Excel获取待发布视频列表"""
        print("正在加载发布跟踪表...")

        if not os.path.exists(TRACKER_FILE):
            print(f"错误: 跟踪文件不存在: {TRACKER_FILE}")
            return []

        try:
            # 读取对应语言的工作表
            df = pd.read_excel(TRACKER_FILE, sheet_name=self.language)
            print(f"工作表 '{self.language}' 共有 {len(df)} 条记录")

            # 检查是否包含"频道名称"列
            if "频道名称" not in df.columns:
                print("警告: Excel中缺少'频道名称'列，请确保已添加该列")
                return []

            # 过滤条件：是否发布=1 且 是否已经发布=0 且 频道名称列不为空
            pending = df[
                (df["是否发布"] == 1)
                & (df["是否已经发布"] == 0)
                & (df["频道名称"].notna() & (df["频道名称"] != ""))
            ]
            print(f"找到 {len(pending)} 个待发布视频")

            # 检查待发布视频是否都有频道信息
            missing_channel = pending[
                pending["频道名称"].isna() | (pending["频道名称"] == "")
            ]
            if len(missing_channel) > 0:
                print(f"警告: {len(missing_channel)} 个视频缺少频道信息:")
                for _, row in missing_channel.iterrows():
                    print(f"  - {row['MP4名称']}")

            # 只返回有频道信息的视频
            valid_pending = pending[
                pending["频道名称"].notna() & (pending["频道名称"] != "")
            ]
            print(f"有效的待发布视频: {len(valid_pending)} 个")

            return valid_pending.to_dict("records")

        except Exception as e:
            print(f"读取跟踪文件时出错: {e}")
            return []

    def get_latest_publish_time(self):
        """获取已发布视频的最远发布时间

        逻辑说明：
        - 如果全部视频都未发布，返回当前时间作为基准
        - 如果已有视频发布，返回已发布视频中的最远发布时间
        - 包含未来时间的记录（因为我们就是要设置未来的发布时间）
        """
        try:
            print("🔄 重新读取Excel获取最新发布时间...")
            df = pd.read_excel(TRACKER_FILE, sheet_name=self.language)

            # 过滤已发布的视频（是否已经发布=1）
            published = df[df["是否已经发布"] == 1]
            print(f"📊 已发布视频数量: {len(published)}")

            # 如果全部都未发布，使用当前时间作为基准
            if len(published) == 0:
                print("全部视频都未发布，使用当前时间作为基准")
                return datetime.now()

            # 获取发布时间列，排除空值
            publish_times = published["发布时间"].dropna()
            print(f"📅 有效发布时间记录数量: {len(publish_times)}")

            # 如果已发布视频中没有有效的发布时间记录，使用当前时间作为基准
            if len(publish_times) == 0:
                print("已发布视频中没有有效的发布时间记录，使用当前时间作为基准")
                return datetime.now()

            # 转换为datetime
            publish_times_dt = pd.to_datetime(publish_times)

            # 直接找到最远的时间（包含未来时间）
            max_time = publish_times_dt.max()
            print(f"✅ 已发布视频的最远发布时间: {max_time}")

            return max_time

        except Exception as e:
            print(f"获取发布时间时出错: {e}")
            print("出错时使用当前时间作为基准")
            return datetime.now()

    def calculate_next_publish_time(self):
        """计算下一个发布时间（最远时间+6小时）"""
        print("⏰ 开始计算下一个发布时间...")
        latest_time = self.get_latest_publish_time()
        next_time = latest_time + timedelta(hours=6)
        print(f"🎯 基准时间: {latest_time}")
        print(f"➕ 添加6小时后: {next_time}")
        print(f"✅ 下一个发布时间: {next_time}")
        return next_time

    def get_video_content(self, video_name, channel_name):
        """获取视频的标题、描述和文件路径"""
        # 去除.mp4后缀
        base_name = video_name.replace(".mp4", "")

        # 构建文件路径
        mp4_path = os.path.join(MP4_DIR, channel_name, self.language, video_name)
        title_path = os.path.join(
            TITLE_DIR, channel_name, self.language, f"{base_name}.txt"
        )
        desc_path = os.path.join(
            DESC_DIR, channel_name, self.language, f"{base_name}.txt"
        )
        # 添加封面路径
        thumbnail_path = os.path.join(
            BASE_PATH, "thumbnail", channel_name, self.language, f"{base_name}.png"
        )

        content = {
            "mp4_path": mp4_path,
            "title": "",
            "description": "",
            "thumbnail_path": thumbnail_path,
            "valid": True,
        }

        # 检查MP4文件
        if not os.path.exists(mp4_path):
            print(f"警告: MP4文件不存在: {mp4_path}")
            content["valid"] = False

        # 读取标题
        if os.path.exists(title_path):
            try:
                with open(title_path, "r", encoding="utf-8") as f:
                    content["title"] = f.read().strip()
            except Exception as e:
                print(f"读取标题文件出错: {e}")
                content["title"] = base_name  # 使用文件名作为备选
        else:
            print(f"警告: 标题文件不存在: {title_path}")
            content["title"] = base_name  # 使用文件名作为备选

        # 读取描述
        if os.path.exists(desc_path):
            try:
                with open(desc_path, "r", encoding="utf-8") as f:
                    content["description"] = f.read().strip()
            except Exception as e:
                print(f"读取描述文件出错: {e}")
                content["description"] = "精彩内容，敬请观看！"  # 默认描述
        else:
            print(f"警告: 描述文件不存在: {desc_path}")
            content["description"] = "精彩内容，敬请观看！"  # 默认描述

        # 检查封面文件
        if not os.path.exists(thumbnail_path):
            print(f"警告: 封面文件不存在: {thumbnail_path}")
            content["thumbnail_path"] = None
        else:
            print(f"找到封面文件: {thumbnail_path}")

        return content

    def get_adspower_info(self):
        """连接AdsPower浏览器"""
        open_url = f"http://127.0.0.1:50325/api/v1/browser/start?user_id={self.ads_id}"

        self.http = urllib3.PoolManager()

        print("正在连接AdsPower...")
        r = self.http.request("GET", open_url)

        if r.status != 200:
            print(f"错误: API返回状态码 {r.status}")
            print("请确保AdsPower已启动并且本地API已启用")
            return None, None

        resp = json.loads(r.data.decode("utf-8"))

        if resp["code"] != 0:
            print(f"错误: {resp['msg']}")
            print("请检查ads_id是否正确")
            return None, None

        ws_endpoint = resp["data"]["ws"]["puppeteer"]
        debug_port = resp["data"]["debug_port"]
        remote_debugging_url = f"http://localhost:{debug_port}"

        print(f"成功连接AdsPower，WebSocket地址: {ws_endpoint}")
        print(f"远程调试URL: {remote_debugging_url}")

        return ws_endpoint, remote_debugging_url

    def format_publish_time(self, publish_time):
        """格式化发布时间为YouTube需要的格式

        Returns:
            tuple: (date_str, time_str)
            date_str: 如 "Dec 2, 2025"
            time_str: 如 "12:00 AM" 或 "10:15 PM"
        """
        # 月份映射
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

    def upload_video(
        self, video_content, dry_run=False, publish_time=None, is_first_video=False
    ):
        """上传视频到YouTube"""
        if dry_run:
            print(f"[试运行] 将要上传视频:")
            print(f"  文件: {video_content['mp4_path']}")
            print(f"  标题: {video_content['title']}")
            print(f"  描述: {video_content['description'][:100]}...")
            if video_content.get("thumbnail_path"):
                print(f"  封面: {video_content['thumbnail_path']}")
            else:
                print(f"  封面: 无")
            return True

        if not video_content["valid"]:
            print("视频内容无效，跳过上传")
            return False

        # 连接AdsPower
        ws_endpoint, remote_debugging_url = self.get_adspower_info()
        if not ws_endpoint:
            return False

        try:
            with sync_playwright() as p:
                # 连接浏览器
                browser = p.chromium.connect_over_cdp(remote_debugging_url)
                print("成功连接到浏览器！")

                # 获取上下文和页面
                if not browser.contexts:
                    context = browser.new_context()
                else:
                    context = browser.contexts[0]

                # 只在第一个视频时关闭其他tab
                if is_first_video:
                    print("初次运行，正在关闭其他tab...")
                    all_pages = context.pages
                    for page in all_pages:
                        try:
                            page.close()
                            print(f"已关闭tab: {page.url}")
                        except Exception as e:
                            print(f"关闭tab时出错: {e}")

                # 为每个视频打开新的tab
                print("正在打开新的tab...")
                page = context.new_page()
                print("已创建新的tab")

                # 导航到YouTube Studio
                print("正在导航到YouTube Studio...")
                page.goto(self.studio_url)
                page.wait_for_load_state("networkidle")

                # 点击上传图标
                print("正在点击上传图标...")
                upload_icon = page.locator('[test-id="upload-icon-url"]')
                upload_icon.click()

                # 等待文件输入框出现
                print("等待文件上传输入框...")
                page.wait_for_selector(
                    'input[type="file"][name="Filedata"]', state="attached"
                )

                # 先尝试直接上传（适用于小文件）
                try:
                    print(f"正在上传视频: {video_content['mp4_path']}")
                    file_input = page.locator('input[type="file"][name="Filedata"]')
                    file_input.set_input_files(video_content["mp4_path"])
                    print("视频文件已上传")

                except Exception as upload_error:
                    print(f"直接上传失败: {upload_error}")

                    # 如果是大文件错误，尝试使用CDP方法
                    if "Cannot transfer files larger than 50Mb" in str(upload_error):
                        print("检测到大文件，尝试使用CDP方法上传...")

                        # 使用CDP session直接操作DOM
                        if self.upload_file_with_cdp(page, video_content["mp4_path"]):
                            print("✅ CDP方法上传成功")
                        else:
                            print("CDP方法也失败，尝试系统级自动化...")

                            # 备选方案：点击文件输入框触发系统文件对话框
                            file_input = page.locator(
                                'input[type="file"][name="Filedata"]'
                            )
                            file_input.click()

                            # 使用pyautogui自动化文件选择
                            if self.upload_file_with_pyautogui(
                                video_content["mp4_path"]
                            ):
                                print("系统级自动化上传成功")
                            else:
                                print("所有自动化方法都失败，需要手动操作...")
                                print(f"请手动选择文件: {video_content['mp4_path']}")
                                # 给用户30秒时间手动选择
                                page.wait_for_timeout(30000)
                    else:
                        # 其他错误，直接抛出
                        raise upload_error

                # 等待上传处理
                page.wait_for_load_state("networkidle")

                # 添加随机延迟，模拟人工操作
                delay = random.uniform(1.0, 1.5)
                print(f"等待 {delay:.2f} 秒后开始输入标题...")
                page.wait_for_timeout(int(delay * 1000))

                # 输入标题
                title_selector = 'div[id="textbox"][aria-label="Add a title that describes your video (type @ to mention a channel)"]'
                print("等待标题输入框...")
                page.wait_for_selector(title_selector, state="visible")

                title_input = page.locator(title_selector)
                title_input.click()
                title_input.press("Control+a")
                title_input.fill(video_content["title"])
                print(f"已输入标题: {video_content['title']}")

                # 添加随机延迟，模拟人工操作
                delay = random.uniform(1.0, 1.5)
                print(f"等待 {delay:.2f} 秒后开始输入描述...")
                page.wait_for_timeout(int(delay * 1000))

                # 输入描述
                desc_selector = 'div[id="textbox"][aria-label="Tell viewers about your video (type @ to mention a channel)"]'
                print("等待描述输入框...")
                page.wait_for_selector(desc_selector, state="visible")

                desc_input = page.locator(desc_selector)
                desc_input.click()
                desc_input.press("Control+a")
                desc_input.fill(video_content["description"])
                print("已输入描述")

                # 添加随机延迟，模拟人工操作
                delay = random.uniform(1.0, 1.5)
                print(f"等待 {delay:.2f} 秒后开始上传封面...")
                page.wait_for_timeout(int(delay * 1000))

                # 上传封面
                if video_content.get("thumbnail_path") and os.path.exists(
                    video_content["thumbnail_path"]
                ):
                    print(f"正在上传封面: {video_content['thumbnail_path']}")
                    try:
                        # 等待封面上传输入框出现
                        page.wait_for_selector(
                            'input#file-loader[type="file"]', state="attached"
                        )
                        thumbnail_input = page.locator('input#file-loader[type="file"]')
                        thumbnail_input.set_input_files(video_content["thumbnail_path"])
                        print("封面已上传")

                        # 等待封面上传完成
                        page.wait_for_timeout(3000)  # 等待3秒确保上传完成
                    except Exception as thumbnail_error:
                        print(f"上传封面时出错: {thumbnail_error}")
                        print("继续处理，不影响视频发布")
                else:
                    print("跳过封面上传（封面文件不存在）")

                # 添加随机延迟，模拟人工操作
                delay = random.uniform(1.0, 1.5)
                print(f"等待 {delay:.2f} 秒后继续下一步...")
                page.wait_for_timeout(int(delay * 1000))

                # 点击Next按钮3次
                print("正在点击Next按钮...")
                next_button = page.locator('button:has-text("Next")')
                for i in range(3):
                    next_button.click()
                    print(f"已点击Next按钮 ({i+1}/3)")
                    # 在每次点击Next按钮之间也添加随机延迟
                    delay = random.uniform(1.0, 1.5)
                    page.wait_for_timeout(int(delay * 1000))

                # 选择Public选项
                print("正在选择Public选项...")
                public_radio = page.locator('tp-yt-paper-radio-button[name="PUBLIC"]')
                public_radio.click()
                print("已选择Public选项")

                # 展开发布计划选项
                print("正在展开发布计划选项...")
                second_container = page.locator("div#second-container")
                second_container.click()
                print("已展开发布计划选项")

                # 设置发布时间
                if publish_time:
                    print(f"正在设置发布时间: {publish_time}")
                    date_str, time_str = self.format_publish_time(publish_time)
                    print(f"格式化后 - 日期: {date_str}, 时间: {time_str}")

                    # 点击日期选择器
                    print("正在点击日期选择器...")
                    date_dropdown = page.locator(
                        'div[role="button"].container.style-scope.ytcp-dropdown-trigger'
                    )
                    date_dropdown.click()
                    page.wait_for_timeout(1000)

                    # 使用第二个输入框（日期输入框）设置日期
                    print(f"正在设置日期: {date_str}")
                    date_input = page.get_by_label("Enter date").get_by_label("")
                    date_input.click()
                    page.keyboard.press("Control+a")  # 全选
                    date_input.fill(date_str)

                    # 点击两次回车确认日期
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(500)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(1000)
                    print("日期设置完成")

                    # 使用第一个输入框（时间输入框）设置时间
                    print(f"正在设置时间: {time_str}")
                    time_input = page.locator("#input-1").get_by_label("")
                    time_input.click()
                    page.keyboard.press("Control+a")  # 全选
                    time_input.fill(time_str)

                    # 时间设置完成后连续按两次回车
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(500)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(1000)
                    print("时间设置完成")

                    # 添加随机延迟，模拟人工操作
                    delay = random.uniform(1.0, 1.5)
                    print(f"等待 {delay:.2f} 秒后点击Schedule按钮...")
                    page.wait_for_timeout(int(delay * 1000))

                    # 点击Schedule按钮 - 使用多种选择器尝试
                    print("正在点击Schedule按钮...")
                    try:
                        # 首先等待按钮元素出现
                        print("等待Schedule按钮出现...")
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
                                print(f"尝试选择器: {selector}")
                                schedule_button = page.locator(selector)

                                # 检查元素是否存在
                                if schedule_button.count() > 0:
                                    print(f"找到元素，准备点击...")

                                    # 等待元素可点击
                                    schedule_button.wait_for(
                                        state="visible", timeout=5000
                                    )

                                    # 尝试点击
                                    schedule_button.click()
                                    print(
                                        f"✅ 使用选择器 '{selector}' 成功点击Schedule按钮"
                                    )
                                    clicked = True
                                    break
                                else:
                                    print(f"选择器 '{selector}' 未找到元素")
                            except Exception as e:
                                print(f"选择器 '{selector}' 点击失败: {e}")
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
                        print(f"点击Schedule按钮时出错: {e}")
                        return False

                    # 等待发布完成
                    print("等待发布操作完成...")
                    page.wait_for_timeout(5000)  # 等待5秒确保发布完成

                    print("视频发布配置完成")

                    # 不关闭浏览器和tab，保持打开状态
                    print("保持浏览器和tab打开状态")
                    return True

        except Exception as e:
            print(f"上传视频时出错: {e}")
            return False

    def update_publish_status(self, video_name, publish_time):
        """更新Excel中的发布状态"""
        try:
            # 读取当前数据
            df = pd.read_excel(TRACKER_FILE, sheet_name=self.language)

            # 找到对应的记录并更新
            mask = df["MP4名称"] == video_name
            if mask.any():
                df.loc[mask, "是否已经发布"] = 1
                df.loc[mask, "发布时间"] = publish_time.strftime("%Y-%m-%d %H:%M:%S")

                # 保存更新后的数据
                with pd.ExcelWriter(
                    TRACKER_FILE, engine="openpyxl", mode="a", if_sheet_exists="replace"
                ) as writer:
                    df.to_excel(writer, sheet_name=self.language, index=False)

                print(f"已更新 {video_name} 的发布状态")
                return True
            else:
                print(f"警告: 在Excel中未找到视频记录: {video_name}")
                return False

        except Exception as e:
            print(f"更新发布状态时出错: {e}")
            return False

    def find_channel_name(self, video_name, excel_channel_name=None):
        """根据视频名称查找对应的频道名

        Args:
            video_name: 视频文件名
            excel_channel_name: 从Excel中获取的频道名（优先使用）

        Returns:
            频道名称
        """
        # 如果Excel中有频道信息，直接使用
        if excel_channel_name:
            print(f"使用Excel中的频道信息: {excel_channel_name}")

            # 验证频道目录是否存在
            channel_path = os.path.join(MP4_DIR, excel_channel_name, self.language)
            if not os.path.exists(channel_path):
                print(f"警告: 频道目录不存在: {channel_path}")
                # 如果Excel中的频道目录不存在，继续使用原有的搜索逻辑
            else:
                # 验证视频文件是否存在
                video_path = os.path.join(channel_path, video_name)
                if os.path.exists(video_path):
                    return excel_channel_name
                else:
                    print(f"警告: 在指定频道中未找到视频文件: {video_path}")

        print(f"在文件系统中搜索频道...")
        # 原有的搜索逻辑作为备选方案
        try:
            for channel in os.listdir(MP4_DIR):
                channel_path = os.path.join(MP4_DIR, channel)
                if not os.path.isdir(channel_path):
                    continue

                lang_path = os.path.join(channel_path, self.language)
                if not os.path.exists(lang_path):
                    continue

                video_path = os.path.join(lang_path, video_name)
                if os.path.exists(video_path):
                    print(f"在文件系统中找到频道: {channel}")
                    return channel

            print(f"警告: 未找到视频文件对应的频道: {video_name}")
            return None

        except Exception as e:
            print(f"查找频道时出错: {e}")
            return None

    def upload_file_with_pyautogui(self, file_path):
        """使用pyautogui自动化系统文件对话框上传大文件"""
        if not HAS_PYAUTOGUI:
            print("pyautogui未安装，无法自动上传大文件")
            return False

        try:
            print("使用系统级自动化上传大文件...")

            # 等待文件对话框出现
            time.sleep(2)

            # 复制文件路径到剪贴板
            pyperclip.copy(file_path)
            print(f"已复制文件路径到剪贴板: {file_path}")

            # 在文件对话框中粘贴路径
            # Ctrl+L 打开地址栏（在大多数文件对话框中）
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.5)

            # 粘贴文件路径
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.5)

            # 按回车确认
            pyautogui.press("enter")
            time.sleep(2)

            print("文件路径已输入，上传中...")
            return True

        except Exception as e:
            print(f"自动上传文件时出错: {e}")
            return False

    def upload_file_with_cdp(
        self, page, file_path, selector='input[type="file"][name="Filedata"]'
    ):
        """使用CDP session直接操作DOM上传大文件，绕过50MB限制

        Args:
            page: Playwright页面对象
            file_path: 文件路径
            selector: 文件输入框选择器

        Returns:
            bool: 上传成功返回True，失败返回False
        """
        try:
            print("使用CDP session直接上传大文件...")

            # 创建CDP session
            cdp_session = page.context.new_cdp_session(page)

            # 检查文件输入框是否存在
            file_input_handle = page.query_selector(selector)
            if not file_input_handle:
                print(f"文件输入框未找到: {selector}")
                return False

            # 获取DOM文档
            dom_snapshot = cdp_session.send("DOM.getDocument")

            # 查找文件输入框的节点ID
            node_id_result = cdp_session.send(
                "DOM.querySelector",
                {"nodeId": dom_snapshot["root"]["nodeId"], "selector": selector},
            )

            if not node_id_result.get("nodeId"):
                print("无法获取文件输入框的节点ID")
                return False

            # 直接设置文件输入框的文件
            cdp_session.send(
                "DOM.setFileInputFiles",
                {"nodeId": node_id_result["nodeId"], "files": [file_path]},
            )

            print(f"通过CDP成功设置文件: {file_path}")
            return True

        except Exception as e:
            print(f"CDP文件上传失败: {e}")
            return False

    def run(self, max_count=1, dry_run=False):
        """运行自动发布系统"""
        print(f"=== 自动发布系统启动 ===")
        print(
            f"语言: {self.language} ({LANGUAGE_NAMES.get(self.language, self.language)})"
        )
        print(f"最大发布数量: {max_count}")
        print(f"试运行模式: {dry_run}")
        print()

        # 获取待发布视频列表
        pending_videos = self.get_pending_videos()
        if not pending_videos:
            print("没有待发布的视频")
            return

        # 限制发布数量
        videos_to_publish = pending_videos[:max_count]
        print(f"将要处理 {len(videos_to_publish)} 个视频")

        for i, video_info in enumerate(videos_to_publish, 1):
            video_name = video_info["MP4名称"]
            excel_channel_name = video_info.get("频道名称", "")
            print(f"\n--- 处理视频 {i}/{len(videos_to_publish)}: {video_name} ---")

            # 使用Excel中的频道信息查找频道名称
            channel_name = self.find_channel_name(video_name, excel_channel_name)
            if not channel_name:
                print(f"跳过视频 {video_name}（未找到频道）")
                continue

            print(f"频道: {channel_name}")

            # 获取视频内容
            video_content = self.get_video_content(video_name, channel_name)
            if not video_content["valid"] and not dry_run:
                print(f"跳过视频 {video_name}（内容无效）")
                continue

            # 每个视频都重新计算发布时间（确保获取最新的Excel数据）
            publish_time = self.calculate_next_publish_time()

            print(f"计划发布时间: {publish_time}")
            print(f"标题: {video_content['title']}")
            print(f"描述长度: {len(video_content['description'])} 字符")
            if video_content.get("thumbnail_path"):
                print(f"封面文件: {video_content['thumbnail_path']}")
            else:
                print(f"封面文件: 无")

            # 上传视频，标记是否为第一个视频
            is_first_video = i == 1
            success = self.upload_video(
                video_content, dry_run, publish_time, is_first_video
            )

            if success:
                if not dry_run:
                    # 更新Excel状态
                    self.update_publish_status(video_name, publish_time)
                    print(f"✅ 视频 {video_name} 发布成功，Excel已更新")
                    print(
                        f"📝 发布时间已写入Excel: {publish_time.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                else:
                    print(f"✅ [试运行] 视频 {video_name} 处理完成")
            else:
                print(f"❌ 视频 {video_name} 发布失败")

            # 如果不是试运行且不是最后一个视频，等待一段时间
            if not dry_run and i < len(videos_to_publish):
                print("等待60秒后处理下一个视频...")
                time.sleep(60)

        print(f"\n=== 发布完成 ===")

        # 保持浏览器打开，不自动关闭
        print("🌟 所有视频发布完成！浏览器将保持打开状态，方便您检查发布结果。")
        print("💡 如需关闭浏览器，请手动关闭AdsPower中的浏览器实例。")


def main():
    parser = argparse.ArgumentParser(description="YouTube视频自动发布系统")
    parser.add_argument(
        "-l",
        "--language",
        choices=["en", "ko"],
        default="en",
        help="发布语言 (默认: en)",
    )
    parser.add_argument(
        "-n",
        "--max-count",
        type=int,
        default=None,
        help="最大发布数量 (默认: 发布所有)",
    )
    parser.add_argument(
        "-d", "--dry-run", action="store_true", help="试运行模式，不实际发布"
    )
    parser.add_argument(
        "--ads-id", default="kq316tr", help="AdsPower浏览器ID (默认: kq316tr)"
    )
    parser.add_argument("--studio-url", help="YouTube Studio频道URL")

    args = parser.parse_args()

    # 检查必要文件是否存在
    if not os.path.exists(TRACKER_FILE):
        print(f"错误: 跟踪文件不存在: {TRACKER_FILE}")
        print("请先运行 generate_mp4_publish_tracker.py 生成跟踪文件")
        sys.exit(1)

    # 创建发布系统实例
    system = AutoPublishSystem(
        language=args.language, ads_id=args.ads_id, studio_url=args.studio_url
    )

    # 如果没有指定max_count，则发布所有视频
    max_count = args.max_count if args.max_count is not None else 999999

    # 运行发布系统
    try:
        system.run(max_count=max_count, dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"系统错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
