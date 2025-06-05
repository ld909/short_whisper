"""
科幻故事封面图片色彩增强工具

功能说明:
此脚本使用阿里云图像增强服务对封面图片进行色彩增强处理，提升图片的色彩质感和观感。

主要功能:
1. 读取封面图片文件（来自 generate_cover_images.py 的输出）
2. 调用阿里云图像增强服务进行色彩增强处理
3. 将处理后的增强图片保存到指定目录

输入:
- macOS: /Volumes/dhl/audio/scifi/cover_img_small/[故事索引].png
- Linux: /media/dhl/audio/scifi/cover_img_small/[故事索引].png

输出:
- macOS: /Volumes/dhl/audio/scifi/cover_enhanced/[故事索引].png
- Linux: /media/dhl/audio/scifi/cover_enhanced/[故事索引].png

使用方法:
1. 基本使用: python enhance_cover_images.py
2. 强制重新处理: python enhance_cover_images.py -f
3. 指定故事索引范围: python enhance_cover_images.py --start 1 --end 10

注意:
- 需要设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET
- 脚本支持断点续传，中断后可从上次停止的位置继续处理
- 使用 Rec709 调色模式，适合一般条件拍摄的图像
- 处理本地文件，使用阿里云图像增强的advance接口
- 自动排除以点开头的meta文件（如.DS_Store等）
- 根据操作系统自动选择合适的路径（macOS使用/Volumes，Linux使用/media）
"""

import os
import sys
import time
import argparse
import glob
import re
import io
import platform
from tqdm import tqdm
from typing import List

from alibabacloud_imageenhan20190930.client import Client as ImageEnhanClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_credentials.models import Config as CredentialConfig
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_imageenhan20190930 import models as imageenhan_20190930_models
from alibabacloud_imageenhan20190930.models import (
    EnhanceImageColorAdvanceRequest,
)
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient
import requests
from PIL import Image


def get_base_input_path():
    """根据操作系统返回原始图片的适当路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/audio/scifi/cover_img_small"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/audio/scifi/cover_img_small"


def get_base_output_path():
    """根据操作系统返回输出图片的适当路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/audio/scifi/cover_enhanced"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/audio/scifi/cover_enhanced"


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
        print("错误: 未找到阿里云访问密钥")
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
        print(f"初始化阿里云客户端时出错: {e}")
        sys.exit(1)


def enhance_image_color(
    client: ImageEnhanClient,
    image_path: str,
    story_index: int,
    max_retries: int = 3,
):
    """
    使用阿里云图像增强服务进行色彩增强处理

    Args:
        client: 阿里云图像增强客户端
        image_path: 本地图片文件路径
        story_index: 故事索引
        max_retries: 最大重试次数

    Returns:
        处理后的图片数据，失败时返回 None
    """

    # 检查文件是否存在
    if not os.path.exists(image_path):
        print(f"❌ 图片文件不存在: {image_path}")
        return None

    for attempt in range(max_retries):
        try:
            print(
                f"正在处理故事 {story_index} 的图片色彩增强 (尝试 {attempt+1}/{max_retries})..."
            )
            print(f"处理本地文件: {image_path}")

            # 打开本地图片文件
            with open(image_path, "rb") as img_file:
                # 创建色彩增强请求（使用本地文件）
                request = EnhanceImageColorAdvanceRequest(
                    image_urlobject=img_file,  # 修正参数名为 image_urlobject
                    mode="Rec709",  # 使用Rec709调色模式
                    output_format="png",  # 输出格式为PNG
                )

                # 运行时选项
                runtime = util_models.RuntimeOptions()

                # 调用API (使用advance方法处理本地文件)
                response = client.enhance_image_color_advance(request, runtime)

                if (
                    response
                    and response.body
                    and response.body.data
                    and response.body.data.image_url
                ):
                    # 获取处理后的图片URL
                    result_url = response.body.data.image_url

                    print(f"正在下载色彩增强后的图片...")
                    img_response = requests.get(result_url, timeout=30)
                    img_response.raise_for_status()

                    print(f"✅ 已成功处理故事 {story_index} 的图片色彩增强")
                    return img_response.content
                else:
                    print(f"❌ API返回数据格式异常或未包含图片URL")
                    return None

        except Exception as e:
            print(f"图片色彩增强处理出错 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                retry_delay = (attempt + 1) * 5
                print(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print(f"达到最大重试次数 ({max_retries})，处理失败")
                return None


def get_existing_images():
    """获取原始封面图片列表"""
    image_dir = get_base_input_path()

    if not os.path.exists(image_dir):
        print(f"原始图片目录不存在: {image_dir}")
        return {}

    image_files = glob.glob(os.path.join(image_dir, "*.png"))
    images = {}

    for file_path in image_files:
        basename = os.path.basename(file_path)
        # 排除以点开头的meta文件（如.DS_Store等）
        if basename.startswith("."):
            continue
        match = re.match(r"(\d+)\.png", basename)
        if match:
            story_index = int(match.group(1))
            images[story_index] = file_path

    return images


def get_existing_enhanced_images():
    """获取已处理的增强图片列表"""
    output_dir = get_base_output_path()

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        return set()

    existing_files = glob.glob(os.path.join(output_dir, "*.png"))
    existing_indices = set()

    for file_path in existing_files:
        basename = os.path.basename(file_path)
        # 排除以点开头的meta文件（如.DS_Store等）
        if basename.startswith("."):
            continue
        match = re.match(r"(\d+)\.png", basename)
        if match:
            existing_indices.add(int(match.group(1)))

    return existing_indices


def save_enhanced_image(story_index: int, image_data: bytes):
    """保存色彩增强后的图片到文件"""
    output_dir = get_base_output_path()

    # 检查并创建目录
    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"📂 确保目录存在: {output_dir}")
    except Exception as e:
        print(f"❌ 创建目录失败: {e}")
        return False

    file_path = os.path.join(output_dir, f"{story_index}.png")

    # 检查图片数据是否为空
    if not image_data:
        print(f"⚠️ 警告: 故事 {story_index} 的图片数据为空，跳过保存")
        return False

    try:
        # 使用PIL Image处理图片数据
        image = Image.open(io.BytesIO(image_data))
        image.save(file_path, "PNG")

        # 验证文件是否成功写入
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"📁 已保存色彩增强图片到: {file_path} (大小: {file_size} 字节)")
            return True
        else:
            print(f"❌ 文件保存后未找到: {file_path}")
            return False

    except Exception as e:
        print(f"❌ 保存图片到 {file_path} 时出错: {e}")
        return False


