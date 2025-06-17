"""
故事封面图片亮度增强处理工具

功能说明:
此脚本对超分辨率处理后的封面图片进行智能亮度增强，提升图片整体亮度的同时保护高光区域不过曝。

主要功能:
1. 读取超分辨率图片文件（来自 upscale_cover_images.py 的输出）
2. 使用智能算法进行亮度增强处理
3. 将处理后的增亮图片保存到指定目录
4. 支持多个主题：scifi、thriller、horror、fantasy、romance

算法特点:
- 使用 CLAHE (限制对比度自适应直方图均衡化) 增强细节
- 结合 Gamma 校正智能提亮暗部
- 保护高光区域避免过曝
- 自适应处理不同亮度的图片

输入:
- macOS: /Volumes/dhl/audio/{theme}/cover_img_large/[故事索引].png
- Linux: /media/dhl/audio/{theme}/cover_img_large/[故事索引].png

输出:
- macOS: /Volumes/dhl/audio/{theme}/lighten_images/[故事索引].png
- Linux: /media/dhl/audio/{theme}/lighten_images/[故事索引].png

使用方法:
1. 处理所有主题: python lighten_cover_images.py
2. 处理指定主题: python lighten_cover_images.py --theme scifi
3. 强制重新处理: python lighten_cover_images.py -f --theme thriller
4. 指定故事索引范围: python lighten_cover_images.py --theme fantasy --start 1 --end 10
5. 调整增亮强度: python lighten_cover_images.py --theme horror --brightness 1.3

注意:
- 脚本支持断点续传，中断后可从上次停止的位置继续处理
- 自动排除以点开头的meta文件（如.DS_Store等）
- 根据操作系统自动选择合适的路径（macOS使用/Volumes，Linux使用/media）
- 默认处理所有支持的主题，也可指定单个主题处理
- 智能算法会根据图片现有亮度自适应调整处理强度
"""

import os
import sys
import argparse
import glob
import re
import platform
import cv2
import numpy as np
from tqdm import tqdm
from typing import List, Tuple
from PIL import Image, ImageEnhance, ImageStat

# 支持的主题列表
SUPPORTED_THEMES = ["scifi", "thriller", "horror", "fantasy", "romance"]


def get_base_input_path(theme: str):
    """根据操作系统和主题返回超分图片的适当路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return f"/Volumes/dhl/audio/{theme}/cover_img_large"
    else:  # 默认为Linux/Ubuntu
        return f"/media/dhl/audio/{theme}/cover_img_large"


def get_base_output_path(theme: str):
    """根据操作系统和主题返回增亮图片的适当路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return f"/Volumes/dhl/audio/{theme}/lighten_images"
    else:  # 默认为Linux/Ubuntu
        return f"/media/dhl/audio/{theme}/lighten_images"


def analyze_image_brightness(image: np.ndarray) -> dict:
    """
    分析图片的亮度分布

    Args:
        image: BGR格式的图片数组

    Returns:
        包含亮度分析结果的字典
    """
    # 转换为灰度图像
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 计算亮度统计
    mean_brightness = np.mean(gray)
    std_brightness = np.std(gray)

    # 计算直方图
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist = hist.flatten()

    # 计算各亮度区间的像素比例
    dark_pixels = np.sum(hist[0:85]) / np.sum(hist)  # 暗部 (0-84)
    mid_pixels = np.sum(hist[85:170]) / np.sum(hist)  # 中间 (85-169)
    bright_pixels = np.sum(hist[170:256]) / np.sum(hist)  # 亮部 (170-255)

    return {
        "mean_brightness": mean_brightness,
        "std_brightness": std_brightness,
        "dark_ratio": dark_pixels,
        "mid_ratio": mid_pixels,
        "bright_ratio": bright_pixels,
        "histogram": hist,
    }


