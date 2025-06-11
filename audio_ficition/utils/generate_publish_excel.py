#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube发布状态追踪Excel生成器

读取 add_subtitles_to_videos.py 输出的MP4文件，生成Excel表格追踪YouTube发布状态。
支持多个主题：scifi、thriller、romance、horror、fantasy等。

功能特性：
1. 自动扫描各主题的MP4输出文件
2. 生成对应主题的Excel文件（如 scifi.xlsx）
3. 包含列：mp4_name, if_published, publish_date
4. 支持增量更新（append only）
5. 排除Mac系统产生的点文件

使用方法：
1. 单个主题: python generate_publish_excel.py --topic scifi
2. 所有主题: python generate_publish_excel.py --all
3. 指定主题: python generate_publish_excel.py --topic thriller,romance
4. 强制重新生成: python generate_publish_excel.py --topic scifi --force

输出路径: publish_log/[主题].xlsx
"""

import os
import sys
import glob
import re
import argparse
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set
import pandas as pd


# 支持的主题列表
SUPPORTED_TOPICS = ["scifi", "thriller", "romance", "horror", "fantasy"]

# Excel列定义
EXCEL_COLUMNS = ["mp4_name", "if_published", "publish_date"]


def get_topic_paths(topic: str) -> Dict[str, str]:
    """根据主题和操作系统返回对应的路径"""
    system = platform.system()

    if system == "Darwin":  # macOS
        base_path = f"/Volumes/dhl/audio/{topic}"
    else:  # Linux/Ubuntu
        base_path = f"/mnt/dhl/audio/{topic}"

    return {
        "input_dir": f"{base_path}/mp4_with_subtitles",  # add_subtitles_to_videos.py的输出目录
        "excel_dir": "publish_log",  # Excel文件存放目录
        "excel_file": f"publish_log/{topic}.xlsx",
    }


def scan_mp4_files(input_dir: str) -> List[str]:
    """扫描输入目录中的MP4文件，排除点文件"""
    mp4_files = []

    if not os.path.exists(input_dir):
        print(f"⚠️  目录不存在: {input_dir}")
        return mp4_files

    # 扫描所有MP4文件
    pattern = os.path.join(input_dir, "*.mp4")
    for file_path in glob.glob(pattern):
        filename = os.path.basename(file_path)

        # 排除Mac系统产生的点文件
        if filename.startswith("."):
            continue

        # 验证文件名格式（数字.mp4）
        if re.match(r"^\d+\.mp4$", filename):
            # 验证文件大小（大于1MB才认为是有效文件）
            try:
                file_size = os.path.getsize(file_path)
                if file_size > 1024 * 1024:  # 1MB
                    mp4_files.append(filename)
            except Exception:
                continue

    # 按文件名中的数字排序
    mp4_files.sort(key=lambda x: int(x.split(".")[0]))
    return mp4_files


def load_existing_excel(excel_file: str) -> pd.DataFrame:
    """加载现有的Excel文件，如果不存在则返回空DataFrame"""
    if os.path.exists(excel_file):
        try:
            df = pd.read_excel(excel_file)
            print(f"📄 已加载现有Excel: {excel_file} ({len(df)} 条记录)")
            return df
        except Exception as e:
            print(f"⚠️  读取Excel文件失败: {e}")
            print(f"   将创建新的Excel文件")

    # 返回空DataFrame
    return pd.DataFrame(columns=EXCEL_COLUMNS)


def get_existing_mp4_names(df: pd.DataFrame) -> Set[str]:
    """获取已存在的MP4文件名集合"""
    if "mp4_name" in df.columns:
        return set(df["mp4_name"].tolist())
    return set()


def create_new_records(new_mp4_files: List[str]) -> pd.DataFrame:
    """为新的MP4文件创建记录"""
    records = []

    for mp4_file in new_mp4_files:
        records.append(
            {
                "mp4_name": mp4_file,
                "if_published": 0,  # 初始未发布
                "publish_date": "",  # 初始空值
            }
        )

    return pd.DataFrame(records)


def save_excel(df: pd.DataFrame, excel_file: str) -> bool:
    """保存DataFrame到Excel文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(excel_file), exist_ok=True)

        # 保存Excel文件
        df.to_excel(excel_file, index=False)
        print(f"✅ Excel文件已保存: {excel_file}")
        return True
    except Exception as e:
        print(f"❌ 保存Excel文件失败: {e}")
        return False


