#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存优化性能测试脚本
用于验证1秒基础片段+循环扩展的性能提升效果
"""

import time
import subprocess
import tempfile
import os


def test_traditional_method(image_path: str, target_duration: float) -> float:
    """测试传统方法：直接生成完整时长的视频"""
    print(f"🕐 测试传统方法：直接生成 {target_duration:.1f}s 静态视频...")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
        output_path = temp_file.name

    try:
        start_time = time.time()

        cmd = [
            "ffmpeg",
            "-loop",
            "1",
            "-i",
            image_path,
            "-vf",
            "scale=1920:1080",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-t",
            str(target_duration),
            "-pix_fmt",
            "yuv420p",
            "-r",
            "25",
            "-y",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        end_time = time.time()
        elapsed = end_time - start_time

        if result.returncode == 0:
            print(f"✅ 传统方法完成，耗时: {elapsed:.2f}s")
            return elapsed
        else:
            print(f"❌ 传统方法失败: {result.stderr}")
            return float("inf")

    finally:
        try:
            os.unlink(output_path)
        except Exception:
            pass


def test_optimized_method(image_path: str, target_duration: float) -> float:
    """测试优化方法：1秒基础片段+循环扩展"""
    print(f"🚀 测试优化方法：1秒基础片段+循环扩展到 {target_duration:.1f}s...")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_base:
        base_path = temp_base.name

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_final:
        final_path = temp_final.name

    try:
        start_time = time.time()

        # 步骤1：生成1秒基础片段
        base_cmd = [
            "ffmpeg",
            "-loop",
            "1",
            "-i",
            image_path,
            "-vf",
            "scale=1920:1080",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-t",
            "1.0",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "25",
            "-avoid_negative_ts",
            "make_zero",
            "-y",
            base_path,
        ]

        result1 = subprocess.run(base_cmd, capture_output=True, text=True)
        if result1.returncode != 0:
            print(f"❌ 基础片段生成失败: {result1.stderr}")
            return float("inf")

        # 步骤2：循环扩展到目标时长
        loop_times = int(target_duration)

        # 尝试使用stream_loop
        extend_cmd = [
            "ffmpeg",
            "-stream_loop",
            str(loop_times),
            "-i",
            base_path,
            "-t",
            str(target_duration),
            "-c",
            "copy",
            "-avoid_negative_ts",
            "make_zero",
            "-y",
            final_path,
        ]

        result2 = subprocess.run(extend_cmd, capture_output=True, text=True)

        end_time = time.time()
        elapsed = end_time - start_time

        if result2.returncode == 0:
            print(f"✅ 优化方法完成，耗时: {elapsed:.2f}s")
            return elapsed
        else:
            print(f"❌ 优化方法失败: {result2.stderr}")
            return float("inf")

    finally:
        try:
            os.unlink(base_path)
            os.unlink(final_path)
        except Exception:
            pass


def main():
    """性能对比测试"""
    print("🧪 静态图像缓存优化性能测试")
    print("=" * 50)

    # 创建测试用的1x1像素图片
    test_image = "/tmp/test_image.png"

    # 使用FFmpeg创建测试图片
    create_img_cmd = [
        "ffmpeg",
        "-f",
        "lavfi",
        "-i",
        "color=blue:size=1920x1080:duration=1",
        "-vframes",
        "1",
        "-y",
        test_image,
    ]

    result = subprocess.run(create_img_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ 无法创建测试图片: {result.stderr}")
        return

    try:
        # 测试不同时长
        test_durations = [30.0, 60.0, 120.0]  # 30s, 1分钟, 2分钟

        print(f"📊 测试图片: {test_image}")
        print(f"🎯 目标分辨率: 1920x1080")
        print()

        for duration in test_durations:
            print(f"\n📏 测试时长: {duration}s")
            print("-" * 30)

            # 传统方法
            traditional_time = test_traditional_method(test_image, duration)

            # 优化方法
            optimized_time = test_optimized_method(test_image, duration)

            # 计算性能提升
            if traditional_time != float("inf") and optimized_time != float("inf"):
                speedup = traditional_time / optimized_time
                print(f"🚀 性能提升: {speedup:.1f}x 倍")
                print(f"⏱️  时间节省: {traditional_time - optimized_time:.2f}s")

            print()

    finally:
        # 清理测试图片
        try:
            os.unlink(test_image)
        except Exception:
            pass


if __name__ == "__main__":
    main()
