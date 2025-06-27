#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_tyro.py 输出检查脚本

功能描述：
    检查 fix_tyro.py 修复前后的 SRT 文件对，验证字幕条目数量是否相等。
    确保修复过程没有丢失或增加字幕条目。

检查内容：
    1. 修复前后 SRT 文件的字幕条目数量对比
    2. 检测缺失的输出文件
    3. 检测孤立的输出文件（没有对应输入文件）
    4. 验证 SRT 文件格式完整性
    5. 生成详细的检查报告

目录结构：
    输入目录（修复前）：
    - Linux: /media/dhl/buda_videos_youtube/format_srt_zh
    - macOS: /Volumes/dhl/buda_videos_youtube/format_srt_zh

    输出目录（修复后）：
    - Linux: /media/dhl/buda_videos_youtube/zh_srt_tyro_fix
    - macOS: /Volumes/dhl/buda_videos_youtube/zh_srt_tyro_fix

使用方法：
    python check_tyro_fix_srt_pairs.py [选项]

命令行参数：
    -i, --input PATH        输入SRT文件基础目录路径（默认自动检测）
    -o, --output PATH       输出SRT文件基础目录路径（默认自动检测）
    -c, --channel CHANNEL   只检查指定频道
    -v, --verbose           详细输出模式
    --fix-orphans          删除孤立的输出文件
    --show-content-diff     显示内容差异样例
    --diagnose             运行路径诊断模式，帮助找到输出路径问题
    --show-paths           显示示例文件路径

输出信息：
    ✅ 正常：修复前后字幕条目数量相等
    ❌ 错误：修复前后字幕条目数量不相等
    ⚠️  警告：缺失输出文件或孤立文件
    📊 统计：总体检查结果汇总

作者：dhl
版本：1.0
"""

import os
import re
import sys
import argparse
import platform
import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import difflib


def log_with_timestamp(message, level="INFO"):
    """带时间戳的日志输出"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def get_default_input_path():
    """获取默认输入路径（修复前SRT文件位置）"""
    if platform.system() == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube/format_srt_zh"
    else:  # Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube/format_srt_zh"


def get_default_output_path():
    """获取默认输出路径（修复后SRT文件位置）"""
    if platform.system() == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube/zh_srt_tyro_fix"
    else:  # Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube/zh_srt_tyro_fix"


def find_possible_output_paths():
    """查找可能的输出路径"""
    base_paths = []

    if platform.system() == "Darwin":  # macOS
        base_paths = [
            "/Volumes/dhl/buda_videos_youtube",
            "/Users/donghaoliu/Documents/buda_videos_youtube",
        ]
    else:  # Linux/Ubuntu
        base_paths = [
            "/media/dhl/buda_videos_youtube",
            "/home/dhl/buda_videos_youtube",
            os.path.expanduser("~/srt_fixed"),  # local模式
        ]

    possible_paths = []
    for base_path in base_paths:
        # 标准输出路径
        possible_paths.append(os.path.join(base_path, "zh_srt_tyro_fix"))
        # 可能的其他输出路径
        possible_paths.append(os.path.join(base_path, "srt_fixed"))
        possible_paths.append(os.path.join(base_path, "fixed_srt"))
        possible_paths.append(os.path.join(base_path, "tyro_fixed"))

    # 添加本地路径
    home_path = os.path.expanduser("~")
    possible_paths.append(os.path.join(home_path, "srt_fixed"))

    return possible_paths


