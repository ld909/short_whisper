#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍发布Excel生成脚本
读取 merge_book_audio.py 输出的合并音频文件，生成发布管理Excel表格
支持中文和英文书籍，支持断点续传功能，只添加新的UUID，不修改已存在的记录

📚 功能说明:
- 支持中文和英文书籍处理（通过 --language 参数选择）
- 支持多个发布平台（通过 --platform 参数选择）
- 扫描对应语言的合并后书籍音频文件目录
- 从文件名中提取UUID
- 生成包含UUID、发布状态、发布时间的Excel表格
- 支持append only模式，重复运行只添加新记录
- 自动排除Mac系统产生的点文件

🌍 语言支持:
- 英文 (en): /mnt/dhl/audio/books/en/mp3/*.mp3 → excel/book-en.xlsx
- 中文 (zh): /mnt/dhl/audio/books/zh/mp3/*.mp3 → excel/book-zh.xlsx

📱 平台支持:
- YouTube (youtube): 默认平台
  - 英文: excel/book-en.xlsx
  - 中文: excel/book-zh.xlsx
- 小宇宙播客 (xiaoyuzhou): 中文播客平台
  - 中文: excel/book-zh-xiaoyuzhou.xlsx

📥 输入信息:
- Ubuntu: /mnt/dhl/audio/books/{语言}/mp3/*.mp3 (merge_book_audio.py的输出)
- macOS Intel: /Volumes/dhl/audio/books/{语言}/mp3/*.mp3 (merge_book_audio.py的输出)
- macOS Apple Silicon: /Users/donghaoliu/Documents/audio/books/{语言}/mp3/*.mp3 (merge_book_audio.py的输出)

📤 输出信息:
- YouTube平台:
  - 英文Excel文件: excel/book-en.xlsx
  - 中文Excel文件: excel/book-zh.xlsx
- 小宇宙播客平台:
  - 中文Excel文件: excel/book-zh-xiaoyuzhou.xlsx
- 列结构: UUID | 是否发布 | 发布时间

🔄 处理规则:
1. 支持在 Ubuntu 和 macOS 系统上运行
2. 自动排除以点开头的Mac系统文件
3. 支持断点续传，不修改已存在的UUID记录
4. 新UUID默认设置：是否发布=0，发布时间=空
5. 根据语言参数和平台参数自动选择对应的音频目录和Excel文件名
6. 自动检测系统类型并使用对应的路径配置

💡 使用示例:
# 生成/更新英语书籍发布Excel表格（YouTube）
python generate_book_publish_excel.py

# 生成中文书籍发布Excel表格（YouTube）
python generate_book_publish_excel.py --language zh

# 生成中文小宇宙播客发布Excel表格
python generate_book_publish_excel.py --language zh --platform xiaoyuzhou

# 预览模式
python generate_book_publish_excel.py --language zh --platform xiaoyuzhou --preview

# 强制重新生成
python generate_book_publish_excel.py --language zh --platform xiaoyuzhou --force-regenerate
"""

import os
import glob
import argparse
import platform
import pandas as pd
from datetime import datetime
from pathlib import Path

# ============ 配置参数 ============
# Excel输出目录（统一存放所有语种的Excel文件）
DEFAULT_EXCEL_DIR = "excel"

# 默认Excel文件名（英文）
DEFAULT_EXCEL_FILENAME = "book-en.xlsx"

# 最小音频文件大小（字节）
MIN_AUDIO_SIZE = 10240
# ===================================


def check_supported_system():
    """
    检查是否为支持的系统（Ubuntu 或 macOS）

    Returns:
        bool: 是否为支持的系统
    """
    system = platform.system()

    if system == "Darwin":  # macOS
        return True
    elif system == "Linux":
        try:
            # 检查是否为Ubuntu
            with open("/etc/os-release", "r") as f:
                content = f.read()
                if "Ubuntu" in content or "ubuntu" in content:
                    return True
        except:
            pass

    return False


def get_default_audio_dirs():
    """
    根据系统类型获取默认音频目录配置

    Returns:
        dict: 包含语言代码和对应音频目录路径的字典
    """
    system = platform.system()

    if system == "Darwin":  # macOS
        # 检测芯片类型
        machine = platform.machine()
        if machine == "x86_64":  # Intel Mac
            base_path = "/Volumes/dhl/audio"
        else:  # Apple Silicon (arm64)
            base_path = "/Users/donghaoliu/Documents/audio"
    else:  # Ubuntu/Linux
        base_path = "/mnt/dhl/audio"

    return {
        "en": f"{base_path}/books/en/mp3",
        "zh": f"{base_path}/books/zh/mp3",
    }


def is_valid_audio_file(file_path, min_size_bytes=MIN_AUDIO_SIZE):
    """
    检查音频文件是否有效

    Args:
        file_path (str): 音频文件路径
        min_size_bytes (int): 最小文件大小（字节）

    Returns:
        bool: 文件是否有效
    """
    if not os.path.exists(file_path):
        return False

    try:
        file_size = os.path.getsize(file_path)
        if file_size < min_size_bytes:
            print(
                f"⚠️  音频文件过小，可能损坏: {os.path.basename(file_path)} ({file_size} 字节)"
            )
            return False
        return True
    except Exception as e:
        print(f"⚠️  检查音频文件时出错: {file_path}, 错误: {e}")
        return False


def is_valid_uuid(uuid_str):
    """
    检查字符串是否为有效的UUID格式

    Args:
        uuid_str (str): 待检查的字符串

    Returns:
        bool: 是否为有效UUID
    """
    if not uuid_str or not isinstance(uuid_str, str):
        return False

    # UUID格式：36字符，包含4个连字符，格式为 8-4-4-4-12
    if len(uuid_str) != 36 or uuid_str.count("-") != 4:
        return False

    # 检查连字符位置
    parts = uuid_str.split("-")
    if len(parts) != 5:
        return False

    # 检查各部分长度
    expected_lengths = [8, 4, 4, 4, 12]
    for i, part in enumerate(parts):
        if len(part) != expected_lengths[i]:
            return False

        # 检查是否为十六进制字符
        try:
            int(part, 16)
        except ValueError:
            return False

    return True


def get_audio_files(audio_dir):
    """
    获取音频目录中的所有有效MP3文件
    排除Mac生成的以点开头的meta文件

    Args:
        audio_dir (str): 音频文件目录

    Returns:
        list: 有效音频文件路径列表
    """
    if not os.path.exists(audio_dir):
        print(f"❌ 音频目录不存在: {audio_dir}")
        return []

    # 获取所有MP3文件
    mp3_pattern = os.path.join(audio_dir, "*.mp3")
    all_mp3_files = glob.glob(mp3_pattern)

    # 过滤掉以点开头的文件和无效文件
    valid_files = []
    skipped_files = []
    invalid_files = []

    for file_path in all_mp3_files:
        filename = os.path.basename(file_path)

        # 排除以点开头的Mac系统文件
        if filename.startswith(".") or filename.startswith("._"):
            skipped_files.append(filename)
            continue

        # 检查文件有效性
        if not is_valid_audio_file(file_path):
            invalid_files.append(filename)
            continue

        valid_files.append(file_path)

    if skipped_files:
        print(
            f"🚫 跳过 {len(skipped_files)} 个Mac系统文件: {', '.join(skipped_files[:5])}"
            + (f" 等..." if len(skipped_files) > 5 else "")
        )

    if invalid_files:
        print(
            f"⚠️  跳过 {len(invalid_files)} 个无效音频文件: {', '.join(invalid_files[:3])}"
            + (f" 等..." if len(invalid_files) > 3 else "")
        )

    print(f"📊 在音频目录找到 {len(valid_files)} 个有效的MP3文件")
    return valid_files


def extract_uuid_from_filename(file_path):
    """
    从文件路径中提取UUID

    Args:
        file_path (str): 文件路径

    Returns:
        str or None: 提取的UUID，如果无效则返回None
    """
    filename = os.path.basename(file_path)

    # 移除文件扩展名
    uuid_str = os.path.splitext(filename)[0]

    # 验证UUID格式
    if is_valid_uuid(uuid_str):
        return uuid_str
    else:
        print(f"⚠️  文件名包含无效UUID: {filename}")
        return None


def load_existing_excel(excel_path):
    """
    加载现有的Excel文件

    Args:
        excel_path (str): Excel文件路径

    Returns:
        pd.DataFrame: 现有数据，如果文件不存在则返回空DataFrame
    """
    if not os.path.exists(excel_path):
        print(f"📝 Excel文件不存在，将创建新文件: {excel_path}")
        return pd.DataFrame(columns=["UUID", "是否发布", "发布时间"])

    try:
        df = pd.read_excel(excel_path)

        # 确保列名正确
        if "UUID" not in df.columns:
            print(f"⚠️  Excel文件缺少UUID列，将重新创建")
            return pd.DataFrame(columns=["UUID", "是否发布", "发布时间"])

        # 添加缺失的列
        if "是否发布" not in df.columns:
            df["是否发布"] = 0
        if "发布时间" not in df.columns:
            df["发布时间"] = ""

        print(f"📊 加载现有Excel文件: {len(df)} 条记录")
        return df

    except Exception as e:
        print(f"⚠️  读取Excel文件时出错: {e}")
        print(f"📝 将创建新的Excel文件")
        return pd.DataFrame(columns=["UUID", "是否发布", "发布时间"])


def create_book_publish_excel(
    audio_dir, excel_dir, excel_filename, preview_mode=False, force_regenerate=False
):
    """
    创建或更新书籍发布Excel表格

    Args:
        audio_dir (str): 音频文件目录
        excel_dir (str): Excel输出目录
        excel_filename (str): Excel文件名
        preview_mode (bool): 是否为预览模式
        force_regenerate (bool): 是否强制重新生成

    Returns:
        dict: 处理结果
    """
    print(f"\n=== 📊 书籍发布Excel生成器 ===")
    print(f"📁 音频目录: {audio_dir}")

    # 如果excel_dir是相对路径，则相对于脚本所在目录
    if not os.path.isabs(excel_dir):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        excel_dir = os.path.join(script_dir, excel_dir)

    excel_path = os.path.join(excel_dir, excel_filename)
    print(f"📁 Excel文件: {excel_path}")

    # 获取所有有效的音频文件
    audio_files = get_audio_files(audio_dir)

    if not audio_files:
        print(f"❌ 未找到任何有效的音频文件")
        return {
            "status": "failed",
            "reason": "no_audio_files",
            "total_files": 0,
            "new_records": 0,
        }

    # 从文件名中提取UUID
    print(f"\n🔍 从文件名中提取UUID...")
    valid_uuids = []
    invalid_files = []

    for audio_file in audio_files:
        uuid = extract_uuid_from_filename(audio_file)
        if uuid:
            valid_uuids.append(uuid)
        else:
            invalid_files.append(os.path.basename(audio_file))

    if invalid_files:
        print(
            f"⚠️  跳过 {len(invalid_files)} 个无效UUID文件: {', '.join(invalid_files[:3])}"
            + (f" 等..." if len(invalid_files) > 3 else "")
        )

    if not valid_uuids:
        print(f"❌ 未找到任何有效的UUID")
        return {
            "status": "failed",
            "reason": "no_valid_uuids",
            "total_files": len(audio_files),
            "new_records": 0,
        }

    print(f"✅ 提取到 {len(valid_uuids)} 个有效UUID")

    # 加载现有Excel数据
    if force_regenerate:
        print(f"🔄 强制重新生成模式，忽略现有数据")
        existing_df = pd.DataFrame(columns=["UUID", "是否发布", "发布时间"])
    else:
        existing_df = load_existing_excel(excel_path)

    # 找出新的UUID
    existing_uuids = (
        set(existing_df["UUID"].tolist()) if not existing_df.empty else set()
    )
    new_uuids = [uuid for uuid in valid_uuids if uuid not in existing_uuids]

    if not new_uuids and not force_regenerate:
        print(f"✅ 所有UUID都已存在于Excel中，无需添加新记录")
        return {
            "status": "success",
            "reason": "no_new_records",
            "total_files": len(audio_files),
            "existing_records": len(existing_uuids),
            "new_records": 0,
            "excel_path": excel_path,
        }

    print(f"📊 统计信息:")
    print(f"  - 音频文件总数: {len(audio_files)}")
    print(f"  - 有效UUID数: {len(valid_uuids)}")
    print(f"  - 现有记录数: {len(existing_uuids)}")
    print(f"  - 新增记录数: {len(new_uuids)}")

    # 预览模式
    if preview_mode:
        print(f"\n📋 预览模式 - 将要添加的新UUID:")
        if new_uuids:
            show_count = min(10, len(new_uuids))
            for i, uuid in enumerate(new_uuids[:show_count]):
                print(f"  {i+1:3d}. {uuid}")

            if len(new_uuids) > show_count:
                print(f"  ... (还有 {len(new_uuids) - show_count} 个)")
        else:
            print(f"  (无新UUID需要添加)")

        return {
            "status": "preview",
            "total_files": len(audio_files),
            "existing_records": len(existing_uuids),
            "new_records": len(new_uuids),
            "excel_path": excel_path,
        }

    # 创建新记录的DataFrame
    if new_uuids:
        new_records = []
        for uuid in new_uuids:
            new_records.append(
                {
                    "UUID": uuid,
                    "是否发布": 0,  # 默认未发布
                    "发布时间": "",  # 默认空字符串
                }
            )

        new_df = pd.DataFrame(new_records)
        print(f"📝 创建 {len(new_records)} 条新记录")
    else:
        new_df = pd.DataFrame(columns=["UUID", "是否发布", "发布时间"])

    # 合并数据
    if force_regenerate:
        # 强制重新生成：只包含当前找到的UUID
        all_current_records = []
        for uuid in valid_uuids:
            # 如果在现有数据中找到，保留原有数据
            existing_record = existing_df[existing_df["UUID"] == uuid]
            if not existing_record.empty:
                all_current_records.append(existing_record.iloc[0].to_dict())
            else:
                all_current_records.append(
                    {"UUID": uuid, "是否发布": 0, "发布时间": ""}
                )

        final_df = pd.DataFrame(all_current_records)
        print(f"🔄 重新生成Excel，包含 {len(final_df)} 条记录")
    else:
        # Append模式：保留所有现有记录，添加新记录
        if not existing_df.empty and not new_df.empty:
            final_df = pd.concat([existing_df, new_df], ignore_index=True)
        elif not existing_df.empty:
            final_df = existing_df.copy()
        elif not new_df.empty:
            final_df = new_df.copy()
        else:
            final_df = pd.DataFrame(columns=["UUID", "是否发布", "发布时间"])

        print(f"📊 最终Excel包含 {len(final_df)} 条记录")

    # 按UUID排序
    final_df = final_df.sort_values("UUID").reset_index(drop=True)

    # 确保输出目录存在
    os.makedirs(excel_dir, exist_ok=True)

    # 保存Excel文件
    try:
        final_df.to_excel(excel_path, index=False, engine="openpyxl")
        print(f"✅ Excel文件保存成功: {excel_path}")

        # 验证文件
        if os.path.exists(excel_path):
            file_size = os.path.getsize(excel_path)
            print(f"📊 文件大小: {file_size:,} 字节")

        return {
            "status": "success",
            "total_files": len(audio_files),
            "existing_records": len(existing_uuids),
            "new_records": len(new_uuids),
            "total_records": len(final_df),
            "excel_path": excel_path,
        }

    except Exception as e:
        print(f"❌ 保存Excel文件时出错: {e}")
        return {
            "status": "failed",
            "reason": "save_failed",
            "error": str(e),
            "total_files": len(audio_files),
            "new_records": len(new_uuids),
        }


def main():
    """主函数"""
    # 首先检查是否为支持的系统
    if not check_supported_system():
        system_name = platform.system()
        print(f"❌ 此脚本只能在 Ubuntu 或 macOS 系统上运行！")
        print(f"🖥️  当前系统: {system_name}")
        exit(1)

    system_name = platform.system()
    if system_name == "Darwin":
        machine = platform.machine()
        chip_type = "Intel" if machine == "x86_64" else "Apple Silicon"
        print(f"✅ macOS 系统检测通过 ({chip_type})")
    else:
        print("✅ Ubuntu 系统检测通过")

    parser = argparse.ArgumentParser(
        description="书籍发布Excel生成器 - 读取合并音频文件生成发布管理表格（支持断点续传）",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  # YouTube平台（默认）
  python generate_book_publish_excel.py                           # 生成英语书籍Excel表格
  python generate_book_publish_excel.py --language zh             # 生成中文书籍Excel表格  
  
  # 小宇宙播客平台
  python generate_book_publish_excel.py --language zh --platform xiaoyuzhou  # 生成中文小宇宙播客Excel表格
  
  # 其他模式
  python generate_book_publish_excel.py --language zh --platform xiaoyuzhou --preview   # 预览模式
  python generate_book_publish_excel.py --language zh --platform xiaoyuzhou --force-regenerate  # 强制重新生成
  
平台说明:
  • YouTube (youtube): 支持中英文，生成book-en.xlsx/book-zh.xlsx
  • 小宇宙播客 (xiaoyuzhou): 仅支持中文，生成book-zh-xiaoyuzhou.xlsx
  
文件对应关系:
  • book-en.xlsx → upload_books_to_youtube.py (英文)
  • book-zh.xlsx → upload_books_to_youtube.py (中文)  
  • book-zh-xiaoyuzhou.xlsx → upload_books_to_xiaoyuzhou.py (中文小宇宙)
        """,
    )
    # 获取默认音频目录配置
    default_audio_dirs = get_default_audio_dirs()

    parser.add_argument(
        "--audio-dir",
        default=default_audio_dirs["en"],
        help=f"音频文件目录路径 (默认: {default_audio_dirs['en']})",
    )
    parser.add_argument(
        "--excel-dir",
        default=DEFAULT_EXCEL_DIR,
        help=f"Excel输出目录路径 (默认: {DEFAULT_EXCEL_DIR})",
    )
    parser.add_argument(
        "--excel-filename",
        default=DEFAULT_EXCEL_FILENAME,
        help=f"Excel文件名 (默认: {DEFAULT_EXCEL_FILENAME})",
    )
    parser.add_argument(
        "--language",
        "-l",
        default="en",
        help="语言代码，用于生成文件名 (默认: en，将生成book-en.xlsx)",
    )
    parser.add_argument(
        "--platform",
        "-p",
        default="youtube",
        choices=["youtube", "xiaoyuzhou"],
        help="平台代码，用于生成文件名 (默认: youtube，将生成book-en.xlsx和book-zh.xlsx；xiaoyuzhou仅支持中文)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="预览模式，只显示会添加哪些新记录，不实际处理",
    )
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="强制重新生成Excel文件，但保留现有记录的发布状态和时间",
    )

    args = parser.parse_args()

    # 验证平台和语言的组合
    if args.platform == "xiaoyuzhou" and args.language != "zh":
        print(f"❌ 小宇宙播客平台仅支持中文 (zh)，当前语言代码: {args.language}")
        print(
            f"💡 请使用: python generate_book_publish_excel.py --language zh --platform xiaoyuzhou"
        )
        exit(1)

    # 如果用户没有指定自定义音频目录，根据语言代码选择默认目录
    if (
        args.audio_dir == default_audio_dirs["en"]
        and args.language in default_audio_dirs
    ):
        audio_dir = default_audio_dirs[args.language]
    else:
        audio_dir = args.audio_dir

    # 如果用户没有指定自定义文件名，根据语言代码和平台生成文件名
    if args.excel_filename == DEFAULT_EXCEL_FILENAME:
        if args.platform == "xiaoyuzhou":
            excel_filename = f"book-{args.language}-xiaoyuzhou.xlsx"
        elif args.language != "en":
            excel_filename = f"book-{args.language}.xlsx"
        else:
            excel_filename = DEFAULT_EXCEL_FILENAME
    else:
        excel_filename = args.excel_filename

    print(f"\n📊 书籍发布Excel生成器")
    print(f"🌐 语言代码: {args.language}")
    print(f"📱 发布平台: {args.platform}")
    print(f"📁 音频目录: {audio_dir}")
    print(f"📁 Excel目录: {args.excel_dir}")
    print(f"📄 Excel文件: {excel_filename}")
    print(f"🚫 自动排除Mac系统文件 (.DS_Store等)")

    if args.platform == "xiaoyuzhou":
        print(f"🎙️ 小宇宙播客Excel配置:")
        print(f"   - 目标脚本: upload_books_to_xiaoyuzhou.py")
        print(f"   - 平台地址: https://podcaster.xiaoyuzhoufm.com/")
        print(f"   - 列结构: UUID | 是否发布 | 发布时间")
    else:
        print(f"📺 YouTube配置:")
        print(f"   - 目标脚本: upload_books_to_youtube.py")
        print(f"   - 平台地址: https://studio.youtube.com/")
        print(f"   - 列结构: UUID | 是否发布 | 发布时间")

    if args.force_regenerate:
        print(f"🔄 强制重新生成模式")
    else:
        print(f"⚡ Append Only模式: 只添加新记录，保留现有记录")

    if args.preview:
        print(f"👁️  预览模式：只显示将要添加的新记录")

    # 检查必要的Python包
    try:
        import pandas as pd
        import openpyxl

        print("✅ 必要的Python包已安装 (pandas, openpyxl)")
    except ImportError as e:
        print(f"❌ 缺少必要的Python包: {e}")
        print("💡 安装命令: pip install pandas openpyxl")
        return

    # 执行主要处理逻辑
    try:
        result = create_book_publish_excel(
            audio_dir,
            args.excel_dir,
            excel_filename,
            args.preview,
            args.force_regenerate,
        )

        # 显示最终结果
        print(f"\n=== 🎉 处理完成 ===")

        status = result["status"]
        if status == "success":
            if result.get("reason") == "no_new_records":
                print(f"✅ 无新记录需要添加")
                print(f"📊 现有记录数: {result['existing_records']}")
            else:
                print(f"✅ Excel文件更新成功")
                print(f"📊 音频文件总数: {result['total_files']}")
                print(f"📊 现有记录数: {result['existing_records']}")
                print(f"📊 新增记录数: {result['new_records']}")
                print(f"📊 总记录数: {result['total_records']}")
            print(f"📄 Excel文件: {result['excel_path']}")

        elif status == "preview":
            print(f"👁️  预览完成")
            print(f"📊 音频文件总数: {result['total_files']}")
            print(f"📊 现有记录数: {result['existing_records']}")
            print(f"📊 待添加记录数: {result['new_records']}")
            print(f"📄 Excel文件: {result['excel_path']}")

        elif status == "failed":
            reason = result.get("reason", "unknown")
            print(f"❌ 处理失败: {reason}")
            if "error" in result:
                print(f"   错误详情: {result['error']}")

    except KeyboardInterrupt:
        print(f"\n⚠️  用户中断了程序执行")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
