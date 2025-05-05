#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
YouTube Studio自动化上传脚本
使用Playwright自动登录YouTube Studio并发布视频
"""

import os
import sys
import time
import json
import asyncio
import logging
from datetime import datetime
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
    handlers=[logging.StreamHandler(), logging.FileHandler("youtube_upload.log")],
)
logger = logging.getLogger("youtube_uploader")


class YouTubeUploader:
    """YouTube视频上传自动化类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化上传器

        Args:
            config: 包含上传配置的字典
        """
        self.config = config
        self.browser = None
        self.page = None

    async def init_browser(self, headless: bool = False) -> None:
        """
        初始化浏览器

        Args:
            headless: 是否启用无头模式
        """
        playwright = await async_playwright().start()

        # 创建用户数据目录（如果不存在）
        user_data_dir = os.path.expanduser("~/.config/youtube-uploader-profile")
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

        # 设置Cookie以避免部分验证（如果配置文件中有）
        if self.config.get("cookies"):
            for cookie in self.config["cookies"]:
                await self.browser.add_cookies([cookie])

        # 设置超时时间
        self.page.set_default_timeout(120000)  # 120秒

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
        登录YouTube账户

        Returns:
            bool: 登录是否成功
        """
        logger.info("开始登录YouTube...")

        try:
            # 导航到YouTube首页，再去Studio页面，避免直接进入登录页面
            await self.page.goto("https://www.youtube.com/")
            await asyncio.sleep(2)  # 等待页面加载

            # 检查是否已经登录
            is_logged_in = await self.page.query_selector('button[aria-label="创建"]')

            if is_logged_in:
                logger.info("检测到已经登录YouTube")
                await self.page.goto("https://studio.youtube.com/")
                await self.page.wait_for_url(
                    "https://studio.youtube.com/**", timeout=30000
                )
                return True

            # 如果没有登录，点击登录按钮
            await self.page.click('a[aria-label="登录"]')

            # 输入邮箱
            await self.page.wait_for_selector('input[type="email"]', state="visible")
            await self.page.fill('input[type="email"]', self.config["username"])
            await self.page.click("#identifierNext")

            # 等待密码输入框出现并输入密码
            await self.page.wait_for_selector('input[type="password"]', state="visible")
            await asyncio.sleep(2)  # 稍微等待
            await self.page.fill('input[type="password"]', self.config["password"])
            await self.page.click("#passwordNext")

            # 等待重定向到YouTube Studio
            await self.page.wait_for_url("https://studio.youtube.com/**", timeout=60000)

            # 检查是否成功登录
            if "studio.youtube.com" in self.page.url:
                logger.info("成功登录到YouTube Studio")
                # 保存Cookies以备将来使用
                if self.config.get("save_cookies", True):
                    cookies = await self.browser.cookies()
                    try:
                        cookies_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
                        with open(
                            os.path.join(cookies_dir, "youtube_cookies.json"),
                            "w",
                            encoding="utf-8",
                        ) as f:
                            json.dump(cookies, f)
                        logger.info("已保存Cookies")
                    except Exception as e:
                        logger.error(f"保存Cookies失败: {e}")
                return True
            else:
                logger.error(f"登录失败，当前URL: {self.page.url}")
                return False

        except PlaywrightTimeoutError as e:
            logger.error(f"登录超时: {e}")

            # 检查是否需要处理额外验证
            if await self.handle_verification():
                return True

            return False
        except Exception as e:
            logger.error(f"登录过程中出错: {e}")
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
            ]

            for selector in verification_selectors:
                if await self.page.query_selector(selector):
                    logger.warning(f"检测到验证页面: {selector}")

                    # 截图以便分析
                    screenshot_path = f"verification_screenshot_{int(time.time())}.png"
                    await self.page.screenshot(path=screenshot_path)
                    logger.info(f"已保存验证页面截图到: {screenshot_path}")

                    # 提示用户操作
                    logger.info("检测到需要验证，请按以下步骤操作:")
                    logger.info("1. 在正常浏览器中手动登录您的YouTube账号")
                    logger.info(
                        "2. 然后将浏览器cookies导出，保存为youtube_cookies.json"
                    )
                    logger.info(
                        "3. 或者关闭此程序，在脚本中设置use_auth_browser=True后重试"
                    )
                    logger.info("4. 脚本将等待2分钟，如果您完成了手动验证，将继续执行")

                    # 等待用户手动完成验证
                    for _ in range(120):  # 2分钟 = 120秒
                        # 检查是否成功进入YouTube Studio
                        if "studio.youtube.com" in self.page.url:
                            logger.info("验证成功，已进入YouTube Studio")
                            return True

                        # 每秒检查一次
                        await asyncio.sleep(1)

                    logger.error("验证等待超时，请手动完成验证后重试")
                    return False

            return False  # 没有检测到验证页面

        except Exception as e:
            logger.error(f"处理验证过程中出错: {e}")
            return False

    async def upload_video(self) -> bool:
        """
        上传视频文件

        Returns:
            bool: 上传是否成功
        """
        logger.info("开始上传视频...")
        video_path = self.config["video_path"]

        try:
            # 检查文件是否存在
            if not os.path.exists(video_path):
                logger.error(f"视频文件不存在: {video_path}")
                return False

            # 点击创建按钮
            await self.page.click("ytcp-button#create-icon")

            # 点击上传视频选项
            await self.page.click('tp-yt-paper-item:has-text("上传视频")')

            # 等待文件选择对话框出现
            file_input = await self.page.wait_for_selector('input[type="file"]')

            # 上传文件
            await file_input.set_input_files(video_path)

            # 等待上传开始
            await self.page.wait_for_selector("ytcp-uploads-dialog", state="visible")

            logger.info("视频文件已开始上传")

            # 等待上传完成和处理视频
            await self.page.wait_for_selector(
                '.progress-label:has-text("已处理")', state="visible", timeout=300000
            )  # 5分钟超时

            logger.info("视频上传和处理完成")
            return True

        except PlaywrightTimeoutError:
            logger.error("视频上传或处理超时")
            return False
        except Exception as e:
            logger.error(f"上传视频过程中出错: {e}")
            return False

    async def fill_video_details(self) -> bool:
        """
        填写视频详细信息

        Returns:
            bool: 填写是否成功
        """
        logger.info("开始填写视频信息...")

        try:
            # 标题
            title_input = await self.page.wait_for_selector("#title-textarea")
            await title_input.click()
            await title_input.fill("")  # 清空现有内容
            await title_input.fill(self.config["title"])

            # 描述
            description_input = await self.page.wait_for_selector(
                "#description-textarea"
            )
            await description_input.click()
            await description_input.fill(self.config["description"])

            # 标签
            if self.config.get("tags"):
                tags_input = await self.page.wait_for_selector("#tags-container input")
                tags_str = ", ".join(self.config["tags"])
                await tags_input.fill(tags_str)
                await self.page.keyboard.press("Enter")

            # 添加更多设置如需要
            # ...

            logger.info("视频信息填写完成")
            return True

        except Exception as e:
            logger.error(f"填写视频信息时出错: {e}")
            return False

    async def upload_thumbnail(self) -> bool:
        """
        上传视频缩略图

        Returns:
            bool: 上传是否成功
        """
        if not self.config.get("thumbnail_path"):
            logger.info("未指定缩略图，跳过上传缩略图步骤")
            return True

        thumbnail_path = self.config["thumbnail_path"]

        if not os.path.exists(thumbnail_path):
            logger.error(f"缩略图文件不存在: {thumbnail_path}")
            return False

        logger.info("开始上传缩略图...")

        try:
            # 点击缩略图按钮
            thumbnail_button = await self.page.wait_for_selector(
                "#thumbnail-editor button, #upload-thumbnail-button"
            )
            await thumbnail_button.click()

            # 等待文件上传输入框出现
            file_input = await self.page.wait_for_selector('input[type="file"]')

            # 上传文件
            await file_input.set_input_files(thumbnail_path)

            # 等待缩略图上传完成
            await self.page.wait_for_selector(
                '.ytcp-thumbnail-uploader-status:has-text("已上传")',
                state="visible",
                timeout=60000,
            )

            logger.info("缩略图上传成功")
            return True

        except Exception as e:
            logger.error(f"上传缩略图时出错: {e}")
            return False

    async def set_publish_time(self) -> bool:
        """
        设置发布时间

        Returns:
            bool: 设置是否成功
        """
        publish_type = self.config.get("publish_type", "now")

        try:
            # 点击展开可见性设置
            visibility_section = await self.page.wait_for_selector("#toggle-button")
            await visibility_section.click()

            if publish_type == "now":
                # 选择立即发布
                await self.page.click(
                    '#radio-container[name="VISIBILITY_RADIO_PRIVATE"]'
                )
                await self.page.click("tp-yt-paper-radio-button#PUBLIC-radio-button")
                logger.info("设置为立即发布")

            elif publish_type == "schedule":
                # 选择预定发布
                schedule_radio = await self.page.wait_for_selector(
                    '#radio-container[name="VISIBILITY_RADIO_PRIVATE"]'
                )
                await schedule_radio.click()
                schedule_button = await self.page.wait_for_selector(
                    "tp-yt-paper-radio-button#SCHEDULE-radio-button"
                )
                await schedule_button.click()

                # 设置日期和时间
                publish_datetime = datetime.strptime(
                    self.config["publish_time"], "%Y-%m-%d %H:%M"
                )

                # 设置日期
                date_input = await self.page.wait_for_selector(
                    "#datepicker-trigger input"
                )
                await date_input.click()
                await self.page.fill("#input-1", publish_datetime.strftime("%Y-%m-%d"))
                await self.page.keyboard.press("Enter")

                # 设置时间
                time_input = await self.page.wait_for_selector(
                    "#timepicker-local-input"
                )
                await time_input.click()
                await time_input.fill(publish_datetime.strftime("%H:%M"))
                await self.page.keyboard.press("Enter")

                logger.info(f"设置为定时发布: {self.config['publish_time']}")

            else:
                # 默认为私有视频
                private_radio = await self.page.wait_for_selector(
                    '#radio-container[name="VISIBILITY_RADIO_PRIVATE"]'
                )
                await private_radio.click()
                private_button = await self.page.wait_for_selector(
                    "tp-yt-paper-radio-button#PRIVATE-radio-button"
                )
                await private_button.click()
                logger.info("设置为私有视频")

            return True

        except Exception as e:
            logger.error(f"设置发布时间时出错: {e}")
            return False

    async def publish_video(self) -> bool:
        """
        最终发布视频

        Returns:
            bool: 发布是否成功
        """
        logger.info("准备发布视频...")

        try:
            # 点击下一步按钮，直到到达最后的发布页面
            while True:
                next_button = await self.page.query_selector(
                    "#next-button:not([disabled])"
                )
                if not next_button:
                    break

                await next_button.click()
                await asyncio.sleep(1)  # 等待页面加载

            # 点击发布按钮
            publish_button = await self.page.wait_for_selector("#done-button")
            await publish_button.click()

            # 等待发布确认
            success_dialog = await self.page.wait_for_selector(
                "ytcp-uploads-still-processing-dialog, ytcp-uploads-success-dialog",
                state="visible",
            )

            # 点击关闭按钮
            close_button = await self.page.wait_for_selector(
                "ytcp-button.ytcp-uploads-still-processing-dialog-close-button, ytcp-button.ytcp-uploads-success-dialog-close-button"
            )
            await close_button.click()

            logger.info("视频已成功发布!")
            return True

        except Exception as e:
            logger.error(f"发布视频时出错: {e}")
            return False

    async def close(self) -> None:
        """关闭浏览器和相关资源"""
        if self.browser:
            await self.browser.close()
            logger.info("浏览器已关闭")

    async def run(self) -> bool:
        """
        运行完整上传流程

        Returns:
            bool: 整个流程是否成功
        """
        success = False

        try:
            # 初始化浏览器
            await self.init_browser(headless=self.config.get("headless", False))

            # 登录
            if not await self.login():
                logger.error("登录失败，终止上传流程")
                return False

            # 上传视频
            if not await self.upload_video():
                logger.error("上传视频失败，终止上传流程")
                return False

            # 填写视频信息
            if not await self.fill_video_details():
                logger.error("填写视频信息失败，尝试继续执行")

            # 上传缩略图
            if self.config.get("thumbnail_path") and not await self.upload_thumbnail():
                logger.error("上传缩略图失败，尝试继续执行")

            # 设置发布时间
            if not await self.set_publish_time():
                logger.error("设置发布时间失败，尝试继续执行")

            # 发布视频
            if not await self.publish_video():
                logger.error("发布视频失败")
                return False

            logger.info("视频上传发布流程全部完成!")
            success = True

        except Exception as e:
            logger.error(f"上传流程中出现未处理的错误: {e}")
            success = False

        finally:
            if not self.config.get("keep_browser_open", False):
                await self.close()

        return success


async def main():
    """主函数"""
    # 加载配置
    config_path = sys.argv[1] if len(sys.argv) > 1 else "youtube_config.json"

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"无法加载配置文件 {config_path}: {e}")
        return 1

    # 尝试加载保存的cookies
    cookies_path = os.path.join(
        os.path.dirname(os.path.abspath(sys.argv[0])), "youtube_cookies.json"
    )
    if os.path.exists(cookies_path) and not config.get("ignore_cookies"):
        try:
            with open(cookies_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
                config["cookies"] = cookies
                logger.info("已加载保存的Cookies")
        except Exception as e:
            logger.error(f"加载Cookies失败: {e}")

    # 创建上传器并运行
    uploader = YouTubeUploader(config)
    success = await uploader.run()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
