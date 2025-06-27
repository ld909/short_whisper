#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MP4文件损坏检查和修复脚本
-----------------------
这个脚本用于检查MP4文件是否损坏，如果发现损坏的文件，会自动调用add_subtitles_to_mp4.py重新生成，
然后再调用merge_mp4_mp3.py进行合并。主要用于为merge_mp4_mp3.py提供兜底保障。

功能:
1. 检查指定目录下的MP4文件是否损坏
2. 对损坏的MP4文件，调用add_subtitles_to_mp4.py重新生成
3. 重新生成后，调用merge_mp4_mp3.py进行MP4和MP3的合并
4. 自动排除Mac系统产生的点文件(.DS_Store等)

目录结构:
- MP4文件目录: /Volumes/dhl/buda_videos_youtube/mp4_multi_with_subtitles/频道名/语言/
- Linux系统基础路径: /media/dhl/buda_videos_youtube

使用方法:
python check_and_repair_damaged_mp4.py [-c CHANNEL] [-l LANGUAGE] [--dry-run] [--gpu]

参数说明:
- -c, --channel: 指定要检查的频道名
- -l, --language: 指定要检查的语言
- --dry-run: 只检查不修复，显示损坏的文件列表
- --gpu: 使用GPU加速重新生成和合并过程
- --deep-check: 进行深度检查，包括播放兼容性测试
- --list-channels: 列出所有可用频道
- --list-languages: 列出指定频道的所有可用语言
"""

import os
import sys
import argparse
import platform
import subprocess
import glob
import time
import json
from pathlib import Path


def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # Mac OS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 基础路径
BASE_PATH = get_base_path()

# 目录配置
MP4_BASE_DIR = f"{BASE_PATH}/mp4_multi_with_subtitles"
MP3_BASE_DIR = f"{BASE_PATH}/merge_multi_lange_mp3"
OUTPUT_BASE_DIR = f"{BASE_PATH}/mp4_with_audio"

# 添加输入路径配置
INPUT_MP4_PATH = f"{BASE_PATH}/mp4_merge_silient"
INPUT_SRT_PATH = f"{BASE_PATH}/multi_lang_srt"

# 脚本路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ADD_SUBTITLES_SCRIPT = os.path.join(SCRIPT_DIR, "add_subtitles_to_mp4.py")
MERGE_SCRIPT = os.path.join(SCRIPT_DIR, "merge_mp4_mp3.py")


def is_mac_hidden_file(filename):
    """检查是否为Mac系统产生的隐藏文件"""
    hidden_patterns = [
        ".DS_Store",
        "._",
        ".Spotlight-V100",
        ".Trashes",
        ".fseventsd",
        ".TemporaryItems",
        ".VolumeIcon.icns",
    ]
    
    for pattern in hidden_patterns:
        if filename.startswith(pattern):
            return True
    return False


def check_mp4_integrity(mp4_file):
    """检查MP4文件是否损坏"""
    try:
        # 使用ffprobe检查文件完整性
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,duration",
            "-of", "csv=p=0",
            mp4_file
        ]
        
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"❌ 损坏的MP4文件: {os.path.basename(mp4_file)}")
            print(f"   错误信息: {result.stderr.strip()}")
            return False
        
        # 检查是否有有效的视频流
        output = result.stdout.strip()
        if not output or "," not in output:
            print(f"❌ 损坏的MP4文件: {os.path.basename(mp4_file)} (无有效视频流)")
            return False
        
        codec, duration = output.split(",", 1)
        if not codec or float(duration) <= 0:
            print(f"❌ 损坏的MP4文件: {os.path.basename(mp4_file)} (无效编解码器或时长)")
            return False
        
        print(f"✅ 完好的MP4文件: {os.path.basename(mp4_file)} (时长: {float(duration):.2f}秒)")
        return True
        
    except subprocess.TimeoutExpired:
        print(f"❌ 损坏的MP4文件: {os.path.basename(mp4_file)} (检查超时)")
        return False
    except Exception as e:
        print(f"❌ 检查MP4文件时出错: {os.path.basename(mp4_file)} - {str(e)}")
        return False


def check_mp4_playability(mp4_file):
    """检查MP4文件是否可以正常播放（模拟VLC播放器的检查）"""
    try:
        print(f"🎬 检查播放兼容性: {os.path.basename(mp4_file)}")
        
        # 使用ffmpeg尝试解码视频的前几秒，这比ffprobe更严格
        cmd = [
            "ffmpeg",
            "-i", mp4_file,
            "-t", "5",  # 只检查前5秒
            "-f", "null",
            "-v", "error",
            "-"
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"✅ 文件可正常播放: {os.path.basename(mp4_file)}")
            return True
        else:
            print(f"❌ 文件播放异常: {os.path.basename(mp4_file)}")
            print(f"   播放错误: {result.stderr.strip()[:200]}...")  # 只显示前200字符
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ 播放检查超时: {os.path.basename(mp4_file)}")
        return False
    except Exception as e:
        print(f"❌ 播放检查出错: {os.path.basename(mp4_file)} - {str(e)}")
        return False


def comprehensive_mp4_check(mp4_file):
    """综合检查MP4文件的完整性和播放兼容性"""
    print(f"🔍 综合检查: {os.path.basename(mp4_file)}")
    
    # 基础检查
    if not check_mp4_integrity(mp4_file):
        return False
    
    # 播放兼容性检查
    return check_mp4_playability(mp4_file)


def deep_check_mp4_integrity(mp4_file):
    """深度检查MP4文件完整性"""
    print(f"🔬 深度检查文件: {os.path.basename(mp4_file)}")
    
    # 首先检查文件是否存在和大小
    if not os.path.exists(mp4_file):
        print(f"❌ 文件不存在: {mp4_file}")
        return False
    
    file_size = os.path.getsize(mp4_file)
    if file_size == 0:
        print(f"❌ 文件大小为0: {mp4_file}")
        return False
    
    print(f"📊 文件大小: {file_size / (1024*1024):.2f} MB")
    
    try:
        # 使用更详细的ffprobe检查
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration,size,bit_rate:stream=codec_name,width,height,duration",
            "-of", "json",
            mp4_file
        ]
        
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"❌ ffprobe检查失败: {result.stderr.strip()}")
            return False
        
        probe_data = json.loads(result.stdout)
        
        # 检查格式信息
        if 'format' not in probe_data:
            print(f"❌ 无法获取格式信息")
            return False
        
        format_info = probe_data['format']
        duration = float(format_info.get('duration', 0))
        
        if duration <= 0:
            print(f"❌ 无效的时长: {duration}")
            return False
        
        # 检查视频流
        streams = probe_data.get('streams', [])
        video_streams = [s for s in streams if s.get('codec_type') == 'video']
        
        if not video_streams:
            print(f"❌ 没有找到视频流")
            return False
        
        video_stream = video_streams[0]
        codec_name = video_stream.get('codec_name', '')
        width = video_stream.get('width', 0)
        height = video_stream.get('height', 0)
        
        print(f"✅ 视频信息: {codec_name}, {width}x{height}, {duration:.2f}秒")
        return True
        
    except subprocess.TimeoutExpired:
        print(f"❌ 深度检查超时")
        return False
    except json.JSONDecodeError:
        print(f"❌ 无法解析ffprobe输出")
        return False
    except Exception as e:
        print(f"❌ 深度检查出错: {str(e)}")
        return False


def regenerate_mp4_simple(channel, language, video_name):
    """使用简化方式重新生成损坏的MP4文件"""
    print(f"\n{'='*80}")
    print(f"🔧 【步骤1】使用简化方式重新生成MP4文件")
    print(f"📹 视频名称: {video_name}")
    print(f"📺 频道: {channel}")
    print(f"🌐 语言: {language}")
    print(f"{'='*80}")
    
    try:
        # 构建文件路径
        input_mp4 = os.path.join(INPUT_MP4_PATH, channel, language, f"{video_name}.mp4")
        input_srt = os.path.join(INPUT_SRT_PATH, channel, language, f"{video_name}.srt")
        output_mp4 = os.path.join(MP4_BASE_DIR, channel, language, f"{video_name}.mp4")
        
        print(f"📂 输入源文件目录:")
        print(f"   📹 原始MP4: {input_mp4}")
        print(f"   📄 字幕SRT: {input_srt}")
        print(f"📂 输出目标目录:")
        print(f"   🎬 带字幕MP4: {output_mp4}")
        
        # 检查输入文件是否存在
        if not os.path.exists(input_mp4):
            print(f"❌ 输入MP4文件不存在: {input_mp4}")
            return False
            
        if not os.path.exists(input_srt):
            print(f"❌ 输入SRT文件不存在: {input_srt}")
            return False
        
        print(f"✅ 输入文件检查通过")
        
        # 首先验证原始MP4文件是否确实完好
        print(f"🔍 验证原始MP4文件完整性...")
        if not check_mp4_integrity(input_mp4):
            print(f"❌ 原始MP4文件本身损坏，无法修复: {input_mp4}")
            return False
        print(f"✅ 原始MP4文件完好，继续处理")
        
        # 创建输出目录
        os.makedirs(os.path.dirname(output_mp4), exist_ok=True)
        print(f"📁 输出目录已准备就绪")
        
        # 删除现有的损坏文件
        if os.path.exists(output_mp4):
            print(f"🗑️ 删除现有损坏文件: {os.path.basename(output_mp4)}")
            os.remove(output_mp4)
        
        # 创建临时输出文件以避免路径编码问题
        temp_output = output_mp4 + ".tmp"
        
        # 使用简化的ffmpeg命令直接添加字幕
        # 注意：对于包含特殊字符的路径，使用绝对路径并确保正确编码
        cmd = [
            "ffmpeg",
            "-i", input_mp4,
            "-vf", f"subtitles='{input_srt}':force_style='FontSize=16,FontWeight=500,PrimaryColour=&Hffffff,OutlineColour=&H000000,BorderStyle=1,Outline=1,MarginV=20'",
            "-c:a", "copy",
            "-c:v", "libx264",
            "-preset", "fast", 
            "-crf", "23",
            "-movflags", "+faststart",  # 确保MP4文件结构正确
            "-avoid_negative_ts", "make_zero",  # 处理时间戳问题
            "-strict", "experimental",  # 允许实验性功能
            "-y",
            temp_output
        ]
        
        print(f"🔧 执行简化ffmpeg命令:")
        print(f"   命令: ffmpeg [添加字幕处理]")
        print(f"   处理方式: 直接在脚本内调用ffmpeg")
        print(f"   临时输出: {os.path.basename(temp_output)}")
        
        # 设置环境变量以处理编码问题
        env = os.environ.copy()
        env['LANG'] = 'en_US.UTF-8'
        env['LC_ALL'] = 'en_US.UTF-8'
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
        
        if result.returncode == 0:
            # 检查临时文件是否生成且有效
            if os.path.exists(temp_output) and os.path.getsize(temp_output) > 1024*1024:  # 至少1MB
                print(f"✅ ffmpeg处理成功，检查输出文件完整性...")
                
                # 验证生成的文件完整性
                if comprehensive_mp4_check(temp_output):
                    # 将临时文件移动到最终位置
                    os.rename(temp_output, output_mp4)
                    print(f"✅ 简化方式重新生成MP4成功且验证通过: {video_name}")
                    print(f"⏳ 等待文件写入完成...")
                    time.sleep(3)
                    return True
                else:
                    print(f"❌ 生成的文件损坏，删除临时文件")
                    if os.path.exists(temp_output):
                        os.remove(temp_output)
                    return False
            else:
                print(f"❌ 生成的文件太小或不存在")
                if os.path.exists(temp_output):
                    os.remove(temp_output)
                return False
        else:
            print(f"❌ 简化方式重新生成MP4失败: {video_name}")
            print(f"📤 标准输出: {result.stdout}")
            print(f"❗ 错误信息: {result.stderr}")
            # 清理临时文件
            if os.path.exists(temp_output):
                os.remove(temp_output)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ 简化方式重新生成MP4超时: {video_name}")
        # 清理临时文件
        temp_output = output_mp4 + ".tmp"
        if os.path.exists(temp_output):
            os.remove(temp_output)
        return False
    except Exception as e:
        print(f"❌ 简化方式重新生成MP4时出错: {str(e)}")
        # 清理临时文件
        temp_output = output_mp4 + ".tmp"
        if os.path.exists(temp_output):
            os.remove(temp_output)
        return False


def regenerate_mp4(channel, language, video_name, use_gpu=False):
    """重新生成损坏的MP4文件"""
    print(f"\n{'='*80}")
    print(f"🔧 【步骤1】开始重新生成损坏的MP4文件")
    print(f"📹 视频名称: {video_name}")
    print(f"📺 频道: {channel}")
    print(f"🌐 语言: {language}")
    print(f"{'='*80}")
    
    # 首先尝试简化方式
    print(f"🚀 尝试方式1: 简化ffmpeg处理")
    if regenerate_mp4_simple(channel, language, video_name):
        return True
    
    print(f"\n⚠️  简化方式失败，尝试方式2: 调用原始脚本")
    print(f"📜 调用脚本: {ADD_SUBTITLES_SCRIPT}")
    
    try:
        # 调用add_subtitles_to_mp4.py重新生成
        cmd = [
            sys.executable,
            ADD_SUBTITLES_SCRIPT,
            "-s", f"{channel}/{video_name}",
            "-l", language,
            "-f"  # 强制重新生成
        ]
        
        if use_gpu:
            cmd.append("--gpu")
            print(f"⚡ GPU加速: 已启用")
        
        print(f"🔧 执行命令:")
        print(f"   脚本: {ADD_SUBTITLES_SCRIPT}")
        print(f"   参数: -s {channel}/{video_name} -l {language} -f")
        print(f"   功能: 重新生成带字幕的MP4文件")
        print(f"   输出到: {MP4_BASE_DIR}/{channel}/{language}/")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 原始脚本重新生成MP4成功: {video_name}")
            print(f"⏳ 等待文件写入完成...")
            time.sleep(2)
            return True
        else:
            print(f"❌ 原始脚本重新生成MP4失败: {video_name}")
            print(f"📤 标准输出: {result.stdout}")
            print(f"❗ 错误信息: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 调用原始脚本时出错: {str(e)}")
        return False


def wait_for_file_ready(file_path, max_wait=10):
    """等待文件准备就绪，确保文件完全写入"""
    print(f"⏳ 等待文件准备就绪: {os.path.basename(file_path)}")
    
    for i in range(max_wait):
        if os.path.exists(file_path):
            try:
                # 尝试获取文件大小，如果文件正在写入会失败
                size = os.path.getsize(file_path)
                if size > 0:
                    # 再等待1秒确保文件完全写入
                    time.sleep(1)
                    final_size = os.path.getsize(file_path)
                    if final_size == size:
                        print(f"✅ 文件准备就绪: {final_size} 字节")
                        return True
            except (OSError, IOError):
                pass
        
        print(f"   等待中... ({i+1}/{max_wait})")
        time.sleep(1)
    
    print(f"⚠️ 文件等待超时")
    return False


def merge_mp4_mp3_file(channel, language, video_name, use_gpu=False):
    """合并MP4和MP3文件"""
    print(f"\n{'='*80}")
    print(f"🔗 【步骤2】开始合并MP4和MP3文件")
    print(f"📹 视频名称: {video_name}")
    print(f"📺 频道: {channel}")
    print(f"🌐 语言: {language}")
    print(f"{'='*80}")
    
    try:
        # 检查MP4和MP3文件是否存在
        mp4_file = os.path.join(MP4_BASE_DIR, channel, language, f"{video_name}.mp4")
        mp3_file = os.path.join(MP3_BASE_DIR, channel, language, f"{video_name}.mp3")
        output_file = os.path.join(OUTPUT_BASE_DIR, channel, language, f"{video_name}.mp4")
        
        print(f"📂 输入文件目录:")
        print(f"   🎬 带字幕MP4: {mp4_file}")
        print(f"   🎵 音频MP3: {mp3_file}")
        print(f"📂 输出目标目录:")
        print(f"   🎞️ 最终有声MP4: {output_file}")
        
        if not os.path.exists(mp4_file):
            print(f"❌ MP4文件不存在: {mp4_file}")
            return False
            
        if not os.path.exists(mp3_file):
            print(f"❌ MP3文件不存在: {mp3_file}")
            return False
        
        print(f"✅ 输入文件检查通过")
        
        # 调用merge_mp4_mp3.py进行合并
        cmd = [
            sys.executable,
            MERGE_SCRIPT,
            "-c", channel,
            "-l", language,
            "-f", video_name,
            "--force"  # 强制重新合并
        ]
        
        if use_gpu:
            cmd.append("--gpu")
            print(f"⚡ GPU加速: 已启用")
        
        print(f"🔧 执行合并命令:")
        print(f"   脚本: {MERGE_SCRIPT}")
        print(f"   参数: -c {channel} -l {language} -f {video_name} --force")
        print(f"   功能: 合并带字幕MP4和音频MP3")
        print(f"   输出到: {OUTPUT_BASE_DIR}/{channel}/{language}/")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ 成功合并MP4和MP3文件: {video_name}")
            print(f"🎞️ 最终有声视频已生成")
            return True
        else:
            print(f"❌ 合并MP4和MP3文件失败: {video_name}")
            print(f"📤 标准输出: {result.stdout}")
            print(f"❗ 错误信息: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ 合并MP4和MP3文件超时: {video_name}")
        return False
    except Exception as e:
        print(f"❌ 合并MP4和MP3文件时出错: {str(e)}")
        return False


def check_and_repair_channel_language(channel, language, dry_run=False, use_gpu=False, deep_check=False):
    """检查和修复指定频道和语言的所有MP4文件"""
    mp4_dir = os.path.join(MP4_BASE_DIR, channel, language)
    
    if not os.path.exists(mp4_dir):
        print(f"❌ 目录不存在: {mp4_dir}")
        return
    
    print(f"\n{'='*100}")
    print(f"🔍 开始检查MP4文件损坏情况")
    print(f"📁 检查目录: {mp4_dir}")
    print(f"📺 频道: {channel}")
    print(f"🌐 语言: {language}")
    print(f"{'='*100}")
    
    # 获取所有MP4文件
    mp4_files = []
    for file in os.listdir(mp4_dir):
        if file.endswith('.mp4') and not is_mac_hidden_file(file):
            mp4_files.append(os.path.join(mp4_dir, file))
    
    if not mp4_files:
        print(f"📂 目录中没有找到MP4文件")
        return
    
    print(f"📊 找到 {len(mp4_files)} 个MP4文件，开始逐个检查...")
    
    damaged_files = []
    repaired_files = []
    
    # 检查每个MP4文件
    for mp4_file in sorted(mp4_files):
        video_name = os.path.splitext(os.path.basename(mp4_file))[0]
        
        # 根据用户选择使用不同的检查方法
        if deep_check:
            if not comprehensive_mp4_check(mp4_file):
                damaged_files.append((mp4_file, video_name))
        else:
            if not check_mp4_integrity(mp4_file):
                damaged_files.append((mp4_file, video_name))
    
    if not damaged_files:
        print(f"\n🎉 所有MP4文件都完好无损！")
        return
    
    print(f"\n{'='*100}")
    print(f"⚠️  发现 {len(damaged_files)} 个损坏的MP4文件")
    print(f"{'='*100}")
    
    if dry_run:
        print("🔍 仅检查模式，不进行修复。损坏的文件列表:")
        for mp4_file, video_name in damaged_files:
            print(f"   - {video_name}")
        return
    
    # 修复损坏的文件
    print(f"🔧 开始修复损坏的MP4文件...")
    print(f"📋 修复流程说明:")
    print(f"   步骤1: 重新生成带字幕MP4 (from mp4_merge_silient + multi_lang_srt → mp4_multi_with_subtitles)")
    print(f"   步骤2: 验证修复后文件完整性")
    print(f"   步骤3: 合并MP4和MP3 (from mp4_multi_with_subtitles + merge_multi_lange_mp3 → mp4_with_audio)")
    
    for i, (mp4_file, video_name) in enumerate(damaged_files, 1):
        print(f"\n{'='*100}")
        print(f"🔧 修复进度: [{i}/{len(damaged_files)}]")
        print(f"📹 修复文件: {video_name}")
        print(f"{'='*100}")
        
        # 步骤1: 重新生成MP4文件
        if regenerate_mp4(channel, language, video_name, use_gpu):
            # 步骤2: 等待文件准备就绪
            print(f"\n⏳ 检查文件是否准备就绪...")
            if wait_for_file_ready(mp4_file, max_wait=15):
                # 步骤3: 重新验证修复后的文件完整性
                print(f"🔍 重新验证修复后的文件完整性...")
                if os.path.exists(mp4_file) and comprehensive_mp4_check(mp4_file):
                    print(f"✅ 修复后的文件验证通过: {video_name}")
                    
                    # 步骤4: 尝试合并MP4和MP3
                    if merge_mp4_mp3_file(channel, language, video_name, use_gpu):
                        repaired_files.append(video_name)
                        print(f"\n🎉 完成修复和合并: {video_name}")
                    else:
                        print(f"\n⚠️ 合并失败，但MP4文件已修复: {video_name}")
                        # 即使合并失败，也算作部分成功
                        repaired_files.append(video_name)
                        print(f"💡 MP4文件已修复，建议手动检查合并结果")
                else:
                    print(f"❌ 修复后的文件仍然损坏或不存在: {video_name}")
                    # 检查原始文件是否有问题
                    input_mp4 = os.path.join(INPUT_MP4_PATH, channel, language, f"{video_name}.mp4")
                    input_srt = os.path.join(INPUT_SRT_PATH, channel, language, f"{video_name}.srt")
                    print(f"🗑️ 建议手动检查以下源文件:")
                    print(f"   - 原始视频: {input_mp4}")
                    print(f"   - 字幕文件: {input_srt}")
                    if os.path.exists(input_mp4):
                        print(f"   - 原始视频完整性: {'✅ 完好' if check_mp4_integrity(input_mp4) else '❌ 损坏'}")
                    if os.path.exists(input_srt):
                        srt_size = os.path.getsize(input_srt)
                        print(f"   - 字幕文件大小: {srt_size} 字节")
            else:
                print(f"❌ 文件未准备就绪: {video_name}")
        else:
            print(f"❌ 重新生成失败: {video_name}")
    
    # 总结
    print(f"\n{'='*100}")
    print(f"📊 修复完成总结")
    print(f"{'='*100}")
    print(f"📁 检查目录: {mp4_dir}")
    print(f"📊 总共检查: {len(mp4_files)} 个文件")
    print(f"⚠️  发现损坏: {len(damaged_files)} 个文件")
    print(f"✅ 成功修复: {len(repaired_files)} 个文件")
    print(f"❌ 修复失败: {len(damaged_files) - len(repaired_files)} 个文件")
    
    if repaired_files:
        print(f"\n✅ 成功修复的文件:")
        for video_name in repaired_files:
            print(f"   - {video_name}")
    
    failed_files = [video_name for _, video_name in damaged_files if video_name not in repaired_files]
    if failed_files:
        print(f"\n❌ 修复失败的文件:")
        for video_name in failed_files:
            print(f"   - {video_name}")
            
    print(f"\n💡 故障排除建议:")
    print(f"   1. 对于修复失败的文件，请检查原始源文件是否完好")
    print(f"   2. 验证字幕文件格式是否正确（UTF-8编码）")
    print(f"   3. 确保ffmpeg支持字幕处理功能")
    print(f"   4. 检查磁盘空间是否充足")
    
    print(f"\n📂 相关目录说明:")
    print(f"   📹 原始MP4: {INPUT_MP4_PATH}")
    print(f"   📄 字幕SRT: {INPUT_SRT_PATH}")
    print(f"   🎬 带字幕MP4: {MP4_BASE_DIR}")
    print(f"   🎵 音频MP3: {MP3_BASE_DIR}")
    print(f"   🎞️ 最终有声MP4: {OUTPUT_BASE_DIR}")


def list_channels():
    """列出所有可用的频道"""
    if not os.path.exists(MP4_BASE_DIR):
        print(f"❌ MP4基础目录不存在: {MP4_BASE_DIR}")
        return
    
    channels = []
    for item in os.listdir(MP4_BASE_DIR):
        if os.path.isdir(os.path.join(MP4_BASE_DIR, item)) and not is_mac_hidden_file(item):
            channels.append(item)
    
    if channels:
        print("📺 可用的频道:")
        for channel in sorted(channels):
            print(f"   - {channel}")
    else:
        print("📂 没有找到任何频道")


def list_languages(channel):
    """列出指定频道的所有可用语言"""
    channel_dir = os.path.join(MP4_BASE_DIR, channel)
    
    if not os.path.exists(channel_dir):
        print(f"❌ 频道目录不存在: {channel_dir}")
        return
    
    languages = []
    for item in os.listdir(channel_dir):
        if os.path.isdir(os.path.join(channel_dir, item)) and not is_mac_hidden_file(item):
            languages.append(item)
    
    if languages:
        print(f"🌐 频道 '{channel}' 的可用语言:")
        for language in sorted(languages):
            print(f"   - {language}")
    else:
        print(f"📂 频道 '{channel}' 没有找到任何语言")


def main():
    parser = argparse.ArgumentParser(
        description="检查和修复损坏的MP4文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有频道
  python check_and_repair_damaged_mp4.py --list-channels
  
  # 列出频道'buddha'的所有语言
  python check_and_repair_damaged_mp4.py --list-languages buddha
  
  # 检查频道'buddha'下语言'english'的所有MP4文件
  python check_and_repair_damaged_mp4.py -c buddha -l english
  
  # 只检查不修复，显示损坏文件列表
  python check_and_repair_damaged_mp4.py -c buddha -l english --dry-run
  
  # 使用GPU加速修复过程
  python check_and_repair_damaged_mp4.py -c buddha -l english --gpu
  
  # 进行深度检查，包括播放兼容性测试
  python check_and_repair_damaged_mp4.py -c buddha -l english --deep-check
  
  # 组合选项：深度检查 + GPU加速
  python check_and_repair_damaged_mp4.py -c buddha -l english --deep-check --gpu
        """
    )
    
    parser.add_argument("-c", "--channel", help="指定要检查的频道名")
    parser.add_argument("-l", "--language", help="指定要检查的语言")
    parser.add_argument("--dry-run", action="store_true", help="只检查不修复，显示损坏的文件列表")
    parser.add_argument("--gpu", action="store_true", help="使用GPU加速重新生成和合并过程")
    parser.add_argument("--deep-check", action="store_true", help="进行深度检查，包括播放兼容性测试")
    parser.add_argument("--list-channels", action="store_true", help="列出所有可用频道")
    parser.add_argument("--list-languages", help="列出指定频道的所有可用语言")
    
    args = parser.parse_args()
    
    # 检查必要的脚本是否存在
    if not os.path.exists(ADD_SUBTITLES_SCRIPT):
        print(f"❌ 找不到字幕添加脚本: {ADD_SUBTITLES_SCRIPT}")
        sys.exit(1)
    
    if not os.path.exists(MERGE_SCRIPT):
        print(f"❌ 找不到合并脚本: {MERGE_SCRIPT}")
        sys.exit(1)
    
    # 处理命令行参数
    if args.list_channels:
        list_channels()
        return
    
    if args.list_languages:
        list_languages(args.list_languages)
        return
    
    if not args.channel or not args.language:
        print("❌ 请指定频道名和语言，或使用 --list-channels 查看可用频道")
        parser.print_help()
        sys.exit(1)
    
    # 打印脚本信息和配置
    print(f"\n{'='*120}")
    print(f"🔍 MP4文件损坏检查和修复工具")
    print(f"{'='*120}")
    print(f"📋 脚本功能说明:")
    print(f"   1. 检查指定目录下的MP4文件是否损坏")
    print(f"   2. 对损坏的MP4文件，重新生成带字幕的MP4")
    print(f"   3. 将重新生成的MP4与音频MP3合并成最终有声视频")
    print(f"   4. 为 merge_mp4_mp3.py 脚本提供兜底保障")
    print(f"")
    print(f"📂 目录配置:")
    print(f"   📁 基础路径: {BASE_PATH}")
    print(f"   📹 原始MP4源: {INPUT_MP4_PATH}")
    print(f"   📄 字幕SRT源: {INPUT_SRT_PATH}")
    print(f"   🎬 带字幕MP4: {MP4_BASE_DIR}")
    print(f"   🎵 音频MP3: {MP3_BASE_DIR}")
    print(f"   🎞️ 最终有声MP4: {OUTPUT_BASE_DIR}")
    print(f"")
    print(f"🔧 脚本依赖:")
    print(f"   📜 字幕添加脚本: {ADD_SUBTITLES_SCRIPT}")
    print(f"   📜 音视频合并脚本: {MERGE_SCRIPT}")
    print(f"")
    print(f"⚙️ 运行参数:")
    print(f"   📺 频道: {args.channel}")
    print(f"   🌐 语言: {args.language}")
    
    if args.dry_run:
        print(f"   🔍 模式: 仅检查 (不修复)")
    else:
        print(f"   🔧 模式: 检查并修复")
    
    if args.gpu:
        print(f"   ⚡ GPU加速: 启用")
    else:
        print(f"   💻 CPU处理: 启用")
    
    if args.deep_check:
        print(f"   🔬 深度检查: 启用 (包括播放兼容性测试)")
    else:
        print(f"   🔍 标准检查: 启用 (仅ffprobe验证)")
    print(f"{'='*120}")

    start_time = time.time()
    
    try:
        check_and_repair_channel_language(
            args.channel, 
            args.language, 
            dry_run=args.dry_run, 
            use_gpu=args.gpu,
            deep_check=args.deep_check
        )
    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        sys.exit(1)
    
    end_time = time.time()
    print(f"\n⏱️  总耗时: {end_time - start_time:.2f} 秒")
    print(f"🎉 脚本执行完成！")


if __name__ == "__main__":
    main() 