def process_topic(topic: str, force: bool = False) -> bool:
    """处理单个主题"""
    print(f"\n🎬 处理主题: {topic.upper()}")
    print("-" * 50)

    # 获取路径配置
    paths = get_topic_paths(topic)
    input_dir = paths["input_dir"]
    excel_file = paths["excel_file"]

    print(f"📁 输入目录: {input_dir}")
    print(f"📊 Excel文件: {excel_file}")

    # 扫描MP4文件
    print(f"🔍 扫描MP4文件...")
    mp4_files = scan_mp4_files(input_dir)

    if not mp4_files:
        print(f"❌ 未找到任何有效的MP4文件")
        return False

    print(f"📦 找到 {len(mp4_files)} 个MP4文件")

    # 加载现有Excel文件
    if force:
        print(f"🔄 强制重新生成Excel文件")
        existing_df = pd.DataFrame(columns=EXCEL_COLUMNS)
    else:
        existing_df = load_existing_excel(excel_file)

    # 获取已存在的MP4文件名
    existing_mp4_names = get_existing_mp4_names(existing_df)

    # 找出新的MP4文件
    new_mp4_files = [f for f in mp4_files if f not in existing_mp4_names]

    if not new_mp4_files and not force:
        print(f"✅ 所有MP4文件都已在Excel中，无需更新")
        print(f"   总记录数: {len(existing_df)}")
        return True

    print(f"🆕 发现 {len(new_mp4_files)} 个新MP4文件")

    # 为新文件创建记录
    if new_mp4_files:
        new_records_df = create_new_records(new_mp4_files)
        print(f"📝 创建 {len(new_records_df)} 条新记录")

        # 合并数据（append only）
        if not existing_df.empty:
            final_df = pd.concat([existing_df, new_records_df], ignore_index=True)
        else:
            final_df = new_records_df
    else:
        final_df = existing_df

    # 按mp4_name排序（按数字顺序）
    try:
        final_df["sort_key"] = final_df["mp4_name"].apply(
            lambda x: int(x.split(".")[0])
        )
        final_df = final_df.sort_values("sort_key").drop("sort_key", axis=1)
    except Exception:
        # 如果排序失败，使用原始顺序
        pass

    # 保存Excel文件
    success = save_excel(final_df, excel_file)

    if success:
        print(f"📊 Excel统计:")
        print(f"   总记录数: {len(final_df)}")
        print(f"   已发布: {len(final_df[final_df['if_published'] == 1])}")
        print(f"   未发布: {len(final_df[final_df['if_published'] == 0])}")

        # 显示最新添加的文件
        if new_mp4_files:
            print(f"🆕 新增文件:")
            for mp4_file in new_mp4_files[:5]:  # 显示前5个
                print(f"   - {mp4_file}")
            if len(new_mp4_files) > 5:
                print(f"   ... 还有 {len(new_mp4_files) - 5} 个文件")

    return success


def validate_topics(topics: List[str]) -> List[str]:
    """验证主题列表，返回有效的主题"""
    valid_topics = []
    invalid_topics = []

    for topic in topics:
        topic = topic.strip().lower()
        if topic in SUPPORTED_TOPICS:
            valid_topics.append(topic)
        else:
            invalid_topics.append(topic)

    if invalid_topics:
        print(f"⚠️  不支持的主题: {', '.join(invalid_topics)}")
        print(f"   支持的主题: {', '.join(SUPPORTED_TOPICS)}")

    return valid_topics


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="YouTube发布状态追踪Excel生成器")

    # 主题参数
    parser.add_argument(
        "--topic",
        help=f"指定要处理的主题，支持多个主题用逗号分隔。支持的主题: {', '.join(SUPPORTED_TOPICS)}",
    )
    parser.add_argument("--all", action="store_true", help="处理所有支持的主题")

    # 行为参数
    parser.add_argument(
        "--force", action="store_true", help="强制重新生成Excel文件（忽略现有数据）"
    )

    # 信息参数
    parser.add_argument("--list-topics", action="store_true", help="列出所有支持的主题")

    args = parser.parse_args()

    # 显示支持的主题
    if args.list_topics:
        print("📋 支持的主题列表:")
        for topic in SUPPORTED_TOPICS:
            print(f"   - {topic}")
        return

    print("📊 YouTube发布状态追踪Excel生成器")
    print("=" * 60)
    print(f"🖥️  操作系统: {platform.system()}")

    # 确定要处理的主题
    topics_to_process = []

    if args.all:
        topics_to_process = SUPPORTED_TOPICS.copy()
        print(f"🎯 处理所有主题: {', '.join(topics_to_process)}")
    elif args.topic:
        topics_input = args.topic.split(",")
        topics_to_process = validate_topics(topics_input)
        if not topics_to_process:
            print(f"❌ 没有有效的主题可处理")
            return
        print(f"🎯 处理指定主题: {', '.join(topics_to_process)}")
    else:
        print(f"❌ 请指定要处理的主题或使用 --all 处理所有主题")
        print(f"   使用 --help 查看使用说明")
        return

    # 确保输出目录存在
    os.makedirs("publish_log", exist_ok=True)

    # 处理每个主题
    success_count = 0
    failed_count = 0

    for topic in topics_to_process:
        try:
            success = process_topic(topic, args.force)
            if success:
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"❌ 处理主题 {topic} 时出错: {e}")
            failed_count += 1

    # 总结
    print(f"\n{'='*60}")
    print(f"🎉 处理完成")
    print(f"✅ 成功: {success_count} 个主题")
    print(f"❌ 失败: {failed_count} 个主题")
    print(f"📁 Excel文件目录: publish_log/")

    if success_count > 0:
        print(f"\n💡 使用提示:")
        print(f"   - 使用 --force 可强制重新生成Excel文件")
        print(f"   - Excel文件包含三列: mp4_name, if_published, publish_date")
        print(f"   - if_published: 0=未发布, 1=已发布")
        print(f"   - publish_date: 发布日期（格式: YYYY-MM-DD）")


if __name__ == "__main__":
    main()
