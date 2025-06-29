#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube视频标题生成脚本

功能说明：
1. 读取书籍信息文件（由book_info_scraper.py生成）
2. 使用 Google Gemini AI 生成吸引人的YouTube视频标题
3. 确保标题符合YouTube标准，不超过100字符
4. 自动保存生成的标题到对应目录
5. 支持中文(zh)和英文(en)两种语言主题

输入依赖文件：
• 书籍信息文件（由book_info_scraper.py生成）：
  - Intel Mac: /Volumes/dhl/audio/books/{language}/info/{uuid}.json
  - Apple Silicon: /Users/donghaoliu/Documents/audio/books/{language}/info/{uuid}.json

输出目标文件：
• YouTube标题文件：
  - Intel Mac: /Volumes/dhl/audio/books/{language}/youtube_titles/{uuid}.txt
  - Apple Silicon: /Users/donghaoliu/Documents/audio/books/{language}/youtube_titles/{uuid}.txt

使用方法：
python generate_youtube_titles.py --lang en               # 处理英文书籍
python generate_youtube_titles.py --lang zh               # 处理中文书籍
python generate_youtube_titles.py --count 10 --lang en    # 处理10个文件
python generate_youtube_titles.py --force --lang zh       # 强制重新生成
python generate_youtube_titles.py --uuid abc123 --lang en # 处理指定UUID

