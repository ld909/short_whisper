"""
科幻故事封面图片超分辨率处理工具

功能说明:
此脚本使用 GFPGAN 网络对封面图片进行超分辨率处理，提升图片质量和分辨率。

主要功能:
1. 读取小尺寸封面图片文件
2. 使用 GFPGAN 进行超分辨率处理
3. 将处理后的高清图片保存到指定目录
4. 支持多个主题：scifi、thriller、horror、fantasy、romance
5. 只支持 Ubuntu 系统运行

输入:
- Ubuntu: /media/dhl/audio/{theme}/cover_img_small/[故事索引].png

输出:
- Ubuntu: /media/dhl/audio/{theme}/cover_img_large/[故事索引].png

使用方法:
1. 处理所有主题: python upscale_cover_images.py
2. 处理指定主题: python upscale_cover_images.py --theme scifi
3. 强制重新处理: python upscale_cover_images.py -f --theme thriller
4. 指定故事索引范围: python upscale_cover_images.py --theme fantasy --start 1 --end 10
5. 指定超分倍数: python upscale_cover_images.py --theme horror --scale 4

注意:
- 只支持 Ubuntu 系统运行
- 需要安装 conda 环境和 GFPGAN
- 脚本支持断点续传，中断后可从上次停止的位置继续处理
- 支持超分倍数 2x 和 4x
- 处理本地文件，使用 GFPGAN 的 inference_gfpgan.py
- 自动排除以点开头的meta文件（如.DS_Store等）
- 默认处理所有支持的主题，也可指定单个主题处理

依赖环境:
- Ubuntu 操作系统
- conda 环境
- /home/dhl/Documents/GFPGAN/inference_gfpgan.py
"""

import os
import sys
import time
import argparse
import glob
import re
import shutil
import platform
import subprocess
from tqdm import tqdm
from typing import List
from pathlib import Path

# 支持的主题列表
SUPPORTED_THEMES = ["scifi", "thriller", "horror", "fantasy", "romance"]


def check_ubuntu_system():
    """检查是否为Ubuntu系统"""
    system = platform.system()
    if system != "Linux":
        print(f"❌ 错误：此脚本只支持Ubuntu系统")
        print(f"   当前系统：{system}")
        return False
    
    # 进一步检查是否为Ubuntu
    try:
        with open("/etc/os-release", "r") as f:
            content = f.read()
            if "Ubuntu" not in content:
                print(f"❌ 错误：此脚本只支持Ubuntu系统")
                print(f"   当前Linux发行版不是Ubuntu")
                return False
    except FileNotFoundError:
        # 尝试检查另一个文件
        try:
            with open("/etc/lsb-release", "r") as f:
                content = f.read()
                if "Ubuntu" not in content:
                    print(f"❌ 错误：此脚本只支持Ubuntu系统")
                    return False
        except FileNotFoundError:
            print(f"⚠️ 警告：无法确定Linux发行版，假设为Ubuntu继续执行")
    
    print(f"✅ 系统检查通过：Ubuntu")
    return True


