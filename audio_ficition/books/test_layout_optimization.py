#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
布局优化测试脚本 - 演示不同参数效果

此脚本用于测试 generate_book_clips.py 的新布局优化功能
会生成多个不同布局参数的示例，方便对比效果
"""

import os
import sys
import subprocess
import time
from pathlib import Path


def get_script_dir():
    """获取脚本所在目录"""
    return os.path.dirname(os.path.abspath(__file__))


def run_with_layout_params(params_name, extra_args):
    """运行生成脚本，使用指定的布局参数"""
    print(f"\n{'='*60}")
    print(f"🎬 测试布局: {params_name}")
    print(f"📋 参数: {' '.join(extra_args)}")
    print(f"{'='*60}")

    # 构建完整命令
    cmd = [
        "python",
        "generate_book_clips.py",
        "--debug",  # 启用调试模式查看详细信息
        "--force",  # 强制重新处理（覆盖已有文件）
    ] + extra_args

    print(f"🚀 执行命令: {' '.join(cmd)}")

    try:
        # 记录开始时间
        start_time = time.time()

        # 执行命令
        result = subprocess.run(cmd, cwd=get_script_dir(), text=True)

        # 记录结束时间
        end_time = time.time()
        process_time = end_time - start_time

        if result.returncode == 0:
            print(f"✅ {params_name} 测试完成 (耗时: {process_time:.2f}秒)")
            return True
        else:
            print(f"❌ {params_name} 测试失败")
            return False

    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return False


def main():
    """主函数 - 运行各种布局测试"""
    print("🧪 书籍 MP4 Clip 布局优化测试")
    print("本脚本将测试多种布局参数组合效果")
    print("请确保已有书籍数据并安装了所需依赖")

    # 检查主脚本是否存在
    main_script = os.path.join(get_script_dir(), "generate_book_clips.py")
    if not os.path.exists(main_script):
        print(f"❌ 未找到主脚本: {main_script}")
        sys.exit(1)

    # 询问用户是否继续
    choice = input("\n是否继续测试？(y/N): ").lower().strip()
    if choice not in ["y", "yes"]:
        print("测试取消")
        sys.exit(0)

    print("\n开始测试各种布局参数...")

    # 定义测试用例
    test_cases = [
        {
            "name": "默认优化布局",
            "args": [],
            "description": "封面保持比例，视频50%宽度右对齐",
        },
        {
            "name": "精致小视频",
            "args": ["--video-width", "0.3"],
            "description": "视频30%宽度，更突出封面",
        },
        {
            "name": "居中平衡布局",
            "args": ["--video-width", "0.6", "--video-center"],
            "description": "视频60%宽度居中对齐",
        },
        {
            "name": "极简风格",
            "args": ["--video-width", "0.25"],
            "description": "视频25%宽度，强调静态内容",
        },
        {
            "name": "旧版本兼容",
            "args": ["--no-preserve-aspect", "--video-width", "1.0"],
            "description": "恢复旧版本行为（允许裁剪封面）",
        },
    ]

    # 执行测试
    success_count = 0
    total_count = len(test_cases)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔄 进度: {i}/{total_count}")
        print(f"📝 说明: {test_case['description']}")

        success = run_with_layout_params(test_case["name"], test_case["args"])
        if success:
            success_count += 1

        # 测试间隔
        if i < total_count:
            print(f"⏳ 等待3秒后进行下一个测试...")
            time.sleep(3)

    # 输出总结
    print(f"\n{'='*60}")
    print(f"🎯 测试完成总结")
    print(f"{'='*60}")
    print(f"✅ 成功: {success_count}/{total_count} 个测试")
    print(f"❌ 失败: {total_count - success_count}/{total_count} 个测试")

    if success_count > 0:
        print(f"\n📁 生成的测试文件位于输出目录")
        print(f"💡 建议:")
        print(f"   1. 检查不同布局效果的差异")
        print(f"   2. 选择最适合的参数组合")
        print(f"   3. 根据书籍类型调整布局风格")

    print(f"\n🎉 布局优化测试完成!")


if __name__ == "__main__":
    main()
