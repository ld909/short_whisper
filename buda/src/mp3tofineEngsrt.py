"""
MP3到英文SRT字幕转换控制器

此脚本控制整个从MP3音频到SRT字幕的转换流程：
1. 使用OpenAI的Whisper模型将MP3音频文件转录为文本
2. 生成英文SRT字幕文件
3. 对SRT格式进行优化，使其更易读
4. 处理字幕断句，提高可读性

输入路径：/media/dhl/buda_videos_youtube/channel_mp3_raw/{频道名称}/*.mp3
输出路径：/media/dhl/buda_videos_youtube/format_srt_zh/{主题名称}/{频道名称}/*.srt

注意：此脚本需要在Nvidia GPU上运行，否则Whisper模型处理速度会很慢！

使用方法：
    python mp3tofineEngsrt.py <主题名称>

示例：
    python mp3tofineEngsrt.py code

更新说明：
    - 使用faster-whisper替代原版whisper解决PyTorch 2.7.0兼容性问题
    - faster-whisper速度更快，内存占用更少，兼容性更好
"""

import os
import sys
import requests
from tqdm import tqdm
from mp3toscripts_faster import mp3totxt, save_srt
from srt_format import format_srt, break_srt_txt_into_sentences
from mutagen import File

# 设置代理环境变量，加速Whisper模型下载
def setup_proxy():
    """
    设置代理环境变量以加速模型下载
    根据截图中的代理设置，支持多种代理端口
    """
    # 根据截图中的代理端口配置
    proxy_configs = [
        {"name": "混合代理", "port": "7897"},
        {"name": "HTTP(S)代理", "port": "7899"},
        {"name": "SOCKS代理", "port": "7898"},
    ]
    
    proxy_host = "127.0.0.1"
    
    # 尝试不同的代理端口，找到可用的
    for config in proxy_configs:
        proxy_url = f"http://{proxy_host}:{config['port']}"
        print(f"尝试使用{config['name']}端口 {config['port']}...")
        
        try:
            # 测试代理连接
            test_response = requests.get(
                'https://httpbin.org/ip', 
                proxies={'http': proxy_url, 'https': proxy_url},
                timeout=5
            )
            if test_response.status_code == 200:
                print(f"✓ {config['name']}连接成功！")
                
                # 设置环境变量
                os.environ['HTTP_PROXY'] = proxy_url
                os.environ['HTTPS_PROXY'] = proxy_url
                os.environ['http_proxy'] = proxy_url
                os.environ['https_proxy'] = proxy_url
                
                # 设置不使用代理的地址（本地地址）
                os.environ['NO_PROXY'] = 'localhost,127.0.0.1,::1'
                os.environ['no_proxy'] = 'localhost,127.0.0.1,::1'
                
                print(f"已设置代理: {proxy_url}")
                print("代理设置完成，Whisper模型下载将通过代理进行")
                return True
                
        except Exception as e:
            print(f"✗ {config['name']}连接失败: {e}")
            continue
    
    print("⚠️  所有代理端口都无法连接，将使用直连方式")
    print("如果下载速度较慢，请检查代理软件是否正常运行")
    return False

# 在导入whisper相关模块之前设置代理
setup_proxy()

def get_duration(file_path):
    """get the duration of the media file in seconds"""
    media = File(file_path)
    duration = media.info.length
    return duration


