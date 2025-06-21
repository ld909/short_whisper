#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Podcast 语音识别和说话人识别脚本
使用 WhisperX 对音频文件进行语音转文字和说话人识别

📚 功能说明:
- 扫描指定目录中的 MP3 音频文件
- 使用 WhisperX 进行高精度语音识别
- 进行说话人识别（Speaker Diarization）
- 生成带时间戳和说话人标签的转录文本
- 支持可调节批量大小以优化内存使用和处理速度
- 自动排除Mac系统产生的点文件

📥 输入信息:
- 默认输入目录: audio_ficition/podcast/
- 支持文件格式: .mp3, .wav, .m4a, .flac, .ogg
- 自动排除以点开头的Mac系统文件
- 批量大小默认为16，可通过--batch-size参数调节（推荐范围1-16）

📤 输出信息:
- 转录文本文件: {filename}_transcript.txt
- 说话人识别结果: {filename}_speakers.json
- 详细时间戳文件: {filename}_detailed.json

💡 使用示例:
python podcast_speaker_recognition.py                          # 处理当前目录所有音频文件
python podcast_speaker_recognition.py --file t.mp3             # 处理指定文件
python podcast_speaker_recognition.py --preview                # 预览模式
python podcast_speaker_recognition.py --hf-token YOUR_TOKEN    # 设置 HuggingFace Token
python podcast_speaker_recognition.py --batch-size 4           # 设置批量大小为4（默认为16）
python podcast_speaker_recognition.py --model base --batch-size 8 --device cuda  # 组合设置
"""

import os
import glob
import json
import argparse
import platform
import time
from pathlib import Path
import sys
import warnings

try:
    import whisperx
    import gc
    WHISPERX_AVAILABLE = True
    
    # 修复TF32兼容性问题
    try:
        import torch
        # 明确禁用TF32来避免兼容性问题和警告
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        print("✅ 已禁用TF32以确保兼容性")
    except ImportError:
        pass  # 如果torch未安装，会在后续检查中处理
        
except ImportError:
    WHISPERX_AVAILABLE = False
    print("⚠️  WhisperX 未安装。请运行: pip install whisperx")

# ============ 配置参数 ============
DEFAULT_INPUT_DIR = "."
SUPPORTED_FORMATS = [".mp3", ".wav", ".m4a", ".flac", ".ogg"]
DEFAULT_MODEL = "turbo"
DEFAULT_BATCH_SIZE = 16
DEFAULT_COMPUTE_TYPE = "float16"
HF_TOKEN = None  # 请在命令行参数中提供或在此设置您的 HuggingFace Token
# ===================================

# 禁用TF32以确保兼容性（修复TF32相关的IOT错误）
import torch
torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False

# 设置环境变量来处理CUDNN兼容性问题
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'  # 同步启动以更好地捕获错误
os.environ['TORCH_USE_CUDA_DSA'] = '1'    # 启用CUDA动态并行调试支持

# 处理libcudnn库缺失问题的环境变量设置
if platform.system() == "Linux":
    # 尝试设置LD_LIBRARY_PATH以包含可能的CUDNN路径
    current_ld_path = os.environ.get('LD_LIBRARY_PATH', '')
    possible_cudnn_paths = [
        '/usr/local/cuda/lib64',
        '/usr/local/cuda-12/lib64',
        '/usr/local/cuda-11/lib64',
        '/opt/cuda/lib64',
        '/usr/lib/x86_64-linux-gnu'
    ]
    
    for path in possible_cudnn_paths:
        if os.path.exists(path) and path not in current_ld_path:
            if current_ld_path:
                current_ld_path += ':' + path
            else:
                current_ld_path = path
    
    if current_ld_path:
        os.environ['LD_LIBRARY_PATH'] = current_ld_path

# 添加CUDNN兼容性检查
def check_cudnn_compatibility():
    """检查CUDNN兼容性并提供解决方案"""
    try:
        import torch
        if torch.cuda.is_available():
            # 尝试进行一个简单的CUDA操作来测试CUDNN
            test_tensor = torch.randn(2, 3, 4, 4).cuda()
            conv = torch.nn.Conv2d(3, 16, 3).cuda()
            result = conv(test_tensor)
            return True, "CUDNN兼容性检查通过"
    except Exception as e:
        error_msg = str(e)
        if "libcudnn" in error_msg:
            suggestion = """
