import requests
import time
import json
import sys
import urllib3
import os
import glob
import re
from playwright.sync_api import sync_playwright
from gen_prompt import generate_prompt, remove_markdown


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
        match = re.match(r"(\d+)\.txt", basename)
        if match:
            existing_numbers.append(int(match.group(1)))

    return sorted(existing_numbers)


def get_story_parameters_to_generate(num_needed=1):
    """生成需要的故事参数，跳过已经存在的"""
    story_dir = "/Volumes/dhl/audio/scifi/full_story/language_code"
    existing_stories = get_existing_stories(story_dir)

    print(f"已存在的故事索引: {existing_stories}")

    # 找出下一个需要生成的索引
    if existing_stories:
        next_index = max(existing_stories) + 1
    else:
        next_index = 1

    stories_to_generate = []
    for i in range(num_needed):
        story_index = next_index + i
        # 生成故事参数
        story_prompt = generate_prompt()
        clean_prompt = remove_markdown(story_prompt)

        stories_to_generate.append({"index": story_index, "prompt": clean_prompt})
        print(f"准备生成故事 {story_index}")

    return stories_to_generate


def wait_for_ai_completion(page, window_index):
    """等待AI运行完成"""
    print(f"窗口 {window_index}: 正在等待AI运行完成...")

    # 等待运行按钮变为可用状态（AI开始运行）
    page.wait_for_timeout(3000)

    # 多种可能的停止按钮选择器
    stop_selectors = [
        'rect[class*="stoppable-stop"]',  # 更通用的停止按钮选择器
        'button[aria-label*="stop"]',
        'button[aria-label*="Stop"]',
        '[class*="stop-button"]',
        '[class*="stoppable"]',
        'rect[class="stoppable-stop ng-tns-c51961493-15"]',  # 原有的具体选择器作为备用
    ]

    # 多种运行状态指示器
    running_indicators = [
        '[class*="generating"]',
        '[class*="loading"]',
        '[class*="thinking"]',
        '[class*="processing"]',
        ".spinner",
        '[aria-busy="true"]',
    ]

    max_wait_time = 300  # 最大等待时间5分钟
    start_time = time.time()
    found_running_state = False

    try:
        # 第一步：等待AI开始运行（尝试找到停止按钮或运行指示器）
        print(f"窗口 {window_index}: 等待AI开始运行...")
        for attempt in range(10):  # 最多尝试10次，每次1.5秒
            found_stop_button = False
            found_running = False

            # 检查停止按钮
            for selector in stop_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        print(f"窗口 {window_index}: 发现停止按钮: {selector}")
                        found_stop_button = True
                        found_running_state = True
                        break
                except:
                    continue

            # 检查运行指示器
            if not found_stop_button:
                for selector in running_indicators:
                    try:
                        if page.locator(selector).count() > 0:
                            print(f"窗口 {window_index}: 发现运行指示器: {selector}")
                            found_running = True
                            found_running_state = True
                            break
                    except:
                        continue

            if found_stop_button or found_running:
                print(f"窗口 {window_index}: AI开始运行")
                break

            page.wait_for_timeout(1500)

        if not found_running_state:
            print(f"窗口 {window_index}: 未检测到AI运行状态，可能已经完成或未开始")
            # 等待一段时间再检查内容
            page.wait_for_timeout(10000)
            return

        # 第二步：等待AI运行完成
        print(f"窗口 {window_index}: 监控AI运行状态...")

        while time.time() - start_time < max_wait_time:
            try:
                # 检查所有停止按钮是否都消失了
                stop_buttons_exist = False
                for selector in stop_selectors:
                    try:
                        if page.locator(selector).count() > 0:
                            stop_buttons_exist = True
                            break
                    except:
                        continue

                # 检查运行指示器是否都消失了
                running_indicators_exist = False
                for selector in running_indicators:
                    try:
                        if page.locator(selector).count() > 0:
                            running_indicators_exist = True
                            break
                    except:
                        continue

                # 如果停止按钮和运行指示器都消失了，认为运行完成
                if not stop_buttons_exist and not running_indicators_exist:
                    print(
                        f"窗口 {window_index}: AI运行完成（停止按钮和运行指示器都已消失）"
                    )
                    break

                # 检查是否有新生成的内容
                try:
                    # 检查是否有AI Studio的响应内容
                    content_elements = page.locator(
                        "ms-prompt-chunk, .text-chunk, ms-text-chunk"
                    )
                    if content_elements.count() > 0:
                        # 检查最后一个元素的文本长度，如果足够长且停止按钮消失，可能已完成
                        last_element_text = content_elements.last.inner_text().strip()
                        if len(last_element_text) > 100 and not stop_buttons_exist:
                            print(
                                f"窗口 {window_index}: 检测到足够长的内容且停止按钮消失，认为完成"
                            )
                            break
                except:
                    pass

                elapsed = time.time() - start_time
                print(f"窗口 {window_index}: 继续等待... ({elapsed:.1f}s)")
                time.sleep(3)

            except Exception as e:
                print(f"窗口 {window_index}: 检查运行状态时出错: {e}")
                break

        # 额外等待确保完全完成
        time.sleep(5)
        print(f"窗口 {window_index}: 运行完成")

    except Exception as e:
        print(f"窗口 {window_index}: 等待过程中出现异常: {e}")
        # 异常情况下也等待一段时间
        page.wait_for_timeout(15000)


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


