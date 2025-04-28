import os
import argparse
import platform
import subprocess
import concurrent.futures
import sys
from tqdm import tqdm
import importlib.util


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
# 输入TXT目录
INPUT_TXT_PATH = os.path.join(BASE_PATH, "multi_lang_txt")


def import_generate_mp3_module():
    """导入 generate_mp3.py 模块以重用其功能"""
    try:
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建generate_mp3.py的完整路径
        generate_mp3_path = os.path.join(current_dir, "generate_mp3.py")

        if not os.path.exists(generate_mp3_path):
            print(f"警告: 找不到 {generate_mp3_path}")
            return None

        # 导入模块
        spec = importlib.util.spec_from_file_location("generate_mp3", generate_mp3_path)
        generate_mp3 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generate_mp3)

        return generate_mp3
    except Exception as e:
        print(f"导入generate_mp3模块失败: {e}")
        return None


def verify_mp3_file(file_path):
    """验证MP3文件是否有效"""
    try:
        cmd = ["ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"]
        result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, check=False)

        # 如果没有错误输出，则文件有效
        if not result.stderr.strip():
            return True

        print(f"检测到损坏的MP3文件: {file_path}")
        print(f"错误信息: {result.stderr}")
        return False
    except Exception as e:
        print(f"验证MP3文件时出错: {e}")
        return False