CUDNN库缺失或不兼容。请尝试以下解决方案：

1. 安装兼容的CUDNN版本：
   conda install cudnn -c conda-forge
   
2. 或使用pip安装：
   pip install nvidia-cudnn-cu12
   
3. 设置环境变量（如果手动安装）：
   export LD_LIBRARY_PATH=/path/to/cudnn/lib64:$LD_LIBRARY_PATH
   
4. 检查CUDA版本兼容性：
   nvidia-smi
   nvcc --version
            """
            return False, f"CUDNN错误: {error_msg}\n{suggestion}"
        return False, f"CUDA错误: {error_msg}"
    
    return False, "CUDA不可用"

print("✅ 已禁用TF32以确保兼容性")

def setup_environment_variables():
    """设置环境变量以优化性能和兼容性"""
    env_vars = {
        'TOKENIZERS_PARALLELISM': 'false',  # 避免tokenizers警告
        'OMP_NUM_THREADS': '1',             # 避免多线程冲突
        'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:128',  # 优化CUDA内存分配
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    print("🔧 已设置环境变量以优化兼容性")

setup_environment_variables()

def check_system_compatibility():
    """检查系统兼容性并返回推荐配置"""
    system_info = {
        'system': platform.system(),
        'machine': platform.machine(),
        'device': 'cpu',
        'compute_type': 'int8',
        'batch_size': DEFAULT_BATCH_SIZE
    }
    
    # 根据内存设置，macOS 不启用 GPU 加速
    if system_info['system'] == 'Linux':
        try:
            import torch
            if torch.cuda.is_available():
                system_info['device'] = 'cuda'
                system_info['compute_type'] = 'float16'
                system_info['batch_size'] = DEFAULT_BATCH_SIZE
                print("✅ 检测到 CUDA GPU，将使用 GPU 加速")
            else:
                print("ℹ️  未检测到 CUDA GPU，将使用 CPU")
        except ImportError:
            print("⚠️  PyTorch 未安装，将使用 CPU")
    else:
        print(f"ℹ️  检测到 {system_info['system']} 系统，将使用 CPU（推荐配置）")
    
    print(f"🔧 推荐配置: 设备={system_info['device']}, 计算类型={system_info['compute_type']}, 批量大小={system_info['batch_size']}")
    
    return system_info


def get_audio_files(input_dir):
    """获取目录中的音频文件，排除Mac系统文件"""
    if not os.path.exists(input_dir):
        print(f"❌ 输入目录不存在: {input_dir}")
        return []
    
    audio_files = []
    skipped_files = []
    
    # 搜索所有支持的音频格式
    for fmt in SUPPORTED_FORMATS:
        pattern = os.path.join(input_dir, f"*{fmt}")
        files = glob.glob(pattern)
        
        for file_path in files:
            filename = os.path.basename(file_path)
            
            # 排除以点开头的Mac系统文件
            if filename.startswith(".") or filename.startswith("._"):
                skipped_files.append(filename)
                continue
                
            audio_files.append(file_path)
    
    if skipped_files:
        print(f"🚫 跳过 {len(skipped_files)} 个Mac系统文件: {', '.join(skipped_files)}")
    
    # 按文件名排序
    audio_files.sort()
    
    print(f"📊 找到 {len(audio_files)} 个音频文件")
    for i, file_path in enumerate(audio_files, 1):
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
        print(f"  {i:2d}. {os.path.basename(file_path)} ({file_size:.1f} MB)")
    
    return audio_files


def check_existing_outputs(audio_file):
    """检查是否已存在输出文件"""
    base_name = os.path.splitext(audio_file)[0]
    
    outputs = {
        'transcript': f"{base_name}_transcript.txt",
        'speakers': f"{base_name}_speakers.json", 
        'detailed': f"{base_name}_detailed.json"
    }
    
    existing = {}
    for key, file_path in outputs.items():
        existing[key] = os.path.exists(file_path)
    
    return existing, outputs


def save_transcript_text(result, output_file):
    """保存转录文本到文件"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for segment in result.get('segments', []):
                start_time = segment.get('start', 0)
                end_time = segment.get('end', 0)
                text = segment.get('text', '').strip()
                speaker = segment.get('speaker', 'UNKNOWN')
                
                # 格式化时间戳
                start_min, start_sec = divmod(start_time, 60)
                end_min, end_sec = divmod(end_time, 60)
                
                f.write(f"[{int(start_min):02d}:{start_sec:05.2f} -> {int(end_min):02d}:{end_sec:05.2f}] {speaker}: {text}\n")
        
        print(f"✅ 转录文本已保存: {output_file}")
        
    except Exception as e:
        print(f"❌ 保存转录文本失败: {e}")


