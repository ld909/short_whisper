#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据UUID查找对应的URL
简单实用工具
"""

import os
import json
import sys
import argparse
import platform


def get_base_media_path():
    """根据操作系统返回适当的媒体路径"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl/audio"
    else:  # 默认为Linux/Ubuntu
        return "/mnt/dhl/audio"


def find_url_by_uuid(target_uuid, language="en"):
    """根据UUID查找对应的URL"""
    base_media_path = get_base_media_path()

    # 根据语言设置路径
    if language == "zh":
        uuid_mapping_file = os.path.join(
            base_media_path, "books_zh", "zh", "uuid_mapping.json"
        )
    else:
        uuid_mapping_file = os.path.join(
            base_media_path, "books", "en", "uuid_mapping.json"
        )

    # 检查文件是否存在
    if not os.path.exists(uuid_mapping_file):
        print(f"❌ UUID映射文件不存在: {uuid_mapping_file}")
        return None

    try:
        # 加载UUID映射
        with open(uuid_mapping_file, "r", encoding="utf-8") as f:
            uuid_mapping = json.load(f)

        # 反向搜索 (URL -> UUID 映射中找到 UUID -> URL)
        for url, uuid_val in uuid_mapping.items():
            if uuid_val == target_uuid:
                return url

        return None

    except Exception as e:
        print(f"❌ 读取UUID映射文件失败: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="根据UUID查找对应的URL")
    parser.add_argument("uuid", help="要查找的UUID")
    parser.add_argument(
        "--language",
        "-l",
        choices=["en", "zh"],
        default="en",
        help="选择语种: en(英文) 或 zh(中文) [默认: en]",
    )

    args = parser.parse_args()

    # 查找URL
    url = find_url_by_uuid(args.uuid, args.language)

    if url:
        print(f"✅ 找到对应URL:")
        print(url)
    else:
        print(f"❌ 未找到UUID对应的URL: {args.uuid}")
        sys.exit(1)


if __name__ == "__main__":
    main()
