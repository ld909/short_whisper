#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码行数统计脚本
统计指定目录中所有代码文件的行数，排除非代码文件和Mac系统文件
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import argparse

# 定义代码文件扩展名
CODE_EXTENSIONS = {
    # Python
    '.py', '.pyx', '.pyi',
    # JavaScript/TypeScript
    '.js', '.jsx', '.ts', '.tsx', '.mjs',
    # 配置文件
    '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
    # 标记语言
    '.rst',
    # Web
    '.html', '.htm', '.css', '.scss', '.sass', '.less',
    # Shell
    '.sh', '.bash', '.zsh', '.fish',
    # C/C++
    '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx',
    # Java
    '.java', '.kt', '.scala',
    # Go
    '.go',
    # Rust
    '.rs',
    # SQL
    '.sql',
    # R
    '.r', '.R',
    # 其他
    '.xml', '.svg', '.dockerfile', '.gitignore', '.gitattributes',
    # 字幕文件
    '.vtt'
}

# 需要排除的目录
EXCLUDE_DIRS = {
    '.git', '__pycache__', '.vscode', '.idea', 'node_modules', 
    '.pytest_cache', '.mypy_cache', 'venv', 'env', '.env',
    'dist', 'build', '.tox', '.coverage'
}

# 需要排除的文件模式
EXCLUDE_PATTERNS = [
    # Mac 系统文件
    '.DS_Store', '._*', '.Spotlight-V100', '.Trashes',
    # Windows 系统文件
    'Thumbs.db', 'desktop.ini',
    # 临时文件
    '*.tmp', '*.temp', '*.bak', '*.backup',
    # 编译文件
    '*.pyc', '*.pyo', '*.so', '*.dll', '*.exe',
    # 媒体文件
    '*.mp4', '*.mp3', '*.avi', '*.wav', '*.jpg', '*.png', '*.gif',
    '*.jpeg', '*.bmp', '*.tiff', '*.pdf', '*.zip', '*.tar', '*.gz'
]

def should_exclude_file(file_path):
    """检查文件是否应该被排除"""
    file_name = file_path.name
    
    # 排除点开头的文件（Mac 系统文件）
    if file_name.startswith('.') and file_name != '.gitignore' and file_name != '.gitattributes':
        return True
    
    # 检查排除模式
    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith('*'):
            if file_name.endswith(pattern[1:]):
                return True
        elif file_name == pattern:
            return True
    
    return False

def should_exclude_dir(dir_name):
    """检查目录是否应该被排除"""
    return dir_name in EXCLUDE_DIRS or dir_name.startswith('.')

def is_code_file(file_path):
    """判断文件是否为代码文件"""
    return file_path.suffix.lower() in CODE_EXTENSIONS

