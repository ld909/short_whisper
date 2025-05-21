import requests
import time
import json
import sys
import urllib3
from playwright.sync_api import sync_playwright


def get_adspower_info(ads_id):
    open_url = f"http://local.adspower.net:50325/api/v1/browser/start?user_id={ads_id}"

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
    # 启动AdsPower浏览器
    ads_id = "kq316tr"
    close_url = f"http://local.adspower.net:50325/api/v1/browser/stop?user_id={ads_id}"

    try:
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

            # 获取已有页面或创建新页面
            if not context.pages:
                page = context.new_page()
                print("在现有上下文中创建了新页面。")
            else:
                page = context.pages[0]  # 使用已存在的第一个页面
                print("使用上下文中的现有页面。")

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

            # 上传测试文件
            print("正在上传测试文件 ./t.mp4...")
            file_input = page.locator('input[type="file"][name="Filedata"]')
            file_input.set_input_files("./t.mp4")
            print("文件已上传")

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
            title_input.fill("test_title")  # 输入标题
            print("已输入标题: test_title")

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
            desc_input.fill("test_desc")  # 输入描述
            print("已输入描述: test_desc")

            # 等待输入完成
            page.wait_for_timeout(1000)  # 等待1秒确保输入已完成

            # 上传缩略图
            print("正在上传缩略图...")
            thumbnail_input = page.locator('input#file-loader[type="file"]')
            thumbnail_input.set_input_files("./t1.png")
            print("缩略图已上传")

            # 等待缩略图上传完成
            page.wait_for_timeout(3000)  # 等待2秒确保上传完成

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
