#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI Studio 多主题故事生成自动化脚本 (已升级为 Gemini App)

功能说明：
这是一个用于 Google Gemini App 的自动化故事生成脚本，支持多种主题类型：

📚 支持的主题类型：
- scifi: 科幻故事
- fantasy: 奇幻故事
- thriller: 惊悚故事
- romance: 爱情故事
- horror: 恐怖故事

1. 📖 多主题严格轮流生成
   - 支持同时为多个主题生成故事（默认所有主题）
   - 严格轮流生成模式：逐个主题轮流生成，避免单一主题连续生成
   - 生成顺序示例：科幻故事1 → 奇幻故事1 → 惊悚故事1 → 科幻故事2 → 奇幻故事2...
   - 从multi_theme_story_generator.py的输出读取故事参数
   - 智能索引管理：优先填补缺失的故事索引，然后生成新索引
   - 自动清理 markdown 标记：在发送前彻底清除所有 markdown 格式符号

2. 🌐 浏览器自动化
   - 通过 AdsPower 浏览器实现多开隔离
   - 使用 Playwright 进行精确的网页操作控制
   - 单窗口顺序处理模式：确保严格按照轮流顺序生成
   - **新版本使用 Gemini App 接口替代老旧的 AI Studio**

3. 🎯 智能热身机制
   - 首次运行时自动进行AI热身，发送随机问题激活模型
   - 后续生成跳过热身，直接进入正式内容生成

4. 💾 自动保存管理
   - 自动将生成的故事保存为编号的文本文件
   - 支持断点续传：检测已存在的故事，只生成缺失的部分
   - 智能路径选择：
     * Intel Mac (x86_64): /Volumes/dhl/audio/{theme}/full_story/{index}.txt
     * Apple Silicon Mac (M1/M2/M3): /Users/donghaoliu/Documents/audio/{theme}/full_story/{index}.txt
   - 文件命名格式：{索引号}.txt (例如: 1.txt, 2.txt, 3.txt...)
   - 自动排除Mac系统产生的点文件(.DS_Store等)

5. 🔄 错误处理与重试
   - 智能检测AI生成状态（通过监控停止按钮状态）
   - 生成失败时自动清理资源并提示重新运行
   - 完善的异常处理机制

6. ⚙️ 命令行界面
   - 支持指定生成数量：--count 或 -c 参数（每个主题的数量）
   - 支持指定浏览器ID：--ads-id 参数
   - 支持指定主题：--theme 或 -t 参数（可选，默认所有主题）
   - 默认每个主题生成2个故事，使用 k10i5y1s 浏览器配置

🗂️ 路径结构说明：
Intel Mac (x86_64) 系统:
  /Volumes/dhl/audio/
  ├── scifi/
  │   ├── full_story/      ← 生成的故事保存位置 (1.txt, 2.txt, ...)
  │   └── story_param/     ← 故事参数文件 (由multi_theme_story_generator.py生成)
  ├── fantasy/
  │   ├── full_story/
  │   └── story_param/
  └── ...

Apple Silicon Mac (M1/M2/M3) 系统:
  /Users/donghaoliu/Documents/audio/
  ├── scifi/
  │   ├── full_story/      ← 生成的故事保存位置 (1.txt, 2.txt, ...)
  │   └── story_param/     ← 故事参数文件 (由multi_theme_story_generator.py生成)
  ├── fantasy/
  │   ├── full_story/
  │   └── story_param/
  └── ...

使用方法：
python ai_studio_bot.py --count 3                                    # 所有主题各生成3个故事(轮流生成)
python ai_studio_bot.py --theme scifi fantasy --count 2              # 科幻奇幻轮流各生成2个故事
python ai_studio_bot.py --theme scifi --count 2 --ads-id your_id     # 指定浏览器ID

轮流生成顺序示例（--count 2 --theme scifi fantasy thriller）：
1. 科幻故事1 → 2. 奇幻故事1 → 3. 惊悚故事1 → 4. 科幻故事2 → 5. 奇幻故事2 → 6. 惊悚故事2

检查状态：
python ai_studio_bot.py --check-resume                               # 检查所有主题的断点续传状态
python ai_studio_bot.py --check-resume --theme scifi thriller        # 检查指定主题的断点续传状态

依赖组件：
- AdsPower：提供浏览器环境隔离
- Playwright：网页自动化控制
- multi_theme_story_generator.py：提供故事参数文件

作者：AI Studio 自动化团队
版本：v5.0 (Gemini App)
更新：升级到 Gemini App 接口，提升稳定性和生成质量
"""

import time
import json
import sys
import os
import glob
import re
import argparse
import random
import platform

# 不再需要主题相关的导入，直接从参数文件读取

# 支持的主题配置 - 所有主题均默认可用，从参数文件读取
SUPPORTED_THEMES = {
    "scifi": {
        "name": "科幻",
        "available": True,  # 现在从文件读取，不依赖模块
        "description": "科幻故事生成，包含未来科技、太空探索、时间旅行等元素",
    },
    "fantasy": {
        "name": "奇幻",
        "available": True,  # 现在从文件读取，不依赖模块
        "description": "奇幻故事生成，包含魔法、龙、精灵等奇幻元素",
    },
    "thriller": {
        "name": "惊悚",
        "available": True,
        "description": "惊悚故事生成，包含悬疑、恐怖等元素",
    },
    "romance": {
        "name": "爱情",
        "available": True,
        "description": "爱情故事生成，包含浪漫、情感等元素",
    },
    "horror": {
        "name": "恐怖",
        "available": True,
        "description": "恐怖故事生成，包含恐怖、惊悚等元素",
    },
}

# 添加随机问题列表用于热身
WARMUP_QUESTIONS = [
    "今天天气如何？",
    "你好吗？",
    "现在几点了？",
    "请介绍一下你自己。",
    "你能帮我做什么？",
    "今天是星期几？",
    "你最喜欢什么颜色？",
    "请说一个简单的笑话。",
    "什么是人工智能？",
    "你会说中文吗？",
]


def get_base_audio_dir():
    """返回音频基础目录，根据Mac芯片类型区分路径

    详细路径说明：
    - Intel Mac (x86_64): /Volumes/dhl/audio
      └── 故事保存路径示例: /Volumes/dhl/audio/scifi/full_story/1.txt
    - Apple Silicon Mac (M1/M2/M3等): /Users/donghaoliu/Documents/audio
      └── 故事保存路径示例: /Users/donghaoliu/Documents/audio/scifi/full_story/1.txt

    返回:
        str: 基础音频目录路径
    """
    # 检查操作系统
    if platform.system() == "Darwin":
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
            base_dir = "/Users/donghaoliu/Documents/audio"
            print(f"🔍 检测到 Apple Silicon Mac，使用基础目录: {base_dir}")
            return base_dir
        else:
            # Intel Mac
            base_dir = "/Volumes/dhl/audio"
            print(f"🔍 检测到 Intel Mac，使用基础目录: {base_dir}")
            return base_dir
    # 其他系统暂时不支持
    base_dir = "/Users/donghaoliu/Documents/audio"
    print(f"🔍 未识别系统类型，使用默认目录: {base_dir}")
    return base_dir


def get_theme_story_path_prefix(theme):
    """获取主题对应的故事文件目录路径

    参数:
        theme (str): 主题名称 (scifi, fantasy, thriller, romance, horror)

    返回路径格式:
        - Intel Mac: /Volumes/dhl/audio/{theme}/full_story/
        - Apple Silicon Mac: /Users/donghaoliu/Documents/audio/{theme}/full_story/

    故事文件命名格式: {index}.txt
    例如: 1.txt, 2.txt, 3.txt...
    """
    base_dir = get_base_audio_dir()
    story_dir = f"{base_dir}/{theme}/full_story"

    # 添加详细的路径说明输出
    print(
        f"📁 {SUPPORTED_THEMES.get(theme, {}).get('name', theme)}({theme}) 主题故事保存目录:"
    )
    print(f"   完整路径: {story_dir}")
    print(f"   文件格式: {story_dir}/{{索引号}}.txt")
    print(f"   示例文件: {story_dir}/1.txt, {story_dir}/2.txt, ...")

    return story_dir


def get_theme_param_path_prefix(theme):
    """获取主题对应的参数文件目录路径（从multi_theme_story_generator.py输出读取）

    参数:
        theme (str): 主题名称 (scifi, fantasy, thriller, romance, horror)

    返回路径格式:
        - Intel Mac: /Volumes/dhl/audio/{theme}/story_param/
        - Apple Silicon Mac: /Users/donghaoliu/Documents/audio/{theme}/story_param/

    参数文件由 multi_theme_story_generator.py 脚本生成
    """
    base_dir = get_base_audio_dir()
    param_dir = f"{base_dir}/{theme}/story_param"

    print(
        f"📋 {SUPPORTED_THEMES.get(theme, {}).get('name', theme)}({theme}) 主题参数文件目录: {param_dir}"
    )

    return param_dir


def get_available_story_param_files(theme):
    """获取主题目录下可用的故事参数文件，排除Mac产生的点文件"""
    param_dir = get_theme_param_path_prefix(theme)

    if not os.path.exists(param_dir):
        print(f"参数目录不存在: {param_dir}")
        return []

    try:
        # 获取所有文件
        all_files = os.listdir(param_dir)
        # 排除点文件（Mac系统文件）和非文件
        valid_files = [
            f
            for f in all_files
            if not f.startswith(".") and os.path.isfile(os.path.join(param_dir, f))
        ]

        # 返回完整路径
        param_files = [os.path.join(param_dir, f) for f in valid_files]
        param_files.sort()  # 排序确保顺序一致

        print(f"主题 {theme} 找到 {len(param_files)} 个参数文件")
        return param_files

    except Exception as e:
        print(f"读取主题 {theme} 参数目录失败: {e}")
        return []


def clean_markdown_from_text(text):
    """清理文本中的所有 markdown 标记符号"""
    if not text:
        return text

    import re

    # 保存原始文本用于调试
    original_length = len(text)

    # 1. 清理代码块 ```code```
    text = re.sub(r"```[\s\S]*?```", "", text)

    # 2. 清理行内代码 `code`
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # 3. 清理标题标记 # ## ### 等
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)

    # 4. 清理粗体标记 **text** 和 __text__
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)

    # 5. 清理斜体标记 *text* 和 _text_
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)

    # 6. 清理删除线 ~~text~~
    text = re.sub(r"~~([^~]+)~~", r"\1", text)

    # 7. 清理链接 [text](url)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

    # 8. 清理图片 ![alt](url)
    text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"\1", text)

    # 9. 清理引用标记 > text
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)

    # 10. 清理无序列表标记 - * +
    text = re.sub(r"^[\s]*[-*+]\s*", "", text, flags=re.MULTILINE)

    # 11. 清理有序列表标记 1. 2. 等
    text = re.sub(r"^\s*\d+\.\s*", "", text, flags=re.MULTILINE)

    # 12. 清理水平线 --- *** ___
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    # 13. 清理表格分隔符 | --- |
    text = re.sub(r"^\s*\|.*\|\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\|[\s\-\|]*\|\s*$", "", text, flags=re.MULTILINE)

    # 14. 清理其他常见的 markdown 符号
    # 清理剩余的单独的星号、下划线等
    text = re.sub(r"(?<!\w)[\*_]+(?!\w)", "", text)

    # 15. 清理多余的空行（保留单个换行）
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    # 16. 清理行首行尾的多余空格
    lines = text.split("\n")
    cleaned_lines = [line.strip() for line in lines]
    text = "\n".join(cleaned_lines)

    # 17. 最终清理：去掉开头和结尾的空白
    text = text.strip()

    # 调试信息
    cleaned_length = len(text)
    removed_chars = original_length - cleaned_length
    if removed_chars > 0:
        print(
            f"✂️ 已清理 markdown 标记，移除了 {removed_chars} 个字符 ({original_length} -> {cleaned_length})"
        )

    return text


def read_story_param_from_file(file_path):
    """从文件中读取故事参数"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        return content
    except Exception as e:
        print(f"读取参数文件 {file_path} 失败: {e}")
        return None


