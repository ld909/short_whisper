#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频片段合并脚本 (merge_audio_clips.py)
====================================

⚠️ 重要提醒：此脚本仅支持 Ubuntu/Linux 系统运行，不支持 macOS 或 Windows 系统。

功能说明
-------
将音频片段按故事合并为完整的故事音频文件。支持多主题批量处理和断点续传。

主要特性
-------
- 支持多主题批量处理（scifi, thriller, horror, fantasy, romance）
- 断点续传功能，自动跳过已存在的有效文件
- 智能文件验证和Mac系统文件过滤
- 详细的进度显示和统计信息

输入要求
-------
- 输入目录：`/home/dhl/Documents/audio/mp3_clips/{theme}/`
- 文件格式：MP3音频片段（1.mp3, 2.mp3, 3.mp3...）
- 目录结构：`{theme}/{story_index}/{chunk_index}.mp3`

输出路径
-------
- 输出目录：`/mnt/dhl/audio/{theme}/mp3_merge/`
- 输出文件：`{story_index}/story.mp3`

系统要求
-------
- 操作系统：仅支持 Ubuntu/Linux 系统
- 依赖工具：ffmpeg
- Python 3.6+

使用示例
-------
```bash
# 处理所有主题（传统模式）
python merge_audio_clips.py

# 处理指定主题
python merge_audio_clips.py --theme scifi

# 预览模式
python merge_audio_clips.py --theme thriller --preview

# 强制重新生成
python merge_audio_clips.py --theme horror --force-regenerate

# 启用一致性检查（推荐：指定主题）
python merge_audio_clips.py --check-consistency --theme fantasy

# 一致性检查 + 预览模式
python merge_audio_clips.py --check-consistency --theme thriller --preview

# 一致性检查 + 强制重新生成
python merge_audio_clips.py --check-consistency --theme scifi --force-regenerate

# 传统模式：书籍音频一致性检查（已废弃）
python merge_audio_clips.py --check-consistency --lang en --theme all

# 指定自定义chunk目录进行一致性检查
python merge_audio_clips.py --check-consistency --theme horror --chunk-dir /custom/path/to/chunks
```

一致性检查功能说明
---------------
- `--check-consistency`: 启用chunk文本文件和mp3音频文件数量一致性检查
- `--theme`: 指定主题类型（scifi/thriller/horror/fantasy/romance），自动使用对应主题路径
- `--lang`: 语言类型（en/zh），用于传统书籍音频路径（已废弃，建议使用主题路径）
- `--chunk-dir`: 可选，指定自定义chunk文件目录（默认根据主题自动选择）
- 只有当chunk数量与mp3数量完全匹配时才会进行音频合并
- 推荐使用主题路径结构：
  - Chunk目录：`/home/dhl/Documents/audio/chunks/{theme}/{story_index}/`
  - MP3目录：`/home/dhl/Documents/audio/mp3_clips/{theme}/{story_index}/`
- 适用于故事音频处理流水线，确保数据完整性

