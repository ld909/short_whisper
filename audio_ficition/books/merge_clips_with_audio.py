#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍视频音频合并脚本
将 generate_book_clips.py 输出的MP4 clip与 merge_book_audio.py 输出的音频合并
并提取第一帧作为YouTube封面图片

📚 功能说明:
- 读取 generate_book_clips.py 输出的 1080p MP4 clip文件
- 读取 merge_book_audio.py 输出的完整音频文件
- 将 MP4 clip 快速 loop 合并为稍长于对应音频的视频
- 将音频合入到新的 MP4 中
- 提取 MP4 clip 的第一帧作为 YouTube 封面图片
- 支持断点续传，跳过已存在的有效文件
- 自动排除Mac系统产生的点文件
- 支持中文(zh)和英文(en)两种语言主题

📥 输入信息:
- MP4 Clip目录: /Volumes/dhl/audio/books/{language}/1080_clips/{uuid}.mp4
- 音频文件目录: /Volumes/dhl/audio/books/{language}/mp3/{uuid}.mp3

📤 输出信息:
- 合并视频: /Volumes/dhl/audio/books/{language}/mp4_with_audio/{uuid}.mp4
- YouTube封面: /Volumes/dhl/audio/books/{language}/ytb_cover/{uuid}.png (1280x720像素)

🔄 处理规则:
1. 在macOS系统上运行（适配Intel和Apple Silicon）
2. 支持断点续传，跳过已存在的有效文件
3. 自动排除以点开头的Mac系统文件
4. 使用concat方式拼接多个clip副本，不使用静态图循环
5. 参考 merge_mp4_cover_audio.py 的优化技术
6. YouTube封面使用标准尺寸 1280x720 (16:9比例)

💡 使用示例:
# 处理英文书籍
python merge_clips_with_audio.py --lang en

# 处理中文书籍
python merge_clips_with_audio.py --lang zh

# 处理指定UUID的书籍
python merge_clips_with_audio.py --uuid 12345678-abcd-efgh-ijkl-123456789012 --lang en

# 预览模式
python merge_clips_with_audio.py --preview --lang zh

