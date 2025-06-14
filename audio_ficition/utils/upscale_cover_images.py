"""
科幻故事封面图片超分辨率处理工具

功能说明:
此脚本使用阿里云图像增强服务对封面图片进行超分辨率处理，提升图片质量和分辨率。

主要功能:
1. 读取封面图片文件（来自 enhance_cover_images.py 的输出）
2. 调用阿里云图像增强服务进行超分辨率处理
3. 将处理后的高清图片保存到指定目录
4. 支持多个主题：scifi、thriller、horror、fantasy、romance

输入:
- macOS: /Volumes/dhl/audio/{theme}/cover_enhanced/[故事索引].png
- Linux: /media/dhl/audio/{theme}/cover_enhanced/[故事索引].png

输出:
- macOS: /Volumes/dhl/audio/{theme}/cover_img_large/[故事索引].png
- Linux: /media/dhl/audio/{theme}/cover_img_large/[故事索引].png

使用方法:
1. 处理所有主题: python upscale_cover_images.py
2. 处理指定主题: python upscale_cover_images.py --theme scifi
3. 强制重新处理: python upscale_cover_images.py -f --theme thriller
4. 指定故事索引范围: python upscale_cover_images.py --theme fantasy --start 1 --end 10
5. 指定超分倍数: python upscale_cover_images.py --theme horror --scale 4

注意:
- 需要设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET
- 脚本支持断点续传，中断后可从上次停止的位置继续处理
- 支持超分倍数 2x 和 4x
- 处理本地文件，使用阿里云图像增强的advance接口
- 自动排除以点开头的meta文件（如.DS_Store等）
- 根据操作系统自动选择合适的路径（macOS使用/Volumes，Linux使用/media）
- 默认处理所有支持的主题，也可指定单个主题处理
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
    MakeSuperResolutionImageAdvanceRequest,
)
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient
import requests
from PIL import Image

# 支持的主题列表
SUPPORTED_THEMES = ["scifi", "thriller", "horror", "fantasy", "romance"]


def get_base_input_path(theme: str):
    """根据操作系统和主题返回原始图片的适当路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return f"/Volumes/dhl/audio/{theme}/cover_enhanced"
    else:  # 默认为Linux/Ubuntu
        return f"/media/dhl/audio/{theme}/cover_enhanced"


