#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X平台帖子生成器
基于书籍总结生成病毒式传播的X平台帖子（3-4条推文线程）

📚 功能说明:
- 读取书籍总结文件(来自 generate_book_summary.py 的输出)
- 使用OpenAI GPT模型生成专业的X平台帖子线程
- 遵循病毒式传播的写作风格和结构要求
- 支持断点续传，跳过已存在的帖子文件
- 自动保存生成的X帖子到指定目录

📥 输入信息:
- 书籍总结目录:
  - Intel Mac: /Volumes/dhl/audio/books/en/summary/{uuid}.txt
  - Apple Silicon: /Users/donghaoliu/Documents/audio/books/en/summary/{uuid}.txt

📤 输出信息:
- X帖子:
  - Intel Mac: /Volumes/dhl/audio/books/en/x_posts/{uuid}.txt
  - Apple Silicon: /Users/donghaoliu/Documents/audio/books/en/x_posts/{uuid}.txt

🔄 处理规则:
1. 在macOS系统上运行（适配Intel和Apple Silicon）
2. 支持断点续传，跳过已存在的帖子文件
3. 自动排除以点开头的Mac系统文件
4. 生成3-4条推文线程，每条推文符合X平台字符限制
5. 使用病毒式传播的写作风格

💡 使用示例:
# 处理所有书籍
python generate_x_posts.py

# 处理指定UUID的书籍
python generate_x_posts.py --uuid 12345678-abcd-efgh-ijkl-123456789012

# 预览模式
python generate_x_posts.py --preview

# 强制重新生成
python generate_x_posts.py --force