def remove_trash_files(mp3_abs_path):
    """
    清理目录中的垃圾文件

    此函数删除指定目录及其子目录中的.DS_Store文件和所有以'._'开头的文件，
    这些通常是macOS系统生成的元数据文件。

    参数:
        mp3_abs_path (str): MP3文件所在的绝对路径
    """
    # 先删除主目录下的.DS_Store文件
    ds_store_path = os.path.join(mp3_abs_path, ".DS_Store")
    if os.path.exists(ds_store_path):
        try:
            os.remove(ds_store_path)
            print(f"已删除主目录中的 .DS_Store 文件")
        except OSError as e:
            print(f"无法删除 {ds_store_path}: {e}")
            print("继续执行，跳过此文件")

    # 获取目录列表，过滤掉所有非目录项
    channels = []
    for item in os.listdir(mp3_abs_path):
        item_path = os.path.join(mp3_abs_path, item)
        if os.path.isdir(item_path):
            channels.append(item)

    # 处理子目录中的垃圾文件
    for channel in channels:
        channel_path = os.path.join(mp3_abs_path, channel)
        for file in os.listdir(channel_path):
            if file.startswith("._") or file == ".DS_Store":
                try:
                    os.remove(os.path.join(channel_path, file))
                    print(f"{channel}, {file} 已删除")
                except OSError as e:
                    print(f"无法删除 {channel}/{file}: {e}")
                    print("继续执行，跳过此文件")


