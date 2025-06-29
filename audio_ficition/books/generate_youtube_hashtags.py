#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube视频标签生成脚本

功能说明：
1. 读取 generate_youtube_descriptions.py 生成的YouTube描述文件
2. 使用 Google Gemini AI 生成SEO优化的hashtag标签
3. 自动保存生成的标签到对应目录
4. 支持中文(zh)和英文(en)两种语言主题

输入依赖文件：
• YouTube描述文件（由generate_youtube_descriptions.py生成）：
  - Intel Mac: /Volumes/dhl/audio/books/{language}/youtube_description/{uuid}.txt
  - Apple Silicon: /Users/donghaoliu/Documents/audio/books/{language}/youtube_description/{uuid}.txt

输出目标文件：
• YouTube hashtag文件：
  - Intel Mac: /Volumes/dhl/audio/books/{language}/youtube_hashtags/{uuid}.txt
  - Apple Silicon: /Users/donghaoliu/Documents/audio/books/{language}/youtube_hashtags/{uuid}.txt

使用方法：
python generate_youtube_hashtags.py --lang en               # 处理英文书籍
python generate_youtube_hashtags.py --lang zh               # 处理中文书籍
python generate_youtube_hashtags.py --count 10 --lang en    # 处理10个文件
python generate_youtube_hashtags.py --force --lang zh       # 强制重新生成
python generate_youtube_hashtags.py --uuid abc123 --lang en # 处理指定UUID

前置条件：
• 环境变量UNI_API_KEY: 必须设置有效的API密钥
• 先决脚本: 需要运行generate_youtube_descriptions.py生成描述文件
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


