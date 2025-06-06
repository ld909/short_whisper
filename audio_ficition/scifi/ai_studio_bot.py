#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI Studio 故事生成自动化脚本

功能说明：
这是一个用于 Google AI Studio 的自动化故事生成脚本，主要功能包括：

1. 📖 批量故事生成
   - 支持批量生成多个科幻故事
   - 自动生成随机故事参数（通过 gen_prompt 模块）
   - 智能索引管理：优先填补缺失的故事索引，然后生成新索引

2. 🌐 浏览器自动化
   - 通过 AdsPower 浏览器实现多开隔离
   - 使用 Playwright 进行精确的网页操作控制
   - 支持多窗口并发生成（最多2个窗口同时工作）

3. 🎯 智能热身机制
   - 首次运行时自动进行AI热身，发送随机问题激活模型
   - 后续生成跳过热身，直接进入正式内容生成

4. 💾 自动保存管理
   - 自动将生成的故事保存为编号的文本文件
   - 支持断点续传：检测已存在的故事，只生成缺失的部分
   - 文件保存路径：/Volumes/dhl/audio/scifi/full_story/language_code/

5. 🔄 错误处理与重试
   - 智能检测AI生成状态（通过监控停止按钮状态）
   - 生成失败时自动清理资源并提示重新运行
   - 完善的异常处理机制

6. ⚙️ 命令行界面
   - 支持指定生成数量：--count 或 -c 参数
   - 支持指定浏览器ID：--ads-id 参数
   - 默认生成2个故事，使用 kyencl7 浏览器配置

使用方法：
python ai_studio_bot.py --count 5 --ads-id your_browser_id

依赖组件：
- AdsPower：提供浏览器环境隔离
- Playwright：网页自动化控制
- gen_prompt：故事参数生成模块

