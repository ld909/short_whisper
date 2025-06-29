#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍Clip生成器配置测试脚本

用于验证 generate_book_clips.py 的路径配置和字体设置是否正确
"""

import os
import sys

# 将generate_book_clips.py所在的目录添加到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from generate_book_clips import (
    check_ubuntu_system,
    get_base_media_path,
    get_input_directories,
    get_output_directory,
    get_available_fonts,
    get_merriweather_font_path,
    get_background_video,
)

def test_system_check():
    """测试系统检查"""
    print("=== 系统检查 ===")
    is_ubuntu = check_ubuntu_system()
    print(f"Ubuntu系统检查: {'通过' if is_ubuntu else '失败'}")
    
    base_path = get_base_media_path()
    print(f"基础媒体路径: {base_path}")
    
    return is_ubuntu, base_path


def test_paths_config(language="en"):
    """测试路径配置"""
    print(f"\n=== 路径配置测试 ({language}) ===")
    
    # 输入目录配置
    input_dirs = get_input_directories(language)
    print(f"输入目录配置:")
    for key, path in input_dirs.items():
        exists = os.path.exists(path) if path else False
        status = "✅ 存在" if exists else "❌ 不存在"
        print(f"  {key}: {path} {status}")
    
    # 输出目录配置
    output_dir = get_output_directory(language)
    output_exists = os.path.exists(output_dir) if output_dir else False
    output_status = "✅ 存在" if output_exists else "❌ 不存在"
    print(f"输出目录: {output_dir} {output_status}")
    
    return input_dirs, output_dir


def test_font_config(language="en"):
    """测试字体配置"""
    print(f"\n=== 字体配置测试 ({language}) ===")
    
    # 获取可用字体
    font_files = get_available_fonts(language)
    print(f"找到字体文件 {len(font_files)} 个:")
    for font_file in font_files[:5]:  # 只显示前5个
        font_name = os.path.basename(font_file)
        print(f"  📝 {font_name}")
    
    if len(font_files) > 5:
        print(f"  ... 还有 {len(font_files) - 5} 个字体文件")
    
    # 获取推荐字体
    recommended_font = get_merriweather_font_path(language)
    if recommended_font:
        print(f"推荐字体: {os.path.basename(recommended_font)} ✅")
    else:
        print(f"推荐字体: 未找到 ❌")
    
    return font_files, recommended_font


def test_background_video(language="en"):
    """测试背景视频"""
    print(f"\n=== 背景视频测试 ({language}) ===")
    
    bg_video = get_background_video(language)
    if bg_video:
        video_exists = os.path.exists(bg_video)
        status = "✅ 存在" if video_exists else "❌ 不存在"
        print(f"背景视频: {bg_video} {status}")
        
        if video_exists:
            file_size = os.path.getsize(bg_video) / (1024 * 1024)  # MB
            print(f"文件大小: {file_size:.2f} MB")
    else:
        print("背景视频: 未找到 ❌")
    
    return bg_video


def main():
    """主测试函数"""
    print("🧪 书籍Clip生成器配置测试")
    print("=" * 50)
    
    # 系统检查
    is_ubuntu, base_path = test_system_check()
    
    if not is_ubuntu:
        print("\n⚠️ 注意: 该脚本只支持Ubuntu系统")
        print("   如果你在其他系统上测试，路径可能不正确")
    
    if not base_path:
        print("\n❌ 无法获取基础媒体路径，请检查系统配置")
        return
    
    # 测试英文配置
    print("\n" + "="*50)
    print("🇺🇸 英文配置测试")
    en_input_dirs, en_output_dir = test_paths_config("en")
    en_fonts, en_recommended_font = test_font_config("en")
    en_bg_video = test_background_video("en")
    
    # 测试中文配置
    print("\n" + "="*50)
    print("🇨🇳 中文配置测试")
    zh_input_dirs, zh_output_dir = test_paths_config("zh")
    zh_fonts, zh_recommended_font = test_font_config("zh")
    zh_bg_video = test_background_video("zh")
    
    # 总结
    print("\n" + "="*50)
    print("📊 测试总结")
    
    print(f"\n英文配置:")
    print(f"  字体文件: {len(en_fonts)} 个")
    print(f"  推荐字体: {'✅' if en_recommended_font else '❌'}")
    print(f"  背景视频: {'✅' if en_bg_video and os.path.exists(en_bg_video) else '❌'}")
    
    print(f"\n中文配置:")
    print(f"  字体文件: {len(zh_fonts)} 个")
    print(f"  推荐字体: {'✅' if zh_recommended_font else '❌'}")
    print(f"  背景视频: {'✅' if zh_bg_video and os.path.exists(zh_bg_video) else '❌'}")
    
    # 建议
    print(f"\n💡 建议:")
    
    if not en_fonts:
        print("  - 请在 font/en/ 目录添加英文字体文件")
    
    if not zh_fonts:
        print("  - 请在 font/zh/ 目录添加中文字体文件")
    
    if not (en_bg_video and os.path.exists(en_bg_video)):
        print("  - 请确保 assets/plate_upscaled.mp4 文件存在")
    
    if not os.path.exists(en_input_dirs.get('thumbnails_large', '')):
        print("  - 请先运行 upscale_book_thumbnails.py 生成超分封面图片")
    
    print(f"\n✅ 配置测试完成！")


if __name__ == "__main__":
    main() 