def validate_theme(theme):
    """验证主题是否支持"""
    if theme not in SUPPORTED_THEMES:
        available_themes = [k for k, v in SUPPORTED_THEMES.items() if v["available"]]
        raise ValueError(f"不支持的主题: {theme}。\n可用主题: {available_themes}")

    if not SUPPORTED_THEMES[theme]["available"]:
        raise ValueError(
            f"主题 '{theme}' 暂不可用: {SUPPORTED_THEMES[theme]['description']}"
        )

    return True


def list_available_themes():
    """列出所有可用的主题"""
    print("\n=== 📚 可用主题列表 ===")
    for theme_id, theme_info in SUPPORTED_THEMES.items():
        status = "✅ 可用" if theme_info["available"] else "❌ 不可用"
        print(f"  {theme_id}: {theme_info['name']} - {status}")
        print(f"    描述: {theme_info['description']}")
    print()


def countdown_wait(seconds=20, window_index=None):
    """显示倒计时等待"""
    prefix = f"窗口 {window_index}: " if window_index else ""
    print(f"⏳ {prefix}等待 {seconds} 秒后继续...")

    for i in range(seconds, 0, -1):
        print(f"\r⏰ {prefix}倒计时: {i:2d} 秒", end="", flush=True)
        time.sleep(1)

    print(f"\r✅ {prefix}等待完成！{'':10}")  # 清除倒计时显示


def get_adspower_info(ads_id):
    """连接AdsPower浏览器，带重试和详细错误提示"""
    try:
        import urllib3
    except ImportError:
        print("❌ 错误: 缺少 urllib3 模块，请安装: pip install urllib3")
        return None, None, None

    # 先检查 AdsPower 服务是否运行
    test_url = "http://127.0.0.1:50325/api/v1/status"
    open_url = f"http://127.0.0.1:50325/api/v1/browser/start?user_id={ads_id}"

    http = urllib3.PoolManager()

    print("🔍 检查 AdsPower 服务状态...")

    # 检查服务是否运行
    try:
        test_resp = http.request("GET", test_url, timeout=10)
        print("✅ AdsPower 服务已运行")
    except Exception as e:
        print("❌ AdsPower 服务未运行或无法连接")
        print("请确保:")
        print("  1. AdsPower 客户端已启动")
        print("  2. 本地API已启用 (设置 -> 本地API -> 启用)")
        print("  3. 端口 50325 未被占用")
        print("  4. 防火墙允许本地连接")
        print(f"详细错误: {e}")
        return None, None, None

    print(f"🚀 正在启动浏览器 (ID: {ads_id})...")

    # 尝试启动浏览器，最多重试3次
    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = http.request("GET", open_url, timeout=30)

            if r.status != 200:
                print(f"❌ 错误: API返回状态码 {r.status}")
                if attempt < max_retries - 1:
                    print(f"🔄 第 {attempt + 1} 次尝试失败，{5} 秒后重试...")
                    time.sleep(5)
                    continue
                else:
                    print("请确保AdsPower已启动并且本地API已启用")
                    return None, None, http

            # 解析响应
            try:
                resp = json.loads(r.data.decode("utf-8"))
            except json.JSONDecodeError as e:
                print(f"❌ 解析响应JSON失败: {e}")
                if attempt < max_retries - 1:
                    print(f"🔄 第 {attempt + 1} 次尝试失败，{5} 秒后重试...")
                    time.sleep(5)
                    continue
                else:
                    return None, None, http

            if resp["code"] != 0:
                error_msg = resp.get("msg", "未知错误")
                print(f"❌ AdsPower 错误: {error_msg}")

                # 针对常见错误提供解决建议
                if "not found" in error_msg.lower():
                    print(f"💡 浏览器ID '{ads_id}' 不存在，请检查:")
                    print("  1. 浏览器ID是否正确")
                    print("  2. 浏览器配置文件是否存在")
                    print("  3. 尝试在AdsPower客户端中手动启动该浏览器")
                elif "running" in error_msg.lower():
                    print("💡 浏览器可能已在运行，请:")
                    print("  1. 在AdsPower中关闭该浏览器")
                    print("  2. 等待几秒后重试")
                elif "license" in error_msg.lower():
                    print("💡 许可证问题，请检查AdsPower账户状态")

                if attempt < max_retries - 1:
                    print(f"🔄 第 {attempt + 1} 次尝试失败，{10} 秒后重试...")
                    time.sleep(10)
                    continue
                else:
                    return None, None, http

            # 成功获取浏览器信息
            ws_endpoint = resp["data"]["ws"]["puppeteer"]
            debug_port = resp["data"]["debug_port"]
            remote_debugging_url = f"http://localhost:{debug_port}"

            print(f"✅ 成功连接AdsPower浏览器!")
            print(f"   浏览器ID: {ads_id}")
            print(f"   调试端口: {debug_port}")
            print(f"   WebSocket: {ws_endpoint}")

            return ws_endpoint, remote_debugging_url, http

        except urllib3.exceptions.MaxRetryError as e:
            print(f"❌ 网络连接错误: {e}")
            if attempt < max_retries - 1:
                print(f"🔄 第 {attempt + 1} 次尝试失败，{5} 秒后重试...")
                time.sleep(5)
                continue
            else:
                print("请检查:")
                print("  1. AdsPower是否正在运行")
                print("  2. 网络连接是否正常")
                print("  3. 是否有防火墙阻止连接")
                return None, None, None

        except Exception as e:
            print(f"❌ 连接 AdsPower 时发生意外错误: {e}")
            if attempt < max_retries - 1:
                print(f"🔄 第 {attempt + 1} 次尝试失败，{5} 秒后重试...")
                time.sleep(5)
                continue
            else:
                print("请尝试:")
                print("  1. 重启 AdsPower 客户端")
                print("  2. 检查系统资源使用情况")
                print("  3. 更换浏览器ID重试")
                return None, None, None

    print(f"❌ 所有重试都失败了，无法连接到AdsPower浏览器 (ID: {ads_id})")
    return None, None, None


