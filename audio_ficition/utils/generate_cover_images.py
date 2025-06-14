"""
科幻故事封面图片生成工具

功能说明:
此脚本使用 Leonardo AI API 根据封面提示词生成故事封面图片。

主要功能:
1. 读取封面提示词文件（来自 generate_cover_prompts.py 的输出）
2. 调用 Leonardo AI 模型生成图片
3. 将生成的图片保存到指定目录
4. 支持多个主题：scifi、thriller、horror、fantasy、romance

输入:
- Intel Mac: /Volumes/dhl/audio/{theme}/cover_prompts/[故事索引].txt
- Apple Silicon: /Users/donghaoliu/Documents/audio/{theme}/cover_prompts/[故事索引].txt

输出:
- Intel Mac: /Volumes/dhl/audio/{theme}/cover_img_small/[故事索引].png
- Apple Silicon: /Users/donghaoliu/Documents/audio/{theme}/cover_img_small/[故事索引].png

使用方法:
1. 基本使用: python generate_cover_images.py (生成所有主题的图片)
2. 指定主题: python generate_cover_images.py --theme scifi
3. 强制重新生成: python generate_cover_images.py -f --theme thriller
4. 指定故事索引范围: python generate_cover_images.py --theme horror --start 1 --end 10
5. 指定生成数量: python generate_cover_images.py --theme fantasy --count 5

注意:
- 使用 Leonardo AI API 生成图片
- 脚本支持断点续传，中断后可从上次停止的位置继续处理
- 生成的图片为 PNG 格式
- 默认处理所有主题，可用 --theme 参数指定单个主题
"""

import os
import sys
import time
import argparse
import base64
import glob
import re
import requests
import json
import random
import platform
from tqdm import tqdm
from PIL import Image
from io import BytesIO


def get_system_info():
    """获取系统信息，判断芯片类型"""
    system = platform.system()
    machine = platform.machine()

    if system == "Darwin":  # macOS
        if machine == "x86_64":
            return "intel_mac"
        elif machine == "arm64":
            return "apple_silicon"

    return "unknown"


def get_base_path():
    """根据系统类型获取基础路径"""
    system_type = get_system_info()

    if system_type == "intel_mac":
        return "/Volumes/dhl/audio"
    elif system_type == "apple_silicon":
        return "/Users/donghaoliu/Documents/audio"
    else:
        print(f"⚠️ 未知系统类型: {system_type}")
        # 默认使用Apple Silicon路径
        return "/Users/donghaoliu/Documents/audio"


def get_theme_paths(theme):
    """获取指定主题的路径"""
    base_path = get_base_path()

    paths = {
        "prompt_dir": os.path.join(base_path, theme, "cover_prompts"),
        "image_dir": os.path.join(base_path, theme, "cover_img_small"),
    }

    return paths