def count_lines_in_file(file_path):
    """统计文件行数"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return len(f.readlines())
    except Exception as e:
        print(f"警告: 无法读取文件 {file_path}: {e}")
        return 0

def scan_directory(root_path):
    """扫描目录，统计代码文件行数"""
    root_path = Path(root_path)
    
    if not root_path.exists():
        print(f"错误: 目录 {root_path} 不存在")
        return None
    
    stats = {
        'total_lines': 0,
        'total_files': 0,
        'by_extension': defaultdict(lambda: {'files': 0, 'lines': 0}),
        'by_directory': defaultdict(lambda: {'files': 0, 'lines': 0}),
        'file_details': []
    }
    
    print(f"开始扫描目录: {root_path}")
    print("=" * 60)
    
    for root, dirs, files in os.walk(root_path):
        root_path_obj = Path(root)
        
        # 排除特定目录
        dirs[:] = [d for d in dirs if not should_exclude_dir(d)]
        
        for file_name in files:
            file_path = root_path_obj / file_name
            
            # 排除特定文件
            if should_exclude_file(file_path):
                continue
            
            # 只统计代码文件
            if not is_code_file(file_path):
                continue
            
            # 统计行数
            line_count = count_lines_in_file(file_path)
            if line_count == 0:
                continue
            
            # 更新统计信息
            stats['total_lines'] += line_count
            stats['total_files'] += 1
            
            # 按扩展名统计
            ext = file_path.suffix.lower()
            stats['by_extension'][ext]['files'] += 1
            stats['by_extension'][ext]['lines'] += line_count
            
            # 按目录统计
            rel_dir = str(file_path.parent.relative_to(Path(root_path).resolve()))
            stats['by_directory'][rel_dir]['files'] += 1
            stats['by_directory'][rel_dir]['lines'] += line_count
            
            # 记录文件详情
            stats['file_details'].append({
                'path': str(file_path.relative_to(Path(root_path).resolve())),
                'extension': ext,
                'lines': line_count
            })
            
            print(f"处理: {file_path.relative_to(Path(root_path).resolve())} ({line_count} 行)")
    
    return stats

def print_summary(stats):
    """打印统计摘要"""
    if not stats:
        return
    
    print("\n" + "=" * 60)
    print("📊 代码统计摘要")
    print("=" * 60)
    
    print(f"📁 总文件数: {stats['total_files']:,}")
    print(f"📄 总行数: {stats['total_lines']:,}")
    
    if stats['total_files'] > 0:
        avg_lines = stats['total_lines'] / stats['total_files']
        print(f"📊 平均每文件行数: {avg_lines:.1f}")
    
    # 按扩展名统计
    print(f"\n📋 按文件类型统计:")
    print("-" * 40)
    sorted_ext = sorted(stats['by_extension'].items(), 
                       key=lambda x: x[1]['lines'], reverse=True)
    
    for ext, data in sorted_ext:
        percentage = (data['lines'] / stats['total_lines']) * 100
        print(f"{ext:>8} | {data['files']:>4} 文件 | {data['lines']:>8,} 行 | {percentage:>5.1f}%")
    
    # 按目录统计（显示前10个）
    print(f"\n📂 按目录统计 (前10个):")
    print("-" * 50)
    sorted_dirs = sorted(stats['by_directory'].items(), 
                        key=lambda x: x[1]['lines'], reverse=True)
    
    for i, (dir_name, data) in enumerate(sorted_dirs[:10]):
        percentage = (data['lines'] / stats['total_lines']) * 100
        display_dir = dir_name if dir_name != '.' else '根目录'
        print(f"{i+1:>2}. {display_dir:<30} | {data['files']:>4} 文件 | {data['lines']:>8,} 行 | {percentage:>5.1f}%")
    
    # 最大的文件（前10个）
    print(f"\n📄 最大的代码文件 (前10个):")
    print("-" * 60)
    sorted_files = sorted(stats['file_details'], key=lambda x: x['lines'], reverse=True)
    
    for i, file_info in enumerate(sorted_files[:10]):
        percentage = (file_info['lines'] / stats['total_lines']) * 100
        print(f"{i+1:>2}. {file_info['path']:<40} | {file_info['lines']:>6,} 行 | {percentage:>5.1f}%")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='统计目录中代码文件的行数')
    parser.add_argument('directory', nargs='?', default='/home/dhl/Documents/short_whisper',
                       help='要统计的目录路径 (默认: /home/dhl/Documents/short_whisper)')
    parser.add_argument('--detail', '-d', action='store_true',
                       help='显示详细的文件信息')
    parser.add_argument('--export', '-e', type=str,
                       help='导出统计结果到文件 (JSON格式)')
    
    args = parser.parse_args()
    
    # 执行统计
    stats = scan_directory(args.directory)
    
    if stats:
        print_summary(stats)
        
        # 导出到文件
        if args.export:
            import json
            with open(args.export, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            print(f"\n💾 统计结果已导出到: {args.export}")
        
        # 显示详细信息
        if args.detail and stats['file_details']:
            print(f"\n📋 所有代码文件详情:")
            print("-" * 80)
            for file_info in sorted(stats['file_details'], key=lambda x: x['lines'], reverse=True):
                print(f"{file_info['path']:<50} | {file_info['extension']:<6} | {file_info['lines']:>6,} 行")
    else:
        print("❌ 统计失败")
        sys.exit(1)

if __name__ == "__main__":
    main() 