def get_existing_stories(story_dir_path):
    """获取已存在的故事索引，支持Intel Mac断点续传"""
    # 确保目录存在
    if not os.path.exists(story_dir_path):
        print(f"故事目录不存在: {story_dir_path}")
        return set()

    # 搜索目录下的数字命名txt文件
    story_files = glob.glob(f"{story_dir_path}/*.txt")
    print(f"🔍 在目录 {story_dir_path} 中搜索故事文件...")
    print(f"📁 使用搜索模式: {story_dir_path}/*.txt")
    print(f"📊 找到 {len(story_files)} 个 .txt 文件")

    existing_indices = []
    valid_stories = []

    for f in story_files:
        filename = os.path.basename(f)

        # 排除Mac系统产生的点文件
        if filename.startswith("."):
            print(f"⏭️  跳过Mac系统文件: {filename}")
            continue

        # 从文件名中提取数字索引
        match = re.search(r"^(\d+)\.txt$", filename)
        if match:
            story_index = int(match.group(1))

            # 验证文件是否有效（检查文件大小和内容）
            try:
                file_size = os.path.getsize(f)
                if file_size > 100:  # 文件大小应该大于100字节
                    with open(f, "r", encoding="utf-8") as file:
                        content = file.read(200)  # 读取前200字符检查
                        if content.strip():  # 确保文件有内容
                            existing_indices.append(story_index)
                            valid_stories.append((story_index, filename, file_size))
                        else:
                            print(f"⚠️  空文件: {filename}")
                else:
                    print(f"⚠️  文件过小: {filename} ({file_size} 字节)")
            except Exception as e:
                print(f"⚠️  无法验证文件: {filename} - {e}")
        else:
            print(f"⏭️  跳过非数字命名文件: {filename}")

    if existing_indices:
        sorted_indices = sorted(existing_indices)
        print(f"✅ 找到 {len(existing_indices)} 个有效的已存在故事:")
        for story_index, filename, file_size in sorted(valid_stories):
            print(f"   📄 故事 {story_index}: {filename} ({file_size} 字节)")
        print(f"📋 故事索引范围: {min(sorted_indices)} - {max(sorted_indices)}")
    else:
        print("❌ 未找到任何有效的已存在故事")

    return set(existing_indices)


def get_next_story_index_for_theme(theme):
    """获取主题的下一个可用故事索引（支持断点续传）"""
    theme_name = SUPPORTED_THEMES.get(theme, {}).get("name", theme)
    story_dir_path = get_theme_story_path_prefix(theme)

    print(f"\n🔍 检查 {theme_name}({theme}) 主题的已存在故事...")
    print(f"📁 故事目录: {story_dir_path}")

    # 确保目录存在
    os.makedirs(story_dir_path, exist_ok=True)

    existing_indices = get_existing_stories(story_dir_path)

    if not existing_indices:
        print(f"🆕 {theme_name} 主题还没有任何故事，将从索引 1 开始")
        return 1

    # 找出缺失的最小索引（优先填补空缺）
    max_existing = max(existing_indices)
    min_existing = min(existing_indices)

    print(f"📊 {theme_name} 主题现有故事索引分析:")
    print(f"   最小索引: {min_existing}")
    print(f"   最大索引: {max_existing}")
    print(f"   故事总数: {len(existing_indices)}")

    # 查找空缺
    missing_indices = []
    for i in range(1, max_existing + 1):
        if i not in existing_indices:
            missing_indices.append(i)

    if missing_indices:
        next_index = min(missing_indices)
        print(f"🔄 发现空缺索引，{theme_name} 下一个生成索引: {next_index} (填补空缺)")
        print(f"   所有空缺索引: {missing_indices}")
        return next_index
    else:
        next_index = max_existing + 1
        print(f"➕ 无空缺索引，{theme_name} 下一个生成索引: {next_index} (续接最大值)")
        return next_index


def get_next_story_index_for_theme_with_allocated(theme, allocated_indices):
    """获取主题的下一个可用故事索引（考虑已分配的索引）

    Args:
        theme: 主题名称
        allocated_indices: 当前规划中已分配的索引集合

    Returns:
        int: 下一个可用的故事索引
    """
    theme_name = SUPPORTED_THEMES.get(theme, {}).get("name", theme)
    story_dir_path = get_theme_story_path_prefix(theme)

    # 确保目录存在
    os.makedirs(story_dir_path, exist_ok=True)

    # 获取已存在的故事索引
    existing_indices = get_existing_stories(story_dir_path)

    # 合并已存在和已分配的索引
    occupied_indices = existing_indices | allocated_indices

    if not occupied_indices:
        return 1

    # 找出缺失的最小索引（优先填补空缺）
    max_occupied = max(occupied_indices)

    # 查找空缺（从1开始）
    for i in range(1, max_occupied + 1):
        if i not in occupied_indices:
            return i

    # 如果没有空缺，返回最大值+1
    return max_occupied + 1


def get_next_available_param_file_for_theme(theme, used_param_files):
    """获取主题的下一个可用参数文件"""
    available_files = get_available_story_param_files(theme)

    if not available_files:
        return None

    # 找到第一个未使用的参数文件
    for file_path in available_files:
        if file_path not in used_param_files:
            return file_path

    return None


def check_theme_resume_status(theme):
    """检查主题的断点续传状态"""
    theme_name = SUPPORTED_THEMES.get(theme, {}).get("name", theme)
    story_dir_path = get_theme_story_path_prefix(theme)
    param_dir_path = get_theme_param_path_prefix(theme)

    print(f"\n=== 📋 {theme_name}({theme}) 断点续传状态检查 ===")

    # 检查目录是否存在
    story_dir_exists = os.path.exists(story_dir_path)
    param_dir_exists = os.path.exists(param_dir_path)

    print(
        f"📁 故事目录: {story_dir_path} {'✅存在' if story_dir_exists else '❌不存在'}"
    )
    print(
        f"📁 参数目录: {param_dir_path} {'✅存在' if param_dir_exists else '❌不存在'}"
    )

    if not story_dir_exists and not param_dir_exists:
        print(f"⚠️  {theme_name} 主题相关目录都不存在，可能是首次运行")
        return

    # 获取已有故事
    existing_stories = set()
    if story_dir_exists:
        existing_stories = get_existing_stories(story_dir_path)

    # 获取可用参数文件
    available_params = []
    if param_dir_exists:
        available_params = get_available_story_param_files(theme)

    print(f"📊 {theme_name} 主题状态汇总:")
    print(f"   已有故事: {len(existing_stories)} 个")
    print(f"   可用参数: {len(available_params)} 个")

    if existing_stories:
        sorted_stories = sorted(existing_stories)
        print(f"   故事索引: {sorted_stories}")

        # 检查是否有空缺
        max_story = max(existing_stories)
        expected_range = set(range(1, max_story + 1))
        missing = expected_range - existing_stories

        if missing:
            print(f"   ⚠️  发现空缺索引: {sorted(missing)}")
        else:
            print(f"   ✅ 故事索引连续完整")

    if available_params:
        print(f"   参数文件: {[os.path.basename(p) for p in available_params]}")

    # 计算可以生成的故事数量
    if available_params:
        if existing_stories:
            next_index = get_next_story_index_for_theme(theme)
            print(f"   🎯 下一个生成索引: {next_index}")
        print(f"   🚀 理论可生成: {len(available_params)} 个新故事")
    else:
        print(f"   ❌ 无可用参数文件，无法生成新故事")

    print(f"{'='*50}")

    return {
        "theme": theme,
        "existing_stories": len(existing_stories),
        "available_params": len(available_params),
        "can_generate": len(available_params) > 0,
    }


