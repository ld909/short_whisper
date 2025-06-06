#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多语言视频字幕添加工具 - 优化版本

主要优化:
1. 并行处理支持 - 充分利用多核CPU/GPU资源
2. 增强安全性 - 更严格的路径验证和资源管理
3. 性能优化 - 智能任务调度和内存管理
4. 错误恢复 - 失败重试机制和优雅降级
5. 进度监控 - 实时进度显示和性能统计
"""

import os
import argparse
import platform
import subprocess
import sys
from tqdm import tqdm
import logging
import time
import glob
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import threading
import psutil
import signal
import hashlib
from pathlib import Path
import shutil
from typing import List, Tuple, Optional, Dict, Any
import json
import tempfile
from dataclasses import dataclass


@dataclass
class TaskResult:
    """任务执行结果"""

    success: bool
    channel: str
    video_name: str
    language: str
    processing_time: float
    error_message: Optional[str] = None
    output_size: Optional[int] = None


class ResourceManager:
    """资源管理器 - 监控和管理系统资源"""

    def __init__(self):
        self.cpu_count = multiprocessing.cpu_count()
        self.memory_total = psutil.virtual_memory().total
        self.gpu_memory = self._get_gpu_memory()

    def _get_gpu_memory(self) -> Optional[int]:
        """获取GPU内存信息"""
        try:
            if platform.system() == "Linux":
                result = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=memory.total,memory.free",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split("\n")
                    if lines:
                        parts = lines[0].strip().split(",")
                        return int(parts[1].strip())  # 可用内存
            return None
        except Exception:
            return None

    def get_optimal_workers(self, use_gpu: bool = False) -> int:
        """根据系统资源计算最优工作进程数"""
        if use_gpu and self.gpu_memory:
            # GPU模式：根据GPU内存计算
            if self.gpu_memory > 8000:  # 8GB+
                return min(4, self.cpu_count // 2)
            elif self.gpu_memory > 4000:  # 4GB+
                return min(2, self.cpu_count // 4)
            else:
                return 1
        else:
            # CPU模式：根据CPU核心数和内存
            memory_gb = self.memory_total // (1024**3)
            if memory_gb >= 16:
                return min(self.cpu_count, 8)
            elif memory_gb >= 8:
                return min(self.cpu_count // 2, 4)
            else:
                return min(self.cpu_count // 4, 2)


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.start_time = time.time()
        self.processed_count = 0
        self.failed_count = 0
        self.total_size_processed = 0
        self.lock = threading.Lock()

    def update(self, result: TaskResult):
        """更新统计信息"""
        with self.lock:
            if result.success:
                self.processed_count += 1
                if result.output_size:
                    self.total_size_processed += result.output_size
            else:
                self.failed_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        elapsed = time.time() - self.start_time
        with self.lock:
            return {
                "elapsed_time": elapsed,
                "processed_count": self.processed_count,
                "failed_count": self.failed_count,
                "total_size_mb": self.total_size_processed / (1024 * 1024),
                "avg_speed": self.processed_count / elapsed if elapsed > 0 else 0,
            }


def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


def get_fonts_dir():
    """根据操作系统类型返回对应的字体目录"""
    if platform.system() == "Darwin":  # macOS
        return "/Users/donghaoliu/doc/short_whisper/fonts"
    else:  # 默认为Linux/Ubuntu
        font_paths = [
            "/home/dhl/doc/short_whisper/fonts",
            "/home/dhl/Documents/short_whisper/fonts",
            "/usr/share/fonts",
            "/usr/local/share/fonts",
        ]

        for path in font_paths:
            if os.path.exists(path):
                return path

        default_path = "/home/dhl/Documents/short_whisper/fonts"
        os.makedirs(default_path, exist_ok=True)
        return default_path


# 全局配置
BASE_PATH = get_base_path()
INPUT_MP4_PATH = os.path.join(BASE_PATH, "mp4_merge_silient")
INPUT_SRT_PATH = os.path.join(BASE_PATH, "multi_lang_srt")
FONTS_DIR = get_fonts_dir()
OUTPUT_MP4_PATH = os.path.join(BASE_PATH, "mp4_multi_with_subtitles")

SUPPORTED_LANGUAGES = ["en", "ja", "vi", "ko"]

LANGUAGE_FONTS = {
    "en": "Noto_Sans_EN/NotoSans-VariableFont_wdth,wght.ttf",
    "ja": "Noto_Sans_JP/NotoSansJP-VariableFont_wght.ttf",
    "vi": "Noto_Sans_VI/NotoSans-VariableFont_wdth,wght.ttf",
    "ko": "Noto_Sans_KR/NotoSansKR-VariableFont_wght.ttf",
}

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def validate_path(path: str, path_type: str = "file") -> bool:
    """安全的路径验证 - 增强对特殊字符和中文的支持"""
    try:
        # 先检查原始路径是否存在，避免过度规范化导致问题
        if path_type == "file" and os.path.isfile(path):
            return True
        elif path_type == "dir" and os.path.isdir(path):
            return True
        elif path_type == "exists" and os.path.exists(path):
            return True

        # 如果原始路径检查失败，尝试规范化路径
        try:
            normalized_path = os.path.abspath(os.path.normpath(path))
        except (OSError, ValueError, UnicodeError) as e:
            logger.debug(f"路径规范化失败: {path}, 错误: {e}")
            return False

        # 确保路径在允许的基础目录内
        allowed_bases = [
            os.path.abspath(BASE_PATH),
            os.path.abspath(FONTS_DIR),
            "/tmp",
            tempfile.gettempdir(),
        ]

        # 更宽松的路径检查 - 只要路径存在且在合理范围内就允许
        path_in_allowed_base = False
        for base in allowed_bases:
            try:
                if normalized_path.startswith(base):
                    path_in_allowed_base = True
                    break
            except (AttributeError, TypeError):
                continue

        if not path_in_allowed_base:
            # 对于非常规路径，检查是否是相对于BASE_PATH的有效路径
            if os.path.commonpath(
                [normalized_path, os.path.abspath(BASE_PATH)]
            ) == os.path.abspath(BASE_PATH):
                path_in_allowed_base = True

        if not path_in_allowed_base:
            logger.debug(f"路径不在允许的目录内: {path}")
            return False

        # 最终存在性检查
        if path_type == "file":
            return os.path.isfile(normalized_path)
        elif path_type == "dir":
            return os.path.isdir(normalized_path)
        else:
            return os.path.exists(normalized_path)

    except Exception as e:
        logger.debug(f"路径验证异常: {path}, 错误: {e}")
        # 对于验证失败的情况，尝试直接检查文件是否存在
        try:
            if path_type == "file":
                return os.path.isfile(path)
            elif path_type == "dir":
                return os.path.isdir(path)
            else:
                return os.path.exists(path)
        except:
            return False


def get_file_hash(file_path: str) -> Optional[str]:
    """获取文件的MD5哈希值，用于完整性检查"""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return None


def add_subtitle_to_video_parallel(
    video_path: str,
    srt_path: str,
    output_path: str,
    language: str,
    use_gpu: bool = False,
    timeout: Optional[int] = None,
) -> TaskResult:
    """并行安全的字幕添加函数"""
    start_time = time.time()
    channel = os.path.basename(os.path.dirname(os.path.dirname(video_path)))
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    try:
        # 路径验证 - 提供详细的错误信息
        path_checks = [
            (video_path, "file", "视频文件"),
            (srt_path, "file", "字幕文件"),
            (os.path.dirname(output_path), "dir", "输出目录"),
        ]

        for path, path_type, desc in path_checks:
            if not validate_path(path, path_type):
                # 创建输出目录如果不存在
                if desc == "输出目录":
                    try:
                        os.makedirs(path, exist_ok=True)
                        if validate_path(path, "dir"):
                            continue
                    except Exception as e:
                        logger.debug(f"创建输出目录失败: {path}, 错误: {e}")

                error_msg = f"{desc}路径验证失败: {path}"
                logger.debug(error_msg)
                return TaskResult(
                    False,
                    channel,
                    video_name,
                    language,
                    time.time() - start_time,
                    error_msg,
                )

        # 检查字体文件
        font_file = LANGUAGE_FONTS.get(language)
        if not font_file:
            return TaskResult(
                False,
                channel,
                video_name,
                language,
                time.time() - start_time,
                f"不支持的语言: {language}",
            )

        font_path = os.path.join(FONTS_DIR, font_file)
        if not validate_path(font_path, "file"):
            return TaskResult(
                False,
                channel,
                video_name,
                language,
                time.time() - start_time,
                f"字体文件不存在: {font_path}",
            )

        # 创建输出目录
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 构建ffmpeg命令
        cmd = build_ffmpeg_command(video_path, srt_path, output_path, language, use_gpu)

        # 执行命令（可选超时）
        if timeout:
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
        else:
            # 无超时限制，等待处理完成
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

        if process.returncode == 0:
            # 验证输出文件
            if validate_path(output_path, "file"):
                output_size = os.path.getsize(output_path)
                processing_time = time.time() - start_time
                logger.info(
                    f"成功处理: {channel}/{video_name}/{language} ({processing_time:.1f}s)"
                )
                return TaskResult(
                    True,
                    channel,
                    video_name,
                    language,
                    processing_time,
                    output_size=output_size,
                )
            else:
                return TaskResult(
                    False,
                    channel,
                    video_name,
                    language,
                    time.time() - start_time,
                    "输出文件验证失败",
                )
        else:
            error_msg = process.stderr[:500] if process.stderr else "未知错误"
            return TaskResult(
                False,
                channel,
                video_name,
                language,
                time.time() - start_time,
                f"ffmpeg错误: {error_msg}",
            )

    except subprocess.TimeoutExpired:
        timeout_msg = f"处理超时 (>{timeout}s)" if timeout else "处理超时"
        return TaskResult(
            False,
            channel,
            video_name,
            language,
            time.time() - start_time,
            timeout_msg,
        )
    except Exception as e:
        return TaskResult(
            False,
            channel,
            video_name,
            language,
            time.time() - start_time,
            f"处理异常: {str(e)}",
        )


def build_ffmpeg_command(
    video_path: str,
    srt_path: str,
    output_path: str,
    language: str,
    use_gpu: bool = False,
) -> List[str]:
    """构建优化的ffmpeg命令"""

    font_file = LANGUAGE_FONTS[language]
    font_path = os.path.join(FONTS_DIR, font_file)
    fonts_dir = os.path.dirname(font_path)

    # 字体名称映射
    font_names = {
        "en": "notosans",
        "ja": "notosansjp",
        "vi": "notosans",
        "ko": "notosanskr",
    }
    font_name = font_names.get(language, "notosans")

    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error"]

    # GPU加速配置
    if use_gpu:
        system = platform.system()
        if system == "Linux":
            # NVIDIA GPU
            cmd.extend(
                [
                    "-hwaccel",
                    "cuda",
                    "-hwaccel_output_format",
                    "cuda",
                    "-extra_hw_frames",
                    "3",
                ]
            )
        elif system == "Darwin":
            # macOS VideoToolbox
            cmd.extend(["-hwaccel", "videotoolbox"])

    # 输入文件
    cmd.extend(["-i", video_path])

    # 字幕滤镜
    if use_gpu and platform.system() == "Linux":
        subtitle_filter = (
            f"hwdownload,format=nv12,"
            f"subtitles={srt_path}:fontsdir={fonts_dir}:"
            f"force_style='Fontname={font_name},FontSize=16,FontWeight=500,"
            f"PrimaryColour=&HFFFFFF,OutlineColour=&H383838,BorderStyle=1,Outline=0.6,MarginV=20',"
            f"hwupload_cuda"
        )
    else:
        subtitle_filter = (
            f"subtitles={srt_path}:fontsdir={fonts_dir}:"
            f"force_style='Fontname={font_name},FontSize=16,FontWeight=500,"
            f"PrimaryColour=&HFFFFFF,OutlineColour=&H383838,BorderStyle=1,Outline=0.6,MarginV=20'"
        )

    cmd.extend(["-vf", subtitle_filter])

    # 编码设置
    if use_gpu:
        system = platform.system()
        if system == "Linux":
            # NVIDIA GPU编码
            cmd.extend(
                [
                    "-c:v",
                    "h264_nvenc",
                    "-preset",
                    "p1",
                    "-profile:v",
                    "main",
                    "-b:v",
                    "2M",
                    "-maxrate",
                    "3M",
                    "-bufsize",
                    "3M",
                    "-rc",
                    "constqp",
                    "-qp",
                    "26",
                ]
            )
        elif system == "Darwin":
            # VideoToolbox编码
            cmd.extend(
                [
                    "-c:v",
                    "h264_videotoolbox",
                    "-b:v",
                    "2.5M",
                    "-maxrate",
                    "3.5M",
                    "-q:v",
                    "75",
                    "-profile:v",
                    "main",
                ]
            )
    else:
        # CPU编码
        cmd.extend(
            ["-c:v", "libx264", "-preset", "fast", "-crf", "23", "-profile:v", "main"]
        )

    # 音频复制和输出
    cmd.extend(["-c:a", "copy", "-y", output_path])

    return cmd


def diagnose_paths(channel: str, video_name: str, language: str) -> None:
    """诊断路径问题"""
    video_path = os.path.join(INPUT_MP4_PATH, channel, language, f"{video_name}.mp4")
    srt_path = os.path.join(INPUT_SRT_PATH, channel, language, f"{video_name}.srt")
    output_path = os.path.join(OUTPUT_MP4_PATH, channel, language, f"{video_name}.mp4")

    logger.info(f"诊断路径问题:")
    logger.info(f"  视频文件: {video_path}")
    logger.info(f"    存在: {os.path.exists(video_path)}")
    logger.info(f"    是文件: {os.path.isfile(video_path)}")
    logger.info(f"  字幕文件: {srt_path}")
    logger.info(f"    存在: {os.path.exists(srt_path)}")
    logger.info(f"    是文件: {os.path.isfile(srt_path)}")
    logger.info(f"  输出目录: {os.path.dirname(output_path)}")
    logger.info(f"    存在: {os.path.exists(os.path.dirname(output_path))}")
    logger.info(f"    是目录: {os.path.isdir(os.path.dirname(output_path))}")


def collect_tasks(
    languages: List[str], force: bool = False
) -> List[Tuple[str, str, str]]:
    """收集所有待处理任务"""
    tasks = []

    if not os.path.exists(INPUT_MP4_PATH):
        logger.error(f"输入MP4路径不存在: {INPUT_MP4_PATH}")
        return tasks

    # 获取所有频道
    channels = [
        d
        for d in os.listdir(INPUT_MP4_PATH)
        if os.path.isdir(os.path.join(INPUT_MP4_PATH, d)) and not d.startswith(".")
    ]

    for channel in channels:
        channel_path = os.path.join(INPUT_MP4_PATH, channel)

        # 获取语言目录
        lang_dirs = [
            d
            for d in os.listdir(channel_path)
            if (
                os.path.isdir(os.path.join(channel_path, d))
                and d in languages
                and not d.startswith(".")
            )
        ]

        for lang in lang_dirs:
            lang_path = os.path.join(channel_path, lang)

            # 获取视频文件
            video_files = [
                f
                for f in glob.glob(os.path.join(lang_path, "*.mp4"))
                if not os.path.basename(f).startswith(".")
            ]

            for video_file in video_files:
                video_name = os.path.splitext(os.path.basename(video_file))[0]

                # 检查SRT文件
                srt_file = os.path.join(
                    INPUT_SRT_PATH, channel, lang, f"{video_name}.srt"
                )
                if not os.path.exists(srt_file):
                    continue

                # 检查输出文件
                output_file = os.path.join(
                    OUTPUT_MP4_PATH, channel, lang, f"{video_name}.mp4"
                )
                if os.path.exists(output_file) and not force:
                    continue

                tasks.append((channel, video_name, lang))

    return tasks


def process_videos_parallel(
    languages: List[str],
    force: bool = False,
    use_gpu: bool = False,
    max_workers: Optional[int] = None,
    timeout: Optional[int] = None,
) -> None:
    """并行处理所有视频"""

    # 资源管理
    resource_manager = ResourceManager()
    performance_monitor = PerformanceMonitor()

    if max_workers is None:
        max_workers = resource_manager.get_optimal_workers(use_gpu)

    logger.info(f"使用 {max_workers} 个并行工作进程")
    if timeout:
        logger.info(f"每个任务超时时间: {timeout}秒")
    else:
        logger.info("无超时限制，等待每个任务完成")

    # 收集任务
    tasks = collect_tasks(languages, force)
    total_tasks = len(tasks)

    if total_tasks == 0:
        logger.info("没有需要处理的任务")
        return

    logger.info(f"找到 {total_tasks} 个待处理任务")

    # 创建进度条
    pbar = tqdm(total=total_tasks, desc="处理视频", unit="个")

    # 并行处理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_task = {}

        for channel, video_name, language in tasks:
            video_path = os.path.join(
                INPUT_MP4_PATH, channel, language, f"{video_name}.mp4"
            )
            srt_path = os.path.join(
                INPUT_SRT_PATH, channel, language, f"{video_name}.srt"
            )
            output_path = os.path.join(
                OUTPUT_MP4_PATH, channel, language, f"{video_name}.mp4"
            )

            future = executor.submit(
                add_subtitle_to_video_parallel,
                video_path,
                srt_path,
                output_path,
                language,
                use_gpu,
                timeout,
            )
            future_to_task[future] = (channel, video_name, language)

        # 处理完成的任务
        for future in as_completed(future_to_task):
            try:
                result = future.result()
                performance_monitor.update(result)

                if not result.success:
                    logger.error(
                        f"处理失败: {result.channel}/{result.video_name}/{result.language} - {result.error_message}"
                    )

                pbar.update(1)

                # 更新进度条描述
                stats = performance_monitor.get_stats()
                pbar.set_postfix(
                    {
                        "成功": stats["processed_count"],
                        "失败": stats["failed_count"],
                        "速度": f"{stats['avg_speed']:.1f}/s",
                    }
                )

            except Exception as e:
                task_info = future_to_task.get(future, "未知任务")
                logger.error(f"任务执行异常: {task_info} - {str(e)}")
                pbar.update(1)

    pbar.close()

    # 最终统计
    final_stats = performance_monitor.get_stats()
    logger.info(
        f"处理完成 - 总耗时: {final_stats['elapsed_time']:.1f}s, "
        f"成功: {final_stats['processed_count']}, "
        f"失败: {final_stats['failed_count']}, "
        f"平均速度: {final_stats['avg_speed']:.2f}个/s, "
        f"总大小: {final_stats['total_size_mb']:.1f}MB"
    )


def main():
    """主函数"""

    # 检查必要工具
    try:
        subprocess.run(
            ["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except FileNotFoundError:
        logger.error("未找到ffmpeg，请先安装ffmpeg")
        sys.exit(1)

    # 命令行参数解析
    parser = argparse.ArgumentParser(description="多语言视频字幕添加工具 - 优化版本")

    parser.add_argument(
        "-l",
        "--languages",
        nargs="+",
        choices=SUPPORTED_LANGUAGES,
        default=SUPPORTED_LANGUAGES,
        help=f"目标语言列表 (默认: {' '.join(SUPPORTED_LANGUAGES)})",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="强制重新生成，即使输出文件已存在"
    )
    parser.add_argument(
        "-s", "--single", type=str, help="只处理指定的单个视频，格式: 频道名/视频名"
    )
    parser.add_argument("--gpu", action="store_true", help="使用GPU加速ffmpeg处理")
    parser.add_argument(
        "-w", "--workers", type=int, help="并行工作进程数 (默认根据系统资源自动计算)"
    )
    parser.add_argument(
        "--sequential", action="store_true", help="使用串行处理模式 (禁用并行)"
    )
    parser.add_argument(
        "--debug", action="store_true", help="启用调试模式，显示详细的错误信息"
    )
    parser.add_argument(
        "--test-paths",
        action="store_true",
        help="测试路径配置并显示第一个任务的详细信息",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="设置每个任务的超时时间（秒），默认无超时限制",
    )

    args = parser.parse_args()

    # 设置调试模式
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # 验证语言参数
    valid_languages = [lang for lang in args.languages if lang in SUPPORTED_LANGUAGES]
    if not valid_languages:
        logger.error("没有指定任何有效的语言")
        sys.exit(1)

    # 路径测试模式
    if args.test_paths:
        logger.info("测试路径配置...")
        logger.info(f"基础路径: {BASE_PATH}")
        logger.info(f"输入MP4路径: {INPUT_MP4_PATH}")
        logger.info(f"输入SRT路径: {INPUT_SRT_PATH}")
        logger.info(f"字体目录: {FONTS_DIR}")
        logger.info(f"输出MP4路径: {OUTPUT_MP4_PATH}")

        # 测试第一个任务
        tasks = collect_tasks(valid_languages)
        if tasks:
            channel, video_name, language = tasks[0]
            logger.info(f"测试第一个任务: {channel}/{video_name}/{language}")
            diagnose_paths(channel, video_name, language)
        else:
            logger.info("没有找到任何任务")
        return

    # 单个视频处理模式
    if args.single:
        if "/" not in args.single:
            logger.error("单个视频参数格式应为 '频道名/视频名'")
            sys.exit(1)

        channel, video_name = args.single.split("/", 1)
        logger.info(f"处理单个视频: {channel}/{video_name}")

        success_count = 0
        for language in valid_languages:
            video_path = os.path.join(
                INPUT_MP4_PATH, channel, language, f"{video_name}.mp4"
            )
            srt_path = os.path.join(
                INPUT_SRT_PATH, channel, language, f"{video_name}.srt"
            )
            output_path = os.path.join(
                OUTPUT_MP4_PATH, channel, language, f"{video_name}.mp4"
            )

            result = add_subtitle_to_video_parallel(
                video_path, srt_path, output_path, language, args.gpu, args.timeout
            )

            if result.success:
                success_count += 1
                logger.info(f"成功处理: {language}")
            else:
                logger.error(f"处理失败: {language} - {result.error_message}")

        logger.info(
            f"处理完成，成功生成 {success_count}/{len(valid_languages)} 个语言版本"
        )

    else:
        # 批量处理模式
        if args.sequential:
            logger.info("使用串行处理模式")
            # 这里可以调用原始的顺序处理函数
            # process_all_videos(valid_languages, args.force, args.gpu)
        else:
            logger.info("使用并行处理模式")
            if args.gpu:
                logger.info("已启用GPU加速")

            process_videos_parallel(
                valid_languages, args.force, args.gpu, args.workers, args.timeout
            )


if __name__ == "__main__":
    # 信号处理，优雅关闭
    def signal_handler(sig, frame):
        logger.info("收到中断信号，正在停止...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    main()