def setup_leonardo_client():
    """设置 Leonardo AI 客户端配置"""
    # 使用提供的 API key
    api_key = "3944f0ae-68f6-4b82-8f02-a4c840373f17"

    if not api_key:
        print("错误: 未找到 Leonardo AI 密钥")
        sys.exit(1)

    # Leonardo AI API 配置
    config = {
        "api_key": api_key,
        "base_url": "https://cloud.leonardo.ai/api/rest/v1",
        "model_id": "05ce0082-2d80-4a2d-8653-4d1c85e2418e",
        "headers": {
            "accept": "application/json",
            "authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        },
        "num_images": 1,
        "enhancePrompt": True,
    }

    print("✅ Leonardo AI 客户端配置完成")
    return config


def generate_image_with_leonardo(config, prompt, story_index, max_retries=3):
    """使用 Leonardo AI 模型生成图片"""
    if not prompt.strip():
        print(f"警告: 故事 {story_index} 的提示词为空，无法生成图片")
        return None

    # 检查并截断过长的提示词
    max_prompt_length = 1490
    if len(prompt) > max_prompt_length:
        original_length = len(prompt)
        prompt = prompt[:max_prompt_length]
        print(
            f"⚠️ 提示词过长 ({original_length} 字符)，已截断为 {max_prompt_length} 字符"
        )

    for attempt in range(max_retries):
        try:
            print(
                f"正在为故事 {story_index} 生成图片 (尝试 {attempt+1}/{max_retries})..."
            )

            # 随机选择预设风格
            preset_styles = ["CREATIVE", "DYNAMIC", "CINEMATIC", "HDR"]
            selected_style = random.choice(preset_styles)
            print(f"📸 选择预设风格: {selected_style}")

            # 准备请求数据
            generation_data = {
                "height": 720,
                "width": 1280,
                "prompt": prompt,
                "modelId": config["model_id"],
                "num_images": 1,
                "presetStyle": selected_style,
            }

            # 发送生成请求
            generation_url = f"{config['base_url']}/generations"
            response = requests.post(
                generation_url,
                headers=config["headers"],
                data=json.dumps(generation_data),
            )

            if response.status_code != 200:
                print(f"❌ 生成请求失败: {response.status_code} - {response.text}")
                continue

            generation_response = response.json()
            generation_id = generation_response.get("sdGenerationJob", {}).get(
                "generationId"
            )

            if not generation_id:
                print(f"❌ 未收到生成ID")
                continue

            print(f"📝 获得生成ID: {generation_id}，等待12秒...")
            time.sleep(12)

            # 尝试获取生成的图片（带重试机制）
            get_url = f"{config['base_url']}/generations/{generation_id}"

            # 第一次尝试获取图片
            get_response = requests.get(get_url, headers=config["headers"])

            if get_response.status_code != 200:
                print(
                    f"❌ 获取图片失败: {get_response.status_code} - {get_response.text}"
                )
                continue

            get_data = get_response.json()

            # 检查是否获得了有效的数据
            if get_data is None:
                print(f"⚠️ 第一次获取返回None，等待6秒后重试...")
                time.sleep(6)

                # 第二次尝试获取图片（使用同样的ID）
                get_response = requests.get(get_url, headers=config["headers"])

                if get_response.status_code != 200:
                    print(
                        f"❌ 第二次获取图片失败: {get_response.status_code} - {get_response.text}"
                    )
                    continue

                get_data = get_response.json()

                if get_data is None:
                    print(f"❌ 第二次获取仍然返回None，重新生成...")
                    continue

            generations = get_data.get("generations_by_pk", {}).get(
                "generated_images", []
            )

            if not generations:
                print(f"⚠️ 未找到生成的图片，等待6秒后重试...")
                time.sleep(6)

                # 第二次尝试获取图片（使用同样的ID）
                get_response = requests.get(get_url, headers=config["headers"])

                if get_response.status_code != 200:
                    print(
                        f"❌ 第二次获取图片失败: {get_response.status_code} - {get_response.text}"
                    )
                    continue

                get_data = get_response.json()

                if get_data is None:
                    print(f"❌ 第二次获取仍然返回None，重新生成...")
                    continue

                generations = get_data.get("generations_by_pk", {}).get(
                    "generated_images", []
                )

                if not generations:
                    print(f"❌ 第二次获取仍未找到生成的图片，重新生成...")
                    continue

            # 获取第一张图片的URL
            image_url = generations[0].get("url")
            if not image_url:
                print(f"❌ 未找到图片URL")
                continue

            # 下载图片
            img_response = requests.get(image_url)
            if img_response.status_code != 200:
                print(f"❌ 下载图片失败: {img_response.status_code}")
                continue

            print(f"✅ 已成功生成故事 {story_index} 的封面图片")
            return img_response.content

        except Exception as e:
            print(f"生成图片出错 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                retry_delay = (attempt + 1) * 5
                print(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print(f"达到最大重试次数 ({max_retries})，生成失败")
                return None


def get_existing_prompts(theme):
    """获取已生成的封面提示词文件列表"""
    paths = get_theme_paths(theme)
    prompt_dir = paths["prompt_dir"]

    if not os.path.exists(prompt_dir):
        print(f"提示词目录不存在: {prompt_dir}")
        return {}

    prompt_files = glob.glob(os.path.join(prompt_dir, "*.txt"))
    prompts = {}

    for file_path in prompt_files:
        basename = os.path.basename(file_path)
        # 排除以点开头的文件（如.DS_Store等）
        if basename.startswith("."):
            continue
        match = re.match(r"(\d+)\.txt", basename)
        if match:
            story_index = int(match.group(1))
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:  # 只包含有内容的提示词
                    prompts[story_index] = content
            except Exception as e:
                print(f"读取提示词文件 {file_path} 时出错: {e}")

    return prompts


def get_existing_images(theme):
    """获取已生成的封面图片列表"""
    paths = get_theme_paths(theme)
    image_dir = paths["image_dir"]

    if not os.path.exists(image_dir):
        os.makedirs(image_dir, exist_ok=True)
        return set()

    existing_files = glob.glob(os.path.join(image_dir, "*.png"))
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


def save_image(theme, story_index, image_bytes):
    """保存图片到文件"""
    paths = get_theme_paths(theme)
    image_dir = paths["image_dir"]

    # 检查并创建目录
    try:
        os.makedirs(image_dir, exist_ok=True)
        print(f"📂 确保目录存在: {image_dir}")
    except Exception as e:
        print(f"❌ 创建目录失败: {e}")
        return False

    file_path = os.path.join(image_dir, f"{story_index}.png")

    # 检查图片数据是否为空
    if not image_bytes:
        print(f"⚠️ 警告: 故事 {story_index} 的图片数据为空，跳过保存")
        return False

    try:
        # 使用PIL Image处理图片数据
        image = Image.open(BytesIO(image_bytes))
        image.save(file_path)

        # 验证文件是否成功写入
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"📁 已保存封面图片到: {file_path} (大小: {file_size} 字节)")
            return True
        else:
            print(f"❌ 文件保存后未找到: {file_path}")
            return False

    except Exception as e:
        print(f"❌ 保存图片到 {file_path} 时出错: {e}")
        return False


def process_theme(
    config, theme, force=False, start_index=None, end_index=None, count=None
):
    """处理单个主题的所有提示词，生成封面图片"""
    print(f"\n🎨 开始处理主题: {theme}")
    print("=" * 50)

    # 获取所有已存在的提示词
    prompts = get_existing_prompts(theme)

    if not prompts:
        print(f"❌ 主题 {theme} 未找到任何提示词文件")
        return 0, 0

    # 获取已存在的封面图片
    existing_images = get_existing_images(theme)

    # 过滤需要处理的提示词
    prompts_to_process = {}

    # 如果指定了数量参数，按索引顺序处理
    if count is not None:
        # 获取所有需要生成的故事索引（按顺序排列）
        candidate_indices = []
        for story_index in sorted(prompts.keys()):
            # 检查是否需要重新生成
            if force or story_index not in existing_images:
                candidate_indices.append(story_index)

        # 取前 count 个
        selected_indices = candidate_indices[:count]
        for story_index in selected_indices:
            prompts_to_process[story_index] = prompts[story_index]
    else:
        # 原有的范围过滤逻辑
        for story_index, content in prompts.items():
            # 应用索引范围过滤
            if start_index is not None and story_index < start_index:
                continue
            if end_index is not None and story_index > end_index:
                continue

            # 检查是否需要重新生成
            if force or story_index not in existing_images:
                prompts_to_process[story_index] = content

    if not prompts_to_process:
        print(f"✅ 主题 {theme} 所有指定范围内的故事都已有封面图片")
        return 0, 0

    print(f"\n=== 📊 主题 {theme} 封面图片生成分析 ===")
    print(f"总提示词数量: {len(prompts)}")
    print(f"已有封面图片: {len(existing_images)}")
    print(f"需要处理的提示词: {len(prompts_to_process)}")
    if count is not None:
        print(f"指定生成数量: {count}")
        if len(prompts_to_process) < count:
            print(f"⚠️ 实际可生成数量: {len(prompts_to_process)} (少于指定数量)")
    print(f"处理的故事索引: {sorted(prompts_to_process.keys())}")

    # 统计变量
    success_count = 0
    failure_count = 0

    # 处理每个提示词
    with tqdm(total=len(prompts_to_process), desc=f"生成 {theme} 封面图片进度") as pbar:
        for story_index in sorted(prompts_to_process.keys()):
            prompt = prompts_to_process[story_index]

            print(f"\n=== 处理主题 {theme} 故事 {story_index} ===")
            print(
                f"提示词内容: {prompt[:100]}..."
                if len(prompt) > 100
                else f"提示词内容: {prompt}"
            )

            # 生成封面图片
            image_bytes = generate_image_with_leonardo(config, prompt, story_index)

            if image_bytes:
                # 保存图片
                if save_image(theme, story_index, image_bytes):
                    success_count += 1
                    print(f"✅ 主题 {theme} 故事 {story_index} 封面图片生成成功")
                else:
                    failure_count += 1
                    print(f"❌ 主题 {theme} 故事 {story_index} 封面图片保存失败")
            else:
                failure_count += 1
                print(f"❌ 主题 {theme} 故事 {story_index} 封面图片生成失败")

            pbar.update(1)

            # 短暂延迟，避免API请求过快
            time.sleep(2)

    # 输出主题统计
    print(f"\n=== 📈 主题 {theme} 处理完成统计 ===")
    print(f"✅ 成功生成: {success_count}/{len(prompts_to_process)} 个封面图片")
    print(f"❌ 生成失败: {failure_count}/{len(prompts_to_process)} 个封面图片")
    if len(prompts_to_process) > 0:
        print(f"📊 成功率: {success_count/len(prompts_to_process)*100:.1f}%")

    return success_count, failure_count


def process_prompts(
    config, themes=None, force=False, start_index=None, end_index=None, count=None
):
    """处理所有主题的提示词，生成封面图片"""
    # 支持的主题列表
    available_themes = ["scifi", "thriller", "horror", "fantasy", "romance"]

    # 如果没有指定主题，处理所有主题
    if not themes:
        themes = available_themes
    else:
        # 验证指定的主题是否有效
        invalid_themes = [theme for theme in themes if theme not in available_themes]
        if invalid_themes:
            print(f"❌ 错误：不支持的主题: {invalid_themes}")
            print(f"支持的主题: {available_themes}")
            return

    print(f"🎯 将处理以下主题: {themes}")

    # 显示系统信息
    system_type = get_system_info()
    base_path = get_base_path()
    print(f"🖥️ 系统类型: {system_type}")
    print(f"📁 基础路径: {base_path}")

    total_success = 0
    total_failure = 0

    # 处理每个主题
    for theme in themes:
        success, failure = process_theme(
            config, theme, force, start_index, end_index, count
        )
        total_success += success
        total_failure += failure

    # 输出总体统计
    print(f"\n=== 🎉 所有主题处理完成统计 ===")
    print(f"✅ 总成功生成: {total_success} 个封面图片")
    print(f"❌ 总生成失败: {total_failure} 个封面图片")
    if total_success + total_failure > 0:
        print(f"📊 总成功率: {total_success/(total_success + total_failure)*100:.1f}%")


def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="根据封面提示词生成多主题故事封面图片")

    # 添加命令行参数
    parser.add_argument(
        "--theme",
        type=str,
        choices=["scifi", "thriller", "horror", "fantasy", "romance"],
        help="指定要处理的主题（不指定则处理所有主题）",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="强制重新生成封面图片，忽略已有文件",
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
        "--count",
        type=int,
        help="指定生成图片的数量（按故事索引顺序生成）",
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

    if args.count is not None and args.count <= 0:
        print("❌ 错误：生成数量必须大于 0")
        return

    # 检查参数冲突
    if args.count is not None and (args.start is not None or args.end is not None):
        print("❌ 错误：--count 参数不能与 --start 或 --end 参数同时使用")
        return

    print("🖼️ 多主题故事封面图片生成器")
    print("=" * 50)

    # 设置 Leonardo AI 客户端
    config = setup_leonardo_client()

    # 确定要处理的主题
    themes = [args.theme] if args.theme else None

    # 处理提示词，生成图片
    process_prompts(config, themes, args.force, args.start, args.end, args.count)

    print("\n🎉 封面图片生成任务完成!")


if __name__ == "__main__":
    main()