def diagnose_output_paths(input_base: str, expected_output: str, verbose: bool = False):
    """诊断输出路径问题"""
    log_with_timestamp("🔍 开始路径诊断...")
    log_with_timestamp(f"输入路径: {input_base}")
    log_with_timestamp(f"期望输出路径: {expected_output}")

    # 检查期望输出路径
    if os.path.exists(expected_output):
        log_with_timestamp(f"✅ 期望输出路径存在: {expected_output}")

        # 检查是否为空目录
        try:
            items = os.listdir(expected_output)
            if items:
                log_with_timestamp(f"📁 输出目录包含 {len(items)} 个项目")
                if verbose:
                    for item in items[:5]:  # 只显示前5个
                        log_with_timestamp(f"    - {item}")
                    if len(items) > 5:
                        log_with_timestamp(f"    ... 还有 {len(items) - 5} 个项目")
            else:
                log_with_timestamp("⚠️  输出目录为空")
        except Exception as e:
            log_with_timestamp(f"❌ 无法读取输出目录: {e}", "ERROR")
    else:
        log_with_timestamp(f"❌ 期望输出路径不存在: {expected_output}")

        # 查找可能的输出路径
        log_with_timestamp("🔎 搜索可能的输出路径...")
        possible_paths = find_possible_output_paths()

        found_paths = []
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    items = os.listdir(path)
                    if items:  # 只显示非空目录
                        found_paths.append((path, len(items)))
                except:
                    continue

        if found_paths:
            log_with_timestamp("🎯 发现可能的输出路径:")
            for path, item_count in found_paths:
                log_with_timestamp(f"    - {path} ({item_count} 个项目)")
        else:
            log_with_timestamp("😞 未找到任何可能的输出路径")

            # 提供解决方案
            log_with_timestamp("\n💡 解决方案:")
            log_with_timestamp("1. 确认 fix_tyro.py 是否已运行：")
            log_with_timestamp("   python fix_tyro.py --help")
            log_with_timestamp("2. 检查 fix_tyro.py 运行日志中的输出路径")
            log_with_timestamp("3. 使用本地输出模式运行 fix_tyro.py：")
            log_with_timestamp("   python fix_tyro.py -l")
            log_with_timestamp("4. 手动指定输出路径运行检查脚本：")
            log_with_timestamp(
                "   python check_tyro_fix_srt_pairs.py -o /path/to/actual/output"
            )


def show_sample_file_paths(
    input_base: str, output_base: str, channel_filter: Optional[str] = None
):
    """显示示例文件路径，帮助调试"""
    log_with_timestamp("📋 显示示例文件路径...")

    # 查找输入文件
    input_files = find_srt_files(input_base, channel_filter)

    if not input_files:
        log_with_timestamp("❌ 未找到任何输入文件")
        return

        # 显示第一个频道的第一个文件路径示例
    first_channel = list(input_files.keys())[0]
    first_file = input_files[first_channel][0]

    # 构建对应的输出文件路径，处理双层目录结构
    rel_path = os.path.relpath(first_file, input_base)

    # 如果相对路径包含重复的频道名（双层结构），去掉一层
    path_parts = rel_path.split(os.sep)
    if len(path_parts) >= 3 and path_parts[0] == path_parts[1]:
        # 去掉重复的频道目录层
        rel_path = os.path.join(path_parts[0], *path_parts[2:])

    expected_output_file = os.path.join(output_base, rel_path)

    log_with_timestamp(f"📂 示例文件路径:")
    log_with_timestamp(f"  输入文件: {first_file}")
    log_with_timestamp(f"  期望输出文件: {expected_output_file}")
    log_with_timestamp(f"  相对路径: {rel_path}")

    # 检查输出文件是否存在
    if os.path.exists(expected_output_file):
        log_with_timestamp(f"  ✅ 输出文件存在")
    else:
        log_with_timestamp(f"  ❌ 输出文件不存在")

        # 检查输出目录是否存在
        output_dir = os.path.dirname(expected_output_file)
        if os.path.exists(output_dir):
            log_with_timestamp(f"  📁 输出目录存在: {output_dir}")
            try:
                files_in_dir = [f for f in os.listdir(output_dir) if f.endswith(".srt")]
                if files_in_dir:
                    log_with_timestamp(f"  📄 目录中有 {len(files_in_dir)} 个 SRT 文件")
                    if len(files_in_dir) <= 3:
                        for f in files_in_dir:
                            log_with_timestamp(f"      - {f}")
                    else:
                        for f in files_in_dir[:3]:
                            log_with_timestamp(f"      - {f}")
                        log_with_timestamp(
                            f"      ... 还有 {len(files_in_dir) - 3} 个文件"
                        )
                else:
                    log_with_timestamp(f"  📂 输出目录为空")
            except Exception as e:
                log_with_timestamp(f"  ❌ 无法读取输出目录: {e}")
        else:
            log_with_timestamp(f"  ❌ 输出目录不存在: {output_dir}")


