#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：使用 Playwright 自动化打开多个 Google AI Studio 页面
作用：批量打开5个Chrome浏览器页面，每个页面都访问Google AI Studio的新聊天界面

输入要求：
- 无需输入文件或目录
- 需要系统已安装 Google Chrome 浏览器
- 需要安装 playwright 依赖：pip install playwright

输出效果：
- 打开5个Chrome浏览器标签页
- 每个页面访问：https://aistudio.google.com/prompts/new_chat
- 浏览器数据临时存储在：/tmp/playwright_chrome_data

使用方法：
python playwright_firefox.py

注意事项：
- 脚本会以非无头模式运行（浏览器可见）
- 需要手动按回车键才会关闭浏览器
- Chrome路径默认为 /usr/bin/google-chrome，可根据实际情况修改
"""

import asyncio
from playwright.async_api import async_playwright

async def main():
    # 启动Playwright
    async with async_playwright() as p:
        # 连接到已安装的Chrome浏览器
        # 注意：需要提供Chrome可执行文件的路径
        # 下面是Linux系统上Chrome的一个常见路径，根据实际情况可能需要修改
        chrome_path = "/usr/bin/google-chrome"
        
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="/tmp/playwright_chrome_data",
            executable_path=chrome_path,
            headless=False  # 确保浏览器可见
        )
        
        # 打开5个页面并访问Google AI Studio
        pages = []
        for i in range(5):
            print(f"正在打开第 {i+1} 个页面...")
            if i == 0:
                # 使用当前页面
                page = browser.pages[0]
            else:
                # 创建新页面
                page = await browser.new_page()
            
            # 导航到指定URL
            await page.goto("https://aistudio.google.com/prompts/new_chat")
            pages.append(page)
            
        print("已成功打开全部5个页面")
        
        # 保持浏览器打开，直到用户按下回车键
        input("请按回车键关闭浏览器...")
        
        # 关闭浏览器
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 