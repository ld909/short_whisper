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
6. 自动发布视频到YouTube（使用Playwright标准方法）
7. 更新Excel表格，标记为已发布并记录发布时间

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
from playwright.sync_api import sync_playwright


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

        # 根据语言自动选择对应的YouTube Studio URL
        if studio_url:
            # 如果用户明确提供了URL，使用用户提供的
            self.studio_url = studio_url
        else:
            # 根据语言自动选择默认URL
            if language == "ko":
                self.studio_url = (
                    "https://studio.youtube.com/channel/UCQ2rirB86LDa_LcyjJjeXUw"
                )
                print(f"🌏 韩文模式，使用韩文频道URL: {self.studio_url}")
            else:  # 默认英文
                self.studio_url = (
                    "https://studio.youtube.com/channel/UCiCMH2ZdFy3vNqa6X0NVsoA"
                )
                print(f"🌏 英文模式，使用英文频道URL: {self.studio_url}")

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
            print(f"📄 Excel文件路径: {TRACKER_FILE}")
            print(f"🌏 当前语言模式: {self.language}")

            # 检查Excel文件是否存在
            if not os.path.exists(TRACKER_FILE):
                raise FileNotFoundError(f"Excel文件不存在: {TRACKER_FILE}")

            # 检查Excel文件中是否有对应的语言sheet
            try:
                # 先读取所有sheet名称
                excel_file = pd.ExcelFile(TRACKER_FILE)
                available_sheets = excel_file.sheet_names
                print(f"📋 Excel中可用的工作表: {available_sheets}")

                if self.language not in available_sheets:
                    raise ValueError(
                        f"Excel文件中没有找到语言工作表 '{self.language}'。可用工作表: {available_sheets}"
                    )

                # 读取指定语言的工作表
                df = pd.read_excel(TRACKER_FILE, sheet_name=self.language)
                print(f"✅ 成功读取工作表 '{self.language}'，共 {len(df)} 行数据")

            except Exception as sheet_error:
                print(f"❌ 读取工作表时出错: {sheet_error}")
                raise sheet_error

            # 检查必要的列是否存在
            required_columns = ["是否已经发布", "发布时间"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                print(f"❌ Excel中缺少必要的列: {missing_columns}")
                print(f"📋 当前Excel的列名: {list(df.columns)}")
                raise ValueError(f"Excel中缺少必要的列: {missing_columns}")

            print(f"✅ Excel列检查通过")

            # 过滤已发布的视频（是否已经发布=1）
            print(f"🔍 开始过滤已发布的视频...")
            print(f"📊 '是否已经发布'列的数据类型: {df['是否已经发布'].dtype}")
            print(f"📊 '是否已经发布'列的唯一值: {df['是否已经发布'].unique()}")

            # 更宽泛的过滤条件，处理不同的数据类型
            published = df[
                (df["是否已经发布"] == 1)
                | (df["是否已经发布"] == "1")
                | (df["是否已经发布"] == True)
                | (df["是否已经发布"].astype(str).str.strip() == "1")
            ]
            print(f"📊 已发布视频数量: {len(published)}")

            # 详细显示已发布的视频信息（便于调试）
            if len(published) > 0:
                print(f"🔍 已发布视频详细信息:")
                for idx, row in published.iterrows():
                    mp4_name = row.get("MP4名称", "未知")
                    publish_time = row.get("发布时间", "无")
                    print(f"   - {mp4_name}: {publish_time}")

            # 如果全部都未发布，使用当前时间作为基准
            if len(published) == 0:
                print("📝 全部视频都未发布，使用当前时间作为基准")
                return datetime.now()

            # 显示已发布视频的发布时间列信息
            print(f"🔍 检查发布时间列...")
            print(f"📊 '发布时间'列的数据类型: {df['发布时间'].dtype}")
            print(
                f"📊 已发布视频中'发布时间'列的样本数据: {published['发布时间'].head()}"
            )

            # 获取发布时间列，排除空值
            publish_times = published["发布时间"].dropna()
            print(f"📅 有效发布时间记录数量: {len(publish_times)}")

            # 如果已发布视频中没有有效的发布时间记录，使用当前时间作为基准
            if len(publish_times) == 0:
                print("📝 已发布视频中没有有效的发布时间记录，使用当前时间作为基准")
                return datetime.now()

            # 显示发布时间的详细信息
            print(f"📅 所有有效发布时间:")
            for i, time_val in enumerate(publish_times):
                print(f"   {i+1}: {time_val} (类型: {type(time_val)})")

            # 转换为datetime
            try:
                publish_times_dt = pd.to_datetime(publish_times)
                print(f"✅ 成功转换为datetime格式")
                print(
                    f"📅 转换后的时间范围: {publish_times_dt.min()} 到 {publish_times_dt.max()}"
                )

                # 显示转换后的所有时间
                print(f"📅 转换后的所有发布时间:")
                for i, dt_val in enumerate(publish_times_dt):
                    print(f"   {i+1}: {dt_val}")

            except Exception as dt_error:
                print(f"❌ 转换为datetime时出错: {dt_error}")
                print(f"🔄 尝试使用不同的转换方法...")

                # 尝试不同的日期格式
                try:
                    publish_times_dt = pd.to_datetime(
                        publish_times, format="%Y-%m-%d %H:%M:%S"
                    )
                    print(f"✅ 使用标准格式转换成功")
                except:
                    try:
                        publish_times_dt = pd.to_datetime(
                            publish_times, infer_datetime_format=True
                        )
                        print(f"✅ 使用自动推断格式转换成功")
                    except Exception as final_dt_error:
                        print(f"❌ 所有日期转换方法都失败: {final_dt_error}")
                        raise final_dt_error

            # 直接找到最远的时间（包含未来时间）
            max_time = publish_times_dt.max()
            print(f"✅ 已发布视频的最远发布时间: {max_time}")
            print(f"📅 最远时间类型: {type(max_time)}")

            return max_time

        except Exception as e:
            print(f"❌ 获取发布时间时出错: {e}")
            print(f"🔍 错误类型: {type(e).__name__}")
            print(f"📊 错误详细信息: {str(e)}")
            print("📝 出错时使用当前时间作为基准")
            return datetime.now()

    def calculate_next_publish_time(self):
        """计算下一个发布时间

        逻辑：
        - 如果最远发布时间 >= 当前时间：最远时间 + 6小时
        - 如果最远发布时间 < 当前时间：当前时间 + 6小时（说明有一段时间没有发布了）
        """
        print("⏰ 开始计算下一个发布时间...")
        latest_time = self.get_latest_publish_time()
        current_time = datetime.now()

        print(f"🎯 从Excel获取的最远发布时间: {latest_time}")
        print(f"🎯 最远发布时间类型: {type(latest_time)}")
        print(f"🕐 当前系统时间: {current_time}")
        print(f"🕐 当前时间类型: {type(current_time)}")

        # 计算时间差
        time_diff = latest_time - current_time
        print(f"📊 时间差 (最远时间 - 当前时间): {time_diff}")
        print(f"📊 时间差秒数: {time_diff.total_seconds()}")

        if latest_time < current_time:
            print("📅 ✅ 判断结果: 最远发布时间 < 当前时间")
            print("📅 说明: 有一段时间没有发布了，使用当前时间作为基准")
            base_time = current_time
            print(f"🔄 选择基准时间: {base_time} (当前时间)")
        else:
            print("📅 ✅ 判断结果: 最远发布时间 >= 当前时间")
            print("📅 说明: 继续按计划发布，使用最远时间作为基准")
            base_time = latest_time
            print(f"🔄 选择基准时间: {base_time} (最远发布时间)")

        next_time = base_time + timedelta(hours=6)
        print(f"➕ 计算过程: {base_time} + 6小时 = {next_time}")
        print(f"✅ 最终下一个发布时间: {next_time}")
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

    def initialize_browser(self, max_retries=3):
        """初始化浏览器：先新开tab，再关闭其他tab，最后切换到新tab"""
        print("🔄 正在初始化浏览器...")

        for attempt in range(max_retries):
            print(f"📡 尝试连接浏览器 (第 {attempt + 1}/{max_retries} 次)...")

            # 连接AdsPower
            ws_endpoint, remote_debugging_url = self.get_adspower_info()
            if not ws_endpoint:
                print(f"❌ AdsPower连接失败 (第 {attempt + 1} 次)")
                if attempt < max_retries - 1:
                    print("⏳ 等待5秒后重试...")
                    time.sleep(5)
                    continue
                else:
                    return None, None, None, None

            playwright = None
            try:
                print("🎭 创建Playwright实例...")
                # 创建Playwright实例
                playwright = sync_playwright().start()

                print(f"🌐 尝试连接到浏览器: {remote_debugging_url}")
                # 设置较短的超时时间，快速失败以便重试
                browser = playwright.chromium.connect_over_cdp(
                    remote_debugging_url, timeout=15000  # 15秒超时
                )
                print("✅ 成功连接到浏览器！")

                # 获取上下文
                if not browser.contexts:
                    context = browser.new_context()
                    print("📝 创建了新的浏览器上下文")
                else:
                    context = browser.contexts[0]
                    print("📝 使用现有的浏览器上下文")

                # 获取当前所有页面
                print("📋 正在获取当前所有tab...")
                existing_pages = list(context.pages)
                print(f"🗂️ 当前存在 {len(existing_pages)} 个tab")

                # 先创建新的tab
                print("🆕 正在创建新的tab...")
                try:
                    new_page = context.new_page()
                    print("✅ 已创建新的tab")

                    # 验证新页面是否正常工作
                    new_page.goto("about:blank")
                    print("✅ 新tab验证成功")

                except Exception as page_error:
                    print(f"❌ 创建新tab失败: {page_error}")
                    raise page_error

                # 等待一下确保新tab创建完成
                time.sleep(1)

                # 现在关闭除新tab之外的所有现有tab
                print("🗂️ 正在关闭除新tab之外的所有现有tab...")
                closed_count = 0

                for page in existing_pages:
                    try:
                        page_url = page.url
                        # 确保不关闭新创建的tab
                        if page != new_page:
                            page.close()
                            print(f"   ✅ 已关闭tab: {page_url}")
                            closed_count += 1
                        else:
                            print(f"   🔒 保留新tab: {page_url}")
                    except Exception as e:
                        print(f"   ⚠️ 关闭tab时出错: {e}")

                print(f"📊 总共关闭了 {closed_count} 个旧tab，保留了新创建的tab")

                # 等待一下确保tab关闭完成
                time.sleep(1)

                # 确保切换到新的tab（通常新创建的tab会自动成为活动tab）
                print("🎯 正在切换到新创建的tab...")
                try:
                    new_page.bring_to_front()
                    print("✅ 已切换到新tab")
                except Exception as switch_error:
                    print(f"⚠️ 切换tab时出错: {switch_error}")
                    print("继续使用新tab（通常新tab已经是活动状态）")

                # 最终验证
                print("🔍 最终验证新tab状态...")
                try:
                    current_url = new_page.url
                    print(f"✅ 当前tab URL: {current_url}")

                    # 确认上下文中的页面情况
                    remaining_pages = context.pages
                    print(f"📊 剩余tab数量: {len(remaining_pages)}")

                    return playwright, browser, context, new_page

                except Exception as verify_error:
                    print(f"⚠️ 验证新tab时出错: {verify_error}")
                    # 即使验证出错，如果new_page存在就继续使用
                    if new_page:
                        return playwright, browser, context, new_page
                    else:
                        raise verify_error

            except Exception as e:
                print(f"❌ 浏览器连接失败 (第 {attempt + 1} 次): {e}")

                # 清理Playwright实例
                if playwright:
                    try:
                        playwright.stop()
                        print("🧹 已清理Playwright实例")
                    except:
                        pass

                if attempt < max_retries - 1:
                    print("🔄 尝试重新启动AdsPower浏览器...")
                    # 先尝试关闭浏览器
                    try:
                        if self.http:
                            close_response = self.http.request("GET", self.close_url)
                            print(f"🛑 关闭浏览器请求状态: {close_response.status}")
                    except Exception as close_error:
                        print(f"⚠️ 关闭浏览器时出错: {close_error}")

                    print("⏳ 等待10秒后重试...")
                    time.sleep(10)
                    continue
                else:
                    print("❌ 所有重试都失败了")
                    return None, None, None, None

        print("❌ 浏览器初始化彻底失败")
        return None, None, None, None

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

    def upload_video(self, video_content, page, dry_run=False, publish_time=None):
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

        try:
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

            # 上传视频文件
            print(f"正在上传视频: {video_content['mp4_path']}")

            # 使用CDP方法上传大文件，绕过50MB限制
            try:
                # 获取文件输入选择器
                file_selector = 'input[type="file"][name="Filedata"]'

                # 首先检查文件输入元素是否存在
                file_input_handle = page.query_selector(file_selector)
                if not file_input_handle:
                    print("❌ 文件输入元素未找到!")
                    return False

                # 创建CDP会话
                print("🔗 创建CDP会话...")
                cdp_session = page.context.new_cdp_session(page)

                # 获取DOM文档
                print("📄 获取DOM文档...")
                dom_snapshot = cdp_session.send("DOM.getDocument")

                # 查找文件输入节点
                print("🔍 查找文件输入节点...")
                node_result = cdp_session.send(
                    "DOM.querySelector",
                    {
                        "nodeId": dom_snapshot["root"]["nodeId"],
                        "selector": file_selector,
                    },
                )

                if not node_result.get("nodeId"):
                    print("❌ 无法找到文件输入节点!")
                    cdp_session.detach()
                    return False

                # 使用CDP设置文件
                print("📁 使用CDP设置文件...")
                cdp_session.send(
                    "DOM.setFileInputFiles",
                    {
                        "nodeId": node_result["nodeId"],
                        "files": [video_content["mp4_path"]],
                    },
                )

                # 关闭CDP会话
                cdp_session.detach()
                print("✅ 视频文件上传完成（使用CDP方法）")

            except Exception as cdp_error:
                print(f"❌ CDP上传方法失败: {cdp_error}")
                print("🔄 尝试使用标准Playwright方法...")

                # 如果CDP方法失败，回退到标准方法
                try:
                    file_input = page.locator('input[type="file"][name="Filedata"]')
                    file_input.set_input_files(video_content["mp4_path"])
                    print("✅ 视频文件上传完成（使用标准方法）")
                except Exception as standard_error:
                    print(f"❌ 标准上传方法也失败: {standard_error}")
                    return False

            # 等待上传处理
            page.wait_for_load_state("networkidle")

            # 添加随机延迟，模拟人工操作
            delay = random.uniform(1.0, 1.5)
            print(f"等待 {delay:.2f} 秒后开始输入标题...")
            page.wait_for_timeout(int(delay * 1000))

            # 输入标题 - 增加更长的等待时间确保页面完全加载
            title_selector = 'div[id="textbox"][aria-label="Add a title that describes your video (type @ to mention a channel)"]'
            print("等待标题输入框...")
            page.wait_for_selector(title_selector, state="visible")

            # 增加额外等待时间，确保输入框完全可用
            additional_wait = random.uniform(3.0, 5.0)
            print(f"等待额外 {additional_wait:.2f} 秒确保标题输入框完全可用...")
            page.wait_for_timeout(int(additional_wait * 1000))

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

            # 增加额外等待时间，确保描述输入框完全可用
            additional_wait = random.uniform(2.0, 3.0)
            print(f"等待额外 {additional_wait:.2f} 秒确保描述输入框完全可用...")
            page.wait_for_timeout(int(additional_wait * 1000))

            desc_input = page.locator(desc_selector)
            desc_input.click()
            desc_input.press("Control+a")
            desc_input.fill(video_content["description"])
            print("已输入描述")

            # 验证描述是否成功输入
            try:
                filled_desc = desc_input.input_value()
                if filled_desc.strip() == video_content["description"].strip():
                    print("✅ 描述输入验证成功")
                else:
                    print("⚠️ 描述输入可能不完整，重试一次...")
                    desc_input.click()
                    desc_input.press("Control+a")
                    desc_input.fill(video_content["description"])
                    page.wait_for_timeout(1000)
            except Exception as desc_verify_error:
                print(f"描述验证时出错: {desc_verify_error}")
                print("继续处理，但请注意检查")

            # 添加随机延迟，模拟人工操作
            delay = random.uniform(2.0, 3.0)
            print(f"等待 {delay:.2f} 秒后开始上传封面...")
            page.wait_for_timeout(int(delay * 1000))

            # 改进的封面上传逻辑
            if video_content.get("thumbnail_path") and os.path.exists(
                video_content["thumbnail_path"]
            ):
                print(f"📷 正在上传封面: {video_content['thumbnail_path']}")

                # 使用多次重试机制上传封面
                thumbnail_upload_success = False
                max_thumbnail_retries = 3

                for retry_attempt in range(max_thumbnail_retries):
                    try:
                        print(
                            f"🔄 封面上传尝试 {retry_attempt + 1}/{max_thumbnail_retries}"
                        )

                        # 针对YouTube的具体封面输入框选择器，按优先级排序
                        thumbnail_selectors = [
                            'input#file-loader[type="file"][accept="image/jpeg,image/png"]',  # 最精确的选择器
                            "input#file-loader.style-scope.ytcp-thumbnail-uploader",  # 基于class的选择器
                            'input#file-loader[type="file"]',  # 原始选择器
                            'input[type="file"].ytcp-thumbnail-uploader',  # class选择器
                            'input[type="file"][accept*="image/jpeg"]',  # 基于accept属性
                            'input[type="file"][accept*="image/png"]',  # 基于accept属性
                        ]

                        # 等待封面上传区域完全加载 - 增加等待时间
                        print("⏰ 等待封面上传区域加载...")
                        page.wait_for_timeout(5000)  # 增加到5秒

                        # 尝试找到有效的封面输入框
                        thumbnail_input_found = False
                        active_selector = None

                        for selector in thumbnail_selectors:
                            try:
                                print(f"🔍 检查选择器: {selector}")
                                # 检查元素是否存在
                                element = page.query_selector(selector)
                                if element:
                                    # 对于隐藏的input元素，不检查is_visible()
                                    # 因为YouTube的封面上传input是hidden="true"
                                    print(f"✅ 找到封面输入框: {selector}")
                                    active_selector = selector
                                    thumbnail_input_found = True

                                    # 额外验证：检查元素的hidden属性和accept属性
                                    try:
                                        element_info = page.evaluate(
                                            """(selector) => {
                                            const el = document.querySelector(selector);
                                            if (el) {
                                                return {
                                                    hidden: el.hidden,
                                                    type: el.type,
                                                    accept: el.accept,
                                                    id: el.id,
                                                    className: el.className
                                                };
                                            }
                                            return null;
                                        }""",
                                            selector,
                                        )

                                        if element_info:
                                            print(f"📋 元素信息: {element_info}")
                                            # 验证这确实是封面上传的input
                                            if element_info.get(
                                                "type"
                                            ) == "file" and "image" in element_info.get(
                                                "accept", ""
                                            ):
                                                print(f"✅ 确认这是有效的图片上传input")
                                                break
                                            else:
                                                print(f"⚠️ 元素类型不匹配，继续查找")
                                                thumbnail_input_found = False
                                                continue
                                        else:
                                            print(f"⚠️ 无法获取元素详细信息")
                                            thumbnail_input_found = False
                                            continue

                                    except Exception as eval_error:
                                        print(f"⚠️ 验证元素时出错: {eval_error}")
                                        # 即使验证出错，如果找到了元素就继续尝试
                                        print(f"继续使用找到的元素: {selector}")
                                        break
                                else:
                                    print(f"❌ 元素不存在: {selector}")

                            except Exception as selector_error:
                                print(
                                    f"⚠️ 检查选择器时出错 {selector}: {selector_error}"
                                )
                                continue

                        if not thumbnail_input_found:
                            print(
                                f"❌ 第 {retry_attempt + 1} 次尝试：未找到有效的封面输入框"
                            )

                            # 尝试通过JavaScript查找所有file input元素进行诊断
                            try:
                                print("🔍 正在诊断页面中的file input元素...")
                                file_inputs_info = page.evaluate(
                                    """() => {
                                    const inputs = document.querySelectorAll('input[type="file"]');
                                    return Array.from(inputs).map(input => ({
                                        id: input.id,
                                        className: input.className,
                                        accept: input.accept,
                                        hidden: input.hidden,
                                        name: input.name
                                    }));
                                }"""
                                )

                                print(f"📋 页面中的file input元素: {file_inputs_info}")

                                # 如果找到了file input，尝试使用通用选择器
                                if file_inputs_info:
                                    for input_info in file_inputs_info:
                                        if "image" in input_info.get("accept", ""):
                                            if input_info.get("id"):
                                                fallback_selector = f'input#{input_info["id"]}[type="file"]'
                                                print(
                                                    f"🔄 尝试回退选择器: {fallback_selector}"
                                                )
                                                if page.query_selector(
                                                    fallback_selector
                                                ):
                                                    active_selector = fallback_selector
                                                    thumbnail_input_found = True
                                                    break

                            except Exception as diagnostic_error:
                                print(f"⚠️ 诊断时出错: {diagnostic_error}")

                            if not thumbnail_input_found:
                                if retry_attempt < max_thumbnail_retries - 1:
                                    print("⏳ 等待5秒后重试...")
                                    page.wait_for_timeout(5000)
                                    continue
                                else:
                                    print("❌ 所有尝试都失败，跳过封面上传")
                                    break

                        # 使用找到的选择器进行上传
                        print(f"📁 使用选择器上传封面: {active_selector}")

                        # 优先使用CDP方法（对隐藏元素更有效）
                        try:
                            print("🔗 使用CDP方法上传封面...")
                            cdp_session = page.context.new_cdp_session(page)

                            # 获取DOM文档
                            dom_snapshot = cdp_session.send("DOM.getDocument")

                            # 查找封面文件输入节点
                            node_result = cdp_session.send(
                                "DOM.querySelector",
                                {
                                    "nodeId": dom_snapshot["root"]["nodeId"],
                                    "selector": active_selector,
                                },
                            )

                            if node_result.get("nodeId"):
                                # 使用CDP设置封面文件
                                cdp_session.send(
                                    "DOM.setFileInputFiles",
                                    {
                                        "nodeId": node_result["nodeId"],
                                        "files": [video_content["thumbnail_path"]],
                                    },
                                )
                                cdp_session.detach()
                                print("✅ 封面文件上传完成（CDP方法）")
                            else:
                                cdp_session.detach()
                                raise Exception("CDP方法找不到节点")

                        except Exception as cdp_thumb_error:
                            print(f"❌ CDP封面上传失败: {cdp_thumb_error}")
                            print("🔄 尝试标准Playwright方法...")

                            # 回退到标准方法（即使对隐藏元素，Playwright也能处理）
                            try:
                                thumbnail_input = page.locator(active_selector)
                                thumbnail_input.set_input_files(
                                    video_content["thumbnail_path"]
                                )
                                print("✅ 封面文件上传完成（标准方法）")
                            except Exception as standard_thumb_error:
                                print(f"❌ 标准方法也失败: {standard_thumb_error}")

                                # 最后尝试：使用JavaScript直接设置文件
                                try:
                                    print("🔄 尝试JavaScript方法...")
                                    page.evaluate(
                                        """(args) => {
                                        const input = document.querySelector(args.selector);
                                        if (input) {
                                            // 创建一个File对象（这只是模拟，实际还是需要真实文件路径）
                                            const event = new Event('change', { bubbles: true });
                                            input.dispatchEvent(event);
                                            return true;
                                        }
                                        return false;
                                    }""",
                                        {"selector": active_selector},
                                    )

                                    # JavaScript方法无法真正设置文件，所以再次尝试Playwright
                                    page.set_input_files(
                                        active_selector, video_content["thumbnail_path"]
                                    )
                                    print(
                                        "✅ 封面文件上传完成（JavaScript+Playwright方法）"
                                    )

                                except Exception as js_error:
                                    print(f"❌ JavaScript方法也失败: {js_error}")
                                    raise Exception("所有上传方法都失败")

                        # 等待封面上传处理完成
                        print("⏰ 等待封面上传处理完成...")
                        page.wait_for_timeout(8000)  # 增加到8秒

                        # 验证封面上传是否成功
                        print("🔍 验证封面上传状态...")
                        verification_success = False

                        # 更全面的验证方式
                        verification_selectors = [
                            # 直接的缩略图元素
                            '[alt*="thumbnail"]',
                            '[alt*="Thumbnail"]',
                            'img[src*="thumbnail"]',
                            'img[src*="ytimg.com"]',  # YouTube图片域名
                            # YouTube特定的元素
                            "ytcp-thumbnail-uploader img",
                            ".ytcp-thumbnail-uploader img",
                            # 可能的canvas元素
                            "canvas",
                            # 通用图片角色
                            '[role="img"]',
                            # 可能的预览容器
                            ".thumbnail-preview",
                            ".thumbnail-container img",
                        ]

                        for verify_selector in verification_selectors:
                            try:
                                elements = page.locator(verify_selector)
                                if elements.count() > 0:
                                    print(
                                        f"✅ 封面验证成功（找到元素: {verify_selector}）"
                                    )
                                    verification_success = True
                                    break
                            except:
                                continue

                        # 额外验证：检查页面是否有上传成功的指示
                        if not verification_success:
                            try:
                                page_content = page.content()
                                if any(
                                    indicator in page_content.lower()
                                    for indicator in [
                                        "thumbnail uploaded",
                                        "image uploaded",
                                        "upload complete",
                                    ]
                                ):
                                    print("✅ 封面验证成功（页面内容指示）")
                                    verification_success = True
                            except:
                                pass

                        if verification_success:
                            print("🎉 封面上传并验证成功！")
                            thumbnail_upload_success = True
                            break
                        else:
                            print(f"⚠️ 第 {retry_attempt + 1} 次尝试：未检测到封面预览")
                            if retry_attempt < max_thumbnail_retries - 1:
                                print("🔄 将重试封面上传...")
                                page.wait_for_timeout(3000)
                                continue
                            else:
                                print("⚠️ 封面验证失败，但继续处理")
                                break

                    except Exception as thumbnail_retry_error:
                        print(
                            f"❌ 第 {retry_attempt + 1} 次封面上传尝试失败: {thumbnail_retry_error}"
                        )
                        if retry_attempt < max_thumbnail_retries - 1:
                            print("⏳ 等待3秒后重试...")
                            page.wait_for_timeout(3000)
                            continue
                        else:
                            print("❌ 所有封面上传尝试都失败，继续处理视频发布")
                            break

                if not thumbnail_upload_success:
                    print("⚠️ 封面上传最终失败，但不影响视频发布流程")

            else:
                print("⚠️ 跳过封面上传（封面文件不存在）")

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
                                schedule_button.wait_for(state="visible", timeout=5000)

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

                # 验证发布是否真正成功
                print("验证发布状态...")
                page.wait_for_timeout(3000)  # 再等待3秒

                # 检查页面是否显示发布成功的相关信息
                try:
                    # 等待页面标题包含"scheduled"或类似的成功提示
                    page.wait_for_timeout(2000)
                    current_url = page.url
                    print(f"当前页面URL: {current_url}")

                    # 方法1: 检查URL变化 - 成功后通常会跳转到不同页面
                    if "upload" in current_url.lower():
                        print("⚠️ 仍在上传页面，发布可能未成功")
                        return False

                    # 方法2: 检查页面是否有成功提示信息
                    success_indicators = [
                        "Scheduled",  # 安排发布成功
                        "Video scheduled",  # 视频已安排
                        "scheduled successfully",  # 安排成功
                        "Upload complete",  # 上传完成
                        "Processing",  # 处理中也表示上传成功
                    ]

                    page_content = ""
                    try:
                        # 获取页面文本内容进行检查
                        page_content = page.locator("body").inner_text()
                    except:
                        pass

                    success_found = False
                    for indicator in success_indicators:
                        if indicator.lower() in page_content.lower():
                            print(f"✅ 找到成功指示: {indicator}")
                            success_found = True
                            break

                    # 方法3: 检查是否还有错误提示
                    error_indicators = [
                        "Error uploading",
                        "Upload failed",
                        "Something went wrong",
                        "Try again",
                        "Retry",
                    ]

                    error_found = False
                    for error in error_indicators:
                        if error.lower() in page_content.lower():
                            print(f"❌ 发现错误指示: {error}")
                            error_found = True
                            break

                    # 综合判断
                    if error_found:
                        print("⚠️ 页面显示错误信息，发布失败")
                        return False

                    if success_found:
                        print("✅ 发现成功提示，发布验证通过")
                    else:
                        print("⚠️ 未发现明确的成功提示，但也没有错误，谨慎继续")
                        # 再等待一会儿看看页面是否会变化
                        page.wait_for_timeout(3000)

                        # 再次检查URL
                        final_url = page.url
                        if "upload" in final_url.lower():
                            print("⚠️ 最终检查：仍在上传页面，发布失败")
                            return False

                    print("✅ 发布验证最终通过")

                except Exception as verify_error:
                    print(f"发布验证时出错: {verify_error}")
                    print("⚠️ 无法确认发布状态，为安全起见标记为失败")
                    return False

                print("✅ 视频发布配置完成且验证成功")
                return True
            else:
                # 如果没有设置发布时间，直接发布
                print("正在立即发布...")
                # 点击Publish按钮
                publish_button = page.locator('button:has-text("Publish")')
                publish_button.click()
                print("已点击Publish按钮")

                # 等待发布完成并验证
                print("等待立即发布完成...")
                page.wait_for_timeout(5000)

                # 验证立即发布是否成功
                try:
                    page.wait_for_timeout(3000)
                    current_url = page.url
                    print(f"当前页面URL: {current_url}")

                    # 方法1: 检查URL变化 - 成功后通常会跳转到不同页面
                    if "upload" in current_url.lower():
                        print("⚠️ 仍在上传页面，立即发布可能未成功")
                        return False

                    # 方法2: 检查页面是否有成功提示信息
                    success_indicators = [
                        "Published",  # 已发布
                        "Video published",  # 视频已发布
                        "published successfully",  # 发布成功
                        "Upload complete",  # 上传完成
                        "Processing",  # 处理中也表示上传成功
                        "Public",  # 公开状态
                    ]

                    page_content = ""
                    try:
                        # 获取页面文本内容进行检查
                        page_content = page.locator("body").inner_text()
                    except:
                        pass

                    success_found = False
                    for indicator in success_indicators:
                        if indicator.lower() in page_content.lower():
                            print(f"✅ 找到成功指示: {indicator}")
                            success_found = True
                            break

                    # 方法3: 检查是否还有错误提示
                    error_indicators = [
                        "Error uploading",
                        "Upload failed",
                        "Something went wrong",
                        "Try again",
                        "Retry",
                    ]

                    error_found = False
                    for error in error_indicators:
                        if error.lower() in page_content.lower():
                            print(f"❌ 发现错误指示: {error}")
                            error_found = True
                            break

                    # 综合判断
                    if error_found:
                        print("⚠️ 页面显示错误信息，立即发布失败")
                        return False

                    if success_found:
                        print("✅ 发现成功提示，立即发布验证通过")
                    else:
                        print("⚠️ 未发现明确的成功提示，但也没有错误，谨慎继续")
                        # 再等待一会儿看看页面是否会变化
                        page.wait_for_timeout(3000)

                        # 再次检查URL
                        final_url = page.url
                        if "upload" in final_url.lower():
                            print("⚠️ 最终检查：仍在上传页面，立即发布失败")
                            return False

                    print("✅ 立即发布验证最终通过")

                except Exception as verify_error:
                    print(f"立即发布验证时出错: {verify_error}")
                    print("⚠️ 无法确认发布状态，为安全起见标记为失败")
                    return False

                print("✅ 视频立即发布完成且验证成功")
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

    def check_upload_progress(self, page):
        """检查页面的上传进度状态 - 基于"Uploading"文字的精确判断

        核心逻辑：
        - 上传中：span元素包含"Uploading"文字（唯一可靠标准）
        - 上传完成：没有"Uploading"文字且在上传页面

        Returns:
            str: 状态值
            - 'uploading': 正在上传中（找到"Uploading"文字）
            - 'completed': 上传完成（在上传页面但没有"Uploading"文字）
            - 'error': 上传出错
            - 'not_upload_page': 不是上传页面
        """
        try:
            # 首先检查是否在上传页面
            current_url = page.url
            if "upload" not in current_url.lower():
                return "not_upload_page"

            print(f"🔍 正在检查页面上传状态: {current_url}")

            # 核心检查：查找包含"Uploading"的span元素
            print(f"🎯 检查关键指标：span元素中的'Uploading'文字...")

            try:
                # 查找所有span元素，检查是否包含"Uploading"
                spans = page.query_selector_all("span")
                uploading_found = False
                uploading_text = ""

                for span in spans:
                    try:
                        span_text = span.inner_text().strip()
                        if "Uploading" in span_text:
                            uploading_found = True
                            uploading_text = span_text
                            print(f"✅ 发现上传中标识: '{span_text}'")
                            break
                    except:
                        continue

                if uploading_found:
                    print(f"🔄 确认状态：正在上传中")
                    return "uploading"
                else:
                    print(f"✅ 未发现'Uploading'文字，上传已完成")

            except Exception as span_error:
                print(f"⚠️ 检查span元素时出错: {span_error}")
                # 如果检查span出错，使用页面内容作为备选
                print(f"🔄 使用页面内容备选检查...")
                try:
                    page_content = page.locator("body").inner_text()
                    if "Uploading" in page_content:
                        print(f"✅ 页面内容中发现'Uploading'，确认为上传中")
                        return "uploading"
                    else:
                        print(f"✅ 页面内容中未发现'Uploading'，确认为已完成")
                except Exception as content_error:
                    print(f"⚠️ 页面内容检查也失败: {content_error}")
                    print(f"🔒 为安全起见，假设仍在上传中")
                    return "uploading"

            # 到这里说明没有找到"Uploading"，检查是否有明确的错误信息
            print(f"🔍 检查是否有错误信息...")
            try:
                page_content = page.locator("body").inner_text()
                page_content_lower = page_content.lower()

                # 明确的错误状态指示词
                error_indicators = [
                    "upload failed",
                    "error uploading",
                    "something went wrong",
                    "upload error",
                    "failed to upload",
                    "upload interrupted",
                    "connection error",
                    "network error",
                    "retry upload",
                    "upload unsuccessful",
                ]

                found_error_indicators = []
                for indicator in error_indicators:
                    if indicator in page_content_lower:
                        found_error_indicators.append(indicator)

                if found_error_indicators:
                    print(f"❌ 发现错误指示: {found_error_indicators}")
                    return "error"

            except Exception as error_check_error:
                print(f"⚠️ 错误检查时出错: {error_check_error}")

            # 没有"Uploading"且没有错误，说明上传已完成
            print(f"✅ 最终判断：上传已完成（无'Uploading'文字且无错误信息）")
            return "completed"

        except Exception as e:
            print(f"⚠️ 检查上传进度时出错: {e}")
            print(f"🔒 出错时默认认为仍在上传中")
            return "uploading"

    def wait_for_tab_slot_with_countdown(self, context, current_page, max_tabs=6):
        """当tab数量达到限制时，等待30分钟并显示倒计时，然后新开tab并关闭其他所有tab

        Args:
            context: 浏览器上下文
            current_page: 当前页面
            max_tabs: 最大tab数量限制

        Returns:
            bool: 是否成功处理
        """
        if not context:
            return False

        current_tab_count = len(context.pages)

        if current_tab_count < max_tabs:
            print(f"✅ Tab数量未达限制 (当前: {current_tab_count}/{max_tabs})")
            return True

        print(f"⏰ Tab数量已达限制 ({current_tab_count}/{max_tabs})")
        print(f"🕐 开始30分钟倒计时等待...")

        # 30分钟 = 1800秒
        total_seconds = 30 * 60

        try:
            for remaining in range(total_seconds, 0, -1):
                # 计算剩余的分钟和秒数
                minutes = remaining // 60
                seconds = remaining % 60

                # 显示倒计时，使用\r让光标回到行首覆盖之前的内容
                print(
                    f"\r⏰ 倒计时: {minutes:02d}:{seconds:02d} 剩余", end="", flush=True
                )

                # 等待1秒
                time.sleep(1)

            # 倒计时结束，换行
            print(f"\n✅ 30分钟等待完成！")

            # 创建新的第7个tab
            print(f"🆕 正在创建第7个tab...")
            new_page = context.new_page()
            print(f"✅ 已创建新tab")

            # 切换到新tab
            new_page.bring_to_front()
            print(f"✅ 已切换到新tab")

            # 关闭所有其他tab（除了新创建的tab）
            print(f"🗂️ 正在关闭其他所有tab...")
            pages_to_close = [page for page in context.pages if page != new_page]
            closed_count = 0

            for page in pages_to_close:
                try:
                    page_url = page.url
                    page.close()
                    closed_count += 1
                    print(f"   ✅ 已关闭tab: {page_url}")
                except Exception as e:
                    print(f"   ⚠️ 关闭tab时出错: {e}")

            print(f"📊 总共关闭了 {closed_count} 个tab，保留了新创建的tab")
            print(f"📊 当前tab数量: {len(context.pages)}")

            # 更新current_page引用（在调用方法中需要处理）
            return new_page  # 返回新创建的页面

        except KeyboardInterrupt:
            print(f"\n🛑 倒计时被用户中断")
            raise  # 重新抛出KeyboardInterrupt，让上层处理
        except Exception as e:
            print(f"\n❌ 倒计时等待时出错: {e}")
            return False

    def close_all_other_tabs(self, context, keep_page):
        """关闭除指定页面外的所有其他tab

        Args:
            context: 浏览器上下文
            keep_page: 要保留的页面

        Returns:
            int: 关闭的tab数量
        """
        if not context:
            return 0

        try:
            pages = context.pages
            closed_count = 0

            print(f"🗂️ 正在关闭除当前页面外的所有tab...")

            for page in pages:
                if page != keep_page:
                    try:
                        page_url = page.url
                        page.close()
                        closed_count += 1
                        print(f"   ✅ 已关闭tab: {page_url}")
                    except Exception as e:
                        print(f"   ⚠️ 关闭tab时出错: {e}")

            print(f"📊 总共关闭了 {closed_count} 个tab")
            return closed_count

        except Exception as e:
            print(f"⚠️ 关闭其他tab时出错: {e}")
            return 0

    def run(self, max_count=1, dry_run=False):
        """运行自动发布系统"""
        print(f"=== 自动发布系统启动 ===")
        print(
            f"语言: {self.language} ({LANGUAGE_NAMES.get(self.language, self.language)})"
        )
        print(f"最大发布数量: {max_count}")
        print(f"试运行模式: {dry_run}")

        if not dry_run:
            print("\n📌 重要提示:")
            print("   • 系统将自动管理浏览器tab，初始化时会关闭所有现有tab")
            print("   • 每个视频都会在新的tab中发布")
            print("   • 当tab数量达到6个时，会等待30分钟倒计时")
            print("   • 30分钟后会新开第7个tab并关闭其他所有tab")
            print("   • 使用 Ctrl+C 可以随时中断程序")
            print("   • 程序结束后浏览器会保持打开，方便检查发布结果")
        print()

        # 获取待发布视频列表
        pending_videos = self.get_pending_videos()
        if not pending_videos:
            print("没有待发布的视频")
            return

        # 限制发布数量
        videos_to_publish = pending_videos[:max_count]
        print(f"将要处理 {len(videos_to_publish)} 个视频")

        # 初始化浏览器（只在非试运行模式下执行）
        playwright = None
        browser = None
        context = None
        page = None

        if not dry_run:
            print("\n🚀 正在初始化浏览器...")
            playwright, browser, context, page = self.initialize_browser()
            if not page:
                print("❌ 浏览器初始化失败，终止运行")
                print("💡 建议检查:")
                print("   • AdsPower是否正常运行")
                print("   • 浏览器ID是否正确")
                print("   • 网络连接是否正常")
                print("   • 尝试手动启动AdsPower浏览器实例")
                return
            print("✅ 浏览器初始化完成\n")

        try:
            for i, video_info in enumerate(videos_to_publish, 1):
                video_name = video_info["MP4名称"]
                excel_channel_name = video_info.get("频道名称", "")
                print(f"\n--- 处理视频 {i}/{len(videos_to_publish)}: {video_name} ---")

                # 显示当前tab状态
                if not dry_run and context:
                    current_tab_count = len(context.pages)
                    print(f"📊 开始处理前Tab数量: {current_tab_count}")

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

                # 为每个视频创建新的tab（包括第一个视频）
                if not dry_run:
                    # 简化的tab数量检查和管理
                    print(f"🔍 检查tab数量...")
                    current_tab_count = len(context.pages)
                    print(f"📊 当前tab数量: {current_tab_count}")

                    if current_tab_count >= 6:
                        print(f"⏳ Tab数量已达限制 ({current_tab_count}/6)")
                        print(f"🕐 将等待30分钟后新开tab并关闭其他所有tab...")

                        # 执行30分钟等待并创建新tab
                        result = self.wait_for_tab_slot_with_countdown(
                            context, page, max_tabs=6
                        )

                        # 检查结果，如果是新页面对象就更新引用
                        if hasattr(result, "url"):  # 返回的是新页面对象
                            print(f"✅ 已创建新tab并关闭其他tab，更新页面引用")
                            page = result  # 更新page引用为新创建的页面
                        elif result is False:
                            print(f"❌ 等待过程出错，跳过视频: {video_name}")
                            continue
                    else:
                        print(f"🆕 正在为第 {i} 个视频创建新的tab...")
                        try:
                            # 创建新的tab
                            new_page = context.new_page()
                            print("✅ 已创建新的tab")

                            # 切换到新的tab
                            new_page.bring_to_front()
                            print("✅ 已切换到新的tab")

                            # 更新page对象为新的tab
                            page = new_page
                            print("✅ 已更新页面对象为新tab")

                            # 等待一下确保tab切换完成
                            page.wait_for_timeout(2000)

                        except Exception as new_tab_error:
                            print(f"❌ 创建新tab时出错: {new_tab_error}")
                            print("🔄 继续在当前tab中处理...")

                # 上传视频
                try:
                    if dry_run:
                        # 试运行模式，不需要page对象
                        success = self.upload_video(
                            video_content, None, dry_run, publish_time
                        )
                    else:
                        # 正常模式，传递page对象
                        success = self.upload_video(
                            video_content, page, dry_run, publish_time
                        )
                except Exception as upload_error:
                    print(f"❌ 上传视频时发生异常: {upload_error}")
                    print("🔄 跳过当前视频，继续处理下一个...")
                    success = False

                if success:
                    if not dry_run:
                        # 只有在真正成功发布/安排发布后才更新Excel状态
                        update_success = self.update_publish_status(
                            video_name, publish_time
                        )
                        if update_success:
                            print(f"✅ 视频 {video_name} 发布成功，Excel已更新")
                            print(
                                f"📝 发布时间已写入Excel: {publish_time.strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                        else:
                            print(f"⚠️ 视频 {video_name} 发布成功，但Excel更新失败")
                    else:
                        print(f"✅ [试运行] 视频 {video_name} 处理完成")
                else:
                    print(f"❌ 视频 {video_name} 发布失败，Excel状态不会更新")

                # 显示当前tab数量（不再进行复杂的清理操作）
                if not dry_run and context:
                    current_tab_count = len(context.pages)
                    print(f"📊 第 {i} 个视频处理完成，当前Tab数量: {current_tab_count}")

                # 如果不是试运行且不是最后一个视频，等待一段时间
                if not dry_run and i < len(videos_to_publish):
                    print("等待20秒后处理下一个视频...")
                    try:
                        page.wait_for_timeout(20000)
                    except Exception as wait_error:
                        print(f"⚠️ 等待时出错: {wait_error}")
                        print("使用系统等待替代...")
                        time.sleep(20)

        except KeyboardInterrupt:
            print("\n🛑 用户中断操作")
            raise  # 重新抛出，让main函数处理
        except Exception as e:
            print(f"❌ 运行过程中发生错误: {e}")
            print("🔄 尝试继续处理或安全退出...")
        finally:
            # 清理资源
            if not dry_run and playwright:
                try:
                    print("\n🧹 正在清理浏览器资源...")
                    # 显示最终的tab统计
                    if context:
                        final_tab_count = len(context.pages)
                        print(f"📊 最终Tab数量: {final_tab_count}")

                        # 显示剩余tab的URL信息
                        print("🔍 最终tab列表:")
                        try:
                            pages = context.pages
                            for i, final_page in enumerate(pages):
                                try:
                                    if not final_page.is_closed():
                                        page_url = final_page.url
                                        print(f"   Tab {i+1}: {page_url}")
                                except:
                                    print(f"   Tab {i+1}: 状态检查失败")
                        except Exception as final_check_error:
                            print(f"⚠️ 最终状态检查时出错: {final_check_error}")

                    # 不主动关闭浏览器，但清理Playwright连接
                    print("💡 浏览器将保持打开状态，Playwright连接已断开")
                    print("💡 如需关闭浏览器，请手动关闭AdsPower中的浏览器实例")
                except Exception as cleanup_error:
                    print(f"⚠️ 清理资源时出错: {cleanup_error}")

        print(f"\n=== 发布完成 ===")
        if not dry_run:
            print(f"📊 总计处理了 {len(videos_to_publish)} 个视频")
            print("💡 上传中的视频将在后台继续处理，建议稍后检查发布状态")


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
        "--ads-id",
        default=None,
        help="AdsPower浏览器ID (默认: 根据语言自动选择，en=kq316tr, ko=kyvhm2m)",
    )
    parser.add_argument("--studio-url", help="YouTube Studio频道URL")

    args = parser.parse_args()

    # 根据语言自动选择浏览器ID（如果用户没有明确指定）
    if args.ads_id is None:
        if args.language == "ko":
            ads_id = "kyvhm2m"
            print(f"🌏 检测到韩文模式，自动使用浏览器ID: {ads_id}")
        else:  # 默认英文
            ads_id = "kq316tr"
            print(f"🌏 检测到英文模式，自动使用浏览器ID: {ads_id}")
    else:
        ads_id = args.ads_id
        print(f"🔧 使用用户指定的浏览器ID: {ads_id}")

    # 检查必要文件是否存在
    if not os.path.exists(TRACKER_FILE):
        print(f"❌ 错误: 跟踪文件不存在: {TRACKER_FILE}")
        print("📝 请先运行 generate_mp4_publish_tracker.py 生成跟踪文件")
        sys.exit(1)

    # 创建发布系统实例
    system = AutoPublishSystem(
        language=args.language, ads_id=ads_id, studio_url=args.studio_url
    )

    # 如果没有指定max_count，则发布所有视频
    max_count = args.max_count if args.max_count is not None else 999999

    print("🎬 YouTube视频自动发布系统")
    print("=" * 50)

    # 运行发布系统
    try:
        system.run(max_count=max_count, dry_run=args.dry_run)
        print("\n🎉 程序正常结束")

    except KeyboardInterrupt:
        print("\n\n🛑 用户中断操作")
        print("📝 提示：浏览器连接已断开，AdsPower浏览器实例仍保持打开状态")
        print("💡 如需关闭浏览器，请手动在AdsPower中关闭")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ 系统错误: {e}")
        print("\n🔧 故障排除建议:")
        print("   1. 检查AdsPower是否正常运行")
        print("   2. 确认浏览器ID是否正确")
        print("   3. 检查网络连接")
        print("   4. 尝试重启AdsPower")
        print("   5. 检查文件路径是否正确")
        print("   6. 确认Excel文件格式正确")
        print("\n📞 如问题持续，请联系技术支持并提供完整错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
