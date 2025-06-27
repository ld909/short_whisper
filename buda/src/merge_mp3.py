"""
这个脚本用于将按语言分类的短小MP3片段合并成完整的音频文件。
主要功能：
1. 自动处理多个频道、视频和语言的MP3文件
2. 验证MP3文件完整性，必要时尝试重新生成
3. 支持并行处理以提高效率
4. 提供强制重新合并和单个视频处理选项
5. 支持直接修复单个损坏的MP3文件

输入路径：
- MP3源文件路径：/Volumes/dhl/buda_videos_youtube/multi_lang_mp3 (macOS)
                /media/dhl/buda_videos_youtube/multi_lang_mp3 (Linux)
- 文本源文件路径：/Volumes/dhl/buda_videos_youtube/multi_lang_txt (macOS)
                /media/dhl/buda_videos_youtube/multi_lang_txt (Linux)

输出路径：
- 合并后MP3文件：/Volumes/dhl/buda_videos_youtube/merge_multi_lange_mp3 (macOS)
                /media/dhl/buda_videos_youtube/merge_multi_lange_mp3 (Linux)

使用方法:
1. 合并MP3: python merge_mp3.py [-l 语言列表] [-f] [-w 工作线程数] [-s 频道名/视频名]
2. 修复单个MP3: python merge_mp3.py -r MP3文件的完整路径
"""

import os
import argparse
import platform
import subprocess
import concurrent.futures
import sys
from tqdm import tqdm
import importlib.util
import tempfile  # 添加这个导入


def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 定义全局路径变量
BASE_PATH = get_base_path()
# 输入MP3目录
INPUT_MP3_PATH = os.path.join(BASE_PATH, "multi_lang_mp3")
# 输出合并MP3目录
OUTPUT_MERGE_PATH = os.path.join(BASE_PATH, "merge_multi_lange_mp3")
# 支持的语言
SUPPORTED_LANGUAGES = ["en", "ja", "vi", "ko"]
# 输入TXT目录 (优先使用generate_mp3_clips.py中使用的目录)
INPUT_TXT_PATH = os.path.join(BASE_PATH, "multi_lang_txt")
# 备用TXT目录
INPUT_TXT_PATH_BACKUP = os.path.join(BASE_PATH, "multi_lang_txt")


def import_generate_mp3_module():
    """导入 generate_mp3.py 模块以重用其功能"""
    try:
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # 搜索可能存在的generate_mp3相关文件的位置
        search_paths = [
            os.path.join(current_dir, "generate_mp3_clips.py"),  # 优先查找clips版本
            os.path.join(current_dir, "generate_mp3.py"),  # 同目录
            os.path.join(
                os.path.dirname(current_dir), "generate_mp3_clips.py"
            ),  # 父目录clips版本
            os.path.join(os.path.dirname(current_dir), "generate_mp3.py"),  # 父目录
            os.path.join(
                current_dir, "..", "generate_mp3_clips.py"
            ),  # 相对父目录clips版本
            os.path.join(current_dir, "..", "generate_mp3.py"),  # 相对父目录
        ]

        # 尝试在所有可能的位置查找文件
        found_path = None
        for path in search_paths:
            if os.path.exists(path):
                found_path = path
                break

        if not found_path:
            # 尝试查找含有generate_mp3的文件
            import glob

            all_py_files = glob.glob(os.path.join(current_dir, "*.py"))
            all_py_files.extend(
                glob.glob(os.path.join(os.path.dirname(current_dir), "*.py"))
            )

            for py_file in all_py_files:
                if "generate_mp3" in os.path.basename(py_file).lower():
                    found_path = py_file
                    break

            if not found_path:
                return None

        # 导入模块
        spec = importlib.util.spec_from_file_location("generate_mp3", found_path)
        if spec is None:
            return None

        generate_mp3 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generate_mp3)

        # 验证模块中是否包含必要的函数
        if not hasattr(generate_mp3, "text_to_mp3"):
            return None

        return generate_mp3
    except Exception as e:
        return None