def controller_mp3_to_format_srt(topic):
    """
    MP3到格式化SRT的控制器主函数

    此函数控制整个处理流程：
    1. 清理垃圾文件
    2. 遍历channel_mp3_raw目录下的所有频道和MP3文件
    3. 使用faster-whisper模型转录音频为文本
    4. 格式化文本为SRT格式
    5. 优化SRT字幕的断句
    6. 保存格式化后的SRT文件

    函数会自动跳过：
    - 已处理过的文件
    - 时长超过120分钟的音频文件

    参数:
        topic (str): 主题名称，用于确定输出SRT文件夹的分类
    """
    hard_dive_path = "/media/dhl"
    mp3_abs_path = f"{hard_dive_path}/buda_videos_youtube/channel_mp3_raw"  # 读取youtube_channel_audio_downloader.py的输出

    remove_trash_files(mp3_abs_path)
    dst_srt_abs_path = f"{hard_dive_path}/buda_videos_youtube/format_srt_zh/{topic}"  # fill in the absolute path of the srt folder

    # check if the dst_srt_abs_path exists, if not create it
    if not os.path.exists(dst_srt_abs_path):
        os.makedirs(dst_srt_abs_path)

    all_channels = os.listdir(mp3_abs_path)
    # remove .DS_store
    all_channels = [folder for folder in all_channels if folder != ".DS_Store"]

    # 删除._开头的文件
    all_channels = [folder for folder in all_channels if not folder.startswith("._")]

    print("所有频道包括:", all_channels)

    # 统计总任务数
    print("\n=== 正在统计总任务数 ===")
    total_mp3_files = 0
    channel_file_counts = {}
    
    for channel in all_channels:
        channel_path = os.path.join(mp3_abs_path, channel)
        if os.path.isdir(channel_path):
            mp3_files = [f for f in os.listdir(channel_path) if f.endswith('.mp3') and not f.startswith('.')]
            channel_file_counts[channel] = len(mp3_files)
            total_mp3_files += len(mp3_files)
            print(f"  频道 '{channel}': {len(mp3_files)} 个MP3文件")
    
    print(f"\n📊 总计发现 {total_mp3_files} 个MP3文件需要处理")
    print(f"📂 涉及 {len(all_channels)} 个频道")
    print("=" * 50)

    # 初始化进度计数器
    completed_count = 0
    skipped_existing_count = 0
    skipped_duration_count = 0
    error_count = 0
    
    # 记录超时跳过的文件
    timeout_skipped_files = []

    # read all mp3 files in the folder
    for channel_idx, channel in enumerate(all_channels, 1):
        print(f"\n🎯 [{channel_idx}/{len(all_channels)}] 正在处理频道: {channel}")
        print(f"📁 频道 '{channel}' 包含 {channel_file_counts[channel]} 个MP3文件")
        
        # read all mp3 files in the folder
        mp3_files = os.listdir(os.path.join(mp3_abs_path, channel))
        # 过滤掉点开头的文件
        mp3_files = [f for f in mp3_files if not f.startswith(".")]

        for file_idx, mp3_file in enumerate(mp3_files, 1):
            if mp3_file.endswith(".mp3"):
                # check if base_name +'.srt' exists in the dst_srt
                base_name = os.path.splitext(mp3_file)[0]
                dst_srt = os.path.join(dst_srt_abs_path, channel, base_name + ".srt")

                # check if os.path.join(dst_srt_abs_path, channel) exists
                if not os.path.exists(os.path.join(dst_srt_abs_path, channel)):
                    os.makedirs(os.path.join(dst_srt_abs_path, channel))

                print(f"\n  📄 [{file_idx}/{len(mp3_files)}] 文件: {mp3_file}")
                print(f"  📈 总体进度: {completed_count + skipped_existing_count + skipped_duration_count + error_count + 1}/{total_mp3_files}")

                # 检查之前是否完成过此任务，完成就跳过
                if os.path.exists(dst_srt):
                    skipped_existing_count += 1
                    print(f"  ✅ SRT文件已存在，跳过 - 已跳过: {skipped_existing_count}")
                    continue
                
                mp3_path = os.path.join(mp3_abs_path, channel, mp3_file)
                print(f"  🔍 检查文件时长...")
                
                try:
                    # if mp3 duration is larger than 120 minutes, skip
                    mp3_duration_seconds = get_duration(mp3_path)
                    duration_minutes = mp3_duration_seconds / 60
                    print(f"  ⏱️  文件时长: {duration_minutes:.1f} 分钟")
                    
                    if mp3_duration_seconds > 7200:
                        skipped_duration_count += 1
                        timeout_skipped_files.append(f"{channel}/{mp3_file}")
                        print(f"  ⚠️  时长超过120分钟，跳过 - 因时长跳过: {skipped_duration_count}")
                        continue

                    print(f"  🚀 开始处理音频转录...")
                    print(f"  🤖 使用faster-whisper模型将MP3转录为文本...")
                    ts_list, txt_list = mp3totxt(mp3_path)

                    print(f"  🔧 格式化SRT字幕...")
                    # format srt
                    ts_list, txt_list = format_srt(ts_list, txt_list)

                    print(f"  ✂️  优化字幕断句...")
                    # break into sub sentences
                    ts_list, txt_list = break_srt_txt_into_sentences(ts_list, txt_list)

                    # check if the number of timestamps and subtitles are the same
                    assert len(ts_list) == len(txt_list)

                    # get base name without extension
                    save_srt(ts_list, txt_list, dst_srt)
                    completed_count += 1
                    
                    print(f"  ✅ 处理完成！字幕已保存到: {dst_srt}")
                    print(f"  📊 已完成: {completed_count}/{total_mp3_files} ({completed_count/total_mp3_files*100:.1f}%)")
                    
                except Exception as e:
                    error_count += 1
                    print(f"  ❌ 处理出错: {str(e)}")
                    print(f"  📊 错误计数: {error_count}")
                    continue

    # 最终统计报告
    print("\n" + "=" * 60)
    print("🎉 处理完成！最终统计报告:")
    print("=" * 60)
    print(f"📊 总文件数: {total_mp3_files}")
    print(f"✅ 成功处理: {completed_count}")
    print(f"⚠️  已存在跳过: {skipped_existing_count}")
    print(f"⏱️  超时跳过: {skipped_duration_count}")
    print(f"❌ 处理出错: {error_count}")
    print(f"📈 成功率: {completed_count/(total_mp3_files-skipped_existing_count)*100:.1f}%" if (total_mp3_files-skipped_existing_count) > 0 else "📈 成功率: 100.0%")
    
    # 显示超时跳过的文件详情
    if timeout_skipped_files:
        print("\n⏱️  超时跳过的文件详情:")
        print("-" * 40)
        for i, file_name in enumerate(timeout_skipped_files, 1):
            print(f"  {i}. {file_name}")
        print("-" * 40)
    
    print("=" * 60)


if __name__ == "__main__":
    # topic = "code"
    topic = sys.argv[1]
    # topic = "mama"
    controller_mp3_to_format_srt(topic=topic)
