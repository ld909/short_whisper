#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音视频字幕同步测试工具

功能说明:
此脚本用于检测视频中的音频和字幕是否同步，特别是定位随时间累积的同步偏差问题。
该工具可以分析三个主要环节可能出现的同步问题：
1. 字幕生成阶段 (generate_subtitles.py 生成的SRT文件时间戳是否准确)
2. 字幕烧录阶段 (add_subtitles_to_mp4.py 添加字幕到无声视频时是否正确)
3. 音频合并阶段 (merge_mp4_mp3.py 合并有字幕视频和音频时是否同步)

使用方法:
python video_subtitle_sync_test.py -c <频道名> -l <语言> -f <文件名> [--verbose] [--analyze-all] [--fix]

参数说明:
-c, --channel        指定要检测的频道名
-l, --language       指定要检测的语言
-f, --file           指定要检测的文件名
--verbose            启用详细输出模式
--analyze-all        分析所有环节，而不仅仅是最终结果
--fix                尝试修复检测到的同步问题
--extract-section    提取问题区域进行分析，格式为"开始时间-结束时间"(秒)，例如"10-20"
"""

import os
import sys
import argparse
import subprocess
import platform
import re
import json
import tempfile
from datetime import timedelta
import matplotlib.pyplot as plt
import numpy as np
from pydub import AudioSegment
import pysrt


def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # Mac OS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 基础路径
BASE_PATH = get_base_path()

# 各阶段文件目录
MP3_BASE_DIR = f"{BASE_PATH}/merge_multi_lange_mp3"  # 音频文件目录
MP4_SILENT_DIR = f"{BASE_PATH}/mp4_merge_silient"    # 无声视频目录
MP4_SUBTITLED_DIR = f"{BASE_PATH}/mp4_multi_with_subtitles"  # 带字幕无声视频目录
MP4_WITH_AUDIO_DIR = f"{BASE_PATH}/mp4_with_audio"   # 最终带字幕和音频的视频目录
SRT_BASE_DIR = f"{BASE_PATH}/multi_lang_srt"         # SRT字幕文件目录
TXT_BASE_DIR = f"{BASE_PATH}/multi_lang_txt"         # 原始文本文件目录

# 是否启用详细输出
VERBOSE = False


def run_command(cmd):
    """执行命令并返回输出"""
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"执行命令失败: {e}")
        print(f"错误输出: {e.stderr}")
        return None
    except Exception as e:
        print(f"执行命令时出错: {e}")
        return None


def get_media_duration(file_path):
    """获取媒体文件的时长(秒)"""
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 {file_path}")
        return None

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    
    duration_str = run_command(cmd)
    if duration_str:
        try:
            return float(duration_str)
        except ValueError:
            print(f"无法解析时长: {duration_str}")
    return None


def check_duration_consistency(channel, language, file_name):
    """检查不同阶段文件的时长一致性"""
    print(f"\n检查文件 {channel}/{language}/{file_name} 的时长一致性:")
    
    mp3_file = os.path.join(MP3_BASE_DIR, channel, language, f"{file_name}.mp3")
    mp4_silent_file = os.path.join(MP4_SILENT_DIR, channel, language, f"{file_name}.mp4")
    mp4_subtitled_file = os.path.join(MP4_SUBTITLED_DIR, channel, language, f"{file_name}.mp4")
    mp4_with_audio_file = os.path.join(MP4_WITH_AUDIO_DIR, channel, language, f"{file_name}.mp4")
    
    durations = {}
    file_paths = {
        "音频文件 (MP3)": mp3_file,
        "无声视频 (MP4)": mp4_silent_file,
        "带字幕无声视频 (MP4)": mp4_subtitled_file,
        "最终视频 (MP4)": mp4_with_audio_file
    }
    
    for desc, path in file_paths.items():
        if os.path.exists(path):
            duration = get_media_duration(path)
            durations[desc] = duration
            print(f"{desc}: {duration:.3f}秒")
        else:
            print(f"{desc}: 文件不存在")
    
    # 检查时长是否一致
    ref_duration = durations.get("音频文件 (MP3)")
    if ref_duration is not None:
        print("\n时长差异分析:")
        for desc, duration in durations.items():
            if desc != "音频文件 (MP3)" and duration is not None:
                diff = duration - ref_duration
                percent = (diff / ref_duration) * 100 if ref_duration > 0 else 0
                print(f"{desc} vs 音频: {diff:.3f}秒 ({percent:.2f}%)")
                if abs(diff) > 0.5:  # 超过0.5秒的差异
                    if diff > 0:
                        print(f"  ⚠️ {desc}比音频长 - 可能会导致字幕提前结束")
                    else:
                        print(f"  ⚠️ {desc}比音频短 - 可能会导致音频在没有字幕的情况下继续播放")
    
    return durations


def parse_srt_file(srt_path):
    """解析SRT文件并返回字幕项列表"""
    if not os.path.exists(srt_path):
        print(f"错误: SRT文件不存在 {srt_path}")
        return None
    
    try:
        subs = pysrt.open(srt_path)
        return subs
    except Exception as e:
        print(f"解析SRT文件时出错: {e}")
        return None


def extract_audio_from_video(video_path, output_path):
    """从视频中提取音频"""
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vn",  # 不处理视频
        "-acodec", "pcm_s16le",  # 使用PCM格式
        "-ar", "44100",  # 采样率
        "-y",  # 覆盖已有文件
        output_path
    ]
    
    return run_command(cmd) is not None


def check_subtitle_timing(channel, language, file_name):
    """检查SRT字幕时间戳是否合理"""
    print(f"\n分析SRT字幕时间戳:")
    
    srt_path = os.path.join(SRT_BASE_DIR, channel, language, f"{file_name}.srt")
    mp3_path = os.path.join(MP3_BASE_DIR, channel, language, f"{file_name}.mp3")
    
    if not os.path.exists(srt_path):
        print(f"错误: SRT文件不存在 {srt_path}")
        return False
    
    if not os.path.exists(mp3_path):
        print(f"错误: MP3文件不存在 {mp3_path}")
        return False
    
    # 解析SRT文件
    subs = parse_srt_file(srt_path)
    if subs is None:
        return False
    
    # 获取MP3时长
    mp3_duration = get_media_duration(mp3_path)
    if mp3_duration is None:
        return False
    
    # 分析字幕时间戳
    subtitle_count = len(subs)
    last_end_time = subs[-1].end.ordinal / 1000.0  # 转换为秒
    
    print(f"字幕数量: {subtitle_count}")
    print(f"MP3时长: {mp3_duration:.3f}秒")
    print(f"最后字幕结束时间: {last_end_time:.3f}秒")
    
    # 检查字幕时长是否覆盖整个音频
    time_diff = mp3_duration - last_end_time
    if abs(time_diff) > 1.0:  # 允许1秒的误差
        print(f"⚠️ 字幕时长与音频时长不匹配, 差异: {time_diff:.3f}秒")
        if time_diff > 0:
            print(f"  音频结束后没有字幕，可能导致最后部分内容没有字幕")
        else:
            print(f"  字幕比音频长，最后的字幕可能无法显示")
    else:
        print(f"✓ 字幕时长与音频时长匹配良好，差异: {time_diff:.3f}秒")
    
    # 分析字幕间隔
    if subtitle_count > 1:
        gaps = []
        for i in range(1, subtitle_count):
            prev_end = subs[i-1].end.ordinal / 1000.0
            curr_start = subs[i].start.ordinal / 1000.0
            gap = curr_start - prev_end
            gaps.append(gap)
            
            if VERBOSE and gap > 0.3:  # 间隔超过0.3秒才报告
                print(f"字幕 {i-1} 和 {i} 之间的间隔: {gap:.3f}秒")
        
        avg_gap = sum(gaps) / len(gaps)
        max_gap = max(gaps)
        print(f"平均字幕间隔: {avg_gap:.3f}秒")
        print(f"最大字幕间隔: {max_gap:.3f}秒")
        
        if max_gap > 1.0:  # 超过1秒的间隔可能是问题
            print(f"⚠️ 检测到较大的字幕间隔 ({max_gap:.3f}秒)，可能有内容缺失")
    
    return True


def analyze_audio_speech_patterns(channel, language, file_name):
    """分析音频中的语音模式，检测是否与字幕同步"""
    print(f"\n分析音频语音模式:")
    
    mp3_path = os.path.join(MP3_BASE_DIR, channel, language, f"{file_name}.mp3")
    mp4_with_audio_path = os.path.join(MP4_WITH_AUDIO_DIR, channel, language, f"{file_name}.mp4")
    srt_path = os.path.join(SRT_BASE_DIR, channel, language, f"{file_name}.srt")
    
    if not os.path.exists(mp3_path):
        print(f"错误: MP3文件不存在 {mp3_path}")
        return False
        
    if not os.path.exists(srt_path):
        print(f"错误: SRT文件不存在 {srt_path}")
        return False
    
    # 解析SRT文件
    subs = parse_srt_file(srt_path)
    if subs is None:
        return False
    
    try:
        # 使用临时文件以避免文件名问题
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
            temp_wav_path = temp_wav.name
            
        # 从MP3提取音频
        print("从MP3提取音频波形...")
        if not extract_audio_from_video(mp3_path, temp_wav_path):
            print("提取音频失败")
            os.unlink(temp_wav_path)
            return False
            
        # 加载音频文件
        audio = AudioSegment.from_wav(temp_wav_path)
        audio_duration = len(audio) / 1000.0  # 转换为秒
        
        # 创建音频的强度图
        print("分析音频强度...")
        chunk_size = 100  # 毫秒
        chunks = [audio[i:i+chunk_size] for i in range(0, len(audio), chunk_size)]
        intensities = [chunk.dBFS for chunk in chunks]
        
        # 创建时间轴（以秒为单位）
        times = [i * (chunk_size / 1000.0) for i in range(len(intensities))]
        
        # 为字幕创建标记
        subtitle_marks = []
        for sub in subs:
            start_time = sub.start.ordinal / 1000.0  # 转换为秒
            end_time = sub.end.ordinal / 1000.0
            subtitle_marks.append((start_time, end_time, sub.text))
        
        # 创建图表
        plt.figure(figsize=(15, 8))
        
        # 绘制音频强度
        plt.plot(times, intensities, label='音频强度(dB)', color='blue', alpha=0.7)
        
        # 添加字幕标记
        for start, end, text in subtitle_marks:
            if start < audio_duration and end < audio_duration:
                plt.axvspan(start, end, alpha=0.2, color='green')
                if VERBOSE:
                    mid = (start + end) / 2
                    plt.text(mid, min(intensities) + 5, text[:20] + "..." if len(text) > 20 else text, 
                             fontsize=8, rotation=0, ha='center')
        
        plt.title(f"音频强度与字幕时间对比 - {file_name}")
        plt.xlabel("时间 (秒)")
        plt.ylabel("音频强度 (dB)")
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # 保存图表到文件
        output_dir = "sync_analysis"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_file = os.path.join(output_dir, f"{channel}_{language}_{file_name}_audio_analysis.png")
        plt.savefig(output_file)
        print(f"音频分析图表已保存到：{output_file}")
        
        # 分析语音段与字幕的同步性
        silence_threshold = -30  # dB，低于此值视为静音
        speech_segments = []
        in_speech = False
        speech_start = 0
        
        for i, intensity in enumerate(intensities):
            time = times[i]
            if intensity > silence_threshold and not in_speech:
                in_speech = True
                speech_start = time
            elif intensity <= silence_threshold and in_speech:
                in_speech = False
                speech_segments.append((speech_start, time))
        
        # 如果最后在语音中，添加最后一段
        if in_speech:
            speech_segments.append((speech_start, times[-1]))
        
        # 比较语音段与字幕
        if VERBOSE:
            print("\n语音段与字幕比较:")
            for i, (speech_start, speech_end) in enumerate(speech_segments):
                print(f"语音段 {i+1}: {speech_start:.2f}s - {speech_end:.2f}s (时长: {speech_end-speech_start:.2f}s)")
                
                # 查找与此语音段重叠的字幕
                overlapping_subs = []
                for sub in subs:
                    sub_start = sub.start.ordinal / 1000.0
                    sub_end = sub.end.ordinal / 1000.0
                    
                    if (sub_start <= speech_end and sub_end >= speech_start):
                        overlapping_subs.append((sub_start, sub_end, sub.text))
                
                if overlapping_subs:
                    for j, (sub_start, sub_end, text) in enumerate(overlapping_subs):
                        overlap_start = max(speech_start, sub_start)
                        overlap_end = min(speech_end, sub_end)
                        overlap_duration = overlap_end - overlap_start
                        speech_duration = speech_end - speech_start
                        overlap_percent = (overlap_duration / speech_duration) * 100
                        
                        print(f"  字幕 {j+1}: {sub_start:.2f}s - {sub_end:.2f}s")
                        print(f"    重叠: {overlap_start:.2f}s - {overlap_end:.2f}s ({overlap_percent:.1f}% 的语音段)")
                        print(f"    文本: {text}")
                else:
                    print("  没有找到与此语音段重叠的字幕")
        
        # 清理临时文件
        os.unlink(temp_wav_path)
        
        return True
    except Exception as e:
        print(f"分析音频语音模式时出错: {e}")
        # 清理临时文件
        if os.path.exists(temp_wav_path):
            os.unlink(temp_wav_path)
        return False


def extract_section_for_analysis(channel, language, file_name, start_time, end_time):
    """提取视频和音频的特定部分进行分析"""
    print(f"\n提取时间段 {start_time}s - {end_time}s 进行详细分析:")
    
    mp4_with_audio_path = os.path.join(MP4_WITH_AUDIO_DIR, channel, language, f"{file_name}.mp4")
    mp3_path = os.path.join(MP3_BASE_DIR, channel, language, f"{file_name}.mp3")
    srt_path = os.path.join(SRT_BASE_DIR, channel, language, f"{file_name}.srt")
    
    output_dir = "sync_analysis"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    duration = end_time - start_time
    
    # 提取视频段
    if os.path.exists(mp4_with_audio_path):
        output_video = os.path.join(output_dir, f"{channel}_{language}_{file_name}_{start_time}-{end_time}.mp4")
        cmd = [
            "ffmpeg",
            "-ss", str(start_time),
            "-i", mp4_with_audio_path,
            "-t", str(duration),
            "-c:v", "copy",
            "-c:a", "copy",
            "-y", output_video
        ]
        if run_command(cmd):
            print(f"已提取视频段到: {output_video}")
    
    # 提取音频段
    if os.path.exists(mp3_path):
        output_audio = os.path.join(output_dir, f"{channel}_{language}_{file_name}_{start_time}-{end_time}.mp3")
        cmd = [
            "ffmpeg",
            "-ss", str(start_time),
            "-i", mp3_path,
            "-t", str(duration),
            "-c:a", "copy",
            "-y", output_audio
        ]
        if run_command(cmd):
            print(f"已提取音频段到: {output_audio}")
    
    # 提取字幕段
    if os.path.exists(srt_path):
        output_srt = os.path.join(output_dir, f"{channel}_{language}_{file_name}_{start_time}-{end_time}.srt")
        subs = parse_srt_file(srt_path)
        if subs:
            # 过滤字幕
            section_subs = []
            for sub in subs:
                sub_start = sub.start.ordinal / 1000.0
                sub_end = sub.end.ordinal / 1000.0
                
                if sub_start >= start_time and sub_end <= end_time:
                    # 完全在区间内的字幕
                    adjusted_sub = sub.copy()
                    adjusted_sub.start = sub.start - pysrt.SubRipTime(seconds=int(start_time))
                    adjusted_sub.end = sub.end - pysrt.SubRipTime(seconds=int(start_time))
                    section_subs.append(adjusted_sub)
                elif sub_start < start_time and sub_end > start_time:
                    # 起始在区间外，结束在区间内的字幕
                    adjusted_sub = sub.copy()
                    adjusted_sub.start = pysrt.SubRipTime(seconds=0)
                    adjusted_sub.end = sub.end - pysrt.SubRipTime(seconds=int(start_time))
                    section_subs.append(adjusted_sub)
                elif sub_start < end_time and sub_end > end_time:
                    # 起始在区间内，结束在区间外的字幕
                    adjusted_sub = sub.copy()
                    adjusted_sub.start = sub.start - pysrt.SubRipTime(seconds=int(start_time))
                    adjusted_sub.end = pysrt.SubRipTime(seconds=int(duration))
                    section_subs.append(adjusted_sub)
            
            # 保存提取的字幕
            if section_subs:
                section_srt = pysrt.SubRipFile()
                for i, sub in enumerate(section_subs, 1):
                    sub.index = i
                    section_srt.append(sub)
                
                section_srt.save(output_srt, encoding='utf-8')
                print(f"已提取字幕段到: {output_srt}")
                
                # 为提取的片段生成带字幕的视频
                if os.path.exists(output_video):
                    output_subtitled = os.path.join(output_dir, f"{channel}_{language}_{file_name}_{start_time}-{end_time}_with_subs.mp4")
                    cmd = [
                        "ffmpeg",
                        "-i", output_video,
                        "-vf", f"subtitles={output_srt}",
                        "-c:a", "copy",
                        "-y", output_subtitled
                    ]
                    if run_command(cmd):
                        print(f"已生成带字幕的提取视频: {output_subtitled}")


def main():
    parser = argparse.ArgumentParser(description="检测视频音频和字幕同步问题")
    parser.add_argument("-c", "--channel", required=True, help="指定要检测的频道名")
    parser.add_argument("-l", "--language", required=True, help="指定要检测的语言")
    parser.add_argument("-f", "--file", required=True, help="指定要检测的文件名")
    parser.add_argument("--verbose", action="store_true", help="启用详细输出模式")
    parser.add_argument("--analyze-all", action="store_true", help="分析所有环节，而不仅仅是最终结果")
    parser.add_argument("--extract-section", help="提取问题区域进行分析，格式为'开始时间-结束时间'(秒)")
    
    args = parser.parse_args()
    
    global VERBOSE
    VERBOSE = args.verbose
    
    # 移除文件名中的扩展名
    file_name = args.file
    if "." in file_name:
        file_name = file_name.rsplit(".", 1)[0]
    
    print(f"开始分析 {args.channel}/{args.language}/{file_name} 的音视频字幕同步问题")
    
    # 检查时长一致性
    durations = check_duration_consistency(args.channel, args.language, file_name)
    
    # 如果指定了提取特定区域
    if args.extract_section:
        try:
            start_time, end_time = map(float, args.extract_section.split("-"))
            extract_section_for_analysis(args.channel, args.language, file_name, start_time, end_time)
        except ValueError:
            print(f"错误: 无效的区间格式 '{args.extract_section}'，应为'开始时间-结束时间'")
    
    # 如果指定了分析所有环节
    if args.analyze_all:
        # 检查SRT字幕时间戳
        check_subtitle_timing(args.channel, args.language, file_name)
        
        # 分析音频语音模式
        analyze_audio_speech_patterns(args.channel, args.language, file_name)


if __name__ == "__main__":
    main() 