def get_base_output_path(theme: str):
    """根据操作系统和主题返回输出图片的适当路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return f"/Volumes/dhl/audio/{theme}/cover_img_large"
    else:  # 默认为Linux/Ubuntu
        return f"/media/dhl/audio/{theme}/cover_img_large"


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


def upscale_image(
    client: ImageEnhanClient,
    image_path: str,
    story_index: int,
    theme: str,
    upscale_factor: int = 2,
    max_retries: int = 3,
):
    """
    使用阿里云图像增强服务进行超分辨率处理

    Args:
        client: 阿里云图像增强客户端
        image_path: 本地图片文件路径
        story_index: 故事索引
        theme: 主题名称
        upscale_factor: 超分倍数（2 或 4）
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
                f"正在处理 {theme} 主题故事 {story_index} 的图片超分 (尝试 {attempt+1}/{max_retries})..."
            )
            print(f"处理本地文件: {image_path}")

            # 打开本地图片文件
            with open(image_path, "rb") as img_file:
                # 创建超分请求（使用本地文件）
                request = MakeSuperResolutionImageAdvanceRequest(
                    url_object=img_file,
                    mode="base",  # 使用base模式而不是enhancement
                    upscale_factor=upscale_factor,
                )

                # 运行时选项
                runtime = util_models.RuntimeOptions()

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

                    print(f"正在下载超分后的图片...")
                    img_response = requests.get(result_url, timeout=30)
                    img_response.raise_for_status()

                    print(f"✅ 已成功处理 {theme} 主题故事 {story_index} 的图片超分")
                    return img_response.content
                else:
                    print(f"❌ API返回数据格式异常或未包含图片URL")
                    return None

        except Exception as e:
            print(f"图片超分处理出错 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                retry_delay = (attempt + 1) * 5
                print(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print(f"达到最大重试次数 ({max_retries})，处理失败")
                return None


def get_existing_images(theme: str):
    """获取指定主题的原始封面图片列表"""
    image_dir = get_base_input_path(theme)

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


def get_existing_upscaled_images(theme: str):
    """获取指定主题已处理的超分图片列表"""
    output_dir = get_base_output_path(theme)

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


def save_upscaled_image(story_index: int, image_data: bytes, theme: str):
    """保存指定主题的超分后的图片到文件"""
    output_dir = get_base_output_path(theme)

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
        print(f"⚠️ 警告: {theme} 主题故事 {story_index} 的图片数据为空，跳过保存")
        return False

    try:
        # 使用PIL Image处理图片数据
        image = Image.open(io.BytesIO(image_data))
        image.save(file_path, "PNG")

        # 验证文件是否成功写入
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(
                f"📁 已保存 {theme} 主题超分图片到: {file_path} (大小: {file_size} 字节)"
            )
            return True
        else:
            print(f"❌ 文件保存后未找到: {file_path}")
            return False

    except Exception as e:
        print(f"❌ 保存图片到 {file_path} 时出错: {e}")
        return False


def process_theme_images(
    client: ImageEnhanClient,
    theme: str,
    force: bool = False,
    start_index: int = None,
    end_index: int = None,
    upscale_factor: int = 2,
):
    """处理指定主题的图片，进行超分辨率处理"""

    print(f"\n🎨 开始处理 {theme.upper()} 主题...")

    # 获取所有已存在的原始图片
    original_images = get_existing_images(theme)

    if not original_images:
        print(f"未找到 {theme} 主题的色彩增强封面图片文件")
        print(f"请先运行 enhance_cover_images.py 生成 {theme} 主题的色彩增强图片")
        return False

    # 获取已存在的超分图片
    existing_upscaled = get_existing_upscaled_images(theme)

    # 过滤需要处理的图片
    images_to_process = {}

    for story_index, image_path in original_images.items():
        # 应用索引范围过滤
        if start_index is not None and story_index < start_index:
            continue
        if end_index is not None and story_index > end_index:
            continue

        # 检查是否需要重新处理
        if force or story_index not in existing_upscaled:
            images_to_process[story_index] = image_path

    if not images_to_process:
        print(f"所有指定范围内的 {theme} 主题故事都已有超分图片")
        return True

    print(f"\n=== 📊 {theme.upper()} 主题图片超分处理分析 ===")
    print(f"总原始图片数量: {len(original_images)}")
    print(f"已有超分图片: {len(existing_upscaled)}")
    print(f"需要处理的图片: {len(images_to_process)}")
    print(f"超分倍数: {upscale_factor}x")
    print(f"处理的故事索引: {sorted(images_to_process.keys())}")

    # 统计变量
    success_count = 0
    failure_count = 0

    # 处理每个图片
    with tqdm(
        total=len(images_to_process), desc=f"{theme.upper()} 主题图片超分处理进度"
    ) as pbar:
        for story_index in sorted(images_to_process.keys()):
            image_path = images_to_process[story_index]

            print(f"\n=== 处理 {theme} 主题故事 {story_index} ===")
            print(f"原始图片路径: {image_path}")

            # 进行超分处理
            upscaled_data = upscale_image(
                client, image_path, story_index, theme, upscale_factor
            )

            if upscaled_data:
                # 保存超分后的图片
                if save_upscaled_image(story_index, upscaled_data, theme):
                    success_count += 1
                    print(f"✅ {theme} 主题故事 {story_index} 图片超分处理成功")
                else:
                    failure_count += 1
                    print(f"❌ {theme} 主题故事 {story_index} 图片保存失败")
            else:
                failure_count += 1
                print(f"❌ {theme} 主题故事 {story_index} 图片超分处理失败")

            pbar.update(1)

            # 短暂延迟，避免API请求过快
            time.sleep(2)

    # 输出最终统计
    print(f"\n=== 📈 {theme.upper()} 主题处理完成统计 ===")
    print(f"✅ 成功处理: {success_count}/{len(images_to_process)} 个图片")
    print(f"❌ 处理失败: {failure_count}/{len(images_to_process)} 个图片")
    print(f"📊 成功率: {success_count/len(images_to_process)*100:.1f}%")

    return success_count > 0


def process_images(
    client: ImageEnhanClient,
    themes: List[str],
    force: bool = False,
    start_index: int = None,
    end_index: int = None,
    upscale_factor: int = 2,
):
    """处理多个主题的图片，进行超分辨率处理"""

    total_themes = len(themes)
    successful_themes = 0

    print(f"\n🚀 开始处理 {total_themes} 个主题的图片超分任务...")
    print(f"主题列表: {', '.join(themes)}")

    for i, theme in enumerate(themes, 1):
        print(f"\n{'='*60}")
        print(f"📍 处理进度: {i}/{total_themes} - 当前主题: {theme.upper()}")
        print(f"{'='*60}")

        success = process_theme_images(
            client, theme, force, start_index, end_index, upscale_factor
        )

        if success:
            successful_themes += 1
            print(f"✅ {theme.upper()} 主题处理完成")
        else:
            print(f"❌ {theme.upper()} 主题处理失败或无图片需要处理")

    # 输出总体统计
    print(f"\n{'='*60}")
    print(f"🎉 所有主题处理完成!")
    print(f"📊 成功处理的主题: {successful_themes}/{total_themes}")
    print(f"📊 总体成功率: {successful_themes/total_themes*100:.1f}%")
    print(f"{'='*60}")


def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="对故事封面图片进行超分辨率处理")

    # 添加命令行参数
    parser.add_argument(
        "--theme",
        type=str,
        choices=SUPPORTED_THEMES,
        help=f"指定要处理的主题 ({', '.join(SUPPORTED_THEMES)})，不指定则处理所有主题",
    )
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
    parser.add_argument(
        "--scale",
        type=int,
        choices=[2, 4],
        default=2,
        help="超分倍数，支持2x或4x (默认: 2)",
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

    # 确定要处理的主题
    if args.theme:
        themes_to_process = [args.theme]
        print(f"🎯 指定处理主题: {args.theme}")
    else:
        themes_to_process = SUPPORTED_THEMES
        print(f"🌟 默认处理所有主题: {', '.join(SUPPORTED_THEMES)}")

    print("🔍 故事封面图片超分辨率处理器")
    print("=" * 50)

    # 创建阿里云客户端
    client = create_client()
    print("✅ 阿里云图像增强客户端初始化成功")

    # 处理图片超分
    process_images(
        client, themes_to_process, args.force, args.start, args.end, args.scale
    )

    print("\n🎉 图片超分处理任务完成!")


if __name__ == "__main__":
    main()
