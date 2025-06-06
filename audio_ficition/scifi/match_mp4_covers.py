#!/usr/bin/env python3
"""
MP4视频与封面图片匹配工具

功能说明:
此脚本用于将 /home/dhl/Documents/Wan2GP/outputs/ 目录下的MP4视频与生成的封面图片进行匹配，
通过比较MP4视频的第一帧与封面图片的像素差异，找到最匹配的视频文件。

主要功能:
1. 检查系统是否为Ubuntu，非Ubuntu系统自动退出
2. 并行提取所有MP4视频的第一帧进行预处理
3. 并行地为多张封面图片与所有视频帧进行像素级别的差异比较
4. 找到差异最小的MP4文件并复制到指定目录
5. 支持断点续传，避免重复计算

输入:
- MP4视频目录: /home/dhl/Documents/Wan2GP/outputs/
- 封面图片目录: /mnt/dhl/audio/scifi/cover_img_small/

输出:
- 匹配的MP4文件: /mnt/dhl/audio/scifi/starting_mp4/story_index.mp4

使用方法:
1. 基本使用: python match_mp4_covers.py
2. 强制重新匹配: python match_mp4_covers.py -f
3. 指定故事索引范围: python match_mp4_covers.py --start 1 --end 10

注意:
- 仅支持Ubuntu系统
- 需要安装 OpenCV 和 PIL 库
- 脚本支持断点续传，已匹配的文件不会重复处理
"""

import os
import sys
import platform
import argparse
import glob
import re
import shutil
import json
import time
import concurrent.futures
from tqdm import tqdm
import cv2
import numpy as np
from PIL import Image

# 用于工作进程的全局变量，存放预处理的MP4帧
g_mp4_frames = {}


def check_ubuntu_system():
    """检查系统是否为Ubuntu"""
    try:
        # 检查是否为Linux系统
        if platform.system() != "Linux":
            print("❌ 错误: 此脚本仅支持Linux系统")
            return False

        # 检查是否为Ubuntu系统
        with open("/etc/os-release", "r") as f:
            os_info = f.read()
            if "ubuntu" not in os_info.lower():
                print("❌ 错误: 此脚本仅支持Ubuntu系统")
                return False

        print("✅ 系统检查通过: Ubuntu系统")
        return True
    except Exception as e:
        print(f"❌ 系统检查失败: {e}")
        return False


def extract_first_frame(video_path):
    """从MP4视频中提取第一帧"""
    try:
        # 使用OpenCV读取视频
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            print(f"❌ 无法打开视频文件: {video_path}")
            return None

        # 读取第一帧
        ret, frame = cap.read()
        cap.release()

        if not ret:
            print(f"❌ 无法读取视频第一帧: {video_path}")
            return None

        # 将BGR转换为RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame_rgb

    except Exception as e:
        print(f"❌ 提取视频第一帧时出错 {video_path}: {e}")
        return None


def preprocess_mp4_frames(mp4_files):
    """并行预处理所有MP4文件，提取第一帧"""
    print(f"🚀 并行预处理 {len(mp4_files)} 个MP4文件以提取第一帧...")
    frames = {}
    with concurrent.futures.ProcessPoolExecutor() as executor:
        future_to_mp4 = {
            executor.submit(extract_first_frame, mp4_file): mp4_file
            for mp4_file in mp4_files
        }
        for future in tqdm(
            concurrent.futures.as_completed(future_to_mp4),
            total=len(mp4_files),
            desc="提取帧",
        ):
            mp4_file = future_to_mp4[future]
            try:
                frame = future.result()
                frames[mp4_file] = frame
            except Exception as e:
                print(f"❌ {mp4_file} 在提取帧时产生异常: {e}")
                frames[mp4_file] = None

    valid_frames_count = sum(1 for frame in frames.values() if frame is not None)
    print(f"🖼️  成功预处理 {valid_frames_count}/{len(mp4_files)} 个MP4帧.")
    return frames


def load_cover_image(image_path):
    """加载封面图片"""
    try:
        image = Image.open(image_path)
        # 转换为RGB模式
        if image.mode != "RGB":
            image = image.convert("RGB")
        return np.array(image)
    except Exception as e:
        print(f"❌ 加载封面图片时出错 {image_path}: {e}")
        return None


def resize_to_match(img1, img2):
    """将两张图片调整为相同尺寸"""
    try:
        # 获取两张图片的尺寸
        h1, w1 = img1.shape[:2]
        h2, w2 = img2.shape[:2]

        # 选择较小的尺寸作为目标尺寸
        target_h = min(h1, h2)
        target_w = min(w1, w2)

        # 调整图片尺寸
        img1_resized = cv2.resize(img1, (target_w, target_h))
        img2_resized = cv2.resize(img2, (target_w, target_h))

        return img1_resized, img2_resized
    except Exception as e:
        print(f"❌ 调整图片尺寸时出错: {e}")
        return None, None


