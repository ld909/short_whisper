#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍音频合成脚本
使用 f5-tts CLI 将 chunk_book_summaries.py 输出的文本块合成为音频文件
支持断点续传功能和UUID目录结构

📚 功能说明:
- 读取 chunk_book_summaries.py 输出的书籍文本块
- 使用 f5-tts 合成高质量音频文件
- 支持断点续传，跳过已存在的有效音频文件
- 自动排除Mac系统产生的点文件

📥 输入信息:
- 默认输入目录: /home/dhl/Documents/book/
- 输入目录结构: book/{uuid}/{chunk_index}.txt
- 支持文件格式: .txt 文件
- 文件编码: UTF-8

📤 输出信息:
- 默认输出目录: /home/dhl/Documents/audio/mp3_clips/book/
- 输出目录结构: mp3_clips/book/{uuid}/{chunk_index}.mp3
- 自动排除Mac系统产生的点文件

🔄 处理规则:
1. 只在Ubuntu系统上运行
2. 支持断点续传，跳过已存在的有效音频文件
3. 自动排除以点开头的Mac系统文件
4. 按UUID和块索引有序处理

💡 使用示例:
# 处理所有书籍
python synthesize_book_audio.py

# 处理指定UUID的书籍
python synthesize_book_audio.py --uuid 12345678-abcd-efgh-ijkl-123456789012

# 预览模式
python synthesize_book_audio.py --preview

# 禁用断点续传
python synthesize_book_audio.py --no-resume

# 强制重新生成
python synthesize_book_audio.py --force-regenerate
"""

import os
import glob
import argparse
import subprocess
import time
import platform
from pathlib import Path

# ============ 配置参数 ============
# 输入目录：存放文本块的目录（chunk_book_summaries.py的输出目录）
DEFAULT_INPUT_BASE_DIR = "/home/dhl/Documents/book"

# 输出目录：生成的音频文件保存目录
DEFAULT_OUTPUT_BASE_DIR = "/home/dhl/Documents/audio/mp3_clips/book"

# 参考音频文件：用于语音克隆的参考音频
REF_AUDIO = (
    "/home/dhl/Documents/short_whisper/audio_ficition/audio_ref/11_normalized_2.mp3"
)

# 默认使用的模型
DEFAULT_MODEL = "F5TTS_v1_Base"

# 代理设置
PROXY_HTTP = "http://127.0.0.1:7897"
PROXY_HTTPS = "http://127.0.0.1:7897"
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
        with open('/etc/os-release', 'r') as f:
            content = f.read()
            if 'Ubuntu' in content or 'ubuntu' in content:
                return True
        
        return False
    except:
        return False


def set_clash_proxy():
    """设置代理环境变量，用于下载模型文件"""
    os.environ["http_proxy"] = PROXY_HTTP
    os.environ["https_proxy"] = PROXY_HTTPS
    print("🌐 成功设定clash环境proxy...")


def unset_clash_proxy():
    """取消代理环境变量"""
    os.environ.pop("http_proxy", None)
    os.environ.pop("https_proxy", None)
    print("🌐 成功取消clash环境proxy...")


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


def read_text_content(file_path):
    """
    读取文本文件内容

    Args:
        file_path (str): 文件路径

    Returns:
        str: 文件内容，如果读取失败返回 None
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        return content
    except Exception as e:
        print(f"❌ 读取文件失败 {file_path}: {e}")
        return None


def synthesize_audio(source_file, ref_audio, output_file, model="F5TTS_v1_Base"):
    """
    使用 f5-tts CLI 合成音频

    Args:
        source_file (str): 源文本文件路径
        ref_audio (str): 参考音频文件路径
        output_file (str): 输出音频文件路径
        model (str): 使用的模型名称

    Returns:
        bool: 合成是否成功
    """
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)

        # 直接使用源文件，构建 f5-tts 命令
        cmd = [
            "f5-tts_infer-cli",
            "--model",
            model,
            "--ref_audio",
            ref_audio,
            "--ref_text",
            "",  # 总是空的，但必须提供
            "--gen_file",
            source_file,  # 直接使用源文件
            "--remove_silence",
            "--output_dir",
            output_dir,
            "--output_file",
            os.path.basename(output_file),
        ]

        print(f"🔄 执行命令: {' '.join(cmd)}")
        print(f"📄 使用源文件: {source_file}")

        # 执行命令
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=1800  # 30分钟超时
        )

        if result.returncode == 0:
            print(f"✅ 音频合成成功: {output_file}")
            return True
        else:
            print(f"❌ 音频合成失败:")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")

            # 如果 --gen_file 参数不支持，回退到读取文件内容使用 --gen_text 方式
            if "--gen_file" in result.stderr or "gen_file" in result.stderr:
                print(f"⚠️  --gen_file 参数不支持，回退到 --gen_text 方式")
                text_content = read_text_content(source_file)
                if text_content:
                    return synthesize_audio_fallback(
                        text_content, ref_audio, output_file, model
                    )
                else:
                    return False

            return False

    except subprocess.TimeoutExpired:
        print(f"❌ 音频合成超时: {output_file}")
        return False
    except Exception as e:
        print(f"❌ 音频合成出错: {e}")
        return False


