#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
生成固定时长(8秒)的视频片段
每个片段会:
1. 随机从/Volumes/dhl/buda_videos_youtube/buda_images_crop选择一张图作为底图
2. 使用随机的zoom效果(in或out)和随机position
3. 保存到/Volumes/dhl/buda_videos_youtube/mp4_clips/目录，使用随机UID命名
4. 支持连续按三个q退出，但会保存正在生成的片段后再退出

使用方法:
1. 基本使用:
   python generate_video_clips.py
   这将使用默认参数生成10个视频片段

2. 指定生成数量:
   python generate_video_clips.py -n 20
   或
   python generate_video_clips.py --number 20
   这将生成20个视频片段

3. 使用多进程加速:
   python generate_video_clips.py -n 20 -p 4
   或
   python generate_video_clips.py --number 20 --processes 4
   这将使用4个进程并行生成20个视频片段

参数说明:
-n, --number: 要生成的视频片段数量（默认：10）
-p, --processes: 并行处理的进程数（默认：1）

运行时控制:
- 在运行过程中，连续按三次'q'键可以安全退出程序
- 按Ctrl+C也可以安全退出程序
- 程序会等待当前正在生成的视频片段完成后再退出
"""

import os
import random
import platform
import uuid
import argparse
from tqdm import tqdm
from camera_motion import smooth_zoom
import multiprocessing
import time
import threading
import sys
import queue
import signal

# 用于控制退出的全局变量
exit_requested = False
q_counter = 0
q_lock = threading.Lock()
q_queue = queue.Queue()

# 全局共享变量，将在main函数中初始化
exit_flag = None


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 获取媒体基础路径
BASE_MEDIA_PATH = get_base_media_path()
# 图片目录
IMAGES_PATH = os.path.join(BASE_MEDIA_PATH, "buda_images_crop")
# MP4片段输出目录
OUTPUT_CLIPS_PATH = os.path.join(BASE_MEDIA_PATH, "mp4_clips")

# 确保输出目录存在
os.makedirs(OUTPUT_CLIPS_PATH, exist_ok=True)

# 定义视频参数
CLIP_DURATION = 8.0  # 固定8秒
ZOOM_TYPES = ["in", "out"]
ZOOM_POSITIONS = [
    "center",
    "left",
    "right",
    "top",
    "bottom",
    "topleft",
    "topright",
    "bottomleft",
    "bottomright",
]
ZOOM_SPEED = 1.0
FPS = 30


def get_random_image():
    """从图片目录中随机选择一张图片"""
    if not os.path.exists(IMAGES_PATH):
        raise FileNotFoundError(f"图片目录不存在: {IMAGES_PATH}")

    # 获取所有图片文件，排除以.开头的隐藏文件
    image_files = []
    for root, _, files in os.walk(IMAGES_PATH):
        for file in files:
            # 排除.开头的隐藏文件和._开头的macOS元数据文件
            if not file.startswith(".") and file.lower().endswith(
                (".jpg", ".jpeg", ".png", ".webp")
            ):
                image_files.append(os.path.join(root, file))

    if not image_files:
        raise FileNotFoundError(f"在图片目录中未找到任何图片: {IMAGES_PATH}")

    # 随机选择一张图片
    return random.choice(image_files)


def create_video_clip(output_path, duration=CLIP_DURATION, fps=FPS):
    """创建一个视频片段"""
    # 随机选择一张图片
    image_path = get_random_image()

    # 随机选择zoom类型和位置
    zoom_type = random.choice(ZOOM_TYPES)
    position = random.choice(ZOOM_POSITIONS)

    # 使用camera_motion.py中的smooth_zoom函数生成视频
    try:
        smooth_zoom(
            image_path=image_path,
            output_path=output_path,
            duration=duration,
            zoom_type=zoom_type,
            fps=fps,
            zoom_speed=ZOOM_SPEED,
            position=position,
        )
        return True
    except Exception as e:
        print(f"创建视频片段时出错: {e}")
        return False


def generate_clip():
    """生成一个8秒的视频片段并返回其路径"""
    # 生成随机UUID作为文件名
    random_uid = str(uuid.uuid4())
    output_path = os.path.join(OUTPUT_CLIPS_PATH, f"{random_uid}.mp4")

    success = create_video_clip(output_path)
    if success:
        return output_path
    return None


def process_batch(count):
    """处理一批视频片段的生成"""
    global exit_requested, exit_flag
    successful_clips = []
    failed_clips = 0

    for i in tqdm(range(count), desc="生成视频片段"):
        # 检查是否请求退出（支持本地变量和共享变量）
        if exit_requested or (exit_flag and exit_flag.value):
            print("检测到退出请求，完成当前片段后退出...")
            break

        clip_path = generate_clip()
        if clip_path:
            successful_clips.append(clip_path)
        else:
            failed_clips += 1

    return successful_clips, failed_clips


def key_listener():
    """监听键盘输入，检测连续三个q"""
    global exit_requested, q_counter, exit_flag

    print("按连续三个q键可以安全退出程序")

    while not exit_requested:
        try:
            # 非阻塞方式读取一个字符
            if sys.stdin.isatty():  # 确保在终端环境下
                # 使用系统特定的方法获取单个字符
                if platform.system() == "Windows":
                    import msvcrt

                    if msvcrt.kbhit():
                        char = msvcrt.getch().decode("utf-8", errors="ignore")
                        q_queue.put(char)
                else:  # Unix/Linux/MacOS
                    import tty
                    import termios
                    import select

                    fd = sys.stdin.fileno()
                    old_settings = termios.tcgetattr(fd)
                    try:
                        tty.setraw(fd, termios.TCSANOW)
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            char = sys.stdin.read(1)
                            q_queue.put(char)
                    finally:
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

            # 处理队列中的字符
            while not q_queue.empty():
                char = q_queue.get()
                if char == "q":
                    with q_lock:
                        q_counter += 1
                        if q_counter >= 3:
                            exit_requested = True
                            # 设置共享退出标志，通知所有进程
                            if exit_flag:
                                exit_flag.value = True
                            print("\n检测到连续三个q，将在完成当前视频后退出...")
                            break
                else:
                    with q_lock:
                        q_counter = 0

            time.sleep(0.1)  # 避免CPU过度使用
        except Exception as e:
            print(f"键盘监听错误: {e}")
            break


def main():
    global exit_flag
    # 创建共享变量
    if multiprocessing.get_start_method() != "fork":
        manager = multiprocessing.Manager()
        exit_flag = manager.Value("b", False)

    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="生成固定时长的视频片段")

    # 添加命令行参数
    parser.add_argument(
        "-n", "--number", type=int, default=10, help="要生成的视频片段数量"
    )
    parser.add_argument(
        "-p", "--processes", type=int, default=1, help="并行处理的进程数"
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 设置信号处理
    def handle_sigint(sig, frame):
        global exit_requested
        print("\n接收到中断信号，将在完成当前视频后退出...")
        exit_requested = True
        if exit_flag:
            exit_flag.value = True
        return

    signal.signal(signal.SIGINT, handle_sigint)

    # 启动键盘监听线程
    listener_thread = threading.Thread(target=key_listener, daemon=True)
    listener_thread.start()

    start_time = time.time()

    if args.processes <= 1:
        # 单进程处理
        successful_clips, failed_clips = process_batch(args.number)
    else:
        # 多进程处理
        print(f"使用 {args.processes} 个进程并行生成视频片段")
        clips_per_process = args.number // args.processes
        remainder = args.number % args.processes

        # 分配任务
        tasks = [clips_per_process] * args.processes
        for i in range(remainder):
            tasks[i] += 1

        # 创建进程池
        with multiprocessing.Pool(processes=args.processes) as pool:
            # 使用apply_async而不是map，可以更好地控制进程
            async_results = []
            for task in tasks:
                async_results.append(pool.apply_async(process_batch, (task,)))

            # 等待结果并检查退出标志
            pool.close()

            # 监控进程
            while async_results and not (
                exit_requested or (exit_flag and exit_flag.value)
            ):
                # 检查是否所有进程都完成了
                all_done = all(result.ready() for result in async_results)
                if all_done:
                    break
                time.sleep(0.5)

            # 如果请求退出，等待当前进程完成
            if exit_requested or (exit_flag and exit_flag.value):
                print("等待当前进程完成...")

            # 获取结果
            pool.join()
            results = [result.get() for result in async_results]

        # 合并结果
        successful_clips = []
        failed_clips = 0
        for success_list, failed_count in results:
            successful_clips.extend(success_list)
            failed_clips += failed_count

    end_time = time.time()

    print(f"\n处理完成:")
    print(f"成功生成: {len(successful_clips)} 个片段")
    print(f"失败: {failed_clips} 个片段")
    print(f"总耗时: {end_time - start_time:.2f}秒")

    if successful_clips:
        print(f"\n示例生成的片段:")
        for path in successful_clips[:5]:
            print(f"- {path}")

        if len(successful_clips) > 5:
            print(f"... 等共 {len(successful_clips)} 个片段")

    # 如果是由于用户请求退出，显示友好信息
    if exit_requested or (exit_flag and exit_flag.value):
        print("程序已安全退出，所有正在处理的视频片段都已完成。")


if __name__ == "__main__":
    multiprocessing.freeze_support()  # Windows兼容性
    main()