def save_speakers_summary(result, output_file):
    """保存说话人识别摘要"""
    try:
        # 统计说话人信息
        speakers_stats = {}
        total_duration = 0
        
        for segment in result.get('segments', []):
            speaker = segment.get('speaker', 'UNKNOWN')
            duration = segment.get('end', 0) - segment.get('start', 0)
            
            if speaker not in speakers_stats:
                speakers_stats[speaker] = {
                    'total_duration': 0,
                    'segment_count': 0,
                    'text_length': 0
                }
            
            speakers_stats[speaker]['total_duration'] += duration
            speakers_stats[speaker]['segment_count'] += 1
            speakers_stats[speaker]['text_length'] += len(segment.get('text', ''))
            total_duration += duration
        
        # 计算说话时间比例
        for speaker in speakers_stats:
            speakers_stats[speaker]['percentage'] = (
                speakers_stats[speaker]['total_duration'] / total_duration * 100
                if total_duration > 0 else 0
            )
        
        summary = {
            'total_speakers': len(speakers_stats),
            'total_duration': total_duration,
            'speakers': speakers_stats,
            'processing_info': {
                'language': result.get('language', 'unknown'),
                'total_segments': len(result.get('segments', []))
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 说话人摘要已保存: {output_file}")
        
        # 显示摘要信息
        print(f"📊 识别到 {len(speakers_stats)} 个说话人:")
        for speaker, stats in speakers_stats.items():
            duration_min = stats['total_duration'] / 60
            print(f"  - {speaker}: {duration_min:.1f}分钟 ({stats['percentage']:.1f}%), {stats['segment_count']}段话")
        
    except Exception as e:
        print(f"❌ 保存说话人摘要失败: {e}")


def save_detailed_results(result, diarize_segments, output_file):
    """保存详细的识别结果"""
    try:
        detailed_data = {
            'transcription_result': result,
            'diarization_segments': diarize_segments.to_dict() if hasattr(diarize_segments, 'to_dict') else str(diarize_segments),
            'metadata': {
                'processing_time': time.time(),
                'language': result.get('language', 'unknown'),
                'total_segments': len(result.get('segments', []))
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"✅ 详细结果已保存: {output_file}")
        
    except Exception as e:
        print(f"❌ 保存详细结果失败: {e}")


def process_audio_file(
    audio_file,
    model_name=DEFAULT_MODEL,
    device='cpu',
    compute_type='int8',
    batch_size=DEFAULT_BATCH_SIZE,
    min_speakers=None,
    max_speakers=None,
    force_regenerate=False
):
    """处理单个音频文件"""
    print(f"\n=== 🎵 处理音频文件: {os.path.basename(audio_file)} ===")
    
    # 检查文件是否存在
    if not os.path.exists(audio_file):
        print(f"❌ 文件不存在: {audio_file}")
        return False
    
    # 检查已存在的输出文件
    existing, output_files = check_existing_outputs(audio_file)
    
    if not force_regenerate and all(existing.values()):
        print(f"⏭️  所有输出文件已存在，跳过处理")
        for key, file_path in output_files.items():
            if existing[key]:
                print(f"   ✓ {key}: {file_path}")
        return True
    
    if not WHISPERX_AVAILABLE:
        print(f"❌ WhisperX 未安装，无法处理")
        return False
    
    try:
        start_time = time.time()
        
        print(f"🔄 开始处理...")
        print(f"   模型: {model_name}")
        print(f"   设备: {device}")
        print(f"   计算类型: {compute_type}")
        print(f"   批量大小: {batch_size}")
        
        # 1. 加载模型并转录
        print(f"📥 加载转录模型...")
        model = whisperx.load_model(model_name, device, compute_type=compute_type)
        
        print(f"🎵 加载音频文件...")
        audio = whisperx.load_audio(audio_file)
        
        print(f"🔄 开始转录...")
        result = model.transcribe(audio, batch_size=batch_size)
        print(f"✅ 转录完成，识别语言: {result.get('language', 'unknown')}")
        
        # 清理模型以释放内存
        del model
        if device == 'cuda':
            import torch
            gc.collect()
            torch.cuda.empty_cache()
        
        # 2. 对齐获得词级别时间戳
        print(f"🎯 加载对齐模型...")
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
        result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
        print(f"✅ 对齐完成")
        
        # 清理对齐模型
        del model_a
        if device == 'cuda':
            gc.collect()
            torch.cuda.empty_cache()
        
        # 3. 说话人识别
        if HF_TOKEN:
            print(f"👥 开始说话人识别...")
            diarize_model = whisperx.diarize.DiarizationPipeline(use_auth_token=HF_TOKEN, device=device)
            
            # 设置说话人数量限制
            diarize_kwargs = {}
            if min_speakers is not None:
                diarize_kwargs['min_speakers'] = min_speakers
            if max_speakers is not None:
                diarize_kwargs['max_speakers'] = max_speakers
            
            if diarize_kwargs:
                print(f"   说话人数量限制: {diarize_kwargs}")
                
            diarize_segments = diarize_model(audio, **diarize_kwargs)
            
            # 分配说话人标签到转录结果
            result = whisperx.assign_word_speakers(diarize_segments, result)
            print(f"✅ 说话人识别完成")
            
            # 清理说话人识别模型
            del diarize_model
            if device == 'cuda':
                gc.collect()
                torch.cuda.empty_cache()
        else:
            print(f"⚠️  未提供 HuggingFace Token，跳过说话人识别")
            print(f"💡 请使用 --hf-token 参数设置您的 HuggingFace Token")
            diarize_segments = None
        
        # 4. 保存结果
        print(f"💾 保存结果...")
        
        # 保存转录文本
        save_transcript_text(result, output_files['transcript'])
        
        # 保存说话人摘要（如果有说话人识别结果）
        if HF_TOKEN and 'segments' in result and len(result['segments']) > 0:
            # 检查是否有说话人信息
            has_speaker_info = any('speaker' in seg for seg in result['segments'])
            if has_speaker_info:
                save_speakers_summary(result, output_files['speakers'])
            else:
                print(f"⚠️  转录结果中没有说话人信息")
        
        # 保存详细结果
        save_detailed_results(result, diarize_segments, output_files['detailed'])
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"🎉 处理完成！")
        print(f"⏱️  总耗时: {total_time:.1f} 秒 ({total_time/60:.1f} 分钟)")
        
        return True
        
    except Exception as e:
        print(f"❌ 处理过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Podcast 语音识别和说话人识别工具 - 使用 WhisperX",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python podcast_speaker_recognition.py                          # 处理当前目录所有音频文件
  python podcast_speaker_recognition.py --file t.mp3             # 处理指定文件
  python podcast_speaker_recognition.py --preview                # 预览模式
  python podcast_speaker_recognition.py --hf-token YOUR_TOKEN    # 设置 HuggingFace Token
  python podcast_speaker_recognition.py --min-speakers 2 --max-speakers 3  # 设置说话人数量

注意事项:
  1. 需要安装 WhisperX: pip install whisperx
  2. 说话人识别需要 HuggingFace Token: https://huggingface.co/settings/tokens
  3. Linux 系统可使用 GPU 加速，macOS 建议使用 CPU
        """)
    
    parser.add_argument("--input-dir", "-d", default=DEFAULT_INPUT_DIR, help=f"输入目录路径 (默认: {DEFAULT_INPUT_DIR})")
    parser.add_argument("--file", "-f", help="处理指定的音频文件")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"使用的 WhisperX 模型 (默认: {DEFAULT_MODEL})")
    parser.add_argument("--device", choices=['auto', 'cpu', 'cuda'], default='auto', help="计算设备 (默认: auto - 自动检测)")
    parser.add_argument("--compute-type", choices=['auto', 'float16', 'int8'], default='auto', help="计算类型 (默认: auto - 根据设备自动选择)")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help=f"批量大小 (默认: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--min-speakers", type=int, help="最小说话人数量")
    parser.add_argument("--max-speakers", type=int, help="最大说话人数量")
    parser.add_argument("--preview", action="store_true", help="预览模式，只显示会处理哪些文件")
    parser.add_argument("--force-regenerate", action="store_true", help="强制重新生成所有文件，忽略已存在的文件")
    parser.add_argument("--hf-token", help="HuggingFace Token (用于说话人识别)")
    
    args = parser.parse_args()
    
    # 设置 HuggingFace Token
    global HF_TOKEN
    if args.hf_token:
        HF_TOKEN = args.hf_token
        print(f"✅ 已设置 HuggingFace Token")
    elif not HF_TOKEN:
        print(f"⚠️  未设置 HuggingFace Token，将跳过说话人识别")
        print(f"💡 请使用 --hf-token 参数或访问 https://huggingface.co/settings/tokens 获取token")
    
    # 检查 WhisperX 可用性
    if not WHISPERX_AVAILABLE:
        print(f"❌ WhisperX 未安装")
        print(f"💡 请运行以下命令安装:")
        print(f"   pip install whisperx")
        return
    
    # 检查系统兼容性
    system_config = check_system_compatibility()
    
    # 设置设备和计算类型
    if args.device == 'auto':
        device = system_config['device']
    else:
        device = args.device
    
    if args.compute_type == 'auto':
        compute_type = system_config['compute_type']
    else:
        compute_type = args.compute_type
    
    # 使用用户指定的批量大小，如果未指定则使用默认值
    batch_size = args.batch_size
    
    print(f"\n🎵 Podcast 语音识别和说话人识别工具")
    print(f"📁 输入目录: {args.input_dir}")
    print(f"🤖 使用模型: {args.model}")
    print(f"🔧 设备配置: {device} / {compute_type} / 批量大小 {batch_size}")
    print(f"🚫 自动排除Mac系统文件 (.DS_Store等)")
    
    if args.min_speakers or args.max_speakers:
        print(f"👥 说话人数量限制: {args.min_speakers}-{args.max_speakers}")
    
    if args.force_regenerate:
        print(f"🔄 强制重新生成模式")
    
    if args.preview:
        print(f"👁️  预览模式：只显示将要处理的文件")
    
    # 获取要处理的文件列表
    if args.file:
        # 处理指定文件
        if not os.path.exists(args.file):
            print(f"❌ 指定文件不存在: {args.file}")
            return
        audio_files = [args.file]
        print(f"📄 处理指定文件: {args.file}")
    else:
        # 获取目录中的所有音频文件
        audio_files = get_audio_files(args.input_dir)
        
        if not audio_files:
            print(f"❌ 在目录 {args.input_dir} 中未找到任何音频文件")
            print(f"💡 支持的格式: {', '.join(SUPPORTED_FORMATS)}")
            return
    
    if args.preview:
        print(f"\n📋 预览模式 - 将要处理的文件:")
        for i, audio_file in enumerate(audio_files, 1):
            existing, output_files = check_existing_outputs(audio_file)
            status = "需要处理" if not all(existing.values()) or args.force_regenerate else "已完成"
            print(f"  {i:2d}. {os.path.basename(audio_file)} - {status}")
            
            if not args.force_regenerate:
                for key, exists in existing.items():
                    status_icon = "✓" if exists else "✗"
                    print(f"      {status_icon} {key}")
        return
    
    # 处理所有文件
    total_files = len(audio_files)
    successful_count = 0
    failed_count = 0
    
    try:
        for i, audio_file in enumerate(audio_files, 1):
            print(f"\n处理第 {i}/{total_files} 个文件...")
            
            success = process_audio_file(
                audio_file,
                args.model,
                device,
                compute_type,
                batch_size,
                args.min_speakers,
                args.max_speakers,
                args.force_regenerate
            )
            
            if success:
                successful_count += 1
            else:
                failed_count += 1
            
            # 在文件之间稍作停顿
            if i < total_files:
                print(f"⏳ 等待 3 秒...")
                time.sleep(3)
    
    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断了程序执行")
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        # 提供特定错误的解决建议
        if "IOT instruction" in error_msg or "core dumped" in error_msg:
            print(f"""
❌ 检测到IOT指令错误或核心转储 ({error_type}): {e}

这通常是由于以下原因之一造成的：
1. TF32兼容性问题（已尝试修复）
2. CUDNN版本不匹配或库缺失
3. PyTorch和CUDA版本不兼容
4. GPU硬件/驱动问题

建议的解决方案：
1. 重新安装兼容的CUDNN：
   conda install cudnn -c conda-forge
   
2. 重新安装PyTorch：
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   
3. 重新安装WhisperX：
   pip uninstall whisperx -y
   pip install git+https://github.com/m-bain/whisperX.git
   
4. 使用CPU模式避免GPU问题：
   python {' '.join(sys.argv)} --device cpu
   
5. 检查系统状态：
   nvidia-smi
   nvcc --version
            """)
        elif "libcudnn" in error_msg:
            print(f"""
❌ CUDNN库错误 ({error_type}): {e}

解决方案：
1. 安装CUDNN：
   conda install cudnn -c conda-forge
   
2. 或者使用pip安装：
   pip install nvidia-cudnn-cu12
   
3. 设置环境变量：
   export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
   
4. 使用CPU模式：
   python {' '.join(sys.argv)} --device cpu
            """)
        elif "torch" in error_msg.lower() or "cuda" in error_msg.lower():
            print(f"""
❌ PyTorch/CUDA相关错误 ({error_type}): {e}

解决方案：
1. 检查CUDA版本：
   nvidia-smi
   
2. 重新安装匹配的PyTorch：
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   
3. 使用CPU模式：
   python {' '.join(sys.argv)} --device cpu
            """)
        else:
            print(f"\n❌ 程序执行出错 ({error_type}): {e}")
            print(f"💡 建议尝试使用CPU模式: python {' '.join(sys.argv)} --device cpu")
    finally:
        # 显示最终统计
        print(f"\n=== 🎉 处理完成总结 ===")
        print(f"📊 总文件数: {total_files}")
        print(f"✅ 成功处理: {successful_count}")
        print(f"❌ 处理失败: {failed_count}")
        
        if successful_count > 0:
            print(f"\n📝 输出文件说明:")
            print(f"  - *_transcript.txt: 带时间戳和说话人的转录文本")
            print(f"  - *_speakers.json: 说话人识别摘要统计")
            print(f"  - *_detailed.json: 完整的识别结果数据")


if __name__ == "__main__":
    main() 