def synthesize_audio_fallback(
    text_content, ref_audio, output_file, model="F5TTS_v1_Base"
):
    """
    回退方案：直接使用 --gen_text 参数

    Args:
        text_content (str): 要合成的文本内容
        ref_audio (str): 参考音频文件路径
        output_file (str): 输出音频文件路径
        model (str): 使用的模型名称

    Returns:
        bool: 合成是否成功
    """
    try:
        output_dir = os.path.dirname(output_file)

        # 简单处理换行符，避免命令行参数问题
        clean_text = text_content.replace("\n", " ").replace("\r", " ").strip()

        # 限制文本长度，避免命令行参数过长
        if len(clean_text) > 1000:
            clean_text = clean_text[:1000] + "..."
            print(f"⚠️  文本过长，已截断到1000字符")

        # 构建 f5-tts 命令
        cmd = [
            "f5-tts_infer-cli",
            "--model",
            model,
            "--ref_audio",
            ref_audio,
            "--ref_text",
            "",
            "--gen_text",
            clean_text,
            "--remove_silence",
            "--output_dir",
            output_dir,
            "--output_file",
            os.path.basename(output_file),
        ]

        print(f"🔄 回退方案执行命令（使用 --gen_text）")

        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30分钟超时

        if result.returncode == 0:
            print(f"✅ 音频合成成功（回退方案）: {output_file}")
            return True
        else:
            print(f"❌ 音频合成失败（回退方案）:")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ 回退方案出错: {e}")
        return False


def get_book_directories(input_base_dir):
    """
    获取所有书籍目录（UUID目录）
    排除Mac生成的以点开头的meta文件和目录

    Args:
        input_base_dir (str): 输入基础目录路径

    Returns:
        list: 排序后的书籍目录列表，格式：[(uuid, directory_path)]
    """
    if not os.path.exists(input_base_dir):
        print(f"❌ 输入目录不存在: {input_base_dir}")
        return []

    book_dirs = []
    skipped_dirs = []

    # 收集所有书籍目录
    for item in os.listdir(input_base_dir):
        item_path = os.path.join(input_base_dir, item)
        
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
        print(f"🚫 跳过 {len(skipped_dirs)} 个Mac系统目录: {', '.join(skipped_dirs)}")

    # 按UUID排序
    book_dirs.sort(key=lambda x: x[0])
    
    print(f"📊 找到 {len(book_dirs)} 个书籍目录")
    return book_dirs


def get_chunk_files_by_uuid(book_directory, uuid):
    """
    获取指定UUID书籍的所有文本块文件，按块索引排序
    排除Mac生成的以点开头的meta文件

    Args:
        book_directory (str): 书籍目录路径
        uuid (str): 书籍UUID

    Returns:
        list: 排序后的文本块文件路径列表
    """
    if not os.path.exists(book_directory):
        print(f"❌ [UUID:{uuid[:8]}...] 书籍目录不存在: {book_directory}")
        return []

    # 获取所有txt文件
    chunk_pattern = os.path.join(book_directory, "*.txt")
    all_txt_files = glob.glob(chunk_pattern)

    # 过滤掉以点开头的文件
    chunk_files = []
    skipped_files = []
    
    for chunk_file in all_txt_files:
        filename = os.path.basename(chunk_file)
        if filename.startswith(".") or filename.startswith("._"):
            skipped_files.append(filename)
            continue
        
        # 确保是txt文件
        if filename.endswith(".txt"):
            chunk_files.append(chunk_file)
        else:
            skipped_files.append(filename)

    if skipped_files:
        print(f"🚫 [UUID:{uuid[:8]}...] 跳过 {len(skipped_files)} 个Mac系统文件: {', '.join(skipped_files)}")

    # 按块索引排序
    def extract_chunk_number(filepath):
        basename = os.path.basename(filepath)
        try:
            return int(basename.split(".")[0])
        except:
            return 0

    chunk_files.sort(key=extract_chunk_number)
    
    print(f"📚 [UUID:{uuid[:8]}...] 找到 {len(chunk_files)} 个文本块文件")
    return chunk_files