# 强制重新生成
python merge_clips_with_audio.py --force --lang en
"""

import os
import sys
import glob
import json
import argparse
import subprocess
import time
import platform
import shutil
import math
from pathlib import Path
from tqdm import tqdm
from typing import Optional, Dict, List, Tuple

# ============ 配置参数 ============
# YouTube 封面标准尺寸 (16:9 比例)
YOUTUBE_COVER_WIDTH = 1280
YOUTUBE_COVER_HEIGHT = 720

# 最小文件大小检查 (字节)
MIN_CLIP_SIZE = 1024 * 1024  # 1MB
MIN_AUDIO_SIZE = 1024 * 100  # 100KB
MIN_OUTPUT_SIZE = 1024 * 1024 * 5  # 5MB
MIN_COVER_SIZE = 1024 * 10  # 10KB

# 额外视频长度 (秒)，确保视频略长于音频
EXTRA_VIDEO_DURATION = 1.0

# 临时目录
DEFAULT_TEMP_DIR = "/tmp/book_clip_audio_merge"


# macOS 路径配置
def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/audio"
    else:  # 默认为Linux/Ubuntu
        return "/mnt/dhl/audio"


def get_directories(language="en"):
    """获取所有相关目录路径"""
    base_media_path = get_base_media_path()
    books_path = os.path.join(base_media_path, "books", language)

    return {
        "clips": os.path.join(books_path, "1080_clips"),
        "audio": os.path.join(books_path, "mp3"),
        "output": os.path.join(books_path, "mp4_with_audio"),
        "covers": os.path.join(books_path, "ytb_cover"),
        "temp": DEFAULT_TEMP_DIR,
    }


# ===================================


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


def get_available_books(directories: Dict) -> List[Tuple[str, str, str]]:
    """
    获取所有可用的书籍文件（同时有clip和audio的书籍）
    排除Mac生成的点文件

    Args:
        directories: 目录配置字典

    Returns:
        list: [(uuid, clip_path, audio_path)] 格式的书籍列表
    """
    clips_dir = directories["clips"]
    audio_dir = directories["audio"]

    if not os.path.exists(clips_dir):
        print(f"❌ Clips目录不存在: {clips_dir}")
        return []

    if not os.path.exists(audio_dir):
        print(f"❌ 音频目录不存在: {audio_dir}")
        return []

    # 获取所有clip文件
    clip_files = glob.glob(os.path.join(clips_dir, "*.mp4"))
    clip_uuids = {}
    skipped_clips = []

    for clip_file in clip_files:
        basename = os.path.basename(clip_file)

        # 跳过点开头的文件
        if basename.startswith(".") or basename.startswith("._"):
            skipped_clips.append(basename)
            continue

        # 提取UUID
        if basename.endswith(".mp4"):
            uuid = basename[:-4]  # 移除 .mp4 扩展名
            if len(uuid) == 36 and uuid.count("-") == 4:  # 简单UUID格式验证
                clip_uuids[uuid] = clip_file
            else:
                skipped_clips.append(basename)

    if skipped_clips:
        print(
            f"🚫 跳过 {len(skipped_clips)} 个Mac系统clip文件: {', '.join(skipped_clips[:5])}{'...' if len(skipped_clips) > 5 else ''}"
        )

    # 获取所有音频文件
    audio_files = glob.glob(os.path.join(audio_dir, "*.mp3"))
    audio_uuids = {}
    skipped_audio = []

    for audio_file in audio_files:
        basename = os.path.basename(audio_file)

        # 跳过点开头的文件
        if basename.startswith(".") or basename.startswith("._"):
            skipped_audio.append(basename)
            continue

        # 提取UUID
        if basename.endswith(".mp3"):
            uuid = basename[:-4]  # 移除 .mp3 扩展名
            if len(uuid) == 36 and uuid.count("-") == 4:  # 简单UUID格式验证
                audio_uuids[uuid] = audio_file
            else:
                skipped_audio.append(basename)

    if skipped_audio:
        print(
            f"🚫 跳过 {len(skipped_audio)} 个Mac系统音频文件: {', '.join(skipped_audio[:5])}{'...' if len(skipped_audio) > 5 else ''}"
        )

    # 找到同时有clip和audio的书籍
    common_uuids = set(clip_uuids.keys()) & set(audio_uuids.keys())
    available_books = []

    for uuid in sorted(common_uuids):
        clip_path = clip_uuids[uuid]
        audio_path = audio_uuids[uuid]

        # 验证文件有效性
        if is_valid_file(clip_path, MIN_CLIP_SIZE) and is_valid_file(
            audio_path, MIN_AUDIO_SIZE
        ):
            available_books.append((uuid, clip_path, audio_path))

    print(f"📊 统计信息:")
    print(f"   - 找到clip文件: {len(clip_uuids)} 个")
    print(f"   - 找到音频文件: {len(audio_uuids)} 个")
    print(f"   - 同时包含两者的书籍: {len(available_books)} 个")

    return available_books


def get_audio_duration(audio_file: str) -> Optional[float]:
    """
    获取音频文件时长（秒）

    Args:
        audio_file: 音频文件路径

    Returns:
        float: 音频时长（秒），失败时返回None
    """
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            audio_file,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)

        duration = float(info["format"]["duration"])
        return duration
    except Exception as e:
        print(f"❌ 获取音频时长失败: {os.path.basename(audio_file)}, 错误: {e}")
        return None


def get_video_duration(video_file: str) -> Optional[float]:
    """
    获取视频文件时长（秒）

    Args:
        video_file: 视频文件路径

    Returns:
        float: 视频时长（秒），失败时返回None
    """
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            video_file,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)

        duration = float(info["format"]["duration"])
        return duration
    except Exception as e:
        print(f"❌ 获取视频时长失败: {os.path.basename(video_file)}, 错误: {e}")
        return None


def get_optimal_encoder_settings():
    """
    获取最优的编码器设置（参考 merge_mp4_cover_audio.py）
    """
    system = platform.system()

    # 检测可用的硬件编码器
    encoders_to_test = []

    if system == "Darwin":  # macOS
        encoders_to_test = [
            ("h264_videotoolbox", "veryfast"),  # Apple硬件编码，苹果系统优先
            ("libx264", "ultrafast"),  # 软件编码备选
        ]
    else:  # Linux/Ubuntu
        encoders_to_test = [
            ("h264_nvenc", "fast"),  # NVIDIA GPU
            ("h264_qsv", "fast"),  # Intel GPU
            ("h264_amf", "fast"),  # AMD GPU
            ("libx264", "ultrafast"),  # 软件编码
        ]

    # 测试编码器可用性
    for encoder, preset in encoders_to_test:
        try:
            # 简单测试编码器是否可用
            test_cmd = [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                "testsrc=duration=0.1:size=32x32:rate=1",
                "-c:v",
                encoder,
                "-preset",
                preset,
                "-f",
                "null",
                "-",
            ]
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return encoder, preset
        except:
            continue

    # 默认回退
    return "libx264", "ultrafast"


def create_looped_video_with_audio(
    uuid: str,
    clip_path: str,
    audio_path: str,
    output_path: str,
    temp_dir: str,
    debug: bool = False,
) -> bool:
    """
    通过拼接多个clip片段创建长视频并合并音频（参考 merge_mp4_cover_audio.py 的快速合成方法）

    Args:
        uuid: 书籍UUID
        clip_path: 源clip路径
        audio_path: 音频文件路径
        output_path: 输出视频路径
        temp_dir: 临时目录
        debug: 是否启用调试模式

    Returns:
        bool: 处理是否成功
    """
    print(f"🎬 [UUID:{uuid[:8]}...] 开始创建拼接视频...")

    # 获取音频和视频时长
    audio_duration = get_audio_duration(audio_path)
    if audio_duration is None:
        print(f"❌ [UUID:{uuid[:8]}...] 无法获取音频时长")
        return False

    video_duration = get_video_duration(clip_path)
    if video_duration is None:
        print(f"❌ [UUID:{uuid[:8]}...] 无法获取视频时长")
        return False

    # 计算需要的总视频时长（比音频稍长）
    target_duration = audio_duration + EXTRA_VIDEO_DURATION

    # 计算需要拼接的clip数量
    repeat_count = math.ceil(target_duration / video_duration)

    if debug:
        print(f"🎯 [UUID:{uuid[:8]}...] 时长计算:")
        print(f"   - 音频时长: {audio_duration:.2f}秒")
        print(f"   - Clip时长: {video_duration:.2f}秒")
        print(f"   - 目标时长: {target_duration:.2f}秒")
        print(f"   - 需要拼接: {repeat_count} 个clip")

    try:
        # 确保目录存在
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 获取最优编码器设置
        encoder, preset = get_optimal_encoder_settings()

        if debug:
            print(f"🚀 [UUID:{uuid[:8]}...] 使用编码器: {encoder}, 预设: {preset}")

        # 创建临时文件列表供ffmpeg concat使用
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as temp_file:
            # 写入重复的clip文件路径
            for i in range(repeat_count):
                temp_file.write(f"file '{clip_path}'\n")
            temp_list_file = temp_file.name

        if debug:
            print(f"📝 [UUID:{uuid[:8]}...] 临时文件列表: {temp_list_file}")
            print(f"   - 包含 {repeat_count} 个重复的clip引用")

        # 第一步：使用concat方式拼接多个clip
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
            temp_video_file = temp_video.name

        print(f"🔗 [UUID:{uuid[:8]}...] 第一步：拼接 {repeat_count} 个clip副本...")

        concat_cmd = [
            "ffmpeg",
            "-y",  # 覆盖输出文件
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            temp_list_file,
            "-c",
            "copy",  # 快速复制，不重编码
            temp_video_file,
        ]

        if debug:
            print(f"🔧 [UUID:{uuid[:8]}...] 拼接命令: {' '.join(concat_cmd)}")

        start_time = time.time()
        result = subprocess.run(concat_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ [UUID:{uuid[:8]}...] 视频拼接失败: {result.stderr}")
            return False

        concat_time = time.time() - start_time
        if debug:
            print(f"⚡ [UUID:{uuid[:8]}...] 拼接用时: {concat_time:.2f} 秒")

        # 第二步：合并音频并截断到目标时长
        print(f"🎵 [UUID:{uuid[:8]}...] 第二步：合并音频并截断到目标时长...")

        final_cmd = [
            "ffmpeg",
            "-y",  # 覆盖输出文件
            "-i",
            temp_video_file,  # 输入拼接后的视频
            "-i",
            audio_path,  # 输入音频
            "-map",
            "0:v",  # 映射视频流
            "-map",
            "1:a",  # 映射音频流
            "-c:v",
            encoder,  # 视频编码器
            "-preset",
            preset,  # 编码预设
            "-c:a",
            "aac",  # 音频编码器
            "-b:a",
            "192k",  # 音频比特率
            "-t",
            str(target_duration),  # 限制输出时长
            "-pix_fmt",
            "yuv420p",  # 像素格式
            "-movflags",
            "+faststart",  # 优化网络播放
            "-threads",
            "0",  # 使用所有可用线程
            output_path,
        ]

        if debug:
            print(f"🔧 [UUID:{uuid[:8]}...] 最终合并命令: {' '.join(final_cmd)}")

        # 执行最终合并命令
        result = subprocess.run(final_cmd, capture_output=True, text=True)
        total_time = time.time() - start_time

        # 清理临时文件
        try:
            os.unlink(temp_list_file)
            os.unlink(temp_video_file)
        except Exception:
            pass

        if result.returncode == 0:
            print(
                f"✅ [UUID:{uuid[:8]}...] 视频合成成功: {os.path.basename(output_path)}"
            )

            # 验证输出文件
            if is_valid_file(output_path, MIN_OUTPUT_SIZE):
                file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
                print(f"📊 [UUID:{uuid[:8]}...] 输出文件大小: {file_size:.2f} MB")
                print(f"⚡ [UUID:{uuid[:8]}...] 总处理时间: {total_time:.2f} 秒")
                return True
            else:
                print(f"❌ [UUID:{uuid[:8]}...] 输出文件无效或过小")
                return False
        else:
            print(f"❌ [UUID:{uuid[:8]}...] 最终合并失败:")
            if debug:
                print(f"   stdout: {result.stdout}")
                print(f"   stderr: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ [UUID:{uuid[:8]}...] 创建拼接视频失败: {e}")
        return False


def extract_youtube_cover(
    uuid: str, clip_path: str, cover_path: str, debug: bool = False
) -> bool:
    """
    从clip视频中提取第一帧作为YouTube封面

    Args:
        uuid: 书籍UUID
        clip_path: 源clip路径
        cover_path: 封面输出路径
        debug: 是否启用调试模式

    Returns:
        bool: 提取是否成功
    """
    print(f"🖼️  [UUID:{uuid[:8]}...] 提取YouTube封面...")

    try:
        # 确保输出目录存在
        os.makedirs(os.path.dirname(cover_path), exist_ok=True)

        # 构建FFmpeg命令提取第一帧并调整为YouTube标准尺寸
        cmd = [
            "ffmpeg",
            "-y",  # 覆盖输出文件
            "-i",
            clip_path,  # 输入视频
            "-vf",
            f"scale={YOUTUBE_COVER_WIDTH}:{YOUTUBE_COVER_HEIGHT}:force_original_aspect_ratio=decrease,pad={YOUTUBE_COVER_WIDTH}:{YOUTUBE_COVER_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black",  # 缩放并填充黑边保持比例
            "-frames:v",
            "1",  # 只提取第一帧
            "-q:v",
            "2",  # 高质量
            cover_path,
        ]

        if debug:
            print(f"🔧 [UUID:{uuid[:8]}...] 封面提取命令: {' '.join(cmd)}")

        # 执行FFmpeg命令
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(
                f"✅ [UUID:{uuid[:8]}...] YouTube封面提取成功: {os.path.basename(cover_path)}"
            )

            # 验证输出文件
            if is_valid_file(cover_path, MIN_COVER_SIZE):
                file_size = os.path.getsize(cover_path)
                print(
                    f"📊 [UUID:{uuid[:8]}...] 封面大小: {YOUTUBE_COVER_WIDTH}x{YOUTUBE_COVER_HEIGHT}, 文件大小: {file_size} 字节"
                )
                return True
            else:
                print(f"❌ [UUID:{uuid[:8]}...] 封面文件无效或过小")
                return False
        else:
            print(f"❌ [UUID:{uuid[:8]}...] 封面提取失败:")
            if debug:
                print(f"   stdout: {result.stdout}")
                print(f"   stderr: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ [UUID:{uuid[:8]}...] 提取YouTube封面失败: {e}")
        return False


def get_existing_outputs(directories: Dict) -> Tuple[set, set]:
    """
    获取已存在的输出文件UUID集合

    Args:
        directories: 目录配置字典

    Returns:
        tuple: (视频UUID集合, 封面UUID集合)
    """
    video_uuids = set()
    cover_uuids = set()

    # 检查视频文件
    output_dir = directories["output"]
    if os.path.exists(output_dir):
        video_files = glob.glob(os.path.join(output_dir, "*.mp4"))
        for video_file in video_files:
            basename = os.path.basename(video_file)
            if not basename.startswith(".") and basename.endswith(".mp4"):
                uuid = basename[:-4]
                if len(uuid) == 36 and uuid.count("-") == 4:
                    if is_valid_file(video_file, MIN_OUTPUT_SIZE):
                        video_uuids.add(uuid)

    # 检查封面文件
    covers_dir = directories["covers"]
    if os.path.exists(covers_dir):
        cover_files = glob.glob(os.path.join(covers_dir, "*.png"))
        for cover_file in cover_files:
            basename = os.path.basename(cover_file)
            if not basename.startswith(".") and basename.endswith(".png"):
                uuid = basename[:-4]
                if len(uuid) == 36 and uuid.count("-") == 4:
                    if is_valid_file(cover_file, MIN_COVER_SIZE):
                        cover_uuids.add(uuid)

    return video_uuids, cover_uuids


def process_single_book(
    uuid: str,
    clip_path: str,
    audio_path: str,
    directories: Dict,
    force: bool = False,
    preview: bool = False,
    debug: bool = False,
) -> Dict:
    """
    处理单个书籍的视频音频合并

    Args:
        uuid: 书籍UUID
        clip_path: clip文件路径
        audio_path: 音频文件路径
        directories: 目录配置
        force: 是否强制重新处理
        preview: 是否为预览模式
        debug: 是否启用调试模式

    Returns:
        dict: 处理结果
    """
    print(f"\n=== 📚 处理书籍 UUID: {uuid[:8]}...{uuid[-8:]} ===")

    # 生成输出路径
    output_path = os.path.join(directories["output"], f"{uuid}.mp4")
    cover_path = os.path.join(directories["covers"], f"{uuid}.png")

    print(f"📁 Clip文件: {os.path.basename(clip_path)}")
    print(f"📁 音频文件: {os.path.basename(audio_path)}")
    print(f"📁 输出视频: {os.path.basename(output_path)}")
    print(f"📁 YouTube封面: {os.path.basename(cover_path)}")

    # 检查是否需要跳过（除非强制处理）
    video_exists = is_valid_file(output_path, MIN_OUTPUT_SIZE)
    cover_exists = is_valid_file(cover_path, MIN_COVER_SIZE)

    if not force and video_exists and cover_exists:
        print(f"⏭️  [UUID:{uuid[:8]}...] 文件已存在且有效，跳过处理")
        return {
            "uuid": uuid,
            "status": "skipped",
            "reason": "already_exists",
            "video_path": output_path,
            "cover_path": cover_path,
        }

    # 预览模式
    if preview:
        audio_duration = get_audio_duration(audio_path)
        video_duration = get_video_duration(clip_path)

        print(f"📋 [UUID:{uuid[:8]}...] 预览模式:")
        print(
            f"   - 音频时长: {audio_duration:.2f}秒"
            if audio_duration
            else "   - 音频时长: 无法获取"
        )
        print(
            f"   - 视频时长: {video_duration:.2f}秒"
            if video_duration
            else "   - 视频时长: 无法获取"
        )
        print(f"   - 需要生成视频: {'是' if not video_exists or force else '否'}")
        print(f"   - 需要生成封面: {'是' if not cover_exists or force else '否'}")

        return {
            "uuid": uuid,
            "status": "preview",
            "needs_video": not video_exists or force,
            "needs_cover": not cover_exists or force,
            "audio_duration": audio_duration,
            "video_duration": video_duration,
        }

    # 实际处理
    results = {
        "uuid": uuid,
        "status": "in_progress",
        "video_success": False,
        "cover_success": False,
    }

    # 处理视频合成
    if force or not video_exists:
        print(f"🎬 [UUID:{uuid[:8]}...] 开始视频音频合并...")
        video_success = create_looped_video_with_audio(
            uuid, clip_path, audio_path, output_path, directories["temp"], debug
        )
        results["video_success"] = video_success

        if not video_success:
            results["status"] = "failed"
            results["error"] = "video_creation_failed"
            return results
    else:
        print(f"⏭️  [UUID:{uuid[:8]}...] 视频文件已存在，跳过")
        results["video_success"] = True

    # 处理封面提取
    if force or not cover_exists:
        print(f"🖼️  [UUID:{uuid[:8]}...] 开始提取YouTube封面...")
        cover_success = extract_youtube_cover(uuid, clip_path, cover_path, debug)
        results["cover_success"] = cover_success

        if not cover_success:
            results["status"] = (
                "partial_success" if results["video_success"] else "failed"
            )
            results["error"] = "cover_extraction_failed"
            return results
    else:
        print(f"⏭️  [UUID:{uuid[:8]}...] 封面文件已存在，跳过")
        results["cover_success"] = True

    # 最终状态
    if results["video_success"] and results["cover_success"]:
        results["status"] = "success"
        results["video_path"] = output_path
        results["cover_path"] = cover_path
        print(f"🎉 [UUID:{uuid[:8]}...] 处理完成!")
    else:
        results["status"] = "partial_success"

    return results


def check_dependencies():
    """检查必要的依赖是否安装"""
    dependencies = ["ffmpeg", "ffprobe"]
    missing = []

    for dep in dependencies:
        if not shutil.which(dep):
            missing.append(dep)

    if missing:
        print(f"❌ 缺少依赖: {', '.join(missing)}")
        print("请安装 FFmpeg:")
        print("macOS: brew install ffmpeg")
        print("Ubuntu: sudo apt install ffmpeg")
        return False

    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="📚 书籍视频音频合并器",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python merge_clips_with_audio.py --lang en                      # 处理英文书籍
  python merge_clips_with_audio.py --lang zh                      # 处理中文书籍
  python merge_clips_with_audio.py --uuid abc123 --lang en        # 处理指定UUID
  python merge_clips_with_audio.py --preview --lang zh            # 预览模式
  python merge_clips_with_audio.py --force --lang en              # 强制重新生成

注意:
- 需要FFmpeg支持
- 会生成合并视频和YouTube封面图片
- 自动排除Mac系统文件
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

    parser.add_argument("--uuid", help="只处理指定UUID的书籍")
    parser.add_argument(
        "--force", "-f", action="store_true", help="强制重新生成所有文件"
    )
    parser.add_argument(
        "--preview", "-p", action="store_true", help="预览模式，只显示要处理的文件"
    )
    parser.add_argument("--debug", "-d", action="store_true", help="启用调试模式")

    args = parser.parse_args()

    print("📚 书籍视频音频合并器")
    print("=" * 50)

    # 检查系统
    if not check_macos_system():
        print("⚠️  警告: 此脚本主要为macOS设计，在其他系统上可能需要调整路径")

    # 检查依赖
    if not check_dependencies():
        print("❌ 依赖检查失败，退出")
        sys.exit(1)

    language = args.lang
    lang_name = "中文" if language == "zh" else "English"

    print(f"🌍 语言主题: {lang_name}")

    # 获取目录配置
    directories = get_directories(language)

    print(f"📁 Clips目录: {directories['clips']}")
    print(f"📁 音频目录: {directories['audio']}")
    print(f"📁 输出目录: {directories['output']}")
    print(f"📁 封面目录: {directories['covers']}")

    # 确保输出目录存在
    os.makedirs(directories["output"], exist_ok=True)
    os.makedirs(directories["covers"], exist_ok=True)
    os.makedirs(directories["temp"], exist_ok=True)

    # 获取可用的书籍
    if args.uuid:
        # 处理单个UUID
        print(f"🎯 目标UUID: {args.uuid}")

        clip_path = os.path.join(directories["clips"], f"{args.uuid}.mp4")
        audio_path = os.path.join(directories["audio"], f"{args.uuid}.mp3")

        if not os.path.exists(clip_path):
            print(f"❌ Clip文件不存在: {clip_path}")
            sys.exit(1)

        if not os.path.exists(audio_path):
            print(f"❌ 音频文件不存在: {audio_path}")
            sys.exit(1)

        available_books = [(args.uuid, clip_path, audio_path)]
    else:
        # 处理所有可用书籍
        available_books = get_available_books(directories)

    if not available_books:
        print("❌ 未找到可处理的书籍文件")
        sys.exit(1)

    print(f"📊 统计信息:")
    print(f"   - 找到书籍: {len(available_books)} 个")

    # 预览模式
    if args.preview:
        print(f"\n📋 预览模式 - 将要处理的书籍:")
        for i, (uuid, clip_path, audio_path) in enumerate(available_books, 1):
            output_path = os.path.join(directories["output"], f"{uuid}.mp4")
            cover_path = os.path.join(directories["covers"], f"{uuid}.png")

            clip_size = os.path.getsize(clip_path) if os.path.exists(clip_path) else 0
            audio_size = (
                os.path.getsize(audio_path) if os.path.exists(audio_path) else 0
            )

            print(f"  {i:2d}. UUID: {uuid}")
            print(f"      Clip: {os.path.basename(clip_path)} ({clip_size:,} 字节)")
            print(f"      音频: {os.path.basename(audio_path)} ({audio_size:,} 字节)")
            print(f"      输出视频: {os.path.basename(output_path)}")
            print(f"      封面图片: {os.path.basename(cover_path)}")
        return

    # 处理书籍
    print(f"\n🔄 开始处理 {len(available_books)} 个书籍...")

    success_count = 0
    failed_count = 0
    skipped_count = 0

    try:
        for i, (uuid, clip_path, audio_path) in enumerate(available_books, 1):
            print(f"\n{'='*60}")
            print(f"处理第 {i}/{len(available_books)} 个书籍: {uuid}")
            print(f"{'='*60}")

            result = process_single_book(
                uuid=uuid,
                clip_path=clip_path,
                audio_path=audio_path,
                directories=directories,
                force=args.force,
                preview=False,
                debug=args.debug,
            )

            if result["success"]:
                success_count += 1
                print(f"✅ 成功处理: {uuid}")
            elif result.get("skipped"):
                skipped_count += 1
                print(f"⏭️  跳过已存在: {uuid}")
            else:
                failed_count += 1
                print(f"❌ 处理失败: {uuid}")

    except KeyboardInterrupt:
        print("\n⏹️ 用户中断，正在清理...")
    finally:
        # 清理临时目录
        if os.path.exists(directories["temp"]):
            try:
                shutil.rmtree(directories["temp"])
                print(f"🧹 已清理临时目录: {directories['temp']}")
            except Exception as e:
                print(f"⚠️  清理临时目录失败: {e}")

    # 最终统计
    print(f"\n📊 处理完成统计:")
    print(f"  ✅ 成功: {success_count} 个")
    print(f"  ❌ 失败: {failed_count} 个")
    print(f"  ⏭️  跳过: {skipped_count} 个")
    print(
        f"  📈 成功率: {success_count/(success_count+failed_count)*100:.1f}%"
        if (success_count + failed_count) > 0
        else "N/A"
    )

    if success_count > 0:
        print(f"\n📁 输出文件已保存到:")
        print(f"  🎬 合并视频: {directories['output']}")
        print(f"  🖼️ YouTube封面: {directories['covers']}")


if __name__ == "__main__":
    main()
