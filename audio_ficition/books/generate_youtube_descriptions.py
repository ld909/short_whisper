#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube视频描述生成脚本

功能说明：
1. 检查 merge_clips_with_audio.py 生成的合并视频文件
2. 读取对应的书籍总结文件
3. 使用 Google Gemini AI 生成专业的YouTube视频描述
4. 遵循特定的写作风格和结构要求
5. 自动保存生成的描述到对应目录
6. 支持中文(zh)和英文(en)两种语言主题

输入依赖文件：
• 合并视频文件（由merge_clips_with_audio.py生成）：
  - Intel Mac: /Volumes/dhl/audio/books/{language}/mp4_with_audio/{uuid}.mp4
  - Apple Silicon: /Users/donghaoliu/Documents/audio/books/{language}/mp4_with_audio/{uuid}.mp4
• 书籍总结文件（由generate_book_summary.py生成）：
  - Intel Mac: /Volumes/dhl/audio/books/{language}/summary/{uuid}.txt
  - Apple Silicon: /Users/donghaoliu/Documents/audio/books/{language}/summary/{uuid}.txt

输出目标文件：
• YouTube描述文件：
  - Intel Mac: /Volumes/dhl/audio/books/{language}/youtube_description/{uuid}.txt
  - Apple Silicon: /Users/donghaoliu/Documents/audio/books/{language}/youtube_description/{uuid}.txt

处理逻辑：
• 只有当MP4视频文件存在时，才会为对应的UUID生成YouTube描述
• 需要同时存在MP4文件和总结文件才能生成描述
• 确保视频制作完成后再生成对应的YouTube描述

使用方法：
python generate_youtube_descriptions.py --lang en                # 处理英文书籍
python generate_youtube_descriptions.py --lang zh                # 处理中文书籍
python generate_youtube_descriptions.py --count 10 --lang en     # 处理10个文件
python generate_youtube_descriptions.py --force --lang zh        # 强制重新生成
python generate_youtube_descriptions.py --uuid abc123 --lang en  # 处理指定UUID

