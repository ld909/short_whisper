#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube视频内容生成统一脚本

功能说明：
这是一个统一的脚本，整合了三个YouTube内容生成功能：
1. 生成YouTube视频标题 (titles)
2. 生成YouTube视频描述 (descriptions)
3. 生成YouTube hashtag标签 (hashtags)

支持功能：
• 单独生成某种类型的内容
• 批量生成所有类型的内容（pipeline模式）
• 支持中文(zh)和英文(en)两种语言主题
• 断点续传，跳过已生成的内容
• 强制重新生成模式

输入依赖文件：
• 标题生成依赖：
  - 书籍信息文件：{base_path}/books/{lang}/info/{uuid}.json
  - 书籍总结文件：{base_path}/books/{lang}/summary/{uuid}.txt
• 描述生成依赖：
  - MP4视频文件：{base_path}/books/{lang}/mp4_with_audio/{uuid}.mp4
  - 书籍总结文件：{base_path}/books/{lang}/summary/{uuid}.txt
• 标签生成依赖：
  - YouTube描述文件：{base_path}/books/{lang}/youtube_description/{uuid}.txt

输出目标文件：
• YouTube标题文件：{base_path}/books/{lang}/youtube_titles/{uuid}.txt
• YouTube描述文件：{base_path}/books/{lang}/youtube_description/{uuid}.txt
• YouTube标签文件：{base_path}/books/{lang}/youtube_hashtags/{uuid}.txt

使用方法：
# 生成所有类型内容（推荐的pipeline模式）
python generate_youtube_content.py --lang en --type all

# 单独生成特定类型
python generate_youtube_content.py --lang en --type titles        # 仅生成标题
python generate_youtube_content.py --lang zh --type descriptions  # 仅生成描述
python generate_youtube_content.py --lang en --type hashtags      # 仅生成标签

# 其他选项
python generate_youtube_content.py --lang en --type all --count 10    # 处理10个文件
python generate_youtube_content.py --lang zh --type all --force       # 强制重新生成
python generate_youtube_content.py --lang en --type descriptions --uuid abc123  # 处理指定UUID

前置条件：
• 环境变量UNI_API_KEY: 必须设置有效的API密钥
• 根据生成类型，需要相应的先决脚本已运行
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


def is_mac_system_file(filename):
    """检查是否是Mac系统文件"""
    return filename.startswith(".") or filename.startswith("._")