def calculate_pixel_difference(img1, img2):
    """计算两张图片的像素差异平均值"""
    try:
        # 确保图片尺寸一致
        img1_resized, img2_resized = resize_to_match(img1, img2)
        if img1_resized is None or img2_resized is None:
            return float("inf")

        # 计算像素差异的绝对值
        diff = np.abs(img1_resized.astype(np.float32) - img2_resized.astype(np.float32))

        # 计算所有像素差异的平均值
        mean_diff = np.mean(diff)

        return mean_diff
    except Exception as e:
        print(f"❌ 计算像素差异时出错: {e}")
        return float("inf")


def get_mp4_files():
    """获取所有MP4文件列表"""
    mp4_dir = "/home/dhl/Documents/Wan2GP/outputs"

    if not os.path.exists(mp4_dir):
        print(f"❌ MP4目录不存在: {mp4_dir}")
        return []

    mp4_files = glob.glob(os.path.join(mp4_dir, "*.mp4"))
    print(f"📁 找到 {len(mp4_files)} 个MP4文件")
    return mp4_files


def get_cover_images():
    """获取所有封面图片"""
    # 修改为Linux系统路径
    cover_dir = "/mnt/dhl/audio/scifi/cover_img_small"

    if not os.path.exists(cover_dir):
        print(f"❌ 封面图片目录不存在: {cover_dir}")
        return {}

    cover_files = glob.glob(os.path.join(cover_dir, "*.png"))
    covers = {}

    for cover_file in cover_files:
        basename = os.path.basename(cover_file)
        # 排除以点开头的文件（如.DS_Store等）
        if basename.startswith("."):
            continue
        match = re.match(r"(\d+)\.png", basename)
        if match:
            story_index = int(match.group(1))
            covers[story_index] = cover_file

    print(f"🖼️ 找到 {len(covers)} 张封面图片")
    return covers


def get_existing_matches():
    """获取已经匹配的MP4文件"""
    output_dir = "/mnt/dhl/audio/scifi/starting_mp4"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        return set()

    existing_files = glob.glob(os.path.join(output_dir, "*.mp4"))
    existing_indices = set()

    for file_path in existing_files:
        basename = os.path.basename(file_path)
        # 排除以点开头的文件（如.DS_Store等）
        if basename.startswith("."):
            continue
        match = re.match(r"(\d+)\.mp4", basename)
        if match:
            existing_indices.add(int(match.group(1)))

    return existing_indices