def process_window(page, window_index, story_data):
    """处理单个窗口的故事生成"""
    try:
        print(f"窗口 {window_index}: 开始处理故事 {story_data['index']}")

        # 导航到AI Studio
        print(f"窗口 {window_index}: 正在打开AI Studio...")
        page.goto("https://aistudio.google.com/u/1/prompts/new_chat")
        page.wait_for_load_state("networkidle")

        # 等待页面加载完成，增加等待时间
        print(f"窗口 {window_index}: 等待页面完全加载...")
        page.wait_for_timeout(8000)

        # 多种可能的文本框选择器
        textarea_selectors = [
            'textarea[aria-label*="Type something"]',
            'textarea[class*="textarea"]',
            'textarea[class*="gmat-body-medium"]',
            "ms-autosize-textarea textarea",
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

        # 输入故事参数
        print(f"窗口 {window_index}: 正在输入故事参数...")

        # 确保元素可见和可交互
        textarea.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)

        # 点击并清空
        textarea.click()
        page.wait_for_timeout(500)

        # 清空现有内容
        page.keyboard.press("Control+a")  # 全选
        page.wait_for_timeout(200)

        # 输入新内容
        textarea.fill(story_data["prompt"])
        page.wait_for_timeout(2000)

        # 验证输入是否成功
        current_value = textarea.input_value()
        if len(current_value) < 50:  # 如果内容太短，可能输入失败
            print(f"窗口 {window_index}: 内容可能输入失败，重试...")
            textarea.clear()
            page.wait_for_timeout(1000)
            textarea.type(story_data["prompt"], delay=50)
            page.wait_for_timeout(1000)

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
        wait_for_ai_completion(page, window_index)

        # 保存生成的故事
        story_dir = "/Volumes/dhl/audio/scifi/full_story/language_code"
        success = save_generated_story(page, story_data["index"], story_dir)

        if success:
            print(f"窗口 {window_index}: 故事 {story_data['index']} 处理完成")
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
    ads_id = "kyencl7"
    close_url = f"http://127.0.0.1:50325/api/v1/browser/stop?user_id={ads_id}"

    try:
        # 获取需要生成的故事参数（一次只生成一个）
        stories_to_generate = get_story_parameters_to_generate(1)

        if not stories_to_generate:
            print("没有需要生成的故事")
            return

        story_data = stories_to_generate[0]  # 只取第一个故事
        print(f"准备生成故事 {story_data['index']}")

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

            # 先创建一个新窗口
            print("正在创建新窗口...")
            new_page = context.new_page()

            # 关闭所有之前的窗口，但保留新创建的窗口
            print("正在关闭之前的窗口...")
            for page in context.pages:
                if page != new_page:
                    try:
                        page.close()
                        print("已关闭一个之前的窗口")
                    except Exception as e:
                        print(f"关闭窗口时出错: {e}")

            # 切换到新窗口并使其获得焦点
            print("正在切换到新窗口...")
            new_page.bring_to_front()

            # 使用新窗口作为主页面
            page = new_page

            print("开始处理单个故事...")

            # 处理单个故事
            success = process_window(page, 1, story_data)

            if success:
                print(f"故事 {story_data['index']} 生成成功！")
            else:
                print(f"故事 {story_data['index']} 生成失败！")

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
