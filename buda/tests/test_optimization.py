#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
字幕处理优化版本测试脚本

用于快速验证优化版本的功能和性能
"""

import os
import sys
import time
import subprocess
from pathlib import Path
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """检查依赖项"""
    logger.info("检查依赖项...")
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version < (3, 7):
        logger.error(f"Python版本过低: {python_version}, 需要3.7+")
        return False
    logger.info(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 检查FFmpeg
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            logger.info("FFmpeg: 已安装")
        else:
            logger.error("FFmpeg: 未正确安装")
            return False
    except Exception as e:
        logger.error(f"FFmpeg检查失败: {str(e)}")
        return False
    
    # 检查必要的Python模块
    required_modules = ['pathlib', 'dataclasses', 'typing']
    for module in required_modules:
        try:
            __import__(module)
            logger.info(f"Python模块 {module}: 已安装")
        except ImportError:
            logger.error(f"Python模块 {module}: 未安装")
            return False
    
    return True


def check_file_structure():
    """检查文件结构"""
    logger.info("检查文件结构...")
    
    current_dir = Path.cwd()
    
    # 检查脚本文件
    required_files = [
        "add_subtitles_to_mp4_optimized.py",
        "benchmark_subtitle_processing.py"
    ]
    
    for file in required_files:
        file_path = current_dir / file
        if file_path.exists():
            logger.info(f"脚本文件 {file}: 存在")
        else:
            logger.error(f"脚本文件 {file}: 不存在")
            return False
    
    # 检查字体目录
    fonts_dir = Path("/Users/donghaoliu/doc/short_whisper/fonts")
    if not fonts_dir.exists():
        fonts_dir = Path("/home/dhl/doc/short_whisper/fonts")
    
    if fonts_dir.exists():
        logger.info(f"字体目录: {fonts_dir}")
        
        # 检查字体文件
        font_files = [
            "Noto_Sans_EN/NotoSans-VariableFont_wdth,wght.ttf",
            "Noto_Sans_JP/NotoSansJP-VariableFont_wght.ttf",
            "Noto_Sans_VI/NotoSans-VariableFont_wdth,wght.ttf",
            "Noto_Sans_KR/NotoSansKR-VariableFont_wght.ttf"
        ]
        
        for font_file in font_files:
            font_path = fonts_dir / font_file
            if font_path.exists():
                logger.info(f"字体文件 {font_file}: 存在")
            else:
                logger.warning(f"字体文件 {font_file}: 不存在")
    else:
        logger.warning("字体目录不存在，可能影响字幕渲染")
    
    return True


def test_script_import():
    """测试脚本导入"""
    logger.info("测试脚本导入...")
    
    try:
        # 添加当前目录到Python路径
        current_dir = str(Path.cwd())
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # 尝试导入优化版本的主要类
        from add_subtitles_to_mp4_optimized import OptimizedSubtitleProcessor, TaskInfo
        
        logger.info("OptimizedSubtitleProcessor: 导入成功")
        logger.info("TaskInfo: 导入成功")
        
        # 测试实例化
        processor = OptimizedSubtitleProcessor()
        logger.info("OptimizedSubtitleProcessor: 实例化成功")
        
        # 测试基本方法
        if hasattr(processor, 'check_required_tools'):
            logger.info("check_required_tools方法: 存在")
        
        if hasattr(processor, 'collect_all_tasks'):
            logger.info("collect_all_tasks方法: 存在")
        
        if hasattr(processor, 'process_single_task'):
            logger.info("process_single_task方法: 存在")
        
        return True
        
    except Exception as e:
        logger.error(f"脚本导入失败: {str(e)}")
        return False


def test_basic_functionality():
    """测试基本功能"""
    logger.info("测试基本功能...")
    
    try:
        from add_subtitles_to_mp4_optimized import OptimizedSubtitleProcessor
        
        processor = OptimizedSubtitleProcessor()
        
        # 测试工具检查
        tools_ok = processor.check_required_tools()
        logger.info(f"必要工具检查: {'通过' if tools_ok else '失败'}")
        
        # 测试任务收集（空运行）
        try:
            tasks = processor.collect_all_tasks(['en'], force=False)
            logger.info(f"任务收集测试: 成功，找到 {len(tasks)} 个任务")
        except Exception as e:
            logger.warning(f"任务收集测试: 失败 ({str(e)}) - 这是正常的，如果没有测试数据")
        
        # 测试GPU检查
        gpu_info = processor.gpu_info
        if gpu_info and gpu_info.get('available'):
            logger.info(f"GPU检测: 可用 ({gpu_info.get('type', 'unknown')})")
        else:
            logger.info("GPU检测: 不可用，将使用CPU模式")
        
        # 测试系统信息
        system_info = processor.system_info
        logger.info(f"系统信息: {system_info['platform']}, CPU核心数: {system_info['cpu_count']}")
        
        return True
        
    except Exception as e:
        logger.error(f"基本功能测试失败: {str(e)}")
        return False


def run_help_test():
    """运行帮助信息测试"""
    logger.info("测试帮助信息...")
    
    try:
        result = subprocess.run(
            ["python3", "add_subtitles_to_mp4_optimized.py", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info("帮助信息测试: 成功")
            # 检查关键参数是否存在
            help_text = result.stdout
            required_args = ["-l", "--languages", "-f", "--force", "-s", "--single", "--gpu"]
            for arg in required_args:
                if arg in help_text:
                    logger.info(f"参数 {arg}: 存在")
                else:
                    logger.warning(f"参数 {arg}: 不存在")
            return True
        else:
            logger.error(f"帮助信息测试失败: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"帮助信息测试出错: {str(e)}")
        return False


def performance_comparison_test():
    """性能对比测试"""
    logger.info("测试性能对比工具...")
    
    try:
        result = subprocess.run(
            ["python3", "benchmark_subtitle_processing.py", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info("性能对比工具: 可用")
            return True
        else:
            logger.error(f"性能对比工具测试失败: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"性能对比工具测试出错: {str(e)}")
        return False


def main():
    """主测试函数"""
    logger.info("开始字幕处理优化版本测试...")
    logger.info("=" * 50)
    
    tests = [
        ("依赖项检查", check_dependencies),
        ("文件结构检查", check_file_structure),
        ("脚本导入测试", test_script_import),
        ("基本功能测试", test_basic_functionality),
        ("帮助信息测试", run_help_test),
        ("性能对比工具测试", performance_comparison_test),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n运行测试: {test_name}")
        logger.info("-" * 30)
        
        try:
            if test_func():
                logger.info(f"✅ {test_name}: 通过")
                passed_tests += 1
            else:
                logger.error(f"❌ {test_name}: 失败")
        except Exception as e:
            logger.error(f"❌ {test_name}: 异常 - {str(e)}")
    
    logger.info("\n" + "=" * 50)
    logger.info("测试总结:")
    logger.info(f"总测试数: {total_tests}")
    logger.info(f"通过测试: {passed_tests}")
    logger.info(f"失败测试: {total_tests - passed_tests}")
    logger.info(f"通过率: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        logger.info("🎉 所有测试通过！优化版本已准备就绪。")
        print("\n使用建议:")
        print("1. 运行 'python3 add_subtitles_to_mp4_optimized.py --help' 查看所有选项")
        print("2. 使用 'python3 benchmark_subtitle_processing.py' 对比性能")
        print("3. 查看 'README_subtitle_optimization.md' 了解详细使用说明")
    else:
        logger.warning("⚠️  部分测试失败，请检查相关问题后再使用。")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
