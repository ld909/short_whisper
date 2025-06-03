#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kling AI 图片自动生成工具

功能说明:
此脚本用于自动将科幻故事封面提示词提交到 Kling AI 进行图片生成。
脚本使用 AdsPower 浏览器和 Playwright 进行自动化操作。
脚本会自动从 generate_cover_prompts.py 的输出目录中读取提示词文件。

依赖的输入目录:
- 封面提示词: /Volumes/dhl/audio/scifi/cover_prompts/*.txt

输出:
- 进度记录: /Volumes/dhl/audio/scifi/kling.json

使用方法:
1. 基本使用: python auto_generate_kling_images.py
2. 强制重新生成: python auto_generate_kling_images.py -f
3. 指定索引范围: python auto_generate_kling_images.py --start 1 --end 10

注意:
- 需要先启动 AdsPower 并确保本地 API 已启用
- 需要安装 playwright: pip install playwright
- 默认使用浏览器 ID: kyvvcnm
- 支持断点续传，会跳过已处理的文件
"""

import requests
import time
import json
import sys
import urllib3
import os
import platform
import argparse
import glob
import re
import random
from playwright.sync_api import sync_playwright
from tqdm import tqdm


def get_adspower_info(ads_id):
    """连接 AdsPower 浏览器并获取连接信息"""
    open_url = f"http://127.0.0.1:50325/api/v1/browser/start?user_id={ads_id}"

    # 使用urllib3替代requests，避免可能的连接问题
    http = urllib3.PoolManager()

    print("🔗 正在连接AdsPower...")
    r = http.request("GET", open_url)

    if r.status != 200:
        print(f"❌ 错误: API返回状态码 {r.status}")
        print("请确保AdsPower已启动并且本地API已启用")
        return None, None, http

    # 解析JSON响应
    resp = json.loads(r.data.decode("utf-8"))

    if resp["code"] != 0:
        print(f"❌ 错误: {resp['msg']}")
        print("请检查ads_id是否正确")
        return None, None, http

    # 获取WebSocket地址
    ws_endpoint = resp["data"]["ws"]["puppeteer"]
    debug_port = resp["data"]["debug_port"]
    remote_debugging_url = f"http://localhost:{debug_port}"

    print(f"✅ 成功连接AdsPower")
    print(f"🔧 远程调试URL: {remote_debugging_url}")

    return ws_endpoint, remote_debugging_url, http


def load_processed_files():
    """加载已处理文件的记录"""
    json_path = "/Volumes/dhl/audio/scifi/kling.json"

    if not os.path.exists(json_path):
        return set()

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("processed_files", []))
    except Exception as e:
        print(f"⚠️ 加载进度记录时出错: {e}")
        return set()


def save_processed_file(filename):
    """保存已处理文件的记录"""
    json_path = "/Volumes/dhl/audio/scifi/kling.json"

    # 加载现有数据
    processed_files = load_processed_files()
    processed_files.add(filename)

    # 保存数据
    data = {
        "processed_files": list(processed_files),
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"📝 已记录处理文件: {filename}")
        return True
    except Exception as e:
        print(f"❌ 保存进度记录时出错: {e}")
        return False


def get_prompt_files(start_index=None, end_index=None, force=False):
    """获取需要处理的提示词文件列表"""
    prompt_dir = "/Volumes/dhl/audio/scifi/cover_prompts"

    if not os.path.exists(prompt_dir):
        print(f"❌ 提示词目录不存在: {prompt_dir}")
        return []

    # 获取所有txt文件
    all_files = glob.glob(os.path.join(prompt_dir, "*.txt"))
    prompt_files = {}

    for file_path in all_files:
        basename = os.path.basename(file_path)
        match = re.match(r"(\d+)\.txt", basename)
        if match:
            story_index = int(match.group(1))

            # 应用索引范围过滤
            if start_index is not None and story_index < start_index:
                continue
            if end_index is not None and story_index > end_index:
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:  # 只包含有内容的文件
                    prompt_files[story_index] = {
                        "filename": basename,
                        "path": file_path,
                        "content": content,
                    }
            except Exception as e:
                print(f"⚠️ 读取文件 {file_path} 时出错: {e}")

    # 如果不是强制模式，过滤掉已处理的文件
    if not force:
        processed_files = load_processed_files()
        prompt_files = {
            index: info
            for index, info in prompt_files.items()
            if info["filename"] not in processed_files
        }

    return prompt_files


def wait_for_page_load(page, timeout=30):
    """等待页面完全加载"""
    print("⏳ 等待页面加载完成...")
    try:
        page.wait_for_load_state("networkidle", timeout=timeout * 1000)
        time.sleep(2)  # 额外等待2秒确保所有元素渲染完成
        print("✅ 页面加载完成")
        return True
    except Exception as e:
        print(f"⚠️ 页面加载超时: {e}")
        return False


def clear_and_fill_prompt(page, prompt_content):
    """清空并填入新的提示词"""
    try:
        # 找到输入框
        input_selector = (
            'div[contenteditable="true"][role="textbox"].tiptap.ProseMirror'
        )

        print("🔍 正在定位输入框...")
        page.wait_for_selector(input_selector, state="visible", timeout=10000)

        input_element = page.locator(input_selector)

        # 清空输入框
        print("🧹 正在清空输入框...")
        input_element.click()
        page.keyboard.press("Control+a")  # 全选
        page.keyboard.press("Delete")  # 删除
        time.sleep(0.5)

        # 填入新提示词
        print("📝 正在填入提示词...")
        input_element.fill(prompt_content)

        # 确认内容已输入
        time.sleep(1)
        print(f"✅ 已输入提示词: {prompt_content[:100]}...")
        return True

    except Exception as e:
        print(f"❌ 填入提示词时出错: {e}")
        return False


def click_generate_button(page):
    """点击生成按钮"""
    try:
        # 更新后的生成按钮选择器，适配新的元素结构
        button_selectors = [
            # 主要选择器：通过类名和包含文本定位
            'button.generic-button.critical.large:has-text("立即生成")',
            # 备用选择器1：通过特定的类组合
            "button.generic-button.animation-available.critical.large.el-tooltip__trigger",
            # 备用选择器2：通过内部文本定位
            'button:has(div.inner:has-text("立即生成"))',
            # 备用选择器3：通过类名和属性
            'button.generic-button.critical.large[class*="el-tooltip__trigger"]',
        ]

        print("🔍 正在定位生成按钮...")

        generate_button = None
        for i, selector in enumerate(button_selectors):
            try:
                print(f"尝试选择器 {i+1}: {selector}")
                page.wait_for_selector(selector, state="visible", timeout=5000)
                generate_button = page.locator(selector)

                # 验证按钮是否可见且可点击
                if generate_button.is_visible() and generate_button.is_enabled():
                    print(f"✅ 成功找到生成按钮，使用选择器 {i+1}")
                    break

            except Exception as e:
                print(f"选择器 {i+1} 失败: {e}")
                continue

        if generate_button is None:
            print("❌ 所有选择器都失败了")
            return False

        print("🎯 正在点击生成按钮...")

        # 确保按钮在视图中
        generate_button.scroll_into_view_if_needed()
        time.sleep(0.5)

        # 点击按钮
        generate_button.click()

        print("✅ 已点击生成按钮")
        return True

    except Exception as e:
        print(f"❌ 点击生成按钮时出错: {e}")
        return False


def process_prompts(ads_id, force=False, start_index=None, end_index=None):
    """处理所有提示词文件"""

    # 获取需要处理的文件
    prompt_files = get_prompt_files(start_index, end_index, force)

    if not prompt_files:
        print("📭 没有找到需要处理的提示词文件")
        return

    print(f"\n=== 📊 Kling AI 图片生成分析 ===")
    print(f"需要处理的文件数量: {len(prompt_files)}")
    print(f"处理的文件索引: {sorted(prompt_files.keys())}")

    # 获取AdsPower连接信息
    ws_endpoint, remote_debugging_url, http = get_adspower_info(ads_id)
    if not remote_debugging_url:
        return

    close_url = f"http://127.0.0.1:50325/api/v1/browser/stop?user_id={ads_id}"

    success_count = 0
    failure_count = 0

    try:
        # 使用Playwright连接浏览器
        print("🌐 正在使用Playwright连接浏览器...")
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(remote_debugging_url)
            print("✅ 成功连接到浏览器！")

            # 获取已有上下文或创建新上下文
            if not browser.contexts:
                print("创建新的浏览器上下文...")
                context = browser.new_context()
            else:
                context = browser.contexts[0]

            # 创建新标签页
            print("📄 正在创建新标签页...")
            new_page = context.new_page()

            # 关闭其他标签页
            print("🗂️ 正在关闭其他标签页...")
            for i, page in enumerate(context.pages):
                if page != new_page:
                    print(f"关闭标签页 {i+1}")
                    page.close()

            page = new_page
            print("✅ 已创建新标签页并关闭其他标签页")

            # 导航到Kling AI
            print("🎨 正在打开Kling AI...")
            page.goto("https://app.klingai.com/cn/text-to-image/new")

            if not wait_for_page_load(page):
                print("❌ 页面加载失败")
                return

            print(f"页面标题: {page.title()}")

            # 处理每个提示词文件
            with tqdm(total=len(prompt_files), desc="生成图片进度") as pbar:
                for story_index in sorted(prompt_files.keys()):
                    file_info = prompt_files[story_index]
                    filename = file_info["filename"]
                    content = file_info["content"]

                    print(f"\n=== 处理文件 {filename} ===")
                    print(f"提示词长度: {len(content)} 字符")

                    # 清空并填入提示词
                    if not clear_and_fill_prompt(page, content):
                        print(f"❌ 处理文件 {filename} 失败：无法填入提示词")
                        failure_count += 1
                        pbar.update(1)
                        continue

                    # 随机等待1-1.5秒
                    wait_time = random.uniform(1.0, 1.5)
                    print(f"⏰ 等待 {wait_time:.1f} 秒...")
                    time.sleep(wait_time)

                    # 点击生成按钮
                    if not click_generate_button(page):
                        print(f"❌ 处理文件 {filename} 失败：无法点击生成按钮")
                        failure_count += 1
                        pbar.update(1)
                        continue

                    # 保存处理记录
                    if save_processed_file(filename):
                        success_count += 1
                        print(f"✅ 文件 {filename} 处理成功")
                    else:
                        print(f"⚠️ 文件 {filename} 处理成功但记录保存失败")
                        success_count += 1

                    # 等待20-25秒再处理下一个
                    if story_index != max(prompt_files.keys()):  # 不是最后一个
                        wait_time = random.uniform(20.0, 25.0)
                        print(f"⏰ 等待 {wait_time:.1f} 秒后处理下一个...")
                        time.sleep(wait_time)

                    pbar.update(1)

            print("🔌 正在断开Playwright连接...")
            browser.close()

    except Exception as e:
        print(f"❌ 处理过程中发生错误: {e}")

    finally:
        # 关闭AdsPower浏览器
        print("🔒 正在关闭AdsPower浏览器...")
        try:
            http.request("GET", close_url)
            print("✅ AdsPower浏览器已关闭")
        except:
            print("⚠️ 关闭AdsPower浏览器时出现错误")

    # 输出最终统计
    print(f"\n=== 📈 处理完成统计 ===")
    print(f"✅ 成功处理: {success_count}/{len(prompt_files)} 个文件")
    print(f"❌ 处理失败: {failure_count}/{len(prompt_files)} 个文件")
    if len(prompt_files) > 0:
        print(f"📊 成功率: {success_count/len(prompt_files)*100:.1f}%")


def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description="自动提交封面提示词到 Kling AI 生成图片"
    )

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="强制重新处理所有文件，忽略已处理记录",
    )
    parser.add_argument(
        "--start",
        type=int,
        help="指定开始处理的故事索引",
    )
    parser.add_argument(
        "--end",
        type=int,
        help="指定结束处理的故事索引",
    )
    parser.add_argument(
        "--ads_id",
        default="kyvvcnm",
        help="AdsPower浏览器ID (默认: kyvvcnm)",
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 验证参数
    if args.start is not None and args.end is not None:
        if args.start > args.end:
            print("❌ 错误：开始索引不能大于结束索引")
            return
        if args.start <= 0 or args.end <= 0:
            print("❌ 错误：索引必须大于 0")
            return

    print("🎨 Kling AI 图片自动生成工具")
    print("=" * 50)

    # 处理提示词文件
    process_prompts(args.ads_id, args.force, args.start, args.end)

    print("\n🎉 图片生成任务完成!")


if __name__ == "__main__":
    main()