def save_match_cache(cache_file, cache_data):
    """保存匹配缓存"""
    try:
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)

        # 转换numpy类型为标准Python类型
        serializable_data = {}
        for key, value in cache_data.items():
            if isinstance(value, np.floating):
                serializable_data[key] = float(value)
            else:
                serializable_data[key] = value

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(serializable_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ 保存缓存失败: {e}")


def load_match_cache(cache_file):
    """加载匹配缓存"""
    try:
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ 加载缓存失败: {e}")

    return {}


def init_worker(frames_data):
    """初始化工作进程，传递预处理的帧数据"""
    global g_mp4_frames
    g_mp4_frames = frames_data


def find_best_match_worker(story_index, cover_image_path, cache_data):
    """为单张封面图片找到最佳匹配的MP4文件 (在工作进程中运行)"""
    cover_image = load_cover_image(cover_image_path)
    if cover_image is None:
        return story_index, None, float("inf"), {}

    best_mp4 = None
    min_diff = float("inf")
    local_cache_updates = {}

    for mp4_file, first_frame in g_mp4_frames.items():
        mp4_basename = os.path.basename(mp4_file)
        cache_key = f"{story_index}_{mp4_basename}"

        if cache_key in cache_data:
            diff = cache_data[cache_key]
        else:
            if first_frame is None:
                continue

            diff = calculate_pixel_difference(cover_image, first_frame)
            local_cache_updates[cache_key] = diff

        if diff < min_diff:
            min_diff = diff
            best_mp4 = mp4_file

    return story_index, best_mp4, min_diff, local_cache_updates


def copy_matched_mp4(source_mp4, story_index):
    """将匹配的MP4文件复制到目标目录"""
    output_dir = "/mnt/dhl/audio/scifi/starting_mp4"

    try:
        os.makedirs(output_dir, exist_ok=True)
        target_file = os.path.join(output_dir, f"{story_index}.mp4")

        shutil.copy2(source_mp4, target_file)

        # 验证文件是否成功复制
        if os.path.exists(target_file):
            file_size = os.path.getsize(target_file)
            print(f"✅ 已复制到: {target_file} (大小: {file_size} 字节)")
            return True
        else:
            print(f"❌ 文件复制后未找到: {target_file}")
            return False

    except Exception as e:
        print(f"❌ 复制文件时出错: {e}")
        return False


def process_matching(force=False, start_index=None, end_index=None):
    """处理MP4与封面图片的匹配"""
    # 获取所有MP4文件和封面图片
    mp4_files = get_mp4_files()
    cover_images = get_cover_images()

    if not mp4_files:
        print("❌ 未找到任何MP4文件")
        return

    if not cover_images:
        print("❌ 未找到任何封面图片")
        return

    # 获取已存在的匹配
    existing_matches = get_existing_matches()

    # 过滤需要处理的封面图片
    covers_to_process = {}

    for story_index, cover_path in sorted(cover_images.items()):
        # 应用索引范围过滤
        if start_index is not None and story_index < start_index:
            continue
        if end_index is not None and story_index > end_index:
            continue

        # 检查是否需要重新匹配
        if force or story_index not in existing_matches:
            covers_to_process[story_index] = cover_path

    if not covers_to_process:
        print("✅ 所有指定范围内的封面都已匹配MP4文件")
        return

    print(f"\n=== 📊 MP4匹配分析 ===")
    print(f"总封面图片数量: {len(cover_images)}")
    print(f"总MP4文件数量: {len(mp4_files)}")
    print(f"已有匹配: {len(existing_matches)}")
    print(f"需要处理的封面: {len(covers_to_process)}")
    print(f"处理的故事索引: {sorted(covers_to_process.keys())}")

    # 1. 并行预处理所有MP4文件，提取第一帧
    mp4_frames = preprocess_mp4_frames(mp4_files)
    if not mp4_frames:
        print("❌ 预处理失败，未能提取任何MP4帧。")
        return

    # 加载匹配缓存
    cache_file = "/tmp/mp4_cover_match_cache.json"
    cache_data = load_match_cache(cache_file)

    # 统计变量
    success_count = 0
    failure_count = 0
    results = {}

    # 2. 使用多进程并行处理匹配
    with concurrent.futures.ProcessPoolExecutor(
        initializer=init_worker, initargs=(mp4_frames,)
    ) as executor:
        futures = {
            executor.submit(find_best_match_worker, idx, path, cache_data): idx
            for idx, path in covers_to_process.items()
        }

        for future in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(covers_to_process),
            desc="匹配封面",
        ):
            try:
                story_idx, best_mp4, min_diff, local_cache = future.result()
                results[story_idx] = (best_mp4, min_diff)
                cache_data.update(local_cache)
            except Exception as e:
                story_idx = futures[future]
                results[story_idx] = (None, float("inf"))
                print(f"❌ 故事 {story_idx} 的匹配任务失败: {e}")

    # 3. 按顺序处理和报告结果
    print("\n=== 📝 处理匹配结果 ===")
    for story_index in sorted(covers_to_process.keys()):
        if story_index not in results:
            print(f"🤷‍♂️ 故事 {story_index} 没有结果，可能在处理中被跳过。")
            continue

        best_mp4, min_diff = results[story_index]

        print(f"\n--- 故事 {story_index} ---")
        if best_mp4:
            print(
                f"🎯 找到最佳匹配: {os.path.basename(best_mp4)} (差异值: {min_diff:.2f})"
            )

            # 检查差异值是否超过阈值
            if min_diff > 20:
                print(
                    f"⚠️ 差异值 {min_diff:.2f} 大于阈值 20，认为MP4视频未正确生成，跳过复制"
                )
                print(f"⏭️  跳过故事 {story_index}")
                failure_count += 1
            else:
                # 复制MP4文件
                if copy_matched_mp4(best_mp4, story_index):
                    success_count += 1
                    print(f"✅ 故事 {story_index} 匹配成功")
                else:
                    failure_count += 1
                    print(f"❌ 故事 {story_index} 文件复制失败")
        else:
            failure_count += 1
            print(f"❌ 故事 {story_index} 未找到匹配的MP4文件")

    # 保存最终缓存
    save_match_cache(cache_file, cache_data)

    # 输出最终统计
    total_processed = len(covers_to_process)
    print(f"\n=== 📈 匹配完成统计 ===")
    print(f"✅ 成功匹配: {success_count}/{total_processed} 个封面图片")
    print(f"❌ 匹配失败: {failure_count}/{total_processed} 个封面图片")
    if total_processed > 0:
        success_rate = (success_count / total_processed) * 100
        print(f"📊 成功率: {success_rate:.1f}%")


def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="MP4视频与封面图片匹配工具")

    # 添加命令行参数
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="强制重新匹配，忽略已有文件",
    )
    parser.add_argument(
        "--start",
        type=int,
        help="指定开始处理的故事索引",
    )
    parser.add_argument(
        "--end",
        type=int,
        help="指定结束处理的故事索引",
    )

    # 解析命令行参数
    args = parser.parse_args()

    # 验证参数
    if args.start is not None and args.end is not None:
        if args.start > args.end:
            print("❌ 错误：开始索引不能大于结束索引")
            return
        if args.start <= 0 or args.end <= 0:
            print("❌ 错误：索引必须大于 0")
            return

    print("🎬 MP4视频与封面图片匹配工具")
    print("=" * 50)

    # 检查Ubuntu系统
    if not check_ubuntu_system():
        sys.exit(1)

    # 处理匹配
    process_matching(args.force, args.start, args.end)

    print("\n🎉 MP4匹配任务完成!")


if __name__ == "__main__":
    main()