"""

import os
import glob
import argparse
import subprocess
import time
import platform
from pathlib import Path


# ============ 配置参数 ============
# 支持的主题列表
SUPPORTED_THEMES = ["scifi", "thriller", "horror", "fantasy", "romance"]


# 输入目录：根据操作系统和主题自动选择
def get_input_dir(theme):
    """根据操作系统和主题返回合适的输入目录"""
    if platform.system() == "Linux":  # Ubuntu
        return f"/home/dhl/Documents/audio/mp3_clips/{theme}"
    else:  # 其他系统
        print("❌ 此脚本只能在Ubuntu系统上运行！")
        print(f"🖥️  当前系统: {platform.system()}")
        exit(1)


# 输出目录：根据操作系统和主题自动选择
def get_output_dir(theme):
    """根据操作系统和主题返回合适的输出目录"""
    if platform.system() == "Linux":  # Ubuntu
        return f"/mnt/dhl/audio/{theme}/mp3_merge"
    else:  # 其他系统
        print("❌ 此脚本只能在Ubuntu系统上运行！")
        print(f"🖥️  当前系统: {platform.system()}")
        exit(1)


# 新增：获取主题相关路径配置
def get_theme_chunk_dir(theme):
    """获取主题chunk文本文件目录路径"""
    return f"/home/dhl/Documents/audio/chunks/{theme}"


def get_theme_mp3_dir(theme):
    """获取主题mp3音频文件目录路径"""
    return f"/home/dhl/Documents/audio/mp3_clips/{theme}"


# 兼容性函数：为书籍音频保留原有接口（已废弃，使用主题路径）
def get_book_chunk_dir(lang="en"):
    """获取书籍chunk文本文件目录路径（已废弃，请使用get_theme_chunk_dir）"""
    print("⚠️  警告：get_book_chunk_dir已废弃，请使用主题相关的路径配置")
    return f"/home/dhl/Documents/book/{lang}"


def get_book_mp3_dir(lang="en"):
    """获取书籍mp3音频文件目录路径（已废弃，请使用get_theme_mp3_dir）"""
    print("⚠️  警告：get_book_mp3_dir已废弃，请使用主题相关的路径配置")
    if lang == "zh":
        return "/home/dhl/Documents/audio/mp3_clips/book/book_zh"
    else:  # lang == "en"
        return "/home/dhl/Documents/audio/mp3_clips/book/book_en"


# 合并后的文件名
OUTPUT_FILENAME = "story.mp3"
# ===================================


def check_ubuntu_system():
    """
    检查是否为Ubuntu系统

    Returns:
        bool: 是否为Ubuntu系统
    """
    try:
        # 检查系统类型
        if platform.system() != "Linux":
            return False

        # 检查是否为Ubuntu
        with open("/etc/os-release", "r") as f:
            content = f.read()
            if "Ubuntu" in content or "ubuntu" in content:
                return True

        return False
    except:
        return False


def get_chunk_files_count(chunk_dir, uuid):
    """
    获取指定UUID的chunk文本文件数量
    
    Args:
        chunk_dir (str): chunk文本文件基础目录
        uuid (str): 书籍或故事UUID
        
    Returns:
        int: chunk文件数量
        list: chunk文件路径列表
    """
    uuid_chunk_dir = os.path.join(chunk_dir, uuid)
    
    if not os.path.exists(uuid_chunk_dir):
        print(f"❌ [UUID:{uuid[:8]}...] chunk目录不存在: {uuid_chunk_dir}")
        return 0, []
        
    # 获取所有txt文件
    txt_pattern = os.path.join(uuid_chunk_dir, "*.txt")
    all_txt_files = glob.glob(txt_pattern)
    
    # 过滤掉以点开头的Mac系统文件
    chunk_files = []
    for txt_file in all_txt_files:
        filename = os.path.basename(txt_file)
        if not filename.startswith(".") and not filename.startswith("._"):
            chunk_files.append(txt_file)
    
    # 按chunk索引排序
    def extract_chunk_number(filepath):
        basename = os.path.basename(filepath)
        try:
            return int(basename.split(".")[0])
        except:
            return 0
    
    chunk_files.sort(key=extract_chunk_number)
    
    print(f"📄 [UUID:{uuid[:8]}...] 找到 {len(chunk_files)} 个chunk文本文件")
    return len(chunk_files), chunk_files


def get_mp3_files_count(mp3_dir, uuid):
    """
    获取指定UUID的mp3音频文件数量
    
    Args:
        mp3_dir (str): mp3音频文件基础目录
        uuid (str): 书籍或故事UUID
        
    Returns:
        int: mp3文件数量
        list: mp3文件路径列表
    """
    uuid_mp3_dir = os.path.join(mp3_dir, uuid)
    
    if not os.path.exists(uuid_mp3_dir):
        print(f"❌ [UUID:{uuid[:8]}...] mp3目录不存在: {uuid_mp3_dir}")
        return 0, []
        
    # 获取所有mp3文件
    mp3_pattern = os.path.join(uuid_mp3_dir, "*.mp3")
    all_mp3_files = glob.glob(mp3_pattern)
    
    # 过滤掉以点开头的Mac系统文件，并验证文件有效性
    mp3_files = []
    for mp3_file in all_mp3_files:
        filename = os.path.basename(mp3_file)
        if not filename.startswith(".") and not filename.startswith("._"):
            # 检查文件是否有效
            if is_valid_audio_file(mp3_file):
                mp3_files.append(mp3_file)
            else:
                print(f"⚠️  [UUID:{uuid[:8]}...] 跳过无效mp3文件: {mp3_file}")
    
    # 按chunk索引排序
    def extract_chunk_number(filepath):
        basename = os.path.basename(filepath)
        try:
            return int(basename.split(".")[0])
        except:
            return 0
    
    mp3_files.sort(key=extract_chunk_number)
    
    print(f"🎵 [UUID:{uuid[:8]}...] 找到 {len(mp3_files)} 个有效mp3音频文件")
    return len(mp3_files), mp3_files


def check_chunk_mp3_consistency(chunk_dir, mp3_dir, uuid):
    """
    检查指定UUID的chunk文件数量和mp3文件数量是否一致
    
    Args:
        chunk_dir (str): chunk文本文件基础目录
        mp3_dir (str): mp3音频文件基础目录
        uuid (str): 书籍或故事UUID
        
    Returns:
        bool: 数量是否一致
        dict: 详细信息
    """
    print(f"\n🔍 [UUID:{uuid[:8]}...] 检查chunk和mp3文件数量一致性...")
    
    # 获取chunk文件数量
    chunk_count, chunk_files = get_chunk_files_count(chunk_dir, uuid)
    
    # 获取mp3文件数量
    mp3_count, mp3_files = get_mp3_files_count(mp3_dir, uuid)
    
    # 检查数量是否一致
    is_consistent = chunk_count == mp3_count and chunk_count > 0
    
    result = {
        "uuid": uuid,
        "chunk_count": chunk_count,
        "mp3_count": mp3_count,
        "is_consistent": is_consistent,
        "chunk_files": chunk_files,
        "mp3_files": mp3_files
    }
    
    if is_consistent:
        print(f"✅ [UUID:{uuid[:8]}...] 数量检查通过: chunk={chunk_count}, mp3={mp3_count}")
    else:
        print(f"❌ [UUID:{uuid[:8]}...] 数量检查失败: chunk={chunk_count}, mp3={mp3_count}")
        
        if chunk_count == 0:
            print(f"   💡 [UUID:{uuid[:8]}...] 没有找到chunk文本文件")
        if mp3_count == 0:
            print(f"   💡 [UUID:{uuid[:8]}...] 没有找到mp3音频文件")
        if chunk_count > 0 and mp3_count > 0 and chunk_count != mp3_count:
            print(f"   💡 [UUID:{uuid[:8]}...] chunk文件数量 ({chunk_count}) 与 mp3文件数量 ({mp3_count}) 不匹配")
            print(f"   💡 [UUID:{uuid[:8]}...] 请检查 synthesize_book_audio.py 是否完整执行")
    
    return is_consistent, result


def get_story_directories(input_dir):
    """
    获取所有故事目录，排除Mac生成的隐藏文件

    Args:
        input_dir (str): 输入目录路径

    Returns:
        list: 排序后的故事目录列表
    """
    if not os.path.exists(input_dir):
        print(f"❌ 输入目录不存在: {input_dir}")
        return []

    story_dirs = []

    # 遍历所有子目录
    for item in os.listdir(input_dir):
        item_path = os.path.join(input_dir, item)

        # 排除隐藏文件和目录
        if item.startswith("."):
            print(f"⏭️  跳过隐藏目录: {item}")
            continue

        # 只处理目录
        if os.path.isdir(item_path):
            story_dirs.append((item, item_path))

    # 按故事索引排序
    def extract_story_number(item):
        story_index = item[0]
        try:
            return int(story_index)
        except:
            return 0

    story_dirs.sort(key=extract_story_number)

    print(f"📊 找到 {len(story_dirs)} 个故事目录")
    return story_dirs


def get_audio_clips(story_dir):
    """
    获取故事目录下的所有音频片段，按块索引排序

    Args:
        story_dir (str): 故事目录路径

    Returns:
        list: 排序后的音频文件路径列表
    """
    audio_files = []

    # 获取所有 mp3 文件
    mp3_pattern = os.path.join(story_dir, "*.mp3")
    found_files = glob.glob(mp3_pattern)

    # 过滤掉隐藏文件和临时文件
    for audio_file in found_files:
        filename = os.path.basename(audio_file)

        # 排除隐藏文件和临时文件
        if filename.startswith(".") or filename.startswith("._"):
            print(f"⏭️  跳过隐藏/临时文件: {audio_file}")
            continue

        audio_files.append(audio_file)

    # 按块索引排序
    def extract_chunk_number(filepath):
        basename = os.path.basename(filepath)
        try:
            return int(basename.split(".")[0])
        except:
            return 0

    audio_files.sort(key=extract_chunk_number)

    return audio_files


def is_valid_audio_file(file_path, min_size_bytes=1024):
    """
    检查音频文件是否有效

    Args:
        file_path (str): 音频文件路径
        min_size_bytes (int): 最小文件大小（字节）

    Returns:
        bool: 文件是否有效
    """
    if not os.path.exists(file_path):
        return False

    try:
        file_size = os.path.getsize(file_path)
        if file_size < min_size_bytes:
            print(f"⚠️  文件过小，可能损坏: {file_path} ({file_size} 字节)")
            return False
        return True
    except Exception as e:
        print(f"⚠️  检查文件时出错: {file_path}, 错误: {e}")
        return False


def merge_audio_clips(audio_files, output_file):
    """
    使用 ffmpeg 合并音频片段

    Args:
        audio_files (list): 音频文件路径列表
        output_file (str): 输出文件路径

    Returns:
        bool: 合并是否成功
    """
    if not audio_files:
        print(f"❌ 没有音频文件需要合并")
        return False

    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)

        # 创建临时文件列表
        temp_file_list = os.path.join(output_dir, "temp_file_list.txt")

        # 写入文件列表
        with open(temp_file_list, "w", encoding="utf-8") as f:
            for audio_file in audio_files:
                # 使用相对路径或绝对路径，确保路径中的特殊字符被正确处理
                escaped_path = audio_file.replace("'", "'\"'\"'")
                f.write(f"file '{escaped_path}'\n")

        print(f"📝 创建临时文件列表: {temp_file_list}")
        print(f"🔗 准备合并 {len(audio_files)} 个音频片段")

        # 构建 ffmpeg 命令 - 使用重新编码而不是直接复制
        cmd = [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            temp_file_list,
            "-acodec",
            "libmp3lame",  # 使用MP3编码器
            "-b:a",
            "192k",  # 设置比特率
            "-ar",
            "44100",  # 设置采样率
            "-ac",
            "1",  # 单声道
            "-y",  # 覆盖输出文件
            output_file,
        ]

        print(f"🔄 执行合并命令...")

        # 执行命令
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=3600  # 60分钟超时
        )

        # 清理临时文件
        try:
            os.remove(temp_file_list)
        except:
            pass

        if result.returncode == 0:
            print(f"✅ 音频合并成功: {output_file}")

            # 检查输出文件
            if is_valid_audio_file(output_file, min_size_bytes=10240):  # 至少10KB
                file_size = os.path.getsize(output_file)
                print(
                    f"📊 输出文件大小: {file_size:,} 字节 ({file_size/1024/1024:.1f} MB)"
                )
                return True
            else:
                print(f"❌ 输出文件无效或过小")
                return False
        else:
            print(f"❌ 音频合并失败:")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"❌ 音频合并超时: {output_file}")
        return False
    except Exception as e:
        print(f"❌ 音频合并出错: {e}")
        return False


def scan_existing_merged_files(output_dir):
    """
    扫描已存在的合并音频文件

    Args:
        output_dir (str): 输出目录路径

    Returns:
        set: 已存在的故事索引集合
    """
    existing_stories = set()

    if not os.path.exists(output_dir):
        return existing_stories

    print(f"🔍 扫描已存在的合并音频文件...")

    # 遍历所有故事目录
    for item in os.listdir(output_dir):
        if item.startswith("."):
            continue

        story_path = os.path.join(output_dir, item)
        if os.path.isdir(story_path):
            story_file = os.path.join(story_path, OUTPUT_FILENAME)

            if is_valid_audio_file(story_file, min_size_bytes=10240):
                existing_stories.add(item)
                file_size = os.path.getsize(story_file)
                print(f"✅ 已存在: 故事 {item} ({file_size:,} 字节)")
            else:
                print(f"🗑️  发现无效文件，将重新生成: {story_file}")
                try:
                    if os.path.exists(story_file):
                        os.remove(story_file)
                        print(f"✅ 已删除无效文件: {story_file}")
                except Exception as e:
                    print(f"❌ 删除无效文件失败: {e}")

    print(f"📊 找到 {len(existing_stories)} 个有效的合并音频文件")
    return existing_stories


def get_progress_stats(story_dirs, existing_stories):
    """
    获取进度统计信息

    Args:
        story_dirs (list): 所有故事目录列表
        existing_stories (set): 已存在的故事索引集合

    Returns:
        dict: 进度统计信息
    """
    total_stories = len(story_dirs)
    completed_stories = 0
    pending_stories = []

    for story_index, story_dir in story_dirs:
        if story_index in existing_stories:
            completed_stories += 1
        else:
            pending_stories.append((story_index, story_dir))

    remaining_stories = total_stories - completed_stories
    completion_rate = (
        (completed_stories / total_stories * 100) if total_stories > 0 else 0
    )

    return {
        "total_stories": total_stories,
        "completed_stories": completed_stories,
        "remaining_stories": remaining_stories,
        "pending_stories": pending_stories,
        "completion_rate": completion_rate,
    }


def process_story(story_index, story_dir, output_base_dir, force_regenerate=False, check_consistency=False, chunk_dir=None, lang="en", theme=None):
    """
    处理单个故事，合并其所有音频片段

    Args:
        story_index (str): 故事索引
        story_dir (str): 故事目录路径
        output_base_dir (str): 输出基础目录
        force_regenerate (bool): 是否强制重新生成
        check_consistency (bool): 是否检查chunk和mp3数量一致性
        chunk_dir (str): chunk文本文件目录（当check_consistency=True时需要）
        lang (str): 语言类型，用于书籍音频处理（en/zh）（已废弃）
        theme (str): 主题名称，用于确定正确的路径

    Returns:
        bool: 处理是否成功
    """
    print(f"\n📚 处理故事: {story_index}")
    print(f"   输入目录: {story_dir}")

    # 构建输出文件路径
    output_story_dir = os.path.join(output_base_dir, story_index)
    output_file = os.path.join(output_story_dir, OUTPUT_FILENAME)

    print(f"   输出文件: {output_file}")

    # 检查是否已存在且有效（除非强制重新生成）
    if not force_regenerate and is_valid_audio_file(output_file, min_size_bytes=10240):
        file_size = os.path.getsize(output_file)
        print(f"⏭️  文件已存在且有效，跳过: {output_file} ({file_size:,} 字节)")
        return True

    # 如果启用一致性检查，则检查chunk和mp3数量是否一致
    if check_consistency and chunk_dir:
        print(f"🔍 启用一致性检查模式...")
        
        # 故事索引就是UUID/故事ID
        uuid = story_index
        
        # 检查数量一致性
        # 使用主题相关的正确路径
        if theme:
            # 使用主题路径（推荐方式）
            chunk_base_dir = get_theme_chunk_dir(theme)
            mp3_base_dir = get_theme_mp3_dir(theme)
        else:
            # 向后兼容：使用传入的chunk_dir和lang参数
            chunk_base_dir = chunk_dir
            mp3_base_dir = get_book_mp3_dir(lang)
            
        is_consistent, check_result = check_chunk_mp3_consistency(chunk_base_dir, mp3_base_dir, uuid)
        
        if not is_consistent:
            print(f"❌ 故事 {story_index} 一致性检查失败，跳过合并")
            print(f"   Chunk文件数量: {check_result['chunk_count']}")
            print(f"   MP3文件数量: {check_result['mp3_count']}")
            if check_result['chunk_count'] == 0:
                if theme:
                    print(f"   💡 建议: 检查 {chunk_base_dir}/{story_index}/ 目录是否存在chunk文件")
                else:
                    print(f"   💡 建议: 先运行 chunk_book_summaries.py 生成chunk文件")
            if check_result['mp3_count'] == 0:
                if theme:
                    print(f"   💡 建议: 检查 {mp3_base_dir}/{story_index}/ 目录是否存在mp3文件")
                else:
                    print(f"   💡 建议: 先运行 synthesize_book_audio.py --lang {lang} 生成音频文件")
            elif check_result['chunk_count'] != check_result['mp3_count']:
                if theme:
                    print(f"   💡 建议: 重新运行音频合成，确保所有chunk都已合成音频")
                else:
                    print(f"   💡 建议: 重新运行 synthesize_book_audio.py --lang {lang} 确保所有chunk都已合成音频")
            return False
        else:
            print(f"✅ 故事 {story_index} 一致性检查通过，继续合并...")
            # 使用检查结果中的有效mp3文件列表
            valid_clips = check_result['mp3_files']
    else:
        # 原有逻辑：获取所有音频片段
        audio_clips = get_audio_clips(story_dir)

        if not audio_clips:
            print(f"❌ 故事 {story_index} 没有找到音频片段")
            return False

        print(f"📊 找到 {len(audio_clips)} 个音频片段")

        # 检查所有片段是否有效
        valid_clips = []
        for clip in audio_clips:
            if is_valid_audio_file(clip):
                valid_clips.append(clip)
            else:
                print(f"⚠️  跳过无效音频片段: {clip}")

        if not valid_clips:
            print(f"❌ 故事 {story_index} 没有有效的音频片段")
            return False

        if len(valid_clips) != len(audio_clips):
            print(f"⚠️  有 {len(audio_clips) - len(valid_clips)} 个无效片段被跳过")

    # 显示将要合并的片段
    print(f"🔗 将合并以下 {len(valid_clips)} 个片段:")
    for i, clip in enumerate(valid_clips, 1):
        filename = os.path.basename(clip)
        file_size = os.path.getsize(clip)
        print(f"     {i:2d}. {filename} ({file_size:,} 字节)")

    # 合并音频片段
    success = merge_audio_clips(valid_clips, output_file)

    if success:
        print(f"✅ 故事 {story_index} 合并完成")
        return True
    else:
        print(f"❌ 故事 {story_index} 合并失败")
        return False


def process_theme(
    theme,
    input_dir=None,
    output_dir=None,
    story_filter=None,
    force_regenerate=False,
    preview=False,
    check_consistency=False,
    chunk_base_dir=None,
    lang="en",
):
    """
    处理单个主题的所有故事

    Args:
        theme (str): 主题名称
        input_dir (str): 自定义输入目录（可选）
        output_dir (str): 自定义输出目录（可选）
        story_filter (str): 只处理指定故事索引（可选）
        force_regenerate (bool): 是否强制重新生成
        preview (bool): 是否预览模式
        check_consistency (bool): 是否检查chunk和mp3数量一致性
        chunk_base_dir (str): chunk文本文件基础目录（当check_consistency=True时需要）
        lang (str): 语言类型，用于书籍音频处理（en/zh）

    Returns:
        dict: 处理结果统计
    """
    print(f"\n🎬 处理主题: {theme.upper()}")

    # 使用默认路径或自定义路径
    theme_input_dir = input_dir or get_input_dir(theme)
    theme_output_dir = output_dir or get_output_dir(theme)

    print(f"📁 输入目录: {theme_input_dir}")
    print(f"📁 输出目录: {theme_output_dir}")

    # 如果启用一致性检查，显示相关信息
    if check_consistency:
        print(f"🔍 一致性检查: 启用")
        print(f"📄 Chunk目录: {chunk_base_dir}")
        print(f"🌐 语言类型: {lang}")
        
        if not chunk_base_dir or not os.path.exists(chunk_base_dir):
            print(f"❌ Chunk目录不存在或未指定: {chunk_base_dir}")
            return {
                "theme": theme,
                "success": False,
                "error": "Chunk目录不存在或未指定",
                "processed": 0,
                "successful": 0,
                "failed": 0,
            }
    else:
        print(f"🔍 一致性检查: 禁用")

    # 检查输入目录是否存在
    if not os.path.exists(theme_input_dir):
        print(f"❌ 主题 {theme} 的输入目录不存在: {theme_input_dir}")
        return {
            "theme": theme,
            "success": False,
            "error": "输入目录不存在",
            "processed": 0,
            "successful": 0,
            "failed": 0,
        }

    # 获取所有故事目录
    story_dirs = get_story_directories(theme_input_dir)

    if not story_dirs:
        print(f"❌ 主题 {theme} 在目录 {theme_input_dir} 中未找到任何故事目录")
        return {
            "theme": theme,
            "success": False,
            "error": "未找到故事目录",
            "processed": 0,
            "successful": 0,
            "failed": 0,
        }

    # 过滤故事（如果指定了特定故事）
    if story_filter:
        original_count = len(story_dirs)
        story_dirs = [
            (story_idx, story_dir)
            for story_idx, story_dir in story_dirs
            if story_idx == story_filter
        ]
        if not story_dirs:
            print(f"❌ 主题 {theme} 中未找到故事 {story_filter}")
            return {
                "theme": theme,
                "success": False,
                "error": f"未找到指定故事 {story_filter}",
                "processed": 0,
                "successful": 0,
                "failed": 0,
            }
        print(f"🔍 已过滤: 从 {original_count} 个故事中选择了故事 {story_filter}")

    print(f"📊 主题 {theme} 找到 {len(story_dirs)} 个故事目录")

    # 扫描已存在的文件（除非强制重新生成）
    existing_stories = set()
    if not force_regenerate:
        existing_stories = scan_existing_merged_files(theme_output_dir)

    # 获取进度统计
    stats = get_progress_stats(story_dirs, existing_stories)

    print(f"📈 主题 {theme} 进度统计:")
    print(f"   总故事数: {stats['total_stories']}")
    print(f"   已完成: {stats['completed_stories']} ({stats['completion_rate']:.1f}%)")
    print(f"   待处理: {stats['remaining_stories']}")

    if preview:
        print(f"📋 主题 {theme} 预览模式 - 将要处理的故事:")
        for i, (story_index, story_dir) in enumerate(stats["pending_stories"], 1):
            output_file = os.path.join(theme_output_dir, story_index, OUTPUT_FILENAME)

            # 统计音频片段数量
            if check_consistency and chunk_base_dir:
                # 使用一致性检查来获取详细信息
                uuid = story_index
                # 使用主题相关的正确路径结构
                if theme:
                    chunk_dir_for_check = get_theme_chunk_dir(theme)
                    mp3_dir_for_check = get_theme_mp3_dir(theme)
                else:
                    chunk_dir_for_check = chunk_base_dir
                    mp3_dir_for_check = get_book_mp3_dir(lang)
                is_consistent, check_result = check_chunk_mp3_consistency(chunk_dir_for_check, mp3_dir_for_check, uuid)
                
                print(f"  {i:3d}. 故事 {story_index}")
                print(f"       输入: {story_dir}")
                print(f"       输出: {output_file}")
                print(f"       Chunk: {check_result['chunk_count']} 个")
                print(f"       MP3: {check_result['mp3_count']} 个")
                if is_consistent:
                    print(f"       状态: ✅ 一致性检查通过，需要合并")
                else:
                    print(f"       状态: ❌ 一致性检查失败，跳过合并")
            else:
                # 原有逻辑
                audio_clips = get_audio_clips(story_dir)
                clip_count = len(
                    [clip for clip in audio_clips if is_valid_audio_file(clip)]
                )

                print(f"  {i:3d}. 故事 {story_index}")
                print(f"       输入: {story_dir} ({clip_count} 个片段)")
                print(f"       输出: {output_file}")
                print(f"       状态: 🆕 需要合并")

        if stats["completed_stories"] > 0:
            print(f"✅ 主题 {theme} 已完成的故事: {stats['completed_stories']} 个")

        return {
            "theme": theme,
            "success": True,
            "preview": True,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "pending": len(stats["pending_stories"]),
            "completed": stats["completed_stories"],
        }

    # 如果没有待处理的故事
    if not stats["pending_stories"]:
        print(f"🎉 主题 {theme} 所有故事都已完成！无需处理。")
        return {
            "theme": theme,
            "success": True,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "already_completed": stats["completed_stories"],
        }

    # 确保输出目录存在
    os.makedirs(theme_output_dir, exist_ok=True)

    print(f"🔄 开始主题 {theme} 的音频合并...")
    print(f"📝 本次将处理 {len(stats['pending_stories'])} 个故事")

    successful_count = 0
    failed_count = 0
    skipped_count = 0  # 新增：跳过的故事数量（一致性检查失败）

    try:
        start_time = time.time()

        for i, (story_index, story_dir) in enumerate(stats["pending_stories"], 1):
            print(
                f"\n[{theme}] 处理第 {i}/{len(stats['pending_stories'])} 个故事: {story_index}"
            )
            print(
                f"总体进度: {stats['completed_stories'] + i}/{stats['total_stories']} ({(stats['completed_stories'] + i)/stats['total_stories']*100:.1f}%)"
            )

            success = process_story(
                story_index, 
                story_dir, 
                theme_output_dir, 
                force_regenerate,
                check_consistency,
                chunk_base_dir,
                lang,
                theme
            )

            if success:
                successful_count += 1
            else:
                # 检查是否是因为一致性检查失败而跳过
                if check_consistency and chunk_base_dir:
                    # 重新检查一致性来确定失败原因
                    uuid = story_index
                    # 对于一致性检查，使用书籍音频的正确路径结构
                    mp3_dir = get_book_mp3_dir(lang)
                    is_consistent, _ = check_chunk_mp3_consistency(chunk_base_dir, mp3_dir, uuid)
                    if not is_consistent:
                        skipped_count += 1
                        print(f"⏭️  故事 {story_index} 因一致性检查失败被跳过")
                    else:
                        failed_count += 1
                else:
                    failed_count += 1

        end_time = time.time()
        total_time = end_time - start_time

        # 统计结果
        print(f"\n=== 🎉 主题 {theme} 处理完成 ===")
        print(f"✅ 本次成功合并: {successful_count} 个故事")
        print(f"❌ 本次合并失败: {failed_count} 个故事")
        if check_consistency and skipped_count > 0:
            print(f"⏭️  一致性检查跳过: {skipped_count} 个故事")
        print(f"⏭️  之前已完成: {stats['completed_stories']} 个故事")
        print(
            f"📊 总体完成: {stats['completed_stories'] + successful_count}/{stats['total_stories']} ({(stats['completed_stories'] + successful_count)/stats['total_stories']*100:.1f}%)"
        )
        print(f"⏱️  本次耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")

        if successful_count > 0:
            avg_time = total_time / successful_count
            print(f"📊 平均每个故事: {avg_time:.1f} 秒")

        return {
            "theme": theme,
            "success": True,
            "processed": successful_count + failed_count,
            "successful": successful_count,
            "failed": failed_count,
            "already_completed": stats["completed_stories"],
            "total_time": total_time,
        }

    except Exception as e:
        print(f"\n❌ 主题 {theme} 处理出错: {e}")
        return {
            "theme": theme,
            "success": False,
            "error": str(e),
            "processed": successful_count + failed_count,
            "successful": successful_count,
            "failed": failed_count,
        }


def main():
    """主函数"""
    # 首先检查是否为Ubuntu系统
    if not check_ubuntu_system():
        print("❌ 此脚本只能在Ubuntu系统上运行！")
        print(f"🖥️  当前系统: {platform.system()}")
        exit(1)

    print("✅ Ubuntu系统检测通过")

    parser = argparse.ArgumentParser(
        description="音频片段合并器 - 将音频片段合并为完整故事（支持多主题和断点续传）"
    )
    parser.add_argument(
        "--theme",
        choices=SUPPORTED_THEMES + ["all"],
        default="all",
        help=f"指定主题 ({', '.join(SUPPORTED_THEMES)}) 或 'all' 处理所有主题 (默认: all)",
    )
    parser.add_argument(
        "--input-dir",
        help=f"自定义输入目录路径 (默认: 根据操作系统和主题自动选择)",
    )
    parser.add_argument(
        "--output-dir",
        help=f"自定义输出目录路径 (默认: 根据操作系统和主题自动选择)",
    )
    parser.add_argument("--story", help="只处理指定故事索引（可选）")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="预览模式，只显示会处理哪些故事，不实际处理",
    )
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="强制重新生成所有文件，忽略已存在的文件",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="断点续传模式，跳过已存在的有效音频文件 (默认: True)",
    )
    parser.add_argument(
        "--check-consistency",
        action="store_true",
        help="启用chunk和mp3文件数量一致性检查（适用于书籍音频合并）",
    )
    parser.add_argument(
        "--chunk-dir",
        help="chunk文本文件基础目录路径（启用一致性检查时需要）",
    )
    parser.add_argument(
        "--lang",
        choices=["en", "zh"],
        default="en",
        help="语言类型，用于书籍音频处理 (默认: en)",
    )

    args = parser.parse_args()

    print(f"🎵 音频片段合并器 (多主题支持 + 断点续传)")
    print(f"🖥️  运行平台: {platform.system()}")
    print(f"📄 输出文件名: {OUTPUT_FILENAME}")

    if args.force_regenerate:
        print(f"🔄 强制重新生成模式: 将重新生成所有文件")
    elif args.resume:
        print(f"⚡ 断点续传模式: 将跳过已存在的有效文件")
    
    if args.check_consistency:
        print(f"🔍 一致性检查: 启用")
        print(f"🌐 语言类型: {args.lang}")
        
        # 如果指定了特定主题，使用主题路径；否则使用传统的书籍路径
        if args.theme != "all":
            # 单一主题模式：使用主题路径
            chunk_dir = args.chunk_dir or get_theme_chunk_dir(args.theme)
            mp3_dir = get_theme_mp3_dir(args.theme)
            print(f"📄 主题Chunk目录: {chunk_dir}")
            print(f"🎵 主题MP3目录: {mp3_dir}")
        else:
            # 多主题模式：使用书籍路径（向后兼容）
            chunk_dir = args.chunk_dir or get_book_chunk_dir(args.lang)
            mp3_dir = get_book_mp3_dir(args.lang)
            print(f"📄 Chunk目录: {chunk_dir}")
            print(f"🎵 MP3目录: {mp3_dir}")
        
        # 检查基础目录是否存在
        if not os.path.exists(chunk_dir):
            print(f"❌ Chunk目录不存在: {chunk_dir}")
            if args.theme != "all":
                print(f"💡 请检查主题 {args.theme} 的chunk文件是否已生成")
            else:
                print(f"💡 请先运行 chunk_book_summaries.py 生成chunk文件")
            return
            
        if not os.path.exists(mp3_dir):
            print(f"❌ MP3目录不存在: {mp3_dir}")
            if args.theme != "all":
                print(f"💡 请检查主题 {args.theme} 的mp3文件是否已生成")
            else:
                print(f"💡 请先运行 synthesize_book_audio.py --lang {args.lang} 生成音频文件")
            return
            
        print(f"✅ 一致性检查目录验证通过")
    else:
        print(f"🔍 一致性检查: 禁用")
        chunk_dir = None

    # 检查 ffmpeg 是否可用
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print(f"✅ ffmpeg 可用")
    except:
        print(f"❌ ffmpeg 不可用，请确保已安装 ffmpeg")
        return

    # 确定要处理的主题
    if args.theme == "all":
        themes_to_process = SUPPORTED_THEMES
        print(f"🎬 将处理所有主题: {', '.join(themes_to_process)}")
    else:
        themes_to_process = [args.theme]
        print(f"🎬 将处理主题: {args.theme}")

    # 处理每个主题
    all_results = []
    total_start_time = time.time()

    try:
        for theme_index, theme in enumerate(themes_to_process, 1):
            print(f"\n{'='*60}")
            print(
                f"🎬 处理第 {theme_index}/{len(themes_to_process)} 个主题: {theme.upper()}"
            )
            print(f"{'='*60}")

            result = process_theme(
                theme=theme,
                input_dir=args.input_dir,
                output_dir=args.output_dir,
                story_filter=args.story,
                force_regenerate=args.force_regenerate,
                preview=args.preview,
                check_consistency=args.check_consistency,
                chunk_base_dir=chunk_dir,
                lang=args.lang,
            )

            all_results.append(result)

            # 如果是预览模式，跳过后续处理
            if args.preview:
                continue

            # 如果主题处理失败，询问是否继续
            if not result["success"] and len(themes_to_process) > 1:
                print(f"\n⚠️  主题 {theme} 处理失败: {result.get('error', '未知错误')}")
                if theme_index < len(themes_to_process):
                    print(f"🔄 继续处理下一个主题...")

        total_end_time = time.time()
        total_time = total_end_time - total_start_time

        # 汇总结果
        print(f"\n{'='*60}")
        print(f"🎉 所有主题处理完成")
        print(f"{'='*60}")

        if args.preview:
            print(f"📋 预览模式结果:")
            for result in all_results:
                if result["success"]:
                    pending = result.get("pending", 0)
                    completed = result.get("completed", 0)
                    print(
                        f"   {result['theme']:10s}: {completed:3d} 已完成, {pending:3d} 待处理"
                    )
                else:
                    print(
                        f"   {result['theme']:10s}: ❌ 错误 - {result.get('error', '未知')}"
                    )
        else:
            # 统计所有主题的结果
            total_processed = sum(r.get("processed", 0) for r in all_results)
            total_successful = sum(r.get("successful", 0) for r in all_results)
            total_failed = sum(r.get("failed", 0) for r in all_results)
            total_already_completed = sum(
                r.get("already_completed", 0) for r in all_results
            )
            successful_themes = len([r for r in all_results if r["success"]])
            failed_themes = len([r for r in all_results if not r["success"]])

            print(f"📊 总体统计:")
            print(f"   成功主题: {successful_themes}/{len(themes_to_process)}")
            print(f"   失败主题: {failed_themes}")
            print(f"   本次处理: {total_processed} 个故事")
            print(f"   本次成功: {total_successful} 个故事")
            print(f"   本次失败: {total_failed} 个故事")
            print(f"   之前完成: {total_already_completed} 个故事")
            print(f"   总计耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")

            if total_successful > 0:
                avg_time = total_time / total_successful
                print(f"   平均每个故事: {avg_time:.1f} 秒")

            # 显示每个主题的详细结果
            print(f"\n📝 各主题详细结果:")
            for result in all_results:
                if result["success"]:
                    if result.get("processed", 0) > 0:
                        print(
                            f"   {result['theme']:10s}: ✅ {result['successful']:3d} 成功, {result['failed']:2d} 失败"
                        )
                    else:
                        completed = result.get("already_completed", 0)
                        print(
                            f"   {result['theme']:10s}: ⏭️  {completed} 个故事已完成，无需处理"
                        )
                else:
                    print(
                        f"   {result['theme']:10s}: ❌ 错误 - {result.get('error', '未知')}"
                    )

    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断了程序执行")
        print(f"✅ 已处理的主题: {len([r for r in all_results if r.get('success')])}")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")


if __name__ == "__main__":
    main()
