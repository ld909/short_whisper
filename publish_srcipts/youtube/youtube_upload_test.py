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
from pathlib import Path
import argparse
import random
import glob  # 添加glob库

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

    def __init__(self, config):
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

        # 创建Chrome配置副本目录而非直接使用Chrome目录
        username = self.config.get("username", "dhliu.eth")
        user_data_dir = os.path.expanduser(
            f"~/.config/youtube-uploader-chrome-{username}"
        )
        os.makedirs(user_data_dir, exist_ok=True)

        logger.info(f"使用Chrome用户数据目录副本: {user_data_dir}")

        # Chrome浏览器设置
        chrome_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-web-security",
            "--disable-extensions",
            "--disable-notifications",
            "--disable-popup-blocking",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ]

        # 使用已安装的Chrome浏览器
        try:
            self.browser = await playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=headless,
                slow_mo=50,  # 调整速度，不要太慢
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                accept_downloads=True,
                ignore_https_errors=True,
                args=chrome_args,
            )
            logger.info("成功启动Chrome浏览器")
        except Exception as e:
            logger.error(f"启动Chrome浏览器失败: {e}")
            # 尝试备选方案：使用已安装的Chrome
            logger.info("尝试使用已安装的Chrome浏览器...")
            self.browser = await playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",  # 使用已安装的Chrome
                headless=headless,
                slow_mo=50,
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                accept_downloads=True,
                args=chrome_args,
            )
            logger.info("成功使用已安装的Chrome浏览器")

        # 创建页面
        self.page = await self.browser.new_page()

        # 设置更逼真的行为
        await self.page.set_extra_http_headers(
            {
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "sec-ch-ua": '"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
            }
        )

        # 修改navigator.webdriver属性来逃避机器人检测
        await self.page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            // 隐藏自动化标志
            delete window.navigator.__proto__.webdriver;
            
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
            
            // 修改连接信息
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    rtt: 50,
                    downlink: 10.0,
                    saveData: false
                }),
            });
            
            // 修改用户激活状态
            Object.defineProperty(navigator, 'userActivation', {
                get: () => ({
                    hasBeenActive: true,
                    isActive: true
                }),
            });
            
            // 阻止检测Webdriver
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    const plugins = [];
                    for (let i = 0; i < 5; i++) {
                        plugins.push({
                            name: `Plugin ${i}`,
                            description: `Description ${i}`,
                            filename: `filename${i}.dll`,
                            length: 1,
                            item: function() { return this; }
                        });
                    }
                    return plugins;
                }
            });
        """
        )

    async def login_with_cookies(self) -> bool:
        """
        使用Cookie登录YouTube账户

        Returns:
            bool: 登录是否成功
        """
        logger.info("开始使用Chrome配置登录YouTube...")

        try:
            # 1. 先进入YouTube主页
            await self.page.goto("https://www.youtube.com/", timeout=60000)

            # 检查是否需要登录
            await asyncio.sleep(3)

            # 检查是否已经登录
            is_logged_in = (
                await self.page.query_selector('button[aria-label="创建"]')
                or await self.page.query_selector('button[aria-label="Create"]')
                or await self.page.query_selector("yt-icon-button#avatar-btn")
                or await self.page.query_selector("img#avatar-image")
            )

            if is_logged_in:
                logger.info("已成功登录YouTube")
                return True
            else:
                logger.info("未检测到登录状态，需要手动登录")
                # 如果未登录，调用手动登录流程
                return await self.manual_login()

        except Exception as e:
            logger.error(f"登录过程中出错: {e}")
            return False

    async def switch_to_channel(self, channel_type: str = "channel_ko") -> bool:
        """
        切换到指定的频道

        Args:
            channel_type: 频道类型，对应配置文件中的键名

        Returns:
            bool: 切换是否成功
        """
        logger.info(f"正在切换到频道: {channel_type}")

        try:
            # 获取频道URL
            channel_url = self.config.get(channel_type)
            if not channel_url:
                logger.error(f"配置中未找到频道URL: {channel_type}")
                return False

            # 先确保我们在studio.youtube.com
            if "studio.youtube.com" not in self.page.url:
                await self.page.goto("https://studio.youtube.com/")
                await asyncio.sleep(2)  # 等待页面加载

            # 直接导航到频道URL
            await self.page.goto(channel_url)
            await asyncio.sleep(3)  # 等待页面加载

            # 检查是否成功切换
            current_url = self.page.url
            channel_id = channel_url.split("/channel/")[1]

            if channel_id in current_url:
                logger.info(f"成功切换到频道: {channel_type}")
                return True
            else:
                logger.error(
                    f"切换频道失败，当前URL: {current_url}，期望包含: {channel_id}"
                )

                # 尝试再次切换
                logger.info("尝试再次切换频道...")
                await self.page.goto(channel_url)
                await asyncio.sleep(5)  # 多等待一些时间

                current_url = self.page.url
                if channel_id in current_url:
                    logger.info(f"第二次尝试成功切换到频道: {channel_type}")
                    return True
                else:
                    logger.error(f"再次切换频道失败，当前URL: {current_url}")
                    return False

        except Exception as e:
            logger.error(f"切换频道时出错: {e}")
            return False

    def get_random_mp4(self, directory="/Volumes/dhl/buda_videos_youtube/mp4_clips"):
        """
        从指定目录随机选择一个MP4文件

        Args:
            directory: 包含MP4文件的目录路径

        Returns:
            str: 随机选择的MP4文件的完整路径，如果没有找到文件则返回None
        """
        # 获取目录中所有MP4文件
        mp4_files = glob.glob(os.path.join(directory, "*.mp4"))

        # 如果找到MP4文件，随机选择一个
        if mp4_files:
            random_file = random.choice(mp4_files)
            logger.info(f"随机选择MP4文件: {random_file}")
            return random_file
        else:
            logger.error(f"在目录 {directory} 中未找到MP4文件")
            return None

    async def upload_video(self) -> bool:
        """
        上传视频文件

        Returns:
            bool: 上传是否成功
        """
        logger.info("开始上传视频...")

        # 使用随机选择的MP4文件替换配置中的视频路径
        random_video = self.get_random_mp4()
        if random_video:
            self.config["video_path"] = random_video

        video_path = self.config["video_path"]

        try:
            # 检查文件是否存在
            if not os.path.exists(video_path):
                logger.error(f"视频文件不存在: {video_path}")
                return False

            # 1. 查找并点击包含"Create"的按钮
            create_button = await self.page.wait_for_selector(
                'button:has-text("Create")', timeout=10000
            )
            if not create_button:
                create_button = await self.page.wait_for_selector(
                    'button[aria-label="Create"]', timeout=10000
                )
            if not create_button:
                create_button = await self.page.wait_for_selector(
                    'button:has-text("创建")', timeout=10000
                )

            if not create_button:
                logger.error("无法找到'Create'按钮")
                return False

            await create_button.click()
            logger.info("已点击'Create'按钮")
            await asyncio.sleep(1)  # 等待菜单弹出

            # 2. 等待菜单弹出，点击包含"Upload videos"的选项
            upload_option = await self.page.wait_for_selector(
                'yt-formatted-string.item-text:has-text("Upload videos")', timeout=10000
            )
            if not upload_option:
                upload_option = await self.page.wait_for_selector(
                    'ytcp-ve:has(yt-formatted-string:has-text("Upload videos"))',
                    timeout=10000,
                )
            if not upload_option:
                upload_option = await self.page.wait_for_selector(
                    'a:has-text("Upload videos")', timeout=10000
                )
            if not upload_option:
                upload_option = await self.page.wait_for_selector(
                    'span:has-text("上传视频")', timeout=10000
                )
            if not upload_option:
                upload_option = await self.page.wait_for_selector(
                    'a:has-text("上传视频")', timeout=10000
                )
            if not upload_option:
                upload_option = await self.page.wait_for_selector(
                    'yt-formatted-string:has-text("上传视频")', timeout=10000
                )

            if not upload_option:
                logger.error("无法找到'Upload videos'选项")
                return False

            await upload_option.click()
            logger.info("已点击'Upload videos'选项")

            # 3. 等待文件上传页面出现并准备文件输入框
            logger.info("等待文件上传页面准备就绪...")
            await asyncio.sleep(2)  # 给页面一些时间加载

            # 查找文件输入框
            file_input = await self.page.wait_for_selector(
                'input[type="file"]',
                timeout=10000,
                state="attached",  # 使用attached状态，因为文件输入通常是隐藏的
            )

            if not file_input:
                logger.error("无法找到文件输入框")
                return False

            # 上传文件
            logger.info(f"准备上传视频文件: {video_path}")
            await file_input.set_input_files(video_path)
            logger.info(f"已设置视频文件: {video_path}")

            # 等待上传开始并完成
            logger.info("视频文件已上传成功，请在浏览器中继续操作...")
            return True

        except Exception as e:
            logger.error(f"上传视频过程中出错: {e}")
            return False

    async def close(self) -> None:
        """关闭浏览器和相关资源"""
        if self.browser:
            await self.browser.close()
            logger.info("浏览器已关闭")

    async def run(self) -> bool:
        """
        运行简化的上传流程

        Returns:
            bool: 整个流程是否成功
        """
        success = False

        try:
            # 初始化浏览器
            await self.init_browser(headless=self.config.get("headless", False))

            # 使用登录
            if not await self.login_with_cookies():
                logger.error("登录失败，终止上传流程")
                return False

            # 切换到指定频道
            channel_type = self.config.get("target_channel", "channel_ko")

            # 获取频道URL
            channel_url = self.config.get(channel_type)
            if not channel_url:
                logger.error(f"配置中未找到频道URL: {channel_type}")
                return False

            # 直接导航到频道URL
            logger.info(f"正在切换到频道: {channel_type}")
            await self.page.goto(channel_url)
            await asyncio.sleep(3)  # 等待页面加载

            # 检查是否成功进入频道
            current_url = self.page.url
            if "/channel/" in current_url:
                logger.info(f"成功进入{channel_type}频道")
            else:
                logger.warning(f"可能未成功进入频道，当前URL: {current_url}")
                # 继续执行，不要中断流程

            # 上传视频
            if not await self.upload_video():
                logger.error("上传视频失败，终止上传流程")
                return False

            logger.info("视频上传成功!")
            success = True

            # 设置keep_browser_open为True，确保浏览器不会关闭
            self.config["keep_browser_open"] = True

            # 等待10000秒进行调试
            logger.info("视频上传完成，保持浏览器打开状态10000秒供调试...")
            await asyncio.sleep(10000)  # 等待10000秒用于调试

        except Exception as e:
            logger.error(f"上传流程中出现未处理的错误: {e}")
            import traceback

            logger.error(traceback.format_exc())
            success = False

        finally:
            if not self.config.get("keep_browser_open", False):
                await self.close()

        return success

    async def manual_login(self) -> bool:
        """
        手动登录流程，用于获取新的Cookie

        Returns:
            bool: 登录是否成功
        """
        logger.info("开始手动登录流程...")

        try:
            # 直接导航到YouTube首页
            await self.page.goto("https://www.youtube.com/", timeout=60000)
            await asyncio.sleep(2)

            # 检查是否已经登录
            login_button = await self.page.query_selector(
                'a[href^="https://accounts.google.com/ServiceLogin"]'
            )

            if login_button:
                logger.info("找到登录按钮，点击开始登录...")
                await login_button.click()
            else:
                # 如果找不到登录按钮，直接访问登录页面
                await self.page.goto(
                    "https://accounts.google.com/ServiceLogin?service=youtube",
                    timeout=60000,
                )

            # 等待用户手动登录
            logger.info("请在浏览器窗口中手动完成登录流程...")
            logger.info("提示: 请输入您的Google账号和密码，并完成所有验证步骤")
            logger.info("提示: 完成登录后，您将被重定向回YouTube。")
            logger.info("     系统将等待最多5分钟，完成后会自动继续。")

            # 等待重定向到YouTube主页 或 YouTube studio页面
            try:
                await self.page.wait_for_url(
                    "https://www.youtube.com/**", timeout=300000
                )
            except PlaywrightTimeoutError:
                try:
                    # 也可能重定向到studio页面
                    if "studio.youtube.com" in self.page.url:
                        logger.info("已重定向到YouTube Studio页面")
                    else:
                        logger.error(f"未重定向到预期页面，当前URL: {self.page.url}")
                        return False
                except Exception:
                    logger.error("等待登录超时")
                    return False

            # 额外等待，确保完全登录
            await asyncio.sleep(5)

            # 访问YouTube主页，确保登录状态
            await self.page.goto("https://www.youtube.com/", timeout=60000)
            await asyncio.sleep(3)

            # 检查是否登录成功
            login_successful = (
                await self.page.query_selector('button[aria-label="创建"]')
                or await self.page.query_selector('button[aria-label="Create"]')
                or await self.page.query_selector("yt-icon-button#avatar-btn")
                or await self.page.query_selector("img#avatar-image")
            )

            if login_successful:
                logger.info("手动登录成功")

                # 保存新的Cookie
                await self.save_cookies()

                # 访问Studio确认登录有效
                await self.page.goto("https://studio.youtube.com/", timeout=60000)
                await asyncio.sleep(3)

                # 检查是否成功进入studio页面
                if "studio.youtube.com" in self.page.url:
                    logger.info("成功访问Studio页面，登录完全有效")
                    return True
                else:
                    logger.warning("无法访问Studio页面，登录可能不完全有效")
                    return False
            else:
                logger.error("手动登录似乎未成功")
                return False

        except Exception as e:
            logger.error(f"手动登录过程中出错: {e}")
            return False

    async def save_cookies(self) -> None:
        """保存当前的Cookie到文件"""
        cookies_dir = os.path.join(
            os.path.dirname(os.path.abspath(sys.argv[0])), "cookies"
        )

        # 确保目录存在
        os.makedirs(cookies_dir, exist_ok=True)

        # 使用用户名对应的cookie文件
        username = self.config.get("username", "dhliu.eth")
        cookie_path = os.path.join(
            cookies_dir, f"youtube_cookies_chrome_{username}.json"
        )

        # 获取当前的Cookie
        cookies = await self.browser.cookies()

        # 保存到文件
        try:
            with open(cookie_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger.info(f"成功保存Cookie到: {cookie_path}")
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")


async def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="YouTube 视频上传工具")
    parser.add_argument("config", help="配置文件路径")
    parser.add_argument(
        "--username", help="用户名，用于加载对应的cookie文件", default="dhliu.eth"
    )
    parser.add_argument("--target-channel", help="目标频道类型", default="channel_ko")
    parser.add_argument("--clean", action="store_true", help="清理浏览器配置文件")
    parser.add_argument(
        "--headless", action="store_true", help="无头模式（不显示浏览器界面）"
    )
    parser.add_argument(
        "--refresh-cookies", action="store_true", help="刷新Cookie（启动手动登录流程）"
    )
    parser.add_argument(
        "--force-login", action="store_true", help="强制进行手动登录流程"
    )

    args = parser.parse_args()

    # 加载配置文件
    config_path = args.config

    # 检查是否需要清理浏览器配置文件
    clean_profile = args.clean
    if clean_profile:
        logger.info("检测到--clean参数，将清理浏览器配置文件")

    # 如果设置了清理标志，清理浏览器配置文件
    if clean_profile:
        username = args.username
        if username:
            # 清理我们自己创建的用户数据目录
            user_data_dir = os.path.expanduser(
                f"~/.config/youtube-uploader-chrome-{username}"
            )
            if os.path.exists(user_data_dir):
                import shutil

                try:
                    shutil.rmtree(user_data_dir)
                    logger.info(f"已清理浏览器配置文件: {user_data_dir}")
                except Exception as e:
                    logger.error(f"清理浏览器配置文件失败: {e}")

    # 加载配置
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"无法加载配置文件 {config_path}: {e}")
        return 1

    # 添加命令行选项到配置
    config["headless"] = args.headless
    config["refresh_cookies"] = args.refresh_cookies
    config["force_login"] = args.force_login

    # 添加username和目标频道设置
    if args.username:
        config["username"] = args.username
    if args.target_channel:
        config["target_channel"] = args.target_channel

    # 设置默认用户名
    if not config.get("username"):
        config["username"] = "dhliu.eth"
        logger.info(f"未指定用户名，使用默认值: {config['username']}")

    # 设置cookie文件路径（基于用户名）
    config_file = config_path if isinstance(config_path, str) else args.config
    config["cookie_file"] = os.path.basename(config_file)

    # 设置默认目标频道
    if not config.get("target_channel"):
        config["target_channel"] = "channel_ko"
        logger.info(f"未指定目标频道，使用默认值: {config['target_channel']}")

    # 运行上传流程
    uploader = YouTubeUploader(config)

    try:
        # 如果需要刷新Cookie或强制登录，运行手动登录流程
        if config.get("refresh_cookies") or config.get("force_login"):
            logger.info(
                "检测到--refresh-cookies或--force-login参数，将运行手动登录流程"
            )
            await uploader.init_browser(headless=False)  # 手动登录必须使用有头浏览器
            login_success = await uploader.manual_login()
            await uploader.close()

            if login_success:
                logger.info("登录成功，请重新运行脚本进行上传")
            else:
                logger.error("登录失败")

            return 0 if login_success else 1

        # 正常上传流程
        success = await uploader.run()
        return 0 if success else 1

    except Exception as e:
        logger.error(f"运行过程中出现未处理的错误: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