def parse_srt_file(file_path: str) -> Tuple[int, List[Dict], bool]:
    """
    解析SRT文件并返回字幕条目信息

    Returns:
        Tuple[int, List[Dict], bool]: (条目数量, 条目列表, 是否解析成功)
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 使用正则表达式匹配SRT格式
        pattern = re.compile(
            r"(\d+)\s+(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\s+(.*?)(?=\n\n|\n\d+\n|\Z)",
            re.DOTALL,
        )

        matches = pattern.findall(content)
        subtitles = []

        for match in matches:
            index, start_time, end_time, subtitle_text = match
            subtitle_text = subtitle_text.replace("\n", " ").strip()

            subtitles.append(
                {
                    "index": int(index),
                    "start_time": start_time,
                    "end_time": end_time,
                    "text": subtitle_text,
                }
            )

        return len(subtitles), subtitles, True

    except Exception as e:
        log_with_timestamp(f"解析SRT文件失败 {file_path}: {e}", "ERROR")
        return 0, [], False


def check_srt_format_integrity(file_path: str) -> Tuple[bool, List[str]]:
    """
    检查SRT文件格式完整性

    Returns:
        Tuple[bool, List[str]]: (是否完整, 错误信息列表)
    """
    issues = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            issues.append("文件为空")
            return False, issues

        # 检查是否有基本的SRT格式元素
        if "-->" not in content:
            issues.append("缺少时间戳分隔符 '-->'")

        # 检查是否有数字索引
        if not re.search(r"^\d+$", content, re.MULTILINE):
            issues.append("缺少字幕索引号")

        # 检查时间戳格式
        timestamp_pattern = r"\d{2}:\d{2}:\d{2},\d{3}"
        if not re.search(timestamp_pattern, content):
            issues.append("时间戳格式不正确")

        return len(issues) == 0, issues

    except Exception as e:
        issues.append(f"读取文件异常: {e}")
        return False, issues


def find_srt_files(
    directory: str, channel_filter: Optional[str] = None
) -> Dict[str, List[str]]:
    """
    查找目录中的SRT文件，按频道分组

    Returns:
        Dict[str, List[str]]: {频道名: [SRT文件路径列表]}
    """
    srt_files = {}

    if not os.path.exists(directory):
        log_with_timestamp(f"目录不存在: {directory}", "ERROR")
        return srt_files

    try:
        for item in os.listdir(directory):
            if item.startswith("."):  # 跳过隐藏文件
                continue

            item_path = os.path.join(directory, item)
            if not os.path.isdir(item_path):
                continue

            channel = item
            if channel_filter and channel != channel_filter:
                continue

            # 检查是否为双层目录结构
            inner_channel_path = os.path.join(item_path, channel)
            if os.path.exists(inner_channel_path) and os.path.isdir(inner_channel_path):
                actual_path = inner_channel_path
            else:
                actual_path = item_path

            # 查找SRT文件
            channel_srt_files = []
            if os.path.exists(actual_path):
                for file in os.listdir(actual_path):
                    if file.endswith(".srt") and not file.startswith("."):
                        file_path = os.path.join(actual_path, file)
                        channel_srt_files.append(file_path)

            if channel_srt_files:
                srt_files[channel] = sorted(channel_srt_files)

    except Exception as e:
        log_with_timestamp(f"扫描目录失败 {directory}: {e}", "ERROR")

    return srt_files


def compare_srt_content(
    input_subtitles: List[Dict], output_subtitles: List[Dict], show_diff: bool = False
) -> List[str]:
    """
    比较修复前后字幕内容差异

    Returns:
        List[str]: 差异描述列表
    """
    differences = []

    if len(input_subtitles) != len(output_subtitles):
        differences.append(
            f"字幕条目数量不匹配: 输入{len(input_subtitles)} vs 输出{len(output_subtitles)}"
        )
        return differences

    content_changes = 0
    for i, (input_sub, output_sub) in enumerate(zip(input_subtitles, output_subtitles)):
        if input_sub["text"] != output_sub["text"]:
            content_changes += 1
            if show_diff and content_changes <= 3:  # 只显示前3个差异示例
                differences.append(f"第{i+1}条字幕内容变化:")
                differences.append(f"  修复前: {input_sub['text']}")
                differences.append(f"  修复后: {output_sub['text']}")

    if content_changes > 0:
        differences.append(f"总共{content_changes}条字幕内容被修改")

    return differences


def check_srt_pair(
    input_file: str,
    output_file: str,
    verbose: bool = False,
    show_content_diff: bool = False,
) -> Dict:
    """
    检查单个SRT文件对

    Returns:
        Dict: 检查结果
    """
    result = {
        "input_file": input_file,
        "output_file": output_file,
        "input_count": 0,
        "output_count": 0,
        "count_match": False,
        "input_valid": False,
        "output_valid": False,
        "issues": [],
        "differences": [],
    }

    # 检查输入文件
    if os.path.exists(input_file):
        input_count, input_subtitles, input_valid = parse_srt_file(input_file)
        result["input_count"] = input_count
        result["input_valid"] = input_valid

        if not input_valid:
            result["issues"].append("输入文件格式无效")

        # 检查输入文件完整性
        input_integrity, input_issues = check_srt_format_integrity(input_file)
        if not input_integrity:
            result["issues"].extend([f"输入文件: {issue}" for issue in input_issues])
    else:
        result["issues"].append("输入文件不存在")
        return result

    # 检查输出文件
    if os.path.exists(output_file):
        output_count, output_subtitles, output_valid = parse_srt_file(output_file)
        result["output_count"] = output_count
        result["output_valid"] = output_valid

        if not output_valid:
            result["issues"].append("输出文件格式无效")

        # 检查输出文件完整性
        output_integrity, output_issues = check_srt_format_integrity(output_file)
        if not output_integrity:
            result["issues"].extend([f"输出文件: {issue}" for issue in output_issues])

        # 比较数量
        result["count_match"] = input_count == output_count

        # 比较内容差异
        if input_valid and output_valid:
            differences = compare_srt_content(
                input_subtitles, output_subtitles, show_content_diff
            )
            result["differences"] = differences

    else:
        result["issues"].append("输出文件不存在")

    return result


def check_all_pairs(
    input_base: str,
    output_base: str,
    channel_filter: Optional[str] = None,
    verbose: bool = False,
    show_content_diff: bool = False,
) -> Dict:
    """
    检查所有SRT文件对

    Returns:
        Dict: 全部检查结果
    """
    log_with_timestamp(f"开始检查SRT文件对")
    log_with_timestamp(f"输入目录: {input_base}")
    log_with_timestamp(f"输出目录: {output_base}")

    # 查找输入和输出文件
    input_files = find_srt_files(input_base, channel_filter)
    output_files = find_srt_files(output_base, channel_filter)

    results = {
        "total_channels": 0,
        "total_files": 0,
        "successful_pairs": 0,
        "failed_pairs": 0,
        "missing_output": 0,
        "orphaned_output": 0,
        "channel_results": {},
        "orphaned_files": [],
    }

    # 检查每个频道
    for channel in input_files:
        log_with_timestamp(f"检查频道: {channel}")
        results["total_channels"] += 1

        channel_result = {
            "input_files": len(input_files[channel]),
            "successful_pairs": 0,
            "failed_pairs": 0,
            "missing_output": 0,
            "file_results": [],
        }

        for input_file in input_files[channel]:
            # 构建对应的输出文件路径，处理双层目录结构
            rel_path = os.path.relpath(input_file, input_base)

            # 如果相对路径包含重复的频道名（双层结构），去掉一层
            path_parts = rel_path.split(os.sep)
            if len(path_parts) >= 3 and path_parts[0] == path_parts[1]:
                # 去掉重复的频道目录层
                rel_path = os.path.join(path_parts[0], *path_parts[2:])

            output_file = os.path.join(output_base, rel_path)

            results["total_files"] += 1

            # 检查文件对
            pair_result = check_srt_pair(
                input_file, output_file, verbose, show_content_diff
            )
            channel_result["file_results"].append(pair_result)

            # 统计结果
            if os.path.exists(output_file):
                if (
                    pair_result["count_match"]
                    and pair_result["input_valid"]
                    and pair_result["output_valid"]
                ):
                    channel_result["successful_pairs"] += 1
                    results["successful_pairs"] += 1
                    if verbose:
                        log_with_timestamp(
                            f"✅ {os.path.basename(input_file)}: {pair_result['input_count']} 条字幕"
                        )
                else:
                    channel_result["failed_pairs"] += 1
                    results["failed_pairs"] += 1
                    log_with_timestamp(
                        f"❌ {os.path.basename(input_file)}: 输入{pair_result['input_count']} vs 输出{pair_result['output_count']}",
                        "ERROR",
                    )
                    if pair_result["issues"]:
                        for issue in pair_result["issues"]:
                            log_with_timestamp(f"   问题: {issue}", "ERROR")
                    if pair_result["differences"] and verbose:
                        for diff in pair_result["differences"]:
                            log_with_timestamp(f"   差异: {diff}", "INFO")
            else:
                channel_result["missing_output"] += 1
                results["missing_output"] += 1
                log_with_timestamp(
                    f"⚠️  缺失输出文件: {os.path.basename(input_file)}", "WARNING"
                )

        results["channel_results"][channel] = channel_result

    # 检查孤立的输出文件
    for channel in output_files:
        if channel not in input_files:
            for output_file in output_files[channel]:
                results["orphaned_files"].append(output_file)
                results["orphaned_output"] += 1
        else:
            # 检查频道内的孤立文件
            input_basenames = set(os.path.basename(f) for f in input_files[channel])
            for output_file in output_files[channel]:
                output_basename = os.path.basename(output_file)
                if output_basename not in input_basenames:
                    results["orphaned_files"].append(output_file)
                    results["orphaned_output"] += 1

    return results


def print_summary_report(results: Dict):
    """打印汇总报告"""
    log_with_timestamp("=" * 80)
    log_with_timestamp("📊 检查结果汇总报告")
    log_with_timestamp("=" * 80)

    log_with_timestamp(f"检查的频道数量: {results['total_channels']}")
    log_with_timestamp(f"检查的文件总数: {results['total_files']}")
    log_with_timestamp(f"成功的文件对: {results['successful_pairs']}")
    log_with_timestamp(f"失败的文件对: {results['failed_pairs']}")
    log_with_timestamp(f"缺失的输出文件: {results['missing_output']}")
    log_with_timestamp(f"孤立的输出文件: {results['orphaned_output']}")

    if results["total_files"] > 0:
        success_rate = (results["successful_pairs"] / results["total_files"]) * 100
        log_with_timestamp(f"成功率: {success_rate:.1f}%")

    # 频道详细报告
    if results["channel_results"]:
        log_with_timestamp("\n频道详细统计:")
        for channel, channel_result in results["channel_results"].items():
            log_with_timestamp(f"  {channel}:")
            log_with_timestamp(f"    输入文件: {channel_result['input_files']}")
            log_with_timestamp(f"    成功: {channel_result['successful_pairs']}")
            log_with_timestamp(f"    失败: {channel_result['failed_pairs']}")
            log_with_timestamp(f"    缺失: {channel_result['missing_output']}")

    # 孤立文件列表
    if results["orphaned_files"]:
        log_with_timestamp(
            f"\n⚠️  发现 {len(results['orphaned_files'])} 个孤立的输出文件:"
        )
        for orphaned_file in results["orphaned_files"][:10]:  # 只显示前10个
            log_with_timestamp(f"    {orphaned_file}")
        if len(results["orphaned_files"]) > 10:
            log_with_timestamp(
                f"    ... 还有 {len(results['orphaned_files']) - 10} 个文件"
            )

    log_with_timestamp("=" * 80)


def fix_orphaned_files(orphaned_files: List[str]) -> int:
    """删除孤立的输出文件"""
    deleted_count = 0

    for orphaned_file in orphaned_files:
        try:
            os.remove(orphaned_file)
            log_with_timestamp(f"已删除孤立文件: {orphaned_file}")
            deleted_count += 1
        except Exception as e:
            log_with_timestamp(f"删除文件失败 {orphaned_file}: {e}", "ERROR")

    return deleted_count


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="检查 fix_tyro.py 修复前后的 SRT 文件对"
    )

    parser.add_argument(
        "-i", "--input", default=None, help="输入SRT文件基础目录路径（默认自动检测）"
    )

    parser.add_argument(
        "-o", "--output", default=None, help="输出SRT文件基础目录路径（默认自动检测）"
    )

    parser.add_argument("-c", "--channel", help="只检查指定频道")

    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出模式")

    parser.add_argument("--fix-orphans", action="store_true", help="删除孤立的输出文件")

    parser.add_argument(
        "--show-content-diff", action="store_true", help="显示内容差异样例"
    )

    parser.add_argument(
        "--diagnose", action="store_true", help="运行路径诊断模式，帮助找到输出路径问题"
    )

    parser.add_argument("--show-paths", action="store_true", help="显示示例文件路径")

    args = parser.parse_args()

    # 确定输入输出路径
    input_base = args.input if args.input else get_default_input_path()
    output_base = args.output if args.output else get_default_output_path()

    log_with_timestamp("开始 fix_tyro.py SRT 文件对检查")
    log_with_timestamp(f"Python版本: {sys.version}")
    log_with_timestamp(f"操作系统: {platform.system()} {platform.release()}")

    # 检查目录是否存在
    if not os.path.exists(input_base):
        log_with_timestamp(f"输入目录不存在: {input_base}", "ERROR")
        return

    # 路径诊断模式
    if args.diagnose:
        diagnose_output_paths(input_base, output_base, args.verbose)
        return

    # 显示路径模式
    if args.show_paths:
        show_sample_file_paths(input_base, output_base, args.channel)
        return

    if not os.path.exists(output_base):
        log_with_timestamp(f"输出目录不存在: {output_base}", "ERROR")
        log_with_timestamp(
            "💡 建议运行路径诊断: python check_tyro_fix_srt_pairs.py --diagnose"
        )
        return

    # 执行检查
    results = check_all_pairs(
        input_base, output_base, args.channel, args.verbose, args.show_content_diff
    )

    # 打印报告
    print_summary_report(results)

    # 如果所有文件都缺失，提供诊断建议
    if (
        results["total_files"] > 0
        and results["missing_output"] == results["total_files"]
    ):
        log_with_timestamp("\n💡 所有输出文件都缺失，建议:")
        log_with_timestamp(
            "1. 运行路径诊断: python check_tyro_fix_srt_pairs.py --diagnose"
        )
        log_with_timestamp(
            "2. 查看示例路径: python check_tyro_fix_srt_pairs.py --show-paths"
        )
        log_with_timestamp("3. 确认 fix_tyro.py 是否已成功运行")

    # 处理孤立文件
    if args.fix_orphans and results["orphaned_files"]:
        user_confirm = input(
            f"\n确认删除 {len(results['orphaned_files'])} 个孤立的输出文件? (y/N): "
        )
        if user_confirm.lower() == "y":
            deleted_count = fix_orphaned_files(results["orphaned_files"])
            log_with_timestamp(f"已删除 {deleted_count} 个孤立文件")

    # 返回退出码
    if results["failed_pairs"] > 0 or results["missing_output"] > 0:
        log_with_timestamp("检查发现问题，退出码: 1", "WARNING")
        sys.exit(1)
    else:
        log_with_timestamp("所有检查通过，退出码: 0")
        sys.exit(0)


if __name__ == "__main__":
    main()
