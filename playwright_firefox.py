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