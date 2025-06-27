#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YouTube视频自动发布工具

功能说明:
此脚本用于自动发布YouTube视频，使用AdsPower浏览器和Playwright进行自动化操作。
脚本会自动从相应的多语言内容生成脚本的输出目录中读取真实的标题、描述和封面。

依赖的输出目录:
- 简化标题: [媒体路径]/title_shorten_multi_lang/[频道名称]/[语言代码]/[视频名].txt
- 视频描述: [媒体路径]/multi_lang_desc/[频道名称]/[语言代码]/[视频名].txt
- 封面图片: [媒体路径]/thumbnail/[频道名称]/[语言代码]/[视频名].png
- 视频文件: [媒体路径]/mp4_with_audio/[频道名称]/[语言代码]/[视频名].mp4

使用方法:
1. 基本使用 (使用默认参数): python auto_publish.py
2. 指定频道: python auto_publish.py -c 频道名称
3. 指定视频: python auto_publish.py -v 视频名称
4. 指定语言: python auto_publish.py -l ko  # 韩语
5. 完整指定: python auto_publish.py -c huoshan -v 1 -l en --ads_id kq316tr

注意:
- 需要先启动AdsPower并确保本地API已启用
- 需要安装playwright: pip install playwright
- 需要先运行相关的多语言内容生成脚本，确保所有必需的文件都已生成
- 支持的语言代码：en(英语), ko(韩语)
"""

import requests
import time
import json
import sys
import urllib3
import os
import platform
import argparse
from playwright.sync_api import sync_playwright


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    if platform.system() == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


def get_shortened_title(channel, video_name, language_code):
    """从shorten_titles_multi_lang.py的输出中获取简化标题"""
    media_path = get_base_media_path()
    title_file = os.path.join(
        media_path,
        "title_shorten_multi_lang",
        channel,
        language_code,
        f"{video_name}.txt",
    )

    if not os.path.exists(title_file):
        print(f"警告: 简化标题文件不存在: {title_file}")
        return None

    try:
        with open(title_file, "r", encoding="utf-8") as f:
            title = f.read().strip()
            if title:
                return title
            else:
                print(f"警告: 简化标题文件为空: {title_file}")
                return None
    except Exception as e:
        print(f"读取简化标题文件时出错: {e}")
        return None


def get_description(channel, video_name, language_code):
    """从generate_multi_lang_descriptions.py的输出中获取描述"""
    media_path = get_base_media_path()
    desc_file = os.path.join(
        media_path, "multi_lang_desc", channel, language_code, f"{video_name}.txt"
    )

    if not os.path.exists(desc_file):
        print(f"警告: 描述文件不存在: {desc_file}")
        return None

    try:
        with open(desc_file, "r", encoding="utf-8") as f:
            description = f.read().strip()
            if description:
                return description
            else:
                print(f"警告: 描述文件为空: {desc_file}")
                return None
    except Exception as e:
        print(f"读取描述文件时出错: {e}")
        return None


def get_thumbnail_path(channel, video_name, language_code):
    """从generate_multilingual_thumbnails.py的输出中获取封面路径"""
    media_path = get_base_media_path()
    thumbnail_file = os.path.join(
        media_path, "thumbnail", channel, language_code, f"{video_name}.png"
    )

    if not os.path.exists(thumbnail_file):
        print(f"警告: 封面文件不存在: {thumbnail_file}")
        return None

    return thumbnail_file


def get_video_path(channel, video_name, language_code):
    """获取视频文件路径"""
    media_path = get_base_media_path()
    video_file = os.path.join(
        media_path, "mp4_with_audio", channel, language_code, f"{video_name}.mp4"
    )

    if not os.path.exists(video_file):
        print(f"错误: 视频文件不存在: {video_file}")
        return None

    return video_file


def get_adspower_info(ads_id):
    open_url = f"http://127.0.0.1:50325/api/v1/browser/start?user_id={ads_id}"

    # 使用urllib3替代requests，避免可能的连接问题
    http = urllib3.PoolManager()

    print("正在连接AdsPower...")
    r = http.request("GET", open_url)

    if r.status != 200:
        print(f"错误: API返回状态码 {r.status}")
        print("请确保AdsPower已启动并且本地API已启用")
        return None, None, http

    # 解析JSON响应
    resp = json.loads(r.data.decode("utf-8"))

    if resp["code"] != 0:
        print(f"错误: {resp['msg']}")
        print("请检查ads_id是否正确")
        return None, None, http

    # 获取WebSocket地址
    ws_endpoint = resp["data"]["ws"]["puppeteer"]
    debug_port = resp["data"]["debug_port"]
    remote_debugging_url = f"http://localhost:{debug_port}"

    print(f"成功连接AdsPower，WebSocket地址: {ws_endpoint}")
    print(f"远程调试URL: {remote_debugging_url}")

    return ws_endpoint, remote_debugging_url, http


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="自动发布YouTube视频")
    parser.add_argument(
        "-c", "--channel", default="huoshan", help="频道名称 (默认: huoshan)"
    )
    parser.add_argument(
        "-v", "--video", default="1", help="视频名称，不含扩展名 (默认: 1)"
    )
    parser.add_argument(
        "-l",
        "--language",
        default="en",
        choices=["en", "ko"],
        help="语言代码: en(英语), ko(韩语) (默认: en)",
    )
    parser.add_argument(
        "--ads_id", default="kq316tr", help="AdsPower浏览器ID (默认: kq316tr)"
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 启动AdsPower浏览器
    ads_id = args.ads_id
    close_url = f"http://127.0.0.1:50325/api/v1/browser/stop?user_id={ads_id}"

    # 配置要上传的视频信息
    channel = args.channel  # 频道名称
    video_name = args.video  # 视频名称（不含扩展名）
    language_code = args.language  # 语言代码：en(英语), ko(韩语)

    try:
        # 获取真实的标题、描述和封面
        title = get_shortened_title(channel, video_name, language_code)
        description = get_description(channel, video_name, language_code)
        thumbnail_path = get_thumbnail_path(channel, video_name, language_code)
        video_path = get_video_path(channel, video_name, language_code)

        # 检查所有必需的文件是否存在
        if not title:
            print("错误: 无法获取视频标题")
            return
        if not description:
            print("错误: 无法获取视频描述")
            return
        if not thumbnail_path:
            print("错误: 无法获取封面文件")
            return
        if not video_path:
            print("错误: 无法获取视频文件")
            return

        print(f"准备上传视频:")
        print(f"  频道: {channel}")
        print(f"  视频: {video_name}")
        print(f"  语言: {language_code}")
        print(f"  标题: {title}")
        print(f"  描述: {description}")
        print(f"  视频文件: {video_path}")
        print(f"  封面文件: {thumbnail_path}")

        # 获取WebDriver
        ws_endpoint, remote_debugging_url, http = get_adspower_info(ads_id)

        if not ws_endpoint:
            return

        # 使用Playwright连接浏览器
        print("正在使用Playwright连接浏览器...")
        with sync_playwright() as p:
            # 可以使用WebSocket地址或远程调试URL
            # browser = p.chromium.connect_over_cdp(ws_endpoint)
            browser = p.chromium.connect_over_cdp(remote_debugging_url)

            print("成功连接到浏览器！")

            # 获取已有上下文或创建新上下文
            if not browser.contexts:
                print("没有找到上下文。浏览器可能没有打开默认页面。")
                context = browser.new_context()
            else:
                context = browser.contexts[0]  # 获取已存在的上下文

            # 创建新标签页并关闭其他标签页
            print("正在创建新标签页...")
            new_page = context.new_page()
            print("新标签页已创建")

            # 关闭所有其他标签页
            print("正在关闭其他标签页...")
            for i, page in enumerate(context.pages):
                if page != new_page:
                    print(f"关闭标签页 {i+1}")
                    page.close()

            # 使用新创建的标签页
            page = new_page
            print("已创建新标签页并关闭其他标签页")

            # 导航到YouTube
            print("正在打开YouTube...")
            page.goto("https://www.youtube.com")
            print(f"页面标题: {page.title()}")
            print("已成功打开YouTube")

            # 导航到指定的YouTube Studio频道
            print("正在导航到YouTube Studio频道...")
            studio_url = "https://studio.youtube.com/channel/UCiCMH2ZdFy3vNqa6X0NVsoA"
            page.goto(studio_url)
            print(f"页面标题: {page.title()}")
            print("已成功导航到YouTube Studio频道")

            # 等待页面加载完成
            print("等待页面加载完成...")
            page.wait_for_load_state("networkidle")

            # 点击上传图标
            print("正在点击上传图标...")
            upload_icon = page.locator('[test-id="upload-icon-url"]')
            upload_icon.click()
            print("已点击上传图标")

            # 等待文件输入元素出现
            print("等待文件上传输入框出现...")
            page.wait_for_selector(
                'input[type="file"][name="Filedata"]', state="attached"
            )

            print(f"正在上传视频文件: {video_path}")
            print(f"正在上传封面文件: {thumbnail_path}")

            # 上传视频文件
            print(f"正在上传视频文件 {video_path}...")
            file_input = page.locator('input[type="file"][name="Filedata"]')
            file_input.set_input_files(video_path)
            print("视频文件已上传")

            # 等待上传处理
            print("等待上传处理...")
            page.wait_for_load_state("networkidle")

            # 等待输入框出现（使用更精确的选择器）
            print("等待输入框出现...")

            # 使用更精确的选择器定位标题输入框（基于aria-label属性）
            title_selector = 'div[id="textbox"][aria-label="Add a title that describes your video (type @ to mention a channel)"]'
            desc_selector = 'div[id="textbox"][aria-label="Tell viewers about your video (type @ to mention a channel)"]'

            # 等待标题输入框出现
            print("等待标题输入框出现...")
            page.wait_for_selector(title_selector, state="visible")
            print("标题输入框已出现，正在输入标题...")

            # 输入标题
            title_input = page.locator(title_selector)
            title_input.click()
            title_input.press("Control+a")  # 全选当前内容
            title_input.fill(title)  # 输入真实标题
            print(f"已输入标题: {title}")

            # 等待输入完成
            page.wait_for_timeout(1000)  # 等待1秒确保输入已完成

            # 等待描述输入框出现
            print("等待描述输入框出现...")
            page.wait_for_selector(desc_selector, state="visible")
            print("描述输入框已出现，正在输入描述...")

            # 输入描述
            desc_input = page.locator(desc_selector)
            desc_input.click()
            desc_input.press("Control+a")  # 全选当前内容
            desc_input.fill(description)  # 输入真实描述
            print(f"已输入描述: {description}")

            # 等待输入完成
            page.wait_for_timeout(1000)  # 等待1秒确保输入已完成

            # 上传缩略图
            print("正在上传缩略图...")
            thumbnail_input = page.locator('input#file-loader[type="file"]')
            thumbnail_input.set_input_files(thumbnail_path)
            print("缩略图已上传")

            # 等待缩略图上传完成
            page.wait_for_timeout(3000)  # 等待3秒确保上传完成

            # 点击Next按钮
            print("正在点击Next按钮...")
            next_button = page.locator('button:has-text("Next")')
            for i in range(3):
                next_button.click()
                print(f"已点击Next按钮 ({i+1}/3)")
                page.wait_for_timeout(1000)  # 每次点击后等待1秒
            print("已完成3次Next按钮点击")

            # 等待100秒
            print("等待100秒...")
            time.sleep(100)

            # 断开Playwright连接
            print("正在断开Playwright连接...")
            browser.close()
            print("已断开Playwright连接")

            # 关闭AdsPower浏览器
            print("正在关闭AdsPower浏览器...")
            http.request("GET", close_url)
            print("AdsPower浏览器已关闭")

    except Exception as e:
        print(f"发生错误: {str(e)}")


if __name__ == "__main__":
    main()