def verify_mp3_file(file_path):
    """验证MP3文件是否有效"""
    try:
        cmd = ["ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"]
        result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, check=False)

        # 如果没有错误输出，则文件有效
        if not result.stderr.strip():
            return True

        return False
    except Exception as e:
        return False


def regenerate_mp3_file(mp3_path, generate_mp3):
    """重新生成损坏的MP3文件"""
    try:
        # 从MP3文件路径推断出TXT文件路径
        # 假设目录结构: multi_lang_mp3/channel/video_name/language/number.mp3
        parts = mp3_path.split(os.sep)

        if len(parts) < 5:
            return False

        # 解析信息
        # 兼容子目录可能不包含完整路径的情况
        if "multi_lang_mp3" in parts:
            relative_idx = parts.index("multi_lang_mp3")
        else:
            # 尝试匹配路径的最后几个部分
            # 假设格式是 */channel/video_name/language/number.mp3
            if len(parts) < 4:  # 至少需要4个部分
                return False
            # 假设倒数第4个是channel，倒数第3个是video_name，倒数第2个是language
            relative_idx = len(parts) - 4

        if relative_idx < 0 or relative_idx + 3 >= len(parts):
            return False

        channel = parts[relative_idx]
        video_name = parts[relative_idx + 1]
        language = parts[relative_idx + 2]
        file_number = os.path.splitext(parts[-1])[0]  # 不带扩展名的文件编号

        # 构建对应的TXT文件路径（优先使用INPUT_TXT_PATH目录）
        txt_file_path = os.path.join(
            INPUT_TXT_PATH, channel, language, f"{video_name}.txt"
        )

        # 如果在主TXT目录中找不到文件，尝试备用目录
        if not os.path.exists(txt_file_path):
            backup_txt_path = os.path.join(
                INPUT_TXT_PATH_BACKUP, channel, language, f"{video_name}.txt"
            )

            if os.path.exists(backup_txt_path):
                txt_file_path = backup_txt_path
            else:
                # 尝试在频道的子目录中寻找
                # 先在主目录中查找
                if os.path.exists(os.path.join(INPUT_TXT_PATH, channel)):
                    for subdir in os.listdir(os.path.join(INPUT_TXT_PATH, channel)):
                        sub_txt_path = os.path.join(
                            INPUT_TXT_PATH,
                            channel,
                            subdir,
                            language,
                            f"{video_name}.txt",
                        )
                        if os.path.exists(sub_txt_path):
                            txt_file_path = sub_txt_path
                            break

                # 如果在主目录没找到，再在备用目录中查找
                if not os.path.exists(txt_file_path) and os.path.exists(
                    os.path.join(INPUT_TXT_PATH_BACKUP, channel)
                ):
                    for subdir in os.listdir(
                        os.path.join(INPUT_TXT_PATH_BACKUP, channel)
                    ):
                        sub_txt_path = os.path.join(
                            INPUT_TXT_PATH_BACKUP,
                            channel,
                            subdir,
                            language,
                            f"{video_name}.txt",
                        )
                        if os.path.exists(sub_txt_path):
                            txt_file_path = sub_txt_path
                            break

                if not os.path.exists(txt_file_path):
                    return False

        # 读取TXT文件中对应行的文本
        try:
            with open(txt_file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            return False

        try:
            file_idx = int(file_number) - 1
            if not lines or file_idx < 0 or file_idx >= len(lines):
                return False
        except ValueError:
            return False

        # 获取对应行的文本
        text = lines[file_idx].strip()

        if not text:
            return False

        # 确保目标目录存在
        target_dir = os.path.dirname(mp3_path)
        os.makedirs(target_dir, exist_ok=True)

        # 调用generate_mp3模块中的text_to_mp3函数重新生成MP3
        if generate_mp3:
            if not hasattr(generate_mp3, "text_to_mp3"):
                return False

            try:
                success = generate_mp3.text_to_mp3(text, mp3_path, language)
                if success:
                    # 验证文件是否实际创建成功
                    if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0:
                        return True
                    else:
                        return False
                else:
                    return False
            except Exception as e:
                return False
        else:
            return False
    except Exception as e:
        return False


def merge_mp3_files(input_dir, output_file, force=False):
    """使用ffmpeg合并一个目录下的所有MP3文件成为一个单一的MP3"""
    # 如果输出文件已存在且不强制重新生成，则跳过
    if os.path.exists(output_file) and not force:
        print(f"输出文件已存在，跳过: {output_file}")
        return True

    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")

    # 检查所有MP3文件
    mp3_files = [
        f for f in os.listdir(input_dir) if f.endswith(".mp3") and not f.startswith(".")
    ]
    if not mp3_files:
        print(f"警告: 目录 {input_dir} 中没有MP3文件")
        return False

    # 按文件名中的数字排序
    mp3_files.sort(key=lambda f: int(os.path.splitext(f)[0]))

    # 导入generate_mp3模块
    generate_mp3 = import_generate_mp3_module()

    # 验证所有MP3文件是否有效，并修复损坏的文件
    valid_files = []
    invalid_files = []
    fixed_files = []

    print(f"\n===== 开始验证 {len(mp3_files)} 个MP3文件 =====")
    for mp3_file in mp3_files:
        file_path = os.path.join(input_dir, mp3_file)

        # 检查文件是否存在且大小大于0
        if not os.path.exists(file_path):
            invalid_files.append((mp3_file, "不存在"))
        elif os.path.getsize(file_path) == 0:
            invalid_files.append((mp3_file, "大小为0"))
        else:
            # 验证文件格式
            if not verify_mp3_file(file_path):
                invalid_files.append((mp3_file, "格式无效"))
            else:
                valid_files.append(mp3_file)

    print(f"\n有效文件: {len(valid_files)}/{len(mp3_files)}")
    print(f"无效文件: {len(invalid_files)}/{len(mp3_files)}")

    # 尝试修复无效文件
    if invalid_files and generate_mp3:
        print(f"\n===== 尝试修复 {len(invalid_files)} 个无效文件 =====")
        for mp3_file, reason in invalid_files:
            file_path = os.path.join(input_dir, mp3_file)

            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 尝试重新生成文件
            if regenerate_mp3_file(file_path, generate_mp3):
                # 验证重新生成的文件
                if (
                    os.path.exists(file_path)
                    and os.path.getsize(file_path) > 0
                    and verify_mp3_file(file_path)
                ):
                    valid_files.append(mp3_file)
                    fixed_files.append(mp3_file)
                else:
                    pass  # 修复尝试失败
            else:
                pass  # 无法修复文件

        print(f"\n成功修复的文件: {len(fixed_files)}/{len(invalid_files)}")

    # 更新mp3_files为有效的文件列表
    mp3_files = sorted(valid_files, key=lambda f: int(os.path.splitext(f)[0]))
    print(f"\n最终有效文件数: {len(mp3_files)}")

    if not mp3_files:
        print(f"警告: 目录 {input_dir} 中没有有效的MP3文件")
        return False

    # 更改合并策略，使用FFmpeg完整解码重新编码所有片段
    # 这确保语速保持一致并且不会有空白段
    print(f"使用完整解码重新编码方法合并 {len(mp3_files)} 个MP3文件...")

    # 使用系统临时目录避免路径过长问题
    temp_dir = None
    try:
        # 创建一个临时文件夹用于中间文件，使用系统临时目录
        temp_dir = tempfile.mkdtemp(prefix="merge_mp3_")
        print(f"创建临时目录: {temp_dir}")

        # 首先将所有MP3转换为WAV，确保采样率和格式一致
        wav_files = []
        print("步骤1: 转换MP3为标准WAV格式...")

        for i, mp3_file in enumerate(mp3_files):
            src_file = os.path.join(input_dir, mp3_file)
            temp_wav = os.path.join(temp_dir, f"{i:04d}.wav")
            wav_files.append(temp_wav)

            # 将MP3转换为统一采样率和格式的WAV
            convert_cmd = [
                "ffmpeg",
                "-y",
                "-v",
                "error",  # 只显示错误
                "-i",
                src_file,
                "-ar",
                "44100",  # 统一采样率
                "-ac",
                "2",  # 统一声道数
                "-acodec",
                "pcm_s16le",  # 统一编码
                temp_wav,
            ]

            try:
                result = subprocess.run(
                    convert_cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                # 验证WAV文件是否生成
                if not os.path.exists(temp_wav) or os.path.getsize(temp_wav) == 0:
                    print(f"警告: 无法转换文件 {mp3_file} 为WAV")
                    # 尝试使用另一种方法
                    alternative_cmd = [
                        "ffmpeg",
                        "-y",
                        "-v",
                        "error",
                        "-i",
                        src_file,
                        "-ar",
                        "44100",
                        "-ac",
                        "2",
                        "-acodec",
                        "pcm_s16le",
                        "-af",
                        "aresample=44100",  # 强制重采样
                        temp_wav,
                    ]

                    subprocess.run(
                        alternative_cmd,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )

                    if not os.path.exists(temp_wav) or os.path.getsize(temp_wav) == 0:
                        print(
                            f"错误: 所有方法都无法转换文件 {mp3_file} 为WAV，跳过此文件"
                        )
                        wav_files.remove(temp_wav)
            except subprocess.CalledProcessError as e:
                print(f"警告: 转换文件 {mp3_file} 时出错: {e.stderr}")
                # 跳过这个文件
                if temp_wav in wav_files:
                    wav_files.remove(temp_wav)

        if not wav_files:
            print("错误: 没有有效的WAV文件可以合并")
            return False

        # 步骤2: 合并所有WAV文件
        print(f"步骤2: 合并 {len(wav_files)} 个WAV文件...")

        # 创建合并用的文件列表
        concat_list = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for wav_file in wav_files:
                # 处理路径中的特殊字符
                escaped_path = wav_file.replace("'", "'\\''").replace("\\", "\\\\")
                f.write(f"file '{escaped_path}'\n")

        # 使用concat合并WAV文件为一个临时WAV文件
        temp_merged_wav = os.path.join(temp_dir, "merged.wav")
        concat_cmd = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list,
            "-c:a",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "2",
            temp_merged_wav,
        ]

        print(f"运行命令: {' '.join(concat_cmd)}")
        subprocess.run(
            concat_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # 验证合并WAV
        if not os.path.exists(temp_merged_wav) or os.path.getsize(temp_merged_wav) == 0:
            print("错误: 合并WAV文件失败")

            # 尝试使用filter_complex方式合并
            print("尝试使用filter_complex方式合并...")
            filter_inputs = ""
            for i in range(len(wav_files)):
                filter_inputs += f"[{i}:a]"

            filter_concat = f"{filter_inputs}concat=n={len(wav_files)}:v=0:a=1[out]"

            filter_cmd = ["ffmpeg", "-y", "-v", "error"]
            for wav_file in wav_files:
                filter_cmd.extend(["-i", wav_file])

            filter_cmd.extend(
                [
                    "-filter_complex",
                    filter_concat,
                    "-map",
                    "[out]",
                    "-ar",
                    "44100",
                    "-ac",
                    "2",
                    temp_merged_wav,
                ]
            )

            print(f"运行命令: {' '.join(filter_cmd)}")
            subprocess.run(
                filter_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            if (
                not os.path.exists(temp_merged_wav)
                or os.path.getsize(temp_merged_wav) == 0
            ):
                print("错误: 所有合并方法都失败")
                return False

        # 步骤3: 将合并后的WAV转换为MP3
        print("步骤3: 将合并后的WAV转换为MP3...")
        mp3_cmd = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            temp_merged_wav,
            "-ar",
            "44100",
            "-ac",
            "2",
            "-b:a",
            "128k",
            "-codec:a",
            "libmp3lame",
            output_file,
        ]

        print(f"运行命令: {' '.join(mp3_cmd)}")
        subprocess.run(
            mp3_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # 验证最终输出文件
        if (
            os.path.exists(output_file)
            and os.path.getsize(output_file) > 0
            and verify_mp3_file(output_file)
        ):
            print(f"成功合并并保存到: {output_file}")
            return True
        else:
            print("错误: 无法创建有效的输出MP3文件")
            return False

    except Exception as e:
        print(f"合并过程中出错: {e}")
        return False
    finally:
        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir)
                print(f"清理临时目录: {temp_dir}")
            except Exception as cleanup_e:
                print(f"清理临时文件时出错: {cleanup_e}")


def process_language(channel, video_name, language, force=False):
    """处理单个语言的MP3片段合并"""
    # 构建输入目录路径
    input_dir = os.path.join(INPUT_MP3_PATH, channel, video_name, language)

    # 如果输入目录不存在，跳过处理
    if not os.path.exists(input_dir):
        print(f"输入目录不存在，跳过: {input_dir}")
        return False

    # 构建输出文件路径
    output_dir = os.path.join(OUTPUT_MERGE_PATH, channel, language)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_file = os.path.join(output_dir, f"{video_name}.mp3")

    print(f"处理视频: {video_name}, 语言: {language}")
    print(f"输入目录: {input_dir}")
    print(f"输出文件: {output_file}")

    # 合并MP3文件
    return merge_mp3_files(input_dir, output_file, force)


def process_video(channel, video_name, languages, force=False):
    """处理一个视频的所有语言版本"""
    success_count = 0

    for language in languages:
        if process_language(channel, video_name, language, force):
            success_count += 1

    return success_count


def process_all_channels(languages=None, force=False, max_workers=3):
    """处理所有频道的所有视频"""
    if languages is None:
        languages = SUPPORTED_LANGUAGES

    # 验证语言是否支持
    for lang in languages[:]:  # 创建一个副本以便在迭代时修改
        if lang not in SUPPORTED_LANGUAGES:
            print(f"警告: 不支持的语言 {lang}，将被忽略")
            languages.remove(lang)

    if not languages:
        print("错误: 没有指定任何有效的语言")
        return

    # 检查输入路径是否存在
    if not os.path.exists(INPUT_MP3_PATH):
        print(f"错误: 输入路径不存在: {INPUT_MP3_PATH}")
        return

    # 获取所有频道目录
    channels = [
        d
        for d in os.listdir(INPUT_MP3_PATH)
        if os.path.isdir(os.path.join(INPUT_MP3_PATH, d))
    ]

    if not channels:
        print(f"在 {INPUT_MP3_PATH} 中未找到任何频道目录")
        return

    print(f"找到 {len(channels)} 个频道目录")

    # 处理每个频道
    for channel in channels:
        channel_path = os.path.join(INPUT_MP3_PATH, channel)
        print(f"\n处理频道: {channel}")

        # 获取当前频道下的所有视频目录
        videos = [
            d
            for d in os.listdir(channel_path)
            if os.path.isdir(os.path.join(channel_path, d))
        ]

        if not videos:
            print(f"在频道 {channel} 中未找到任何视频目录")
            continue

        print(f"找到 {len(videos)} 个视频目录")

        # 创建任务列表
        tasks = []
        for video_name in videos:
            for language in languages:
                # 构建输入目录路径
                input_dir = os.path.join(channel_path, video_name, language)

                # 检查输入目录是否存在
                if not os.path.exists(input_dir):
                    continue

                # 构建输出文件路径
                output_dir = os.path.join(OUTPUT_MERGE_PATH, channel, language)
                output_file = os.path.join(output_dir, f"{video_name}.mp3")

                # 如果输出文件已存在且不强制重新生成，则跳过
                if os.path.exists(output_file) and not force:
                    print(f"输出文件已存在，跳过: {output_file}")
                    continue

                # 添加任务
                tasks.append((channel, video_name, language))

        # 并发处理任务
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    process_language, channel, video_name, language, force
                ): (channel, video_name, language)
                for channel, video_name, language in tasks
            }

            for future in tqdm(
                concurrent.futures.as_completed(futures),
                total=len(futures),
                desc=f"处理 {channel} 频道",
            ):
                channel, video_name, language = futures[future]
                try:
                    future.result()
                except Exception:
                    pass


