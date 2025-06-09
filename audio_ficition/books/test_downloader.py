#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF下载器测试脚本
用于验证book_pdf_downloader.py的主要功能
"""

import os
import sys
import json
from pathlib import Path

# 添加当前目录到路径，以便导入book_pdf_downloader
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from book_pdf_downloader import BookPDFDownloader, get_base_media_path

    print("✅ 成功导入 BookPDFDownloader")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)


def test_paths():
    """测试路径配置"""
    print("\n=== 测试路径配置 ===")

    base_path = get_base_media_path()
    print(f"📁 基础媒体路径: {base_path}")

    downloader = BookPDFDownloader(debug=True)
    print(f"📂 info目录: {downloader.info_dir}")
    print(f"📂 PDF目录: {downloader.pdf_dir}")
    print(f"📄 UUID映射文件: {downloader.uuid_mapping_file}")
    print(f"📄 进度文件: {downloader.download_progress_file}")

    # 检查目录是否存在
    if os.path.exists(downloader.info_dir):
        print(f"✅ info目录存在")
        info_files = [
            f
            for f in os.listdir(downloader.info_dir)
            if f.endswith(".json") and not f.startswith(".")
        ]
        print(f"📚 找到 {len(info_files)} 个书籍信息文件")
    else:
        print(f"❌ info目录不存在: {downloader.info_dir}")

    if os.path.exists(downloader.pdf_dir):
        print(f"✅ PDF目录存在")
        pdf_files = [
            f
            for f in os.listdir(downloader.pdf_dir)
            if f.endswith(".pdf") and not f.startswith(".")
        ]
        print(f"📄 找到 {len(pdf_files)} 个PDF文件")
    else:
        print(f"❌ PDF目录不存在，但会自动创建")


def test_load_data():
    """测试数据加载"""
    print("\n=== 测试数据加载 ===")

    downloader = BookPDFDownloader(debug=True)

    # 测试加载书籍数据
    try:
        book_data = downloader.load_book_data()
        print(f"📚 成功加载 {len(book_data)} 本书籍信息")

        if book_data:
            sample_book = book_data[0]
            print(
                f"📖 示例书籍: {sample_book['title']} (UUID: {sample_book['uuid'][:8]}...)"
            )

    except Exception as e:
        print(f"❌ 加载书籍数据失败: {e}")

    # 测试已存在的PDF
    try:
        existing_pdfs = downloader.get_existing_pdfs()
        print(f"📄 已存在 {len(existing_pdfs)} 个PDF文件")

        if existing_pdfs:
            sample_pdf = list(existing_pdfs)[0]
            print(f"📑 示例PDF: {sample_pdf[:8]}...")

    except Exception as e:
        print(f"❌ 检查已存在PDF失败: {e}")


def test_progress_management():
    """测试进度管理"""
    print("\n=== 测试进度管理 ===")

    downloader = BookPDFDownloader(debug=True)

    # 测试进度文件
    try:
        progress = downloader._load_download_progress()
        print(f"📊 下载进度:")
        print(f"   ✅ 已完成: {len(progress.get('completed', []))} 个")
        print(f"   ❌ 失败: {len(progress.get('failed', []))} 个")
        print(f"   ⏭️ 跳过: {len(progress.get('skipped', []))} 个")

    except Exception as e:
        print(f"❌ 加载进度失败: {e}")


def test_ads_connection():
    """测试AdsPower连接（不实际连接）"""
    print("\n=== 测试AdsPower连接配置 ===")

    downloader = BookPDFDownloader(ads_id="kq316tr", debug=True)
    print(f"🌐 配置的浏览器ID: {downloader.ads_id}")

    # 提示用户检查AdsPower
    print("⚠️  请确保:")
    print("   - AdsPower 已启动")
    print("   - 浏览器ID 'kq316tr' 存在且可用")
    print("   - 本地API已启用 (端口: 50325)")


def create_sample_book_data():
    """创建示例书籍数据用于测试"""
    print("\n=== 创建示例数据 ===")

    downloader = BookPDFDownloader(debug=True)

    # 确保目录存在
    Path(downloader.info_dir).mkdir(parents=True, exist_ok=True)

    # 创建示例书籍信息
    sample_uuid = "test-book-001"
    sample_book = {
        "uuid": sample_uuid,
        "url": "https://example.com/book/1",
        "title": "测试书籍",
        "author": "测试作者",
        "description": "这是一个测试用的书籍信息",
        "publication_year": "2023",
        "cover_url": "",
        "extracted_at": 1234567890,
    }

    info_file = os.path.join(downloader.info_dir, f"{sample_uuid}.json")

    try:
        with open(info_file, "w", encoding="utf-8") as f:
            json.dump(sample_book, f, ensure_ascii=False, indent=2)

        print(f"✅ 创建示例书籍信息: {info_file}")
        print(f"📖 书籍: {sample_book['title']}")

        # 验证加载
        book_data = downloader.load_book_data()
        test_books = [book for book in book_data if book["uuid"] == sample_uuid]
        if test_books:
            print(f"✅ 示例数据加载成功")
        else:
            print(f"❌ 示例数据加载失败")

    except Exception as e:
        print(f"❌ 创建示例数据失败: {e}")


def main():
    """主测试函数"""
    print("🧪 PDF下载器功能测试")
    print("=" * 50)

    try:
        test_paths()
        test_load_data()
        test_progress_management()
        test_ads_connection()

        # 如果没有书籍数据，创建示例数据
        downloader = BookPDFDownloader(debug=True)
        book_data = downloader.load_book_data()
        if not book_data:
            print("\n⚠️  未找到书籍数据，创建示例数据...")
            create_sample_book_data()

        print("\n" + "=" * 50)
        print("✅ 测试完成！")
        print("\n📋 下一步:")
        print("1. 确保AdsPower已启动并配置好浏览器")
        print("2. 运行book_info_scraper.py生成书籍数据")
        print("3. 使用book_pdf_downloader.py开始下载PDF")

    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
