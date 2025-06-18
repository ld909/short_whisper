#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多语种Z-Library爬虫测试脚本
演示英文和中文版本的使用
"""

import subprocess
import time


def test_language_crawler(language, pages=2):
    """测试指定语种的爬虫"""
    print(f"\n{'='*50}")
    print(f"🧪 测试 {'中文' if language == 'zh' else '英文'} 爬虫")
    print(f"{'='*50}")

    # 构建命令
    cmd = [
        "python",
        "zlib_crawler.py",
        "--language",
        language,
        "--max-pages",
        str(pages),
    ]

    print(f"📝 执行命令: {' '.join(cmd)}")
    print()

    # 执行命令
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        print("📤 输出:")
        print(result.stdout)

        if result.stderr:
            print("⚠️ 错误信息:")
            print(result.stderr)

        print(f"🏁 退出码: {result.returncode}")

        # 检查生成的文件
        output_file = f"book_url{'_zh' if language == 'zh' else ''}.txt"
        progress_file = f"crawler_progress{'_zh' if language == 'zh' else ''}.json"

        print(f"\n📁 生成的文件:")
        print(f"   - URL文件: {output_file}")
        print(f"   - 进度文件: {progress_file}")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("⏰ 测试超时")
        return False
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 多语种Z-Library爬虫测试")
    print("本测试将演示英文和中文两种语言的爬虫功能")

    # 测试英文爬虫
    print("\n🔸 第一步：测试英文爬虫")
    en_success = test_language_crawler("en", 2)

    time.sleep(2)  # 稍作等待

    # 测试中文爬虫
    print("\n🔸 第二步：测试中文爬虫")
    zh_success = test_language_crawler("zh", 2)

    # 总结测试结果
    print(f"\n{'='*60}")
    print("📊 测试结果总结")
    print(f"{'='*60}")
    print(f"🇺🇸 英文爬虫: {'✅ 成功' if en_success else '❌ 失败'}")
    print(f"🇨🇳 中文爬虫: {'✅ 成功' if zh_success else '❌ 失败'}")

    if en_success and zh_success:
        print("\n🎉 所有测试通过！多语种爬虫工作正常")
    else:
        print("\n⚠️ 部分测试失败，请检查配置和网络连接")

    print("\n💡 使用提示:")
    print("1. 爬取英文书籍: python zlib_crawler.py --language en --max-pages 50")
    print("2. 爬取中文书籍: python zlib_crawler.py --language zh --max-pages 50")
    print("3. 断点续传: 添加 --resume 参数")
    print("4. 交互模式: 直接运行 python zlib_crawler.py")


if __name__ == "__main__":
    main()