def fix_single_mp3(mp3_path):
    """修复单个MP3文件"""
    print(f"\n尝试修复单个MP3文件: {mp3_path}")

    # 检查文件是否存在
    if not os.path.exists(mp3_path):
        print(f"错误: 文件不存在 {mp3_path}")
        return False

    # 检查文件格式
    is_valid = os.path.getsize(mp3_path) > 0 and verify_mp3_file(mp3_path)
    if is_valid:
        print(f"文件已经是有效的MP3: {mp3_path}")
        return True

    # 尝试修复文件
    generate_mp3 = import_generate_mp3_module()
    if not generate_mp3:
        print("错误: 无法导入generate_mp3模块，无法修复文件")
        return False

    # 重新生成文件
    success = regenerate_mp3_file(mp3_path, generate_mp3)
    if success:
        # 验证结果
        if (
            os.path.exists(mp3_path)
            and os.path.getsize(mp3_path) > 0
            and verify_mp3_file(mp3_path)
        ):
            print(f"成功修复文件: {mp3_path}")
            return True
        else:
            print(f"修复尝试失败")
            return False
    else:
        print(f"无法修复文件")
        return False


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="合并多语言MP3文件")

    # 添加命令行参数
    parser.add_argument(
        "-l",
        "--languages",
        nargs="+",
        choices=SUPPORTED_LANGUAGES,
        default=SUPPORTED_LANGUAGES,
        help=f"目标语言列表 (默认: {' '.join(SUPPORTED_LANGUAGES)})",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="强制重新合并，即使输出文件已存在"
    )
    parser.add_argument(
        "-w", "--workers", type=int, default=3, help="并发处理的工作线程数，默认为3"
    )
    parser.add_argument(
        "-s", "--single", type=str, help="只处理指定的单个视频，格式: 频道名/视频名"
    )
    parser.add_argument(
        "-r", "--repair", type=str, help="修复单个损坏的MP3文件，提供完整路径"
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 处理修复单个MP3文件的模式 (优先级最高)
    if args.repair:
        success = fix_single_mp3(args.repair)
        if success:
            print("文件修复成功")
        else:
            print("文件修复失败")
        return

    # 处理单个视频模式
    if args.single:
        if "/" not in args.single:
            print("错误: 单个视频参数格式应为 '频道名/视频名'")
            return

        channel, video_name = args.single.split("/", 1)

        # 构建视频路径
        video_path = os.path.join(INPUT_MP3_PATH, channel, video_name)

        if not os.path.exists(video_path):
            print(f"错误: 指定的视频路径不存在: {video_path}")
            return

        print(f"处理单个视频: {channel}/{video_name}")
        success_count = process_video(channel, video_name, args.languages, args.force)

        print(f"处理完成，成功合并 {success_count}/{len(args.languages)} 个语言版本")
    else:
        # 处理所有频道和视频
        process_all_channels(args.languages, args.force, args.workers)


if __name__ == "__main__":
    main()
