#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
YouTube Cookie 管理工具
用于管理不同 Gmail 账户的 YouTube Cookie，避免频繁验证
"""

import os
import json
import logging
import argparse
import asyncio
import getpass
from pathlib import Path
from typing import Dict, List, Optional, Any

from playwright.async_api import (
    async_playwright,
    Page,
    Browser,
    BrowserContext,
    TimeoutError as PlaywrightTimeoutError,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("youtube_cookie_manager.log"),
    ],
)
logger = logging.getLogger("youtube_cookie_manager")


class YouTubeCookieManager:
    """YouTube Cookie 管理类"""

    def __init__(
        self, config_path: str = None, username: str = None, password: str = None
    ):
        """
        初始化 Cookie 管理器

        Args:
            config_path: 配置文件路径
            username: 用户名（可选，优先于配置文件）
            password: 密码（可选，优先于配置文件）
        """
        self.config_path = config_path
        self.config = {}

        # 如果提供了配置文件路径，先尝试加载
        if config_path:
            self.config = self._load_config()

        # 如果提供了用户名和密码，覆盖配置文件中的值
        if username:
            self.config["username"] = username
        if password:
            self.config["password"] = password

        # 确定 cookies 目录
        if config_path:
            self.cookies_dir = os.path.join(
                os.path.dirname(os.path.abspath(config_path)), "cookies"
            )
        else:
            # 如果没有配置文件，使用脚本当前目录
            self.cookies_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "cookies"
            )

        self.browser = None
        self.page = None

        # 确保 cookies 目录存在
        os.makedirs(self.cookies_dir, exist_ok=True)

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"无法加载配置文件 {self.config_path}: {e}")
            return {}

    def _get_cookie_path(self) -> str:
        """获取 cookie 文件路径"""
        # 使用用户名作为 cookie 文件名的一部分
        username = self.config.get("username", "").split("@")[0]
        return os.path.join(self.cookies_dir, f"youtube_cookies_{username}.json")

    async def init_browser(self, headless: bool = False) -> None:
        """
        初始化浏览器

        Args:
            headless: 是否启用无头模式
        """
        playwright = await async_playwright().start()

        # 创建用户数据目录（如果不存在）
        username = self.config.get("username", "").split("@")[0]
        user_data_dir = os.path.expanduser(
            f"~/.config/youtube-uploader-profile-{username}"
        )
        os.makedirs(user_data_dir, exist_ok=True)

        # 使用持久化上下文代替普通浏览器
        self.browser = await playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            slow_mo=100,  # 放慢操作，避免被检测为机器人
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            accept_downloads=True,
            ignore_https_errors=True,
            java_script_enabled=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )

        # 创建页面
        self.page = await self.browser.new_page()

        # 设置Cookie（如果有）
        cookie_path = self._get_cookie_path()
        if os.path.exists(cookie_path):
            try:
                with open(cookie_path, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                    await self.browser.add_cookies(cookies)
                    logger.info(f"已加载 Cookie: {cookie_path}")
            except Exception as e:
                logger.error(f"加载 Cookie 失败: {e}")

        # 设置超时时间
        self.page.set_default_timeout(60000)  # 60秒

        # 修改navigator.webdriver属性来逃避机器人检测
        await self.page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            // 隐藏自动化标志
            window.navigator.chrome = {
                runtime: {},
            };
            
            // 修改语言检测
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en-US', 'en'],
            });
            
            // 修改硬件并发性
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8,
            });
            
            // 修改设备内存
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
            });
        """
        )

    async def login(self) -> bool:
        """
        登录 YouTube 账户并保存 Cookie

        Returns:
            bool: 登录是否成功
        """
        logger.info(f"开始登录 YouTube 账号: {self.config['username']}...")

        try:
            # 导航到 YouTube 首页
            await self.page.goto("https://www.youtube.com/")
            await asyncio.sleep(2)  # 等待页面加载

            # 检查是否已经登录
            is_logged_in = await self.page.query_selector('button[aria-label="创建"]')

            if is_logged_in:
                logger.info("检测到已经登录 YouTube")

                # 如果配置中设置了强制登录，则先退出当前账号
                if self.config.get("force_login", False):
                    logger.info("配置中设置了强制登录，尝试退出当前账号")

                    # 点击头像打开菜单
                    await self.page.click("button#avatar-btn")
                    await asyncio.sleep(1)

                    # 点击退出选项
                    sign_out_button = await self.page.query_selector(
                        'a[href="/logout"]'
                    )
                    if sign_out_button:
                        await sign_out_button.click()
                        await asyncio.sleep(3)  # 等待退出
                        logger.info("已退出当前账号")

                        # 刷新页面
                        await self.page.goto("https://www.youtube.com/")
                        await asyncio.sleep(2)
                    else:
                        logger.warning("未找到退出按钮，继续使用当前登录状态")
                        await self.save_cookies()
                        return True
                else:
                    # 已登录且不需要强制登录，直接保存 cookie
                    await self.save_cookies()
                    return True

            # 如果没有登录或已退出，点击登录按钮
            login_button = await self.page.query_selector('a[aria-label="登录"]')
            if login_button:
                await login_button.click()
            else:
                logger.warning("未找到登录按钮，尝试直接导航到登录页面")
                await self.page.goto("https://accounts.google.com/signin")

            # 输入邮箱
            await self.page.wait_for_selector('input[type="email"]', state="visible")
            await self.page.fill('input[type="email"]', self.config["username"])
            await self.page.click("#identifierNext")

            # 等待密码输入框出现并输入密码
            await self.page.wait_for_selector('input[type="password"]', state="visible")
            await asyncio.sleep(2)  # 稍微等待
            await self.page.fill('input[type="password"]', self.config["password"])
            await self.page.click("#passwordNext")

            # 等待可能出现的验证页面
            logger.info("等待可能的额外验证步骤...")

            # 检查是否有验证步骤
            if await self.handle_verification():
                logger.info("验证步骤处理完成")

            # 等待重定向到 YouTube
            for _ in range(60):  # 最多等待60秒
                if "youtube.com" in self.page.url:
                    break
                await asyncio.sleep(1)

            # 访问 YouTube Studio
            await self.page.goto("https://studio.youtube.com/")

            # 等待加载完成
            try:
                await self.page.wait_for_url(
                    "https://studio.youtube.com/**", timeout=30000
                )
            except PlaywrightTimeoutError:
                logger.warning("等待 YouTube Studio 加载超时，但将继续执行")

            # 检查是否成功登录
            if "studio.youtube.com" in self.page.url:
                logger.info(f"成功登录 YouTube Studio: {self.config['username']}")
                await self.save_cookies()
                return True
            else:
                logger.error(f"登录失败，当前 URL: {self.page.url}")
                return False

        except PlaywrightTimeoutError as e:
            logger.error(f"登录超时: {e}")
            return False
        except Exception as e:
            logger.error(f"登录过程中出错: {e}")
            return False

    async def save_cookies(self) -> bool:
        """
        保存当前会话的 Cookie

        Returns:
            bool: 保存是否成功
        """
        try:
            cookies = await self.browser.cookies()
            cookie_path = self._get_cookie_path()

            with open(cookie_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)

            logger.info(f"已保存 Cookie 到: {cookie_path}")
            return True
        except Exception as e:
            logger.error(f"保存 Cookie 失败: {e}")
            return False

    async def verify_cookies(self) -> bool:
        """
        验证 Cookie 是否有效

        Returns:
            bool: Cookie 是否有效
        """
        try:
            # 访问 YouTube Studio
            await self.page.goto("https://studio.youtube.com/")
            await asyncio.sleep(3)  # 等待页面加载

            # 检查是否需要登录
            login_required = await self.page.query_selector('input[type="email"]')

            if login_required:
                logger.info("Cookie 无效或已过期，需要重新登录")
                return False
            else:
                logger.info("Cookie 有效，无需重新登录")
                return True
        except Exception as e:
            logger.error(f"验证 Cookie 时出错: {e}")
            return False

    async def handle_verification(self) -> bool:
        """
        处理可能的额外验证步骤

        Returns:
            bool: 验证是否成功处理
        """
        try:
            # 检查是否出现了验证页面或不安全浏览器提示
            verification_selectors = [
                "text=验证您的身份",
                "text=Verify it's you",
                "text=This browser or app may not be secure",
                "text=此浏览器或应用可能不安全",
                "text=Try using a different browser",
                "text=尝试使用其他浏览器",
                'form[action="/signin/v2/challenge/ipp"]',
                'input[aria-label="输入验证码"]',
                'input[aria-label="Enter the code"]',
            ]

            for selector in verification_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        logger.warning(f"检测到验证页面: {selector}")

                        # 截图以便分析
                        screenshot_path = f"verification_screenshot_{self.config['username'].split('@')[0]}_{int(time.time())}.png"
                        await self.page.screenshot(path=screenshot_path)
                        logger.info(f"已保存验证页面截图到: {screenshot_path}")

                        # 提示用户手动验证
                        logger.info(
                            "====================================================="
                        )
                        logger.info("检测到需要验证码，请在浏览器中完成验证!")
                        logger.info("完成验证后，脚本将自动继续执行")
                        logger.info(
                            "====================================================="
                        )

                        # 等待用户完成验证
                        for _ in range(300):  # 最多等待5分钟
                            if (
                                "youtube.com" in self.page.url
                                or "myaccount.google.com" in self.page.url
                            ):
                                logger.info("验证成功完成")
                                return True

                            # 每2秒检查一次
                            await asyncio.sleep(2)

                        logger.warning("等待验证超时，请在验证完成后重新运行")
                        return False
                except Exception:
                    continue

            # 没有检测到验证页面
            return True

        except Exception as e:
            logger.error(f"处理验证过程中出错: {e}")
            return False

    async def close(self) -> None:
        """关闭浏览器和相关资源"""
        if self.browser:
            await self.browser.close()
            logger.info("浏览器已关闭")

    async def run(self) -> bool:
        """
        运行 Cookie 管理流程

        Returns:
            bool: 整个流程是否成功
        """
        success = False

        try:
            # 初始化浏览器
            await self.init_browser(headless=self.config.get("headless", False))

            # 验证当前 Cookie
            if await self.verify_cookies():
                logger.info("Cookie 验证成功，保存当前有效 Cookie")
                await self.save_cookies()
                success = True
            else:
                # 如果 Cookie 无效，尝试登录
                logger.info("Cookie 无效，尝试重新登录")
                if await self.login():
                    logger.info("重新登录并保存 Cookie 成功")
                    success = True
                else:
                    logger.error("登录失败，请检查用户名和密码或手动完成验证")
                    success = False

        except Exception as e:
            logger.error(f"Cookie 管理流程中出现未处理的错误: {e}")
            success = False

        finally:
            await self.close()

        return success


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="YouTube Cookie 管理工具")
    parser.add_argument("--config", help="配置文件路径（可选）")
    parser.add_argument("--username", help="YouTube 账户邮箱（优先于配置文件）")
    parser.add_argument("--force", action="store_true", help="强制重新登录")
    parser.add_argument(
        "--headless", action="store_true", help="无头模式（不显示浏览器界面）"
    )

    args = parser.parse_args()

    # 配置对象，用于传递给 YouTubeCookieManager
    config = {"force_login": args.force, "headless": args.headless}

    # 获取用户名（从命令行或手动输入）
    username = args.username
    if not username:
        if args.config:
            # 如果指定了配置文件但没有指定用户名，先尝试从配置文件加载
            try:
                with open(args.config, "r", encoding="utf-8") as f:
                    file_config = json.load(f)
                    username = file_config.get("username")
            except Exception as e:
                logger.error(f"无法从配置文件加载用户名: {e}")

        # 如果仍然没有用户名，请求用户输入
        if not username:
            username = input("请输入 YouTube 账户邮箱: ")

    # 设置用户名
    config["username"] = username

    # 获取密码（不从命令行参数接收，而是手动输入）
    password = getpass.getpass(f"请输入 {username} 的密码: ")
    config["password"] = password

    # 创建 Cookie 管理器
    cookie_manager = YouTubeCookieManager(
        config_path=args.config, username=username, password=password
    )

    # 将命令行参数传递给配置
    cookie_manager.config.update(config)

    # 运行 Cookie 管理器
    success = await cookie_manager.run()

    return 0 if success else 1


if __name__ == "__main__":
    import time
    import sys

    exit_code = asyncio.run(main())
    sys.exit(exit_code)
