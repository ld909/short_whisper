#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YouTube 自动发布系统 - 基于 generate_publish_excel.py

功能说明:
1. 读取 generate_publish_excel.py 生成的不同主题的 Excel 文件
2. 从对应主题路径找到 MP4 文件（基于 add_subtitles_to_videos.py 的输出路径）
3. 智能读取视频内容：
   - 标题：从 /Volumes/dhl/audio/[主题]/titles/[index].txt 读取
   - 描述：从 /Volumes/dhl/audio/[主题]/description/[index].txt 读取
   - 封面：从 /Volumes/dhl/audio/[主题]/cover_img_small/[index].png 读取
   - 自动从MP4文件名解析index（如 "123.mp4" -> "123"）
   - 如果文件不存在，使用主题相关的默认内容
4. 计算发布时间：基于最远发布时间 + 指定间隔小时
5. 自动发布视频到 YouTube（包含标题、描述、封面上传）
6. 更新 Excel 状态（is_published=1, publish_date=发布时间）

Tab管理功能:
- 启动时自动关闭所有现有tab，创建一个新的干净tab
- 第一个视频使用初始tab，后续每个视频都创建新tab进行上传
- 当tab数量达到设定上限时（默认7个），系统会等待指定时间（默认30分钟）
- 等待完成后，关闭所有tab（认为上传工作已完成），然后创建新tab继续工作
- 自动清理已关闭的无效tab，保持tab计数准确

大文件上传优化:
- 优先使用CDP (Chrome DevTools Protocol) 方法上传视频，绕过50MB文件大小限制
- 如果CDP方法失败，自动回退到标准Playwright方法
- 支持GB级别大视频文件的稳定上传

Excel 文件格式:
- 路径: publish_log/[主题].xlsx
- 列: mp4_name, if_published, publish_date

资源文件路径:
- 视频文件:
  * macOS: /Volumes/dhl/audio/[主题]/mp4_with_subtitles/[文件名]
  * Linux: /mnt/dhl/audio/[主题]/mp4_with_subtitles/[文件名]
- 标题文件:
  * macOS: /Volumes/dhl/audio/[主题]/titles/[index].txt
  * Linux: /mnt/dhl/audio/[主题]/titles/[index].txt
- 描述文件:
  * macOS: /Volumes/dhl/audio/[主题]/description/[index].txt
  * Linux: /mnt/dhl/audio/[主题]/description/[index].txt
- 封面文件:
  * macOS: /Volumes/dhl/audio/[主题]/cover_img_small/[index].png
  * Linux: /mnt/dhl/audio/[主题]/cover_img_small/[index].png

使用方法:
python auto_youtube_publish.py --topic scifi --interval 4  # 发布所有scifi视频
python auto_youtube_publish.py --topic scifi --interval 4 --max-count 2  # 限制发布2个
python auto_youtube_publish.py --topic scifi,thriller --interval 6 --dry-run
python auto_youtube_publish.py --all --interval 4 --max-tabs 5 --wait-minutes 45
python auto_youtube_publish.py --topic scifi --diagnose-covers  # 诊断封面目录