def prepare_multi_theme_generation(themes, num_per_theme):
    """
    准备多主题轮流生成的参数列表

    返回一个按轮次组织的生成计划，每轮为每个主题生成一个故事
    """
    print(f"\n🔍 开始检查所有主题的断点续传状态...")

    # 先检查所有主题的断点续传状态
    theme_status = {}
    for theme in themes:
        status = check_theme_resume_status(theme)
        theme_status[theme] = status

    # 检查每个主题的参数文件可用性
    theme_param_files = {}
    theme_available_counts = {}

    print(f"\n📋 汇总所有主题状态:")
    for theme in themes:
        param_files = get_available_story_param_files(theme)
        theme_param_files[theme] = param_files
        theme_available_counts[theme] = len(param_files)

        theme_name = SUPPORTED_THEMES.get(theme, {}).get("name", theme)
        status = theme_status.get(theme, {})
        existing_count = status.get("existing_stories", 0)

        if not param_files:
            print(
                f"❌ {theme_name}({theme}): 无可用参数文件 (已有故事: {existing_count})"
            )
        else:
            print(
                f"✅ {theme_name}({theme}): {len(param_files)} 个参数文件可用 (已有故事: {existing_count})"
            )

    # 生成轮次计划
    generation_plan = []
    used_param_files = {theme: set() for theme in themes}
    # 添加：跟踪每个主题已分配的索引，确保不重复
    theme_allocated_indices = {theme: set() for theme in themes}

    for round_num in range(num_per_theme):
        print(f"\n=== 📋 规划第 {round_num + 1} 轮生成 ===")
        round_plan = []

        for theme in themes:
            # 获取下一个故事索引 - 考虑已分配的索引
            next_index = get_next_story_index_for_theme_with_allocated(
                theme, theme_allocated_indices[theme]
            )

            # 获取下一个可用参数文件
            next_param_file = get_next_available_param_file_for_theme(
                theme, used_param_files[theme]
            )

            if next_param_file:
                # 读取参数内容
                param_content = read_story_param_from_file(next_param_file)
                if param_content:
                    # 清理 markdown 标记符号
                    cleaned_content = clean_markdown_from_text(param_content)

                    story_data = {
                        "theme": theme,
                        "index": next_index,
                        "prompt": cleaned_content,
                        "param_file": next_param_file,
                        "dir_path": get_theme_story_path_prefix(theme),
                    }
                    round_plan.append(story_data)
                    used_param_files[theme].add(next_param_file)
                    # 记录已分配的索引
                    theme_allocated_indices[theme].add(next_index)

                    theme_name = SUPPORTED_THEMES[theme]["name"]
                    print(
                        f"  ✅ {theme_name}({theme}) - 故事{next_index} - 参数文件: {os.path.basename(next_param_file)}"
                    )
                else:
                    print(f"  ❌ {theme} - 无法读取参数文件: {next_param_file}")
            else:
                print(f"  ⚠️ {theme} - 没有更多可用的参数文件")

        if round_plan:
            generation_plan.extend(round_plan)
        else:
            print(f"第 {round_num + 1} 轮没有可生成的故事，停止规划")
            break

    print(f"\n=== 📊 生成计划汇总 ===")
    print(f"总计划生成 {len(generation_plan)} 个故事")

    # 按主题统计
    theme_counts = {}
    for story in generation_plan:
        theme = story["theme"]
        if theme not in theme_counts:
            theme_counts[theme] = 0
        theme_counts[theme] += 1

    for theme, count in theme_counts.items():
        theme_name = SUPPORTED_THEMES[theme]["name"]
        print(f"  {theme_name}({theme}): {count} 个故事")

    return generation_plan


def wait_for_warmup_completion(page, window_index):
    """等待热身问题的AI回答完成 - 停止按钮状态判断 (Gemini App版本)"""
    print(f"🔄 窗口 {window_index}: 正在等待热身问题AI回答完成...")

    # Gemini App的停止按钮选择器
    stop_selectors = [
        'mat-icon[fonticon="stop"]',
        'mat-icon.icon-filled[fonticon="stop"]',
        '.mat-icon.icon-filled[fonticon="stop"]',
        'mat-icon[data-mat-icon-name="stop"]',
        'button:has(mat-icon[fonticon="stop"])',
    ]

    try:
        # 先等待3秒让AI开始运行
        print(f"⏳ 窗口 {window_index}: 等待热身AI启动...")
        time.sleep(3)

        # 检查停止按钮状态
        print(f"👀 窗口 {window_index}: 监控热身AI运行状态...")

        while True:
            # 检查停止按钮是否存在
            stop_buttons_exist = False
            for selector in stop_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        stop_buttons_exist = True
                        break
                except:
                    continue

            if stop_buttons_exist:
                print(f"🏃‍♂️ 窗口 {window_index}: 热身AI正在运行...")
            else:
                print(f"✅ 窗口 {window_index}: 热身AI运行完成")
                return

            # 每2秒检查一次
            time.sleep(2)

    except Exception as e:
        print(f"⚠️ 窗口 {window_index}: 热身等待过程中出现异常: {e}")
        raise e


def wait_for_ai_completion(page, window_index):
    """等待AI运行完成 - 停止按钮状态判断 (Gemini App版本)"""
    print(f"🔄 窗口 {window_index}: 正在等待AI运行完成...")

    # 等待一下让AI开始运行
    page.wait_for_timeout(3000)

    # Gemini App的停止按钮选择器
    stop_selectors = [
        'mat-icon[fonticon="stop"]',
        'mat-icon.icon-filled[fonticon="stop"]',
        '.mat-icon.icon-filled[fonticon="stop"]',
        'mat-icon[data-mat-icon-name="stop"]',
        'button:has(mat-icon[fonticon="stop"])',
    ]

    try:
        # 第一步：等待AI开始运行（等待停止按钮出现）
        print(f"⏳ 窗口 {window_index}: 等待AI启动...")
        found_stop_button = False

        for attempt in range(15):  # 等待最多30秒
            for selector in stop_selectors:
                try:
                    count = page.locator(selector).count()
                    if count > 0:
                        print(f"🚦 窗口 {window_index}: 检测到AI已启动")
                        found_stop_button = True
                        break
                except:
                    continue

            if found_stop_button:
                print(f"🏃‍♂️ 窗口 {window_index}: AI开始运行")
                break

            print(f"⏳ 窗口 {window_index}: 等待AI启动... ({attempt + 1}/15)")
            page.wait_for_timeout(2000)

        if not found_stop_button:
            print(f"⚠️ 窗口 {window_index}: 未检测到AI启动，可能存在问题")
            raise Exception(f"窗口 {window_index}: 无法检测到AI运行状态")

        # 第二步：等待停止按钮消失
        print(f"👀 窗口 {window_index}: 监控AI运行状态...")
        consecutive_no_stop_button = 0
        check_count = 0

        while True:
            check_count += 1

            # 检查所有停止按钮是否都消失了
            stop_buttons_exist = False
            for selector in stop_selectors:
                try:
                    count = page.locator(selector).count()
                    if count > 0:
                        stop_buttons_exist = True
                        break
                except:
                    continue

            if stop_buttons_exist:
                print(f"🏃‍♂️ 窗口 {window_index}: AI正在运行... (检查 {check_count})")
            else:
                consecutive_no_stop_button += 1
                print(
                    f"⏸️ 窗口 {window_index}: AI运行状态检查 (连续无活动 {consecutive_no_stop_button} 次)"
                )

                # 连续3次检查都没有停止按钮，认为完成
                if consecutive_no_stop_button >= 3:
                    print(f"✅ 窗口 {window_index}: AI运行完成")
                    break

            if not stop_buttons_exist:
                pass  # 已在上面处理
            else:
                consecutive_no_stop_button = 0  # 重置计数器

            # 安全超时：如果检查超过120次（约10分钟）
            if check_count >= 120:
                print(f"⏰ 窗口 {window_index}: 已达到最大等待时间（10分钟）")
                raise Exception(f"窗口 {window_index}: AI生成超时")

            # 每次等待5秒
            time.sleep(5)

        # 额外等待确保完全完成
        print(f"⏳ 窗口 {window_index}: 等待3秒确保完成...")
        time.sleep(3)
        print(f"✅ 窗口 {window_index}: 运行完成")

    except Exception as e:
        print(f"⚠️ 窗口 {window_index}: 等待过程中出现异常: {e}")
        raise e


