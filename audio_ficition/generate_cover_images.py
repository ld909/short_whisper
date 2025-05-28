"""
科幻故事封面图片生成工具

功能说明:
此脚本使用 AiHubMix 调用 Google Gemini 的 Imagen-3 模型，根据封面提示词生成故事封面图片。

主要功能:
1. 读取封面提示词文件（来自 generate_cover_prompts.py 的输出）
2. 调用 Google Gemini Imagen-3 模型生成图片
3. 将生成的图片保存到指定目录

输入:
- 封面提示词文件: /Volumes/dhl/audio/scifi/cover_prompts/[故事索引].txt

输出:
- 封面图片文件: /Volumes/dhl/audio/scifi/cover_img_small/[故事索引].png

使用方法:
1. 基本使用: python generate_cover_images.py
2. 强制重新生成: python generate_cover_images.py -f
3. 指定故事索引范围: python generate_cover_images.py --start 1 --end 10

注意:
- 需要设置环境变量 AIHUBMIX_API_KEY 以提供 AiHubMix 密钥
- 脚本支持断点续传，中断后可从上次停止的位置继续处理
- 生成的图片为 PNG 格式
"""

import os
import sys
import time
import argparse
import base64
import glob
import re
from tqdm import tqdm
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO


def setup_genai_client():
    """设置 Google GenAI 客户端（用于通过 AiHubMix 调用 Google Gemini）"""
    api_key = os.environ.get("AIHUBMIX_API_KEY")

    if not api_key:
        print("错误: 未找到 AiHubMix 密钥")
        print("请设置环境变量 AIHUBMIX_API_KEY")
        print("例如: export AIHUBMIX_API_KEY='your-api-key'")
        sys.exit(1)

    try:
        # 使用 AiHubMix 的 base_url
        client = genai.Client(
            api_key=api_key,
            http_options={"base_url": "https://aihubmix.com/gemini"},
        )
        return client
    except Exception as e:
        print(f"初始化 GenAI 客户端时出错: {e}")
        sys.exit(1)


def generate_image_with_imagen3(client, prompt, story_index, max_retries=3):
    """使用 Google Gemini Imagen-3 模型生成图片"""
    if not prompt.strip():
        print(f"警告: 故事 {story_index} 的提示词为空，无法生成图片")
        return None

    for attempt in range(max_retries):
        try:
            print(
                f"正在为故事 {story_index} 生成图片 (尝试 {attempt+1}/{max_retries})..."
            )

            # 调用 Google Gemini Imagen-3 模型
            response = client.models.generate_images(
                model="imagen-4.0-generate-preview-05-20",
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9",
                ),
            )

            # 获取生成的图片数据
            if response.generated_images and len(response.generated_images) > 0:
                image_bytes = response.generated_images[0].image.image_bytes
                print(f"✅ 已成功生成故事 {story_index} 的封面图片")
                return image_bytes
            else:
                print(f"❌ 未收到图片数据")
                return None

        except Exception as e:
            print(f"生成图片出错 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                retry_delay = (attempt + 1) * 5
                print(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print(f"达到最大重试次数 ({max_retries})，生成失败")
                return None


def get_existing_prompts():
    """获取已生成的封面提示词文件列表"""
    prompt_dir = "/Volumes/dhl/audio/scifi/cover_prompts"

    if not os.path.exists(prompt_dir):
        print(f"提示词目录不存在: {prompt_dir}")
        return {}

    prompt_files = glob.glob(os.path.join(prompt_dir, "*.txt"))
    prompts = {}

    for file_path in prompt_files:
        basename = os.path.basename(file_path)
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


def get_existing_images():
    """获取已生成的封面图片列表"""
    image_dir = "/Volumes/dhl/audio/scifi/cover_img_small"

    if not os.path.exists(image_dir):
        os.makedirs(image_dir, exist_ok=True)
        return set()

    existing_files = glob.glob(os.path.join(image_dir, "*.png"))
    existing_indices = set()

    for file_path in existing_files:
        basename = os.path.basename(file_path)
        match = re.match(r"(\d+)\.png", basename)
        if match:
            existing_indices.add(int(match.group(1)))

    return existing_indices


def save_image(story_index, image_bytes):
    """保存图片到文件"""
    image_dir = "/Volumes/dhl/audio/scifi/cover_img_small"

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


def process_prompts(client, force=False, start_index=None, end_index=None):
    """处理所有提示词，生成封面图片"""
    # 获取所有已存在的提示词
    prompts = get_existing_prompts()

    if not prompts:
        print("未找到任何提示词文件")
        return

    # 获取已存在的封面图片
    existing_images = get_existing_images()

    # 过滤需要处理的提示词
    prompts_to_process = {}

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
        print("所有指定范围内的故事都已有封面图片")
        return

    print(f"\n=== 📊 封面图片生成分析 ===")
    print(f"总提示词数量: {len(prompts)}")
    print(f"已有封面图片: {len(existing_images)}")
    print(f"需要处理的提示词: {len(prompts_to_process)}")
    print(f"处理的故事索引: {sorted(prompts_to_process.keys())}")

    # 统计变量
    success_count = 0
    failure_count = 0

    # 处理每个提示词
    with tqdm(total=len(prompts_to_process), desc="生成封面图片进度") as pbar:
        for story_index in sorted(prompts_to_process.keys()):
            prompt = prompts_to_process[story_index]

            print(f"\n=== 处理故事 {story_index} ===")
            print(
                f"提示词内容: {prompt[:100]}..."
                if len(prompt) > 100
                else f"提示词内容: {prompt}"
            )

            # 生成封面图片
            image_bytes = generate_image_with_imagen3(client, prompt, story_index)

            if image_bytes:
                # 保存图片
                if save_image(story_index, image_bytes):
                    success_count += 1
                    print(f"✅ 故事 {story_index} 封面图片生成成功")
                else:
                    failure_count += 1
                    print(f"❌ 故事 {story_index} 封面图片保存失败")
            else:
                failure_count += 1
                print(f"❌ 故事 {story_index} 封面图片生成失败")

            pbar.update(1)

            # 短暂延迟，避免API请求过快
            time.sleep(2)

    # 输出最终统计
    print(f"\n=== 📈 处理完成统计 ===")
    print(f"✅ 成功生成: {success_count}/{len(prompts_to_process)} 个封面图片")
    print(f"❌ 生成失败: {failure_count}/{len(prompts_to_process)} 个封面图片")
    print(f"📊 成功率: {success_count/len(prompts_to_process)*100:.1f}%")


def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="根据封面提示词生成科幻故事封面图片")

    # 添加命令行参数
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

    print("🖼️ 科幻故事封面图片生成器")
    print("=" * 50)

    # 设置 GenAI 客户端
    client = setup_genai_client()
    print("✅ GenAI 客户端初始化成功")

    # 处理提示词，生成图片
    process_prompts(client, args.force, args.start, args.end)

    print("\n🎉 封面图片生成任务完成!")


if __name__ == "__main__":
    main()