选项:
--topic: 指定主题 (scifi/thriller/romance/horror/fantasy)
--all: 处理所有主题
--interval: 发布间隔小时数 (默认4小时)
--max-count: 最大发布数量 (默认全部)
--dry-run: 试运行模式
--diagnose-covers: 诊断封面目录结构
--ads-id: AdsPower浏览器ID
--max-tabs: 最大tab数量 (默认7)
--wait-minutes: tab限制时等待分钟数 (默认30)
"""

import os
import sys
import time
import json
import random
import argparse
import platform
import urllib3
import re
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright


def countdown_timer(total_seconds, description="等待中"):
    """在终端显示倒计时"""
    print(f"\n⏰ {description}...")

    while total_seconds > 0:
        # 计算时、分、秒
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        # 格式化时间显示
        if hours > 0:
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            time_str = f"{minutes:02d}:{seconds:02d}"

        # 创建进度条
        if hours > 0:
            total_display = total_seconds // 60  # 按分钟显示进度
            remaining_display = (total_seconds % 3600) // 60 + (
                1 if total_seconds % 60 > 0 else 0
            )
        else:
            total_display = (total_seconds // 60) + (1 if total_seconds % 60 > 0 else 0)
            remaining_display = total_seconds // 60 + (
                1 if total_seconds % 60 > 0 else 0
            )

        if total_display > 0:
            progress = max(0, total_display - remaining_display) / total_display
            bar_length = 30
            filled_length = int(bar_length * progress)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            percentage = progress * 100
        else:
            bar = "█" * 30
            percentage = 100

        # 清除当前行并显示倒计时
        print(
            f"\r⏱️  剩余时间: {time_str} │{bar}│ {percentage:5.1f}%", end="", flush=True
        )

        time.sleep(1)
        total_seconds -= 1

    # 完成时的显示
    print(f"\r✅ {description}完成！" + " " * 50)
    print()  # 换行


# 支持的主题列表
SUPPORTED_TOPICS = ["scifi", "thriller", "romance", "horror", "fantasy"]

# YouTube Studio URLs - 按主题映射频道 (可以根据需要配置)
YOUTUBE_STUDIO_URLS = {
    # 各主题对应的频道URL
    "scifi": "https://studio.youtube.com/channel/UCDZT5uELAHTw2VhWwHISdZA",  # 科幻频道
    "thriller": "https://studio.youtube.com/channel/UCGT_hGqykWVkN8CGij2z4Vg",  # 惊悚频道
    "romance": None,  # 浪漫频道 (待配置)
    "horror": None,  # 恐怖频道 (待配置)
    "fantasy": "https://studio.youtube.com/channel/UCe4grZMmPMmnMcIoaTJc05w",  # 奇幻频道
    # 默认频道 (当主题频道未配置时使用)
    "default": "https://studio.youtube.com/channel/UCiCMH2ZdFy3vNqa6X0NVsoA",
}

# AdsPower 浏览器 ID 映射 - 按主题映射不同的浏览器账户
ADSPOWER_BROWSER_IDS = {
    "scifi": "k10i5y1s",  # 科幻主题使用新浏览器
    "thriller": "k10i5y1s",  # 惊悚主题使用新浏览器
    "fantasy": "k10i5y1s",  # 奇幻主题使用新浏览器
    "romance": "kq316tr",  # 浪漫主题使用旧浏览器
    "horror": "kq316tr",  # 恐怖主题使用旧浏览器
    # 默认浏览器 ID (当主题未配置时使用)
    "default": "kq316tr",
}


# 主题资源路径映射 - 用于获取标题、描述和封面
def get_adspower_browser_id_for_topics(topics):
    """根据主题列表获取适合的浏览器 ID"""
    if not topics:
        return ADSPOWER_BROWSER_IDS["default"]

    # 如果只有一个主题，使用该主题的浏览器 ID
    if len(topics) == 1:
        topic = topics[0]
        browser_id = ADSPOWER_BROWSER_IDS.get(topic, ADSPOWER_BROWSER_IDS["default"])
        print(f"🎯 主题 '{topic}' 使用浏览器 ID: {browser_id}")
        return browser_id

    # 多主题情况：检查是否都使用相同的浏览器 ID
    browser_ids = set()
    for topic in topics:
        browser_id = ADSPOWER_BROWSER_IDS.get(topic, ADSPOWER_BROWSER_IDS["default"])
        browser_ids.add(browser_id)

    if len(browser_ids) == 1:
        # 所有主题使用相同的浏览器 ID
        selected_id = browser_ids.pop()
        print(f"🎯 多主题 {topics} 都使用相同浏览器 ID: {selected_id}")
        return selected_id
    else:
        # 主题使用不同的浏览器 ID，使用默认的
        print(
            f"⚠️  多主题 {topics} 使用不同浏览器 ID，采用默认: {ADSPOWER_BROWSER_IDS['default']}"
        )
        print(f"💡 建议分别处理不同浏览器 ID 的主题")
        return ADSPOWER_BROWSER_IDS["default"]


def get_topic_resource_paths(topic: str):
    """根据主题和操作系统返回资源文件路径"""
    system = platform.system()

    if system == "Darwin":  # macOS
        base_path = f"/Volumes/dhl/audio/{topic}"
    else:  # Linux/Ubuntu
        base_path = f"/media/dhl/audio/{topic}"

    return {
        "titles_dir": f"{base_path}/titles",
        "descriptions_dir": f"{base_path}/description",
        "covers_dir": f"{base_path}/cover_img_small",
        # 添加备选封面目录
        "covers_dir_alt1": f"{base_path}/cover_img",
        "covers_dir_alt2": f"{base_path}/thumbnail",
        "covers_dir_alt3": f"{base_path}/covers",
    }


def get_video_paths(topic: str):
    """根据主题和操作系统返回视频文件路径"""
    system = platform.system()

    if system == "Darwin":  # macOS
        base_path = f"/Volumes/dhl/audio/{topic}"
    else:  # Linux/Ubuntu
        base_path = f"/media/dhl/audio/{topic}"

    return {
        "video_dir": f"{base_path}/mp4_with_subtitles",  # add_subtitles_to_videos.py 的输出目录
        "excel_file": f"publish_log/{topic}.xlsx",  # generate_publish_excel.py 的输出文件
    }


def diagnose_cover_directory_structure(topic: str):
    """诊断封面目录结构，帮助用户了解实际的文件布局"""
    print(f"\n🔍 诊断主题 '{topic}' 的封面目录结构:")
    print("=" * 60)

    resource_paths = get_topic_resource_paths(topic)

    # 检查所有可能的封面目录
    cover_dirs = [
        ("主目录", resource_paths["covers_dir"]),
        ("备选目录1", resource_paths["covers_dir_alt1"]),
        ("备选目录2", resource_paths["covers_dir_alt2"]),
        ("备选目录3", resource_paths["covers_dir_alt3"]),
    ]

    found_dirs = []

    for dir_name, dir_path in cover_dirs:
        print(f"\n📁 {dir_name}: {dir_path}")

        if os.path.exists(dir_path):
            print(f"   ✅ 目录存在")
            try:
                # 列出前10个非隐藏文件
                files = [f for f in os.listdir(dir_path) if not f.startswith(".")]
                if files:
                    print(f"   📄 文件数量: {len(files)}")
                    print(f"   📋 示例文件 (前10个):")
                    for i, file in enumerate(files[:10]):
                        file_path = os.path.join(dir_path, file)
                        try:
                            file_size = os.path.getsize(file_path)
                            print(f"      {i+1}. {file} ({file_size} bytes)")
                        except:
                            print(f"      {i+1}. {file} (无法获取大小)")

                    if len(files) > 10:
                        print(f"      ... 还有 {len(files) - 10} 个文件")

                    found_dirs.append((dir_name, dir_path, len(files)))
                else:
                    print(f"   ⚠️  目录为空")

            except Exception as e:
                print(f"   ❌ 无法列出文件: {e}")
        else:
            print(f"   ❌ 目录不存在")

    print(f"\n📊 总结:")
    if found_dirs:
        print(f"✅ 找到 {len(found_dirs)} 个有效的封面目录:")
        for dir_name, dir_path, file_count in found_dirs:
            print(f"   • {dir_name}: {file_count} 个文件")
    else:
        print(f"❌ 未找到任何有效的封面目录")

    print("=" * 60)


class YouTubeAutoPublisher:
    def __init__(
        self,
        topics,
        interval_hours=4,
        ads_id=None,
        studio_url=None,
        wait_minutes=30,
        max_tabs=7,
    ):
        self.topics = topics if isinstance(topics, list) else [topics]
        self.interval_hours = interval_hours

        # 智能选择浏览器 ID：优先使用用户指定 > 主题自动选择 > 默认
        if ads_id:
            self.ads_id = ads_id
            print(f"🎯 使用用户指定浏览器 ID: {self.ads_id}")
        else:
            self.ads_id = get_adspower_browser_id_for_topics(self.topics)

        self.max_tabs = max_tabs  # 最大tab数量

        # 智能选择频道URL：优先使用用户指定 > 主题专用频道 > 默认频道
        if studio_url:
            self.studio_url = studio_url
        else:
            # 如果只有一个主题且该主题有专用频道，使用专用频道
            if len(self.topics) == 1 and YOUTUBE_STUDIO_URLS.get(self.topics[0]):
                self.studio_url = YOUTUBE_STUDIO_URLS[self.topics[0]]
                print(f"🎯 使用主题 {self.topics[0]} 的专用频道")
            else:
                # 多主题或无专用频道时使用默认频道
                self.studio_url = YOUTUBE_STUDIO_URLS["default"]
                if len(self.topics) > 1:
                    print(f"🔀 多主题处理，使用默认频道")
                else:
                    print(f"⚠️  主题 {self.topics[0]} 暂无专用频道，使用默认频道")

        self.wait_minutes = wait_minutes
        self.http = None
        self.close_url = (
            f"http://127.0.0.1:50325/api/v1/browser/stop?user_id={self.ads_id}"
        )

        # tab管理相关
        self.current_tabs = []  # 当前打开的tab列表
        self.context = None  # 浏览器上下文

        print(f"🎬 YouTube 自动发布系统初始化")
        print(f"📋 处理主题: {', '.join(self.topics)}")
        print(f"⏱️  发布间隔: {self.interval_hours} 小时")
        print(f"🌐 YouTube Studio: {self.studio_url}")
        print(f"📑 最大tab数量: {self.max_tabs}")
        print(f"⏳ tab限制等待时间: {self.wait_minutes} 分钟")
        print(f"🖥️  操作系统: {platform.system()}")

        # 快速检查封面目录状态
        print(f"🖼️  封面目录快速检查:")
        for topic in self.topics:
            resource_paths = get_topic_resource_paths(topic)
            cover_dir = resource_paths["covers_dir"]
            if os.path.exists(cover_dir):
                try:
                    file_count = len(
                        [f for f in os.listdir(cover_dir) if not f.startswith(".")]
                    )
                    print(f"   ✅ {topic}: {file_count} 个封面文件")
                except:
                    print(f"   ⚠️  {topic}: 目录存在但无法读取")
            else:
                print(f"   ❌ {topic}: 主封面目录不存在")

    def get_pending_videos(self):
        """获取所有主题的待发布视频列表"""
        all_pending = []

        for topic in self.topics:
            print(f"\n🔍 扫描主题: {topic}")
            paths = get_video_paths(topic)
            excel_file = paths["excel_file"]
            video_dir = paths["video_dir"]

            # 检查Excel文件是否存在
            if not os.path.exists(excel_file):
                print(f"⚠️  Excel文件不存在: {excel_file}")
                print(f"💡 请先运行: python generate_publish_excel.py --topic {topic}")
                continue

            # 检查视频目录是否存在
            if not os.path.exists(video_dir):
                print(f"⚠️  视频目录不存在: {video_dir}")
                continue

            try:
                # 读取Excel文件
                df = pd.read_excel(excel_file)
                print(f"📊 Excel文件共 {len(df)} 条记录")

                # 过滤待发布视频 (if_published == 0)
                pending = df[df["if_published"] == 0]
                print(f"📝 待发布视频: {len(pending)} 个")

                # 检查视频文件是否存在
                valid_pending = []
                for _, row in pending.iterrows():
                    mp4_name = row["mp4_name"]
                    video_path = os.path.join(video_dir, mp4_name)

                    # 排除Mac系统产生的点文件
                    if mp4_name.startswith("."):
                        continue

                    if os.path.exists(video_path):
                        # 验证文件大小（大于1MB）
                        try:
                            file_size = os.path.getsize(video_path)
                            if file_size > 1024 * 1024:  # 1MB
                                video_info = {
                                    "topic": topic,
                                    "mp4_name": mp4_name,
                                    "video_path": video_path,
                                    "excel_file": excel_file,
                                    "if_published": row.get("if_published", 0),
                                    "publish_date": row.get("publish_date", ""),
                                }
                                valid_pending.append(video_info)
                                print(f"✅ 有效视频: {mp4_name}")
                            else:
                                print(f"⚠️  文件过小，跳过: {mp4_name}")
                        except Exception as e:
                            print(f"⚠️  文件检查失败: {mp4_name} - {e}")
                    else:
                        print(f"❌ 视频文件不存在: {video_path}")

                all_pending.extend(valid_pending)
                print(f"✅ 主题 {topic} 有效视频: {len(valid_pending)} 个")

            except Exception as e:
                print(f"❌ 处理主题 {topic} 时出错: {e}")
                continue

        print(f"\n📊 总计待发布视频: {len(all_pending)} 个")
        return all_pending

    def get_latest_publish_time_from_topics(self):
        """获取所有主题中的最远发布时间"""
        print("\n⏰ 计算所有主题的最远发布时间...")

        all_publish_times = []

        for topic in self.topics:
            paths = get_video_paths(topic)
            excel_file = paths["excel_file"]

            if not os.path.exists(excel_file):
                continue

            try:
                df = pd.read_excel(excel_file)

                # 过滤已发布的视频
                published = df[df["if_published"] == 1]

                if len(published) > 0:
                    # 获取发布时间列，排除空值
                    publish_times = published["publish_date"].dropna()

                    if len(publish_times) > 0:
                        # 转换为datetime
                        publish_times_dt = pd.to_datetime(publish_times)
                        all_publish_times.extend(publish_times_dt.tolist())
                        print(f"📅 主题 {topic}: {len(publish_times_dt)} 个已发布视频")

            except Exception as e:
                print(f"⚠️  读取主题 {topic} 发布时间失败: {e}")
                continue

        # 如果没有任何发布时间，使用当前时间
        if not all_publish_times:
            print("📝 未找到任何发布时间，使用当前时间作为基准")
            return datetime.now()

        # 找到最远的发布时间
        max_time = max(all_publish_times)
        current_time = datetime.now()

        print(f"📅 所有主题最远发布时间: {max_time}")
        print(f"🕐 当前系统时间: {current_time}")

        # 如果最远时间小于当前时间，使用当前时间
        if max_time < current_time:
            print("📝 最远发布时间 < 当前时间，使用当前时间作为基准")
            return current_time
        else:
            print("📝 最远发布时间 >= 当前时间，使用最远时间作为基准")
            return max_time

    def calculate_next_publish_time(self):
        """计算下一个发布时间"""
        print(f"\n{'='*50}")
        print("⏰ 开始计算下一个发布时间...")
        print(f"{'='*50}")

        # 获取最远发布时间
        latest_time = self.get_latest_publish_time_from_topics()
        current_time = datetime.now()

        # 计算下一个发布时间
        if latest_time < current_time:
            base_time = current_time
            print(f"🔄 使用当前时间作为基准: {base_time}")
        else:
            base_time = latest_time
            print(f"🔄 使用最远时间作为基准: {base_time}")

        next_time = base_time + timedelta(hours=self.interval_hours)
        print(f"➕ 计算过程: {base_time} + {self.interval_hours}小时 = {next_time}")

        hours_from_now = (next_time - current_time).total_seconds() / 3600
        print(f"📅 距离现在: {hours_from_now:.2f} 小时")

        if hours_from_now < 0:
            print("⚠️  警告: 计算出的发布时间在过去")
        elif hours_from_now < 1:
            print("⚠️  警告: 发布时间距离现在不到1小时")
        elif hours_from_now > 24 * 7:  # 一周
            print("⚠️  警告: 发布时间距离现在超过一周")
        else:
            print("✅ 发布时间安排合理")

        print(f"✅ 最终下一个发布时间: {next_time}")
        print(f"{'='*50}\n")
        return next_time

    def get_studio_url_for_topic(self, topic):
        """根据主题获取对应的YouTube Studio URL"""
        topic_url = YOUTUBE_STUDIO_URLS.get(topic)
        if topic_url:
            print(f"🎯 主题 {topic} 使用专用频道: {topic_url}")
            return topic_url
        else:
            print(
                f"⚠️  主题 {topic} 无专用频道，使用默认频道: {YOUTUBE_STUDIO_URLS['default']}"
            )
            return YOUTUBE_STUDIO_URLS["default"]

    def extract_index_from_filename(self, mp4_name):
        """从MP4文件名中提取index"""
        try:
            # 假设文件名格式为 [index].mp4 或者包含数字的格式
            base_name = mp4_name.replace(".mp4", "")

            # 尝试直接解析为数字（如果整个文件名就是数字）
            try:
                return str(int(base_name))
            except ValueError:
                pass

            # 尝试从文件名中提取数字
            numbers = re.findall(r"\d+", base_name)
            if numbers:
                # 取最后一个数字作为index
                return numbers[-1]

            # 如果找不到数字，使用完整的base_name
            return base_name

        except Exception as e:
            print(f"⚠️  解析文件名索引失败 {mp4_name}: {e}")
            return mp4_name.replace(".mp4", "")

    def get_video_content(self, video_info):
        """获取视频的标题、描述和封面"""
        mp4_name = video_info["mp4_name"]
        topic = video_info["topic"]
        video_path = video_info["video_path"]

        # 从文件名提取index
        index = self.extract_index_from_filename(mp4_name)
        print(f"📂 视频文件: {mp4_name}, 解析出的索引: {index}")

        # 获取主题资源路径
        resource_paths = get_topic_resource_paths(topic)

        # 初始化内容结构
        content = {
            "mp4_path": video_path,
            "title": "",
            "description": "",
            "thumbnail_path": None,
            "valid": True,
        }

        # 检查MP4文件是否存在
        if not os.path.exists(video_path):
            print(f"⚠️  MP4文件不存在: {video_path}")
            content["valid"] = False

        # 读取标题
        title_file = os.path.join(resource_paths["titles_dir"], f"{index}.txt")
        if os.path.exists(title_file):
            try:
                with open(title_file, "r", encoding="utf-8") as f:
                    content["title"] = f.read().strip()
                print(f"✅ 从文件读取标题: {title_file}")
            except Exception as e:
                print(f"⚠️  读取标题文件出错: {e}")
                content["title"] = self.get_fallback_title(topic, index)
        else:
            print(f"⚠️  标题文件不存在: {title_file}")
            content["title"] = self.get_fallback_title(topic, index)

        # 读取描述
        desc_file = os.path.join(resource_paths["descriptions_dir"], f"{index}.txt")
        if os.path.exists(desc_file):
            try:
                with open(desc_file, "r", encoding="utf-8") as f:
                    content["description"] = f.read().strip()
                print(f"✅ 从文件读取描述: {desc_file}")
            except Exception as e:
                print(f"⚠️  读取描述文件出错: {e}")
                content["description"] = self.get_fallback_description(topic)
        else:
            print(f"⚠️  描述文件不存在: {desc_file}")
            content["description"] = self.get_fallback_description(topic)

        # 读取封面 - 改进的多路径查找逻辑
        print(f"🔍 开始查找封面文件，索引: {index}")

        # 定义所有可能的封面目录和文件扩展名
        cover_dirs = [
            resource_paths["covers_dir"],  # 主目录
            resource_paths["covers_dir_alt1"],  # 备选目录1
            resource_paths["covers_dir_alt2"],  # 备选目录2
            resource_paths["covers_dir_alt3"],  # 备选目录3
        ]

        # 支持的文件扩展名
        extensions = [".png", ".jpg", ".jpeg", ".webp"]

        content["thumbnail_path"] = None

        # 在所有目录中查找封面文件
        for cover_dir in cover_dirs:
            print(f"📁 检查目录: {cover_dir}")
            if not os.path.exists(cover_dir):
                print(f"   ❌ 目录不存在")
                continue

            # 尝试所有扩展名
            for ext in extensions:
                cover_file = os.path.join(cover_dir, f"{index}{ext}")
                if os.path.exists(cover_file):
                    # 验证文件大小（大于1KB）
                    try:
                        file_size = os.path.getsize(cover_file)
                        if file_size > 1024:  # 1KB
                            content["thumbnail_path"] = cover_file
                            print(f"✅ 找到封面文件: {cover_file} ({file_size} bytes)")
                            break
                        else:
                            print(
                                f"   ⚠️  文件太小，跳过: {cover_file} ({file_size} bytes)"
                            )
                    except Exception as size_error:
                        print(f"   ⚠️  检查文件大小失败: {cover_file} - {size_error}")
                else:
                    print(f"   ❌ 文件不存在: {cover_file}")

            # 如果找到了封面文件，就跳出目录循环
            if content["thumbnail_path"]:
                break

        if not content["thumbnail_path"]:
            print(f"⚠️  所有目录中都未找到封面文件 (索引: {index})")

            # 显示目录诊断信息
            print(f"🔍 封面目录诊断:")
            for i, cover_dir in enumerate(cover_dirs):
                print(f"   目录 {i+1}: {cover_dir}")
                if os.path.exists(cover_dir):
                    try:
                        files = [
                            f for f in os.listdir(cover_dir) if not f.startswith(".")
                        ][
                            :5
                        ]  # 只显示前5个文件
                        print(f"     ✅ 存在，示例文件: {files}")
                    except Exception as e:
                        print(f"     ⚠️  无法列出文件: {e}")
                else:
                    print(f"     ❌ 不存在")

        # 验证内容
        if not content["title"]:
            content["title"] = self.get_fallback_title(topic, index)
        if not content["description"]:
            content["description"] = self.get_fallback_description(topic)

        print(f"📝 最终标题: {content['title']}")
        print(f"📝 最终描述长度: {len(content['description'])} 字符")
        print(f"🖼️  封面文件: {content['thumbnail_path'] or '无'}")

        return content

    def get_fallback_title(self, topic, index):
        """获取回退标题（当文件不存在时使用）"""
        topic_titles = {
            "scifi": f"Sci-Fi Story #{index} - Epic Science Fiction Adventure",
            "thriller": f"Thriller #{index} - Heart-Pounding Suspense",
            "romance": f"Romance #{index} - Beautiful Love Story",
            "horror": f"Horror #{index} - Spine-Chilling Terror",
            "fantasy": f"Fantasy #{index} - Magical Adventure",
        }
        return topic_titles.get(topic, f"{topic.title()} Story #{index}")

    def get_fallback_description(self, topic):
        """获取回退描述（当文件不存在时使用）"""
        topic_descriptions = {
            "scifi": "Immerse yourself in this captivating science fiction story filled with futuristic technology and extraordinary adventures.",
            "thriller": "Experience heart-pounding suspense in this thrilling story that will keep you on the edge of your seat.",
            "romance": "Discover a beautiful love story that will touch your heart and remind you of the power of true romance.",
            "horror": "Prepare for spine-chilling terror in this horror story that will haunt your dreams.",
            "fantasy": "Enter a magical world of fantasy filled with wonder, magic, and extraordinary adventures.",
        }
        return topic_descriptions.get(topic, f"Enjoy this amazing {topic} story!")

    def get_adspower_info(self):
        """连接AdsPower浏览器，带重试和详细错误提示"""
        try:
            import urllib3
        except ImportError:
            print("❌ 错误: 缺少 urllib3 模块，请安装: pip install urllib3")
            return None, None

        # 先检查 AdsPower 服务是否运行
        test_url = "http://127.0.0.1:50325/api/v1/status"
        open_url = f"http://127.0.0.1:50325/api/v1/browser/start?user_id={self.ads_id}"

        self.http = urllib3.PoolManager()

        print("🔍 检查 AdsPower 服务状态...")

        # 检查服务是否运行
        try:
            test_resp = self.http.request("GET", test_url, timeout=10)
            print("✅ AdsPower 服务已运行")
        except Exception as e:
            print("❌ AdsPower 服务未运行或无法连接")
            print("请确保:")
            print("  1. AdsPower 客户端已启动")
            print("  2. 本地API已启用 (设置 -> 本地API -> 启用)")
            print("  3. 端口 50325 未被占用")
            print("  4. 防火墙允许本地连接")
            print(f"详细错误: {e}")
            return None, None

        print(f"🚀 正在启动浏览器 (ID: {self.ads_id})...")

        # 尝试启动浏览器，最多重试3次
        max_retries = 3
        for attempt in range(max_retries):
            try:
                r = self.http.request("GET", open_url, timeout=30)

                if r.status != 200:
                    print(f"❌ 错误: API返回状态码 {r.status}")
                    if attempt < max_retries - 1:
                        print(f"🔄 第 {attempt + 1} 次尝试失败，{5} 秒后重试...")
                        time.sleep(5)
                        continue
                    else:
                        print("请确保AdsPower已启动并且本地API已启用")
                        return None, None

                # 解析响应
                try:
                    resp = json.loads(r.data.decode("utf-8"))
                except json.JSONDecodeError as e:
                    print(f"❌ 解析响应JSON失败: {e}")
                    if attempt < max_retries - 1:
                        print(f"🔄 第 {attempt + 1} 次尝试失败，{5} 秒后重试...")
                        time.sleep(5)
                        continue
                    else:
                        return None, None

                if resp["code"] != 0:
                    error_msg = resp.get("msg", "未知错误")
                    print(f"❌ AdsPower 错误: {error_msg}")

                    # 针对常见错误提供解决建议
                    if "not found" in error_msg.lower():
                        print(f"💡 浏览器ID '{self.ads_id}' 不存在，请检查:")
                        print("  1. 浏览器ID是否正确")
                        print("  2. 浏览器配置文件是否存在")
                        print("  3. 尝试在AdsPower客户端中手动启动该浏览器")
                    elif "running" in error_msg.lower():
                        print("💡 浏览器可能已在运行，请:")
                        print("  1. 在AdsPower中关闭该浏览器")
                        print("  2. 等待几秒后重试")
                    elif "license" in error_msg.lower():
                        print("💡 许可证问题，请检查AdsPower账户状态")

                    if attempt < max_retries - 1:
                        print(f"🔄 第 {attempt + 1} 次尝试失败，{10} 秒后重试...")
                        time.sleep(10)
                        continue
                    else:
                        return None, None

                # 成功获取浏览器信息
                ws_endpoint = resp["data"]["ws"]["puppeteer"]
                debug_port = resp["data"]["debug_port"]
                remote_debugging_url = f"http://localhost:{debug_port}"

                print(f"✅ 成功连接AdsPower浏览器!")
                print(f"   浏览器ID: {self.ads_id}")
                print(f"   调试端口: {debug_port}")
                print(f"   WebSocket: {ws_endpoint}")

                return ws_endpoint, remote_debugging_url

            except urllib3.exceptions.MaxRetryError as e:
                print(f"❌ 网络连接错误: {e}")
                if attempt < max_retries - 1:
                    print(f"🔄 第 {attempt + 1} 次尝试失败，{5} 秒后重试...")
                    time.sleep(5)
                    continue
                else:
                    print("请检查:")
                    print("  1. AdsPower是否正在运行")
                    print("  2. 网络连接是否正常")
                    print("  3. 是否有防火墙阻止连接")
                    return None, None

            except Exception as e:
                print(f"❌ 连接 AdsPower 时发生意外错误: {e}")
                if attempt < max_retries - 1:
                    print(f"🔄 第 {attempt + 1} 次尝试失败，{5} 秒后重试...")
                    time.sleep(5)
                    continue
                else:
                    print("请尝试:")
                    print("  1. 重启 AdsPower 客户端")
                    print("  2. 检查系统资源使用情况")
                    print("  3. 更换浏览器ID重试")
                    return None, None

        print(f"❌ 所有重试都失败了，无法连接到AdsPower浏览器 (ID: {self.ads_id})")
        return None, None

    def initialize_browser(self, max_retries=3):
        """初始化浏览器，关闭所有其他tab并创建一个新tab"""
        print("🔄 正在初始化浏览器...")

        for attempt in range(max_retries):
            print(f"📡 尝试连接浏览器 (第 {attempt + 1}/{max_retries} 次)...")

            # 连接AdsPower
            ws_endpoint, remote_debugging_url = self.get_adspower_info()
            if not ws_endpoint:
                print(f"❌ AdsPower连接失败 (第 {attempt + 1} 次)")
                if attempt < max_retries - 1:
                    countdown_timer(5, "等待重试")
                    continue
                else:
                    return None, None, None

            playwright = None
            try:
                print("🎭 创建Playwright实例...")
                playwright = sync_playwright().start()

                print(f"🌐 尝试连接到浏览器: {remote_debugging_url}")
                browser = playwright.chromium.connect_over_cdp(
                    remote_debugging_url, timeout=15000
                )
                print("✅ 成功连接到浏览器！")

                # 获取上下文
                if not browser.contexts:
                    context = browser.new_context()
                    print("📝 创建了新的浏览器上下文")
                else:
                    context = browser.contexts[0]
                    print("📝 使用现有的浏览器上下文")

                # 保存上下文引用
                self.context = context

                # 关闭所有现有tab
                print("🧹 正在关闭所有现有tab...")
                existing_pages = context.pages
                print(f"📊 发现 {len(existing_pages)} 个现有tab")

                for page in existing_pages:
                    try:
                        print(f"❌ 关闭tab: {page.url[:50]}...")
                        page.close()
                    except Exception as e:
                        print(f"⚠️  关闭tab时出错: {e}")

                print("✅ 已关闭所有现有tab")

                # 创建第一个新tab
                print("🆕 正在创建第一个新tab...")
                new_page = context.new_page()
                print("✅ 已创建第一个新tab")

                # 将新页面添加到tab列表
                self.current_tabs = [new_page]

                # 验证新页面是否正常工作
                new_page.goto("about:blank")
                print("✅ 新tab验证成功")
                print(f"📑 当前tab数量: {len(self.current_tabs)}")

                return playwright, browser, new_page

            except Exception as e:
                print(f"❌ 浏览器连接失败 (第 {attempt + 1} 次): {e}")

                if playwright:
                    try:
                        playwright.stop()
                        print("🧹 已清理Playwright实例")
                    except:
                        pass

                if attempt < max_retries - 1:
                    countdown_timer(10, "等待重试")
                    continue
                else:
                    print("❌ 所有重试都失败了")
                    return None, None, None

        return None, None, None

    def create_new_tab_for_upload(self):
        """为视频上传创建新tab"""
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

    def upload_video(
        self, video_content, page, dry_run=False, publish_time=None, topic=None
    ):
        """上传视频到YouTube（简化版）"""
        if dry_run:
            print(f"[试运行] 将要上传视频:")
            print(f"  文件: {video_content['mp4_path']}")
            print(f"  标题: {video_content['title']}")
            print(f"  描述: {video_content['description'][:100]}...")
            print(f"  计划发布时间: {publish_time}")
            if topic:
                print(f"  主题: {topic}")
                studio_url = self.get_studio_url_for_topic(topic)
                print(f"  频道URL: {studio_url}")
            return True

        if not video_content["valid"]:
            print("❌ 视频内容无效，跳过上传")
            return False

        try:
            # 根据主题动态选择频道URL
            if topic:
                studio_url = self.get_studio_url_for_topic(topic)
            else:
                studio_url = self.studio_url

            # 导航到YouTube Studio
            print(f"🌐 正在导航到YouTube Studio: {studio_url}")
            page.goto(studio_url)

            # 改进的页面加载等待逻辑
            print("⏳ 等待页面加载...")
            try:
                # 使用更短的超时时间避免无限等待
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                print("✅ DOM内容加载完成")

                # 额外等待一段时间让页面完全渲染
                page.wait_for_timeout(5000)
                print("✅ 页面渲染等待完成")

                # 尝试等待网络空闲，但设置较短超时
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                    print("✅ 网络活动已空闲")
                except Exception as network_timeout:
                    print(f"⚠️ 网络空闲等待超时，继续执行: {network_timeout}")

            except Exception as load_error:
                print(f"⚠️ 页面加载等待超时，继续尝试: {load_error}")

            # 检查当前页面状态
            current_url = page.url
            print(f"📍 当前页面URL: {current_url}")

            # 检查页面标题
            try:
                page_title = page.title()
                print(f"📄 页面标题: {page_title}")
            except Exception as title_error:
                print(f"⚠️ 无法获取页面标题: {title_error}")

            # 检查是否需要登录
            try:
                # 检查常见的登录指示器
                login_indicators = [
                    "Sign in",
                    "登录",
                    "accounts.google.com",
                    "Choose an account",
                    "选择账户",
                ]

                page_text = page.locator("body").inner_text()
                for indicator in login_indicators:
                    if indicator.lower() in page_text.lower():
                        print(f"⚠️ 检测到可能需要登录: 发现 '{indicator}'")
                        print("💡 请确保浏览器已登录YouTube账户")
                        break

            except Exception as login_check_error:
                print(f"⚠️ 登录状态检查失败: {login_check_error}")

            # 点击上传图标 - 使用多种选择器和重试机制
            print("📤 正在寻找并点击上传图标...")

            # 多种可能的上传图标选择器
            upload_selectors = [
                '[test-id="upload-icon-url"]',  # 原始选择器
                'button[aria-label*="Create"]',  # Create按钮
                'button[aria-label*="Upload"]',  # Upload按钮
                "#upload-icon",  # ID选择器
                ".upload-icon",  # Class选择器
                'ytcp-icon-button[icon="upload"]',  # YouTube组件选择器
                '[title*="Upload"]',  # Title属性
                '[aria-label*="Upload video"]',  # 更具体的aria-label
            ]

            upload_clicked = False
            for i, selector in enumerate(upload_selectors):
                try:
                    print(
                        f"🔍 尝试上传图标选择器 {i+1}/{len(upload_selectors)}: {selector}"
                    )

                    # 先检查元素是否存在
                    element_count = page.locator(selector).count()
                    if element_count > 0:
                        print(f"✅ 找到 {element_count} 个匹配元素")

                        # 等待元素可见和可点击
                        page.wait_for_selector(selector, state="visible", timeout=5000)
                        upload_icon = page.locator(selector).first

                        # 点击元素
                        upload_icon.click()
                        print(f"✅ 成功点击上传图标 (选择器: {selector})")
                        upload_clicked = True
                        break
                    else:
                        print(f"❌ 选择器未找到元素: {selector}")

                except Exception as selector_error:
                    print(f"❌ 选择器 {selector} 失败: {selector_error}")
                    continue

            if not upload_clicked:
                print("❌ 所有上传图标选择器都失败")
                print("🔍 正在分析页面内容...")

                # 打印页面的一些基本信息用于调试
                try:
                    # 查找所有可能相关的按钮
                    buttons = page.locator("button").all()
                    print(f"📊 页面中发现 {len(buttons)} 个按钮元素")

                    # 显示前几个按钮的信息
                    for i, button in enumerate(buttons[:10]):
                        try:
                            text = button.inner_text()
                            aria_label = button.get_attribute("aria-label")
                            title = button.get_attribute("title")
                            print(
                                f"   按钮 {i+1}: text='{text}' aria-label='{aria_label}' title='{title}'"
                            )
                        except:
                            print(f"   按钮 {i+1}: 无法获取属性")

                    if len(buttons) > 10:
                        print(f"   ... 还有 {len(buttons) - 10} 个按钮")

                except Exception as debug_error:
                    print(f"⚠️ 页面调试信息获取失败: {debug_error}")

                return False

            # 等待文件输入框出现
            print("⏳ 等待文件上传输入框...")
            page.wait_for_selector(
                'input[type="file"][name="Filedata"]', state="attached"
            )

            # 上传视频文件
            print(f"📁 正在上传视频: {video_content['mp4_path']}")

            # 检查文件大小，决定上传策略
            try:
                file_size = os.path.getsize(video_content["mp4_path"])
                file_size_mb = file_size / (1024 * 1024)
                print(f"📊 文件大小: {file_size_mb:.2f} MB")

                # 大于50MB的文件必须使用CDP方法
                use_cdp = file_size_mb > 50
                if use_cdp:
                    print("🔧 文件大于50MB，将使用CDP方法上传")
                else:
                    print("📁 文件小于50MB，尝试标准方法上传")

            except Exception as size_error:
                print(f"⚠️ 无法获取文件大小: {size_error}")
                print("🔧 默认使用CDP方法确保兼容性")
                use_cdp = True

            upload_success = False

            # 模拟人工操作的预处理步骤（减少反检测）
            print("🎭 执行人工行为模拟...")
            try:
                # 随机移动鼠标到不同位置
                page.mouse.move(random.randint(100, 500), random.randint(100, 300))
                page.wait_for_timeout(random.randint(500, 1000))

                # 模拟鼠标悬停在上传区域
                upload_area = page.locator('input[type="file"][name="Filedata"]').first
                if upload_area.count() > 0:
                    # 悬停在上传区域附近
                    box = upload_area.bounding_box()
                    if box:
                        page.mouse.move(
                            box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                        )
                        page.wait_for_timeout(random.randint(800, 1500))

                # 模拟键盘操作（如Tab键导航）
                page.keyboard.press("Tab")
                page.wait_for_timeout(random.randint(300, 600))
                page.keyboard.press("Tab")
                page.wait_for_timeout(random.randint(300, 600))

            except Exception as simulation_error:
                print(f"⚠️ 人工行为模拟失败: {simulation_error}")

            if not use_cdp:
                # 对于小文件，先尝试标准方法
                try:
                    print("🔄 尝试标准Playwright方法...")
                    file_input = page.locator('input[type="file"][name="Filedata"]')

                    if file_input.count() > 0:
                        # 人工操作延迟
                        delay = random.uniform(2.0, 4.0)
                        print(f"⏳ 人工操作延迟 {delay:.2f} 秒...")
                        time.sleep(delay)

                        file_input.set_input_files(video_content["mp4_path"])
                        print("✅ 标准方法上传完成")
                        upload_success = True

                        # 等待文件处理并检查错误
                        page.wait_for_timeout(5000)

                        try:
                            error_text = page.locator("body").inner_text()
                            if (
                                "you're all set" in error_text.lower()
                                or "already have access" in error_text.lower()
                            ):
                                print("⚠️ 检测到限制错误，切换到CDP方法...")
                                upload_success = False
                                use_cdp = True
                        except:
                            pass

                except Exception as standard_error:
                    print(f"❌ 标准方法失败: {standard_error}")
                    print("🔄 切换到CDP方法...")
                    use_cdp = True

            # 使用CDP方法上传（大文件必需，或标准方法失败时的回退）
            if use_cdp and not upload_success:
                print("🔧 使用优化的CDP方法上传...")

                # 多次尝试，增加成功率
                max_cdp_attempts = 3
                for attempt in range(max_cdp_attempts):
                    try:
                        print(f"🔄 CDP尝试 {attempt + 1}/{max_cdp_attempts}")

                        # 如果不是第一次尝试，刷新页面重置状态
                        if attempt > 0:
                            print("🔄 刷新页面重置状态...")
                            page.reload()
                            page.wait_for_load_state("domcontentloaded", timeout=15000)
                            page.wait_for_timeout(3000)

                            # 重新点击上传图标
                            upload_selectors = [
                                '[test-id="upload-icon-url"]',
                                'button[aria-label*="Create"]',
                                'button[aria-label*="Upload"]',
                                "#upload-icon",
                                ".upload-icon",
                            ]

                            for selector in upload_selectors:
                                if page.locator(selector).count() > 0:
                                    page.locator(selector).first.click()
                                    print("✅ 重新点击上传图标")
                                    break

                            page.wait_for_selector(
                                'input[type="file"][name="Filedata"]', state="attached"
                            )

                            # 刷新后的人工行为模拟
                            page.wait_for_timeout(random.randint(2000, 4000))

                        # 人工交互热身（重要：让页面认为这是真实用户）
                        print("🎭 执行用户交互热身...")

                        # 模拟鼠标在页面上的自然移动
                        for _ in range(3):
                            x = random.randint(200, 800)
                            y = random.randint(150, 400)
                            page.mouse.move(x, y)
                            page.wait_for_timeout(random.randint(500, 1200))

                        # 模拟点击页面空白区域
                        page.mouse.click(400, 200)
                        page.wait_for_timeout(random.randint(1000, 2000))

                        # 获取文件输入选择器
                        file_selector = 'input[type="file"][name="Filedata"]'

                        # 验证元素存在
                        file_input_handle = page.query_selector(file_selector)
                        if not file_input_handle:
                            print("❌ 文件输入元素未找到!")
                            if attempt == max_cdp_attempts - 1:
                                return False
                            continue

                        # 创建CDP会话
                        print("🔗 创建CDP会话...")
                        cdp_session = page.context.new_cdp_session(page)

                        # 启用DOM域
                        cdp_session.send("DOM.enable")

                        # 获取DOM文档
                        dom_snapshot = cdp_session.send(
                            "DOM.getDocument", {"depth": -1}
                        )

                        # 查找文件输入节点
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
                            if attempt == max_cdp_attempts - 1:
                                return False
                            continue

                        # 在设置文件前，模拟一些用户事件
                        print("🎭 触发用户事件...")
                        try:
                            # 触发focus事件
                            cdp_session.send(
                                "DOM.focus", {"nodeId": node_result["nodeId"]}
                            )
                            page.wait_for_timeout(500)

                            # 触发鼠标事件
                            page.mouse.click(400, 300)
                            page.wait_for_timeout(300)
                        except:
                            pass

                        # 关键延迟：让页面完全"相信"这是人工操作
                        critical_delay = random.uniform(3.0, 6.0)
                        print(f"⏳ 关键人工延迟 {critical_delay:.2f} 秒...")
                        time.sleep(critical_delay)

                        # 使用CDP设置文件
                        print("📁 设置文件...")
                        cdp_session.send(
                            "DOM.setFileInputFiles",
                            {
                                "nodeId": node_result["nodeId"],
                                "files": [video_content["mp4_path"]],
                            },
                        )

                        # 立即触发change事件确保页面响应
                        try:
                            cdp_session.send(
                                "Runtime.evaluate",
                                {
                                    "expression": f"document.querySelector('{file_selector}').dispatchEvent(new Event('change', {{bubbles: true}}))"
                                },
                            )
                        except:
                            pass

                        # 关闭CDP会话
                        cdp_session.detach()
                        print("✅ 视频文件上传完成（优化CDP方法）")
                        upload_success = True

                        # 等待处理并检查是否成功
                        page.wait_for_timeout(5000)

                        # 检查是否仍然出现错误
                        try:
                            error_text = page.locator("body").inner_text()
                            if (
                                "you're all set" in error_text.lower()
                                or "already have access" in error_text.lower()
                            ):
                                print(f"⚠️ 第{attempt + 1}次尝试仍有错误，准备重试...")
                                upload_success = False
                                if attempt < max_cdp_attempts - 1:
                                    # 增加重试间隔
                                    retry_delay = random.uniform(5.0, 10.0)
                                    print(f"⏳ 重试前等待 {retry_delay:.2f} 秒...")
                                    time.sleep(retry_delay)
                                    continue
                            else:
                                print("✅ CDP上传成功，未检测到错误")
                                break
                        except:
                            print("✅ CDP上传完成（无法验证状态，继续执行）")
                            break

                    except Exception as cdp_error:
                        print(f"❌ CDP尝试 {attempt + 1} 失败: {cdp_error}")
                        if attempt < max_cdp_attempts - 1:
                            retry_delay = random.uniform(3.0, 6.0)
                            print(f"⏳ CDP重试前等待 {retry_delay:.2f} 秒...")
                            time.sleep(retry_delay)
                            continue
                        else:
                            print("❌ 所有CDP尝试都失败")

            if not upload_success:
                print("❌ 文件上传失败")
                return False

            # 等待上传处理
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # 输入标题前随机等待
            delay = random.uniform(3.0, 5.0)
            print(f"⏳ 随机等待 {delay:.2f} 秒后开始输入标题...")
            time.sleep(delay)

            # 输入标题
            print("✏️  正在输入标题...")
            title_selector = 'div[id="textbox"][aria-label="Add a title that describes your video (type @ to mention a channel)"]'
            page.wait_for_selector(title_selector, state="visible")
            title_input = page.locator(title_selector)
            title_input.click()
            title_input.press("Control+a")
            title_input.fill(video_content["title"])
            print(f"✅ 已输入标题: {video_content['title']}")

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

            # 简化的封面上传逻辑
            if video_content.get("thumbnail_path") and os.path.exists(
                video_content["thumbnail_path"]
            ):
                print(f"📷 正在上传封面: {video_content['thumbnail_path']}")

                try:
                    # 等待封面上传区域加载
                    print("⏰ 等待封面上传区域加载...")
                    page.wait_for_timeout(3000)

                    # 基于实际DOM结构的精确选择器
                    thumbnail_selectors = [
                        'ytcp-thumbnail-uploader input#file-loader[type="file"]',  # 最精确的选择器
                        'input#file-loader[type="file"][accept="image/jpeg,image/png"]',  # 带accept属性
                        'input#file-loader[type="file"]',  # 基础ID选择器
                        '.style-scope.ytcp-thumbnail-uploader input[type="file"]',  # 基于class和容器
                        'input[type="file"][accept="image/jpeg,image/png"]',  # 基于accept属性
                    ]

                    # 查找封面输入框
                    active_selector = None
                    for selector in thumbnail_selectors:
                        try:
                            print(f"🔍 尝试选择器: {selector}")
                            element = page.query_selector(selector)
                            if element:
                                print(f"✅ 找到封面输入框: {selector}")
                                active_selector = selector
                                break
                            else:
                                print(f"❌ 选择器未找到元素: {selector}")
                        except Exception as e:
                            print(f"⚠️ 选择器出错 {selector}: {e}")
                            continue

                    if not active_selector:
                        print("⚠️ 未找到封面输入框，尝试点击上传按钮激活")
                        # 尝试点击上传按钮来激活文件选择
                        try:
                            upload_button = page.query_selector(
                                'button#select-button[aria-label="Upload file"]'
                            )
                            if upload_button:
                                print("✅ 找到上传按钮，点击激活")
                                upload_button.click()
                                page.wait_for_timeout(2000)
                                # 重新尝试查找input
                                for selector in thumbnail_selectors:
                                    element = page.query_selector(selector)
                                    if element:
                                        print(f"✅ 点击后找到封面输入框: {selector}")
                                        active_selector = selector
                                        break
                            if not active_selector:
                                print("❌ 点击上传按钮后仍未找到输入框")
                        except Exception as button_error:
                            print(f"❌ 点击上传按钮失败: {button_error}")

                    if not active_selector:
                        print("⚠️ 所有方法都无法找到封面输入框，跳过封面上传")
                    else:
                        # 尝试多种上传方法
                        upload_success = False

                        # 方法1: CDP方法（推荐用于隐藏元素）
                        try:
                            print("🔗 方法1: 使用CDP方法上传封面...")
                            cdp_session = page.context.new_cdp_session(page)

                            # 启用DOM
                            cdp_session.send("DOM.enable")

                            # 获取文档
                            doc = cdp_session.send("DOM.getDocument", {"depth": -1})
                            print(f"✅ 获取到DOM文档: {doc['root']['nodeId']}")

                            # 查找节点
                            node_result = cdp_session.send(
                                "DOM.querySelector",
                                {
                                    "nodeId": doc["root"]["nodeId"],
                                    "selector": active_selector,
                                },
                            )

                            if node_result.get("nodeId"):
                                print(f"✅ 找到节点ID: {node_result['nodeId']}")

                                # 设置文件
                                cdp_session.send(
                                    "DOM.setFileInputFiles",
                                    {
                                        "nodeId": node_result["nodeId"],
                                        "files": [video_content["thumbnail_path"]],
                                    },
                                )

                                cdp_session.detach()
                                print("✅ 封面上传完成（CDP方法）")
                                upload_success = True
                            else:
                                cdp_session.detach()
                                print("❌ CDP方法：未找到对应节点")

                        except Exception as cdp_error:
                            print(f"❌ CDP方法失败: {cdp_error}")
                            try:
                                cdp_session.detach()
                            except:
                                pass

                        # 方法2: 标准Playwright方法
                        if not upload_success:
                            try:
                                print("🔄 方法2: 使用标准Playwright方法...")
                                thumbnail_input = page.locator(active_selector)

                                # 检查元素是否存在
                                if thumbnail_input.count() > 0:
                                    print("✅ 找到input元素，开始上传...")
                                    thumbnail_input.set_input_files(
                                        video_content["thumbnail_path"]
                                    )
                                    print("✅ 封面上传完成（标准方法）")
                                    upload_success = True
                                else:
                                    print("❌ 标准方法：元素不存在")

                            except Exception as standard_error:
                                print(f"❌ 标准方法失败: {standard_error}")

                        # 方法3: 使用page.set_input_files直接方法
                        if not upload_success:
                            try:
                                print("🔄 方法3: 使用直接文件设置方法...")

                                # 验证文件存在
                                if os.path.exists(video_content["thumbnail_path"]):
                                    print(
                                        f"✅ 文件存在: {video_content['thumbnail_path']}"
                                    )

                                    # 使用page.set_input_files方法（可能更可靠）
                                    page.set_input_files(
                                        active_selector, video_content["thumbnail_path"]
                                    )
                                    print("✅ 封面上传完成（直接方法）")
                                    upload_success = True
                                else:
                                    print(
                                        f"❌ 文件不存在: {video_content['thumbnail_path']}"
                                    )

                            except Exception as direct_error:
                                print(f"❌ 直接方法失败: {direct_error}")

                        if upload_success:
                            print("🎉 封面上传成功！")
                        else:
                            print("❌ 所有上传方法都失败，跳过封面上传")

                        # 等待上传处理
                        print("⏰ 等待封面处理完成...")
                        page.wait_for_timeout(5000)

                except Exception as thumbnail_error:
                    print(f"❌ 封面上传过程出错: {thumbnail_error}")
                    print("⚠️ 跳过封面上传，继续处理视频发布")

            else:
                print("⚠️ 跳过封面上传（封面文件不存在）")

            # 等待一段时间后继续
            time.sleep(2)

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

            # 设置发布时间
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

                # 等待发布完成
                countdown_timer(5, "等待发布操作完成")

                # 改进的发布状态验证 - 更宽松的判断标准
                print("🔍 验证发布状态...")
                countdown_timer(3, "等待页面状态更新")

                try:
                    current_url = page.url
                    print(f"📍 当前页面URL: {current_url}")

                    # 方法1: 检查URL是否已经跳转离开上传页面（关键指标）
                    if "upload" not in current_url.lower():
                        print("✅ 已跳转离开上传页面，发布成功的强烈指示")
                        print("✅ 发布配置完成且验证成功")
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
                        "Failed to schedule",
                        "Scheduling failed",
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
                        print("❌ 发布失败")
                        return False

                    # 方法3: 检查是否有成功指示（不作为必需条件）
                    success_indicators = [
                        "scheduled",
                        "video scheduled",
                        "upload complete",
                        "processing",
                        "will be published",
                        "publish at",
                    ]

                    found_success = [
                        indicator
                        for indicator in success_indicators
                        if indicator in page_text
                    ]
                    if found_success:
                        print(f"✅ 发现成功指示: {found_success}")
                        print("✅ 发布配置完成且验证成功")
                        return True

                    # 方法4: 最后的宽松判断 - 如果没有错误信息，就认为成功
                    print("⚠️ 未发现明确的成功或错误指示")
                    print("📝 由于没有发现错误信息，按照宽松标准判断为成功")
                    print("✅ 发布配置完成（宽松验证通过）")
                    return True

                except Exception as verify_error:
                    print(f"❌ 发布验证时出错: {verify_error}")
                    print("📝 验证过程出错，但按照宽松标准判断为成功")
                    print("✅ 发布配置完成（异常后默认成功）")
                    return True

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

    def update_publish_status(self, video_info, publish_time):
        """更新Excel中的发布状态"""
        excel_file = video_info["excel_file"]
        mp4_name = video_info["mp4_name"]
        topic = video_info["topic"]

        print(f"📝 开始更新发布状态: {topic}/{mp4_name}")
        print(f"🕐 发布时间: {publish_time}")

        try:
            # 读取当前数据
            if not os.path.exists(excel_file):
                print(f"❌ Excel文件不存在: {excel_file}")
                return False

            df = pd.read_excel(excel_file)
            print(f"✅ 成功读取Excel，共 {len(df)} 条记录")

            # 查找视频记录
            mask = df["mp4_name"] == mp4_name
            if not mask.any():
                print(f"❌ 在Excel中未找到视频记录: {mp4_name}")
                return False

            # 显示更新前的状态
            matching_rows = df[mask]
            print(f"📊 找到 {len(matching_rows)} 条匹配记录")
            for idx, row in matching_rows.iterrows():
                print(f"   更新前状态:")
                print(f"     mp4_name: {row['mp4_name']}")
                print(f"     if_published: {row.get('if_published', 'N/A')}")
                print(f"     publish_date: {row.get('publish_date', 'N/A')}")

            # 执行更新
            df.loc[mask, "if_published"] = 1
            df.loc[mask, "publish_date"] = publish_time.strftime("%Y-%m-%d %H:%M:%S")

            # 保存更新后的数据
            df.to_excel(excel_file, index=False)
            print(f"✅ Excel文件保存成功")

            # 验证保存结果
            verify_df = pd.read_excel(excel_file)
            verify_mask = verify_df["mp4_name"] == mp4_name
            if verify_mask.any():
                verify_row = verify_df[verify_mask].iloc[0]
                saved_status = verify_row["if_published"]
                saved_time = verify_row["publish_date"]
                print(f"✅ 验证成功:")
                print(f"   保存的发布状态: {saved_status}")
                print(f"   保存的发布时间: {saved_time}")
                return True
            else:
                print(f"❌ 验证时未找到记录")
                return False

        except Exception as e:
            print(f"❌ 更新发布状态时出错: {e}")
            return False

    def run(self, max_count=None, dry_run=False):
        """运行自动发布系统"""
        print(f"\n{'='*60}")
        print(f"🚀 YouTube 自动发布系统启动")
        print(f"{'='*60}")
        print(f"📋 处理主题: {', '.join(self.topics)}")
        print(f"⏱️  发布间隔: {self.interval_hours} 小时")
        print(f"📊 最大发布数量: {'全部' if max_count is None else max_count}")
        print(f"🧪 试运行模式: {dry_run}")
        print(f"📑 最大tab数量: {self.max_tabs}")
        print(f"⏳ tab限制等待时间: {self.wait_minutes} 分钟")

        # 获取待发布视频列表
        pending_videos = self.get_pending_videos()
        if not pending_videos:
            print("❌ 没有待发布的视频")
            return

        # 限制发布数量
        if max_count is None:
            videos_to_publish = pending_videos  # 发布所有视频
            print(f"\n📊 将要处理所有 {len(videos_to_publish)} 个视频")
        else:
            videos_to_publish = pending_videos[:max_count]
            print(
                f"\n📊 将要处理 {len(videos_to_publish)} 个视频 (限制数量: {max_count})"
            )

        # 显示视频列表
        for i, video in enumerate(videos_to_publish, 1):
            print(f"   {i}. {video['topic']}/{video['mp4_name']}")

        # 初始化浏览器（只在非试运行模式下执行）
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
            # 处理每个视频
            for i, video_info in enumerate(videos_to_publish, 1):
                print(f"\n{'-'*50}")
                print(
                    f"📹 处理视频 {i}/{len(videos_to_publish)}: {video_info['topic']}/{video_info['mp4_name']}"
                )
                print(f"{'-'*50}")

                # 获取视频内容
                video_content = self.get_video_content(video_info)

                # 计算发布时间（每个视频都重新计算，确保获取最新数据）
                publish_time = self.calculate_next_publish_time()
                print(f"📅 计划发布时间: {publish_time}")

                # 在非试运行模式下管理tab
                upload_page = None
                if not dry_run:
                    # 清理已关闭的tab
                    self.cleanup_closed_tabs()

                    # 检查是否需要等待（达到tab限制）
                    wait_result = self.check_and_wait_for_tab_limit()

                    # 为当前视频创建新tab或使用第一个tab
                    if wait_result:
                        # 如果等待限制并返回了新tab，使用这个新tab
                        upload_page = wait_result
                        print("📑 使用等待后创建的新tab进行上传")
                    elif i == 1:
                        # 第一个视频使用初始tab
                        upload_page = initial_page
                        print("📑 使用初始tab进行上传")
                    else:
                        # 后续视频创建新tab
                        upload_page = self.create_new_tab_for_upload()
                        if not upload_page:
                            print("❌ 无法创建新tab，跳过当前视频")
                            continue

                # 上传视频
                print(f"🚀 开始上传第 {i} 个视频...")
                try:
                    success = self.upload_video(
                        video_content,
                        upload_page,
                        dry_run,
                        publish_time,
                        video_info["topic"],
                    )
                except Exception as upload_error:
                    print(f"❌ 上传视频时发生异常: {upload_error}")
                    success = False

                # 处理上传结果
                if success:
                    print(f"🎉 视频 {video_info['mp4_name']} 上传/安排发布成功！")

                    if not dry_run:
                        # 更新Excel状态
                        print(f"📝 开始更新Excel状态...")
                        update_success = self.update_publish_status(
                            video_info, publish_time
                        )

                        if update_success:
                            print(f"✅✅ 完整成功: 视频发布成功且Excel已更新")
                        else:
                            print(f"❌⚠️ 部分成功: 视频发布成功，但Excel更新失败")
                    else:
                        print(f"✅ [试运行] 视频处理完成")
                else:
                    print(f"❌ 视频 {video_info['mp4_name']} 发布失败")

                # 显示当前tab状态
                if not dry_run:
                    print(f"📑 当前tab状态: {len(self.current_tabs)}/{self.max_tabs}")

                # 如果不是最后一个视频，等待一段时间
                if i < len(videos_to_publish):
                    wait_time = 20
                    countdown_timer(wait_time, f"视频间隔等待 {wait_time} 秒")

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
                    print("💡 浏览器将保持打开状态，方便检查发布结果")
                    print(f"📑 最终tab数量: {len(self.current_tabs)}")
                except Exception as cleanup_error:
                    print(f"⚠️ 清理资源时出错: {cleanup_error}")

        print(f"\n{'='*60}")
        print(f"🎉 发布任务完成")
        print(f"📊 总计处理了 {len(videos_to_publish)} 个视频")
        print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="YouTube 自动发布系统 - 基于 generate_publish_excel.py"
    )

    # 主题参数
    parser.add_argument(
        "--topic",
        help=f"指定要处理的主题，支持多个主题用逗号分隔。支持的主题: {', '.join(SUPPORTED_TOPICS)}",
    )
    parser.add_argument("--all", action="store_true", help="处理所有支持的主题")

    # 发布参数
    parser.add_argument(
        "--interval", type=int, default=4, help="视频发布间隔小时数 (默认: 4)"
    )
    parser.add_argument(
        "--max-count", type=int, default=None, help="最大发布数量 (默认: 全部)"
    )

    # 浏览器参数
    parser.add_argument("--ads-id", help="AdsPower浏览器ID (默认: 根据主题自动选择)")
    parser.add_argument("--studio-url", help="YouTube Studio频道URL")
    parser.add_argument(
        "--max-tabs",
        type=int,
        default=7,
        help="最大tab数量，达到此数量时将等待 (默认: 7)",
    )
    parser.add_argument(
        "--wait-minutes",
        type=int,
        default=30,
        help="当tab达到限制时的等待时间（分钟） (默认: 30)",
    )

    # 行为参数
    parser.add_argument("--dry-run", action="store_true", help="试运行模式，不实际发布")
    parser.add_argument(
        "--diagnose-covers", action="store_true", help="诊断封面目录结构"
    )

    args = parser.parse_args()

    print("🎬 YouTube 自动发布系统")
    print("=" * 60)
    print(f"🖥️  操作系统: {platform.system()}")

    # 显示浏览器 ID 映射信息
    print(f"🌐 浏览器 ID 映射:")
    for topic, browser_id in ADSPOWER_BROWSER_IDS.items():
        if topic != "default":
            print(f"   {topic}: {browser_id}")
    print(f"   默认: {ADSPOWER_BROWSER_IDS['default']}")

    # 确定要处理的主题
    topics_to_process = []

    if args.all:
        topics_to_process = SUPPORTED_TOPICS.copy()
        print(f"🎯 处理所有主题: {', '.join(topics_to_process)}")
    elif args.topic:
        topics_input = args.topic.split(",")
        for topic in topics_input:
            topic = topic.strip().lower()
            if topic in SUPPORTED_TOPICS:
                topics_to_process.append(topic)
            else:
                print(f"⚠️  不支持的主题: {topic}")

        if not topics_to_process:
            print(f"❌ 没有有效的主题可处理")
            print(f"   支持的主题: {', '.join(SUPPORTED_TOPICS)}")
            return

        print(f"🎯 处理指定主题: {', '.join(topics_to_process)}")
    else:
        print(f"❌ 请指定要处理的主题或使用 --all 处理所有主题")
        print(f"   使用 --help 查看使用说明")
        return

    # 如果是诊断模式，运行诊断并退出
    if args.diagnose_covers:
        print("🔍 封面目录诊断模式")
        for topic in topics_to_process:
            diagnose_cover_directory_structure(topic)
        return

    # 检查依赖文件
    missing_files = []
    for topic in topics_to_process:
        paths = get_video_paths(topic)
        excel_file = paths["excel_file"]
        if not os.path.exists(excel_file):
            missing_files.append(f"{topic}: {excel_file}")

    if missing_files:
        print(f"❌ 缺少必需的Excel文件:")
        for missing in missing_files:
            print(f"   {missing}")
        print(f"💡 请先运行: python generate_publish_excel.py --topic [主题名]")
        return

    # 创建发布系统实例
    publisher = YouTubeAutoPublisher(
        topics=topics_to_process,
        interval_hours=args.interval,
        ads_id=args.ads_id,
        studio_url=args.studio_url,
        wait_minutes=args.wait_minutes,
        max_tabs=args.max_tabs,
    )

    # 运行发布系统
    try:
        publisher.run(max_count=args.max_count, dry_run=args.dry_run)
        print("\n🎉 程序正常结束")

    except KeyboardInterrupt:
        print("\n\n🛑 用户中断操作")
        print("📝 提示：浏览器连接已断开，AdsPower浏览器实例仍保持打开状态")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ 系统错误: {e}")
        print("\n🔧 故障排除建议:")
        print("   1. 检查AdsPower是否正常运行")
        print("   2. 确认浏览器ID是否正确")
        print("   3. 检查网络连接")
        print("   4. 确认Excel文件格式正确")
        print("   5. 检查视频文件路径是否正确")
        sys.exit(1)


if __name__ == "__main__":
    main()
