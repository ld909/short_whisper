#!/usr/bin/env python3
"""
NVIDIA ASR 字幕生成器
使用 NVIDIA NeMo ASR 模型为音频文件生成 word-level 和 segment-level 字幕

功能说明:
1. 读取 merge_audio.py 输出的 MP3 文件
2. 使用 NVIDIA NeMo ASR 进行语音识别
3. 生成 word-level 和 segment-level SRT 字幕文件
4. 支持断点续传，跳过已生成的字幕文件
5. 自动排除 macOS 生成的点文件

路径说明:
输入:
- 音频文件: /media/dhl/audio/scifi/mp3_merge/[故事索引]/story.mp3

输出:
- Word-level 字幕: /mnt/dhl/audio/scifi/word_level_srt/[故事索引].srt
- Segment-level 字幕: /mnt/dhl/audio/scifi/seg_level_srt/[故事索引].srt

使用方法:
1. 基本使用: python generate_subtitles_with_nvasr.py
2. 强制重新处理: python generate_subtitles_with_nvasr.py -f
3. 指定故事索引范围: python generate_subtitles_with_nvasr.py --start 1 --end 10
4. 只处理指定故事: python generate_subtitles_with_nvasr.py --story 5
5. 指定模型: python generate_subtitles_with_nvasr.py --model nvidia/parakeet-tdt-0.6b-v2

注意:
- 需要安装 NVIDIA NeMo 和相关依赖: pip install nemo_toolkit[asr]
- 需要 NVIDIA GPU 支持
"""

import os
import sys
import time
import argparse
import glob
import re
import json
import subprocess
import platform
from pathlib import Path
from tqdm import tqdm
from typing import Dict, List, Optional, Tuple


def get_audio_files_info() -> Dict:
    """扫描音频文件信息"""
    audio_dir = "/media/dhl/audio/scifi/mp3_merge"
    
    if not os.path.exists(audio_dir):
        print(f"❌ 音频目录不存在: {audio_dir}")
        return {}
    
    audio_files = {}
    
    for story_dir in glob.glob(os.path.join(audio_dir, "*")):
        if not os.path.isdir(story_dir):
            continue
            
        story_index = os.path.basename(story_dir)
        
        # 排除以点开头的目录（如 .DS_Store 等）
        if story_index.startswith("."):
            continue
            
        # 检查是否为数字索引
        if not re.match(r'^\d+$', story_index):
            continue
            
        audio_file = os.path.join(story_dir, "story.mp3")
        
        if os.path.exists(audio_file):
            # 验证文件大小（大于 1MB 才认为有效）
            file_size = os.path.getsize(audio_file)
            if file_size > 1024 * 1024:
                audio_files[story_index] = {
                    "audio_path": audio_file,
                    "size_mb": file_size / 1024 / 1024
                }
                print(f"✅ 发现音频文件: 故事 {story_index} ({file_size / 1024 / 1024:.1f} MB)")
            else:
                print(f"⚠️  音频文件过小，跳过: 故事 {story_index} ({file_size} bytes)")
    
    return audio_files


def get_existing_subtitles() -> Tuple[set, set]:
    """获取已存在的字幕文件"""
    word_level_dir = "/mnt/dhl/audio/scifi/word_level_srt"
    seg_level_dir = "/mnt/dhl/audio/scifi/seg_level_srt"
    
    existing_word = set()
    existing_seg = set()
    
    # 检查 word-level 字幕
    if os.path.exists(word_level_dir):
        for srt_file in glob.glob(os.path.join(word_level_dir, "*.srt")):
            basename = os.path.basename(srt_file)
            if basename.startswith("."):
                continue
            match = re.match(r"(\d+)\.srt", basename)
            if match:
                story_index = match.group(1)
                # 验证文件大小
                file_size = os.path.getsize(srt_file)
                if file_size > 100:  # 大于 100 字节才认为有效
                    existing_word.add(story_index)
                    print(f"✅ 发现现有 word-level 字幕: 故事 {story_index}")
    
    # 检查 segment-level 字幕
    if os.path.exists(seg_level_dir):
        for srt_file in glob.glob(os.path.join(seg_level_dir, "*.srt")):
            basename = os.path.basename(srt_file)
            if basename.startswith("."):
                continue
            match = re.match(r"(\d+)\.srt", basename)
            if match:
                story_index = match.group(1)
                # 验证文件大小
                file_size = os.path.getsize(srt_file)
                if file_size > 100:  # 大于 100 字节才认为有效
                    existing_seg.add(story_index)
                    print(f"✅ 发现现有 segment-level 字幕: 故事 {story_index}")
    
    return existing_word, existing_seg


