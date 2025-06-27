#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
字幕处理性能对比工具

用于对比原版和优化版字幕处理脚本的性能差异
"""

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path
import logging
import json
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_script_with_timing(script_path: str, args: list) -> dict:
    """运行脚本并记录性能数据"""
    if not Path(script_path).exists():
        logger.error(f"脚本不存在: {script_path}")
        return None
    
    logger.info(f"开始运行: {script_path}")
    logger.info(f"参数: {' '.join(args)}")
    
    start_time = time.time()
    start_datetime = datetime.now()
    
    try:
        # 运行脚本
        cmd = ["python3", script_path] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(script_path).parent
        )
        
        end_time = time.time()
        end_datetime = datetime.now()
        execution_time = end_time - start_time
        
        # 解析输出中的统计信息
        stats = parse_script_output(result.stdout, result.stderr)
        
        performance_data = {
            'script_path': script_path,
            'args': args,
            'start_time': start_datetime.isoformat(),
            'end_time': end_datetime.isoformat(),
            'execution_time': execution_time,
            'return_code': result.returncode,
            'success': result.returncode == 0,
            'stdout_lines': len(result.stdout.splitlines()),
            'stderr_lines': len(result.stderr.splitlines()),
            'parsed_stats': stats
        }
        
        if result.returncode == 0:
            logger.info(f"脚本执行成功，耗时: {execution_time:.2f}秒")
        else:
            logger.error(f"脚本执行失败，返回码: {result.returncode}")
            logger.error(f"错误输出: {result.stderr[:500]}...")
        
        return performance_data
        
    except Exception as e:
        logger.error(f"运行脚本时出错: {str(e)}")
        return None


def parse_script_output(stdout: str, stderr: str) -> dict:
    """解析脚本输出中的统计信息"""
    stats = {}
    
    # 解析标准输出中的统计信息
    lines = stdout.splitlines()
    for line in lines:
        line = line.strip()
        
        # 解析各种统计信息
        if "找到" in line and "个待处理任务" in line:
            try:
                stats['total_tasks_found'] = int(line.split("找到")[1].split("个")[0].strip())
            except:
                pass
        
        elif "总任务数:" in line:
            try:
                stats['total_tasks'] = int(line.split(":")[1].strip())
            except:
                pass
        
        elif "成功任务:" in line:
            try:
                stats['successful_tasks'] = int(line.split(":")[1].strip())
            except:
                pass
        
        elif "失败任务:" in line:
            try:
                stats['failed_tasks'] = int(line.split(":")[1].strip())
            except:
                pass
        
        elif "成功率:" in line:
            try:
                stats['success_rate'] = float(line.split(":")[1].replace("%", "").strip())
            except:
                pass
        
        elif "总耗时:" in line:
            try:
                stats['total_time'] = float(line.split(":")[1].replace("秒", "").strip())
            except:
                pass
        
        elif "I/O耗时:" in line:
            try:
                stats['io_time'] = float(line.split(":")[1].replace("秒", "").strip())
            except:
                pass
        
        elif "编码耗时:" in line:
            try:
                stats['encoding_time'] = float(line.split(":")[1].replace("秒", "").strip())
            except:
                pass
        
        elif "平均处理时间:" in line:
            try:
                stats['avg_processing_time'] = float(line.split(":")[1].replace("秒/任务", "").strip())
            except:
                pass
    
    return stats


def compare_performance(original_data: dict, optimized_data: dict) -> dict:
    """对比两个版本的性能数据"""
    if not original_data or not optimized_data:
        return None
    
    comparison = {
        'original': original_data,
        'optimized': optimized_data,
        'improvements': {}
    }
    
    # 对比执行时间
    if original_data['execution_time'] > 0:
        time_improvement = (original_data['execution_time'] - optimized_data['execution_time']) / original_data['execution_time'] * 100
        comparison['improvements']['execution_time'] = {
            'original': original_data['execution_time'],
            'optimized': optimized_data['execution_time'],
            'improvement_percent': time_improvement,
            'time_saved': original_data['execution_time'] - optimized_data['execution_time']
        }
    
    # 对比解析出的统计数据
    original_stats = original_data.get('parsed_stats', {})
    optimized_stats = optimized_data.get('parsed_stats', {})
    
    for key in ['total_time', 'io_time', 'encoding_time', 'avg_processing_time']:
        if key in original_stats and key in optimized_stats and original_stats[key] > 0:
            improvement = (original_stats[key] - optimized_stats[key]) / original_stats[key] * 100
            comparison['improvements'][key] = {
                'original': original_stats[key],
                'optimized': optimized_stats[key],
                'improvement_percent': improvement,
                'time_saved': original_stats[key] - optimized_stats[key]
            }
    
    return comparison


def print_comparison_report(comparison: dict):
    """打印性能对比报告"""
    if not comparison:
        logger.error("无法生成对比报告")
        return
    
    print("\n" + "="*60)
    print("性能对比报告")
    print("="*60)
    
    original = comparison['original']
    optimized = comparison['optimized']
    improvements = comparison['improvements']
    
    print(f"\n原版脚本:")
    print(f"  执行时间: {original['execution_time']:.2f}秒")
    print(f"  成功状态: {'成功' if original['success'] else '失败'}")
    
    print(f"\n优化版脚本:")
    print(f"  执行时间: {optimized['execution_time']:.2f}秒")
    print(f"  成功状态: {'成功' if optimized['success'] else '失败'}")
    
    print(f"\n性能改进:")
    
    if 'execution_time' in improvements:
        exec_imp = improvements['execution_time']
        print(f"  总执行时间: {exec_imp['improvement_percent']:.1f}% 提升")
        print(f"    原版: {exec_imp['original']:.2f}秒")
        print(f"    优化版: {exec_imp['optimized']:.2f}秒")
        print(f"    节省时间: {exec_imp['time_saved']:.2f}秒")
    
    for key, label in [
        ('total_time', '总处理时间'),
        ('io_time', 'I/O时间'),
        ('encoding_time', '编码时间'),
        ('avg_processing_time', '平均处理时间')
    ]:
        if key in improvements:
            imp = improvements[key]
            print(f"  {label}: {imp['improvement_percent']:.1f}% 提升")
            print(f"    原版: {imp['original']:.2f}秒")
            print(f"    优化版: {imp['optimized']:.2f}秒")
            print(f"    节省时间: {imp['time_saved']:.2f}秒")
    
    print("\n" + "="*60)


def save_benchmark_results(comparison: dict, output_file: str):
    """保存基准测试结果到文件"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(comparison, f, ensure_ascii=False, indent=2)
        logger.info(f"基准测试结果已保存到: {output_file}")
    except Exception as e:
        logger.error(f"保存结果时出错: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="字幕处理性能对比工具")
    
    parser.add_argument(
        "--original",
        default="add_subtitles_to_mp4.py",
        help="原版脚本路径"
    )
    parser.add_argument(
        "--optimized", 
        default="add_subtitles_to_mp4_optimized.py",
        help="优化版脚本路径"
    )
    parser.add_argument(
        "--test-args",
        nargs="*",
        default=["-l", "en", "-s", "test_channel/test_video"],
        help="测试参数"
    )
    parser.add_argument(
        "--output",
        default="benchmark_results.json",
        help="结果输出文件"
    )
    parser.add_argument(
        "--skip-original",
        action="store_true",
        help="跳过原版脚本测试（仅测试优化版）"
    )
    
    args = parser.parse_args()
    
    # 确保脚本路径是绝对路径
    current_dir = Path.cwd()
    original_script = current_dir / args.original
    optimized_script = current_dir / args.optimized
    
    logger.info("开始性能基准测试...")
    logger.info(f"测试参数: {' '.join(args.test_args)}")
    
    original_data = None
    if not args.skip_original:
        logger.info("\n测试原版脚本...")
        original_data = run_script_with_timing(str(original_script), args.test_args)
    
    logger.info("\n测试优化版脚本...")
    optimized_data = run_script_with_timing(str(optimized_script), args.test_args)
    
    if original_data and optimized_data:
        # 生成对比报告
        comparison = compare_performance(original_data, optimized_data)
        print_comparison_report(comparison)
        
        # 保存结果
        save_benchmark_results(comparison, args.output)
    elif optimized_data:
        logger.info("仅优化版脚本测试完成")
        print(f"\n优化版脚本执行时间: {optimized_data['execution_time']:.2f}秒")
        print(f"执行状态: {'成功' if optimized_data['success'] else '失败'}")
        
        # 保存单个结果
        result = {'optimized_only': optimized_data}
        save_benchmark_results(result, args.output)
    else:
        logger.error("测试失败")


if __name__ == "__main__":
    main()
