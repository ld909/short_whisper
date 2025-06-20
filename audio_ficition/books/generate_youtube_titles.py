#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍YouTube标题生成器
为 merge_clips_with_audio.py 的输出MP4文件生成YouTube标题

📚 功能说明:
- 读取现有的MP4文件(来自 merge_clips_with_audio.py 的输出)
- 从书籍信息JSON文件中获取书名
- 生成标题格式: 书名 | Book Summary
- 如果书名过长，截断并添加三个点...
- 确保最终标题长度不超过99字符
- 保存标题到指定目录的文本文件中

📥 输入信息:
- MP4文件目录: /Volumes/dhl/audio/books/en/mp4_with_audio/{uuid}.mp4
- 书籍信息目录: /Volumes/dhl/audio/books/en/info/{uuid}.json

📤 输出信息:
- YouTube标题: /Volumes/dhl/audio/books/en/youtube_titles/{uuid}.txt

🔄 处理规则:
1. 在macOS系统上运行（适配Intel和Apple Silicon）
2. 支持断点续传，跳过已存在的标题文件
3. 自动排除以点开头的Mac系统文件
4. 标题格式: 书名 | Book Summary
5. 总长度限制在99字符以内
6. 书名过长时智能截断并添加...

💡 使用示例:
# 处理所有书籍
python generate_youtube_titles.py

# 处理指定UUID的书籍
python generate_youtube_titles.py --uuid 12345678-abcd-efgh-ijkl-123456789012

# 预览模式
python generate_youtube_titles.py --preview

