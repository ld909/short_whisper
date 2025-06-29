#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍封面图片超分辨率处理工具

功能说明:
此脚本专门用于处理 book_info_scraper.py 保存的书籍封面图片，使用阿里云图像增强服务对封面图片进行超分辨率处理，提升图片质量和分辨率。
支持断点续传，自动跳过已处理的文件和Mac系统生成的点开头文件。

主要功能:
1. 自动扫描 books/en/thumbnails 目录中的封面图片
2. 调用阿里云图像增强服务进行超分辨率处理
3. 将处理后的高清图片保存到 thumbnails_large 目录
4. 支持断点续传，避免重复处理
5. 自动跳过Mac系统生成的点开头文件

输入:
- 输入目录: audio_ficition/books/en/thumbnails/
- 支持的格式: *.png

输出:
- 输出目录: /Volumes/dhl/audio/books/en/thumbnails_large/
- 命名规则: [uuid].png

使用方法:
1. 默认处理所有图片: python upscale_book_thumbnails.py
2. 指定超分倍数: python upscale_book_thumbnails.py --scale 4
3. 强制重新处理: python upscale_book_thumbnails.py --force
4. 调试模式: python upscale_book_thumbnails.py --debug
5. 指定语言: python upscale_book_thumbnails.py --language zh

处理流程:
1. 扫描 books/{language}/thumbnails 目录中的所有PNG文件
2. 检查是否已存在超分后的文件（断点续传）
3. 调用阿里云图像增强服务进行超分处理
4. 保存处理后的高清图片到 thumbnails_large 目录

