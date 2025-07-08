#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube封面制作工具

功能说明：
此脚本用于将大尺寸图片转换为标准YouTube封面尺寸（1280x720）。

主要功能：
1. 支持macOS (Intel/Apple Silicon) 和 Linux/Ubuntu 系统
2. 读取yt_cover_large目录中的图片文件
3. 转换为YouTube标准封面尺寸（1280x720）
4. 智能调整：保持纵横比，适当裁剪或添加黑边
5. 支持多种图片格式（jpg、png、jpeg、webp等）
6. 支持断点续传，自动跳过已处理的图片
7. 自动排除Mac系统产生的点文件

输入路径：
- Intel Mac: /Volumes/dhl/beauty/yt_cover_large/*.{jpg,png,jpeg,webp}
- Apple Silicon Mac: /Users/donghaoliu/Documents/beauty/yt_cover_large/*.{jpg,png,jpeg,webp}
- Ubuntu: /mnt/dhl/beauty/yt_cover_large/*.{jpg,png,jpeg,webp}

输出路径：
- Intel Mac: /Volumes/dhl/beauty/yt_cover_right/*.jpg
- Apple Silicon Mac: /Users/donghaoliu/Documents/beauty/yt_cover_right/*.jpg
- Ubuntu: /mnt/dhl/beauty/yt_cover_right/*.jpg

分辨率转换：
- 目标分辨率：1280x720 (YouTube标准封面)
- 处理方式：
  - 如果原图比例接近16:9，则裁剪适配
  - 如果原图过宽或过高，则等比缩放并添加黑边
  - 保持最佳视觉效果

依赖环境：
- macOS 或 Ubuntu 操作系统
- Python PIL/Pillow库

使用方法：
# 处理所有图片（默认模式）
python create_youtube_covers.py

# 强制重新处理已存在的图片
python create_youtube_covers.py --force

# 指定图片质量
python create_youtube_covers.py --quality 95

# 调试模式
python create_youtube_covers.py --debug
"""

import os
import sys
import platform
import argparse
from pathlib import Path
from PIL import Image, ImageOps
import time


def check_supported_system():
    """检查是否为支持的系统（macOS 或 Ubuntu）"""
    system = platform.system()

    if system == "Darwin":
        # macOS
        machine = platform.machine()
        if machine == "x86_64":
            print(f"✅ 系统检查通过：macOS (Intel)")
        elif machine == "arm64":
            print(f"✅ 系统检查通过：macOS (Apple Silicon)")
        else:
            print(f"✅ 系统检查通过：macOS ({machine})")
        return True

    elif system == "Linux":
        # 检查是否为Ubuntu
        try:
            with open("/etc/os-release", "r") as f:
                content = f.read()
                if "Ubuntu" in content:
                    print(f"✅ 系统检查通过：Ubuntu")
                    return True
                else:
                    print(f"✅ 系统检查通过：Linux")
                    return True
        except FileNotFoundError:
            # 尝试检查另一个文件
            try:
                with open("/etc/lsb-release", "r") as f:
                    content = f.read()
                    if "Ubuntu" in content:
                        print(f"✅ 系统检查通过：Ubuntu")
                        return True
            except FileNotFoundError:
                pass
            print(f"✅ 系统检查通过：Linux")
            return True
    else:
        print(f"❌ 错误：不支持的操作系统")
        print(f"   当前系统：{system}")
        print(f"   支持的系统：macOS, Ubuntu/Linux")
        return False


def get_base_media_path():
    """根据系统类型返回相应的媒体路径"""
    system = platform.system()

    if system == "Darwin":
        # macOS
        machine = platform.machine()
        if machine == "x86_64":
            # Intel Mac
            return "/Volumes/dhl/beauty"
        else:
            # Apple Silicon Mac
            return "/Users/donghaoliu/Documents/beauty"
    else:
        # Linux/Ubuntu
        return "/mnt/dhl/beauty"


def check_pil_installation():
    """检查PIL/Pillow是否已安装"""
    try:
        from PIL import Image, ImageOps

        print(f"✅ PIL/Pillow库可用")
        return True
    except ImportError:
        print(f"❌ 错误：PIL/Pillow库未安装")
        print(f"   请安装：pip install Pillow")
        return False


def get_image_files(input_dir: str) -> list:
    """获取输入目录中的所有图片文件"""
    if not os.path.exists(input_dir):
        print(f"❌ 错误：输入目录不存在 {input_dir}")
        return []

    # 支持的图片格式
    supported_formats = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}

    image_files = []
    for filename in os.listdir(input_dir):
        # 排除Mac产生的点文件
        if filename.startswith("."):
            continue

        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext in supported_formats:
            image_files.append(filename)

    if not image_files:
        print(f"❌ 错误：输入目录中未找到支持的图片文件 {input_dir}")
        print(f"   支持的格式：{', '.join(supported_formats)}")
        return []

    image_files.sort()
    print(f"✅ 输入图片文件检查通过")
    print(f"📁 输入目录: {input_dir}")
    print(f"📊 图片文件数量: {len(image_files)}")
    print(f"📝 首个文件: {image_files[0]}")
    print(f"📝 最后文件: {image_files[-1]}")

    return image_files


def check_output_status(output_dir: str, input_files: list) -> dict:
    """检查输出状态，用于断点续传"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        return {
            "completed": [],
            "remaining": input_files,
            "completed_count": 0,
            "total_count": len(input_files),
        }

    completed_files = []
    for filename in os.listdir(output_dir):
        # 排除Mac产生的点文件
        if filename.startswith("."):
            continue

        if filename.endswith(".jpg"):
            # 提取原始文件名（去掉可能的扩展名变化）
            base_name = os.path.splitext(filename)[0]
            completed_files.append(base_name)

    # 找出还需要处理的文件
    remaining_files = []
    for input_file in input_files:
        base_name = os.path.splitext(input_file)[0]
        if base_name not in completed_files:
            remaining_files.append(input_file)

    return {
        "completed": completed_files,
        "remaining": remaining_files,
        "completed_count": len(completed_files),
        "total_count": len(input_files),
    }


def create_youtube_cover(
    input_path: str,
    output_path: str,
    target_width: int = 1280,
    target_height: int = 720,
    quality: int = 90,
    debug: bool = False,
) -> bool:
    """
    将输入图片转换为YouTube封面尺寸

    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        target_width: 目标宽度（默认1280）
        target_height: 目标高度（默认720）
        quality: JPEG质量（默认90）
        debug: 是否显示调试信息

    Returns:
        bool: 是否成功
    """
    try:
        # 打开图片
        with Image.open(input_path) as img:
            original_width, original_height = img.size
            original_ratio = original_width / original_height
            target_ratio = target_width / target_height

            if debug:
                print(f"   📐 原始尺寸: {original_width}x{original_height}")
                print(f"   📐 原始比例: {original_ratio:.3f}")
                print(f"   📐 目标比例: {target_ratio:.3f}")

            # 转换为RGB模式（如果需要）
            if img.mode in ("RGBA", "LA", "P"):
                # 创建白色背景
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(
                    img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None
                )
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # 计算缩放策略
            if abs(original_ratio - target_ratio) < 0.01:
                # 比例几乎相同，直接缩放
                final_img = img.resize(
                    (target_width, target_height), Image.Resampling.LANCZOS
                )
                if debug:
                    print(f"   🔄 策略：直接缩放")
            elif original_ratio > target_ratio:
                # 原图更宽，需要裁剪宽度或添加上下黑边
                if original_ratio / target_ratio > 1.5:
                    # 差异较大，添加上下黑边
                    new_width = int(original_height * target_ratio)
                    # 先调整大小，保持高度
                    scale_factor = target_height / original_height
                    scaled_width = int(original_width * scale_factor)
                    scaled_height = target_height

                    img_scaled = img.resize(
                        (scaled_width, scaled_height), Image.Resampling.LANCZOS
                    )

                    # 创建目标尺寸的黑色背景
                    final_img = Image.new(
                        "RGB", (target_width, target_height), (0, 0, 0)
                    )
                    # 居中粘贴
                    paste_x = (target_width - scaled_width) // 2
                    final_img.paste(img_scaled, (paste_x, 0))

                    if debug:
                        print(f"   🔄 策略：等比缩放后添加左右黑边")
                else:
                    # 差异不大，裁剪宽度
                    new_width = int(original_height * target_ratio)
                    crop_x = (original_width - new_width) // 2
                    img_cropped = img.crop(
                        (crop_x, 0, crop_x + new_width, original_height)
                    )
                    final_img = img_cropped.resize(
                        (target_width, target_height), Image.Resampling.LANCZOS
                    )

                    if debug:
                        print(f"   🔄 策略：裁剪宽度后缩放")
            else:
                # 原图更高，需要裁剪高度或添加左右黑边
                if target_ratio / original_ratio > 1.5:
                    # 差异较大，添加左右黑边
                    new_height = int(original_width / target_ratio)
                    # 先调整大小，保持宽度
                    scale_factor = target_width / original_width
                    scaled_width = target_width
                    scaled_height = int(original_height * scale_factor)

                    img_scaled = img.resize(
                        (scaled_width, scaled_height), Image.Resampling.LANCZOS
                    )

                    # 创建目标尺寸的黑色背景
                    final_img = Image.new(
                        "RGB", (target_width, target_height), (0, 0, 0)
                    )
                    # 居中粘贴
                    paste_y = (target_height - scaled_height) // 2
                    final_img.paste(img_scaled, (0, paste_y))

                    if debug:
                        print(f"   🔄 策略：等比缩放后添加上下黑边")
                else:
                    # 差异不大，裁剪高度
                    new_height = int(original_width / target_ratio)
                    crop_y = (original_height - new_height) // 2
                    img_cropped = img.crop(
                        (0, crop_y, original_width, crop_y + new_height)
                    )
                    final_img = img_cropped.resize(
                        (target_width, target_height), Image.Resampling.LANCZOS
                    )

                    if debug:
                        print(f"   🔄 策略：裁剪高度后缩放")

            # 保存结果
            final_img.save(output_path, "JPEG", quality=quality, optimize=True)

            if debug:
                print(f"   💾 输出尺寸: {final_img.size}")
                print(f"   💾 输出质量: {quality}")

            return True

    except Exception as e:
        print(f"❌ 处理图片时出错: {str(e)}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="YouTube封面制作工具")
    parser.add_argument("--force", action="store_true", help="强制重新处理已存在的图片")
    parser.add_argument(
        "--quality",
        type=int,
        default=90,
        choices=range(1, 101),
        help="JPEG输出质量 (1-100, 默认90)",
    )
    parser.add_argument("--debug", action="store_true", help="显示详细调试信息")

    args = parser.parse_args()

    print("🎬 YouTube封面制作工具启动")
    print("=" * 60)

    # 检查系统
    if not check_supported_system():
        sys.exit(1)

    # 检查PIL库
    if not check_pil_installation():
        sys.exit(1)

    # 获取路径
    base_path = get_base_media_path()
    input_dir = os.path.join(base_path, "yt_cover_large")
    output_dir = os.path.join(base_path, "yt_cover_right")

    print(f"\n📁 路径配置:")
    print(f"   输入目录: {input_dir}")
    print(f"   输出目录: {output_dir}")

    # 获取输入文件
    image_files = get_image_files(input_dir)
    if not image_files:
        sys.exit(1)

    # 检查输出状态
    if args.force:
        print(f"\n🔄 强制模式：将重新处理所有图片")
        status = {
            "remaining": image_files,
            "completed_count": 0,
            "total_count": len(image_files),
        }
    else:
        status = check_output_status(output_dir, image_files)
        if status["completed_count"] > 0:
            print(f"\n📊 断点续传状态:")
            print(f"   已完成: {status['completed_count']}")
            print(f"   待处理: {len(status['remaining'])}")
            print(f"   总数量: {status['total_count']}")

    if not status["remaining"]:
        print(f"\n✅ 所有图片已处理完成！")
        print(f"📊 总计处理: {status['total_count']} 张图片")
        return

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n🚀 开始处理图片...")
    print(f"📊 待处理: {len(status['remaining'])} 张图片")
    print(f"🎯 目标尺寸: 1280x720")
    print(f"🎨 输出质量: {args.quality}")

    # 处理图片
    success_count = 0
    error_count = 0
    start_time = time.time()

    for i, filename in enumerate(status["remaining"], 1):
        print(f"\n[{i}/{len(status['remaining'])}] 处理: {filename}")

        input_path = os.path.join(input_dir, filename)
        # 输出文件统一使用.jpg扩展名
        output_filename = os.path.splitext(filename)[0] + ".jpg"
        output_path = os.path.join(output_dir, output_filename)

        if args.debug:
            print(f"   📥 输入: {input_path}")
            print(f"   📤 输出: {output_path}")

        if create_youtube_cover(
            input_path, output_path, quality=args.quality, debug=args.debug
        ):
            success_count += 1
            print(f"   ✅ 成功")
        else:
            error_count += 1
            print(f"   ❌ 失败")

    # 处理完成统计
    end_time = time.time()
    duration = end_time - start_time

    print(f"\n" + "=" * 60)
    print(f"🎉 处理完成！")
    print(f"📊 成功: {success_count} 张")
    print(f"📊 失败: {error_count} 张")
    print(f"📊 总计: {success_count + error_count} 张")
    print(f"⏱️ 耗时: {duration:.1f} 秒")
    if success_count > 0:
        print(f"⚡ 平均: {duration/success_count:.1f} 秒/张")
    print(f"📁 输出目录: {output_dir}")


if __name__ == "__main__":
    main()