class YouTubeContentGenerator:
    """YouTube内容生成器统一类"""

    def __init__(self, debug=False, language="en"):
        self.debug = debug
        self.language = language
        self.base_media_path = get_base_media_path()
        self.books_base_path = os.path.join(self.base_media_path, "books", language)

        # 设置语言配置
        self.setup_language_config()

        # 目录结构
        self.info_dir = os.path.join(self.books_base_path, "info")
        self.summary_dir = os.path.join(self.books_base_path, "summary")
        self.mp4_dir = os.path.join(self.books_base_path, "mp4_with_audio")
        self.youtube_title_dir = os.path.join(self.books_base_path, "youtube_titles")
        self.youtube_desc_dir = os.path.join(
            self.books_base_path, "youtube_description"
        )
        self.youtube_hashtag_dir = os.path.join(
            self.books_base_path, "youtube_hashtags"
        )

        # 创建输出目录
        for output_dir in [
            self.youtube_title_dir,
            self.youtube_desc_dir,
            self.youtube_hashtag_dir,
        ]:
            os.makedirs(output_dir, exist_ok=True)

        # 设置Gemini客户端
        self.client = setup_gemini_client()

        print(f"🌍 语言主题: {self.language_name}")
        print(f"📁 书籍目录: {self.books_base_path}")

    def setup_language_config(self):
        """根据语种设置配置"""
        if self.language == "zh":
            self.language_name = "中文"
            self.setup_chinese_prompts()
        else:
            self.language_name = "English"
            self.setup_english_prompts()

    def setup_chinese_prompts(self):
        """设置中文提示词"""
        # 标题生成提示词
        self.title_prompt_template = """# 角色与目标
你是一位世界顶级的 YouTube 内容策略专家和文案大师。你的任务是为一个书籍总结音频频道，创作一个具有病毒式传播潜力的、可以直接使用的最终视频标题。你深谙人性心理学和第一性原理，能精准地激发观众的好奇心，让他们在看到标题的瞬间就产生强烈的点击欲望。

# 背景信息
我的 YouTube 频道内容是书籍的精华总结音频。我需要你为我生成一个极具吸引力的视频标题。

# 核心任务
根据我提供的书名和书籍核心思想，直接生成 1 个最能激发点击欲望的最终 YouTube 标题。

# 生成指令与原则
你生成的标题必须综合运用以下原则，并选择最优角度进行创作：

运用第一性原理：
直击本质： 提炼出书中最根本、最颠覆性的核心观点。

运用心理学扳机：
制造知识鸿沟： 透露部分信息，但隐藏关键部分。
承诺收益/解决痛点： 清晰地告诉观众能获得什么或解决什么问题。
提出一个意想不到的问题： 用一个引人深思的问题开头。
揭示秘密/设定框架： 让观众感觉将要了解到少数人才知道的"秘密"。

# 格式与要求
直接返回最终标题： 你只需要返回最终的那一句话标题，它将作为视频的完整标题。
无需解释： 不需要任何解释、分析或备选选项。
包含书名： 生成的话术中必须清晰地包含完整的书名。

# 我将提供的内容
书名： {book_title}
书籍核心思想：{summary_content}"""

        # 描述生成提示词
        self.description_instruction = [
            "你是一个专门制作重要非虚构类书籍音频总结的YouTube频道的内容创作者。你的写作风格是频道的品牌：简单、直接、真诚。你让深刻的思想变得易于理解和实用，避免所有营销炒作和行话。",
            "你的任务是根据我提供的脚本来撰写YouTube视频描述。",
            "严格遵守这些规则来生成每一个描述：",
            "规则1：语调",
            "用朴实、认真、尊重的语调写作。风格应该谦逊但有力。用简单的词语传达深刻的思想。避免感叹号和过于热情的语言。",
            "规则2：结构",
            "严格按照这个4到5句话的结构：",
            "第1句是钩子。以一个相关的问题或有力的、发人深省的陈述开始，直达书籍核心问题的要害。",
            "第2句是介绍。简要介绍书名和作者，将其与钩子联系起来。",
            "第3句是核心思想。清楚、直接地陈述书籍最重要的论点或中心论题。",
            "第4句是「为什么」。解释为什么这个想法重要，或者它如何挑战一个普遍信念。将其与普遍的人类经验联系起来。",
            "第5句是可选的。可以是一个温和的号召，邀请读者在总结中发现更多。有时可以与第4句合并。",
            "规则3：长度",
            "整个描述必须是4到5句话长。不多不少。",
            "规则4：格式",
            "你的最终输出必须只是纯文本。不要使用任何markdown符号，如星号加粗、斜体或列表。",
            "规则5：返回内容",
            "直接返回你的描述。不要其他任何内容。",
        ]

        # 标签生成提示词
        self.hashtag_instruction = [
            "你是一位专门为书籍总结视频创建标签的YouTube SEO专家。",
            "你的任务是根据我提供的视频描述，生成恰好10个相关的、SEO优化的标签。",
            "请遵循以下规则：",
            "1. 生成恰好10个标签，不多不少",
            "2. 每个标签都应以#符号开头",
            "3. 专注于书籍相关、自我提升和教育主题",
            "4. 包含广泛和具体标签的组合，以获得最大影响力",
            "5. 考虑个人发展和学习领域的热门话题",
            "6. 保持标签简洁但具有描述性",
            "7. 多词标签使用驼峰命名法（例如：#读书笔记）",
            "8. 包含相关的类型或主题特定标签",
            "9. 添加流行的通用标签，如#读书、#学习、#自我提升",
            "10. 只返回用空格分隔的标签，不要其他内容",
        ]

    def setup_english_prompts(self):
        """设置英文提示词"""
        # 标题生成提示词
        self.title_prompt_template = """# Task
Create a compelling YouTube title for a book summary. Aim for 70-90 characters - long enough to be descriptive, short enough to be punchy.

# Requirements
- MUST include book title: "{book_title}"
- Target length: 70-90 characters (optimal range)
- Maximum 100 characters (hard limit)
- Balance information with curiosity
- Use compelling but not excessive language
- Include specific benefits or revelations

# Style Examples (BALANCED LENGTH):
- "Why [Book] Will Change How You Think About Success Forever"
- "The Shocking Truth Behind [Book] That Nobody Talks About"
- "[Book]: The Revolutionary Ideas That Challenge Everything We Know"
- "How [Book] Reveals the Hidden Psychology of Human Behavior"
- "The Life-Changing Lessons from [Book] You Need to Hear"
- "[Book] Exposes the Secrets of [Core Topic] - Mind Blowing!"

# Psychology Triggers (Use strategically):
1. Transformation: "Change How You Think", "Revolutionary Ideas"
2. Forbidden knowledge: "Hidden Truth", "Nobody Talks About"
3. Challenge conventional: "Challenge Everything", "Shocking Truth"
4. Personal benefit: "Life-Changing", "You Need to Hear"
5. Exclusive insight: "Reveals", "Exposes", "Behind the Scenes"

# Book Core Ideas:
{summary_content}

# Output
Return ONLY the final title (70-90 chars preferred, max 100). No explanations."""

        # 描述生成提示词
        self.description_instruction = [
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

        # 标签生成提示词
        self.hashtag_instruction = [
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
            "10. Return only the hashtags separated by spaces, nothing else",
        ]

    # ======================== 文件获取与检查方法 ========================

    def get_available_uuids(self):
        """获取所有可用的书籍UUID（基于MP4文件）"""
        if not os.path.exists(self.mp4_dir):
            print(f"❌ MP4目录不存在: {self.mp4_dir}")
            return []

        mp4_files = glob.glob(os.path.join(self.mp4_dir, "*.mp4"))
        available_uuids = []

        for mp4_file in mp4_files:
            basename = os.path.basename(mp4_file)

            # 跳过Mac系统文件
            if is_mac_system_file(basename):
                continue

            if basename.endswith(".mp4"):
                uuid = basename[:-4]
                if len(uuid) == 36 and uuid.count("-") == 4:  # 简单UUID格式验证
                    available_uuids.append(uuid)

        if self.debug:
            print(f"📊 找到 {len(available_uuids)} 个可用的MP4文件")

        return sorted(available_uuids)

    def load_book_info(self, uuid):
        """加载书籍信息"""
        info_file = os.path.join(self.info_dir, f"{uuid}.json")

        if not os.path.exists(info_file):
            return None

        try:
            with open(info_file, "r", encoding="utf-8") as f:
                book_info = json.load(f)

            if not book_info.get("title"):
                if self.debug:
                    print(f"⚠️ 书籍信息缺少标题: {uuid[:8]}...")
                return None

            return book_info
        except Exception as e:
            if self.debug:
                print(f"❌ 读取书籍信息失败 {uuid[:8]}...: {e}")
            return None

    def load_book_summary(self, uuid):
        """加载书籍总结"""
        summary_file = os.path.join(self.summary_dir, f"{uuid}.txt")

        if not os.path.exists(summary_file):
            return None

        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if len(content) < 100:
                return None

            return content
        except Exception as e:
            if self.debug:
                print(f"⚠️ 读取总结文件失败 {uuid[:8]}...: {e}")
            return None

    def load_description(self, uuid):
        """加载YouTube描述"""
        desc_file = os.path.join(self.youtube_desc_dir, f"{uuid}.txt")

        if not os.path.exists(desc_file):
            return None

        try:
            with open(desc_file, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if len(content) < 50:
                return None

            return content
        except Exception as e:
            if self.debug:
                print(f"⚠️ 读取描述文件失败 {uuid[:8]}...: {e}")
            return None

    def check_file_exists(self, uuid, content_type):
        """检查指定类型的文件是否存在"""
        if content_type == "titles":
            file_path = os.path.join(self.youtube_title_dir, f"{uuid}.txt")
        elif content_type == "descriptions":
            file_path = os.path.join(self.youtube_desc_dir, f"{uuid}.txt")
        elif content_type == "hashtags":
            file_path = os.path.join(self.youtube_hashtag_dir, f"{uuid}.txt")
        else:
            return False

        return os.path.exists(file_path) and os.path.getsize(file_path) > 20

    # ======================== AI生成方法 ========================

    def generate_title_with_ai(self, book_title, summary_content):
        """使用AI生成YouTube标题"""
        if len(summary_content) > 3000:
            summary_content = summary_content[:3000] + "..."

        prompt = self.title_prompt_template.format(
            book_title=book_title, summary_content=summary_content
        )

        try:
            response = self.client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=200,
                    top_p=0.9,
                ),
            )

            if response and response.text:
                generated_title = response.text.strip()
                generated_title = generated_title.replace("\n", " ").replace("\r", " ")
                generated_title = " ".join(generated_title.split())

                # 长度检查
                max_length = 99 if self.language == "zh" else 100
                if len(generated_title) > max_length:
                    generated_title = generated_title[: max_length - 3] + "..."

                return generated_title

        except Exception as e:
            print(f"❌ AI生成标题失败: {e}")

        return None

    def generate_description_with_ai(self, summary_content):
        """使用AI生成YouTube描述"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-preview-04-17",
                contents=f"书籍总结脚本：\n\n{summary_content}",
                config=types.GenerateContentConfig(
                    system_instruction=self.description_instruction,
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=1024, include_thoughts=True
                    ),
                ),
            )

            if response and response.text:
                result = response.text.strip()
                if len(result) > 50:
                    return result

        except Exception as e:
            print(f"❌ AI生成描述失败: {e}")

        return None

    def generate_hashtags_with_ai(self, description_content):
        """使用AI生成YouTube hashtag"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-preview-04-17",
                contents=f"视频描述内容：\n\n{description_content}",
                config=types.GenerateContentConfig(
                    system_instruction=self.hashtag_instruction,
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=512, include_thoughts=True
                    ),
                ),
            )

            if response and response.text:
                result = response.text.strip()
                if self.validate_hashtags(result):
                    return result

        except Exception as e:
            print(f"❌ AI生成hashtag失败: {e}")

        return None

    def validate_hashtags(self, hashtag_text):
        """验证hashtag格式"""
        if not hashtag_text or "#" not in hashtag_text:
            return False

        hashtag_count = hashtag_text.count("#")
        if hashtag_count < 8 or hashtag_count > 12:
            return False

        if "\n" in hashtag_text.strip():
            return False

        return True

    # ======================== 文件保存方法 ========================

    def save_content_to_file(self, uuid, content, content_type):
        """保存内容到文件"""
        if content_type == "titles":
            file_path = os.path.join(self.youtube_title_dir, f"{uuid}.txt")
        elif content_type == "descriptions":
            file_path = os.path.join(self.youtube_desc_dir, f"{uuid}.txt")
        elif content_type == "hashtags":
            file_path = os.path.join(self.youtube_hashtag_dir, f"{uuid}.txt")
        else:
            return False

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(
                    f"💾 已保存{content_type}到: {os.path.basename(file_path)} (大小: {file_size} 字节)"
                )
                return True

        except Exception as e:
            print(f"❌ 保存{content_type}失败 {uuid[:8]}...: {e}")

        return False

    # ======================== 主要处理方法 ========================

    def process_single_item(self, uuid, content_type, force=False):
        """处理单个书籍的指定内容类型"""
        print(f"\n=== 📚 处理 {content_type} - UUID: {uuid[:8]}...{uuid[-8:]} ===")

        # 检查是否需要跳过
        if not force and self.check_file_exists(uuid, content_type):
            print(f"⏭️ {content_type}文件已存在，跳过处理")
            return {"status": "skipped", "reason": "already_exists"}

        # 根据内容类型执行不同的处理逻辑
        if content_type == "titles":
            return self.process_title(uuid)
        elif content_type == "descriptions":
            return self.process_description(uuid)
        elif content_type == "hashtags":
            return self.process_hashtag(uuid)
        else:
            return {"status": "failed", "reason": "invalid_content_type"}

    def process_title(self, uuid):
        """处理标题生成"""
        # 加载书籍信息
        book_info = self.load_book_info(uuid)
        if not book_info:
            print(f"❌ 无法加载书籍信息")
            return {"status": "failed", "reason": "no_book_info"}

        book_title = book_info.get("title", "")
        print(f"📖 书名: {book_title}")

        # 加载书籍总结
        summary_content = self.load_book_summary(uuid)
        if not summary_content:
            print(f"⚠️ 未找到书籍总结，使用简化标题格式")
            # 简化标题格式
            max_length = 99 if self.language == "zh" else 100
            if len(book_title) > max_length - 3:
                youtube_title = book_title[: max_length - 6] + "..."
            else:
                youtube_title = book_title
        else:
            # 使用AI生成标题
            youtube_title = self.generate_title_with_ai(book_title, summary_content)
            if not youtube_title:
                print(f"⚠️ AI生成失败，使用简化标题格式")
                max_length = 99 if self.language == "zh" else 100
                if len(book_title) > max_length - 3:
                    youtube_title = book_title[: max_length - 6] + "..."
                else:
                    youtube_title = book_title

        print(f"🎬 YouTube标题: {youtube_title}")
        print(f"📏 标题长度: {len(youtube_title)}")

        # 保存标题
        if self.save_content_to_file(uuid, youtube_title, "titles"):
            return {"status": "success", "title": youtube_title}
        else:
            return {"status": "failed", "reason": "save_failed"}

    def process_description(self, uuid):
        """处理描述生成"""
        # 加载书籍总结
        summary_content = self.load_book_summary(uuid)
        if not summary_content:
            print(f"❌ 无法加载书籍总结")
            return {"status": "failed", "reason": "no_summary"}

        print(f"📚 总结长度: {len(summary_content)} 字符")

        # 使用AI生成描述
        description = self.generate_description_with_ai(summary_content)
        if not description:
            print(f"❌ AI生成描述失败")
            return {"status": "failed", "reason": "ai_generation_failed"}

        print(
            f"📝 描述预览: {description[:200]}{'...' if len(description) > 200 else ''}"
        )

        # 保存描述
        if self.save_content_to_file(uuid, description, "descriptions"):
            return {"status": "success", "description": description}
        else:
            return {"status": "failed", "reason": "save_failed"}

    def process_hashtag(self, uuid):
        """处理hashtag生成"""
        # 加载描述文件
        description_content = self.load_description(uuid)
        if not description_content:
            print(f"❌ 无法加载YouTube描述文件")
            return {"status": "failed", "reason": "no_description"}

        print(f"📄 描述长度: {len(description_content)} 字符")

        # 使用AI生成hashtag
        hashtags = self.generate_hashtags_with_ai(description_content)
        if not hashtags:
            print(f"❌ AI生成hashtag失败")
            return {"status": "failed", "reason": "ai_generation_failed"}

        print(f"🏷️ Hashtag: {hashtags}")

        # 保存hashtag
        if self.save_content_to_file(uuid, hashtags, "hashtags"):
            return {"status": "success", "hashtags": hashtags}
        else:
            return {"status": "failed", "reason": "save_failed"}

    def process_all_content_types(self, uuid, force=False):
        """为单个UUID生成所有类型的内容（pipeline模式）"""
        print(f"\n🔄 Pipeline模式处理 UUID: {uuid[:8]}...{uuid[-8:]}")

        results = {}
        content_types = ["titles", "descriptions", "hashtags"]

        for content_type in content_types:
            print(f"\n--- 处理 {content_type} ---")

            # 检查依赖
            if not self.check_dependencies(uuid, content_type):
                print(f"❌ {content_type} 缺少依赖文件")
                results[content_type] = {
                    "status": "failed",
                    "reason": "missing_dependencies",
                }
                continue

            result = self.process_single_item(uuid, content_type, force)
            results[content_type] = result

            # 如果生成失败，后续依赖该文件的步骤也会失败
            if result["status"] != "success" and result["status"] != "skipped":
                print(f"⚠️ {content_type} 处理失败，可能影响后续步骤")

            # API调用间隔
            time.sleep(2)

        return results

    def check_dependencies(self, uuid, content_type):
        """检查指定内容类型的依赖文件是否存在"""
        if content_type == "titles":
            # 标题需要书籍信息文件
            return self.load_book_info(uuid) is not None
        elif content_type == "descriptions":
            # 描述需要总结文件
            return self.load_book_summary(uuid) is not None
        elif content_type == "hashtags":
            # hashtag需要描述文件
            return self.load_description(uuid) is not None
        return False

    def process_content(
        self, content_type="all", max_count=None, force=False, target_uuid=None
    ):
        """批量处理内容生成"""
        print(f"🎬 YouTube内容生成器 - {content_type.upper()}")
        print("=" * 60)

        # 获取可用的UUID
        available_uuids = self.get_available_uuids()
        if not available_uuids:
            print("❌ 没有找到可处理的MP4文件")
            return {"total_targets": 0, "successful": 0, "failed": 0, "skipped": 0}

        # 如果指定了特定UUID
        if target_uuid:
            if target_uuid in available_uuids:
                available_uuids = [target_uuid]
                print(f"🎯 处理指定UUID: {target_uuid}")
            else:
                print(f"❌ 未找到指定的UUID: {target_uuid}")
                return {"total_targets": 0, "successful": 0, "failed": 0, "skipped": 0}

        # 限制处理数量
        if max_count and len(available_uuids) > max_count:
            available_uuids = available_uuids[:max_count]

        print(f"\n📊 处理统计:")
        print(f"可处理书籍: {len(available_uuids)}")

        # 开始处理
        stats = {"total_targets": 0, "successful": 0, "failed": 0, "skipped": 0}

        with tqdm(total=len(available_uuids), desc=f"🎬 生成{content_type}") as pbar:
            for uuid in available_uuids:
                try:
                    if content_type == "all":
                        # Pipeline模式 - 生成所有类型
                        results = self.process_all_content_types(uuid, force)
                        stats["total_targets"] += len(results)

                        for result in results.values():
                            if result["status"] == "success":
                                stats["successful"] += 1
                            elif result["status"] == "failed":
                                stats["failed"] += 1
                            else:
                                stats["skipped"] += 1
                    else:
                        # 单一类型模式
                        result = self.process_single_item(uuid, content_type, force)
                        stats["total_targets"] += 1

                        if result["status"] == "success":
                            stats["successful"] += 1
                        elif result["status"] == "failed":
                            stats["failed"] += 1
                        else:
                            stats["skipped"] += 1

                except KeyboardInterrupt:
                    print("⏹️ 用户中断，程序停止")
                    break
                except Exception as e:
                    print(f"❌ 处理 {uuid[:8]}... 时出错: {e}")
                    stats["failed"] += 1

                pbar.update(1)

                # API调用间隔
                if uuid != available_uuids[-1]:
                    time.sleep(1)

        # 最终统计
        print(f"\n🎯 内容生成完成!")
        print(f"✅ 成功: {stats['successful']}")
        print(f"❌ 失败: {stats['failed']}")
        print(f"⏭️ 跳过: {stats['skipped']}")

        if stats["total_targets"] > 0:
            success_rate = stats["successful"] / stats["total_targets"] * 100
            print(f"📊 成功率: {success_rate:.1f}%")

        return stats

    def check_status(self, content_type="all"):
        """检查当前状态"""
        print("📊 当前状态检查")
        print(f"📁 基础路径: {self.books_base_path}")

        available_uuids = self.get_available_uuids()
        print(f"🎥 可用MP4文件: {len(available_uuids)}")

        if content_type == "all" or content_type == "titles":
            existing_titles = [
                uuid
                for uuid in available_uuids
                if self.check_file_exists(uuid, "titles")
            ]
            print(f"📺 已生成标题: {len(existing_titles)}")

        if content_type == "all" or content_type == "descriptions":
            existing_descriptions = [
                uuid
                for uuid in available_uuids
                if self.check_file_exists(uuid, "descriptions")
            ]
            print(f"📝 已生成描述: {len(existing_descriptions)}")

        if content_type == "all" or content_type == "hashtags":
            existing_hashtags = [
                uuid
                for uuid in available_uuids
                if self.check_file_exists(uuid, "hashtags")
            ]
            print(f"🏷️ 已生成标签: {len(existing_hashtags)}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="🎬 YouTube 内容生成器统一脚本",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  # Pipeline模式 - 生成所有类型内容（推荐）
  python generate_youtube_content.py --lang en --type all
  
  # 单独生成特定类型
  python generate_youtube_content.py --lang en --type titles        # 仅生成标题
  python generate_youtube_content.py --lang zh --type descriptions  # 仅生成描述
  python generate_youtube_content.py --lang en --type hashtags      # 仅生成标签
  
  # 其他选项
  python generate_youtube_content.py --lang en --type all --count 10    # 处理10个文件
  python generate_youtube_content.py --lang zh --type all --force       # 强制重新生成
  python generate_youtube_content.py --lang en --type descriptions --uuid abc123  # 处理指定UUID

注意:
- 需要设置环境变量 UNI_API_KEY
- Pipeline模式会按顺序生成: 标题 → 描述 → 标签
- 每种类型都有相应的前置依赖要求
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

    # 内容类型参数
    parser.add_argument(
        "--type",
        "-t",
        choices=["all", "titles", "descriptions", "hashtags"],
        default="all",
        help="内容类型: all(全部), titles(标题), descriptions(描述), hashtags(标签) [默认: all]",
    )

    parser.add_argument(
        "--count", "-c", type=int, help="要处理的书籍数量（默认处理所有）"
    )
    parser.add_argument(
        "--force", "-f", action="store_true", help="强制重新生成已存在的内容"
    )
    parser.add_argument("--uuid", "-u", help="只处理指定UUID的书籍")
    parser.add_argument("--debug", "-d", action="store_true", help="启用调试模式")
    parser.add_argument("--status", "-s", action="store_true", help="检查当前处理状态")

    args = parser.parse_args()

    # 创建生成器实例
    generator = YouTubeContentGenerator(debug=args.debug, language=args.lang)

    print("🎬 YouTube内容生成器统一脚本")
    print("=" * 50)

    # 状态检查模式
    if args.status:
        generator.check_status(args.type)
        return

    # 处理内容生成
    try:
        stats = generator.process_content(
            content_type=args.type,
            max_count=args.count,
            force=args.force,
            target_uuid=args.uuid,
        )

        print(f"\n📊 最终统计:")
        print(f"  🎯 目标数量: {stats.get('total_targets', 0)}")
        print(f"  ✅ 成功生成: {stats.get('successful', 0)}")
        print(f"  ❌ 生成失败: {stats.get('failed', 0)}")
        print(f"  ⏭️ 跳过处理: {stats.get('skipped', 0)}")

    except KeyboardInterrupt:
        print("\n⏹️ 用户中断处理")
    except Exception as e:
        print(f"\n❌ 处理过程中出错: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