def save_generated_story(page, story_index, story_dir_path, theme=""):
    """保存生成的故事内容到指定路径 (Gemini App版本)

    参数:
        page: Playwright页面对象
        story_index (int): 故事索引号
        story_dir_path (str): 故事保存目录路径
        theme (str): 主题名称

    保存路径说明:
        完整文件路径格式: {story_dir_path}/{story_index}.txt
        例如: /Volumes/dhl/audio/scifi/full_story/1.txt
    """
    try:
        theme_name = SUPPORTED_THEMES.get(theme, {}).get("name", theme)
        final_file_path = f"{story_dir_path}/{story_index}.txt"

        print(f"💾 准备保存{theme_name}故事 {story_index}:")
        print(f"   目标文件路径: {final_file_path}")

        # 等待内容生成完成
        page.wait_for_timeout(2000)

        # 查找生成的内容区域 - Gemini App的消息内容选择器
        content_selectors = [
            "message-content",
            ".message-content",
            '[class*="message-content"]',
            "div.message-content",
            "response-container .message-content",
            ".response .message-content",
            'div[class*="response"]',
            'div[class*="content"]',
            'div[class*="message"]',
            "gemini-message .content",
            "chat-message .message-content",
        ]

        content = ""
        for selector in content_selectors:
            try:
                elements = page.locator(selector)
                if elements.count() > 0:
                    theme_name = SUPPORTED_THEMES.get(theme, {}).get("name", theme)
                    print(
                        f"{theme_name}故事 {story_index}: 找到 {elements.count()} 个元素使用选择器: {selector}"
                    )

                    # 从最后一个元素开始检查，这通常是最新生成的内容
                    for i in range(elements.count() - 1, -1, -1):
                        element_text = elements.nth(i).inner_text().strip()
                        if element_text and len(element_text) > 100:  # 过滤掉太短的内容
                            content = element_text
                            print(
                                f"{theme_name}故事 {story_index}: 从元素 #{i+1}（最后一个）提取到内容，长度: {len(content)}"
                            )
                            break

                    if content:
                        break

            except Exception as e:
                theme_name = SUPPORTED_THEMES.get(theme, {}).get("name", theme)
                print(
                    f"{theme_name}故事 {story_index}: 选择器 {selector} 提取失败: {e}"
                )
                continue

        # 如果没有找到内容，尝试通用选择器
        if not content:
            print(f"⚠️ 未能提取到内容，尝试通用选择器...")
            generic_selectors = [
                'div:has-text("story")',
                'div:has-text("chapter")',
                'div:has-text("Once")',
                'div:has-text("The")',
                'div[role="main"]',
                "main",
                "article",
            ]

            for selector in generic_selectors:
                try:
                    elements = page.locator(selector)
                    if elements.count() > 0:
                        for i in range(elements.count() - 1, -1, -1):
                            element_text = elements.nth(i).inner_text().strip()
                            if element_text and len(element_text) > 500:  # 降低阈值
                                content = element_text
                                print(
                                    f"通用选择器提取到内容，长度: {len(content)} 字符"
                                )
                                break
                        if content:
                            break
                except Exception as e:
                    continue

        if content.strip():
            # 清理内容 - 移除多余的换行和空白
            content = content.strip()

            # 保存到文件，使用简单的数字命名
            with open(final_file_path, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"✅ {theme_name}故事 {story_index} 保存成功!")
            print(f"   保存位置: {final_file_path}")
            print(f"   内容长度: {len(content)} 字符")
            # 打印内容的前200个字符作为预览
            preview = content[:200] + "..." if len(content) > 200 else content
            print(f"   内容预览: {preview}")
            return True
        else:
            theme_name = SUPPORTED_THEMES.get(theme, {}).get("name", theme)
            print(f"❌ {theme_name}故事 {story_index}: 未找到生成的内容")
            # 尝试打印页面的部分内容用于调试
            try:
                page_content = page.content()
                if "message-content" in page_content:
                    print(
                        f"{theme_name}故事 {story_index}: 页面中发现message-content元素，但无法提取内容"
                    )
                else:
                    print(
                        f"{theme_name}故事 {story_index}: 页面中未发现message-content元素"
                    )
            except:
                pass
            return False

    except Exception as e:
        theme_name = SUPPORTED_THEMES.get(theme, {}).get("name", theme)
        print(f"保存{theme_name}故事 {story_index} 时出错: {e}")
        return False


