#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍音频合并脚本
将 synthesize_book_audio.py 输出的音频片段合并为完整的书籍音频文件
支持断点续传功能和文件一致性检查

📚 功能说明:
- 读取 synthesize_book_audio.py 输出的音频片段
- 检查音频数量与文本块数量是否一致
- 按正确顺序合并所有音频片段
- 生成完整的书籍音频文件
- 支持音频播放速度调整（0.25x-4.0x）
- 支持断点续传，跳过已存在的有效音频文件
- 自动排除Mac系统产生的点文件

📥 输入信息:
- 文本块目录: /home/dhl/Documents/book/{lang}/{uuid}/{chunk_index}.txt
- 音频片段目录: 
  * 中文: /home/dhl/Documents/audio/mp3_clips/book/book_zh/{uuid}/{chunk_index}.mp3
  * 英文: /home/dhl/Documents/audio/mp3_clips/book/book_en/{uuid}/{chunk_index}.mp3

📤 输出信息:
- 输出目录: 
  * 中文: /mnt/dhl/audio/books/zh/mp3/{uuid}.mp3
  * 英文: /mnt/dhl/audio/books/en/mp3/{uuid}.mp3
- 自动排除Mac系统产生的点文件

🔄 处理规则:
1. 只在Ubuntu系统上运行
2. 检查音频片段数量与文本块数量是否一致
3. 支持断点续传，跳过已存在的有效音频文件
4. 自动排除以点开头的Mac系统文件
5. 按块索引顺序合并音频
6. 支持音频播放速度调整，使用ffmpeg的atempo滤镜

💡 使用示例:
# 合并英文书籍音频
python merge_book_audio.py --lang en

# 合并中文书籍音频
python merge_book_audio.py --lang zh

# 合并指定UUID的书籍
python merge_book_audio.py --uuid 12345678-abcd-efgh-ijkl-123456789012 --lang en

# 预览模式
python merge_book_audio.py --preview --lang zh

# 强制重新生成
python merge_book_audio.py --force-regenerate --lang en

# 1.1倍速合并英文书籍音频
python merge_book_audio.py --speed 1.1 --lang en

# 1.15倍速合并中文书籍音频
python merge_book_audio.py --speed 1.15 --lang zh