def smart_brightness_enhancement(
    image: np.ndarray, brightness_factor: float = 1.2
) -> np.ndarray:
    """
    智能亮度增强处理

    Args:
        image: BGR格式的图片数组
        brightness_factor: 亮度增强因子

    Returns:
        处理后的图片数组
    """
    # 分析图片亮度
    analysis = analyze_image_brightness(image)

    # 根据图片亮度特征动态调整参数
    mean_brightness = analysis["mean_brightness"]
    dark_ratio = analysis["dark_ratio"]
    bright_ratio = analysis["bright_ratio"]

    # 如果图片已经很亮，减少增强强度
    if mean_brightness > 150:
        brightness_factor = min(brightness_factor, 1.1)
    elif mean_brightness < 80:
        brightness_factor = max(brightness_factor, 1.3)

    # 转换到LAB色彩空间进行处理
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    # 方法1: CLAHE (限制对比度自适应直方图均衡化)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_clahe = clahe.apply(l_channel)

    # 方法2: Gamma校正进行智能提亮
    # 根据暗部比例调整gamma值
    if dark_ratio > 0.4:  # 暗部较多
        gamma = 0.7  # 更强的提亮
    elif dark_ratio > 0.2:  # 中等暗部
        gamma = 0.8
    else:  # 暗部较少
        gamma = 0.9

    # 应用gamma校正
    gamma_table = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)]).astype(
        "uint8"
    )
    l_gamma = cv2.LUT(l_channel, gamma_table)

    # 混合CLAHE和Gamma校正的结果
    # 根据图片特征决定混合比例
    if bright_ratio > 0.3:  # 高光较多，更多使用CLAHE保护高光
        alpha = 0.7  # CLAHE权重
        beta = 0.3  # Gamma权重
    else:  # 高光较少，可以更多使用Gamma提亮
        alpha = 0.5
        beta = 0.5

    l_enhanced = cv2.addWeighted(l_clahe, alpha, l_gamma, beta, 0)

    # 应用额外的亮度增强
    l_enhanced = cv2.multiply(l_enhanced, brightness_factor)
    l_enhanced = np.clip(l_enhanced, 0, 255).astype("uint8")

    # 重新组合LAB通道
    enhanced_lab = cv2.merge([l_enhanced, a_channel, b_channel])

    # 转换回BGR色彩空间
    enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

    return enhanced_bgr


def enhance_image_brightness(
    input_path: str, story_index: int, theme: str, brightness_factor: float = 1.2
) -> np.ndarray:
    """
    增强单张图片的亮度

    Args:
        input_path: 输入图片路径
        story_index: 故事索引
        theme: 主题名称
        brightness_factor: 亮度增强因子

    Returns:
        处理后的图片数组，失败时返回 None
    """
    try:
        print(f"正在处理 {theme} 主题故事 {story_index} 的亮度增强...")
        print(f"输入文件: {input_path}")

        # 检查文件是否存在
        if not os.path.exists(input_path):
            print(f"❌ 图片文件不存在: {input_path}")
            return None

        # 读取图片
        image = cv2.imread(input_path)
        if image is None:
            print(f"❌ 无法读取图片: {input_path}")
            return None

        # 分析原图亮度
        analysis = analyze_image_brightness(image)
        print(
            f"原图亮度分析: 平均亮度={analysis['mean_brightness']:.1f}, "
            f"暗部={analysis['dark_ratio']:.1%}, "
            f"亮部={analysis['bright_ratio']:.1%}"
        )

        # 进行智能亮度增强
        enhanced_image = smart_brightness_enhancement(image, brightness_factor)

        # 分析处理后的亮度
        enhanced_analysis = analyze_image_brightness(enhanced_image)
        print(
            f"处理后亮度: 平均亮度={enhanced_analysis['mean_brightness']:.1f}, "
            f"暗部={enhanced_analysis['dark_ratio']:.1%}, "
            f"亮部={enhanced_analysis['bright_ratio']:.1%}"
        )

        print(f"✅ {theme} 主题故事 {story_index} 亮度增强处理成功")
        return enhanced_image

    except Exception as e:
        print(f"❌ 处理 {theme} 主题故事 {story_index} 时出错: {e}")
        return None


def get_existing_images(theme: str):
    """获取指定主题的超分图片列表"""
    image_dir = get_base_input_path(theme)

    if not os.path.exists(image_dir):
        print(f"超分图片目录不存在: {image_dir}")
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


def get_existing_lightened_images(theme: str):
    """获取指定主题已处理的增亮图片列表"""
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


def save_lightened_image(story_index: int, image: np.ndarray, theme: str):
    """保存指定主题的增亮后的图片到文件"""
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
    if image is None:
        print(f"⚠️ 警告: {theme} 主题故事 {story_index} 的图片数据为空，跳过保存")
        return False

    try:
        # 使用OpenCV保存图片
        success = cv2.imwrite(file_path, image)

        if success and os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(
                f"📁 已保存 {theme} 主题增亮图片到: {file_path} (大小: {file_size} 字节)"
            )
            return True
        else:
            print(f"❌ 文件保存失败: {file_path}")
            return False

    except Exception as e:
        print(f"❌ 保存图片到 {file_path} 时出错: {e}")
        return False