# 强制重新生成
python generate_youtube_titles.py --force
"""

import os
import sys
import glob
import json
import argparse
import platform
from pathlib import Path
from tqdm import tqdm
from typing import Optional, Dict, List, Tuple

# ============ 配置参数 ============
# YouTube标题最大长度
MAX_TITLE_LENGTH = 99

# 标题后缀
TITLE_SUFFIX = " | Book Summary"

# 最小文件大小检查 (字节)
MIN_MP4_SIZE = 1024 * 1024 * 5  # 5MB
MIN_INFO_SIZE = 100  # 100字节


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/audio"
    else:  # 默认为Linux/Ubuntu
        return "/mnt/dhl/audio"


def get_directories():
    """获取所有相关目录路径"""
    base_media_path = get_base_media_path()
    books_path = os.path.join(base_media_path, "books", "en")

    return {
        "mp4": os.path.join(books_path, "mp4_with_audio"),
        "info": os.path.join(books_path, "info"),
        "titles": os.path.join(books_path, "youtube_titles"),
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


def get_available_mp4_files(directories: Dict) -> List[Tuple[str, str]]:
    """
    获取所有可用的MP4文件
    排除Mac生成的点文件

    Args:
        directories: 目录配置字典

    Returns:
        list: [(uuid, mp4_path)] 格式的MP4文件列表
    """
    mp4_dir = directories["mp4"]

    if not os.path.exists(mp4_dir):
        print(f"❌ MP4目录不存在: {mp4_dir}")
        return []

    # 获取所有MP4文件
    mp4_files = glob.glob(os.path.join(mp4_dir, "*.mp4"))
    available_mp4s = []
    skipped_files = []

    for mp4_file in mp4_files:
        basename = os.path.basename(mp4_file)

        # 跳过点开头的文件
        if basename.startswith(".") or basename.startswith("._"):
            skipped_files.append(basename)
            continue

        # 提取UUID
        if basename.endswith(".mp4"):
            uuid = basename[:-4]  # 移除 .mp4 扩展名
            if len(uuid) == 36 and uuid.count("-") == 4:  # 简单UUID格式验证
                if is_valid_file(mp4_file, MIN_MP4_SIZE):
                    available_mp4s.append((uuid, mp4_file))
            else:
                skipped_files.append(basename)

    if skipped_files:
        print(
            f"🚫 跳过 {len(skipped_files)} 个Mac系统文件: {', '.join(skipped_files[:5])}{'...' if len(skipped_files) > 5 else ''}"
        )

    print(f"📊 统计信息:")
    print(f"   - 找到MP4文件: {len(available_mp4s)} 个")

    return available_mp4s


def load_book_info(uuid: str, info_dir: str) -> Optional[Dict]:
    """
    加载书籍信息

    Args:
        uuid: 书籍UUID
        info_dir: 信息目录路径

    Returns:
        dict: 书籍信息，失败时返回None
    """
    info_file = os.path.join(info_dir, f"{uuid}.json")

    if not is_valid_file(info_file, MIN_INFO_SIZE):
        return None

    try:
        with open(info_file, "r", encoding="utf-8") as f:
            book_info = json.load(f)

        # 验证必要字段
        if not book_info.get("title"):
            print(f"⚠️  [UUID:{uuid[:8]}...] 书籍信息缺少标题")
            return None

        return book_info
    except Exception as e:
        print(f"❌ [UUID:{uuid[:8]}...] 读取书籍信息失败: {e}")
        return None


def generate_youtube_title(book_title: str) -> str:
    """
    生成YouTube标题

    Args:
        book_title: 书籍标题

    Returns:
        str: 格式化的YouTube标题
    """
    # 清理书名，移除多余的空白字符
    book_title = " ".join(book_title.split()).strip()

    # 构建基础标题格式
    title_template = "{}" + TITLE_SUFFIX

    # 计算可用于书名的最大字符数
    # 减去后缀的字符数
    max_book_title_length = MAX_TITLE_LENGTH - len(title_template.format(""))

    # 如果书名太长，截断并添加...
    if len(book_title) > max_book_title_length:
        # 为省略号留出空间
        truncate_length = max_book_title_length - 3
        book_title = book_title[:truncate_length].rstrip() + "..."

    # 生成最终标题
    final_title = title_template.format(book_title)

    # 最终检查长度
    if len(final_title) > MAX_TITLE_LENGTH:
        # 如果仍然超长（理论上不应该发生），再次截断
        final_title = final_title[: MAX_TITLE_LENGTH - 3] + "..."

    return final_title


def save_title_to_file(uuid: str, title: str, titles_dir: str) -> bool:
    """
    保存标题到文件

    Args:
        uuid: 书籍UUID
        title: YouTube标题
        titles_dir: 标题目录

    Returns:
        bool: 保存是否成功
    """
    try:
        # 确保目录存在
        os.makedirs(titles_dir, exist_ok=True)

        # 保存标题到文件
        title_file = os.path.join(titles_dir, f"{uuid}.txt")
        with open(title_file, "w", encoding="utf-8") as f:
            f.write(title)

        return True
    except Exception as e:
        print(f"❌ [UUID:{uuid[:8]}...] 保存标题文件失败: {e}")
        return False


def get_existing_titles(directories: Dict) -> set:
    """
    获取已存在的标题文件UUID集合

    Args:
        directories: 目录配置字典

    Returns:
        set: 已存在标题的UUID集合
    """
    title_uuids = set()
    titles_dir = directories["titles"]

    if os.path.exists(titles_dir):
        title_files = glob.glob(os.path.join(titles_dir, "*.txt"))
        for title_file in title_files:
            basename = os.path.basename(title_file)
            if not basename.startswith(".") and basename.endswith(".txt"):
                uuid = basename[:-4]
                if len(uuid) == 36 and uuid.count("-") == 4:
                    title_uuids.add(uuid)

    return title_uuids


def process_single_book(
    uuid: str,
    mp4_path: str,
    directories: Dict,
    force: bool = False,
    preview: bool = False,
    debug: bool = False,
) -> Dict:
    """
    处理单个书籍的YouTube标题生成

    Args:
        uuid: 书籍UUID
        mp4_path: MP4文件路径
        directories: 目录配置
        force: 是否强制重新处理
        preview: 是否为预览模式
        debug: 是否启用调试模式

    Returns:
        dict: 处理结果
    """
    print(f"\n=== 📚 处理书籍 UUID: {uuid[:8]}...{uuid[-8:]} ===")

    # 生成输出路径
    title_path = os.path.join(directories["titles"], f"{uuid}.txt")

    print(f"📁 MP4文件: {os.path.basename(mp4_path)}")
    print(f"📁 标题文件: {os.path.basename(title_path)}")

    # 检查是否需要跳过（除非强制处理）
    title_exists = is_valid_file(title_path, 1)

    if not force and title_exists:
        print(f"⏭️  [UUID:{uuid[:8]}...] 标题文件已存在，跳过处理")
        return {
            "uuid": uuid,
            "status": "skipped",
            "reason": "already_exists",
            "title_path": title_path,
        }

    # 加载书籍信息
    book_info = load_book_info(uuid, directories["info"])
    if not book_info:
        print(f"❌ [UUID:{uuid[:8]}...] 无法加载书籍信息")
        return {
            "uuid": uuid,
            "status": "failed",
            "reason": "info_not_found",
        }

    book_title = book_info["title"]
    print(f"📖 书名: {book_title}")

    # 生成YouTube标题
    youtube_title = generate_youtube_title(book_title)
    print(f"🎬 YouTube标题: {youtube_title}")
    print(f"📏 标题长度: {len(youtube_title)}/{MAX_TITLE_LENGTH}")

    # 预览模式
    if preview:
        return {
            "uuid": uuid,
            "status": "preview",
            "book_title": book_title,
            "youtube_title": youtube_title,
            "title_length": len(youtube_title),
            "needs_generation": not title_exists or force,
        }

    # 实际处理 - 保存标题
    if save_title_to_file(uuid, youtube_title, directories["titles"]):
        print(f"✅ [UUID:{uuid[:8]}...] 标题生成成功!")
        return {
            "uuid": uuid,
            "status": "success",
            "book_title": book_title,
            "youtube_title": youtube_title,
            "title_length": len(youtube_title),
            "title_path": title_path,
        }
    else:
        return {
            "uuid": uuid,
            "status": "failed",
            "reason": "save_failed",
        }


def main():
    """主函数"""
    # 检查系统
    if not check_macos_system():
        print("⚠️  此脚本主要为macOS系统设计，其他系统可能需要调整路径")

    print("✅ 系统检测完成")

    parser = argparse.ArgumentParser(
        description="书籍YouTube标题生成器 - 为MP4文件生成YouTube标题（支持断点续传）",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python generate_youtube_titles.py                                # 处理所有书籍
  python generate_youtube_titles.py --uuid 12345678-abcd-efgh-ijkl-123456789012  # 处理指定UUID的书籍
  python generate_youtube_titles.py --preview                      # 预览模式
  python generate_youtube_titles.py --force                        # 强制重新生成

输出说明:
  - YouTube标题文件: /Volumes/dhl/audio/books/en/youtube_titles/{uuid}.txt
  - 标题格式: 书名 | Book Summary
  - 最大长度: 99字符
        """,
    )
    parser.add_argument("--uuid", "-u", help="要处理的书籍UUID，不指定则处理所有书籍")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="预览模式，只显示会生成的标题，不实际处理",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新生成所有标题文件，忽略已存在的文件",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式，显示详细信息",
    )

    args = parser.parse_args()

    # 获取目录配置
    directories = get_directories()

    print(f"\n📚 书籍YouTube标题生成器")
    print(f"📁 MP4目录: {directories['mp4']}")
    print(f"📁 书籍信息目录: {directories['info']}")
    print(f"📁 标题输出目录: {directories['titles']}")
    print(f"🚫 自动排除Mac系统文件 (.DS_Store等)")

    if args.uuid:
        print(f"📚 处理模式: 仅处理指定UUID书籍 ({args.uuid[:8]}...{args.uuid[-8:]})")
    else:
        print(f"📚 处理模式: 处理所有发现的书籍")

    if args.force:
        print(f"🔄 强制重新生成模式: 将重新生成所有标题文件")
    else:
        print(f"⚡ 断点续传模式: 将跳过已存在的标题文件")

    if args.preview:
        print(f"👁️  预览模式：只显示将要生成的标题")

    if args.debug:
        print(f"🐛 调试模式：启用详细日志")

    # 显示标题格式配置
    print(f"🎬 标题格式: 书名 | Book Summary")
    print(f"📏 最大长度: {MAX_TITLE_LENGTH} 字符")

    # 获取可用MP4文件列表
    if args.uuid:
        # 检查指定UUID的文件
        mp4_path = os.path.join(directories["mp4"], f"{args.uuid}.mp4")

        if not os.path.exists(mp4_path):
            print(f"❌ 指定UUID的MP4文件不存在: {mp4_path}")
            return

        if not is_valid_file(mp4_path, MIN_MP4_SIZE):
            print(f"❌ MP4文件无效: {mp4_path}")
            return

        available_mp4s = [(args.uuid, mp4_path)]
    else:
        available_mp4s = get_available_mp4_files(directories)

    if not available_mp4s:
        print("❌ 未找到可处理的MP4文件")
        return

    # 获取已存在的标题文件
    existing_titles = get_existing_titles(directories)

    # 过滤需要处理的书籍
    books_to_process = []
    for uuid, mp4_path in available_mp4s:
        needs_title = args.force or uuid not in existing_titles

        if needs_title:
            books_to_process.append((uuid, mp4_path))
        elif args.debug:
            print(f"⏭️  跳过已有标题的书籍: {uuid[:8]}...{uuid[-8:]}")

    if not books_to_process and not args.preview:
        print("✅ 所有书籍都已生成标题")
        return

    # 显示处理统计
    print(f"\n=== 📊 处理统计 ===")
    print(f"📹 总MP4文件数量: {len(available_mp4s)}")
    print(f"✅ 已有标题文件: {len(existing_titles)}")
    print(f"🎯 需要处理: {len(books_to_process)}")

    # 处理所有书籍
    all_results = []

    try:
        for uuid, mp4_path in tqdm(books_to_process, desc="📚 处理进度"):
            try:
                result = process_single_book(
                    uuid,
                    mp4_path,
                    directories,
                    args.force,
                    args.preview,
                    args.debug,
                )
                all_results.append(result)
            except Exception as e:
                print(f"❌ 处理书籍 UUID:{uuid[:8]}... 时出错: {e}")
                import traceback

                if args.debug:
                    traceback.print_exc()

        # 统计最终结果
        if all_results:
            print(f"\n=== 🎉 处理完成总结 ===")

            total_books = len(all_results)
            success_count = sum(1 for r in all_results if r["status"] == "success")
            failed_count = sum(1 for r in all_results if r["status"] == "failed")
            skipped_count = sum(1 for r in all_results if r["status"] == "skipped")
            preview_count = sum(1 for r in all_results if r["status"] == "preview")

            if args.preview:
                print(f"📊 预览统计:")
                print(f"  - 发现书籍总数: {total_books} 本")
                print(f"  - 需要处理: {preview_count} 本")
                print(f"  - 已完成跳过: {skipped_count} 本")

                print(f"\n📋 标题预览:")
                for result in all_results:
                    if result["status"] == "preview":
                        uuid = result["uuid"]
                        title = result.get("youtube_title", "无法生成")
                        length = result.get("title_length", 0)
                        print(f"  📚 UUID:{uuid[:8]}...{uuid[-8:]}")
                        print(f"     📖 书名: {result.get('book_title', '未知')}")
                        print(f"     🎬 标题: {title} ({length}/99)")
                        print()
            else:
                print(f"📊 处理统计:")
                print(f"  - 书籍总数: {total_books} 本")
                print(f"  - 生成成功: {success_count} 本")
                print(f"  - 处理失败: {failed_count} 本")
                print(f"  - 跳过文件: {skipped_count} 本")

                if total_books > 0:
                    success_rate = (success_count / total_books) * 100
                    print(f"  - 成功率: {success_rate:.1f}%")

                print(f"\n📋 详细结果:")
                for result in all_results:
                    uuid = result["uuid"]
                    status = result["status"]
                    if status == "success":
                        title = result.get("youtube_title", "")
                        length = result.get("title_length", 0)
                        print(
                            f"  ✅ UUID:{uuid[:8]}...{uuid[-8:]}: 成功生成标题 ({length}/99字符)"
                        )
                        if args.debug:
                            print(f"     🎬 {title}")
                    elif status == "failed":
                        reason = result.get("reason", "未知错误")
                        print(f"  ❌ UUID:{uuid[:8]}...{uuid[-8:]}: 失败 ({reason})")
                    elif status == "skipped":
                        print(f"  ⏭️  UUID:{uuid[:8]}...{uuid[-8:]}: 已存在，跳过")

                if success_count > 0:
                    print(f"\n📝 输出文件位置:")
                    print(f"📁 标题文件目录: {directories['titles']}")
                    print(f"💡 标题格式: 书名 | Book Summary (最大99字符)")

    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断了程序执行")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