# 1.2倍速合并指定UUID的书籍
python merge_book_audio.py --speed 1.2 --uuid 12345678-abcd-efgh-ijkl-123456789012 --lang en
"""

import os
import glob
import argparse
import subprocess
import time
import platform
from pathlib import Path

# ============ 配置参数 ============
# 文本块目录：chunk_book_summaries.py的输出目录
# 注意：现在使用多语言路径结构 /home/dhl/Documents/book/{lang}
def get_text_base_dir(language="en"):
    """根据语言获取文本文件基础目录"""
    return f"/home/dhl/Documents/book/{language}"

# 音频片段目录：synthesize_book_audio.py的输出目录（支持多语言）
# 与 synthesize_book_audio.py 的输出路径保持一致

# 临时目录：用于存放合并过程中的临时文件
DEFAULT_TEMP_DIR = "/tmp/book_audio_merge"

# 最小音频文件大小（字节）
MIN_AUDIO_SIZE = 1024

# 最小合并音频文件大小（字节）
MIN_MERGED_AUDIO_SIZE = 10240
# ===================================


def get_audio_base_dir(language="en"):
    """根据语言获取音频片段基础目录"""
    if language == "zh":
        return "/home/dhl/Documents/audio/mp3_clips/book/book_zh"
    else:  # language == "en"
        return "/home/dhl/Documents/audio/mp3_clips/book/book_en"


def get_output_base_dir(language="en"):
    """根据语言获取输出文件基础目录"""
    if language == "zh":
        return "/mnt/dhl/audio/books/zh/mp3"
    else:  # language == "en"
        return "/mnt/dhl/audio/books/en/mp3"


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
        with open('/etc/os-release', 'r') as f:
            content = f.read()
            if 'Ubuntu' in content or 'ubuntu' in content:
                return True
        
        return False
    except:
        return False


def is_valid_audio_file(file_path, min_size_bytes=MIN_AUDIO_SIZE):
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


def get_book_directories(base_dir, dir_type="text"):
    """
    获取所有书籍目录（UUID目录）
    排除Mac生成的以点开头的meta文件和目录

    Args:
        base_dir (str): 基础目录路径
        dir_type (str): 目录类型，用于日志显示

    Returns:
        list: 排序后的书籍目录列表，格式：[(uuid, directory_path)]
    """
    if not os.path.exists(base_dir):
        print(f"❌ {dir_type}目录不存在: {base_dir}")
        return []

    book_dirs = []
    skipped_dirs = []

    # 收集所有书籍目录
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        
        if os.path.isdir(item_path):
            # 排除以点开头的目录（如.DS_Store等）
            if item.startswith("."):
                skipped_dirs.append(item)
                continue
            
            # 简单验证UUID格式（36字符，包含4个连字符）
            if len(item) == 36 and item.count("-") == 4:
                book_dirs.append((item, item_path))
            else:
                print(f"⚠️  跳过非UUID格式目录: {item}")

    if skipped_dirs:
        print(f"🚫 在{dir_type}目录跳过 {len(skipped_dirs)} 个Mac系统目录: {', '.join(skipped_dirs)}")

    # 按UUID排序
    book_dirs.sort(key=lambda x: x[0])
    
    print(f"📊 在{dir_type}目录找到 {len(book_dirs)} 个书籍目录")
    return book_dirs


def get_chunk_files(directory, uuid, file_type="txt"):
    """
    获取指定UUID书籍的所有文件，按块索引排序
    排除Mac生成的以点开头的meta文件

    Args:
        directory (str): 目录路径
        uuid (str): 书籍UUID
        file_type (str): 文件类型（txt 或 mp3）

    Returns:
        list: 排序后的文件路径列表
    """
    if not os.path.exists(directory):
        print(f"❌ [UUID:{uuid[:8]}...] 目录不存在: {directory}")
        return []

    # 获取所有指定类型的文件
    file_pattern = os.path.join(directory, f"*.{file_type}")
    all_files = glob.glob(file_pattern)

    # 过滤掉以点开头的文件
    valid_files = []
    skipped_files = []
    
    for file_path in all_files:
        filename = os.path.basename(file_path)
        if filename.startswith(".") or filename.startswith("._"):
            skipped_files.append(filename)
            continue
        
        # 确保是指定类型的文件
        if filename.endswith(f".{file_type}"):
            valid_files.append(file_path)
        else:
            skipped_files.append(filename)

    if skipped_files:
        print(f"🚫 [UUID:{uuid[:8]}...] 跳过 {len(skipped_files)} 个Mac系统{file_type}文件: {', '.join(skipped_files)}")

    # 按块索引排序
    def extract_chunk_number(filepath):
        basename = os.path.basename(filepath)
        try:
            return int(basename.split(".")[0])
        except:
            return 0

    valid_files.sort(key=extract_chunk_number)
    
    print(f"📚 [UUID:{uuid[:8]}...] 找到 {len(valid_files)} 个有效的{file_type}文件")
    return valid_files


def check_file_consistency(uuid, text_dir, audio_dir):
    """
    检查文本文件和音频文件数量是否一致，以及音频文件是否有效

    Args:
        uuid (str): 书籍UUID
        text_dir (str): 文本文件目录
        audio_dir (str): 音频文件目录

    Returns:
        tuple: (is_consistent, text_files, audio_files, missing_audio, invalid_audio)
    """
    print(f"\n🔍 [UUID:{uuid[:8]}...] 检查文件一致性...")
    
    # 获取文本文件和音频文件
    text_files = get_chunk_files(text_dir, uuid, "txt")
    audio_files = get_chunk_files(audio_dir, uuid, "mp3")
    
    if not text_files:
        print(f"❌ [UUID:{uuid[:8]}...] 未找到任何文本文件")
        return False, [], [], [], []
    
    if not audio_files:
        print(f"❌ [UUID:{uuid[:8]}...] 未找到任何音频文件")
        return False, text_files, [], [], []
    
    # 提取文件索引进行比较
    def get_chunk_indices(files):
        indices = []
        for file_path in files:
            basename = os.path.basename(file_path)
            try:
                index = int(basename.split(".")[0])
                indices.append(index)
            except:
                print(f"⚠️  [UUID:{uuid[:8]}...] 无法解析文件索引: {basename}")
        return sorted(indices)
    
    text_indices = get_chunk_indices(text_files)
    audio_indices = get_chunk_indices(audio_files)
    
    print(f"📊 [UUID:{uuid[:8]}...] 文本文件数量: {len(text_files)} (索引: {min(text_indices) if text_indices else 'N/A'}-{max(text_indices) if text_indices else 'N/A'})")
    print(f"📊 [UUID:{uuid[:8]}...] 音频文件数量: {len(audio_files)} (索引: {min(audio_indices) if audio_indices else 'N/A'}-{max(audio_indices) if audio_indices else 'N/A'})")
    
    # 检查是否有缺失的音频文件
    missing_audio = []
    invalid_audio = []
    
    text_indices_set = set(text_indices)
    audio_indices_set = set(audio_indices)
    
    missing_indices = text_indices_set - audio_indices_set
    if missing_indices:
        missing_audio = sorted(missing_indices)
        print(f"❌ [UUID:{uuid[:8]}...] 缺失音频文件，块索引: {missing_audio}")
    
    # 检查音频文件有效性
    audio_file_map = {}
    for audio_file in audio_files:
        basename = os.path.basename(audio_file)
        try:
            index = int(basename.split(".")[0])
            audio_file_map[index] = audio_file
        except:
            continue
    
    for index in audio_indices:
        audio_file = audio_file_map.get(index)
        if audio_file and not is_valid_audio_file(audio_file):
            invalid_audio.append(index)
            print(f"❌ [UUID:{uuid[:8]}...] 无效音频文件: {os.path.basename(audio_file)}")
    
    # 判断一致性
    is_consistent = (
        len(text_files) == len(audio_files) and
        text_indices_set == audio_indices_set and
        not invalid_audio
    )
    
    if is_consistent:
        print(f"✅ [UUID:{uuid[:8]}...] 文件一致性检查通过！")
    else:
        print(f"❌ [UUID:{uuid[:8]}...] 文件一致性检查失败！")
        if missing_audio:
            print(f"   缺失音频文件: {len(missing_audio)} 个")
        if invalid_audio:
            print(f"   无效音频文件: {len(invalid_audio)} 个")
    
    return is_consistent, text_files, audio_files, missing_audio, invalid_audio


def merge_audio_files(uuid, audio_files, output_file, temp_dir, audio_speed=1.0):
    """
    使用 ffmpeg 合并音频文件

    Args:
        uuid (str): 书籍UUID
        audio_files (list): 按顺序排列的音频文件路径列表
        output_file (str): 输出文件路径
        temp_dir (str): 临时目录
        audio_speed (float): 音频播放速度倍数 (默认: 1.0)

    Returns:
        bool: 合并是否成功
    """
    print(f"\n🔄 [UUID:{uuid[:8]}...] 开始合并音频文件...")
    print(f"📝 [UUID:{uuid[:8]}...] 将合并 {len(audio_files)} 个音频片段")
    print(f"📁 [UUID:{uuid[:8]}...] 输出文件: {output_file}")
    print(f"⚡ [UUID:{uuid[:8]}...] 音频播放速度: {audio_speed}x")
    
    # 检查所有音频片段是否有效
    valid_audio_files = []
    for audio_file in audio_files:
        if is_valid_audio_file(audio_file):
            valid_audio_files.append(audio_file)
        else:
            print(f"⚠️  [UUID:{uuid[:8]}...] 跳过无效音频片段: {os.path.basename(audio_file)}")
    
    if not valid_audio_files:
        print(f"❌ [UUID:{uuid[:8]}...] 没有有效的音频片段可以合并")
        return False
    
    if len(valid_audio_files) != len(audio_files):
        print(f"⚠️  [UUID:{uuid[:8]}...] 有 {len(audio_files) - len(valid_audio_files)} 个无效片段被跳过")
        print(f"📝 [UUID:{uuid[:8]}...] 实际将合并 {len(valid_audio_files)} 个有效音频片段")
    
    try:
        # 确保临时目录和输出目录存在
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 创建文件列表文件
        file_list_path = os.path.join(temp_dir, f"filelist_{uuid}.txt")
        
        with open(file_list_path, 'w', encoding='utf-8') as f:
            for audio_file in valid_audio_files:
                # 使用相对路径或绝对路径，确保路径中的特殊字符被正确处理
                escaped_path = audio_file.replace("'", "'\"'\"'")
                f.write(f"file '{escaped_path}'\n")
        
        print(f"📋 [UUID:{uuid[:8]}...] 创建文件列表: {file_list_path}")
        
        # 构建 ffmpeg 命令 - 使用重新编码而不是直接复制
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", file_list_path,
            "-acodec", "libmp3lame",  # 使用MP3编码器
            "-b:a", "192k",  # 设置比特率
            "-ar", "44100",  # 设置采样率
            "-ac", "1",  # 单声道
        ]
        
        # 添加音频速度调整滤镜（如果不是1.0倍速）
        if audio_speed != 1.0:
            # atempo滤镜的范围是0.5到2.0，如果超出范围需要链式处理
            audio_filters = []
            current_speed = audio_speed
            
            # 处理速度大于2.0的情况
            while current_speed > 2.0:
                audio_filters.append("atempo=2.0")
                current_speed /= 2.0
            
            # 处理速度小于0.5的情况
            while current_speed < 0.5:
                audio_filters.append("atempo=0.5")
                current_speed /= 0.5
            
            # 添加最后的速度调整
            if current_speed != 1.0:
                audio_filters.append(f"atempo={current_speed:.3f}")
            
            if audio_filters:
                filter_chain = ",".join(audio_filters)
                cmd.extend(["-af", filter_chain])
                print(f"🎧 [UUID:{uuid[:8]}...] 应用音频滤镜: {filter_chain}")
        
        cmd.extend(["-y", output_file])  # 覆盖输出文件
        
        print(f"🔄 [UUID:{uuid[:8]}...] 执行合并命令...")
        print(f"🔗 [UUID:{uuid[:8]}...] 准备合并 {len(valid_audio_files)} 个有效音频片段")
        
        # 执行命令
        start_time = time.time()
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=3600  # 1小时超时
        )
        end_time = time.time()
        
        # 清理临时文件
        try:
            os.remove(file_list_path)
        except:
            pass
        
        if result.returncode == 0:
            print(f"✅ [UUID:{uuid[:8]}...] 音频合并成功: {output_file}")
            
            # 检查输出文件
            if is_valid_audio_file(output_file, MIN_MERGED_AUDIO_SIZE):
                file_size = os.path.getsize(output_file)
                merge_time = end_time - start_time
                print(f"📊 [UUID:{uuid[:8]}...] 输出文件大小: {file_size:,} 字节 ({file_size/1024/1024:.1f} MB)")
                print(f"⏱️  [UUID:{uuid[:8]}...] 合并耗时: {merge_time:.1f} 秒")
                return True
            else:
                print(f"❌ [UUID:{uuid[:8]}...] 输出文件无效或过小")
                return False
        else:
            print(f"❌ [UUID:{uuid[:8]}...] ffmpeg 合并失败:")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ [UUID:{uuid[:8]}...] 音频合并超时: {output_file}")
        return False
    except Exception as e:
        print(f"❌ [UUID:{uuid[:8]}...] 音频合并出错: {e}")
        return False


def process_book_by_uuid(
    uuid,
    text_base_dir,
    audio_base_dir,
    output_base_dir,
    temp_dir,
    preview_mode=False,
    force_regenerate=False,
    audio_speed=1.0,
):
    """
    处理指定UUID书籍的音频合并
    
    Args:
        uuid (str): 书籍UUID
        text_base_dir (str): 文本文件基础目录
        audio_base_dir (str): 音频文件基础目录
        output_base_dir (str): 输出基础目录
        temp_dir (str): 临时目录
        preview_mode (bool): 是否为预览模式
        force_regenerate (bool): 是否强制重新生成
        audio_speed (float): 音频播放速度倍数 (默认: 1.0)
        
    Returns:
        dict: 处理结果
    """
    print(f"\n=== 📚 处理书籍音频合并 UUID: {uuid[:8]}...{uuid[-8:]} ===")
    
    text_dir = os.path.join(text_base_dir, uuid)
    audio_dir = os.path.join(audio_base_dir, uuid)
    output_file = os.path.join(output_base_dir, f"{uuid}.mp3")
    
    print(f"📁 文本目录: {text_dir}")
    print(f"📁 音频目录: {audio_dir}")
    print(f"📁 输出文件: {output_file}")
    
    # 检查输出文件是否已存在（除非强制重新生成）
    if not force_regenerate and is_valid_audio_file(output_file, MIN_MERGED_AUDIO_SIZE):
        file_size = os.path.getsize(output_file)
        print(f"⏭️  [UUID:{uuid[:8]}...] 完整音频文件已存在且有效，跳过: {output_file} ({file_size:,} 字节)")
        return {
            'uuid': uuid,
            'status': 'skipped',
            'reason': 'already_exists',
            'output_file': output_file
        }
    
    # 检查文件一致性
    is_consistent, text_files, audio_files, missing_audio, invalid_audio = check_file_consistency(
        uuid, text_dir, audio_dir
    )
    
    if not is_consistent:
        error_details = []
        if missing_audio:
            error_details.append(f"缺失音频: {len(missing_audio)} 个")
        if invalid_audio:
            error_details.append(f"无效音频: {len(invalid_audio)} 个")
        
        error_msg = ", ".join(error_details) if error_details else "文件数量不匹配"
        
        print(f"❌ [UUID:{uuid[:8]}...] 无法合并音频，文件不一致: {error_msg}")
        print(f"💡 [UUID:{uuid[:8]}...] 请先运行 synthesize_book_audio.py 确保所有音频片段正确生成")
        
        return {
            'uuid': uuid,
            'status': 'failed',
            'reason': 'inconsistent_files',
            'error': error_msg,
            'text_count': len(text_files),
            'audio_count': len(audio_files),
            'missing_audio': missing_audio,
            'invalid_audio': invalid_audio
        }
    
    # 预览模式
    if preview_mode:
        print(f"\n📋 [UUID:{uuid[:8]}...] 预览模式 - 将要合并的文件:")
        print(f"   文本文件: {len(text_files)} 个")
        print(f"   音频文件: {len(audio_files)} 个")
        print(f"   播放速度: {audio_speed}x")
        print(f"   输出文件: {output_file}")
        
        # 显示前几个和后几个文件
        show_count = min(3, len(audio_files))
        for i in range(show_count):
            audio_file = audio_files[i]
            basename = os.path.basename(audio_file)
            file_size = os.path.getsize(audio_file)
            print(f"      {i+1:3d}. {basename} ({file_size:,} 字节)")
        
        if len(audio_files) > show_count * 2:
            print(f"      ... ({len(audio_files) - show_count * 2} 个文件) ...")
            
            for i in range(len(audio_files) - show_count, len(audio_files)):
                audio_file = audio_files[i]
                basename = os.path.basename(audio_file)
                file_size = os.path.getsize(audio_file)
                print(f"      {i+1:3d}. {basename} ({file_size:,} 字节)")
        elif len(audio_files) > show_count:
            for i in range(show_count, len(audio_files)):
                audio_file = audio_files[i]
                basename = os.path.basename(audio_file)
                file_size = os.path.getsize(audio_file)
                print(f"      {i+1:3d}. {basename} ({file_size:,} 字节)")
        
        return {
            'uuid': uuid,
            'status': 'preview',
            'text_count': len(text_files),
            'audio_count': len(audio_files),
            'output_file': output_file
        }
    
    # 执行音频合并
    print(f"\n🔄 [UUID:{uuid[:8]}...] 开始音频合并处理...")
    
    success = merge_audio_files(uuid, audio_files, output_file, temp_dir, audio_speed)
    
    if success:
        return {
            'uuid': uuid,
            'status': 'success',
            'text_count': len(text_files),
            'audio_count': len(audio_files),
            'output_file': output_file
        }
    else:
        return {
            'uuid': uuid,
            'status': 'failed',
            'reason': 'merge_failed',
            'text_count': len(text_files),
            'audio_count': len(audio_files)
        }


def main():
    """主函数"""
    # 首先检查是否为Ubuntu系统
    if not check_ubuntu_system():
        print("❌ 此脚本只能在Ubuntu系统上运行！")
        print("🖥️  当前系统: " + platform.system())
        exit(1)
    
    print("✅ Ubuntu系统检测通过")
    
    parser = argparse.ArgumentParser(
        description="书籍音频合并器 - 将音频片段合并为完整的书籍音频文件（支持断点续传）",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python merge_book_audio.py --lang en                      # 合并所有英文书籍音频
  python merge_book_audio.py --lang zh                      # 合并所有中文书籍音频
  python merge_book_audio.py --uuid 12345678-abcd-efgh-ijkl-123456789012 --lang en  # 合并指定UUID的书籍
  python merge_book_audio.py --preview --lang zh            # 预览模式
  python merge_book_audio.py --force-regenerate --lang en   # 强制重新生成
  python merge_book_audio.py --speed 1.1 --lang en         # 1.1倍速合并英文书籍音频
  python merge_book_audio.py --speed 1.15 --lang zh        # 1.15倍速合并中文书籍音频
        """
    )
    parser.add_argument(
        "--uuid", "-u",
        help="要处理的书籍UUID，不指定则处理所有书籍"
    )
    parser.add_argument(
        "--text-base-dir", 
        help="文本文件基础目录路径 (默认：根据语言自动确定)"
    )
    parser.add_argument(
        "--lang", "-l",
        choices=["en", "zh"], 
        default="en",
        help="语言类型: en=英文, zh=中文 (默认: en)"
    )
    parser.add_argument(
        "--audio-base-dir", 
        help="音频文件基础目录路径 (默认：根据语言自动确定)"
    )
    parser.add_argument(
        "--output-base-dir", 
        help="输出基础目录路径 (默认：根据语言自动确定)"
    )
    parser.add_argument(
        "--temp-dir", 
        default=DEFAULT_TEMP_DIR, 
        help=f"临时目录路径 (默认: {DEFAULT_TEMP_DIR})"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="预览模式，只显示会处理哪些文件，不实际处理",
    )
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="强制重新生成所有文件，忽略已存在的文件",
    )
    parser.add_argument(
        "--speed", "-s",
        type=float,
        default=1.0,
        help="音频播放速度倍数 (默认: 1.0, 范围: 0.25-4.0)",
    )

    args = parser.parse_args()

    # 验证速度参数
    if args.speed < 0.25 or args.speed > 4.0:
        print(f"❌ 音频播放速度参数无效: {args.speed}")
        print("💡 播放速度必须在 0.25 到 4.0 之间")
        return

    # 根据语言设置路径
    language = args.lang
    
    # 文本基础目录 - 根据语言确定
    if args.text_base_dir:
        text_base_dir = args.text_base_dir
    else:
        text_base_dir = get_text_base_dir(language)
    
    # 音频基础目录 - 根据语言确定
    if args.audio_base_dir:
        audio_base_dir = args.audio_base_dir
    else:
        audio_base_dir = get_audio_base_dir(language)
    
    # 输出基础目录 - 根据语言确定
    if args.output_base_dir:
        output_base_dir = args.output_base_dir
    else:
        output_base_dir = get_output_base_dir(language)
    
    temp_dir = args.temp_dir

    lang_name = "中文" if language == "zh" else "英文"
    
    print(f"\n🎵 书籍音频合并器 (支持断点续传)")
    print(f"🌍 处理语言: {lang_name} ({language})")
    print(f"⚡ 音频播放速度: {args.speed}x")
    print(f"📁 文本基础目录: {text_base_dir}")
    print(f"📁 音频基础目录: {audio_base_dir}")
    print(f"📁 输出基础目录: {output_base_dir}")
    print(f"📁 临时目录: {temp_dir}")
    print(f"🚫 自动排除Mac系统文件 (.DS_Store等)")

    if args.uuid:
        print(f"📚 处理模式: 仅处理指定UUID书籍 ({args.uuid[:8]}...{args.uuid[-8:]})")
    else:
        print(f"📚 处理模式: 处理所有发现的书籍")

    if args.force_regenerate:
        print(f"🔄 强制重新生成模式: 将重新生成所有文件")
    else:
        print(f"⚡ 断点续传模式: 将跳过已存在的有效文件")

    if args.preview:
        print(f"👁️  预览模式：只显示将要处理的文件")

    # 检查必要的命令
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("✅ ffmpeg 命令可用")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ ffmpeg 命令不可用，请安装 ffmpeg")
        print("💡 安装命令: sudo apt update && sudo apt install ffmpeg")
        return

    # 获取要处理的书籍列表
    if args.uuid:
        # 处理指定UUID的书籍
        text_dir = os.path.join(text_base_dir, args.uuid)
        audio_dir = os.path.join(audio_base_dir, args.uuid)
        
        if not os.path.exists(text_dir):
            print(f"❌ 指定UUID的文本目录不存在: {text_dir}")
            return
        
        if not os.path.exists(audio_dir):
            print(f"❌ 指定UUID的音频目录不存在: {audio_dir}")
            print("💡 请先运行 synthesize_book_audio.py 生成音频片段")
            return
        
        book_list = [args.uuid]
    else:
        # 获取所有书籍UUID（以音频目录为准，因为需要音频文件存在）
        audio_book_dirs = get_book_directories(audio_base_dir, "音频")
        
        if not audio_book_dirs:
            print(f"❌ 在音频目录 {audio_base_dir} 中未找到任何书籍")
            print("💡 请先运行 synthesize_book_audio.py 生成音频片段")
            return
        
        book_list = [uuid for uuid, _ in audio_book_dirs]

    # 处理所有书籍
    all_results = []
    
    try:
        for uuid in book_list:
            try:
                result = process_book_by_uuid(
                    uuid, 
                    text_base_dir,
                    audio_base_dir,
                    output_base_dir,
                    temp_dir,
                    args.preview, 
                    args.force_regenerate,
                    args.speed
                )
                all_results.append(result)
            except Exception as e:
                print(f"❌ 处理书籍 UUID:{uuid[:8]}... 时出错: {e}")
                import traceback
                traceback.print_exc()

        # 统计总结果
        if all_results:
            print(f"\n=== 🎉 处理完成总结 ===")
            
            total_books = len(all_results)
            success_count = sum(1 for r in all_results if r['status'] == 'success')
            failed_count = sum(1 for r in all_results if r['status'] == 'failed')
            skipped_count = sum(1 for r in all_results if r['status'] == 'skipped')
            preview_count = sum(1 for r in all_results if r['status'] == 'preview')
            
            if args.preview:
                print(f"📊 预览统计:")
                print(f"  - 发现书籍总数: {total_books} 本")
                print(f"  - 需要处理: {preview_count} 本")
                print(f"  - 已完成跳过: {skipped_count} 本")
                
                print(f"\n📋 各书籍详情:")
                for result in all_results:
                    uuid = result['uuid']
                    status = result['status']
                    if status == 'preview':
                        print(f"  - UUID:{uuid[:8]}...{uuid[-8:]}: 需处理 (音频:{result['audio_count']}个)")
                    elif status == 'skipped':
                        print(f"  - UUID:{uuid[:8]}...{uuid[-8:]}: 已完成")
                    else:
                        print(f"  - UUID:{uuid[:8]}...{uuid[-8:]}: {status}")
            else:
                print(f"📊 处理统计:")
                print(f"  - 书籍总数: {total_books} 本")
                print(f"  - 成功合并: {success_count} 本")
                print(f"  - 合并失败: {failed_count} 本")
                print(f"  - 跳过文件: {skipped_count} 本")
                
                if total_books > 0:
                    success_rate = (success_count / total_books) * 100
                    print(f"  - 成功率: {success_rate:.1f}%")
                
                print(f"\n📋 各书籍详情:")
                for result in all_results:
                    uuid = result['uuid']
                    status = result['status']
                    if status == 'success':
                        print(f"  ✅ UUID:{uuid[:8]}...{uuid[-8:]}: 合并成功 (音频:{result['audio_count']}个)")
                    elif status == 'failed':
                        reason = result.get('reason', '未知原因')
                        print(f"  ❌ UUID:{uuid[:8]}...{uuid[-8:]}: 合并失败 ({reason})")
                    elif status == 'skipped':
                        print(f"  ⏭️  UUID:{uuid[:8]}...{uuid[-8:]}: 已存在，跳过")
                
                if success_count > 0:
                    print(f"\n📝 合并后的音频文件已保存到: {output_base_dir}")
                    print(f"📁 文件格式: {output_base_dir}/{{uuid}}.mp3")

    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断了程序执行")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")


if __name__ == "__main__":
    main() 