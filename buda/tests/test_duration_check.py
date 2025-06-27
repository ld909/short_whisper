#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试时长检查功能的脚本

用于验证 add_subtitles_to_mp4.py 中新增的时长检查和自动重新生成功能
"""

import os
import sys
import tempfile
import subprocess
import json
from pathlib import Path

# 添加当前目录到 Python 路径，以便导入 add_subtitles_to_mp4 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from add_subtitles_to_mp4 import get_video_duration, check_duration_difference, DURATION_DIFF_THRESHOLD

def create_test_video(output_path, duration_seconds=10):
    """创建一个测试视频文件"""
    try:
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", f"testsrc=duration={duration_seconds}:size=320x240:rate=30",
            "-f", "lavfi", 
            "-i", f"sine=frequency=1000:duration={duration_seconds}",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-t", str(duration_seconds),
            "-y",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ 成功创建测试视频: {output_path} (时长: {duration_seconds}秒)")
            return True
        else:
            print(f"✗ 创建测试视频失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ 创建测试视频时出错: {str(e)}")
        return False

def test_get_video_duration():
    """测试获取视频时长功能"""
    print("\n=== 测试获取视频时长功能 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_video = os.path.join(temp_dir, "test_video.mp4")
        expected_duration = 5
        
        # 创建测试视频
        if not create_test_video(test_video, expected_duration):
            return False
        
        # 测试获取时长
        actual_duration = get_video_duration(test_video)
        
        if actual_duration is None:
            print("✗ 获取视频时长失败")
            return False
        
        # 检查时长是否接近预期值（允许小误差）
        duration_diff = abs(actual_duration - expected_duration)
        if duration_diff < 0.1:  # 允许0.1秒误差
            print(f"✓ 获取视频时长成功: {actual_duration:.2f}秒 (预期: {expected_duration}秒)")
            return True
        else:
            print(f"✗ 获取的视频时长不准确: {actual_duration:.2f}秒 (预期: {expected_duration}秒)")
            return False

def test_check_duration_difference():
    """测试时长差异检查功能"""
    print("\n=== 测试时长差异检查功能 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        video1 = os.path.join(temp_dir, "video1.mp4")
        video2 = os.path.join(temp_dir, "video2.mp4")
        video3 = os.path.join(temp_dir, "video3.mp4")
        
        # 创建不同时长的测试视频
        duration1 = 10
        duration2 = 10.5  # 差异0.5秒，应该在阈值内
        duration3 = 16    # 差异6秒，应该超过阈值
        
        if not all([
            create_test_video(video1, duration1),
            create_test_video(video2, duration2),
            create_test_video(video3, duration3)
        ]):
            return False
        
        # 测试小差异（应该在阈值内）
        print(f"\n测试小差异 (阈值: {DURATION_DIFF_THRESHOLD}秒):")
        needs_regen1, diff1 = check_duration_difference(video1, video2)
        
        if not needs_regen1 and diff1 < DURATION_DIFF_THRESHOLD:
            print(f"✓ 小差异检测正确: {diff1:.2f}秒，不需要重新生成")
        else:
            print(f"✗ 小差异检测错误: {diff1:.2f}秒，返回需要重新生成: {needs_regen1}")
            return False
        
        # 测试大差异（应该超过阈值）
        print(f"\n测试大差异 (阈值: {DURATION_DIFF_THRESHOLD}秒):")
        needs_regen2, diff2 = check_duration_difference(video1, video3)
        
        if needs_regen2 and diff2 > DURATION_DIFF_THRESHOLD:
            print(f"✓ 大差异检测正确: {diff2:.2f}秒，需要重新生成")
        else:
            print(f"✗ 大差异检测错误: {diff2:.2f}秒，返回需要重新生成: {needs_regen2}")
            return False
        
        return True

def test_nonexistent_file():
    """测试不存在文件的处理"""
    print("\n=== 测试不存在文件的处理 ===")
    
    nonexistent_file = "/tmp/nonexistent_video.mp4"
    
    # 测试获取不存在文件的时长
    duration = get_video_duration(nonexistent_file)
    if duration is None:
        print("✓ 正确处理不存在的文件")
        return True
    else:
        print(f"✗ 不存在文件处理错误，返回时长: {duration}")
        return False

def main():
    """主测试函数"""
    print("开始测试时长检查功能...")
    
    # 检查 ffmpeg 是否可用
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("✓ ffmpeg 可用")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ ffmpeg 不可用，无法进行测试")
        return False
    
    # 检查 ffprobe 是否可用
    try:
        subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
        print("✓ ffprobe 可用")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ ffprobe 不可用，无法进行测试")
        return False
    
    # 运行各项测试
    tests = [
        test_get_video_duration,
        test_check_duration_difference,
        test_nonexistent_file
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed_tests += 1
            else:
                print(f"✗ 测试失败: {test_func.__name__}")
        except Exception as e:
            print(f"✗ 测试异常: {test_func.__name__} - {str(e)}")
    
    # 输出测试结果
    print(f"\n=== 测试结果 ===")
    print(f"通过测试: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("✓ 所有测试通过！时长检查功能正常工作。")
        return True
    else:
        print("✗ 部分测试失败，请检查功能实现。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