def regenerate_mp3_file(mp3_path, generate_mp3):
    """重新生成损坏的MP3文件"""
    try:
        # 从MP3文件路径推断出TXT文件路径
        # 假设目录结构: multi_lang_mp3/channel/video_name/language/number.mp3
        parts = mp3_path.split(os.sep)
        if len(parts) < 5:
            print(f"无法从路径解析频道/视频/语言信息: {mp3_path}")
            return False

        # 解析信息
        relative_idx = (
            parts.index("multi_lang_mp3") if "multi_lang_mp3" in parts else -1
        )
        if relative_idx == -1:
            print(f"无法找到multi_lang_mp3在路径中: {mp3_path}")
            return False

        channel = parts[relative_idx + 1]
        video_name = parts[relative_idx + 2]
        language = parts[relative_idx + 3]
        file_number = os.path.splitext(parts[-1])[0]  # 不带扩展名的文件编号

        # 构建对应的TXT文件路径
        txt_file_path = os.path.join(
            INPUT_TXT_PATH, channel, language, f"{video_name}.txt"
        )

        if not os.path.exists(txt_file_path):
            print(f"找不到对应的TXT文件: {txt_file_path}")
            return False

        print(f"找到对应的TXT文件: {txt_file_path}")

        # 读取TXT文件中对应行的文本
        with open(txt_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines or int(file_number) > len(lines):
            print(f"文件编号{file_number}超出了TXT文件的行数{len(lines)}")
            return False

        # 获取对应行的文本
        text = lines[int(file_number) - 1].strip()

        if not text:
            print(f"行{file_number}的文本为空")
            return False

        # 调用generate_mp3模块中的text_to_mp3函数重新生成MP3
        if generate_mp3:
            print(f"重新生成MP3文件: {mp3_path}")
            success = generate_mp3.text_to_mp3(text, mp3_path, language)
            if success:
                print(f"成功重新生成MP3文件: {mp3_path}")
                return True
            else:
                print(f"重新生成MP3文件失败: {mp3_path}")
                return False
        else:
            print("generate_mp3模块不可用，无法重新生成MP3文件")
            return False
    except Exception as e:
        print(f"重新生成MP3文件时出错: {e}")
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
    mp3_files = [f for f in os.listdir(input_dir) if f.endswith(".mp3")]
    if not mp3_files:
        print(f"警告: 目录 {input_dir} 中没有MP3文件")
        return False

    # 按文件名中的数字排序
    mp3_files.sort(key=lambda f: int(os.path.splitext(f)[0]))

    # 导入generate_mp3模块
    generate_mp3 = import_generate_mp3_module()

    # 验证所有MP3文件是否有效，并修复损坏的文件
    valid_files = []
    for mp3_file in mp3_files:
        file_path = os.path.join(input_dir, mp3_file)

        # 检查文件是否存在且大小大于0
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            print(f"文件不存在或大小为0: {file_path}")
            if generate_mp3 and regenerate_mp3_file(file_path, generate_mp3):
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    valid_files.append(mp3_file)
                    print(f"成功重新生成并验证: {file_path}")
                else:
                    print(f"重新生成后文件仍然无效: {file_path}")
            else:
                print(f"跳过无效文件: {file_path}")
            continue

        # 验证文件格式
        if not verify_mp3_file(file_path):
            # 如果文件损坏，尝试重新生成
            print(f"文件格式无效: {file_path}")
            if generate_mp3 and regenerate_mp3_file(file_path, generate_mp3):
                if verify_mp3_file(file_path):
                    valid_files.append(mp3_file)
                    print(f"成功重新生成并验证: {file_path}")
                else:
                    print(f"重新生成后文件仍然无效: {file_path}")
            else:
                print(f"跳过损坏的文件: {file_path}")
        else:
            valid_files.append(mp3_file)
            print(f"文件有效: {file_path}")

    if not valid_files:
        print(f"警告: 目录 {input_dir} 中没有有效的MP3文件")
        return False

    # 更新mp3_files为有效的文件列表
    mp3_files = valid_files

    # 尝试使用简单的连接方法
    print(f"尝试使用简单连接方法合并 {len(mp3_files)} 个MP3文件...")
    temp_file_list = os.path.join(
        output_dir, f"{os.path.basename(output_file)}_list.txt"
    )

    try:
        # 创建临时文件列表
        with open(temp_file_list, "w", encoding="utf-8") as f:
            for mp3_file in mp3_files:
                file_path = os.path.join(input_dir, mp3_file)
                # 处理路径中的特殊字符
                escaped_path = file_path.replace("'", "'\\''").replace("\\", "\\\\")
                f.write(f"file '{escaped_path}'\n")

        # 使用concat demuxer合并MP3文件
        cmd = [
            "ffmpeg",
            "-y" if force else "-n",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            temp_file_list,
            "-c",
            "copy",  # 直接复制，不重新编码
            output_file,
        ]

        print(f"运行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, check=False
        )

        # 检查合并结果
        if result.returncode != 0:
            print(f"简单连接方法失败，错误: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd)

        # 验证输出文件
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            print(f"合并后的文件不存在或大小为0")
            raise Exception("合并后的文件无效")

        print(f"成功合并并保存到: {output_file}")
        return True
    except (subprocess.CalledProcessError, Exception) as e:
        print(f"简单连接方法失败: {e}")

        # 尝试第二种方法：重新编码合并
        try:
            print("尝试使用重新编码方法合并...")

            # 准备输出中间WAV文件
            intermediate_files = []

            for i, mp3_file in enumerate(mp3_files):
                src_file = os.path.join(input_dir, mp3_file)
                temp_wav = os.path.join(output_dir, f"temp_{i}.wav")
                intermediate_files.append(temp_wav)

                # 将MP3转换为WAV
                convert_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    src_file,
                    "-acodec",
                    "pcm_s16le",
                    temp_wav,
                ]

                print(f"转换为WAV: {' '.join(convert_cmd)}")
                subprocess.run(convert_cmd, check=True, capture_output=True, text=True)

            # 如果只有一个文件，直接转换为MP3
            if len(intermediate_files) == 1:
                encode_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    intermediate_files[0],
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    "128k",
                    output_file,
                ]
            else:
                # 合并多个WAV文件
                concat_filter = (
                    "concat=n=" + str(len(intermediate_files)) + ":v=0:a=1[aout]"
                )

                encode_cmd = ["ffmpeg", "-y"]

                # 添加所有输入文件
                for wav_file in intermediate_files:
                    encode_cmd.extend(["-i", wav_file])

                # 添加复杂过滤器
                filter_complex = ""
                for i in range(len(intermediate_files)):
                    filter_complex += f"[{i}:0]"
                filter_complex += concat_filter

                encode_cmd.extend(
                    [
                        "-filter_complex",
                        filter_complex,
                        "-map",
                        "[aout]",
                        "-c:a",
                        "libmp3lame",
                        "-b:a",
                        "128k",
                        output_file,
                    ]
                )

            print(f"合并并编码: {' '.join(encode_cmd)}")
            subprocess.run(encode_cmd, check=True, capture_output=True, text=True)

            # 清理临时文件
            for temp_file in intermediate_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            # 验证输出文件
            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                print(f"第二种方法也失败: 输出文件不存在或大小为0")
                return False

            print(f"成功合并并保存到: {output_file}")
            return True
        except Exception as e2:
            print(f"第二种方法也失败: {e2}")

            # 尝试第三种方法：直接使用system命令
            try:
                print("尝试使用系统命令方法合并...")

                # 准备合并命令
                mp3_paths = " ".join(
                    [f'"{os.path.join(input_dir, mp3)}"' for mp3 in mp3_files]
                )
                shell_cmd = f'cat {mp3_paths} > "{output_file}"'

                print(f"运行系统命令: {shell_cmd}")
                os.system(shell_cmd)

                # 验证输出文件
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    print(f"成功使用系统命令合并并保存到: {output_file}")
                    return True
                else:
                    print(f"系统命令方法也失败")
                    return False
            except Exception as e3:
                print(f"所有合并方法都失败: {e3}")
                return False
    finally:
        # 清理临时文件
        if os.path.exists(temp_file_list):
            try:
                os.remove(temp_file_list)
            except:
                pass


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
                    success = future.result()
                    if success:
                        print(f"成功合并 {channel}/{video_name}/{language}")
                    else:
                        print(f"合并失败 {channel}/{video_name}/{language}")
                except Exception as e:
                    print(f"处理 {channel}/{video_name}/{language} 时出错: {e}")


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

    # 解析命令行参数
    args = parser.parse_args()

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