def process_images(
    client: ImageEnhanClient,
    force: bool = False,
    start_index: int = None,
    end_index: int = None,
):
    """处理图片，进行色彩增强处理"""

    # 获取所有已存在的原始图片
    original_images = get_existing_images()

    if not original_images:
        print("未找到任何原始封面图片文件")
        print("请先运行 generate_cover_images.py 生成封面图片")
        return

    # 获取已存在的增强图片
    existing_enhanced = get_existing_enhanced_images()

    # 过滤需要处理的图片
    images_to_process = {}

    for story_index, image_path in original_images.items():
        # 应用索引范围过滤
        if start_index is not None and story_index < start_index:
            continue
        if end_index is not None and story_index > end_index:
            continue

        # 检查是否需要重新处理
        if force or story_index not in existing_enhanced:
            images_to_process[story_index] = image_path

    if not images_to_process:
        print("所有指定范围内的故事都已有色彩增强图片")
        return

    print(f"\n=== 📊 图片色彩增强处理分析 ===")
    print(f"总原始图片数量: {len(original_images)}")
    print(f"已有增强图片: {len(existing_enhanced)}")
    print(f"需要处理的图片: {len(images_to_process)}")
    print(f"调色模式: Rec709 (适合一般条件拍摄的图像)")
    print(f"处理的故事索引: {sorted(images_to_process.keys())}")

    # 统计变量
    success_count = 0
    failure_count = 0

    # 处理每个图片
    with tqdm(total=len(images_to_process), desc="图片色彩增强处理进度") as pbar:
        for story_index in sorted(images_to_process.keys()):
            image_path = images_to_process[story_index]

            print(f"\n=== 处理故事 {story_index} ===")
            print(f"原始图片路径: {image_path}")

            # 进行色彩增强处理
            enhanced_data = enhance_image_color(client, image_path, story_index)

            if enhanced_data:
                # 保存增强后的图片
                if save_enhanced_image(story_index, enhanced_data):
                    success_count += 1
                    print(f"✅ 故事 {story_index} 图片色彩增强处理成功")
                else:
                    failure_count += 1
                    print(f"❌ 故事 {story_index} 图片保存失败")
            else:
                failure_count += 1
                print(f"❌ 故事 {story_index} 图片色彩增强处理失败")

            pbar.update(1)

            # 短暂延迟，避免API请求过快
            time.sleep(2)

    # 输出最终统计
    print(f"\n=== 📈 处理完成统计 ===")
    print(f"✅ 成功处理: {success_count}/{len(images_to_process)} 个图片")
    print(f"❌ 处理失败: {failure_count}/{len(images_to_process)} 个图片")
    print(f"📊 成功率: {success_count/len(images_to_process)*100:.1f}%")


def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="对科幻故事封面图片进行色彩增强处理")

    # 添加命令行参数
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="强制重新处理图片，忽略已有文件",
    )
    parser.add_argument(
        "--start",
        type=int,
        help="指定开始处理的故事索引",
    )
    parser.add_argument(
        "--end",
        type=int,
        help="指定结束处理的故事索引",
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 验证参数
    if args.start is not None and args.end is not None:
        if args.start > args.end:
            print("❌ 错误：开始索引不能大于结束索引")
            return
        if args.start <= 0 or args.end <= 0:
            print("❌ 错误：索引必须大于 0")
            return

    print("🎨 科幻故事封面图片色彩增强器")
    print("=" * 50)

    # 创建阿里云客户端
    client = create_client()
    print("✅ 阿里云图像增强客户端初始化成功")

    # 处理图片色彩增强
    process_images(client, args.force, args.start, args.end)

    print("\n🎉 图片色彩增强处理任务完成!")


if __name__ == "__main__":
    main()