def format_timestamp_for_srt(seconds: float) -> str:
    """将秒数转换为 SRT 时间格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"


def create_word_level_srt(word_timestamps: List[Dict], output_path: str) -> bool:
    """创建 word-level SRT 字幕文件"""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, word_info in enumerate(word_timestamps, 1):
                start_time = format_timestamp_for_srt(word_info['start'])
                end_time = format_timestamp_for_srt(word_info['end'])
                word = word_info['word'].strip()
                
                # 跳过空白单词
                if not word:
                    continue
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{word}\n\n")
        
        print(f"✅ Word-level SRT 生成成功: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Word-level SRT 生成失败: {e}")
        return False


def create_segment_level_srt(segment_timestamps: List[Dict], output_path: str) -> bool:
    """创建 segment-level SRT 字幕文件"""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment_info in enumerate(segment_timestamps, 1):
                start_time = format_timestamp_for_srt(segment_info['start'])
                end_time = format_timestamp_for_srt(segment_info['end'])
                text = segment_info['segment'].strip()
                
                # 跳过空白段落
                if not text:
                    continue
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")
        
        print(f"✅ Segment-level SRT 生成成功: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Segment-level SRT 生成失败: {e}")
        return False


def check_nemo_asr_available():
    """检查当前环境中是否可用 NeMo ASR"""
    try:
        import nemo.collections.asr
        print("✅ NeMo ASR 可用")
        return True
    except ImportError as e:
        print(f"❌ NeMo ASR 不可用: {e}")
        print("   请安装 NeMo ASR:")
        print("   pip install nemo_toolkit[asr]")
        return False
    except Exception as e:
        print(f"❌ 检查 NeMo ASR 时出错: {e}")
        return False


def run_asr_with_nemo(audio_file: str, model_name: str = "nvidia/parakeet-tdt-0.6b-v2") -> Optional[Tuple[List[Dict], List[Dict]]]:
    """使用当前环境运行 NeMo ASR"""
    
    # 创建临时 Python 脚本
    import tempfile
    
    temp_script = f'''
import sys
import json
import torch
import nemo.collections.asr as nemo_asr

try:
    print("加载 ASR 模型: {model_name}")
    asr_model = nemo_asr.models.ASRModel.from_pretrained(model_name="{model_name}")
    
    # 应用内存优化设置 - 参考: https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2/discussions/46
    print("应用内存优化设置...")
    asr_model.change_attention_model("rel_pos_local_attn", [256, 256])
    asr_model.change_subsampling_conv_chunking_factor(1)
    asr_model = asr_model.to(torch.bfloat16)
    
    print("开始转录音频: {audio_file}")
    output = asr_model.transcribe(["{audio_file}"], timestamps=True)
    
    # 提取时间戳信息
    word_timestamps = output[0].timestamp['word']
    segment_timestamps = output[0].timestamp['segment']
    
    # 输出 JSON 格式结果
    result = {{
        "word_timestamps": word_timestamps,
        "segment_timestamps": segment_timestamps
    }}
    
    print("=== ASR_RESULT_START ===")
    print(json.dumps(result, ensure_ascii=False))
    print("=== ASR_RESULT_END ===")
    
except Exception as e:
    print(f"ASR 处理失败: {{e}}", file=sys.stderr)
    sys.exit(1)
'''
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(temp_script)
            temp_script_path = f.name
        
        # 直接使用当前python环境执行脚本
        cmd = f"python {temp_script_path}"
        
        print(f"🚀 开始 ASR 转录...")
        start_time = time.time()
        
        # 执行 ASR
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600  # 10分钟超时
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        if result.returncode == 0:
            print(f"✅ ASR 转录完成，耗时: {processing_time:.1f}秒")
            
            # 解析结果
            output = result.stdout
            start_marker = "=== ASR_RESULT_START ==="
            end_marker = "=== ASR_RESULT_END ==="
            
            start_idx = output.find(start_marker)
            end_idx = output.find(end_marker)
            
            if start_idx != -1 and end_idx != -1:
                json_str = output[start_idx + len(start_marker):end_idx].strip()
                try:
                    asr_result = json.loads(json_str)
                    word_timestamps = asr_result["word_timestamps"]
                    segment_timestamps = asr_result["segment_timestamps"]
                    
                    print(f"📊 识别结果: {len(word_timestamps)} 个单词, {len(segment_timestamps)} 个段落")
                    return word_timestamps, segment_timestamps
                    
                except json.JSONDecodeError as e:
                    print(f"❌ 解析 ASR 结果失败: {e}")
                    print(f"原始输出: {output}")
                    return None
            else:
                print(f"❌ 未找到 ASR 结果标记")
                print(f"完整输出: {output}")
                return None
        else:
            print(f"❌ ASR 执行失败 (返回码: {result.returncode})")
            print(f"错误输出: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("❌ ASR 处理超时")
        return None
    except Exception as e:
        print(f"❌ ASR 处理出错: {e}")
        return None
    finally:
        # 清理临时文件
        try:
            if 'temp_script_path' in locals():
                os.unlink(temp_script_path)
        except Exception:
            pass


def save_progress_log(stats: Dict, session_stats: Dict):
    """保存处理进度日志"""
    try:
        log_file = "/mnt/dhl/audio/scifi/subtitle_generation_progress.json"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        log_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_audio_files": stats["total_audio_files"],
            "existing_word_subtitles": stats["existing_word_subtitles"],
            "existing_seg_subtitles": stats["existing_seg_subtitles"],
            "pending_processing": stats["pending_processing"],
            "session_successful": session_stats["successful"],
            "session_failed": session_stats["failed"],
            "session_word_generated": session_stats["word_generated"],
            "session_seg_generated": session_stats["seg_generated"],
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        print(f"📝 进度日志已保存: {log_file}")
        
    except Exception as e:
        print(f"⚠️  保存进度日志失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="NVIDIA ASR 字幕生成器 - 为音频文件生成 word-level 和 segment-level 字幕"
    )
    
    parser.add_argument(
        "-f", "--force", 
        action="store_true", 
        help="强制重新处理，忽略已有字幕文件"
    )
    parser.add_argument("--start", type=int, help="指定开始处理的故事索引")
    parser.add_argument("--end", type=int, help="指定结束处理的故事索引")
    parser.add_argument("--story", help="只处理指定的故事索引")
    parser.add_argument(
        "--model", 
        default="nvidia/parakeet-tdt-0.6b-v2",
        help="指定 ASR 模型名称 (默认: nvidia/parakeet-tdt-0.6b-v2)"
    )
    
    args = parser.parse_args()
    
    # 验证参数
    if args.start is not None and args.end is not None:
        if args.start > args.end:
            print("❌ 错误：开始索引不能大于结束索引")
            return
        if args.start <= 0 or args.end <= 0:
            print("❌ 错误：索引必须大于 0")
            return
    
    print("🎙️  NVIDIA ASR 字幕生成器")
    print("=" * 50)
    print(f"🖥️  当前操作系统: {platform.system()}")
    print(f"🤖 ASR 模型: {args.model}")
    
    # 步骤 1: 检查 NeMo ASR 是否可用
    print(f"\n🔍 步骤 1: 检查 NeMo ASR 环境...")
    if not check_nemo_asr_available():
        print("❌ NeMo ASR 不可用，请确保已正确安装")
        return
    
    # 步骤 2: 扫描音频文件
    print(f"\n🔍 步骤 2: 扫描音频文件...")
    audio_files = get_audio_files_info()
    
    if not audio_files:
        print("❌ 未找到任何有效的音频文件")
        return
    
    print(f"📊 找到 {len(audio_files)} 个音频文件")
    
    # 步骤 3: 检查已存在的字幕文件
    print(f"\n🔍 步骤 3: 检查已存在的字幕文件...")
    existing_word, existing_seg = get_existing_subtitles()
    
    # 应用过滤条件
    filtered_audio_files = {}
    for story_index, audio_info in audio_files.items():
        # 应用索引范围过滤
        try:
            story_num = int(story_index)
            if args.start is not None and story_num < args.start:
                continue
            if args.end is not None and story_num > args.end:
                continue
        except ValueError:
            continue
        
        # 应用指定故事过滤
        if args.story and story_index != args.story:
            continue
        
        filtered_audio_files[story_index] = audio_info
    
    # 确定需要处理的文件
    files_to_process = {}
    for story_index, audio_info in filtered_audio_files.items():
        need_word = args.force or story_index not in existing_word
        need_seg = args.force or story_index not in existing_seg
        
        if need_word or need_seg:
            files_to_process[story_index] = {
                **audio_info,
                "need_word": need_word,
                "need_seg": need_seg
            }
    
    # 统计信息
    stats = {
        "total_audio_files": len(audio_files),
        "filtered_audio_files": len(filtered_audio_files),
        "existing_word_subtitles": len(existing_word & set(filtered_audio_files.keys())),
        "existing_seg_subtitles": len(existing_seg & set(filtered_audio_files.keys())),
        "pending_processing": len(files_to_process),
    }
    
    print(f"\n📈 处理统计:")
    print(f"   总音频文件数: {stats['total_audio_files']}")
    print(f"   过滤后文件数: {stats['filtered_audio_files']}")
    print(f"   已有 word-level 字幕: {stats['existing_word_subtitles']}")
    print(f"   已有 segment-level 字幕: {stats['existing_seg_subtitles']}")
    print(f"   待处理文件数: {stats['pending_processing']}")
    
    if stats["pending_processing"] == 0:
        print(f"\n🎉 所有字幕文件都已存在！")
        return
    
    # 确保输出目录存在
    os.makedirs("/mnt/dhl/audio/scifi/word_level_srt", exist_ok=True)
    os.makedirs("/mnt/dhl/audio/scifi/seg_level_srt", exist_ok=True)
    
    # 开始处理
    print(f"\n🔄 开始字幕生成处理...")
    print(f"📝 本次将处理 {stats['pending_processing']} 个音频文件")
    
    session_stats = {
        "successful": 0, 
        "failed": 0,
        "word_generated": 0,
        "seg_generated": 0
    }
    
    try:
        start_time = time.time()
        
        with tqdm(total=stats["pending_processing"], desc="字幕生成进度") as pbar:
            for i, (story_index, file_info) in enumerate(
                sorted(files_to_process.items(), key=lambda x: int(x[0])), 1
            ):
                print(f"\n=== 处理第 {i}/{stats['pending_processing']} 个音频: 故事 {story_index} ===")
                
                audio_path = file_info["audio_path"]
                need_word = file_info["need_word"]
                need_seg = file_info["need_seg"]
                
                print(f"📝 音频文件: {audio_path}")
                print(f"📝 文件大小: {file_info['size_mb']:.1f} MB")
                print(f"📝 需要生成: {'word-level ' if need_word else ''}{'segment-level' if need_seg else ''}")
                
                # 执行 ASR
                asr_result = run_asr_with_nemo(audio_path, args.model)
                
                if asr_result is None:
                    session_stats["failed"] += 1
                    print(f"❌ 故事 {story_index} ASR 处理失败")
                    pbar.update(1)
                    continue
                
                word_timestamps, segment_timestamps = asr_result
                success = True
                
                # 生成 word-level 字幕
                if need_word:
                    word_output_path = f"/mnt/dhl/audio/scifi/word_level_srt/{story_index}.srt"
                    if create_word_level_srt(word_timestamps, word_output_path):
                        session_stats["word_generated"] += 1
                        print(f"✅ Word-level 字幕生成成功: {story_index}")
                    else:
                        success = False
                        print(f"❌ Word-level 字幕生成失败: {story_index}")
                
                # 生成 segment-level 字幕
                if need_seg:
                    seg_output_path = f"/mnt/dhl/audio/scifi/seg_level_srt/{story_index}.srt"
                    if create_segment_level_srt(segment_timestamps, seg_output_path):
                        session_stats["seg_generated"] += 1
                        print(f"✅ Segment-level 字幕生成成功: {story_index}")
                    else:
                        success = False
                        print(f"❌ Segment-level 字幕生成失败: {story_index}")
                
                if success:
                    session_stats["successful"] += 1
                    print(f"✅ 故事 {story_index} 字幕生成完成")
                else:
                    session_stats["failed"] += 1
                    print(f"❌ 故事 {story_index} 字幕生成部分失败")
                
                pbar.update(1)
                
                # 处理间隔
                if i < stats["pending_processing"]:
                    time.sleep(2)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 保存进度日志
        save_progress_log(stats, session_stats)
        
        # 结果统计
        print(f"\n=== 🎉 字幕生成完成 ===")
        print(f"✅ 本次成功处理: {session_stats['successful']} 个音频文件")
        print(f"❌ 本次处理失败: {session_stats['failed']} 个音频文件")
        print(f"📝 生成 word-level 字幕: {session_stats['word_generated']} 个")
        print(f"📝 生成 segment-level 字幕: {session_stats['seg_generated']} 个")
        print(f"⏱️  本次耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")
        
        if session_stats["successful"] > 0:
            avg_time = total_time / session_stats["successful"]
            print(f"📊 平均每个音频: {avg_time:.1f} 秒")
        
        if stats["pending_processing"] > 0:
            success_rate = session_stats["successful"] / stats["pending_processing"] * 100
            print(f"📊 本次成功率: {success_rate:.1f}%")
        
        print(f"📁 Word-level 字幕目录: /mnt/dhl/audio/scifi/word_level_srt")
        print(f"📁 Segment-level 字幕目录: /mnt/dhl/audio/scifi/seg_level_srt")
        
        if session_stats["failed"] > 0:
            print(f"\n⚠️  有 {session_stats['failed']} 个音频处理失败，可以重新运行程序重试")
    
    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断了程序执行")
        print(f"✅ 已成功处理: {session_stats['successful']} 个音频")
        print(f"❌ 处理失败: {session_stats['failed']} 个音频")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        print(f"✅ 已成功处理: {session_stats['successful']} 个音频")
        print(f"❌ 处理失败: {session_stats['failed']} 个音频")


if __name__ == "__main__":
    main() 