# 处理指定数量
python generate_x_posts.py --count 10
"""

import os
import sys
import glob
import json
import argparse
import platform
import time
from pathlib import Path
from tqdm import tqdm
from typing import Optional, Dict, List, Tuple

# 导入OpenAI模块
try:
    from openai import OpenAI
except ImportError:
    print("❌ 缺少依赖模块，请安装: pip install openai")
    sys.exit(1)

# ============ 配置参数 ============
# 最小文件大小检查 (字节)
MIN_SUMMARY_SIZE = 500  # 500字节


def get_base_media_path():
    """根据系统类型返回基础媒体路径"""
    if platform.system() == "Darwin":  # macOS
        machine = platform.machine().lower()
        processor = platform.processor().lower()
        # Apple Silicon (M芯片)
        is_apple_silicon = (
            machine == "arm64"
            or "arm" in machine
            or "apple" in processor
            or "m1" in processor
            or "m2" in processor
            or "m3" in processor
        )
        if is_apple_silicon:
            return "/Users/donghaoliu/Documents/audio"
        else:
            # Intel Mac
            return "/Volumes/dhl/audio"
    return "/Users/donghaoliu/Documents/audio"  # 默认


def setup_openai_client():
    """设置OpenAI客户端并验证API密钥"""
    api_key = os.environ.get("UNI_API_KEY")

    if not api_key:
        print("❌ 错误: 未找到OpenAI API密钥")
        print("请设置环境变量UNI_API_KEY")
        print("例如: export UNI_API_KEY='your-api-key'")
        sys.exit(1)

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.uniapi.io/v1")
        return client
    except Exception as e:
        print(f"❌ 初始化OpenAI客户端时出错: {e}")
        print("这可能是由于以下原因:")
        print("1. OpenAI库版本不兼容，请尝试: pip install openai --upgrade")
        print("2. API密钥格式不正确")
        print("3. 网络连接问题")
        sys.exit(1)


def get_directories():
    """获取所有相关目录路径"""
    base_media_path = get_base_media_path()
    books_path = os.path.join(base_media_path, "books", "en")

    return {
        "summary": os.path.join(books_path, "summary"),
        "x_posts": os.path.join(books_path, "x_posts"),
    }


def check_macos_system():
    """
    检查是否为macOS系统

    Returns:
        bool: 是否为macOS系统
    """
    return platform.system() == "Darwin"


def is_valid_file(file_path: str, min_size: int = 1024) -> bool:
    """
    检查文件是否有效

    Args:
        file_path: 文件路径
        min_size: 最小文件大小（字节）

    Returns:
        bool: 文件是否有效
    """
    if not os.path.exists(file_path):
        return False

    try:
        file_size = os.path.getsize(file_path)
        if file_size < min_size:
            print(
                f"⚠️  文件过小，可能损坏: {os.path.basename(file_path)} ({file_size} 字节)"
            )
            return False
        return True
    except Exception as e:
        print(f"⚠️  检查文件时出错: {os.path.basename(file_path)}, 错误: {e}")
        return False


def get_available_summary_files(directories: Dict) -> List[Tuple[str, str]]:
    """
    获取所有可用的总结文件
    排除Mac生成的点文件

    Args:
        directories: 目录配置字典

    Returns:
        list: [(uuid, summary_path)] 格式的总结文件列表
    """
    summary_dir = directories["summary"]

    if not os.path.exists(summary_dir):
        print(f"❌ 总结目录不存在: {summary_dir}")
        return []

    # 获取所有总结文件
    summary_files = glob.glob(os.path.join(summary_dir, "*.txt"))
    available_summaries = []
    skipped_files = []

    for summary_file in summary_files:
        basename = os.path.basename(summary_file)

        # 跳过点开头的文件
        if basename.startswith(".") or basename.startswith("._"):
            skipped_files.append(basename)
            continue

        # 提取UUID
        if basename.endswith(".txt"):
            uuid = basename[:-4]  # 移除 .txt 扩展名
            if len(uuid) == 36 and uuid.count("-") == 4:  # 简单UUID格式验证
                if is_valid_file(summary_file, MIN_SUMMARY_SIZE):
                    available_summaries.append((uuid, summary_file))
            else:
                skipped_files.append(basename)

    if skipped_files:
        print(
            f"🚫 跳过 {len(skipped_files)} 个Mac系统文件: {', '.join(skipped_files[:5])}{'...' if len(skipped_files) > 5 else ''}"
        )

    print(f"📊 统计信息:")
    print(f"   - 找到总结文件: {len(available_summaries)} 个")

    return available_summaries


def load_summary_content(uuid: str, summary_path: str) -> Optional[str]:
    """
    加载书籍总结内容

    Args:
        uuid: 书籍UUID
        summary_path: 总结文件路径

    Returns:
        str: 总结内容，失败时返回None
    """
    try:
        with open(summary_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            print(f"⚠️  [UUID:{uuid[:8]}...] 总结文件为空")
            return None

        return content
    except Exception as e:
        print(f"⚠️  [UUID:{uuid[:8]}...] 读取总结文件失败: {e}")
        return None


def generate_x_post(
    client: OpenAI, summary_content: str, uuid: str, max_retries: int = 3
) -> Optional[str]:
    """
    使用OpenAI的GPT模型生成X帖子，失败时自动重试

    Args:
        client: OpenAI客户端
        summary_content: 书籍总结内容
        uuid: 书籍UUID
        max_retries: 最大重试次数

    Returns:
        str: 生成的X帖子，失败时返回None
    """
    system_prompt = """You are a social media growth expert specializing in making educational content go viral on X (formerly Twitter). Your brand voice is profound but simple, authoritative but accessible. You get straight to the core of an idea and present it in a way that provides immediate value and sparks conversation.

Your task is to transform the provided book summary script into a short, powerful X thread (3-4 tweets) designed for maximum reach and engagement.

Follow these rules with absolute precision:

RULE 1: THE VIRAL HOOK (TWEET 1)
The first tweet is the most important. It must be a single, powerful sentence. Start with a provocative question, a counter-intuitive statement, or a surprising truth that challenges a common belief. It must make people stop scrolling and want to know the answer. Keep it under 250 characters.