def scan_existing_audio_files(output_base_dir, uuid):
    """
    扫描指定UUID书籍输出目录中已存在的音频文件

    Args:
        output_base_dir (str): 输出基础目录路径
        uuid (str): 书籍UUID

    Returns:
        dict: 已存在文件的字典 {chunk_index: file_path}
    """
    existing_files = {}
    book_output_dir = os.path.join(output_base_dir, uuid)

    if not os.path.exists(book_output_dir):
        return existing_files

    print(f"🔍 [UUID:{uuid[:8]}...] 扫描已存在的音频文件...")

    # 获取所有音频文件
    audio_pattern = os.path.join(book_output_dir, "*.mp3")
    audio_files = glob.glob(audio_pattern)

    skipped_files = []
    for audio_file in audio_files:
        filename = os.path.basename(audio_file)
        
        # 排除以点开头的文件
        if filename.startswith(".") or filename.startswith("._"):
            skipped_files.append(filename)
            continue
        
        chunk_index = filename.split(".")[0]

        # 检查文件是否有效
        if is_valid_audio_file(audio_file):
            existing_files[chunk_index] = audio_file
        else:
            print(f"🗑️  [UUID:{uuid[:8]}...] 发现无效文件，将重新生成: {audio_file}")
            try:
                os.remove(audio_file)
                print(f"✅ [UUID:{uuid[:8]}...] 已删除无效文件: {audio_file}")
            except Exception as e:
                print(f"❌ [UUID:{uuid[:8]}...] 删除无效文件失败: {e}")

    if skipped_files:
        print(f"🚫 [UUID:{uuid[:8]}...] 跳过 {len(skipped_files)} 个Mac系统音频文件: {', '.join(skipped_files)}")

    print(f"📊 [UUID:{uuid[:8]}...] 找到 {len(existing_files)} 个有效的音频文件")
    return existing_files