def process_window(
    page, window_index, story_data, theme, is_first_story=True, need_warmup=False
):
    """处理单个窗口的故事生成 (Gemini App版本)"""
    max_retries = 3  # 最大重试次数
    theme_name = SUPPORTED_THEMES.get(theme, {}).get("name", theme)

    # 首次运行时处理页面初始化（热身、导航等）
    if is_first_story and need_warmup:
        # 全局第一次：先进行热身，然后开新tab进行正式生成
        print(f"🌐 窗口 {window_index}: 首次启动，正在打开Gemini App...")

        # 简化页面加载等待逻辑
        max_navigation_retries = 3
        for nav_attempt in range(max_navigation_retries):
            try:
                print(
                    f"🔗 窗口 {window_index}: 导航尝试 {nav_attempt + 1}/{max_navigation_retries}"
                )
                page.goto("https://gemini.google.com/app", timeout=60000)
                print(f"✅ 窗口 {window_index}: 页面导航成功")

                # 使用更简单的等待策略
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                    print(f"✅ 窗口 {window_index}: DOM加载完成")
                except:
                    print(f"⚠️ 窗口 {window_index}: DOM等待超时，继续...")

                # 固定等待时间，不依赖网络状态
                page.wait_for_timeout(10000)  # 等待10秒确保页面初始化
                print(f"✅ 窗口 {window_index}: 页面初始化完成")
                break
            except Exception as nav_error:
                print(
                    f"❌ 窗口 {window_index}: 导航尝试 {nav_attempt + 1} 失败: {nav_error}"
                )
                if nav_attempt == max_navigation_retries - 1:
                    raise Exception(f"窗口 {window_index}: 所有导航尝试都失败")
                else:
                    print(f"🔄 窗口 {window_index}: 等待5秒后重试...")
                    time.sleep(5)

        # 发送随机问题进行热身
        random_question = random.choice(WARMUP_QUESTIONS)
        print(f"🔥 窗口 {window_index}: 发送热身问题: {random_question}")

        # 热身文本框选择器 - 使用Gemini App的选择器
        textarea_selectors = [
            'rich-textarea .ql-editor[contenteditable="true"]',
            "rich-textarea div.ql-editor",
            ".text-input-field_textarea .ql-editor",
            'div.ql-editor[data-placeholder="Ask Gemini"]',
            'div[contenteditable="true"][role="textbox"]',
            '[contenteditable="true"]',
            'div[role="textbox"]',
            ".ql-editor",
        ]

        warmup_textarea = None
        for selector in textarea_selectors:
            try:
                if page.locator(selector).count() > 0:
                    warmup_textarea = page.locator(selector).first
                    print(
                        f"窗口 {window_index}: 找到热身文本框，使用选择器: {selector}"
                    )
                    break
            except:
                continue

        if warmup_textarea and warmup_textarea.count() > 0:
            warmup_textarea.click()
            page.wait_for_timeout(1000)
            warmup_textarea.focus()
            page.wait_for_timeout(500)

            # 对于contenteditable元素，使用不同的清空方法
            page.keyboard.press("Control+a")
            page.wait_for_timeout(300)
            page.keyboard.press("Delete")
            page.wait_for_timeout(300)

            warmup_textarea.fill(random_question)
            page.wait_for_timeout(1000)
            print(f"窗口 {window_index}: 已输入热身问题到文本框")

            # 发送按钮选择器 - 使用Gemini App的选择器
            run_button_selectors = [
                "button.send-button",
                "button.mdc-icon-button.send-button",
                "button.mat-mdc-icon-button.send-button",
                'button[aria-label="Send message"]',
                'button:has(mat-icon[fonticon="send"])',
                'button:has-text("Send")',
                'button[type="submit"]',
            ]

            warmup_run_button = None
            for selector in run_button_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        warmup_run_button = page.locator(selector).first
                        break
                except:
                    continue

            if warmup_run_button and warmup_run_button.count() > 0:
                print(f"窗口 {window_index}: 发送热身问题...")
                warmup_run_button.click()

                try:
                    wait_for_warmup_completion(page, window_index)
                    print(f"窗口 {window_index}: 热身问题回答完成")
                except Exception as e:
                    print(f"窗口 {window_index}: 热身问题回答过程中出错: {e}")
                    raise Exception(f"窗口 {window_index}: 热身阶段AI生成状态检测失败")

                print(f"窗口 {window_index}: 热身完成，等待5秒...")
                time.sleep(5)

                print(f"窗口 {window_index}: 开新tab进行正式故事生成...")

                # 热身后导航，使用简化的等待机制
                for nav_attempt in range(3):
                    try:
                        print(
                            f"🔗 窗口 {window_index}: 新tab导航尝试 {nav_attempt + 1}/3"
                        )
                        page.goto("https://gemini.google.com/app", timeout=60000)
                        print(f"✅ 窗口 {window_index}: 新tab导航成功")

                        # 简化等待策略
                        try:
                            page.wait_for_load_state("domcontentloaded", timeout=15000)
                            print(f"✅ 窗口 {window_index}: 新tab DOM加载完成")
                        except:
                            print(f"⚠️ 窗口 {window_index}: 新tab DOM等待超时，继续...")

                        page.wait_for_timeout(10000)
                        print(f"✅ 窗口 {window_index}: 新页面已完全加载")
                        break
                    except Exception as nav_error:
                        print(
                            f"❌ 窗口 {window_index}: 新tab导航尝试 {nav_attempt + 1} 失败: {nav_error}"
                        )
                        if nav_attempt == 2:
                            raise Exception(f"窗口 {window_index}: 新tab导航失败")
                        else:
                            print(f"🔄 窗口 {window_index}: 等待5秒后重试...")
                            time.sleep(5)
            else:
                print(f"窗口 {window_index}: 热身阶段未找到发送按钮，跳过热身")
        else:
            print(f"窗口 {window_index}: 热身阶段未找到文本框，跳过热身")
    elif is_first_story and not need_warmup:
        print(f"窗口 {window_index}: 窗口第一次（跳过热身），正在打开Gemini App...")

        # 第一次无热身导航，使用简化的等待机制
        for nav_attempt in range(3):
            try:
                print(f"🔗 窗口 {window_index}: 首次导航尝试 {nav_attempt + 1}/3")
                page.goto("https://gemini.google.com/app", timeout=60000)
                print(f"✅ 窗口 {window_index}: 首次导航成功")

                # 简化等待策略
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                    print(f"✅ 窗口 {window_index}: 首次DOM加载完成")
                except:
                    print(f"⚠️ 窗口 {window_index}: 首次DOM等待超时，继续...")

                page.wait_for_timeout(10000)
                print(f"✅ 窗口 {window_index}: 页面已完全加载")
                break
            except Exception as nav_error:
                print(
                    f"❌ 窗口 {window_index}: 首次导航尝试 {nav_attempt + 1} 失败: {nav_error}"
                )
                if nav_attempt == 2:
                    raise Exception(f"窗口 {window_index}: 首次导航失败")
                else:
                    print(f"🔄 窗口 {window_index}: 等待5秒后重试...")
                    time.sleep(5)
    elif not is_first_story:
        print(f"窗口 {window_index}: 导航到新的Gemini聊天页面...")

        # 非第一次故事导航，使用简化的等待机制
        for nav_attempt in range(3):
            try:
                print(f"🔗 窗口 {window_index}: 新聊天导航尝试 {nav_attempt + 1}/3")
                page.goto("https://gemini.google.com/app", timeout=60000)
                print(f"✅ 窗口 {window_index}: 新聊天导航成功")

                # 简化等待策略
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                    print(f"✅ 窗口 {window_index}: 新聊天DOM加载完成")
                except:
                    print(f"⚠️ 窗口 {window_index}: 新聊天DOM等待超时，继续...")

                page.wait_for_timeout(10000)
                print(f"✅ 窗口 {window_index}: 新页面已完全加载")
                break
            except Exception as nav_error:
                print(
                    f"❌ 窗口 {window_index}: 新聊天导航尝试 {nav_attempt + 1} 失败: {nav_error}"
                )
                if nav_attempt == 2:
                    raise Exception(f"窗口 {window_index}: 新聊天导航失败")
                else:
                    print(f"🔄 窗口 {window_index}: 等待5秒后重试...")
                    time.sleep(5)

    # 重试逻辑：最多尝试3次生成故事
    for retry_count in range(max_retries):
        try:
            if retry_count > 0:
                print(
                    f"窗口 {window_index}: {theme_name}故事 {story_data['index']} 第 {retry_count + 1} 次尝试（重试原因：生成失败）"
                )
            else:
                print(
                    f"窗口 {window_index}: 开始处理{theme_name}故事 {story_data['index']}"
                )

            # 正式的故事生成流程
            # Gemini App的文本框选择器
            textarea_selectors = [
                'rich-textarea .ql-editor[contenteditable="true"]',
                "rich-textarea div.ql-editor",
                ".text-input-field_textarea .ql-editor",
                'div.ql-editor[data-placeholder="Ask Gemini"]',
                'div[contenteditable="true"][role="textbox"]',
                '[contenteditable="true"]',
                'div[role="textbox"]',
                ".ql-editor",
            ]

            print(f"窗口 {window_index}: 尝试查找文本框...")
            textarea = None

            # 首先等待父容器出现
            try:
                print(f"窗口 {window_index}: 等待文本输入容器...")
                page.wait_for_selector(
                    "rich-textarea, .text-input-field_textarea, .ql-editor",
                    timeout=20000,
                )
                page.wait_for_timeout(3000)  # 额外等待容器内容加载
                print(f"窗口 {window_index}: 文本输入容器已加载")
            except:
                print(f"窗口 {window_index}: 父容器等待超时，继续尝试...")

            # 尝试多个选择器
            for i, selector in enumerate(textarea_selectors):
                try:
                    print(
                        f"🔍 窗口 {window_index}: 尝试定位文本框... ({i+1}/{len(textarea_selectors)})"
                    )
                    page.wait_for_selector(selector, timeout=15000)
                    textarea = page.locator(selector).first
                    if textarea.count() > 0:
                        print(f"✅ 窗口 {window_index}: 成功找到文本框")
                        break
                except Exception as e:
                    print(f"⚠️ 窗口 {window_index}: 文本框定位尝试失败")
                    continue

            if not textarea or textarea.count() == 0:
                print(f"❌ 窗口 {window_index}: 无法找到文本框")
                if retry_count == max_retries - 1:
                    return False
                continue

            # 直接输入故事参数到文本框
            print(f"📝 窗口 {window_index}: 正在输入故事参数...")

            # 确保元素可见和可交互
            textarea.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)

            # 点击文本框并获得焦点
            textarea.click()
            page.wait_for_timeout(500)

            # 确保文本框获得焦点
            textarea.focus()
            page.wait_for_timeout(500)

            # 清空现有内容 - 对于contenteditable元素
            print(f"🧹 窗口 {window_index}: 清空现有内容...")
            page.keyboard.press("Control+a")
            page.wait_for_timeout(500)
            page.keyboard.press("Delete")
            page.wait_for_timeout(500)

            # 分段输入长文本，避免一次性输入过多导致问题
            story_prompt = story_data["prompt"]
            print(f"📊 窗口 {window_index}: 故事参数长度: {len(story_prompt)} 字符")

            # 尝试直接使用 fill() 方法快速输入整个文本
            try:
                print(f"⚡ 窗口 {window_index}: 尝试快速输入文本...")
                textarea.fill(story_prompt)
                page.wait_for_timeout(500)

                # 验证输入是否成功 - 对于contenteditable元素使用inner_text()
                current_text = textarea.inner_text()
                if (
                    len(current_text) >= len(story_prompt) * 0.95
                ):  # 如果输入了95%以上内容，认为成功
                    print(
                        f"✅ 窗口 {window_index}: 快速输入成功 ({len(current_text)} 字符)"
                    )
                else:
                    raise Exception("快速输入不完整，切换到分段输入")

            except Exception as e:
                print(f"📝 窗口 {window_index}: 切换到分段输入模式...")

                # 备用方案：分段输入，但使用更快的方式
                chunk_size = 2000  # 增大chunk大小
                page.keyboard.press("Control+a")
                page.wait_for_timeout(300)
                page.keyboard.press("Delete")
                page.wait_for_timeout(300)

                accumulated_text = ""
                for i in range(0, len(story_prompt), chunk_size):
                    chunk = story_prompt[i : i + chunk_size]
                    accumulated_text += chunk

                    # 使用 JavaScript 直接设置值，这比 type() 快很多
                    try:
                        page.evaluate(
                            """
                            (text) => {
                                const textarea = document.querySelector('rich-textarea .ql-editor[contenteditable="true"]') || 
                                               document.querySelector('.ql-editor[contenteditable="true"]') || 
                                               document.querySelector('[contenteditable="true"]');
                                if (textarea) {
                                    textarea.textContent = text;
                                    textarea.dispatchEvent(new Event('input', { bubbles: true }));
                                    textarea.dispatchEvent(new Event('change', { bubbles: true }));
                                }
                            }
                        """,
                            accumulated_text,
                        )

                        progress = (i + chunk_size) / len(story_prompt) * 100
                        print(f"📝 窗口 {window_index}: 输入进度 {progress:.0f}%")

                        # chunk间短暂等待
                        if i + chunk_size < len(story_prompt):
                            page.wait_for_timeout(100)  # 减少等待时间

                    except Exception as js_error:
                        print(f"⚠️ 窗口 {window_index}: 切换到备用输入方式...")
                        # 回退到 fill() 方式
                        textarea.fill(accumulated_text)
                        page.wait_for_timeout(200)

            print(f"✅ 窗口 {window_index}: 故事参数输入完成")

            # 输入完成后等待3-5秒再发送
            wait_before_run = random.randint(3, 5)
            print(f"⏰ 窗口 {window_index}: 等待 {wait_before_run} 秒后发送...")
            time.sleep(wait_before_run)

            # 确保文本框仍然有焦点
            textarea.focus()
            page.wait_for_timeout(500)

            # 查找并点击发送按钮
            print(f"🚀 窗口 {window_index}: 发送故事生成请求...")

            # Gemini App的发送按钮选择器
            send_button_selectors = [
                "button.send-button",
                "button.mdc-icon-button.send-button",
                "button.mat-mdc-icon-button.send-button",
                'button[aria-label="Send message"]',
                'button:has(mat-icon[fonticon="send"])',
                'button:has-text("Send")',
                'button[type="submit"]',
            ]

            send_button = None
            for selector in send_button_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        send_button = page.locator(selector).first
                        print(
                            f"✅ 窗口 {window_index}: 找到发送按钮，使用选择器: {selector}"
                        )
                        break
                except:
                    continue

            if send_button and send_button.count() > 0:
                send_button.click()
                page.wait_for_timeout(1000)
            else:
                # 备用方案：使用快捷键发送
                print(f"⚠️ 窗口 {window_index}: 未找到发送按钮，使用快捷键发送...")
                page.keyboard.press("Control+Enter")
                page.wait_for_timeout(1000)

            # 等待AI运行完成
            try:
                wait_for_ai_completion(page, window_index)
            except Exception as e:
                error_msg = str(e)
                print(f"窗口 {window_index}: AI等待完成失败 - {error_msg}")

                # 检查是否是超时错误（不重试）
                if "超时" in error_msg or "timeout" in error_msg.lower():
                    print(f"❌ 窗口 {window_index}: 遇到超时错误，停止重试")
                    return False
                else:
                    # 其他情况都重试
                    if retry_count < max_retries - 1:
                        print(f"🔄 窗口 {window_index}: AI等待失败，准备重试...")
                        print(
                            f"🔁 窗口 {window_index}: 将在当前标签页重新输入并重试..."
                        )
                        print(f"⏳ 窗口 {window_index}: 等待3秒后重试...")
                        time.sleep(3)
                        continue  # 继续下一次重试
                    else:
                        print(
                            f"❌ 窗口 {window_index}: 已达到最大重试次数({max_retries})，跳过此故事"
                        )
                        return False

            # 保存生成的故事
            success = save_generated_story(
                page, story_data["index"], story_data["dir_path"], theme
            )

            if success:
                print(
                    f"🎉 窗口 {window_index}: {theme_name}故事 {story_data['index']} 处理完成"
                )
                # 生成完成后随机等待20-30秒
                wait_time = random.randint(20, 30)
                print(
                    f"❄️ 窗口 {window_index}: 故事生成完成，开始随机冷却等待 {wait_time} 秒..."
                )
                countdown_wait(wait_time, window_index)
                return True
            else:
                print(
                    f"❌ 窗口 {window_index}: {theme_name}故事 {story_data['index']} 保存失败"
                )
                if retry_count < max_retries - 1:
                    print(f"🔄 窗口 {window_index}: 保存失败，准备重试...")
                    continue
                else:
                    return False

        except Exception as e:
            error_msg = str(e)
            print(
                f"窗口 {window_index}: 处理{theme_name}故事 {story_data['index']} 时出错: {error_msg}"
            )

            # 检查是否是超时错误（不重试）
            if "超时" in error_msg or "timeout" in error_msg.lower():
                print(f"❌ 窗口 {window_index}: 遇到超时错误，停止重试")
                import traceback

                traceback.print_exc()
                return False
            else:
                # 其他错误都重试
                if retry_count < max_retries - 1:
                    print(f"🔄 窗口 {window_index}: 处理出错，将重试...")
                    print(f"⏳ 窗口 {window_index}: 等待3秒后重试...")
                    time.sleep(3)
                    continue
                else:
                    print(f"❌ 窗口 {window_index}: 已达到最大重试次数，跳过此故事")
                    import traceback

                    traceback.print_exc()
                    return False

    # 如果所有重试都用完了但没有成功
    print(
        f"窗口 {window_index}: {theme_name}故事 {story_data['index']} 所有重试都失败，跳过此故事"
    )
    return False


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="AI Studio 多主题故事生成自动化脚本",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
支持的主题:
  scifi     - 科幻故事
  fantasy   - 奇幻故事
  thriller  - 惊悚故事
  romance   - 爱情故事
  horror    - 恐怖故事