def check_gfpgan_environment():
    """检查GFPGAN环境"""
    gfpgan_script = "/home/dhl/Documents/GFPGAN/inference_gfpgan.py"
    
    if not os.path.exists(gfpgan_script):
        print(f"❌ 错误：GFPGAN脚本不存在 {gfpgan_script}")
        return False
    
    print(f"✅ GFPGAN脚本存在: {gfpgan_script}")
    
    # 检查conda
    try:
        result = subprocess.run(
            ["conda", "--version"], capture_output=True, text=True, check=True
        )
        print(f"✅ conda 已安装: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"❌ 错误：未找到conda命令")
        print(f"   请确保已安装conda并添加到PATH环境变量")
        return False


def get_base_input_path(theme: str):
    """根据主题返回原始图片的适当路径（Ubuntu）"""
    return f"/media/dhl/audio/{theme}/cover_img_small"


def get_base_output_path(theme: str):
    """根据主题返回输出图片的适当路径（Ubuntu）"""
    return f"/media/dhl/audio/{theme}/cover_img_large"


def upscale_image_with_gfpgan(
    input_file: str,
    output_dir: str,
    story_index: int,
    theme: str,
    upscale_factor: int = 2,
    max_retries: int = 3,
):
    """
    使用 GFPGAN 进行超分辨率处理

    Args:
        input_file: 输入图片文件路径
        output_dir: 输出目录
        story_index: 故事索引
        theme: 主题名称
        upscale_factor: 超分倍数（2 或 4）
        max_retries: 最大重试次数

    Returns:
        处理是否成功
    """

    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"❌ 图片文件不存在: {input_file}")
        return False

    # 创建临时目录用于单个文件处理
    temp_input_dir = f"/tmp/gfpgan_input_{theme}_{story_index}"
    temp_output_dir = f"/tmp/gfpgan_output_{theme}_{story_index}"
    
    try:
        # 清理并创建临时目录
        if os.path.exists(temp_input_dir):
            shutil.rmtree(temp_input_dir)
        if os.path.exists(temp_output_dir):
            shutil.rmtree(temp_output_dir)
        
        os.makedirs(temp_input_dir, exist_ok=True)
        os.makedirs(temp_output_dir, exist_ok=True)
        
        # 将输入文件复制到临时目录
        temp_input_file = os.path.join(temp_input_dir, f"{story_index}.png")
        shutil.copy2(input_file, temp_input_file)

        for attempt in range(max_retries):
            try:
                print(
                    f"正在处理 {theme} 主题故事 {story_index} 的图片超分 (尝试 {attempt+1}/{max_retries})..."
                )
                print(f"处理文件: {input_file}")

                # 运行GFPGAN处理
                success = run_gfpgan(temp_input_dir, temp_output_dir, upscale_factor)
                
                if success:
                    # 查找输出文件（GFPGAN输出文件在 restored_imgs 子目录中）
                    restored_dir = os.path.join(temp_output_dir, "restored_imgs")
                    if os.path.exists(restored_dir):
                        output_files = [f for f in os.listdir(restored_dir) 
                                      if f.endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('.')]
                        
                        if output_files:
                            # 移动处理后的文件到最终输出目录
                            os.makedirs(output_dir, exist_ok=True)
                            source_file = os.path.join(restored_dir, output_files[0])
                            target_file = os.path.join(output_dir, f"{story_index}.png")
                            
                            shutil.move(source_file, target_file)
                            print(f"✅ 已成功处理 {theme} 主题故事 {story_index} 的图片超分")
                            return True
                        else:
                            print(f"❌ GFPGAN输出目录中未找到处理后的文件")
                    else:
                        print(f"❌ GFPGAN输出的restored_imgs目录不存在")
                else:
                    print(f"❌ GFPGAN处理失败")

            except Exception as e:
                print(f"图片超分处理出错 (尝试 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    retry_delay = (attempt + 1) * 5
                    print(f"等待{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                else:
                    print(f"达到最大重试次数 ({max_retries})，处理失败")

        return False

    finally:
        # 清理临时目录
        try:
            if os.path.exists(temp_input_dir):
                shutil.rmtree(temp_input_dir)
            if os.path.exists(temp_output_dir):
                shutil.rmtree(temp_output_dir)
        except Exception as e:
            print(f"⚠️ 清理临时目录失败: {e}")


def run_gfpgan(input_dir: str, output_dir: str, upscale_factor: int = 2) -> bool:
    """运行GFPGAN进行超分辨率处理"""
    try:
        gfpgan_script = "/home/dhl/Documents/GFPGAN/inference_gfpgan.py"
        
        print(f"🔧 开始运行GFPGAN...")
        print(f"📁 输入目录: {input_dir}")
        print(f"📤 输出目录: {output_dir}")
        
        # 构建conda命令
        cmd = [
            "conda", "run", "-n", "base",  # 使用conda base环境
            "python", gfpgan_script,
            "-i", input_dir,
            "-o", output_dir,
            "-v", "1.4",      # GFPGAN版本
            "-s", str(upscale_factor)  # 放大倍数
        ]
        
        print(f"🔧 执行命令: {' '.join(cmd)}")
        
        # 切换到GFPGAN目录执行
        gfpgan_dir = "/home/dhl/Documents/GFPGAN"
        
        # 执行命令
        result = subprocess.run(
            cmd, 
            cwd=gfpgan_dir,
            capture_output=True, 
            text=True, 
            check=True
        )
        
        print(f"✅ GFPGAN处理完成!")
        
        # 检查输出文件
        restored_dir = os.path.join(output_dir, "restored_imgs")
        if os.path.exists(restored_dir):
            output_files = [f for f in os.listdir(restored_dir) 
                           if f.endswith(('.png', '.jpg', '.jpeg')) and not f.startswith('.')]
            print(f"📊 生成文件数量: {len(output_files)}")
            return len(output_files) > 0
        else:
            print(f"❌ 输出目录的restored_imgs子目录未创建")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ GFPGAN执行失败:")
        print(f"   错误代码: {e.returncode}")
        if e.stdout:
            print(f"   标准输出: {e.stdout}")
        if e.stderr:
            print(f"   错误输出: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ GFPGAN处理过程出错: {e}")
        return False


def get_existing_images(theme: str):
    """获取指定主题的小尺寸封面图片列表"""
    image_dir = get_base_input_path(theme)

    if not os.path.exists(image_dir):
        print(f"小尺寸图片目录不存在: {image_dir}")
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


def process_theme_images(
    theme: str,
    force: bool = False,
    start_index: int = None,
    end_index: int = None,
    upscale_factor: int = 2,
):
    """处理指定主题的图片，进行超分辨率处理"""

    print(f"\n🎨 开始处理 {theme.upper()} 主题...")

    # 获取所有已存在的小尺寸图片
    small_images = get_existing_images(theme)

    if not small_images:
        print(f"未找到 {theme} 主题的小尺寸封面图片文件")
        print(f"请先确保 {theme} 主题的小尺寸封面图片已生成")
        return False

    # 获取已存在的超分图片
    existing_upscaled = get_existing_upscaled_images(theme)

    # 过滤需要处理的图片
    images_to_process = {}

    for story_index, image_path in small_images.items():
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
    print(f"总小尺寸图片数量: {len(small_images)}")
    print(f"已有超分图片: {len(existing_upscaled)}")
    print(f"需要处理的图片: {len(images_to_process)}")
    print(f"超分倍数: {upscale_factor}x")
    print(f"处理的故事索引: {sorted(images_to_process.keys())}")

    # 统计变量
    success_count = 0
    failure_count = 0
    
    # 获取输出目录
    output_dir = get_base_output_path(theme)

    # 处理每个图片
    with tqdm(
        total=len(images_to_process), desc=f"{theme.upper()} 主题图片超分处理进度"
    ) as pbar:
        for story_index in sorted(images_to_process.keys()):
            image_path = images_to_process[story_index]

            print(f"\n=== 处理 {theme} 主题故事 {story_index} ===")
            print(f"小尺寸图片路径: {image_path}")

            # 进行超分处理
            success = upscale_image_with_gfpgan(
                image_path, output_dir, story_index, theme, upscale_factor
            )

            if success:
                success_count += 1
                print(f"✅ {theme} 主题故事 {story_index} 图片超分处理成功")
            else:
                failure_count += 1
                print(f"❌ {theme} 主题故事 {story_index} 图片超分处理失败")

            pbar.update(1)

            # 短暂延迟，避免处理过快
            time.sleep(1)

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
            theme, force, start_index, end_index, upscale_factor
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
    parser = argparse.ArgumentParser(description="对故事封面图片进行超分辨率处理（使用GFPGAN）")

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

    print("🔍 故事封面图片超分辨率处理器 (GFPGAN)")
    print("=" * 50)

    # 检查操作系统
    if not check_ubuntu_system():
        return 1

    # 检查GFPGAN环境
    if not check_gfpgan_environment():
        return 1

    # 确定要处理的主题
    if args.theme:
        themes_to_process = [args.theme]
        print(f"🎯 指定处理主题: {args.theme}")
    else:
        themes_to_process = SUPPORTED_THEMES
        print(f"🌟 默认处理所有主题: {', '.join(SUPPORTED_THEMES)}")

    # 处理图片超分
    process_images(
        themes_to_process, args.force, args.start, args.end, args.scale
    )

    print("\n🎉 图片超分处理任务完成!")


if __name__ == "__main__":
    main()