class YouTubeHashtagGenerator:
    """YouTube标签生成器"""

    def __init__(self, debug=False, language="en"):
        self.debug = debug
        self.language = language
        self.base_media_path = get_base_media_path()
        self.books_base_path = os.path.join(self.base_media_path, "books", language)

        # 设置语言配置
        self.setup_language_config()

        # 目录结构
        self.youtube_desc_dir = os.path.join(
            self.books_base_path, "youtube_description"
        )  # 描述文件目录（输入依赖）
        self.youtube_hashtag_dir = os.path.join(
            self.books_base_path, "youtube_hashtags"
        )  # hashtag文件目录（输出）

        # 创建输出目录
        os.makedirs(self.youtube_hashtag_dir, exist_ok=True)

        # 设置Gemini客户端
        self.client = setup_gemini_client()

        # 系统提示词
        self.system_instruction = [
            "You are a YouTube SEO expert specializing in creating hashtags for book summary videos.",
            "Your task is to generate exactly 10 relevant, SEO-optimized hashtags based on the video description I provide.",
            "Follow these rules:",
            "1. Generate exactly 10 hashtags, no more, no less",
            "2. Each hashtag should start with # symbol",
            "3. Focus on book-related, self-improvement, and educational themes",
            "4. Include a mix of broad and specific tags for maximum reach",
            "5. Consider trending topics in personal development and learning",
            "6. Keep hashtags concise but descriptive",
            "7. Use CamelCase for multi-word hashtags (e.g., #BookSummary)",
            "8. Include relevant genre or topic-specific tags",
            "9. Add popular general tags like #Books, #Learning, #SelfImprovement",
            "10. Return only the hashtags separated by spaces, nothing else"
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

    def get_available_description_files(self):
        """获取所有可用的YouTube描述文件"""
        description_files = {}

        if not os.path.exists(self.youtube_desc_dir):
            print(f"❌ YouTube描述目录不存在: {self.youtube_desc_dir}")
            return description_files

        desc_files = glob.glob(os.path.join(self.youtube_desc_dir, "*.txt"))

        for file_path in desc_files:
            basename = os.path.basename(file_path)
            # 排除以点开头的文件（如.DS_Store等Mac垃圾文件）
            if basename.startswith("."):
                if self.debug:
                    print(f"⏭️ 跳过点开头文件: {basename}")
                continue

            if basename.endswith(".txt"):
                uuid_val = basename[:-4]
                try:
                    # 读取文件内容并检查有效性
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()

                    if content and len(content) > 50:  # 确保内容有意义
                        description_files[uuid_val] = content
                        if self.debug:
                            print(f"✅ 发现描述文件: {uuid_val}")
                    else:
                        if self.debug:
                            print(f"⚠️ 描述文件内容过短，跳过: {uuid_val}")
                except Exception as e:
                    if self.debug:
                        print(f"⚠️ 读取描述文件失败 {file_path}: {e}")

        print(f"📄 找到 {len(description_files)} 个有效的YouTube描述文件")
        return description_files

    def get_existing_hashtags(self):
        """获取已存在的hashtag文件"""
        existing_uuids = set()

        if os.path.exists(self.youtube_hashtag_dir):
            hashtag_files = glob.glob(os.path.join(self.youtube_hashtag_dir, "*.txt"))
            for hashtag_file in hashtag_files:
                basename = os.path.basename(hashtag_file)
                # 排除以点开头的文件
                if basename.startswith("."):
                    continue

                if basename.endswith(".txt"):
                    uuid_val = basename[:-4]
                    # 验证文件是否有效（大小大于20字节，确保有hashtag内容）
                    try:
                        if os.path.getsize(hashtag_file) > 20:
                            existing_uuids.add(uuid_val)
                            if self.debug:
                                print(f"✅ 发现现有hashtag: {uuid_val}")
                    except:
                        if self.debug:
                            print(f"⚠️ 检查hashtag文件失败: {uuid_val}")

        print(f"🏷️ 找到 {len(existing_uuids)} 个已存在的hashtag文件")
        return existing_uuids

    def generate_youtube_hashtags(self, description_content, uuid_val, max_retries=3):
        """使用Google Gemini生成YouTube hashtag"""
        if not description_content.strip():
            print(f"⚠️ 警告: 描述 {uuid_val} 内容为空，无法生成hashtag")
            return ""

        budget = 512  # Thinking budget for Gemini

        for attempt in range(max_retries):
            try:
                print(
                    f"🏷️ 正在为 {uuid_val} 生成YouTube hashtag... (尝试 {attempt+1}/{max_retries})"
                )

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash-preview-04-17",
                    contents=f"视频描述内容：\n\n{description_content}",
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        thinking_config=types.ThinkingConfig(
                            thinking_budget=budget, include_thoughts=True
                        ),
                    ),
                )

                result = response.text.strip()

                # 验证生成的hashtag格式
                if result and self.validate_hashtags(result):
                    print(f"✅ 成功生成 {uuid_val} 的YouTube hashtag")
                    return result
                else:
                    print(f"⚠️ 生成的hashtag格式不正确，重试...")
                    if self.debug:
                        print(f"   返回内容: {result}")
                    continue

            except Exception as e:
                print(
                    f"❌ 生成YouTube hashtag出错 (尝试 {attempt+1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    retry_delay = (attempt + 1) * 3
                    print(f"⏳ 等待{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                else:
                    print(f"❌ 达到最大重试次数 ({max_retries})，跳过该文件")
                    return ""

    def validate_hashtags(self, hashtag_text):
        """验证hashtag格式是否正确"""
        if not hashtag_text or not hashtag_text.strip():
            return False

        # 检查是否包含#符号
        if "#" not in hashtag_text:
            return False

        # 简单检查hashtag数量（应该大约10个）
        hashtag_count = hashtag_text.count("#")
        if hashtag_count < 8 or hashtag_count > 12:  # 允许一些误差
            if self.debug:
                print(f"   Hashtag数量不符合要求: {hashtag_count}")
            return False

        # 检查格式是否合理（不应该有多行）
        if "\n" in hashtag_text.strip():
            if self.debug:
                print(f"   Hashtag包含多行")
            return False

        return True

    def save_youtube_hashtags(self, uuid_val, hashtag_content):
        """保存YouTube hashtag到文件"""
        if not hashtag_content or not hashtag_content.strip():
            print(f"⚠️ 警告: {uuid_val} 的hashtag内容为空，跳过保存")
            return False

        file_path = os.path.join(self.youtube_hashtag_dir, f"{uuid_val}.txt")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(hashtag_content.strip())

            # 验证文件是否成功写入
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(
                    f"💾 已保存YouTube hashtag到: {file_path} (大小: {file_size} 字节)"
                )
                return True
            else:
                print(f"❌ 文件保存后未找到: {file_path}")
                return False

        except Exception as e:
            print(f"❌ 保存YouTube hashtag到 {file_path} 时出错: {e}")
            return False

    def process_descriptions(self, max_count=None, force=False, target_uuid=None):
        """批量处理描述文件，生成YouTube hashtag"""
        print("🏷️ YouTube Hashtag生成器")
        print(f"📄 描述文件目录: {self.youtube_desc_dir}")
        print(f"💾 Hashtag保存目录: {self.youtube_hashtag_dir}")

        # 获取可用的描述文件
        description_files = self.get_available_description_files()
        if not description_files:
            print("❌ 没有找到可处理的YouTube描述文件")
            print("💡 请确保:")
            print("   1. 运行 generate_youtube_descriptions.py 生成描述文件")
            print("   2. 描述文件内容有效且长度大于50字符")
            return {
                'total_targets': 0,
                'successful': 0,
                'failed': 0,
                'skipped': 0
            }

        # 如果指定了特定UUID
        if target_uuid:
            if target_uuid in description_files:
                description_files = {target_uuid: description_files[target_uuid]}
                print(f"🎯 处理指定UUID: {target_uuid}")
            else:
                print(f"❌ 未找到指定的UUID的描述文件: {target_uuid}")
                return {
                    'total_targets': 0,
                    'successful': 0,
                    'failed': 0,
                    'skipped': 0
                }

        # 获取已存在的hashtag
        existing_hashtags = self.get_existing_hashtags()

        # 筛选需要处理的文件
        files_to_process = {}
        for uuid_val, content in description_files.items():
            if force or uuid_val not in existing_hashtags:
                files_to_process[uuid_val] = content
            elif self.debug:
                print(f"⏭️ 跳过已存在的hashtag: {uuid_val}")

        # 限制处理数量
        if max_count and len(files_to_process) > max_count:
            # 按UUID排序，保证处理顺序一致
            sorted_uuids = sorted(files_to_process.keys())[:max_count]
            files_to_process = {
                uuid_val: files_to_process[uuid_val] for uuid_val in sorted_uuids
            }

        if not files_to_process:
            print("🎉 所有描述文件的YouTube hashtag都已生成完成！")
            return {
                'total_targets': 0,
                'successful': 0,
                'failed': 0,
                'skipped': len(description_files)
            }

        print(f"\n📊 处理统计:")
        print(f"可处理描述: {len(description_files)}")
        print(f"已有hashtag: {len(existing_hashtags)}")
        print(f"需要处理: {len(files_to_process)}")

        # 开始处理
        success_count = 0
        failed_count = 0

        with tqdm(total=len(files_to_process), desc="🏷️ 生成YouTube hashtag") as pbar:
            for uuid_val, description_content in files_to_process.items():
                try:
                    print(f"\n=== 处理 {uuid_val} ===")
                    print(f"描述长度: {len(description_content)} 字符")

                    # 生成YouTube hashtag
                    hashtags = self.generate_youtube_hashtags(
                        description_content, uuid_val
                    )

                    if hashtags:
                        # 保存hashtag
                        if self.save_youtube_hashtags(uuid_val, hashtags):
                            success_count += 1
                            print(f"✅ {uuid_val} 处理成功")
                            # 显示hashtag预览
                            print(f"🏷️ Hashtag: {hashtags}")
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
                if uuid_val != list(files_to_process.keys())[-1]:  # 不是最后一个
                    time.sleep(2)

        # 最终统计
        print(f"\n🎯 YouTube hashtag生成完成!")
        print(f"✅ 成功: {success_count}")
        print(f"❌ 失败: {failed_count}")
        print(
            f"📊 成功率: {success_count/(success_count+failed_count)*100:.1f}%"
            if (success_count + failed_count) > 0
            else "N/A"
        )
        
        # 返回统计信息
        return {
            'total_targets': len(files_to_process),
            'successful': success_count,
            'failed': failed_count,
            'skipped': len(description_files) - len(files_to_process)
        }

    def check_status(self):
        """检查当前状态"""
        print("📊 当前状态检查")
        print(f"📁 基础路径: {self.books_base_path}")

        description_files = self.get_available_description_files()
        existing_hashtags = self.get_existing_hashtags()

        print(f"📄 描述文件数量: {len(description_files)}")
        print(f"🏷️ 已生成hashtag: {len(existing_hashtags)}")

        # 计算待处理数量
        pending_count = len(description_files) - len(existing_hashtags)
        print(f"⏳ 待处理数量: {pending_count}")

        if pending_count > 0:
            print("\n📋 待处理示例 (前5个):")
            pending_uuids = [
                uuid_val
                for uuid_val in description_files.keys()
                if uuid_val not in existing_hashtags
            ]
            for i, uuid_val in enumerate(sorted(pending_uuids)[:5]):
                print(f"   {i+1}. {uuid_val}")
            if len(pending_uuids) > 5:
                print(f"   ... 还有 {len(pending_uuids) - 5} 个")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="🏷️ YouTube 标签生成器",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python generate_youtube_hashtags.py --lang en               # 处理英文书籍
  python generate_youtube_hashtags.py --lang zh               # 处理中文书籍
  python generate_youtube_hashtags.py --count 10 --lang en    # 处理10个文件
  python generate_youtube_hashtags.py --force --lang zh       # 强制重新生成
  python generate_youtube_hashtags.py --uuid abc123 --lang en # 处理指定UUID

注意:
- 需要设置环境变量 UNI_API_KEY
- 确保已运行 generate_youtube_descriptions.py 生成描述文件
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
        "--count", "-c", type=int, help="要处理的标签数量（默认处理所有）"
    )
    parser.add_argument(
        "--force", "-f", action="store_true", help="强制重新生成已存在的标签"
    )
    parser.add_argument("--uuid", "-u", help="只处理指定UUID的书籍")
    parser.add_argument("--debug", "-d", action="store_true", help="启用调试模式")

    args = parser.parse_args()

    # 创建生成器实例
    generator = YouTubeHashtagGenerator(debug=args.debug, language=args.lang)

    print("🏷️ YouTube标签生成器")
    print("=" * 50)

    # 检查API密钥
    if not os.environ.get("UNI_API_KEY"):
        print("❌ 未设置UNI_API_KEY环境变量")
        return

    # 确定处理参数
    max_count = args.count
    force = args.force
    target_uuid = args.uuid

    if max_count:
        print(f"🎯 处理数量: {max_count}")
    if force:
        print(f"🔄 强制重新生成模式")
    if target_uuid:
        print(f"🎯 目标UUID: {target_uuid}")

    try:
        generator.process_descriptions(
            max_count=max_count, force=force, target_uuid=target_uuid
        )
    except KeyboardInterrupt:
        print("👋 程序已停止")
    except Exception as e:
        print(f"❌ 程序出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
