#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多语言视频字幕添加工具 - 优化版本

功能说明:
此脚本用于为多语言视频自动添加对应语言的SRT字幕，并使用适合的字体进行渲染。
支持多种语言，包括英语(en)、日语(ja)、越南语(vi)和韩语(ko)等。

优化特性:
1. 批量预处理，减少重复I/O操作
2. 智能缓存机制，避免重复验证
3. 优化的FFmpeg参数选择
4. 更高效的文件系统操作
5. 智能资源管理
6. 输出文件时长验证，确保处理质量

目录结构:
- 输入MP4目录: /Volumes/dhl/buda_videos_youtube/mp4_merge_silient/
- 输入SRT目录: /Volumes/dhl/buda_videos_youtube/multi_lang_srt/
- 字体目录: /Users/donghaoliu/doc/short_whisper/fonts/
- 输出MP4目录: /Volumes/dhl/buda_videos_youtube/mp4_multi_with_subtitles/

使用方法:
python add_subtitles_to_mp4_optimized.py [-l LANGUAGES] [-f] [-s CHANNEL/VIDEO] [--gpu]
"""

import os
import argparse
import platform
import subprocess
import sys
from pathlib import Path
import logging
import time
import json
import multiprocessing
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading
import re


@dataclass
class TaskInfo:
    """任务信息数据类"""
    channel: str
    video_name: str
    language: str
    input_video_path: str
    input_srt_path: str
    output_video_path: str
    video_size: int = 0
    estimated_duration: float = 0.0


class OptimizedSubtitleProcessor:
    """优化的字幕处理器"""
    
    def __init__(self):
        self.base_path = self._get_base_path()
        self.fonts_dir = self._get_fonts_dir()
        
        # 路径定义
        self.input_mp4_path = Path(self.base_path) / "mp4_merge_silient"
        self.input_srt_path = Path(self.base_path) / "multi_lang_srt"
        self.output_mp4_path = Path(self.base_path) / "mp4_multi_with_subtitles"
        
        # 支持的语言和字体映射
        self.supported_languages = ["en", "ja", "vi", "ko"]
        self.language_fonts = {
            "en": "Noto_Sans_EN/NotoSans-VariableFont_wdth,wght.ttf",
            "ja": "Noto_Sans_JP/NotoSansJP-VariableFont_wght.ttf",
            "vi": "Noto_Sans_VI/NotoSans-VariableFont_wdth,wght.ttf",
            "ko": "Noto_Sans_KR/NotoSansKR-VariableFont_wght.ttf",
        }
        
        # 缓存
        self.font_cache = {}
        self.gpu_info = None
        self.validated_paths = set()
        self.system_info = self._get_system_info()
        self.duration_cache = {}  # 缓存文件时长信息
        
        # 性能统计
        self.stats = {
            'total_tasks': 0,
            'successful_tasks': 0,
            'failed_tasks': 0,
            'total_processing_time': 0.0,
            'io_time': 0.0,
            'encoding_time': 0.0,
            'files_checked': 0,
            'invalid_files_removed': 0,
            'duration_check_time': 0.0
        }
        
        # 设置日志
        self._setup_logging()
        
        # 预初始化
        self._initialize_caches()
    
    def _get_base_path(self) -> str:
        """根据操作系统类型返回对应的基础路径"""
        if platform.system() == "Darwin":  # macOS
            return "/Volumes/dhl/buda_videos_youtube"
        else:  # 默认为Linux/Ubuntu
            return "/media/dhl/buda_videos_youtube"
    
    def _get_fonts_dir(self) -> str:
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
    
    def _get_system_info(self) -> Dict:
        """获取系统信息"""
        return {
            'platform': platform.system(),
            'cpu_count': multiprocessing.cpu_count(),
            'python_version': platform.python_version(),
        }
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.logger = logging.getLogger(__name__)
    
    def _initialize_caches(self):
        """初始化缓存"""
        # 预验证字体路径
        for lang, font_file in self.language_fonts.items():
            font_path = Path(self.fonts_dir) / font_file
            self.font_cache[lang] = {
                'path': str(font_path),
                'exists': font_path.exists(),
                'dir': str(font_path.parent)
            }
        
        # 检查GPU信息（只检查一次）
        if self.system_info['platform'] == "Linux":
            self.gpu_info = self._check_nvidia_gpu()
        elif self.system_info['platform'] == "Darwin":
            self.gpu_info = {'available': True, 'type': 'videotoolbox'}
        else:
            self.gpu_info = {'available': False}
    
    def _check_nvidia_gpu(self) -> Dict:
        """检查NVIDIA GPU信息"""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.total,memory.free",
                    "--format=csv,noheader,nounits",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return {'available': False}
            
            lines = result.stdout.strip().split("\n")
            if not lines:
                return {'available': False}
            
            parts = lines[0].strip().split(",")
            if len(parts) >= 2:
                total_memory = int(parts[0].strip())
                free_memory = int(parts[1].strip())
                
                return {
                    'available': True,
                    'type': 'nvidia',
                    'total_memory': total_memory,
                    'free_memory': free_memory
                }
            
            return {'available': False}
        except Exception as e:
            self.logger.warning(f"检查NVIDIA GPU时出错: {str(e)}")
            return {'available': False}
    
    def check_required_tools(self) -> bool:
        """检查必要的工具是否安装"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            self.logger.error("未找到ffmpeg，请先安装ffmpeg")
            return False
    
    def get_video_duration(self, video_path: str) -> Optional[float]:
        """获取视频时长（秒）"""
        if video_path in self.duration_cache:
            return self.duration_cache[video_path]
        
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.logger.warning(f"无法获取视频时长: {video_path}")
                return None
            
            data = json.loads(result.stdout)
            duration = float(data.get('format', {}).get('duration', 0))
            
            # 缓存结果
            self.duration_cache[video_path] = duration
            return duration
            
        except Exception as e:
            self.logger.warning(f"获取视频时长时出错 {video_path}: {str(e)}")
            return None
    
    def check_output_file_validity(self, input_path: str, output_path: str, max_diff: float = 3.0) -> bool:
        """检查输出文件是否有效（时长差异是否在允许范围内）"""
        if not os.path.exists(output_path):
            return False
        
        input_duration = self.get_video_duration(input_path)
        output_duration = self.get_video_duration(output_path)
        
        if input_duration is None or output_duration is None:
            self.logger.warning(f"无法获取文件时长，将重新生成: {output_path}")
            return False
        
        duration_diff = abs(input_duration - output_duration)
        
        if duration_diff > max_diff:
            self.logger.warning(
                f"时长差异过大 ({duration_diff:.2f}s > {max_diff}s): "
                f"输入={input_duration:.2f}s, 输出={output_duration:.2f}s, 文件={output_path}"
            )
            return False
        
        self.logger.debug(
            f"时长验证通过 (差异{duration_diff:.2f}s): {output_path}"
        )
        return True
    
    def validate_and_clean_output_files(self, languages: List[str]) -> int:
        """验证并清理输出目录中的无效文件"""
        start_time = time.time()
        removed_count = 0
        checked_count = 0
        
        self.logger.info("开始检查输出目录中的文件时长...")
        
        if not self.output_mp4_path.exists():
            self.logger.info("输出目录不存在，跳过验证")
            return 0
        
        try:
            # 遍历输出目录
            for channel_path in self.output_mp4_path.iterdir():
                if not channel_path.is_dir() or channel_path.name.startswith('.'):
                    continue
                
                channel = channel_path.name
                
                for lang_path in channel_path.iterdir():
                    if (not lang_path.is_dir() or 
                        lang_path.name not in languages or 
                        lang_path.name.startswith('.')):
                        continue
                    
                    language = lang_path.name
                    
                    # 获取所有输出MP4文件
                    output_files = list(lang_path.glob("*.mp4"))
                    output_files = [f for f in output_files if not f.name.startswith('.')]
                    
                    for output_file in output_files:
                        checked_count += 1
                        video_name = output_file.stem
                        
                        # 对应的输入文件
                        input_file = self.input_mp4_path / channel / language / f"{video_name}.mp4"
                        
                        if not input_file.exists():
                            self.logger.warning(f"对应输入文件不存在，删除输出文件: {output_file}")
                            try:
                                output_file.unlink()
                                removed_count += 1
                            except Exception as e:
                                self.logger.error(f"删除文件失败 {output_file}: {str(e)}")
                            continue
                        
                        # 检查时长是否有效
                        if not self.check_output_file_validity(str(input_file), str(output_file)):
                            self.logger.info(f"删除无效输出文件: {output_file}")
                            try:
                                output_file.unlink()
                                removed_count += 1
                            except Exception as e:
                                self.logger.error(f"删除文件失败 {output_file}: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"验证输出文件时出错: {str(e)}")
        
        validation_time = time.time() - start_time
        self.stats['duration_check_time'] += validation_time
        self.stats['files_checked'] = checked_count
        self.stats['invalid_files_removed'] = removed_count
        
        self.logger.info(
            f"文件验证完成: 检查了{checked_count}个文件，删除了{removed_count}个无效文件，"
            f"耗时{validation_time:.2f}秒"
        )
        
        return removed_count
    
    def collect_all_tasks(self, languages: List[str], force: bool = False) -> List[TaskInfo]:
        """优化的任务收集，批量处理I/O操作"""
        start_time = time.time()
        tasks = []
        
        # 验证语言支持
        valid_languages = [lang for lang in languages if lang in self.supported_languages]
        if not valid_languages:
            self.logger.error("没有指定任何有效的语言")
            return []
        
        # 检查输入路径
        if not self.input_mp4_path.exists():
            self.logger.error(f"输入MP4路径不存在: {self.input_mp4_path}")
            return []
        
        # 在开始任务收集前，先验证和清理输出文件
        if not force:  # 如果不是强制模式，才进行验证
            self.validate_and_clean_output_files(valid_languages)
        
        # 批量扫描所有频道和文件
        self.logger.info("开始批量扫描文件...")
        
        try:
            # 使用 os.walk 一次性遍历所有目录
            for channel_path in self.input_mp4_path.iterdir():
                if not channel_path.is_dir() or channel_path.name.startswith('.'):
                    continue
                
                channel = channel_path.name
                
                for lang_path in channel_path.iterdir():
                    if (not lang_path.is_dir() or 
                        lang_path.name not in valid_languages or 
                        lang_path.name.startswith('.')):
                        continue
                    
                    language = lang_path.name
                    
                    # 批量获取所有MP4文件
                    video_files = list(lang_path.glob("*.mp4"))
                    video_files = [f for f in video_files if not f.name.startswith('.')]
                    
                    for video_file in video_files:
                        video_name = video_file.stem
                        
                        # 构建路径
                        srt_file = self.input_srt_path / channel / language / f"{video_name}.srt"
                        output_file = self.output_mp4_path / channel / language / f"{video_name}.mp4"
                        
                        # 检查SRT文件是否存在
                        if not srt_file.exists():
                            continue
                        
                        # 检查是否需要处理
                        if output_file.exists() and not force:
                            continue
                        
                        # 获取视频文件大小（用于优化处理顺序）
                        try:
                            video_size = video_file.stat().st_size
                        except:
                            video_size = 0
                        
                        task = TaskInfo(
                            channel=channel,
                            video_name=video_name,
                            language=language,
                            input_video_path=str(video_file),
                            input_srt_path=str(srt_file),
                            output_video_path=str(output_file),
                            video_size=video_size
                        )
                        tasks.append(task)
        
        except Exception as e:
            self.logger.error(f"扫描文件时出错: {str(e)}")
            return []
        
        # 按文件大小排序，小文件优先处理（快速获得反馈）
        tasks.sort(key=lambda x: x.video_size)
        
        scan_time = time.time() - start_time
        self.stats['io_time'] += scan_time
        
        self.logger.info(f"文件扫描完成，找到 {len(tasks)} 个待处理任务，耗时: {scan_time:.2f}秒")
        return tasks
    
    def get_optimized_ffmpeg_params(self, task: TaskInfo, use_gpu: bool = False) -> List[str]:
        """根据任务特征获取优化的FFmpeg参数"""
        cmd = ["ffmpeg"]
        
        # 获取语言对应的字体信息
        font_info = self.font_cache.get(task.language)
        if not font_info or not font_info['exists']:
            raise ValueError(f"不支持的语言或字体不存在: {task.language}")
        
        # 字体名称映射
        font_names = {
            "en": "notosans",
            "ja": "notosansjp", 
            "vi": "notosans",
            "ko": "notosanskr"
        }
        font_name = font_names.get(task.language, "notosans")
        
        # GPU加速设置
        hw_accel_used = False
        if use_gpu and self.gpu_info['available']:
            if self.system_info['platform'] == "Linux" and self.gpu_info.get('type') == 'nvidia':
                # NVIDIA GPU加速
                cmd.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])
                
                # 根据GPU内存优化帧缓冲
                free_memory = self.gpu_info.get('free_memory', 0)
                if free_memory > 4000:
                    cmd.extend(["-extra_hw_frames", "5"])
                else:
                    cmd.extend(["-extra_hw_frames", "3"])
                
                hw_accel_used = True
                self.logger.debug("使用NVIDIA GPU硬件加速")
                
            elif self.system_info['platform'] == "Darwin":
                # macOS VideoToolbox加速
                cmd.extend(["-hwaccel", "videotoolbox"])
                hw_accel_used = True
                self.logger.debug("使用macOS VideoToolbox硬件加速")
        
        # 如果没有GPU加速，优化CPU使用
        if not hw_accel_used:
            cmd.extend(["-threads", str(self.system_info['cpu_count'])])
        
        # 输入文件
        cmd.extend(["-i", task.input_video_path])
        
        # 字幕滤镜
        if hw_accel_used and self.system_info['platform'] == "Linux":
            # GPU加速的字幕处理
            subtitle_filter = (
                f"hwdownload,format=nv12,"
                f"subtitles={task.input_srt_path}:fontsdir={font_info['dir']}:"
                f"force_style='Fontname={font_name},FontSize=16,FontWeight=500,"
                f"PrimaryColour=&HFFFFFF,OutlineColour=&H383838,BorderStyle=1,"
                f"Outline=0.6,MarginV=20',hwupload_cuda"
            )
            
            # GPU优化参数
            cmd.extend([
                "-rc-lookahead", "20",
                "-g", "120",
                "-strict", "experimental"
            ])
        else:
            # CPU字幕处理
            subtitle_filter = (
                f"subtitles={task.input_srt_path}:fontsdir={font_info['dir']}:"
                f"force_style='Fontname={font_name},FontSize=16,FontWeight=500,"
                f"PrimaryColour=&HFFFFFF,OutlineColour=&H383838,BorderStyle=1,"
                f"Outline=0.6,MarginV=20'"
            )
        
        cmd.extend(["-vf", subtitle_filter])
        
        # 音频处理（直接复制，不重新编码）
        cmd.extend(["-c:a", "copy"])
        
        # 视频编码设置
        if hw_accel_used:
            if self.system_info['platform'] == "Linux":
                # NVIDIA GPU编码
                free_memory = self.gpu_info.get('free_memory', 0)
                if free_memory > 5000:
                    # 高内存GPU优化设置
                    cmd.extend([
                        "-c:v", "h264_nvenc",
                        "-preset", "p1",
                        "-profile:v", "high",
                        "-tune", "hq",
                        "-b:v", "2.5M",
                        "-maxrate", "128M",
                        "-bufsize", "128M",
                        "-rc", "constqp",
                        "-qp", "26",
                        "-spatial_aq", "1",
                        "-temporal_aq", "1",
                        "-rc-lookahead", "1000"
                    ])
                else:
                    # 低内存GPU优化设置
                    cmd.extend([
                        "-c:v", "h264_nvenc",
                        "-preset", "p1",
                        "-profile:v", "main",
                        "-tune", "ll",
                        "-b:v", "2M",
                        "-maxrate", "3M",
                        "-bufsize", "3M",
                        "-rc", "constqp",
                        "-qp", "26",
                        "-spatial_aq", "1",
                        "-rc-lookahead", "10"
                    ])
            
            elif self.system_info['platform'] == "Darwin":
                # macOS VideoToolbox编码
                cmd.extend([
                    "-c:v", "h264_videotoolbox",
                    "-b:v", "2.5M",
                    "-maxrate", "3.5M",
                    "-q:v", "75",
                    "-allow_sw", "1",
                    "-profile:v", "main",
                    "-pix_fmt", "yuv420p"
                ])
        else:
            # CPU编码优化
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "fast",  # 平衡速度和质量
                "-crf", "23",       # 保持原有质量
                "-profile:v", "main",
                "-pix_fmt", "yuv420p"
            ])
        
        # 输出设置
        cmd.extend(["-y", task.output_video_path])
        
        return cmd
    
    def process_single_task(self, task: TaskInfo, use_gpu: bool = False) -> bool:
        """处理单个任务"""
        start_time = time.time()
        
        try:
            # 创建输出目录
            output_path = Path(task.output_video_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 获取优化的FFmpeg命令
            cmd = self.get_optimized_ffmpeg_params(task, use_gpu)
            
            self.logger.info(f"处理: {task.channel}/{task.video_name}/{task.language}")
            self.logger.debug(f"FFmpeg命令: {' '.join(cmd)}")
            
            # 执行FFmpeg命令
            encoding_start = time.time()
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            encoding_time = time.time() - encoding_start
            self.stats['encoding_time'] += encoding_time
            
            if process.returncode == 0:
                self.logger.info(f"成功处理: {task.channel}/{task.video_name}/{task.language}")
                self.stats['successful_tasks'] += 1
                return True
            else:
                self.logger.error(f"处理失败: {task.channel}/{task.video_name}/{task.language}")
                self.logger.error(f"错误信息: {process.stderr}")
                
                # GPU失败时尝试CPU模式
                if use_gpu:
                    self.logger.warning("GPU处理失败，尝试CPU模式...")
                    return self.process_single_task(task, False)
                
                self.stats['failed_tasks'] += 1
                return False
                
        except Exception as e:
            self.logger.error(f"处理任务时出错: {str(e)}")
            self.stats['failed_tasks'] += 1
            return False
        finally:
            task_time = time.time() - start_time
            self.stats['total_processing_time'] += task_time
    
    def process_all_tasks(self, tasks: List[TaskInfo], use_gpu: bool = False):
        """处理所有任务"""
        if not tasks:
            self.logger.warning("没有找到需要处理的任务")
            return
        
        self.stats['total_tasks'] = len(tasks)
        start_time = time.time()
        
        self.logger.info(f"开始处理 {len(tasks)} 个任务")
        if use_gpu and self.gpu_info['available']:
            self.logger.info(f"已启用GPU加速: {self.gpu_info.get('type', 'unknown')}")
        
        # 顺序处理所有任务
        for i, task in enumerate(tasks, 1):
            self.logger.info(f"进度: {i}/{len(tasks)} - {task.channel}/{task.video_name}/{task.language}")
            
            try:
                self.process_single_task(task, use_gpu)
            except KeyboardInterrupt:
                self.logger.warning("用户中断处理")
                break
            except Exception as e:
                self.logger.error(f"处理任务时发生未预期错误: {str(e)}")
                continue
        
        # 输出统计信息
        total_time = time.time() - start_time
        self._print_statistics(total_time)
    
    def _print_statistics(self, total_time: float):
        """打印处理统计信息"""
        self.logger.info("=" * 50)
        self.logger.info("处理统计信息:")
        self.logger.info(f"总任务数: {self.stats['total_tasks']}")
        self.logger.info(f"成功任务: {self.stats['successful_tasks']}")
        self.logger.info(f"失败任务: {self.stats['failed_tasks']}")
        self.logger.info(f"成功率: {self.stats['successful_tasks']/max(self.stats['total_tasks'], 1)*100:.1f}%")
        self.logger.info(f"总耗时: {total_time:.2f}秒")
        self.logger.info(f"I/O耗时: {self.stats['io_time']:.2f}秒")
        self.logger.info(f"编码耗时: {self.stats['encoding_time']:.2f}秒")
        if self.stats.get('duration_check_time', 0) > 0:
            self.logger.info(f"时长检查耗时: {self.stats['duration_check_time']:.2f}秒")
            self.logger.info(f"检查文件数: {self.stats['files_checked']}")
            self.logger.info(f"删除无效文件数: {self.stats['invalid_files_removed']}")
        if self.stats['successful_tasks'] > 0:
            avg_time = self.stats['total_processing_time'] / self.stats['successful_tasks']
            self.logger.info(f"平均处理时间: {avg_time:.2f}秒/任务")
        self.logger.info("=" * 50)
    
    def process_single_video(self, channel: str, video_name: str, languages: List[str], 
                           force: bool = False, use_gpu: bool = False):
        """处理单个视频的所有语言版本"""
        tasks = []
        
        # 验证语言支持
        valid_languages = [lang for lang in languages if lang in self.supported_languages]
        if not valid_languages:
            self.logger.error("没有指定任何有效的语言")
            return
        
        # 在处理单个视频前也进行时长验证
        if not force:
            self.logger.info(f"检查视频 {channel}/{video_name} 的输出文件...")
            removed_count = 0
            
            for language in valid_languages:
                output_video_path = self.output_mp4_path / channel / language / f"{video_name}.mp4"
                input_video_path = self.input_mp4_path / channel / language / f"{video_name}.mp4"
                
                if (output_video_path.exists() and input_video_path.exists() and 
                    not self.check_output_file_validity(str(input_video_path), str(output_video_path))):
                    self.logger.info(f"删除无效输出文件: {output_video_path}")
                    try:
                        output_video_path.unlink()
                        removed_count += 1
                    except Exception as e:
                        self.logger.error(f"删除文件失败 {output_video_path}: {str(e)}")
            
            if removed_count > 0:
                self.logger.info(f"删除了 {removed_count} 个无效文件")
        
        for language in valid_languages:
            # 构建路径
            input_video_path = self.input_mp4_path / channel / language / f"{video_name}.mp4"
            input_srt_path = self.input_srt_path / channel / language / f"{video_name}.srt"
            output_video_path = self.output_mp4_path / channel / language / f"{video_name}.mp4"
            
            # 检查文件是否存在
            if not input_video_path.exists():
                self.logger.warning(f"输入视频不存在: {input_video_path}")
                continue
            
            if not input_srt_path.exists():
                self.logger.warning(f"输入字幕不存在: {input_srt_path}")
                continue
            
            # 检查是否需要处理
            if output_video_path.exists() and not force:
                self.logger.info(f"输出文件已存在，跳过: {output_video_path}")
                continue
            
            task = TaskInfo(
                channel=channel,
                video_name=video_name,
                language=language,
                input_video_path=str(input_video_path),
                input_srt_path=str(input_srt_path),
                output_video_path=str(output_video_path),
                video_size=input_video_path.stat().st_size if input_video_path.exists() else 0
            )
            tasks.append(task)
        
        if tasks:
            self.process_all_tasks(tasks, use_gpu)
        else:
            self.logger.warning("没有找到需要处理的任务")


def main():
    """主函数"""
    processor = OptimizedSubtitleProcessor()
    
    # 检查必要工具
    if not processor.check_required_tools():
        sys.exit(1)
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="为多语言视频添加字幕 - 优化版本")
    
    parser.add_argument(
        "-l", "--languages",
        nargs="+",
        choices=processor.supported_languages,
        default=processor.supported_languages,
        help=f"目标语言列表 (默认: {' '.join(processor.supported_languages)})"
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="强制重新生成，即使输出文件已存在"
    )
    parser.add_argument(
        "-s", "--single",
        type=str,
        help="只处理指定的单个视频，格式: 频道名/视频名"
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="使用GPU加速ffmpeg处理"
    )
    
    # 解析命令行参数
    args = parser.parse_args()
    
    try:
        if args.single:
            # 处理单个视频
            if "/" not in args.single:
                processor.logger.error("错误: 单个视频参数格式应为 '频道名/视频名'")
                return
            
            channel, video_name = args.single.split("/", 1)
            processor.logger.info(f"处理单个视频: {channel}/{video_name}")
            
            processor.process_single_video(
                channel, video_name, args.languages, args.force, args.gpu
            )
        else:
            # 处理所有视频
            processor.logger.info("开始批量处理所有视频...")
            tasks = processor.collect_all_tasks(args.languages, args.force)
            processor.process_all_tasks(tasks, args.gpu)
    
    except KeyboardInterrupt:
        processor.logger.info("用户中断程序")
    except Exception as e:
        processor.logger.error(f"程序执行出错: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
