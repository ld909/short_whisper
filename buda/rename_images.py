#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
重命名图像文件脚本
功能：将指定目录中所有图像文件完全重命名为随机英文字母和数字的组合
"""

import os
import random
import string
import shutil
import platform
from pathlib import Path

# 图像文件扩展名列表
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"]


def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


def generate_random_chars(length=8):
    """生成指定长度的随机英文字母和数字组合"""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def rename_images(directory_path):
    """重命名指定目录中的所有图像文件"""
    directory = Path(directory_path)

    # 确保目录存在
    if not directory.exists() or not directory.is_dir():
        print(f"错误：目录 {directory_path} 不存在")
        return

    # 获取目录中所有文件
    files = list(directory.iterdir())

    # 计数器
    renamed_count = 0

    # 处理每个文件
    for file_path in files:
        # 检查是否为文件且扩展名在图像扩展名列表中
        if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS:
            # 生成新文件名（完全随机）
            random_chars = generate_random_chars(12)
            new_name = f"{random_chars}{file_path.suffix}"
            new_path = file_path.parent / new_name

            # 重命名文件
            shutil.move(str(file_path), str(new_path))
            print(f"已重命名: {file_path.name} -> {new_name}")
            renamed_count += 1

    print(f"\n总共重命名了 {renamed_count} 个图像文件")


if __name__ == "__main__":
    # 获取基础路径并构建目标目录
    base_path = get_base_path()
    directory_path = os.path.join(base_path, "buda_images")

    print(f"当前操作系统: {platform.system()}")
    print(f"使用基础路径: {base_path}")
    print(f"图像目录路径: {directory_path}")

    rename_images(directory_path)