前置条件：
• 环境变量UNI_API_KEY: 必须设置有效的API密钥
• 先决脚本: 需要运行merge_clips_with_audio.py生成MP4文件
• 先决脚本: 需要运行generate_book_summary.py生成总结文件
• 网络环境: 需要稳定的网络连接访问Gemini API
"""

import os
import sys
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


class YouTubeDescriptionGenerator:
    """YouTube视频描述生成器"""

    def __init__(self, debug=False, language="en"):
        self.debug = debug
        self.language = language
        self.base_media_path = get_base_media_path()
        self.books_base_path = os.path.join(self.base_media_path, "books", language)

        # 设置语言配置
        self.setup_language_config()

        # 目录结构
        self.mp4_dir = os.path.join(
            self.books_base_path, "mp4_with_audio"
        )  # MP4视频目录（输入依赖）
        self.summary_dir = os.path.join(self.books_base_path, "summary")  # 总结文件目录
        self.youtube_desc_dir = os.path.join(
            self.books_base_path, "youtube_description"
        )

        # 创建输出目录
        os.makedirs(self.youtube_desc_dir, exist_ok=True)

        # 设置Gemini客户端
        self.client = setup_gemini_client()

        # 系统提示词
        self.system_instruction = [
            "You are a content creator for a YouTube channel that produces audio summaries of important non-fiction books. Your writing style is the channel's brand: simple, direct, and sincere. You make profound ideas feel accessible and grounded, avoiding all marketing hype and jargon.",
            "Your task is to write a YouTube video description based on the script I provide.",
            "Adhere to these strict rules for every description you generate:",
            "RULE 1: TONE",
            "Write in a plain, earnest, and respectful voice. The style should be unpretentious but powerful. Use simple words to convey deep ideas. Avoid exclamation points and overly enthusiastic language.",
            "RULE 2: STRUCTURE",
            "Follow this 4 to 5 sentence structure precisely:",
            "Sentence 1 is the hook. Start with a relatable question or a powerful, thought-provoking statement that gets to the heart of the book's central problem.",
            "Sentence 2 is the introduction. Briefly introduce the book by its title and author, connecting it to the hook.",
            "Sentence 3 is the core idea. State the book's single most important argument or central thesis in a clear, straightforward way.",
            "Sentence 4 is the 'why'. Explain why this idea matters or how it challenges a common belief. Connect it to a universal human experience.",
            "Sentence 5 is optional. It can be a gentle call to discover more in the summary. It can sometimes be combined with sentence 4.",
            "RULE 3: LENGTH",
            "The entire description must be between 4 and 5 sentences long. No more, no less.",
            "RULE 4: FORMAT",
            "Your final output must be plain text only. Do not use any markdown symbols like asterisks for bolding, italics, or lists.",
            "RULE 5: Return content",
            "Direct return your description. No others.",
        ]

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

    def get_available_mp4_files(self):
        """获取所有可用的MP4视频文件"""
        mp4_files = {}

        if not os.path.exists(self.mp4_dir):
            print(f"❌ MP4视频目录不存在: {self.mp4_dir}")
            return mp4_files

        video_files = glob.glob(os.path.join(self.mp4_dir, "*.mp4"))

        for file_path in video_files:
            basename = os.path.basename(file_path)
            # 排除以点开头的文件（如.DS_Store等）
            if basename.startswith("."):
                continue

            if basename.endswith(".mp4"):
                uuid_val = basename[:-4]
                try:
                    # 检查文件大小，确保是有效的视频文件
                    file_size = os.path.getsize(file_path)
                    if file_size > 1024 * 1024:  # 至少1MB
                        mp4_files[uuid_val] = file_path
                        if self.debug:
                            print(f"✅ 发现MP4文件: {uuid_val}")
                    else:
                        if self.debug:
                            print(f"⚠️ MP4文件过小，跳过: {uuid_val}")
                except Exception as e:
                    if self.debug:
                        print(f"⚠️ 检查MP4文件失败 {file_path}: {e}")

        print(f"🎬 找到 {len(mp4_files)} 个有效的MP4视频文件")
        return mp4_files

    def get_existing_summaries(self):
        """获取已存在的总结文件"""
        summaries = {}

        if not os.path.exists(self.summary_dir):
            print(f"❌ 总结目录不存在: {self.summary_dir}")
            return summaries

        summary_files = glob.glob(os.path.join(self.summary_dir, "*.txt"))

        for file_path in summary_files:
            basename = os.path.basename(file_path)
            # 排除以点开头的文件（如.DS_Store等）
            if basename.startswith("."):
                continue

            if basename.endswith(".txt"):
                uuid_val = basename[:-4]
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    if content and len(content) > 100:  # 确保内容有意义
                        summaries[uuid_val] = content
                        if self.debug:
                            print(f"✅ 发现总结文件: {uuid_val}")
                except Exception as e:
                    if self.debug:
                        print(f"⚠️ 读取总结文件失败 {file_path}: {e}")

        print(f"📚 找到 {len(summaries)} 个有效的总结文件")
        return summaries

    def get_processable_books(self):
        """获取可处理的书籍（同时有MP4和总结文件）"""
        mp4_files = self.get_available_mp4_files()
        summaries = self.get_existing_summaries()

        # 找到同时有MP4和总结的书籍
        common_uuids = set(mp4_files.keys()) & set(summaries.keys())
        processable_books = {}

        for uuid_val in common_uuids:
            processable_books[uuid_val] = summaries[uuid_val]

        print(f"✅ 可处理的书籍: {len(processable_books)} 个（同时有MP4和总结文件）")

        if len(processable_books) != len(mp4_files):
            missing_summaries = set(mp4_files.keys()) - set(summaries.keys())
            if missing_summaries:
                print(f"⚠️ 有MP4但缺少总结文件的书籍: {len(missing_summaries)} 个")
                if self.debug:
                    for uuid_val in sorted(list(missing_summaries))[:5]:
                        print(f"   - {uuid_val}")
                    if len(missing_summaries) > 5:
                        print(f"   - ... 还有 {len(missing_summaries) - 5} 个")

        return processable_books

    def get_existing_descriptions(self):
        """获取已存在的YouTube描述文件"""
        existing_uuids = set()

        if os.path.exists(self.youtube_desc_dir):
            desc_files = glob.glob(os.path.join(self.youtube_desc_dir, "*.txt"))
            for desc_file in desc_files:
                basename = os.path.basename(desc_file)
                # 排除以点开头的文件
                if basename.startswith("."):
                    continue

                if basename.endswith(".txt"):
                    uuid_val = basename[:-4]
                    # 验证文件是否有效（大小大于50字节）
                    try:
                        if os.path.getsize(desc_file) > 50:
                            existing_uuids.add(uuid_val)
                            if self.debug:
                                print(f"✅ 发现现有描述: {uuid_val}")
                    except:
                        if self.debug:
                            print(f"⚠️ 检查描述文件失败: {uuid_val}")

        print(f"📊 找到 {len(existing_uuids)} 个已存在的YouTube描述")
        return existing_uuids

    def generate_youtube_description(self, summary_content, uuid_val, max_retries=3):
        """使用Google Gemini生成YouTube描述"""
        if not summary_content.strip():
            print(f"⚠️ 警告: 总结 {uuid_val} 内容为空，无法生成描述")
            return ""

        budget = 1024  # Thinking budget for Gemini

        for attempt in range(max_retries):
            try:
                print(
                    f"🤖 正在为 {uuid_val} 生成YouTube描述... (尝试 {attempt+1}/{max_retries})"
                )

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash-preview-04-17",
                    contents=f"书籍总结脚本：\n\n{summary_content}",
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        thinking_config=types.ThinkingConfig(
                            thinking_budget=budget, include_thoughts=True
                        ),
                    ),
                )

                result = response.text.strip()

                if result and len(result) > 50:  # 确保生成了有意义的内容
                    print(f"✅ 成功生成 {uuid_val} 的YouTube描述")
                    return result
                else:
                    print(f"⚠️ 生成的描述过短，重试...")
                    continue

            except Exception as e:
                print(f"❌ 生成YouTube描述出错 (尝试 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    retry_delay = (attempt + 1) * 3
                    print(f"⏳ 等待{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                else:
                    print(f"❌ 达到最大重试次数 ({max_retries})，跳过该文件")
                    return ""

    def save_youtube_description(self, uuid_val, description_content):
        """保存YouTube描述到文件"""
        if not description_content or not description_content.strip():
            print(f"⚠️ 警告: {uuid_val} 的描述内容为空，跳过保存")
            return False

        file_path = os.path.join(self.youtube_desc_dir, f"{uuid_val}.txt")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(description_content)

            # 验证文件是否成功写入
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"💾 已保存YouTube描述到: {file_path} (大小: {file_size} 字节)")
                return True
            else:
                print(f"❌ 文件保存后未找到: {file_path}")
                return False

        except Exception as e:
            print(f"❌ 保存YouTube描述到 {file_path} 时出错: {e}")
            return False

    def process_books(self, max_count=None, force=False, target_uuid=None):
        """批量处理书籍，生成YouTube描述"""
        print("🎬 YouTube视频描述生成器")
        print(f"🎥 MP4视频目录: {self.mp4_dir}")
        print(f"📁 总结目录: {self.summary_dir}")
        print(f"💾 描述保存目录: {self.youtube_desc_dir}")

        # 获取可处理的书籍（有MP4和总结文件）
        processable_books = self.get_processable_books()
        if not processable_books:
            print("❌ 没有找到可处理的书籍")
            print("💡 请确保:")
            print("   1. 运行 merge_clips_with_audio.py 生成MP4文件")
            print("   2. 运行 generate_book_summary.py 生成总结文件")
            return

        # 如果指定了特定UUID
        if target_uuid:
            if target_uuid in processable_books:
                processable_books = {target_uuid: processable_books[target_uuid]}
                print(f"🎯 处理指定UUID: {target_uuid}")
            else:
                print(f"❌ 未找到指定的UUID或该UUID缺少必要文件: {target_uuid}")
                return

        # 获取已存在的描述
        existing_descriptions = self.get_existing_descriptions()

        # 筛选需要处理的文件
        books_to_process = {}
        for uuid_val, content in processable_books.items():
            if force or uuid_val not in existing_descriptions:
                books_to_process[uuid_val] = content
            elif self.debug:
                print(f"⏭️ 跳过已存在的描述: {uuid_val}")

        # 限制处理数量
        if max_count and len(books_to_process) > max_count:
            # 按UUID排序，保证处理顺序一致
            sorted_uuids = sorted(books_to_process.keys())[:max_count]
            books_to_process = {
                uuid_val: books_to_process[uuid_val] for uuid_val in sorted_uuids
            }

        if not books_to_process:
            print("🎉 所有已完成的MP4文件的YouTube描述都已生成完成！")
            return

        print(f"\n📊 处理统计:")
        print(f"可处理书籍: {len(processable_books)}")
        print(f"已有描述: {len(existing_descriptions)}")
        print(f"需要处理: {len(books_to_process)}")

        # 开始处理
        success_count = 0
        failed_count = 0

        with tqdm(total=len(books_to_process), desc="🎬 生成YouTube描述") as pbar:
            for uuid_val, summary_content in books_to_process.items():
                try:
                    print(f"\n=== 处理 {uuid_val} ===")
                    print(f"总结长度: {len(summary_content)} 字符")

                    # 生成YouTube描述
                    description = self.generate_youtube_description(
                        summary_content, uuid_val
                    )

                    if description:
                        # 保存描述
                        if self.save_youtube_description(uuid_val, description):
                            success_count += 1
                            print(f"✅ {uuid_val} 处理成功")
                            # 显示描述预览
                            preview = (
                                description[:200] + "..."
                                if len(description) > 200
                                else description
                            )
                            print(f"📝 描述预览: {preview}")
                        else:
                            failed_count += 1
                            print(f"❌ {uuid_val} 保存失败")
                    else:
                        failed_count += 1
                        print(f"❌ {uuid_val} 生成失败")

                except KeyboardInterrupt:
                    print("⏹️ 用户中断，程序停止")
                    break
                except Exception as e:
                    print(f"❌ 处理 {uuid_val} 时出错: {e}")
                    failed_count += 1

                pbar.update(1)

                # API调用间隔，避免请求过快
                if uuid_val != list(books_to_process.keys())[-1]:  # 不是最后一个
                    time.sleep(2)

        # 最终统计
        print(f"\n🎯 YouTube描述生成完成!")
        print(f"✅ 成功: {success_count}")
        print(f"❌ 失败: {failed_count}")
        print(
            f"📊 成功率: {success_count/(success_count+failed_count)*100:.1f}%"
            if (success_count + failed_count) > 0
            else "N/A"
        )

    def check_status(self):
        """检查当前状态"""
        print("📊 当前状态检查")
        print(f"📁 基础路径: {self.books_base_path}")

        mp4_files = self.get_available_mp4_files()
        summaries = self.get_existing_summaries()
        processable_books = self.get_processable_books()
        existing_descriptions = self.get_existing_descriptions()

        print(f"🎥 MP4视频文件: {len(mp4_files)}")
        print(f"📚 总结文件数量: {len(summaries)}")
        print(f"✅ 可处理书籍: {len(processable_books)}")
        print(f"🎬 已生成描述: {len(existing_descriptions)}")

        # 计算待处理数量
        pending_count = len(processable_books) - len(existing_descriptions)
        print(f"⏳ 待处理数量: {pending_count}")

        if pending_count > 0:
            print("\n📋 待处理示例 (前5个):")
            pending_uuids = [
                uuid_val
                for uuid_val in processable_books.keys()
                if uuid_val not in existing_descriptions
            ]
            for i, uuid_val in enumerate(sorted(pending_uuids)[:5]):
                print(f"   {i+1}. {uuid_val}")
            if len(pending_uuids) > 5:
                print(f"   ... 还有 {len(pending_uuids) - 5} 个")

        # 显示阻塞的情况
        mp4_uuids = set(mp4_files.keys())
        summary_uuids = set(summaries.keys())

        blocked_by_summary = mp4_uuids - summary_uuids
        if blocked_by_summary:
            print(f"\n⚠️ 有MP4但缺少总结文件的书籍: {len(blocked_by_summary)} 个")
            print("   建议运行: python generate_book_summary.py")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="🎬 YouTube 视频描述生成器",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python generate_youtube_descriptions.py --lang en               # 处理英文书籍
  python generate_youtube_descriptions.py --lang zh               # 处理中文书籍
  python generate_youtube_descriptions.py --count 10 --lang en    # 处理10个文件
  python generate_youtube_descriptions.py --force --lang zh       # 强制重新生成
  python generate_youtube_descriptions.py --uuid abc123 --lang en # 处理指定UUID
  python generate_youtube_descriptions.py --status --lang zh      # 检查处理状态

注意:
- 需要设置环境变量 UNI_API_KEY
- 确保已运行 merge_clips_with_audio.py 生成MP4文件
- 确保已运行 generate_book_summary.py 生成总结文件
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
        "--count", "-c", type=int, help="要处理的描述数量（默认处理所有）"
    )
    parser.add_argument(
        "--force", "-f", action="store_true", help="强制重新生成已存在的描述"
    )
    parser.add_argument("--uuid", "-u", help="只处理指定UUID的书籍")
    parser.add_argument("--debug", "-d", action="store_true", help="启用调试模式")
    parser.add_argument("--status", "-s", action="store_true", help="检查当前处理状态")

    args = parser.parse_args()

    # 创建生成器实例
    generator = YouTubeDescriptionGenerator(debug=args.debug, language=args.lang)

    print("🎬 YouTube视频描述生成器")
    print("=" * 50)

    # 状态检查模式
    if args.status:
        generator.check_status()
        return

    # 处理书籍描述
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