注意:
- 需要设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET
- 处理本地文件，使用阿里云图像增强的advance接口
- 支持多种超分倍数（2x, 4x）
- 自动跳过点开头的系统文件
- 支持中英文两种语言的书籍处理
"""

import os
import sys
import time
import argparse
import glob
import re
import io
import platform
import logging
from pathlib import Path
from tqdm import tqdm
from typing import Optional, List, Tuple

from alibabacloud_imageenhan20190930.client import Client as ImageEnhanClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_imageenhan20190930 import models as imageenhan_20190930_models
from alibabacloud_imageenhan20190930.models import (
    MakeSuperResolutionImageAdvanceRequest,
)
from alibabacloud_tea_util import models as util_models
import requests
from PIL import Image

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/audio"
    else:  # 默认为Linux/Ubuntu
        return "/mnt/dhl/audio"


def get_input_directory(language="en"):
    """获取输入目录路径"""
    base_media_path = get_base_media_path()
    return os.path.join(base_media_path, "books", language, "thumbnails")


def get_output_directory(language="en"):
    """获取输出目录路径"""
    base_media_path = get_base_media_path()
    return os.path.join(base_media_path, "books", language, "thumbnails_large")


def create_client() -> ImageEnhanClient:
    """
    创建阿里云图像增强客户端
    @return: ImageEnhanClient
    @throws Exception
    """
    # 从环境变量获取访问密钥
    access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
    access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")

    if not access_key_id or not access_key_secret:
        print("❌ 错误: 未找到阿里云访问密钥")
        print(
            "请设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET"
        )
        print("例如:")
        print("export ALIBABA_CLOUD_ACCESS_KEY_ID='your-access-key-id'")
        print("export ALIBABA_CLOUD_ACCESS_KEY_SECRET='your-access-key-secret'")
        sys.exit(1)

    try:
        # 使用更标准的配置方式
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint="imageenhan.cn-shanghai.aliyuncs.com",
            region_id="cn-shanghai",
        )

        return ImageEnhanClient(config)
    except Exception as e:
        print(f"❌ 初始化阿里云客户端时出错: {e}")
        sys.exit(1)


def upscale_image(
    client: ImageEnhanClient,
    image_path: str,
    uuid: str,
    upscale_factor: int = 2,
    max_retries: int = 3,
) -> Optional[bytes]:
    """
    使用阿里云图像增强服务进行超分辨率处理

    Args:
        client: 阿里云图像增强客户端
        image_path: 本地图片文件路径
        uuid: 书籍UUID
        upscale_factor: 超分倍数（2 或 4）
        max_retries: 最大重试次数

    Returns:
        处理后的图片数据，失败时返回 None
    """

    # 检查文件是否存在
    if not os.path.exists(image_path):
        print(f"❌ 图片文件不存在: {image_path}")
        return None

    # 检查文件大小
    file_size = os.path.getsize(image_path)
    if file_size == 0:
        print(f"❌ 图片文件为空: {image_path}")
        return None

    print(f"📹 图片文件大小: {file_size / 1024:.2f} KB")

    for attempt in range(max_retries):
        try:
            print(f"🚀 正在处理图片超分 (尝试 {attempt+1}/{max_retries})...")
            print(f"📂 处理本地文件: {image_path}")

            # 打开本地图片文件
            with open(image_path, "rb") as img_file:
                # 创建超分请求（使用本地文件）
                request = MakeSuperResolutionImageAdvanceRequest(
                    url_object=img_file,
                    mode="base",  # 使用base模式
                    upscale_factor=upscale_factor,
                )

                # 运行时选项
                runtime = util_models.RuntimeOptions()

                print("🚀 正在调用阿里云图像超分API...")

                # 调用API (使用advance方法处理本地文件)
                response = client.make_super_resolution_image_advance(request, runtime)

                if (
                    response
                    and response.body
                    and response.body.data
                    and response.body.data.url
                ):
                    # 获取处理后的图片URL
                    result_url = response.body.data.url
                    print(f"✅ 图片超分处理成功")
                    print(f"📥 处理后图片URL: {result_url}")

                    # 下载处理后的图片
                    print(f"📥 正在下载超分后的图片...")
                    img_response = requests.get(result_url, timeout=30)
                    img_response.raise_for_status()

                    print(f"✅ 图片下载成功")
                    return img_response.content
                else:
                    print(f"❌ API返回数据格式异常")
                    print(f"响应内容: {response}")
                    return None

        except Exception as e:
            print(f"❌ 图片超分处理出错 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                retry_delay = (attempt + 1) * 5
                print(f"⏳ 等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print(f"❌ 达到最大重试次数 ({max_retries})，处理失败")
                return None


def get_input_images(language="en") -> List[Tuple[str, str]]:
    """
    获取需要处理的输入图片文件列表

    Returns:
        图片文件路径和UUID的元组列表
    """
    input_dir = get_input_directory(language)

    if not os.path.exists(input_dir):
        print(f"❌ 输入目录不存在: {input_dir}")
        return []

    # 获取所有PNG文件
    png_files = glob.glob(os.path.join(input_dir, "*.png"))

    # 过滤掉点开头的系统文件
    valid_files = []
    for png_file in png_files:
        basename = os.path.basename(png_file)

        # 跳过点开头的文件
        if basename.startswith("."):
            continue

        # 提取UUID
        uuid_match = re.match(r"([a-f0-9\-]+)\.png", basename)
        if uuid_match:
            uuid = uuid_match.group(1)
            valid_files.append((png_file, uuid))

    # 按UUID排序
    valid_files.sort(key=lambda x: x[1])

    print(f"📁 在 {input_dir} 目录找到 {len(valid_files)} 个需要处理的PNG文件")
    if valid_files:
        for i, (file_path, uuid) in enumerate(valid_files[:10], 1):  # 只显示前10个
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path) / 1024
            print(f"   {i}. {filename} ({file_size:.2f} KB)")
        if len(valid_files) > 10:
            print(f"   ... 还有 {len(valid_files) - 10} 个文件")

    return valid_files


def get_existing_upscaled_images(language="en") -> set:
    """
    获取已存在的超分后图片文件UUID集合

    Returns:
        已存在文件的UUID集合
    """
    output_dir = get_output_directory(language)

    if not os.path.exists(output_dir):
        return set()

    # 获取所有PNG文件
    upscaled_files = glob.glob(os.path.join(output_dir, "*.png"))
    existing_uuids = set()

    for upscaled_file in upscaled_files:
        basename = os.path.basename(upscaled_file)

        # 跳过点开头的文件
        if basename.startswith("."):
            continue

        # 提取UUID
        uuid_match = re.match(r"([a-f0-9\-]+)\.png", basename)
        if uuid_match:
            uuid = uuid_match.group(1)
            existing_uuids.add(uuid)

    return existing_uuids


def save_upscaled_image(uuid: str, image_data: bytes, language="en") -> bool:
    """
    保存超分后的图片到文件

    Args:
        uuid: 书籍UUID
        image_data: 图片数据
        language: 语言

    Returns:
        保存成功返回True，失败返回False
    """
    output_dir = get_output_directory(language)

    # 检查并创建目录
    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"📂 确保目录存在: {output_dir}")
    except Exception as e:
        print(f"❌ 创建目录失败: {e}")
        return False

    file_path = os.path.join(output_dir, f"{uuid}.png")

    # 检查图片数据是否为空
    if not image_data:
        print(f"⚠️ 警告: UUID {uuid} 的图片数据为空，跳过保存")
        return False

    try:
        # 使用PIL Image处理图片数据
        image = Image.open(io.BytesIO(image_data))
        image.save(file_path, "PNG")

        # 验证文件是否成功写入
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"✅ 超分图片已保存: {file_path}")
            print(f"📏 文件大小: {file_size / 1024:.2f} KB")
            return True
        else:
            print(f"❌ 文件保存后未找到: {file_path}")
            return False

    except Exception as e:
        print(f"❌ 保存图片到 {file_path} 时出错: {e}")
        return False


def process_book_thumbnails(
    upscale_factor: int = 2,
    force: bool = False,
    debug: bool = False,
    language: str = "en",
) -> bool:
    """
    批量处理书籍封面图片超分的主要函数

    Args:
        upscale_factor: 超分倍数
        force: 是否强制重新处理
        debug: 是否启用调试模式
        language: 语言

    Returns:
        处理成功返回True，失败返回False
    """

    # 获取需要处理的图片列表
    input_images = get_input_images(language)

    if not input_images:
        print("❌ 未找到需要处理的图片文件")
        return False

    # 获取已存在的超分图片
    existing_images = get_existing_upscaled_images(language)

    # 过滤需要处理的图片
    images_to_process = []
    for image_path, uuid in input_images:
        if force or uuid not in existing_images:
            images_to_process.append((image_path, uuid))
        else:
            if debug:
                print(f"⏭️ 跳过已存在的超分图片: {uuid}")

    if not images_to_process:
        print("✅ 所有图片都已完成超分处理")
        return True

    print(f"\n=== 📊 书籍封面图片超分处理统计 ===")
    print(f"📁 输入目录: {get_input_directory(language)}")
    print(f"📁 输出目录: {get_output_directory(language)}")
    print(f"🌍 语言: {'中文' if language == 'zh' else 'English'}")
    print(f"📹 总图片数量: {len(input_images)}")
    print(f"✅ 已处理数量: {len(existing_images)}")
    print(f"🎯 需要处理: {len(images_to_process)}")
    print(f"📊 超分倍数: {upscale_factor}x")
    print(f"🔄 强制重新处理: {'是' if force else '否'}")
    print(f"🐛 调试模式: {'是' if debug else '否'}")

    # 创建阿里云客户端
    try:
        client = create_client()
        print("✅ 阿里云图像增强客户端初始化成功")
    except Exception as e:
        print(f"❌ 初始化阿里云客户端失败: {e}")
        return False

    # 统计变量
    success_count = 0
    failure_count = 0

    # 批量处理图片
    with tqdm(total=len(images_to_process), desc="🖼️ 超分进度") as pbar:
        for image_path, uuid in images_to_process:
            print(f"\n=== 🖼️ 处理图片: {uuid} ===")
            print(f"📂 输入文件: {image_path}")

            # 检查输入文件
            if not os.path.exists(image_path):
                print(f"❌ 输入图片文件不存在: {image_path}")
                failure_count += 1
                pbar.update(1)
                continue

            # 检查文件大小
            file_size = os.path.getsize(image_path)
            if file_size == 0:
                print(f"❌ 输入图片文件为空: {image_path}")
                failure_count += 1
                pbar.update(1)
                continue

            print(f"📹 图片文件大小: {file_size / 1024:.2f} KB")

            # 进行图片超分处理
            result_data = upscale_image(client, image_path, uuid, upscale_factor)

            if result_data:
                # 保存处理后的图片
                if save_upscaled_image(uuid, result_data, language):
                    success_count += 1
                    print(f"✅ {uuid} 超分处理成功")
                else:
                    failure_count += 1
                    print(f"❌ {uuid} 图片保存失败")
            else:
                failure_count += 1
                print(f"❌ {uuid} 超分处理失败")

            pbar.update(1)

            # 在处理间隔添加短暂延迟，避免API调用过于频繁
            if success_count + failure_count < len(images_to_process):
                print("⏳ 等待2秒后处理下一个文件...")
                time.sleep(2)

    # 输出最终统计
    print(f"\n=== 📈 书籍封面图片超分完成统计 ===")
    print(f"✅ 成功处理: {success_count}/{len(images_to_process)} 个图片")
    print(f"❌ 处理失败: {failure_count}/{len(images_to_process)} 个图片")
    print(f"📊 成功率: {success_count/len(images_to_process)*100:.1f}%")

    # 显示处理后的文件列表
    if success_count > 0:
        output_dir = get_output_directory(language)
        print(f"\n📁 处理完成的文件位于: {output_dir}")
        upscaled_files = glob.glob(os.path.join(output_dir, "*.png"))
        if upscaled_files:
            print("🖼️ 超分后的图片文件:")
            for upscaled_file in sorted(upscaled_files)[:10]:  # 只显示前10个
                filename = os.path.basename(upscaled_file)
                if not filename.startswith("."):
                    file_size = os.path.getsize(upscaled_file) / 1024
                    print(f"   📄 {filename} ({file_size:.2f} KB)")
            if len(upscaled_files) > 10:
                print(f"   ... 还有 {len(upscaled_files) - 10} 个文件")

    return success_count > 0


def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description="📚 书籍封面图片超分辨率处理器",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python upscale_book_thumbnails.py                    # 默认处理英文书籍
  python upscale_book_thumbnails.py --language zh      # 处理中文书籍
  python upscale_book_thumbnails.py --scale 4          # 使用4x超分
  python upscale_book_thumbnails.py --force            # 强制重新处理
  python upscale_book_thumbnails.py --debug            # 启用调试模式

注意:
- 需要设置阿里云访问密钥环境变量
- 处理后的文件保存在 thumbnails_large 目录
- 自动跳过已处理的文件（除非使用 --force）
- 自动跳过Mac系统生成的点开头文件
        """,
    )

    # 添加命令行参数
    parser.add_argument(
        "--scale",
        type=int,
        choices=[2, 4],
        default=2,
        help="超分倍数，支持2x或4x (默认: 2)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新处理所有图片",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式",
    )
    parser.add_argument(
        "--language",
        "-l",
        choices=["en", "zh"],
        default="en",
        help="选择语种: en(英文) 或 zh(中文) [默认: en]",
    )

    # 解析命令行参数
    args = parser.parse_args()

    print("🖼️ 书籍封面图片超分辨率处理器")
    print("=" * 50)

    # 显示系统信息和路径
    input_dir = get_input_directory(args.language)
    output_dir = get_output_directory(args.language)
    lang_name = "中文" if args.language == "zh" else "English"

    print(f"🌍 语种: {lang_name}")
    print(f"📁 输入目录: {input_dir}")
    print(f"📁 输出目录: {output_dir}")
    print(f"🖥️ 操作系统: {platform.system()}")

    # 检查目录是否存在
    if not os.path.exists(input_dir):
        print(f"❌ 输入目录不存在: {input_dir}")
        print("💡 请先运行 book_info_scraper.py 下载书籍封面图片")
        sys.exit(1)

    print(f"📊 超分倍数: {args.scale}x")
    print(f"🔄 强制重新处理: {'是' if args.force else '否'}")
    print(f"🐛 调试模式: {'是' if args.debug else '否'}")
    print()

    # 批量处理书籍封面图片超分
    success = process_book_thumbnails(args.scale, args.force, args.debug, args.language)

    if success:
        print(f"\n🎉 书籍封面图片超分处理任务完成!")
        sys.exit(0)
    else:
        print(f"\n❌ 书籍封面图片超分处理任务失败!")
        sys.exit(1)


if __name__ == "__main__":
    main()