前置条件：
• 环境变量UNI_API_KEY: 必须设置有效的API密钥
• 先决脚本: 需要运行book_info_scraper.py生成书籍信息文件
• 网络环境: 需要稳定的网络连接访问Gemini API
"""

import os
import sys
import json
import time
import argparse
import platform
import glob
import re
from pathlib import Path
from tqdm import tqdm

# 导入Google Gemini相关模块
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ 缺少依赖模块，请安装: pip install google-genai")
    sys.exit(1)


def get_base_media_path():
    """根据系统类型返回基础媒体路径"""
    system = platform.system()

    if system == "Linux":  # Ubuntu/Linux
        return "/media/dhl/audio"
    elif system == "Darwin":  # macOS
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
    else:
        # 默认使用环境变量或默认路径
        return os.environ.get("AUDIO_BASE_DIR", "/Users/donghaoliu/Documents/audio")


def setup_gemini_client():
    """设置Google Gemini客户端并验证API密钥"""
    api_key = os.environ.get("UNI_API_KEY")

    if not api_key:
        print("❌ 错误: 未找到API密钥")
        print("请设置环境变量UNI_API_KEY")
        print("例如: export UNI_API_KEY='your-api-key'")
        sys.exit(1)

    try:
        client = genai.Client(
            http_options=types.HttpOptions(base_url="https://api.uniapi.io/gemini"),
            api_key=api_key,
        )
        return client
    except Exception as e:
        print(f"❌ 初始化Gemini客户端时出错: {e}")
        print("这可能是由于以下原因:")
        print("1. Google GenAI库版本不兼容，请尝试: pip install google-genai")
        print("2. API密钥格式不正确")
        print("3. 网络连接问题")
        sys.exit(1)


class YouTubeTitleGenerator:
    """YouTube标题生成器"""

    def __init__(self, debug=False, language="en"):
        self.debug = debug
        self.language = language
        self.base_media_path = get_base_media_path()
        self.books_base_path = os.path.join(self.base_media_path, "books", language)

        # 设置语言配置
        self.setup_language_config()

        # 目录结构
        self.info_dir = os.path.join(
            self.books_base_path, "info"
        )  # 书籍信息目录（输入依赖）
        self.youtube_title_dir = os.path.join(
            self.books_base_path, "youtube_titles"
        )  # YouTube标题文件目录（输出）

        # 创建输出目录
        os.makedirs(self.youtube_title_dir, exist_ok=True)

        # 设置Gemini客户端
        self.client = setup_gemini_client()

        print(f"🌍 语言主题: {self.language_name}")
        print(f"📁 书籍目录: {self.books_base_path}")

    def setup_language_config(self):
        """根据语种设置配置"""
        if self.language == "zh":
            # 中文配置
            self.language_name = "中文"
        else:
            # 英文配置（默认）
            self.language_name = "English"

    def process_books(self, max_count=None, force=False, target_uuid=None):
        """处理书籍标题"""
        stats = {
            "total_targets": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
        }

        if target_uuid:
            result = self.process_single_book(target_uuid, force)
            stats["total_targets"] = 1
            stats["successful"] = 1 if result["status"] == "success" else 0
            stats["failed"] = 1 if result["status"] == "failed" else 0
            stats["skipped"] = 1 if result["status"] == "skipped" else 0
            return stats

        if max_count is None:
            max_count = float("inf")

        for uuid in self.get_available_uuids():
            if max_count <= 0:
                break

            if not force and self.is_title_exists(uuid):
                stats["skipped"] += 1
                continue

            stats["total_targets"] += 1
            result = self.process_single_book(uuid, force)
            if result["status"] == "success":
                stats["successful"] += 1
            elif result["status"] == "failed":
                stats["failed"] += 1
            elif result["status"] == "skipped":
                stats["skipped"] += 1
            else:
                print(f"⚠️  [UUID:{uuid[:8]}...] 未知状态: {result}")

            max_count -= 1

        return stats

    def process_single_book(self, uuid, force=False):
        """处理单个书籍的YouTube标题生成"""
        print(f"\n=== 📚 处理书籍 UUID: {uuid[:8]}...{uuid[-8:]} ===")

        # 生成输出路径
        title_path = os.path.join(self.youtube_title_dir, f"{uuid}.txt")

        print(
            f"📁 书籍信息文件: {os.path.basename(os.path.join(self.info_dir, f'{uuid}.json'))}"
        )
        print(f"📁 标题文件: {os.path.basename(title_path)}")

        # 检查是否需要跳过（除非强制处理）
        title_exists = self.is_title_exists(uuid)

        if not force and title_exists:
            print(f"⏭️  [UUID:{uuid[:8]}...] 标题文件已存在，跳过处理")
            return {
                "uuid": uuid,
                "status": "skipped",
                "reason": "already_exists",
                "title_path": title_path,
            }

        # 加载书籍信息
        book_info = self.load_book_info(uuid)
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
        youtube_title = self.generate_youtube_title(book_info)
        print(f"🎬 YouTube标题: {youtube_title}")
        print(f"📏 标题长度: {len(youtube_title)}")

        # 实际处理 - 保存标题
        if self.save_title_to_file(uuid, youtube_title, self.youtube_title_dir):
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

    def get_available_uuids(self):
        """获取所有可用的书籍UUID"""
        mp4_dir = os.path.join(self.books_base_path, "mp4_with_audio")
        if not os.path.exists(mp4_dir):
            print(f"❌ MP4目录不存在: {mp4_dir}")
            return []

        # 获取所有MP4文件
        mp4_files = glob.glob(os.path.join(mp4_dir, "*.mp4"))
        available_uuids = []
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
                    available_uuids.append(uuid)
                else:
                    skipped_files.append(basename)

        if skipped_files:
            print(
                f"🚫 跳过 {len(skipped_files)} 个Mac系统文件: {', '.join(skipped_files[:5])}{'...' if len(skipped_files) > 5 else ''}"
            )

        print(f"📊 统计信息:")
        print(f"   - 找到MP4文件: {len(available_uuids)} 个")

        return available_uuids

    def load_book_info(self, uuid):
        """加载书籍信息"""
        info_file = os.path.join(self.info_dir, f"{uuid}.json")

        if not os.path.exists(info_file):
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

    def generate_youtube_title(self, book_info):
        """生成YouTube标题"""
        book_title = book_info.get("title", "")
        
        # 清理书名，移除多余的空白字符
        book_title = " ".join(book_title.split()).strip()

        if self.language == "zh":
            # 中文格式：书名 | 书籍总结
            # "书籍总结"是固定文本，只处理书名
            fixed_suffix = "书籍总结"
            
            # 计算固定部分的字符数：" | " + "书籍总结" = 6个字符
            fixed_chars = 3 + len(fixed_suffix)  # " | " + 书籍总结
            available_chars_for_title = 99 - fixed_chars  # 给书名留的字符数
            
            # 处理书名
            if len(book_title) > available_chars_for_title:
                # 如果书名太长，截断并添加省略号
                truncated_title = book_title[:available_chars_for_title-3].rstrip() + "..."
            else:
                truncated_title = book_title
            
            # 生成最终标题
            final_title = f"{truncated_title} | {fixed_suffix}"
        else:
            # 英文格式：保持原有逻辑
            title_template = "{}"
            
            # 计算可用于书名的最大字符数
            max_book_title_length = 100 - len(title_template.format(""))

            # 如果书名太长，截断并添加...
            if len(book_title) > max_book_title_length:
                # 为省略号留出空间
                truncate_length = max_book_title_length - 3
                book_title = book_title[:truncate_length].rstrip() + "..."

            # 生成最终标题
            final_title = title_template.format(book_title)

        # 最终检查长度（中文99字符，英文100字符）
        max_length = 99 if self.language == "zh" else 100
        if len(final_title) > max_length:
            # 如果仍然超长，再次截断
            final_title = final_title[:max_length-3].rstrip() + "..."

        return final_title

    def save_title_to_file(self, uuid, title, titles_dir):
        """保存标题到文件"""
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

    def is_title_exists(self, uuid):
        """检查标题文件是否存在"""
        title_path = os.path.join(self.youtube_title_dir, f"{uuid}.txt")
        return os.path.exists(title_path)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="📺 YouTube 标题生成器",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python generate_youtube_titles.py --lang en               # 处理英文书籍
  python generate_youtube_titles.py --lang zh               # 处理中文书籍
  python generate_youtube_titles.py --count 10 --lang en    # 处理10个文件
  python generate_youtube_titles.py --force --lang zh       # 强制重新生成
  python generate_youtube_titles.py --uuid abc123 --lang en # 处理指定UUID

注意:
- 需要设置环境变量 UNI_API_KEY
- 确保已运行 book_info_scraper.py 生成书籍信息文件
        """,
    )

    # 语言参数
    parser.add_argument(
        "--lang",
        "-l",
        choices=["en", "zh"],
        default="en",
        help="语言主题: en(英文) 或 zh(中文) [默认: en]",
    )

    parser.add_argument(
        "--count", "-c", type=int, help="要处理的标题数量（默认处理所有）"
    )
    parser.add_argument(
        "--force", "-f", action="store_true", help="强制重新生成已存在的标题"
    )
    parser.add_argument("--uuid", "-u", help="只处理指定UUID的书籍")
    parser.add_argument("--debug", "-d", action="store_true", help="启用调试模式")

    args = parser.parse_args()

    # 创建生成器实例
    generator = YouTubeTitleGenerator(debug=args.debug, language=args.lang)

    print("📺 YouTube标题生成器")
    print("=" * 50)

    # 处理书籍标题
    try:
        stats = generator.process_books(
            max_count=args.count, force=args.force, target_uuid=args.uuid
        )

        print(f"\n📊 处理完成统计:")
        print(f"  🎯 目标文件: {stats.get('total_targets', 0)} 个")
        print(f"  ✅ 成功生成: {stats.get('successful', 0)} 个")
        print(f"  ❌ 生成失败: {stats.get('failed', 0)} 个")
        print(f"  ⏭️ 跳过处理: {stats.get('skipped', 0)} 个")

        if stats.get("total_targets", 0) > 0:
            success_rate = (
                stats.get("successful", 0) / stats.get("total_targets", 1) * 100
            )
            print(f"  📈 成功率: {success_rate:.1f}%")

    except KeyboardInterrupt:
        print("\n⏹️ 用户中断处理")
    except Exception as e:
        print(f"\n❌ 处理过程中出错: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