RULE 2: THE CORE IDEA (TWEET 2)
This tweet reveals the book's central, most powerful argument. Explain this single idea in the simplest terms possible. Use a powerful analogy if you can. It should directly answer the question or validate the statement from the hook.

RULE 3: THE APPLICATION / THE "WHY" (TWEET 3)
Explain why this idea is a game-changer. How does it change the way we should think, work, or live? This is the "aha!" moment for the reader. It must provide actionable insight or a profound shift in perspective.

RULE 4: THE WRAP-UP & CALL TO ACTION (TWEET 4)
Conclude with a final empowering thought. Then, gently guide followers to the full summary for a deeper dive. The call to action should feel like an invitation, not a sales pitch. Finally, add 3-4 strategic hashtags.

GENERAL STYLE GUIDELINES:
- Plain Language: No academic jargon. Write as if you're explaining a brilliant idea to a smart friend.
- Short Sentences: Use clear, concise sentences.
- Authentic Tone: Be genuine and profound. Avoid marketing hype.

Return the x post without other content."""

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Book summary to transform into X thread:\n\n{summary_content}",
                    },
                ],
                max_tokens=1000,
                temperature=0.7,
            )

            x_post = response.choices[0].message.content.strip()

            if x_post and len(x_post) > 50:  # 基本长度检查
                print(f"✅ [UUID:{uuid[:8]}...] 成功生成X帖子")
                return x_post
            else:
                print(f"⚠️  [UUID:{uuid[:8]}...] 生成的帖子过短，尝试重新生成...")

        except Exception as e:
            print(f"⚠️  [UUID:{uuid[:8]}...] 第{attempt + 1}次生成失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # 等待2秒后重试

    print(f"❌ [UUID:{uuid[:8]}...] 生成X帖子失败，已重试{max_retries}次")
    return None


def save_x_post_to_file(uuid: str, x_post: str, x_posts_dir: str) -> bool:
    """
    保存X帖子到文件

    Args:
        uuid: 书籍UUID
        x_post: X帖子内容
        x_posts_dir: X帖子目录

    Returns:
        bool: 保存是否成功
    """
    try:
        os.makedirs(x_posts_dir, exist_ok=True)
        x_post_file = os.path.join(x_posts_dir, f"{uuid}.txt")

        with open(x_post_file, "w", encoding="utf-8") as f:
            f.write(x_post)

        print(f"💾 [UUID:{uuid[:8]}...] X帖子已保存: {x_post_file}")
        return True
    except Exception as e:
        print(f"❌ [UUID:{uuid[:8]}...] 保存X帖子失败: {e}")
        return False


def get_existing_x_posts(directories: Dict) -> set:
    """
    获取已存在的X帖子

    Args:
        directories: 目录配置字典

    Returns:
        set: 已存在X帖子的UUID集合
    """
    x_posts_dir = directories["x_posts"]
    existing_x_posts = set()

    if not os.path.exists(x_posts_dir):
        return existing_x_posts

    x_post_files = glob.glob(os.path.join(x_posts_dir, "*.txt"))

    for x_post_file in x_post_files:
        basename = os.path.basename(x_post_file)
        if basename.endswith(".txt") and not basename.startswith("."):
            uuid = basename[:-4]
            if len(uuid) == 36 and uuid.count("-") == 4:
                existing_x_posts.add(uuid)

    return existing_x_posts


def process_single_book(
    uuid: str,
    summary_path: str,
    directories: Dict,
    client: OpenAI,
    force: bool = False,
    preview: bool = False,
    debug: bool = False,
) -> Dict:
    """
    处理单个书籍的X帖子生成

    Args:
        uuid: 书籍UUID
        summary_path: 总结文件路径
        directories: 目录配置字典
        client: OpenAI客户端
        force: 是否强制重新生成
        preview: 是否预览模式
        debug: 是否调试模式

    Returns:
        dict: 处理结果
    """
    result = {
        "uuid": uuid,
        "success": False,
        "message": "",
        "x_post_length": 0,
    }

    x_posts_dir = directories["x_posts"]
    x_post_file = os.path.join(x_posts_dir, f"{uuid}.txt")

    # 检查是否已存在（断点续传）
    if not force and os.path.exists(x_post_file):
        result["message"] = "X帖子已存在，跳过"
        result["success"] = True
        return result

    # 加载总结内容
    summary_content = load_summary_content(uuid, summary_path)
    if not summary_content:
        result["message"] = "无法加载总结内容"
        return result

    if preview:
        result["message"] = f"预览模式：总结内容长度 {len(summary_content)} 字符"
        result["success"] = True
        return result

    # 生成X帖子
    x_post = generate_x_post(client, summary_content, uuid)
    if not x_post:
        result["message"] = "生成X帖子失败"
        return result

    # 保存X帖子
    if save_x_post_to_file(uuid, x_post, x_posts_dir):
        result["success"] = True
        result["message"] = "X帖子生成成功"
        result["x_post_length"] = len(x_post)
    else:
        result["message"] = "保存X帖子失败"

    return result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="生成X平台帖子")
    parser.add_argument("--uuid", help="指定处理的书籍UUID")
    parser.add_argument("--count", type=int, help="限制处理的书籍数量")
    parser.add_argument(
        "--force", action="store_true", help="强制重新生成已存在的X帖子"
    )
    parser.add_argument("--preview", action="store_true", help="预览模式，不实际生成")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")

    args = parser.parse_args()

    # 检查系统
    if not check_macos_system():
        print("❌ 此脚本只能在macOS系统上运行")
        sys.exit(1)

    print("🚀 启动X平台帖子生成器")
    print(f"📁 媒体根目录: {get_base_media_path()}")

    # 获取目录配置
    directories = get_directories()
    print(f"📂 总结目录: {directories['summary']}")
    print(f"📂 X帖子目录: {directories['x_posts']}")

    # 创建输出目录
    os.makedirs(directories["x_posts"], exist_ok=True)

    # 设置OpenAI客户端
    if not args.preview:
        client = setup_openai_client()
        print("✅ OpenAI客户端初始化成功")
    else:
        client = None

    # 获取可用的总结文件
    available_summaries = get_available_summary_files(directories)

    if not available_summaries:
        print("❌ 未找到可用的总结文件")
        sys.exit(1)

    # 过滤指定UUID
    if args.uuid:
        available_summaries = [
            (uuid, path) for uuid, path in available_summaries if uuid == args.uuid
        ]
        if not available_summaries:
            print(f"❌ 未找到指定UUID的总结文件: {args.uuid}")
            sys.exit(1)

    # 限制处理数量
    if args.count:
        available_summaries = available_summaries[: args.count]

    print(f"📊 即将处理 {len(available_summaries)} 个书籍")

    # 获取已存在的X帖子（用于断点续传）
    existing_x_posts = get_existing_x_posts(directories)
    print(f"📄 已存在 {len(existing_x_posts)} 个X帖子")

    # 处理书籍
    successful_count = 0
    failed_count = 0
    skipped_count = 0

    for uuid, summary_path in tqdm(available_summaries, desc="生成X帖子"):
        if args.debug:
            print(f"\n🔍 处理书籍: {uuid}")

        result = process_single_book(
            uuid=uuid,
            summary_path=summary_path,
            directories=directories,
            client=client,
            force=args.force,
            preview=args.preview,
            debug=args.debug,
        )

        if result["success"]:
            if "跳过" in result["message"]:
                skipped_count += 1
            else:
                successful_count += 1
        else:
            failed_count += 1
            print(f"❌ [UUID:{uuid[:8]}...] {result['message']}")

    print(f"\n🎉 处理完成!")
    print(f"✅ 成功生成: {successful_count} 个")
    print(f"⏭️  跳过处理: {skipped_count} 个")
    print(f"❌ 失败数量: {failed_count} 个")


if __name__ == "__main__":
    main()
