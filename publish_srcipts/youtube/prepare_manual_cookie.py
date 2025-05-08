#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
手动输入方式准备 YouTube Cookie 的工具
"""

import os
import sys
import asyncio
import getpass
import logging
import json
import re
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("manual_cookie.log")],
)
logger = logging.getLogger("manual_cookie")


class YouTubeCookieManager:
    """YouTube Cookie 管理类"""

    def __init__(self, username, password, browser_type="firefox"):
        """
        初始化 Cookie 管理器

        Args:
            username: YouTube 账户的用户名
            password: YouTube 账户的密码
            browser_type: 浏览器类型，默认为 firefox
        """
        self.username = username
        self.password = password
        self.browser_type = browser_type
        self.browser = None
        self.page = None
        self.config = {
            "username": username,
            "password": password,
            "force_login": False,
            "headless": False,
            "browser_type": browser_type,
        }

    async def init_browser(self, headless=False):
        """
        初始化浏览器

        Args:
            headless: 是否使用无头模式
        """
        playwright = await async_playwright().start()

        # 创建用户数据目录
        user_data_dir = os.path.expanduser(
            f"~/.config/youtube-cookie-manager-profile-firefox-{self.username}"
        )
        os.makedirs(user_data_dir, exist_ok=True)

        # Firefox 浏览器设置 - 移除不适用于Firefox的Blink相关参数
        firefox_args = [
            "--no-sandbox",
            "--disable-extensions",
            "--disable-notifications",
            "--disable-popup-blocking",
            "--disable-dev-shm-usage",
        ]

        # 使用 Firefox 浏览器
        self.browser = await playwright.firefox.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            slow_mo=100,  # 增加慢速操作时间，确保页面有足够时间加载
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            accept_downloads=True,
            ignore_https_errors=True,
            java_script_enabled=True,
            args=firefox_args,
        )

        # 创建页面
        self.page = await self.browser.new_page()

        # 设置更逼真的行为
        await self.page.set_extra_http_headers(
            {
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "sec-ch-ua": '"Firefox";v="124", "Not-A.Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
            }
        )

        # 设置超时时间
        self.page.set_default_timeout(120000)  # 120秒

        # 修改navigator属性，调整为Firefox适用的脚本
        await self.page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            // 修改语言检测
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en-US', 'en'],
            });
            
            // 修改硬件并发性
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8,
            });
            
            // 修改设备内存
            if (navigator.deviceMemory !== undefined) {
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8,
                });
            }
        """
        )

    async def manual_login(self):
        """
        执行手动登录流程

        Returns:
            bool: 登录是否成功
        """
        logger.info("开始手动登录流程...")

        try:
            # 清理现有cookie
            await self.browser.clear_cookies()
            logger.info("已清理现有Cookie")

            # 直接导航到Google登录页面
            logger.info("导航到Google登录页面...")
            await self.page.goto(
                "https://accounts.google.com/ServiceLogin?service=youtube",
                timeout=60000,
                wait_until="networkidle",  # 等待网络活动停止
            )

            await asyncio.sleep(3)  # 等待页面完全加载

            # 确认当前是否在登录页面
            current_url = self.page.url
            if "accounts.google.com" not in current_url:
                logger.warning(f"未成功跳转到Google登录页面，当前URL是: {current_url}")
                logger.info("尝试直接访问YouTube...")

                # 如果未成功跳转到登录页面，尝试访问YouTube首页
                await self.page.goto(
                    "https://www.youtube.com/", timeout=60000, wait_until="networkidle"
                )
                await asyncio.sleep(3)

                # 查找并点击登录按钮 (尝试多种可能的选择器)
                login_selectors = [
                    'a[href^="https://accounts.google.com/ServiceLogin"]',
                    'a:has-text("登录")',
                    'a:has-text("Sign in")',
                    'yt-formatted-string:has-text("登录")',
                    'yt-formatted-string:has-text("Sign in")',
                ]

                login_button = None
                for selector in login_selectors:
                    login_button = await self.page.query_selector(selector)
                    if login_button:
                        logger.info(f"使用选择器 '{selector}' 找到登录按钮")
                        break

                if login_button:
                    logger.info("找到登录按钮，点击开始登录...")
                    await login_button.click()
                    # 等待跳转完成
                    await asyncio.sleep(5)
                else:
                    logger.warning("无法找到登录按钮，尝试直接导航到登录页面")
                    await self.page.goto(
                        "https://accounts.google.com/ServiceLogin?service=youtube",
                        timeout=60000,
                        wait_until="networkidle",
                    )

            # 等待用户手动登录
            logger.info("请在浏览器窗口中手动完成登录流程...")
            logger.info("提示: 完成登录后，您将被重定向回YouTube。")
            logger.info("     系统将等待最多5分钟，完成后会自动继续。")

            # 等待重定向到YouTube主页或YouTube studio页面
            try:
                # 使用正则表达式匹配多种可能的URL模式
                await self.page.wait_for_url(
                    re.compile(
                        r"https://(www|studio)\.youtube\.com/|https://myaccount\.google\.com/"
                    ),
                    timeout=300000,
                )
                logger.info(f"成功重定向到: {self.page.url}")
            except PlaywrightTimeoutError:
                try:
                    # 检查当前URL，判断是否已经在正确的页面
                    current_url = self.page.url
                    if (
                        "youtube.com" in current_url
                        or "myaccount.google.com" in current_url
                    ):
                        logger.info(f"已在预期页面: {current_url}")
                    else:
                        logger.error(f"未重定向到预期页面，当前URL: {current_url}")
                        return False
                except Exception as e:
                    logger.error(f"等待登录超时，错误: {e}")
                    return False

            # 额外等待，确保完全登录
            await asyncio.sleep(5)

            # 检查是否登录成功 (尝试多种可能的选择器)
            avatar_selectors = [
                'button[aria-label="创建"]',
                'button[aria-label="Create"]',
                'button[aria-label="创建内容"]',
                'button[aria-label="Create content"]',
                "yt-icon-button#avatar-btn",
                "img#avatar-image",
                'img#img.style-scope.yt-img-shadow[alt="Avatar image"]',
                "button#avatar-btn",
            ]

            login_successful = False
            for selector in avatar_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    login_successful = True
                    logger.info(f"使用选择器 '{selector}' 检测到登录成功")
                    break

            # 如果没有找到预期元素，直接访问YouTube并重新检查
            if not login_successful:
                logger.info("未检测到登录成功的标志，尝试直接访问YouTube并重新检查...")
                await self.page.goto("https://www.youtube.com/", timeout=60000)
                await asyncio.sleep(3)

                # 重新检查登录状态
                for selector in avatar_selectors:
                    element = await self.page.query_selector(selector)
                    if element:
                        login_successful = True
                        logger.info(f"二次检查: 使用选择器 '{selector}' 检测到登录成功")
                        break

            if login_successful:
                logger.info("手动登录成功")
                # 保存Cookie
                await self.save_cookies()
                return True
            else:
                logger.error("手动登录似乎未成功")
                return False

        except Exception as e:
            logger.error(f"手动登录过程中出错: {e}")
            return False

    async def save_cookies(self):
        """保存当前的Cookie到文件"""
        cookies_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "cookies"
        )

        # 确保目录存在
        os.makedirs(cookies_dir, exist_ok=True)

        # 生成cookie文件路径
        cookie_path = os.path.join(
            cookies_dir, f"youtube_cookies_firefox_{self.username.split('@')[0]}.json"
        )

        # 获取当前的Cookie
        cookies = await self.browser.cookies()

        # 保存到文件
        try:
            with open(cookie_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger.info(f"成功保存Cookie到: {cookie_path}")
            return True
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")
            return False

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            logger.info("浏览器已关闭")

    async def run(self):
        """
        运行Cookie管理流程

        Returns:
            bool: 操作是否成功
        """
        try:
            # 初始化浏览器
            await self.init_browser(headless=self.config.get("headless", False))

            # 执行手动登录
            success = await self.manual_login()

            return success
        except Exception as e:
            logger.error(f"运行过程中出错: {e}")
            return False
        finally:
            if not self.config.get("keep_browser_open", False):
                await self.close()


async def prepare_cookie_manually() -> bool:
    """
    通过手动输入账户信息准备 cookie

    Returns:
        bool: 操作是否成功
    """
    try:
        print("=" * 60)
        print("YouTube Cookie 手动准备工具")
        print("=" * 60)
        print("这个工具将帮助您手动准备 YouTube Cookie，避免频繁的验证码验证")
        print("请输入您的 YouTube 账户信息:")

        # 获取用户名
        username = input("请输入 Gmail 邮箱: ")
        if not username:
            logger.error("邮箱不能为空")
            return False

        # 获取密码
        password = getpass.getpass(f"请输入 {username} 的密码: ")
        if not password:
            logger.error("密码不能为空")
            return False

        # 询问是否强制登录
        force_login = input("是否强制重新登录? (y/n，默认n): ").lower() == "y"

        # 询问是否使用无头模式
        headless = (
            input("是否使用无头模式（不显示浏览器界面）? (y/n，默认n): ").lower() == "y"
        )

        print("\n开始准备 Cookie，请稍等...")

        # 创建 Cookie 管理器并运行
        cookie_manager = YouTubeCookieManager(
            username=username,
            password=password,
            browser_type="firefox",  # 明确指定使用Firefox浏览器
        )

        # 更新配置
        cookie_manager.config.update(
            {
                "force_login": force_login,
                "headless": headless,
            }
        )

        # 运行 Cookie 管理器
        success = await cookie_manager.run()

        if success:
            print("\n✅ Cookie 准备成功!")
            print(
                f"Cookie 已保存到: cookies/youtube_cookies_firefox_{username.split('@')[0]}.json"
            )
            return True
        else:
            print("\n❌ Cookie 准备失败，请查看日志获取详细信息")
            return False

    except Exception as e:
        logger.error(f"准备 Cookie 过程中出错: {e}")
        print(f"\n❌ 出现错误: {e}")
        return False


async def main():
    """主函数"""
    # 确保 cookies 目录存在
    cookies_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies")
    os.makedirs(cookies_dir, exist_ok=True)

    # 运行手动准备流程
    success = await prepare_cookie_manually()

    # 程序结束提示
    if success:
        print("\n操作完成，您现在可以使用 youtube_upload_test.py 上传视频了!")
    else:
        print("\n操作失败，请检查错误并重试")

    # 按任意键退出
    input("\n按 Enter 键退出程序...")

    return 0 if success else 1


if __name__ == "__main__":
    import time

    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(1)