def process_theme_images(
    theme: str,
    force: bool = False,
    start_index: int = None,
    end_index: int = None,
    brightness_factor: float = 1.2,
):
    """处理指定主题的图片，进行亮度增强处理"""

    print(f"\n🌟 开始处理 {theme.upper()} 主题...")

    # 获取所有已存在的超分图片
    original_images = get_existing_images(theme)

    if not original_images:
        print(f"未找到 {theme} 主题的超分图片文件")
        print(f"请先运行 upscale_cover_images.py 生成 {theme} 主题的超分图片")
        return False

    # 获取已存在的增亮图片
    existing_lightened = get_existing_lightened_images(theme)

    # 过滤需要处理的图片
    images_to_process = {}

    for story_index, image_path in original_images.items():
        # 应用索引范围过滤
        if start_index is not None and story_index < start_index:
            continue
        if end_index is not None and story_index > end_index:
            continue

        # 检查是否需要重新处理
        if force or story_index not in existing_lightened:
            images_to_process[story_index] = image_path

    if not images_to_process:
        print(f"所有指定范围内的 {theme} 主题故事都已有增亮图片")
        return True

    print(f"\n=== 📊 {theme.upper()} 主题图片亮度增强分析 ===")
    print(f"总超分图片数量: {len(original_images)}")
    print(f"已有增亮图片: {len(existing_lightened)}")
    print(f"需要处理的图片: {len(images_to_process)}")
    print(f"亮度增强因子: {brightness_factor}")
    print(f"处理的故事索引: {sorted(images_to_process.keys())}")

    # 统计变量
    success_count = 0
    failure_count = 0

    # 处理每个图片
    with tqdm(
        total=len(images_to_process), desc=f"{theme.upper()} 主题亮度增强进度"
    ) as pbar:
        for story_index in sorted(images_to_process.keys()):
            image_path = images_to_process[story_index]

            print(f"\n=== 处理 {theme} 主题故事 {story_index} ===")
            print(f"超分图片路径: {image_path}")

            # 进行亮度增强处理
            enhanced_image = enhance_image_brightness(
                image_path, story_index, theme, brightness_factor
            )

            if enhanced_image is not None:
                # 保存增亮后的图片
                if save_lightened_image(story_index, enhanced_image, theme):
                    success_count += 1
                    print(f"✅ {theme} 主题故事 {story_index} 亮度增强处理成功")
                else:
                    failure_count += 1
                    print(f"❌ {theme} 主题故事 {story_index} 图片保存失败")
            else:
                failure_count += 1
                print(f"❌ {theme} 主题故事 {story_index} 亮度增强处理失败")

            pbar.update(1)

    # 输出最终统计
    print(f"\n=== 📈 {theme.upper()} 主题处理完成统计 ===")
    print(f"✅ 成功处理: {success_count}/{len(images_to_process)} 个图片")
    print(f"❌ 处理失败: {failure_count}/{len(images_to_process)} 个图片")
    print(f"📊 成功率: {success_count/len(images_to_process)*100:.1f}%")

    return success_count > 0


def process_images(
    themes: List[str],
    force: bool = False,
    start_index: int = None,
    end_index: int = None,
    brightness_factor: float = 1.2,
):
    """处理多个主题的图片，进行亮度增强处理"""

    total_themes = len(themes)
    successful_themes = 0

    print(f"\n🚀 开始处理 {total_themes} 个主题的图片亮度增强任务...")
    print(f"主题列表: {', '.join(themes)}")

    for i, theme in enumerate(themes, 1):
        print(f"\n{'='*60}")
        print(f"📍 处理进度: {i}/{total_themes} - 当前主题: {theme.upper()}")
        print(f"{'='*60}")

        success = process_theme_images(
            theme, force, start_index, end_index, brightness_factor
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
    parser = argparse.ArgumentParser(description="对故事封面图片进行智能亮度增强处理")

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
        "--brightness",
        type=float,
        default=1.2,
        help="亮度增强因子 (默认: 1.2, 建议范围: 1.1-1.5)",
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

    if args.brightness < 1.0 or args.brightness > 2.0:
        print("❌ 错误：亮度因子建议范围为 1.0-2.0")
        return

    # 确定要处理的主题
    if args.theme:
        themes_to_process = [args.theme]
        print(f"🎯 指定处理主题: {args.theme}")
    else:
        themes_to_process = SUPPORTED_THEMES
        print(f"🌟 默认处理所有主题: {', '.join(SUPPORTED_THEMES)}")

    print("💡 故事封面图片智能亮度增强器")
    print("=" * 50)

    # 检查OpenCV是否可用
    try:
        import cv2

        print("✅ OpenCV 库加载成功")
    except ImportError:
        print("❌ 错误: 未找到 OpenCV 库")
        print("请安装: pip install opencv-python")
        return

    # 处理图片亮度增强
    process_images(themes_to_process, args.force, args.start, args.end, args.brightness)

    print("\n🎉 图片亮度增强处理任务完成!")


if __name__ == "__main__":
    main()