作者：AI Studio 自动化团队
版本：v2.0
更新：支持多窗口并发、智能热身、断点续传
"""

import requests
import time
import json
import sys
import urllib3
import os
import glob
import re
import argparse
import random
from playwright.sync_api import sync_playwright
from gen_prompt import generate_prompt, remove_markdown

# 添加随机问题列表用于热身
WARMUP_QUESTIONS = [
    "今天天气如何？",
    "你好吗？",
    "现在几点了？",
    "请介绍一下你自己。",
    "你能帮我做什么？",
    "今天是星期几？",
    "你最喜欢什么颜色？",
    "请说一个简单的笑话。",
    "什么是人工智能？",
    "你会说中文吗？",
]


def countdown_wait(seconds=20, window_index=None):
    """显示倒计时等待"""
    prefix = f"窗口 {window_index}: " if window_index else ""
    print(f"{prefix}等待 {seconds} 秒后继续...")

    for i in range(seconds, 0, -1):
        print(f"\r{prefix}倒计时: {i:2d} 秒", end="", flush=True)
        time.sleep(1)

    print(f"\r{prefix}等待完成！{'':10}")  # 清除倒计时显示


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


def get_existing_stories(story_dir):
    """获取已经生成的故事索引列表"""
    if not os.path.exists(story_dir):
        os.makedirs(story_dir, exist_ok=True)
        return []

    existing_files = glob.glob(os.path.join(story_dir, "*.txt"))
    existing_numbers = []

    for file_path in existing_files:
        basename = os.path.basename(file_path)
        # 排除以点开头的文件（如.DS_Store等）
        if basename.startswith("."):
            continue
        match = re.match(r"(\d+)\.txt", basename)
        if match:
            existing_numbers.append(int(match.group(1)))

    return sorted(existing_numbers)


def get_story_parameters_to_generate(num_needed=1):
    """生成需要的故事参数，优先填补缺失的索引"""
    story_dir = "/Volumes/dhl/audio/scifi/full_story/language_code"
    existing_stories = get_existing_stories(story_dir)

    print(f"\n=== 📊 故事索引分析 ===")
    print(f"已存在的故事索引: {existing_stories}")
    print(f"需要生成的故事数量: {num_needed}")

    stories_to_generate = []

    if existing_stories:
        max_existing = max(existing_stories)
        print(f"当前最大索引: {max_existing}")

        # 找出缺失的索引（从1到最大值之间的空缺）
        missing_indices = []
        for i in range(1, max_existing + 1):
            if i not in existing_stories:
                missing_indices.append(i)

        missing_indices.sort()  # 确保从小到大排序

        if missing_indices:
            print(f"🔍 发现缺失的故事索引: {missing_indices}")
            print(f"优先填补从索引 {missing_indices[0]} 开始的缺失位置")
        else:
            print(f"✅ 索引 1-{max_existing} 连续完整，无缺失")

        indices_to_use = []

        # 优先使用缺失的索引（从最小开始）
        missing_count = 0
        for missing_idx in missing_indices:
            if len(indices_to_use) < num_needed:
                indices_to_use.append(missing_idx)
                missing_count += 1
                print(f"  📝 将填补缺失索引: {missing_idx}")

        # 如果还需要更多，从最大值+1开始
        if len(indices_to_use) < num_needed:
            next_new_index = max_existing + 1
            remaining_needed = num_needed - len(indices_to_use)
            print(
                f"  🆕 需要生成新索引: {next_new_index} ~ {next_new_index + remaining_needed - 1}"
            )

            for i in range(remaining_needed):
                indices_to_use.append(next_new_index + i)

        print(f"📋 最终生成索引列表: {sorted(indices_to_use)}")
        if missing_count > 0:
            print(f"   其中 {missing_count} 个是填补缺失的索引")
            print(f"   其中 {len(indices_to_use) - missing_count} 个是新增的索引")
    else:
        # 如果没有任何故事，从1开始
        indices_to_use = list(range(1, num_needed + 1))
        print(f"🎯 第一次生成故事，从索引 1 开始")
        print(f"📋 生成索引列表: {indices_to_use}")

    # 生成故事参数
    print(f"\n=== 🎨 开始生成故事参数 ===")
    for story_index in sorted(indices_to_use):  # 确保按索引顺序处理
        story_prompt = generate_prompt()
        clean_prompt = remove_markdown(story_prompt)

        stories_to_generate.append({"index": story_index, "prompt": clean_prompt})
        print(f"✅ 准备生成故事 {story_index}")

    print(f"=== 📝 故事参数生成完成，共 {len(stories_to_generate)} 个 ===\n")
    return stories_to_generate


def wait_for_warmup_completion(page, window_index):
    """等待热身问题的AI回答完成 - 停止按钮状态判断+错误检测"""
    print(f"窗口 {window_index}: 正在等待热身问题AI回答完成...")

    # 多种可能的停止按钮选择器
    stop_selectors = [
        'rect[class*="stoppable-stop"]',
        'button[aria-label*="stop"]',
        'button[aria-label*="Stop"]',
        '[class*="stop-button"]',
        '[class*="stoppable"]',
        'rect[class="stoppable-stop ng-tns-c51961493-15"]',
    ]

    # 错误提示选择器
    error_selectors = [
        'div.model-error:has-text("An internal error has occurred")',  # 具体的错误元素
        'div:has-text("An internal error has occurred")',  # 更通用的选择器
        '[class*="model-error"]:has-text("internal error")',  # 包含internal error的元素
        'div:has-text("internal error")',  # 最通用的错误检测
    ]

    try:
        # 先等待3秒让AI开始运行
        print(f"窗口 {window_index}: 等待3秒让热身AI开始运行...")
        time.sleep(3)

        # 检查停止按钮状态和错误提示
        print(f"窗口 {window_index}: 检查热身AI停止按钮状态和错误提示...")

        while True:
            # 首先检查是否有错误提示
            error_detected = False
            for error_selector in error_selectors:
                try:
                    if page.locator(error_selector).count() > 0:
                        print(
                            f"窗口 {window_index}: ❌ 热身阶段检测到AI生成错误: {error_selector}"
                        )
                        error_detected = True
                        break
                except:
                    continue

            if error_detected:
                raise Exception(
                    f"窗口 {window_index}: 热身阶段AI生成出现internal error"
                )

            # 检查停止按钮是否存在
            stop_buttons_exist = False
            for selector in stop_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        stop_buttons_exist = True
                        break
                except:
                    continue

            print(f"窗口 {window_index}: 热身停止按钮存在: {stop_buttons_exist}")

            # 如果停止按钮不存在，认为热身完成
            if not stop_buttons_exist:
                print(f"窗口 {window_index}: ✅ 热身AI运行完成（停止按钮不存在）")
                return

            # 每2秒检查一次
            time.sleep(2)

    except Exception as e:
        print(f"窗口 {window_index}: 热身等待过程中出现异常: {e}")
        raise e


def wait_for_ai_completion(page, window_index):
    """等待AI运行完成 - 停止按钮状态判断+错误检测"""
    print(f"窗口 {window_index}: 正在等待AI运行完成...")

    # 等待一下让AI开始运行
    page.wait_for_timeout(3000)

    # 停止按钮选择器
    stop_selectors = [
        'rect[class*="stoppable-stop"]',  # 更通用的停止按钮选择器
        'button[aria-label*="stop"]',
        'button[aria-label*="Stop"]',
        '[class*="stop-button"]',
        '[class*="stoppable"]',
        'rect[class="stoppable-stop ng-tns-c51961493-15"]',  # 原有的具体选择器作为备用
    ]

    # 错误提示选择器
    error_selectors = [
        'div.model-error:has-text("An internal error has occurred")',  # 具体的错误元素
        'div:has-text("An internal error has occurred")',  # 更通用的选择器
        '[class*="model-error"]:has-text("internal error")',  # 包含internal error的元素
        'div:has-text("internal error")',  # 最通用的错误检测
    ]

    try:
        # 第一步：等待AI开始运行（等待停止按钮出现）
        print(f"窗口 {window_index}: 等待AI开始运行...")
        found_stop_button = False

        for attempt in range(15):  # 等待最多30秒
            # 首先检查是否有错误提示
            for error_selector in error_selectors:
                try:
                    if page.locator(error_selector).count() > 0:
                        print(
                            f"窗口 {window_index}: ❌ 检测到AI生成错误: {error_selector}"
                        )
                        raise Exception(
                            f"窗口 {window_index}: AI生成出现internal error"
                        )
                except Exception as e:
                    if "AI生成出现internal error" in str(e):
                        raise e  # 重新抛出我们的错误
                    # 其他异常（如选择器语法错误）继续下一个
                    continue

            for selector in stop_selectors:
                try:
                    count = page.locator(selector).count()
                    if count > 0:
                        print(
                            f"窗口 {window_index}: 发现停止按钮: {selector} (数量: {count})"
                        )
                        found_stop_button = True
                        break
                except:
                    continue

            if found_stop_button:
                print(f"窗口 {window_index}: AI开始运行")
                break

            print(f"窗口 {window_index}: 尝试 {attempt + 1}/15 - 等待停止按钮出现...")
            page.wait_for_timeout(2000)

        if not found_stop_button:
            print(f"窗口 {window_index}: ⚠️ 未检测到停止按钮，可能AI没有开始运行")
            raise Exception(f"窗口 {window_index}: 无法检测到AI运行状态")

        # 第二步：等待停止按钮消失，同时检测错误
        print(f"窗口 {window_index}: 监控停止按钮状态和错误提示...")
        consecutive_no_stop_button = 0
        check_count = 0

        while True:
            check_count += 1

            # 首先检查是否有错误提示
            error_detected = False
            for error_selector in error_selectors:
                try:
                    if page.locator(error_selector).count() > 0:
                        print(
                            f"窗口 {window_index}: ❌ 检测到AI生成错误: {error_selector}"
                        )
                        error_detected = True
                        break
                except:
                    continue

            if error_detected:
                raise Exception(f"窗口 {window_index}: AI生成过程中出现internal error")

            # 检查所有停止按钮是否都消失了
            stop_buttons_exist = False
            active_stop_selectors = []
            for selector in stop_selectors:
                try:
                    count = page.locator(selector).count()
                    if count > 0:
                        stop_buttons_exist = True
                        active_stop_selectors.append(f"{selector}({count})")
                except:
                    continue

            print(
                f"窗口 {window_index}: 检查第{check_count}次 - 停止按钮存在: {stop_buttons_exist}"
            )
            if stop_buttons_exist:
                print(
                    f"窗口 {window_index}: 活跃的停止按钮: {', '.join(active_stop_selectors)}"
                )

            if not stop_buttons_exist:
                consecutive_no_stop_button += 1
                print(
                    f"窗口 {window_index}: 停止按钮已消失 (连续 {consecutive_no_stop_button} 次)"
                )

                # 连续3次检查都没有停止按钮，认为完成
                if consecutive_no_stop_button >= 3:
                    print(
                        f"窗口 {window_index}: ✅ AI运行完成 - 停止按钮已连续消失{consecutive_no_stop_button}次"
                    )
                    break
            else:
                consecutive_no_stop_button = 0  # 重置计数器

            # 安全超时：如果检查超过120次（约10分钟）
            if check_count >= 120:
                print(f"窗口 {window_index}: ⚠️ 已达到最大等待时间（10分钟）")
                raise Exception(f"窗口 {window_index}: AI生成超时")

            # 每次等待5秒
            time.sleep(5)

        # 额外等待确保完全完成
        print(f"窗口 {window_index}: 额外等待3秒确保完成...")
        time.sleep(3)
        print(f"窗口 {window_index}: ✅ 运行完成")

    except Exception as e:
        print(f"窗口 {window_index}: 等待过程中出现异常: {e}")
        raise e


def save_generated_story(page, story_index, story_dir):
    """保存生成的故事内容"""
    try:
        # 等待内容生成完成
        page.wait_for_timeout(2000)

        # 查找生成的内容区域 - 重点关注ms-prompt-chunk等AI Studio特有的元素
        content_selectors = [
            "ms-prompt-chunk.text-chunk",  # 具体的AI Studio响应容器
            "ms-prompt-chunk",  # AI Studio的主要内容容器
            "ms-text-chunk",  # AI Studio的文本块
            "ms-cmark-node",  # AI Studio的markdown节点
            "ms-prompt-chunk .text-chunk",  # 嵌套的文本块
            "ms-prompt-chunk span",  # 直接选择span内的文本
            ".text-chunk",  # 通用文本块类
            'div[class*="response"]',
            'div[class*="message-content"]',
            'div[class*="output"]',
            'div[data-testid*="response"]',
            'div[class*="generated"]',
            "pre",
            ".markdown-content",
            "[data-message-content]",
        ]

        content = ""
        for selector in content_selectors:
            try:
                elements = page.locator(selector)
                if elements.count() > 0:
                    print(
                        f"故事 {story_index}: 找到 {elements.count()} 个元素使用选择器: {selector}"
                    )

                    # 对于AI Studio特有的元素，优先选择最后一个元素
                    if (
                        "ms-prompt-chunk" in selector
                        or "ms-text-chunk" in selector
                        or "ms-cmark-node" in selector
                    ):
                        # 从最后一个元素开始检查，这通常是最新生成的内容
                        for i in range(elements.count() - 1, -1, -1):
                            element_text = elements.nth(i).inner_text().strip()
                            if (
                                element_text and len(element_text) > 50
                            ):  # 过滤掉太短的内容
                                content = element_text
                                print(
                                    f"故事 {story_index}: 从AI Studio元素 #{i+1}（最后一个）提取到内容，长度: {len(content)}"
                                )
                                break

                        if content:
                            break
                    else:
                        # 对于其他元素，也优先选择最后一个元素
                        for i in range(elements.count() - 1, -1, -1):
                            element_content = elements.nth(i).inner_text()
                            if (
                                element_content.strip() and len(element_content) > 100
                            ):  # 确保内容足够长
                                content = element_content
                                print(
                                    f"故事 {story_index}: 从选择器 {selector} 的最后一个元素提取到内容，长度: {len(content)}"
                                )
                                break
                        if content:
                            break

            except Exception as e:
                print(f"故事 {story_index}: 选择器 {selector} 提取失败: {e}")
                continue

        if content.strip():
            # 清理内容 - 移除多余的换行和空白
            content = content.strip()

            # 保存到文件
            os.makedirs(story_dir, exist_ok=True)
            file_path = os.path.join(story_dir, f"{story_index}.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"故事 {story_index} 已保存到: {file_path}")
            print(f"内容长度: {len(content)} 字符")
            # 打印内容的前200个字符作为预览
            preview = content[:200] + "..." if len(content) > 200 else content
            print(f"内容预览: {preview}")
            return True
        else:
            print(f"故事 {story_index}: 未找到生成的内容")
            # 尝试打印页面的部分内容用于调试
            try:
                page_content = page.content()
                if "ms-prompt-chunk" in page_content:
                    print(
                        f"故事 {story_index}: 页面中发现ms-prompt-chunk元素，但无法提取内容"
                    )
                else:
                    print(f"故事 {story_index}: 页面中未发现ms-prompt-chunk元素")
            except:
                pass
            return False

    except Exception as e:
        print(f"保存故事 {story_index} 时出错: {e}")
        return False


def process_window(
    page, window_index, story_data, is_first_story=True, need_warmup=False
):
    """处理单个窗口的故事生成"""
    try:
        print(f"窗口 {window_index}: 开始处理故事 {story_data['index']}")
        print(
            f"窗口 {window_index}: 窗口第一次={is_first_story}, 需要热身={need_warmup}"
        )

        if is_first_story and need_warmup:
            # 全局第一次：先进行热身，然后开新tab进行正式生成
            print(f"窗口 {window_index}: 全局第一次需要热身，正在打开AI Studio...")
            page.goto("https://aistudio.google.com/u/1/prompts/new_chat")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(8000)

            # 发送随机问题进行热身
            random_question = random.choice(WARMUP_QUESTIONS)
            print(f"窗口 {window_index}: 发送热身问题: {random_question}")

            # 查找文本框进行热身 - 使用更精确的选择器
            textarea_selectors = [
                ".text-wrapper textarea",  # 根据提供的HTML结构
                "ms-autosize-textarea textarea",  # 具体的组件选择器
                'textarea[aria-label*="Type something"]',  # aria-label匹配
                'textarea[class*="textarea"]',
                'textarea[class*="gmat-body-medium"]',
                ".text-input-wrapper textarea",
                "div.text-wrapper textarea",
                "textarea",
            ]

            warmup_textarea = None
            for selector in textarea_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        warmup_textarea = page.locator(selector)
                        print(
                            f"窗口 {window_index}: 找到热身文本框，使用选择器: {selector}"
                        )
                        break
                except:
                    continue

            if warmup_textarea and warmup_textarea.count() > 0:
                # 点击文本框并直接输入热身问题
                warmup_textarea.click()
                page.wait_for_timeout(1000)

                # 确保文本框获得焦点
                warmup_textarea.focus()
                page.wait_for_timeout(500)

                # 清空现有内容并直接输入热身问题
                warmup_textarea.fill("")  # 清空
                page.wait_for_timeout(300)
                warmup_textarea.type(random_question)  # 直接输入文字
                page.wait_for_timeout(1000)
                print(f"窗口 {window_index}: 已输入热身问题到文本框")

                # 查找并点击运行按钮
                run_button_selectors = [
                    'button[aria-label="Run"][type="submit"]',
                    'button[aria-label="Run"]',
                    'button[type="submit"]',
                    'button:has-text("Run")',
                    ".run-button",
                    'button[class*="run"]',
                ]

                warmup_run_button = None
                for selector in run_button_selectors:
                    try:
                        if page.locator(selector).count() > 0:
                            warmup_run_button = page.locator(selector)
                            break
                    except:
                        continue

                if warmup_run_button and warmup_run_button.count() > 0:
                    print(f"窗口 {window_index}: 发送热身问题...")
                    warmup_run_button.click()

                    # 等待AI回答热身问题 - 使用专门的热身检测函数
                    try:
                        wait_for_warmup_completion(page, window_index)
                        print(f"窗口 {window_index}: 热身问题回答完成")
                    except Exception as e:
                        print(f"窗口 {window_index}: 热身问题回答过程中出错: {e}")
                        # 抛出异常到main函数处理，与正式故事生成保持一致
                        raise Exception(
                            f"窗口 {window_index}: 热身阶段AI生成状态检测失败"
                        )

                    # 等待5秒
                    print(f"窗口 {window_index}: 热身完成，等待5秒...")
                    time.sleep(5)

                    # 开新tab进行正式生成
                    print(f"窗口 {window_index}: 开新tab进行正式故事生成...")
                    page.goto("https://aistudio.google.com/u/1/prompts/new_chat")
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(8000)
                    print(f"窗口 {window_index}: 新页面已完全加载")
                else:
                    print(f"窗口 {window_index}: 热身阶段未找到运行按钮，跳过热身")
            else:
                print(f"窗口 {window_index}: 热身阶段未找到文本框，跳过热身")
        elif is_first_story and not need_warmup:
            # 窗口第一次但全局热身已完成：直接打开AI Studio
            print(f"窗口 {window_index}: 窗口第一次（跳过热身），正在打开AI Studio...")
            page.goto("https://aistudio.google.com/u/1/prompts/new_chat")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(8000)
            print(f"窗口 {window_index}: 页面已完全加载")
        else:
            # 后续故事：直接导航到新的聊天页面
            print(f"窗口 {window_index}: 导航到新的聊天页面...")
            page.goto("https://aistudio.google.com/u/1/prompts/new_chat")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(8000)
            print(f"窗口 {window_index}: 新页面已完全加载")

        # 下面是正式的故事生成流程（适用于热身后的第一个故事和后续故事）
        # 多种可能的文本框选择器 - 使用更精确的选择器
        textarea_selectors = [
            ".text-wrapper textarea",  # 根据提供的HTML结构
            "ms-autosize-textarea textarea",  # 具体的组件选择器
            'textarea[aria-label*="Type something"]',  # aria-label匹配
            'textarea[class*="textarea"]',
            'textarea[class*="gmat-body-medium"]',
            ".text-input-wrapper textarea",
            "div.text-wrapper textarea",
            "textarea",
        ]

        print(f"窗口 {window_index}: 尝试查找文本框...")
        textarea = None

        # 首先等待父容器出现
        try:
            print(f"窗口 {window_index}: 等待文本输入容器...")
            page.wait_for_selector(
                ".text-wrapper, .text-input-wrapper, ms-chunk-input", timeout=20000
            )
            page.wait_for_timeout(3000)  # 额外等待容器内容加载
            print(f"窗口 {window_index}: 文本输入容器已加载")
        except:
            print(f"窗口 {window_index}: 父容器等待超时，继续尝试...")

        # 尝试多个选择器
        for i, selector in enumerate(textarea_selectors):
            try:
                print(
                    f"窗口 {window_index}: 尝试选择器 {i+1}/{len(textarea_selectors)}: {selector}"
                )
                page.wait_for_selector(selector, timeout=15000)
                textarea = page.locator(selector)
                if textarea.count() > 0:
                    print(f"窗口 {window_index}: 成功找到文本框！")
                    break
            except Exception as e:
                print(f"窗口 {window_index}: 选择器 {selector} 失败: {str(e)[:100]}")
                continue

        if not textarea or textarea.count() == 0:
            print(f"窗口 {window_index}: 所有文本框选择器都失败了")
            return False

        # 直接输入故事参数到文本框
        print(f"窗口 {window_index}: 正在输入故事参数到文本框...")

        # 确保元素可见和可交互
        textarea.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)

        # 点击文本框并获得焦点
        textarea.click()
        page.wait_for_timeout(500)

        # 确保文本框获得焦点
        textarea.focus()
        page.wait_for_timeout(500)

        # 清空现有内容并直接输入故事参数
        textarea.fill("")  # 清空
        page.wait_for_timeout(500)

        # 分段输入长文本，避免一次性输入过多导致问题
        story_prompt = story_data["prompt"]
        print(
            f"窗口 {window_index}: 开始输入故事参数，总长度: {len(story_prompt)} 字符"
        )

        # 尝试直接使用 fill() 方法快速输入整个文本
        try:
            print(f"窗口 {window_index}: 尝试快速输入整个文本...")
            textarea.fill(story_prompt)
            page.wait_for_timeout(500)

            # 验证输入是否成功
            current_value = textarea.input_value()
            if (
                len(current_value) >= len(story_prompt) * 0.95
            ):  # 如果输入了95%以上内容，认为成功
                print(
                    f"窗口 {window_index}: 快速输入成功！实际长度: {len(current_value)}"
                )
            else:
                raise Exception("快速输入不完整，切换到分段输入")

        except Exception as e:
            print(f"窗口 {window_index}: 快速输入失败: {e}，切换到分段输入方式...")

            # 备用方案：分段输入，但使用更快的方式
            chunk_size = 2000  # 增大chunk大小
            textarea.fill("")  # 先清空
            page.wait_for_timeout(300)

            accumulated_text = ""
            for i in range(0, len(story_prompt), chunk_size):
                chunk = story_prompt[i : i + chunk_size]
                accumulated_text += chunk

                # 使用 JavaScript 直接设置值，这比 type() 快很多
                try:
                    page.evaluate(
                        """
                        (text) => {
                            const textarea = document.querySelector('.text-wrapper textarea') || 
                                           document.querySelector('ms-autosize-textarea textarea') || 
                                           document.querySelector('textarea');
                            if (textarea) {
                                textarea.value = text;
                                textarea.dispatchEvent(new Event('input', { bubbles: true }));
                                textarea.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                        }
                    """,
                        accumulated_text,
                    )

                    print(
                        f"窗口 {window_index}: 已输入 chunk {i//chunk_size + 1}, 总进度: {len(accumulated_text)}/{len(story_prompt)} 字符"
                    )

                    # chunk间短暂等待
                    if i + chunk_size < len(story_prompt):
                        page.wait_for_timeout(100)  # 减少等待时间

                except Exception as js_error:
                    print(
                        f"窗口 {window_index}: JavaScript输入失败，回退到 fill() 方式: {js_error}"
                    )
                    # 回退到 fill() 方式
                    textarea.fill(accumulated_text)
                    page.wait_for_timeout(200)

        print(f"窗口 {window_index}: 故事参数输入完成")

        # 多种可能的运行按钮选择器
        run_button_selectors = [
            'button[aria-label="Run"][type="submit"]',
            'button[aria-label="Run"]',
            'button[type="submit"]',
            'button:has-text("Run")',
            ".run-button",
            'button[class*="run"]',
        ]

        print(f"窗口 {window_index}: 寻找运行按钮...")
        run_button = None

        for i, selector in enumerate(run_button_selectors):
            try:
                print(
                    f"窗口 {window_index}: 尝试运行按钮选择器 {i+1}/{len(run_button_selectors)}: {selector}"
                )
                page.wait_for_selector(selector, timeout=10000)

                # 等待按钮变为可用状态
                page.wait_for_function(
                    f'document.querySelector("{selector}") && !document.querySelector("{selector}").disabled',
                    timeout=10000,
                )

                run_button = page.locator(selector)
                if run_button.count() > 0:
                    print(f"窗口 {window_index}: 成功找到运行按钮！")
                    break
            except Exception as e:
                print(
                    f"窗口 {window_index}: 运行按钮选择器 {selector} 失败: {str(e)[:100]}"
                )
                continue

        if not run_button or run_button.count() == 0:
            print(f"窗口 {window_index}: 未找到运行按钮")
            return False

        print(f"窗口 {window_index}: 正在点击运行按钮...")
        run_button.click()

        # 等待AI运行完成
        try:
            wait_for_ai_completion(page, window_index)
        except Exception as e:
            print(f"窗口 {window_index}: AI生成失败 - {e}")
            # 抛出异常到main函数处理
            raise Exception(f"窗口 {window_index}: AI生成状态检测失败")

        # 保存生成的故事
        story_dir = "/Volumes/dhl/audio/scifi/full_story/language_code"
        success = save_generated_story(page, story_data["index"], story_dir)

        if success:
            print(f"窗口 {window_index}: 故事 {story_data['index']} 处理完成")
            # 生成完成后等待20秒
            countdown_wait(20, window_index)
        else:
            print(f"窗口 {window_index}: 故事 {story_data['index']} 保存失败")

        return success

    except Exception as e:
        print(f"窗口 {window_index}: 处理故事 {story_data['index']} 时出错: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="AI Studio 故事生成器")
    parser.add_argument(
        "--count", "-c", type=int, default=2, help="要生成的故事数量 (默认: 2)"
    )
    parser.add_argument(
        "--ads-id", default="kyencl7", help="AdsPower 浏览器ID (默认: kyencl7)"
    )

    args = parser.parse_args()

    # 验证参数
    if args.count <= 0:
        print("❌ 错误：故事数量必须大于 0")
        return

    if args.count > 10:
        print("⚠️  警告：建议不要一次生成超过 10 个故事，以免浏览器性能问题")
        response = input("是否继续？(y/N): ")
        if response.lower() != "y":
            print("已取消")
            return

    ads_id = args.ads_id
    story_count = args.count

    print(f"🎯 准备生成 {story_count} 个故事")
    print(f"📱 使用 AdsPower ID: {ads_id}")

    close_url = f"http://127.0.0.1:50325/api/v1/browser/stop?user_id={ads_id}"

    try:
        # 获取需要生成的故事参数
        stories_to_generate = get_story_parameters_to_generate(story_count)

        if not stories_to_generate:
            print("没有需要生成的故事")
            return

        print(f"📝 实际需要生成 {len(stories_to_generate)} 个故事")

        # 获取WebDriver
        ws_endpoint, remote_debugging_url, http = get_adspower_info(ads_id)

        if not ws_endpoint:
            return

        # 使用Playwright连接浏览器
        print("正在使用Playwright连接浏览器...")
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(remote_debugging_url)
            print("成功连接到浏览器！")

            # 获取或创建上下文
            if not browser.contexts:
                context = browser.new_context()
            else:
                context = browser.contexts[0]

            # 先创建一个新的空白页面，确保浏览器不会关闭
            print("正在创建新的空白页面...")
            new_page = context.new_page()
            print("已创建新的空白页面")

            # 记录所有需要关闭的现有页面（除了刚创建的新页面）
            pages_to_close = []
            for page in context.pages:
                if page != new_page:  # 不包括刚创建的新页面
                    pages_to_close.append(page)

            # 关闭所有其他已存在的窗口
            if pages_to_close:
                print(f"正在关闭之前的 {len(pages_to_close)} 个窗口...")
                for i, page in enumerate(pages_to_close):
                    try:
                        page.close()
                        print(f"已关闭第 {i+1} 个之前的窗口")
                    except Exception as e:
                        print(f"关闭第 {i+1} 个窗口时出错: {e}")
            else:
                print("没有需要关闭的之前窗口")

            # 创建需要的窗口数量（最多2个窗口并发）
            windows = []
            max_concurrent_windows = min(2, len(stories_to_generate))  # 最多2个窗口并发

            print(f"正在创建总共 {max_concurrent_windows} 个工作窗口...")

            # 第一个窗口使用已创建的空白页面
            windows.append(new_page)
            print(f"窗口 1 使用已创建的空白页面")

            # 如果需要更多窗口，再创建
            for i in range(1, max_concurrent_windows):
                page = context.new_page()
                windows.append(page)
                print(f"已创建窗口 {i+1}")

            # 分批处理故事
            all_results = []
            stories_processed = 0

            # 全局热身标志，只在第一次运行时进行热身
            global_warmup_done = False
            # 为每个窗口跟踪是否是第一个故事（用于页面初始化，不包括热身）
            window_first_story = [True] * len(windows)

            while stories_processed < len(stories_to_generate):
                # 确定当前批次要处理的故事
                current_batch = []
                for i in range(len(windows)):
                    if stories_processed + i < len(stories_to_generate):
                        current_batch.append(stories_to_generate[stories_processed + i])

                print(
                    f"\n=== 开始处理第 {stories_processed//len(windows) + 1} 批，共 {len(current_batch)} 个故事 ==="
                )

                # 为每个窗口分配故事并处理
                batch_results = []

                try:
                    for i, window in enumerate(windows):
                        if i < len(current_batch):
                            story_data = current_batch[i]
                            print(
                                f"\n=== 开始处理窗口 {i+1}，故事 {story_data['index']} ==="
                            )

                            # 切换到当前窗口并使其获得焦点
                            window.bring_to_front()

                            # 处理当前窗口的故事
                            try:
                                # 传递是否是第一个故事的标志和是否需要热身
                                is_first = window_first_story[i]
                                need_warmup = not global_warmup_done
                                success = process_window(
                                    window, i + 1, story_data, is_first, need_warmup
                                )

                                # 更新全局热身状态和窗口状态
                                if need_warmup:
                                    global_warmup_done = True
                                    print(
                                        f"🎯 全局热身已完成，后续所有故事生成将跳过热身步骤"
                                    )

                                if is_first:
                                    window_first_story[i] = False
                                    print(
                                        f"窗口 {i+1}: 已完成首次初始化，后续将使用快速切换方式"
                                    )

                                batch_results.append(success)

                                if success:
                                    print(
                                        f"窗口 {i+1}：故事 {story_data['index']} 生成成功！"
                                    )
                                else:
                                    print(
                                        f"窗口 {i+1}：故事 {story_data['index']} 生成失败！"
                                    )

                                # 在处理下一个窗口前稍作等待（已在process_window中有20秒等待）
                                if i < len(current_batch) - 1:
                                    print(f"等待 2 秒后处理下一个窗口...")
                                    time.sleep(2)

                            except Exception as e:
                                if "AI生成状态检测失败" in str(e):
                                    print(f"\n❌ 检测到AI生成状态失败！")
                                    print(f"错误信息: {e}")
                                    print(f"正在退出浏览器...")

                                    # 关闭所有窗口
                                    for j, close_window in enumerate(windows):
                                        try:
                                            close_window.close()
                                            print(f"已关闭窗口 {j+1}")
                                        except Exception as close_e:
                                            print(f"关闭窗口 {j+1} 时出错: {close_e}")

                                    # 断开Playwright连接
                                    browser.close()
                                    print("已断开Playwright连接")

                                    # 关闭AdsPower浏览器
                                    print("正在关闭AdsPower浏览器...")
                                    http.request("GET", close_url)
                                    print("AdsPower浏览器已关闭")

                                    print("\n🔄 生成失败，请重新运行程序")
                                    return
                                else:
                                    # 其他异常继续抛出
                                    raise e

                    # 更新处理进度
                    stories_processed += len(current_batch)
                    all_results.extend(batch_results)

                    # 统计当前批次结果
                    successful_in_batch = sum(batch_results)
                    print(f"\n=== 第 {stories_processed//len(windows)} 批处理完成 ===")
                    print(
                        f"本批成功: {successful_in_batch}/{len(current_batch)} 个故事"
                    )
                    print(
                        f"总进度: {stories_processed}/{len(stories_to_generate)} 个故事"
                    )

                    # 如果还有更多故事要处理，稍作等待（每个故事已有20秒等待）
                    if stories_processed < len(stories_to_generate):
                        print(f"等待 3 秒后处理下一批...")
                        time.sleep(3)

                except Exception as e:
                    print(f"处理批次时发生未预期的错误: {e}")
                    import traceback

                    traceback.print_exc()
                    break

            # 统计最终结果
            successful_stories = sum(all_results)
            total_stories = len(all_results)

            print(f"\n=== 🎉 所有故事处理完成 ===")
            print(f"✅ 成功生成: {successful_stories}/{total_stories} 个故事")
            print(f"📊 成功率: {successful_stories/total_stories*100:.1f}%")

            # 关闭所有窗口
            print("正在关闭所有窗口...")
            for i, window in enumerate(windows):
                try:
                    window.close()
                    print(f"已关闭窗口 {i+1}")
                except Exception as e:
                    print(f"关闭窗口 {i+1} 时出错: {e}")

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
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