def process_single_chunk(
    chunk_file,
    uuid,
    chunk_index,
    ref_audio,
    output_base_dir,
    model="F5TTS_v1_Base",
    force_regenerate=False,
):
    """
    处理单个文本块，合成音频

    Args:
        chunk_file (str): 文本块文件路径
        uuid (str): 书籍UUID
        chunk_index (str): 块索引
        ref_audio (str): 参考音频文件路径
        output_base_dir (str): 输出基础目录
        model (str): 使用的模型名称
        force_regenerate (bool): 是否强制重新生成

    Returns:
        bool: 处理是否成功
    """
    # 检查源文件是否存在
    if not os.path.exists(chunk_file):
        print(f"❌ [UUID:{uuid[:8]}...] 源文件不存在: {chunk_file}")
        return False

    # 构建输出文件路径
    book_output_dir = os.path.join(output_base_dir, uuid)
    output_file = os.path.join(book_output_dir, f"{chunk_index}.mp3")

    # 检查文件是否已存在且有效（除非强制重新生成）
    if not force_regenerate and is_valid_audio_file(output_file):
        file_size = os.path.getsize(output_file)
        print(f"⏭️  [UUID:{uuid[:8]}...] 文件已存在且有效，跳过: 块{chunk_index} ({file_size} 字节)")
        return True

    # 获取文件大小用于显示
    try:
        file_size = os.path.getsize(chunk_file)
        print(f"📝 [UUID:{uuid[:8]}...] 处理文本块: 块 {chunk_index}")
        print(f"   输入: {chunk_file} ({file_size} 字节)")
        print(f"   输出: {output_file}")
    except Exception as e:
        print(f"⚠️  [UUID:{uuid[:8]}...] 无法获取文件大小: {e}")

    # 合成音频
    success = synthesize_audio(chunk_file, ref_audio, output_file, model)

    if success:
        # 检查输出文件是否真的生成了且有效
        if is_valid_audio_file(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ [UUID:{uuid[:8]}...] 音频文件生成成功: 块{chunk_index} ({file_size} 字节)")
            return True
        else:
            print(f"❌ [UUID:{uuid[:8]}...] 音频文件未生成或无效: {output_file}")
            return False
    else:
        return False


def process_book_by_uuid(
    uuid,
    book_directory,
    ref_audio,
    output_base_dir,
    model="F5TTS_v1_Base",
    preview_mode=False,
    resume_mode=True,
    force_regenerate=False,
):
    """
    处理指定UUID书籍的所有文本块文件
    
    Args:
        uuid (str): 书籍UUID
        book_directory (str): 书籍目录路径
        ref_audio (str): 参考音频文件路径
        output_base_dir (str): 输出基础目录
        model (str): 使用的模型名称
        preview_mode (bool): 是否为预览模式
        resume_mode (bool): 是否启用断点续传
        force_regenerate (bool): 是否强制重新生成
        
    Returns:
        dict: 处理结果统计
    """
    print(f"\n=== 📚 处理书籍 UUID: {uuid[:8]}...{uuid[-8:]} ===")
    print(f"📁 输入目录: {book_directory}")
    print(f"📁 输出目录: {os.path.join(output_base_dir, uuid)}")
    
    # 获取所有文本块文件
    chunk_files = get_chunk_files_by_uuid(book_directory, uuid)
    
    if not chunk_files:
        print(f"❌ [UUID:{uuid[:8]}...] 在目录中未找到任何文本块文件")
        return {
            'uuid': uuid,
            'total': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
    
    print(f"📊 [UUID:{uuid[:8]}...] 找到 {len(chunk_files)} 个文本块文件")

    # 扫描已存在的文件（除非强制重新生成）
    existing_files = {}
    if not force_regenerate and resume_mode:
        existing_files = scan_existing_audio_files(output_base_dir, uuid)
    
    # 获取进度统计
    total_files = len(chunk_files)
    completed_files = 0
    pending_files = []

    for chunk_file in chunk_files:
        chunk_filename = os.path.basename(chunk_file)
        chunk_index = chunk_filename.split(".")[0]

        if chunk_index in existing_files:
            completed_files += 1
        else:
            pending_files.append((chunk_file, chunk_index))

    remaining_files = total_files - completed_files
    completion_rate = (completed_files / total_files * 100) if total_files > 0 else 0
    
    print(f"\n📈 [UUID:{uuid[:8]}...] 进度统计:")
    print(f"   总文件数: {total_files}")
    print(f"   已完成: {completed_files} ({completion_rate:.1f}%)")
    print(f"   待处理: {remaining_files}")
    
    if preview_mode:
        print(f"\n📋 [UUID:{uuid[:8]}...] 预览模式 - 将要处理的文件:")
        for i, (chunk_file, chunk_index) in enumerate(pending_files[:10], 1):  # 只显示前10个
            output_file = os.path.join(output_base_dir, uuid, f"{chunk_index}.mp3")
            print(f"  {i:3d}. 块 {chunk_index}")
            print(f"       输入: {chunk_file}")
            print(f"       输出: {output_file}")
        
        if len(pending_files) > 10:
            print(f"       ... 还有 {len(pending_files) - 10} 个文件")
        
        return {
            'uuid': uuid,
            'total': total_files,
            'successful': 0,
            'failed': 0,
            'skipped': completed_files,
            'preview': len(pending_files)
        }

    # 如果没有待处理的文件
    if not pending_files:
        print(f"\n🎉 [UUID:{uuid[:8]}...] 所有文件都已完成！无需处理。")
        return {
            'uuid': uuid,
            'total': total_files,
            'successful': total_files,
            'failed': 0,
            'skipped': 0
        }

    # 确保输出目录存在
    book_output_dir = os.path.join(output_base_dir, uuid)
    os.makedirs(book_output_dir, exist_ok=True)

    print(f"\n🔄 [UUID:{uuid[:8]}...] 开始音频合成...")
    print(f"📝 [UUID:{uuid[:8]}...] 本次将处理 {len(pending_files)} 个文件")

    successful_count = 0
    failed_count = 0

    try:
        start_time = time.time()

        for i, (chunk_file, chunk_index) in enumerate(pending_files, 1):
            print(
                f"\n[UUID:{uuid[:8]}...] 处理第 {i}/{len(pending_files)} 个文件: 块 {chunk_index}"
            )
            print(
                f"[UUID:{uuid[:8]}...] 总体进度: {completed_files + i}/{total_files} ({(completed_files + i)/total_files*100:.1f}%)"
            )

            success = process_single_chunk(
                chunk_file,
                uuid,
                chunk_index,
                ref_audio,
                output_base_dir,
                model,
                force_regenerate,
            )

            if success:
                successful_count += 1
            else:
                failed_count += 1

            # 在每个文件处理后稍作停顿
            if i < len(pending_files):
                print(f"[UUID:{uuid[:8]}...] ⏳ 等待 2 秒...")
                time.sleep(2)

        end_time = time.time()
        total_time = end_time - start_time

        print(f"\n=== 🎉 [UUID:{uuid[:8]}...] 处理完成 ===")
        print(f"✅ [UUID:{uuid[:8]}...] 本次成功合成: {successful_count} 个音频文件")
        print(f"❌ [UUID:{uuid[:8]}...] 本次合成失败: {failed_count} 个音频文件")
        print(f"⏭️  [UUID:{uuid[:8]}...] 之前已完成: {completed_files} 个音频文件")
        print(f"⏱️  [UUID:{uuid[:8]}...] 本次耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")

        if successful_count > 0:
            avg_time = total_time / successful_count
            print(f"📊 [UUID:{uuid[:8]}...] 平均每个文件: {avg_time:.1f} 秒")

        return {
            'uuid': uuid,
            'total': total_files,
            'successful': successful_count,
            'failed': failed_count,
            'skipped': completed_files
        }

    except KeyboardInterrupt:
        print(f"\n⚠️  [UUID:{uuid[:8]}...] 用户中断了程序执行")
        return {
            'uuid': uuid,
            'total': total_files,
            'successful': successful_count,
            'failed': failed_count,
            'skipped': completed_files
        }
    except Exception as e:
        print(f"\n❌ [UUID:{uuid[:8]}...] 程序执行出错: {e}")
        return {
            'uuid': uuid,
            'total': total_files,
            'successful': successful_count,
            'failed': failed_count,
            'skipped': completed_files
        }


def cleanup_and_exit(use_proxy):
    """清理代理设置并退出"""
    if use_proxy:
        unset_clash_proxy()


def main():
    """主函数"""
    # 首先检查是否为Ubuntu系统
    if not check_ubuntu_system():
        print("❌ 此脚本只能在Ubuntu系统上运行！")
        print("🖥️  当前系统: " + platform.system())
        exit(1)
    
    print("✅ Ubuntu系统检测通过")
    
    parser = argparse.ArgumentParser(
        description="书籍音频合成器 - 使用 f5-tts 将书籍文本块合成为音频（支持断点续传）",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python synthesize_book_audio.py                                # 处理所有书籍
  python synthesize_book_audio.py --uuid 12345678-abcd-efgh-ijkl-123456789012  # 处理指定UUID的书籍
  python synthesize_book_audio.py --preview                      # 预览模式
  python synthesize_book_audio.py --no-resume                    # 禁用断点续传
  python synthesize_book_audio.py --force-regenerate             # 强制重新生成
        """
    )
    parser.add_argument(
        "--uuid", "-u",
        help="要处理的书籍UUID，不指定则处理所有书籍"
    )
    parser.add_argument(
        "--input-base-dir", 
        default=DEFAULT_INPUT_BASE_DIR, 
        help=f"输入基础目录路径 (默认: {DEFAULT_INPUT_BASE_DIR})"
    )
    parser.add_argument(
        "--output-base-dir", 
        default=DEFAULT_OUTPUT_BASE_DIR, 
        help=f"输出基础目录路径 (默认: {DEFAULT_OUTPUT_BASE_DIR})"
    )
    parser.add_argument(
        "--ref-audio", 
        default=REF_AUDIO, 
        help=f"参考音频文件路径 (默认: {REF_AUDIO})"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"使用的 f5-tts 模型 (默认: {DEFAULT_MODEL})",
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
        "--no-resume",
        action="store_true",
        help="禁用断点续传，重新处理所有文件",
    )
    parser.add_argument(
        "--proxy",
        action="store_true",
        default=True,
        help="启用代理设置，用于下载模型文件 (默认: True)",
    )
    parser.add_argument("--no-proxy", action="store_true", help="禁用代理设置")

    args = parser.parse_args()

    # 设置代理（如果需要）
    use_proxy = args.proxy and not args.no_proxy
    if use_proxy:
        set_clash_proxy()
    else:
        print("🌐 未启用代理设置")

    input_base_dir = args.input_base_dir
    output_base_dir = args.output_base_dir
    ref_audio = args.ref_audio
    model = args.model
    resume_mode = not args.no_resume

    print(f"\n🎵 书籍音频合成器 (支持断点续传)")
    print(f"📁 输入基础目录: {input_base_dir}")
    print(f"📁 输出基础目录: {output_base_dir}")
    print(f"🎤 参考音频: {ref_audio}")
    print(f"🤖 使用模型: {model}")
    print(f"🔄 断点续传: {'启用' if resume_mode else '禁用'}")
    print(f"🚫 自动排除Mac系统文件 (.DS_Store等)")

    if args.uuid:
        print(f"📚 处理模式: 仅处理指定UUID书籍 ({args.uuid[:8]}...{args.uuid[-8:]})")
    else:
        print(f"📚 处理模式: 处理所有发现的书籍")

    if args.force_regenerate:
        print(f"🔄 强制重新生成模式: 将重新生成所有文件")
    elif resume_mode:
        print(f"⚡ 断点续传模式: 将跳过已存在的有效文件")

    if args.preview:
        print(f"👁️  预览模式：只显示将要处理的文件")

    # 检查参考音频文件是否存在
    if not os.path.exists(ref_audio):
        print(f"❌ 参考音频文件不存在: {ref_audio}")
        cleanup_and_exit(use_proxy)
        return

    # 获取要处理的书籍列表
    if args.uuid:
        # 处理指定UUID的书籍
        book_directory = os.path.join(input_base_dir, args.uuid)
        if not os.path.exists(book_directory):
            print(f"❌ 指定UUID的书籍目录不存在: {book_directory}")
            cleanup_and_exit(use_proxy)
            return
        book_dirs = [(args.uuid, book_directory)]
    else:
        # 获取所有书籍目录
        book_dirs = get_book_directories(input_base_dir)
        
        if not book_dirs:
            print(f"❌ 在目录 {input_base_dir} 中未找到任何书籍")
            print("💡 请确保 chunk_book_summaries.py 已经运行并生成了文本块文件")
            cleanup_and_exit(use_proxy)
            return

    # 处理所有书籍
    all_results = []
    
    try:
        for uuid, book_directory in book_dirs:
            try:
                result = process_book_by_uuid(
                    uuid, 
                    book_directory, 
                    ref_audio, 
                    output_base_dir, 
                    model, 
                    args.preview, 
                    resume_mode, 
                    args.force_regenerate
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
            total_files = sum(r['total'] for r in all_results)
            total_successful = sum(r['successful'] for r in all_results)
            total_failed = sum(r['failed'] for r in all_results)
            total_skipped = sum(r['skipped'] for r in all_results)
            
            if args.preview:
                total_preview = sum(r.get('preview', 0) for r in all_results)
                print(f"📊 预览统计:")
                print(f"  - 发现书籍总数: {total_books} 本")
                print(f"  - 发现文件总数: {total_files} 个")
                print(f"  - 需要处理: {total_preview} 个")
                print(f"  - 已处理跳过: {total_skipped} 个")
                
                print(f"\n📋 各书籍详情:")
                for result in all_results:
                    uuid = result['uuid']
                    preview_count = result.get('preview', 0)
                    print(f"  - UUID:{uuid[:8]}...{uuid[-8:]}: 发现 {result['total']} 个，需处理 {preview_count} 个，跳过 {result['skipped']} 个")
            else:
                print(f"📊 处理统计:")
                print(f"  - 书籍总数: {total_books} 本")
                print(f"  - 文件总数: {total_files} 个")
                print(f"  - 成功处理: {total_successful} 个")
                print(f"  - 处理失败: {total_failed} 个")
                print(f"  - 跳过文件: {total_skipped} 个")
                
                if total_files > 0:
                    success_rate = (total_successful / (total_successful + total_failed)) * 100 if (total_successful + total_failed) > 0 else 0
                    print(f"  - 成功率: {success_rate:.1f}%")
                
                print(f"\n📋 各书籍详情:")
                for result in all_results:
                    uuid = result['uuid']
                    print(f"  - UUID:{uuid[:8]}...{uuid[-8:]}: 成功 {result['successful']} 个，失败 {result['failed']} 个，跳过 {result['skipped']} 个")
                
                if total_successful > 0:
                    print(f"\n📝 音频文件已保存到: {output_base_dir}")
                    print(f"📁 目录结构: mp3_clips/book/{uuid}/{chunk_index}.mp3")

    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断了程序执行")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
    finally:
        # 清理代理设置
        cleanup_and_exit(use_proxy)


if __name__ == "__main__":
    main() 