使用示例:
  python ai_studio_bot.py --count 5                                    # 所有主题各生成5个故事
  python ai_studio_bot.py --theme scifi fantasy --count 3              # 只为科幻和奇幻各生成3个故事
  python ai_studio_bot.py --theme scifi --count 2 --ads-id your_id     # 指定浏览器ID
        """,
    )
    parser.add_argument(
        "--count", "-c", type=int, default=2, help="每个主题要生成的故事数量 (默认: 2)"
    )
    parser.add_argument(
        "--ads-id", default="k10i5y1s", help="AdsPower 浏览器ID (默认: k10i5y1s)"
    )
    parser.add_argument(
        "--theme",
        "-t",
        nargs="*",
        choices=list(SUPPORTED_THEMES.keys()),
        help="要生成故事的主题列表 (默认: 所有主题)",
    )
    parser.add_argument("--list-themes", action="store_true", help="列出所有支持的主题")
    parser.add_argument(
        "--check-resume", action="store_true", help="检查断点续传状态（不执行生成）"
    )

    args = parser.parse_args()

    # 如果用户请求列出主题，显示后退出
    if args.list_themes:
        list_available_themes()
        return

    # 如果用户请求检查断点续传状态，检查后退出
    if args.check_resume:
        # 确定要检查的主题
        if args.theme:
            themes_to_check = args.theme
        else:
            themes_to_check = list(SUPPORTED_THEMES.keys())

        print(f"\n🔍 检查断点续传状态 - 共 {len(themes_to_check)} 个主题")

        # 显示系统信息
        base_dir = get_base_audio_dir()
        machine_type = (
            "Intel Mac" if "/Volumes/dhl" in base_dir else "Apple Silicon Mac"
        )
        print(f"💻 检测到系统类型: {machine_type}")
        print(f"📁 音频基础目录: {base_dir}")

        total_existing = 0
        total_params = 0

        for theme in themes_to_check:
            try:
                validate_theme(theme)
                status = check_theme_resume_status(theme)
                if status:
                    total_existing += status.get("existing_stories", 0)
                    total_params += status.get("available_params", 0)
            except ValueError as e:
                print(f"❌ {e}")

        print(f"\n📊 总体统计:")
        print(f"   总已有故事: {total_existing} 个")
        print(f"   总可用参数: {total_params} 个")
        print(f"   理论可生成: {total_params} 个新故事")

        return

    # 确定要处理的主题
    if args.theme:
        themes = args.theme
        # 验证每个主题
        for theme in themes:
            try:
                validate_theme(theme)
            except ValueError as e:
                print(f"❌ {e}")
                list_available_themes()
                return
    else:
        # 默认使用所有可用主题
        themes = list(SUPPORTED_THEMES.keys())
        print("🎯 未指定主题，将为所有主题生成故事")

    # 验证参数
    if args.count <= 0:
        print("❌ 错误：故事数量必须大于 0")
        return

    total_stories = len(themes) * args.count
    if total_stories > 20:
        print(
            f"⚠️ 警告：总共要生成 {total_stories} 个故事（{len(themes)}个主题 × {args.count}个/主题）"
        )
        print("建议不要一次生成超过 20 个故事，以免浏览器性能问题")
        response = input("是否继续？(y/N): ")
        if response.lower() != "y":
            print("已取消")
            return

    ads_id = args.ads_id
    story_count_per_theme = args.count

    print(f"🎯 准备轮流为 {len(themes)} 个主题生成故事")
    for theme in themes:
        theme_name = SUPPORTED_THEMES[theme]["name"]
        print(f"  📚 {theme_name}({theme}): {story_count_per_theme} 个故事")
    print(f"🌐 使用 AdsPower ID: {ads_id}")

    close_url = f"http://127.0.0.1:50325/api/v1/browser/stop?user_id={ads_id}"

    try:
        # 显示系统信息和保存路径
        base_dir = get_base_audio_dir()
        machine_type = (
            "Intel Mac" if "/Volumes/dhl" in base_dir else "Apple Silicon Mac"
        )
        print(f"\n🖥️  系统信息:")
        print(f"   检测到: {machine_type}")
        print(f"   基础目录: {base_dir}")

        print(f"\n📁 故事保存路径说明:")
        print(f"   路径格式: {base_dir}/{{主题}}/full_story/{{索引}}.txt")
        print(f"   例如科幻故事: {base_dir}/scifi/full_story/1.txt")

        # 为所有主题创建故事保存目录
        print(f"\n📂 创建各主题故事保存目录:")
        for theme in themes:
            story_dir_path = get_theme_story_path_prefix(theme)
            os.makedirs(story_dir_path, exist_ok=True)
            theme_name = SUPPORTED_THEMES[theme]["name"]
            print(f"   ✅ {theme_name}({theme}): {story_dir_path}")

        # 准备多主题轮流生成计划
        stories_to_generate = prepare_multi_theme_generation(
            themes, story_count_per_theme
        )

        if not stories_to_generate:
            print("⚠️ 没有需要生成的故事")
            return

        print(f"📋 实际需要生成 {len(stories_to_generate)} 个故事（轮流模式）")

        # 获取WebDriver
        ws_endpoint, remote_debugging_url, http = get_adspower_info(ads_id)

        if not ws_endpoint:
            return

        # 使用Playwright连接浏览器
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("❌ 错误: 缺少 playwright 模块，请安装: pip install playwright")
            return

        print("🔌 正在使用Playwright连接浏览器...")
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(remote_debugging_url)
            print("✅ 成功连接到浏览器！")

            # 获取或创建上下文
            if not browser.contexts:
                context = browser.new_context()
            else:
                context = browser.contexts[0]

            # 先创建一个新的空白页面，确保浏览器不会关闭
            print("正在创建新的空白页面...")
            new_page = context.new_page()
            print("已创建新的空白页面")

            # 记录所有需要关闭的现有页面（除了刚创建的新页面）
            pages_to_close = []
            for page in context.pages:
                if page != new_page:  # 不包括刚创建的新页面
                    pages_to_close.append(page)

            # 关闭所有其他已存在的窗口
            if pages_to_close:
                print(f"正在关闭之前的 {len(pages_to_close)} 个窗口...")
                for i, page in enumerate(pages_to_close):
                    try:
                        page.close()
                        print(f"已关闭第 {i+1} 个之前的窗口")
                    except Exception as e:
                        print(f"关闭第 {i+1} 个窗口时出错: {e}")
            else:
                print("没有需要关闭的之前窗口")

            # 修改为轮流生成模式：只使用一个窗口，严格按照轮流顺序生成
            print(f"🔄 使用单窗口轮流生成模式，确保严格按主题轮流顺序...")

            # 只使用一个窗口
            main_window = new_page
            print(f"使用主窗口进行轮流故事生成")

            # 逐一处理每个故事，严格按照轮流顺序
            all_results = []

            # 全局热身标志，跳过热身直接开始故事生成
            global_warmup_done = True
            # 第一个故事标志
            is_first_story = True

            for story_index, story_data in enumerate(stories_to_generate):
                story_theme = story_data["theme"]
                theme_name = SUPPORTED_THEMES[story_theme]["name"]

                print(
                    f"\n=== 🎯 轮流生成第 {story_index + 1}/{len(stories_to_generate)} 个故事 ==="
                )
                print(f"📚 当前主题: {theme_name}({story_theme})")
                print(f"📄 故事索引: {story_data['index']}")
                print(
                    f"📁 保存路径: {story_data['dir_path']}/{story_data['index']}.txt"
                )

                # 切换到主窗口并使其获得焦点
                try:
                    main_window.bring_to_front()
                except Exception as bring_error:
                    print(f"主窗口已失效，尝试重新创建: {bring_error}")
                    main_window = context.new_page()

                # 处理当前故事
                try:
                    # 传递是否是第一个故事的标志和是否需要热身
                    need_warmup = not global_warmup_done
                    success = process_window(
                        main_window,
                        1,  # 窗口编号固定为1
                        story_data,
                        story_theme,
                        is_first_story,
                        need_warmup,
                    )

                    # 更新全局热身状态和第一个故事状态
                    if need_warmup:
                        global_warmup_done = True
                        print(f"🎯 全局热身已完成，后续所有故事生成将跳过热身步骤")
                    else:
                        print(f"⚡ 已跳过热身，直接进行故事生成")

                    if is_first_story:
                        is_first_story = False
                        print(f"✅ 首个故事处理完成，后续将使用快速切换方式")

                    all_results.append(success)

                    if success:
                        print(f"🎉 {theme_name}故事 {story_data['index']} 生成成功！")
                        print(
                            f"📊 当前进度: {story_index + 1}/{len(stories_to_generate)} ({(story_index + 1)/len(stories_to_generate)*100:.1f}%)"
                        )
                    else:
                        print(f"❌ {theme_name}故事 {story_data['index']} 生成失败！")

                    # 显示轮流生成状态
                    if story_index + 1 < len(stories_to_generate):
                        next_story = stories_to_generate[story_index + 1]
                        next_theme_name = SUPPORTED_THEMES[next_story["theme"]]["name"]
                        print(
                            f"🔄 下一个故事: {next_theme_name}({next_story['theme']}) - 故事{next_story['index']}"
                        )

                except Exception as e:
                    # 所有错误都在process_window中处理，包括internal error重试
                    # 这里只记录错误并继续处理下一个故事
                    print(f"处理{theme_name}故事 {story_data['index']} 时发生异常: {e}")
                    all_results.append(False)
                    print(f"⏭️ 跳过此故事，继续处理下一个...")

                # 每个故事处理完成后的分隔提示
                if story_index + 1 < len(stories_to_generate):
                    print(f"{'='*60}")
                    print(f"⏱️ 故事间隔等待 3 秒...")
                    time.sleep(3)

            # 统计最终结果
            successful_stories = sum(all_results)
            total_stories = len(all_results)

            print(f"\n=== 🎉 所有故事处理完成 ===")
            print(f"✅ 成功生成: {successful_stories}/{total_stories} 个故事")
            if total_stories > 0:
                print(f"📊 成功率: {successful_stories/total_stories*100:.1f}%")
            else:
                print("📊 成功率: 无法计算（没有处理任何故事）")

            # 按主题分类显示结果
            print(f"\n📊 分主题统计:")
            theme_success = {}
            theme_total = {}

            for i, story_data in enumerate(stories_to_generate):
                theme = story_data["theme"]
                theme_name = SUPPORTED_THEMES[theme]["name"]

                if theme not in theme_total:
                    theme_total[theme] = 0
                    theme_success[theme] = 0

                theme_total[theme] += 1
                if i < len(all_results) and all_results[i]:
                    theme_success[theme] += 1

            for theme in sorted(theme_total.keys()):
                theme_name = SUPPORTED_THEMES[theme]["name"]
                success_count = theme_success[theme]
                total_count = theme_total[theme]
                if total_count > 0:
                    success_rate = success_count / total_count * 100
                    print(
                        f"  {theme_name}({theme}): {success_count}/{total_count} ({success_rate:.1f}%)"
                    )
                else:
                    print(
                        f"  {theme_name}({theme}): {success_count}/{total_count} (无数据)"
                    )

            # 关闭主窗口
            print("正在关闭主窗口...")
            try:
                # 检查窗口是否仍然有效
                if not main_window.is_closed():
                    main_window.close()
                    print("主窗口已关闭")
                else:
                    print("主窗口已经关闭")
            except Exception as e:
                print(f"关闭主窗口时出错: {e}")

            # 断开Playwright连接
            print("正在断开Playwright连接...")
            browser.close()
            print("已断开Playwright连接")

        # 关闭AdsPower浏览器
        print("正在关闭AdsPower浏览器...")
        http.request("GET", close_url)
        print("AdsPower浏览器已关闭")

    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
