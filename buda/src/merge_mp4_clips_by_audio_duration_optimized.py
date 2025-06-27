#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
优化版本的MP4片段合并脚本
=======================

主要改进：
1. 并行处理 - 使用多进程池处理多个文件
2. 内存优化 - 避免重复加载视频片段列表
3. 更安全的路径处理 - 使用pathlib和参数验证
4. 更好的错误处理和恢复机制
5. 缓存机制 - 避免重复计算
6. 更精确的视频时长匹配
7. 进度显示和统计信息
8. 配置文件支持
"""

import os
import time
import subprocess
import random
import json
import argparse
import threading
import sys
import platform
import logging
import hashlib
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
import tempfile
from functools import lru_cache


@dataclass
class Config:
    """配置类"""

    base_path: str
    mp3_base_dir: str
    mp4_clips_dir: str
    output_base_dir: str
    clip_duration: float = 8.0
    max_workers: int = 4
    cache_enabled: bool = True
    log_level: str = "INFO"


class VideoProcessor:
    """视频处理器类"""

    def __init__(self, config: Config):
        self.config = config
        self.setup_logging()
        self.video_clips_cache = None
        self.duration_cache = {}

    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("video_processor.log"),
            ],
        )
        self.logger = logging.getLogger(__name__)

    @lru_cache(maxsize=1000)
    def get_audio_duration(self, audio_file: str) -> float:
        """获取音频文件时长，带缓存"""
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio_file),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
            return duration
        except (subprocess.CalledProcessError, ValueError) as e:
            self.logger.error(f"获取音频时长失败 {audio_file}: {e}")
            return 0.0

    def get_video_clips(self) -> List[Path]:
        """获取所有视频片段，带缓存"""
        if self.video_clips_cache is None:
            clips_dir = Path(self.config.mp4_clips_dir)
            if not clips_dir.exists():
                raise FileNotFoundError(f"视频片段目录不存在: {clips_dir}")

            self.video_clips_cache = [
                f
                for f in clips_dir.glob("*.mp4")
                if not f.name.startswith(".") and f.is_file()
            ]
            self.logger.info(f"加载了 {len(self.video_clips_cache)} 个视频片段")

        return self.video_clips_cache

    def calculate_clips_needed(self, audio_duration: float) -> int:
        """计算需要的视频片段数量"""
        return max(
            1,
            int(
                (audio_duration + self.config.clip_duration - 1)
                // self.config.clip_duration
            ),
        )

    def select_clips(
        self, clips_needed: int, available_clips: List[Path]
    ) -> List[Path]:
        """智能选择视频片段"""
        if not available_clips:
            raise ValueError("没有可用的视频片段")

        # 如果需要的片段数少于可用片段，随机选择不重复的片段
        if clips_needed <= len(available_clips):
            return random.sample(available_clips, clips_needed)
        else:
            # 如果需要更多片段，允许重复但尽量均匀分布
            selected = []
            for i in range(clips_needed):
                selected.append(available_clips[i % len(available_clips)])
            random.shuffle(selected)
            return selected

    def create_optimized_video(
        self, selected_clips: List[Path], target_duration: float, output_path: Path
    ) -> bool:
        """使用一次性FFmpeg命令创建精确时长的视频"""
        try:
            # 创建临时文件列表
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                concat_file = Path(f.name)
                for clip in selected_clips:
                    # 安全地转义路径
                    escaped_path = str(clip).replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            # 一次性合并并裁剪到精确时长
            cmd = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-t",
                str(target_duration),
                "-c",
                "copy",
                "-avoid_negative_ts",
                "make_zero",
                "-y",
                str(output_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # 验证输出文件
            if output_path.exists() and output_path.stat().st_size > 0:
                actual_duration = self.get_audio_duration(str(output_path))
                self.logger.info(
                    f"生成视频: {output_path.name}, 目标时长: {target_duration:.2f}s, 实际时长: {actual_duration:.2f}s"
                )
                return True

            return False

        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg错误: {e.stderr}")
            return False
        finally:
            # 清理临时文件
            if concat_file.exists():
                concat_file.unlink()

    def process_single_audio(
        self, audio_file: Path, channel: str, language: str
    ) -> bool:
        """处理单个音频文件"""
        try:
            # 检查输入文件
            if not audio_file.exists():
                self.logger.error(f"音频文件不存在: {audio_file}")
                return False

            # 获取音频时长
            audio_duration = self.get_audio_duration(str(audio_file))
            if audio_duration <= 0:
                self.logger.error(f"无效的音频时长: {audio_file}")
                return False

            # 设置输出路径
            output_dir = Path(self.config.output_base_dir) / channel / language
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{audio_file.stem}.mp4"

            # 检查是否需要重新生成
            if output_file.exists():
                existing_duration = self.get_audio_duration(str(output_file))
                if abs(existing_duration - audio_duration) <= 0.1:  # 允许0.1秒误差
                    self.logger.info(f"跳过已存在的文件: {output_file.name}")
                    return True
                else:
                    self.logger.info(f"重新生成时长不匹配的文件: {output_file.name}")

            # 获取视频片段
            available_clips = self.get_video_clips()
            clips_needed = self.calculate_clips_needed(audio_duration)
            selected_clips = self.select_clips(clips_needed, available_clips)

            # 生成视频
            success = self.create_optimized_video(
                selected_clips, audio_duration, output_file
            )

            if success:
                self.logger.info(f"成功处理: {audio_file.name} -> {output_file.name}")
            else:
                self.logger.error(f"处理失败: {audio_file.name}")

            return success

        except Exception as e:
            self.logger.error(f"处理音频文件时出错 {audio_file}: {e}")
            return False


def get_default_config() -> Config:
    """获取默认配置"""
    if platform.system() == "Darwin":
        base_path = "/Volumes/dhl/buda_videos_youtube"
    else:
        base_path = "/media/dhl/buda_videos_youtube"

    return Config(
        base_path=base_path,
        mp3_base_dir=f"{base_path}/merge_multi_lange_mp3",
        mp4_clips_dir=f"{base_path}/mp4_clips",
        output_base_dir=f"{base_path}/mp4_merge_silient",
        max_workers=min(4, os.cpu_count() or 1),
    )


def load_config_from_file(config_file: str) -> Config:
    """从配置文件加载配置"""
    with open(config_file, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    config = get_default_config()
    for key, value in config_data.items():
        if hasattr(config, key):
            setattr(config, key, value)

    return config


def find_audio_files(
    base_dir: str,
    channel: Optional[str] = None,
    language: Optional[str] = None,
    specific_file: Optional[str] = None,
) -> List[Tuple[Path, str, str]]:
    """查找音频文件"""
    audio_files = []
    base_path = Path(base_dir)

    if not base_path.exists():
        raise FileNotFoundError(f"基础目录不存在: {base_path}")

    # 确定要处理的频道
    if channel:
        channel_dirs = [channel] if (base_path / channel).exists() else []
    else:
        channel_dirs = [
            d.name
            for d in base_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    for ch in channel_dirs:
        channel_path = base_path / ch

        # 确定要处理的语言
        if language:
            lang_dirs = [language] if (channel_path / language).exists() else []
        else:
            lang_dirs = [
                d.name
                for d in channel_path.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]

        for lang in lang_dirs:
            lang_path = channel_path / lang

            # 确定要处理的文件
            if specific_file:
                file_path = lang_path / specific_file
                if file_path.exists():
                    audio_files.append((file_path, ch, lang))
            else:
                for audio_file in lang_path.glob("*.mp3"):
                    if not audio_file.name.startswith("."):
                        audio_files.append((audio_file, ch, lang))

    return audio_files


def process_audio_batch(
    processor: VideoProcessor, audio_batch: List[Tuple[Path, str, str]]
) -> Dict[str, int]:
    """批量处理音频文件"""
    stats = {"success": 0, "failed": 0, "skipped": 0}

    for audio_file, channel, language in audio_batch:
        try:
            success = processor.process_single_audio(audio_file, channel, language)
            if success:
                stats["success"] += 1
            else:
                stats["failed"] += 1
        except Exception as e:
            logging.error(f"处理文件时出错 {audio_file}: {e}")
            stats["failed"] += 1

    return stats


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="优化版MP4片段合并脚本")
    parser.add_argument("-c", "--channel", help="指定频道")
    parser.add_argument("-l", "--language", help="指定语言")
    parser.add_argument("-f", "--file", help="指定音频文件")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--base-path", help="自定义基础路径")
    parser.add_argument("--max-workers", type=int, help="最大并发工作进程数")
    parser.add_argument("--list-channels", action="store_true", help="列出所有频道")
    parser.add_argument("--list-languages", help="列出指定频道的语言")
    parser.add_argument(
        "--dry-run", action="store_true", help="仅显示将要处理的文件，不实际处理"
    )

    args = parser.parse_args()

    # 加载配置
    if args.config:
        config = load_config_from_file(args.config)
    else:
        config = get_default_config()

    # 应用命令行覆盖
    if args.base_path:
        config.base_path = args.base_path
        config.mp3_base_dir = f"{args.base_path}/merge_multi_lange_mp3"
        config.mp4_clips_dir = f"{args.base_path}/mp4_clips"
        config.output_base_dir = f"{args.base_path}/mp4_merge_silient"

    if args.max_workers:
        config.max_workers = args.max_workers

    # 处理列表命令
    if args.list_channels:
        channels = [
            d.name
            for d in Path(config.mp3_base_dir).iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]
        print("可用频道:")
        for ch in channels:
            print(f"  - {ch}")
        return

    if args.list_languages:
        channel_path = Path(config.mp3_base_dir) / args.list_languages
        if channel_path.exists():
            languages = [
                d.name
                for d in channel_path.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ]
            print(f"频道 {args.list_languages} 的可用语言:")
            for lang in languages:
                print(f"  - {lang}")
        else:
            print(f"频道不存在: {args.list_languages}")
        return

    # 查找要处理的音频文件
    try:
        audio_files = find_audio_files(
            config.mp3_base_dir, args.channel, args.language, args.file
        )
    except FileNotFoundError as e:
        print(f"错误: {e}")
        return

    if not audio_files:
        print("未找到匹配的音频文件")
        return

    print(f"找到 {len(audio_files)} 个音频文件待处理")

    if args.dry_run:
        print("试运行模式 - 将要处理的文件:")
        for audio_file, channel, language in audio_files:
            print(f"  {channel}/{language}/{audio_file.name}")
        return

    # 创建处理器
    processor = VideoProcessor(config)

    # 并行处理
    start_time = time.time()
    total_stats = {"success": 0, "failed": 0, "skipped": 0}

    # 将文件分批处理以避免内存过度使用
    batch_size = max(1, len(audio_files) // config.max_workers)
    batches = [
        audio_files[i : i + batch_size] for i in range(0, len(audio_files), batch_size)
    ]

    print(f"使用 {config.max_workers} 个工作进程处理 {len(batches)} 个批次")

    with ProcessPoolExecutor(max_workers=config.max_workers) as executor:
        future_to_batch = {
            executor.submit(process_audio_batch, processor, batch): batch
            for batch in batches
        }

        completed = 0
        for future in as_completed(future_to_batch):
            try:
                stats = future.result()
                for key in total_stats:
                    total_stats[key] += stats[key]
                completed += 1
                print(f"进度: {completed}/{len(batches)} 批次完成")
            except Exception as e:
                logging.error(f"批次处理失败: {e}")

    # 显示统计信息
    end_time = time.time()
    print(f"\n处理完成!")
    print(f"总耗时: {end_time - start_time:.2f} 秒")
    print(f"成功: {total_stats['success']}")
    print(f"失败: {total_stats['failed']}")
    print(f"跳过: {total_stats['skipped']}")
    print(f"处理速度: {len(audio_files) / (end_time - start_time):.2f} 文件/秒")


if __name__ == "__main__":
    main()
