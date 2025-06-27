#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
性能基准测试脚本
===============

用于比较原版本和优化版本的性能差异
"""

import time
import subprocess
import os
import tempfile
import shutil
from pathlib import Path
import statistics


def create_test_environment():
    """创建测试环境"""
    test_dir = Path(tempfile.mkdtemp(prefix="video_merge_test_"))

    # 创建目录结构
    mp3_dir = test_dir / "merge_multi_lange_mp3" / "test_channel" / "chinese"
    mp4_dir = test_dir / "mp4_clips"
    output_dir = test_dir / "mp4_merge_silient"

    mp3_dir.mkdir(parents=True)
    mp4_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)

    # 创建测试MP3文件（使用ffmpeg生成）
    test_audio_files = []
    durations = [10, 30, 60, 120, 300]  # 不同时长的测试文件

    for i, duration in enumerate(durations):
        audio_file = mp3_dir / f"test_audio_{i}_{duration}s.mp3"
        cmd = [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}",
            "-ac",
            "1",
            "-ar",
            "22050",
            "-ab",
            "64k",
            "-y",
            str(audio_file),
        ]
        subprocess.run(cmd, capture_output=True)
        test_audio_files.append(audio_file)

    # 创建测试MP4片段
    test_video_files = []
    for i in range(10):  # 创建10个测试视频片段
        video_file = mp4_dir / f"clip_{i:02d}.mp4"
        cmd = [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=8:size=640x480:rate=30",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "28",
            "-y",
            str(video_file),
        ]
        subprocess.run(cmd, capture_output=True)
        test_video_files.append(video_file)

    return test_dir, test_audio_files, test_video_files


def run_original_script(test_dir, channel="test_channel", language="chinese"):
    """运行原始脚本"""
    start_time = time.time()

    cmd = [
        "python",
        "merge_mp4_clips_by_audio_duration.py",
        "--base-path",
        str(test_dir),
        "-c",
        channel,
        "-l",
        language,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    end_time = time.time()

    return {
        "duration": end_time - start_time,
        "success": result.returncode == 0,
        "output": result.stdout,
        "error": result.stderr,
    }


def run_optimized_script(
    test_dir, max_workers=4, channel="test_channel", language="chinese"
):
    """运行优化脚本"""
    start_time = time.time()

    cmd = [
        "python",
        "merge_mp4_clips_by_audio_duration_optimized.py",
        "--base-path",
        str(test_dir),
        "--max-workers",
        str(max_workers),
        "-c",
        channel,
        "-l",
        language,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    end_time = time.time()

    return {
        "duration": end_time - start_time,
        "success": result.returncode == 0,
        "output": result.stdout,
        "error": result.stderr,
    }


def measure_memory_usage(script_path, test_dir):
    """测量内存使用情况"""
    import psutil
    import threading

    memory_usage = []

    def monitor_memory(pid):
        process = psutil.Process(pid)
        while process.is_running():
            try:
                memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
                time.sleep(0.1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break

    cmd = [
        "python",
        script_path,
        "--base-path",
        str(test_dir),
        "-c",
        "test_channel",
        "-l",
        "chinese",
    ]
    process = subprocess.Popen(cmd)

    monitor_thread = threading.Thread(target=monitor_memory, args=(process.pid,))
    monitor_thread.start()

    process.wait()
    monitor_thread.join()

    return {
        "max_memory": max(memory_usage) if memory_usage else 0,
        "avg_memory": statistics.mean(memory_usage) if memory_usage else 0,
        "memory_samples": len(memory_usage),
    }


def analyze_output_quality(test_dir):
    """分析输出质量"""
    output_dir = test_dir / "mp4_merge_silient" / "test_channel" / "chinese"

    if not output_dir.exists():
        return {"error": "输出目录不存在"}

    video_files = list(output_dir.glob("*.mp4"))

    quality_metrics = {
        "files_generated": len(video_files),
        "total_size": sum(f.stat().st_size for f in video_files),
        "avg_file_size": 0,
        "duration_accuracy": [],
    }

    if video_files:
        quality_metrics["avg_file_size"] = quality_metrics["total_size"] / len(
            video_files
        )

        # 检查时长准确性
        mp3_dir = test_dir / "merge_multi_lange_mp3" / "test_channel" / "chinese"
        for video_file in video_files:
            # 查找对应的音频文件
            audio_file = mp3_dir / f"{video_file.stem}.mp3"
            if audio_file.exists():
                # 获取时长
                audio_duration = get_duration(audio_file)
                video_duration = get_duration(video_file)
                if audio_duration > 0 and video_duration > 0:
                    accuracy = abs(video_duration - audio_duration) / audio_duration
                    quality_metrics["duration_accuracy"].append(accuracy)

    return quality_metrics


def get_duration(file_path):
    """获取媒体文件时长"""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except:
        return 0


def run_benchmark():
    """运行完整基准测试"""
    print("🚀 开始性能基准测试...")

    # 创建测试环境
    print("📁 创建测试环境...")
    test_dir, audio_files, video_files = create_test_environment()
    print(f"✅ 测试环境创建完成: {test_dir}")
    print(f"   - 音频文件: {len(audio_files)} 个")
    print(f"   - 视频片段: {len(video_files)} 个")

    try:
        # 运行多次测试以获得可靠结果
        print("\n🔄 运行性能测试...")

        original_times = []
        optimized_times = []

        num_runs = 3

        for run in range(num_runs):
            print(f"  运行 {run + 1}/{num_runs}...")

            # 清理之前的输出
            output_dir = test_dir / "mp4_merge_silient"
            if output_dir.exists():
                shutil.rmtree(output_dir)

            # 测试原始版本
            if Path("merge_mp4_clips_by_audio_duration.py").exists():
                result = run_original_script(test_dir)
                if result["success"]:
                    original_times.append(result["duration"])
                    print(f"    原始版本: {result['duration']:.2f}s")
                else:
                    print(f"    原始版本执行失败: {result['error']}")

            # 清理输出
            if output_dir.exists():
                shutil.rmtree(output_dir)

            # 测试优化版本
            result = run_optimized_script(test_dir, max_workers=4)
            if result["success"]:
                optimized_times.append(result["duration"])
                print(f"    优化版本: {result['duration']:.2f}s")
            else:
                print(f"    优化版本执行失败: {result['error']}")

        # 分析结果
        print("\n📊 性能测试结果:")

        if original_times:
            avg_original = statistics.mean(original_times)
            print(f"  原始版本平均时间: {avg_original:.2f}s")
        else:
            avg_original = None
            print("  原始版本: 未测试")

        if optimized_times:
            avg_optimized = statistics.mean(optimized_times)
            print(f"  优化版本平均时间: {avg_optimized:.2f}s")

            if avg_original:
                improvement = ((avg_original - avg_optimized) / avg_original) * 100
                print(f"  性能提升: {improvement:.1f}%")
        else:
            print("  优化版本: 测试失败")

        # 测试内存使用
        print("\n🧠 内存使用测试...")
        if Path("merge_mp4_clips_by_audio_duration_optimized.py").exists():
            # 清理输出
            if output_dir.exists():
                shutil.rmtree(output_dir)

            memory_stats = measure_memory_usage(
                "merge_mp4_clips_by_audio_duration_optimized.py", test_dir
            )
            print(f"  最大内存使用: {memory_stats['max_memory']:.1f} MB")
            print(f"  平均内存使用: {memory_stats['avg_memory']:.1f} MB")

        # 分析输出质量
        print("\n🎯 输出质量分析...")
        quality = analyze_output_quality(test_dir)
        print(f"  生成文件数: {quality.get('files_generated', 0)}")
        print(f"  总文件大小: {quality.get('total_size', 0) / 1024 / 1024:.1f} MB")

        if quality.get("duration_accuracy"):
            avg_accuracy = statistics.mean(quality["duration_accuracy"]) * 100
            print(f"  平均时长误差: {avg_accuracy:.1f}%")

    finally:
        # 清理测试环境
        print(f"\n🧹 清理测试环境: {test_dir}")
        shutil.rmtree(test_dir)

    print("\n✅ 基准测试完成!")


if __name__ == "__main__":
    run_benchmark()
