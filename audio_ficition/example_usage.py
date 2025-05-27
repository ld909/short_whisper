#!/usr/bin/env python3
"""
封面提示词生成器使用示例

这个脚本展示了如何使用 generate_cover_prompts.py 的各种功能
"""

import os
import subprocess
import sys


def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"命令: {cmd}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print("输出:")
        print(result.stdout)
        if result.stderr:
            print("错误:")
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"执行命令时出错: {e}")
        return False


def main():
    """主示例函数"""
    print("🎨 封面提示词生成器使用示例")
    print("本脚本展示各种使用方式，请根据需要选择")

    examples = [
        {"cmd": "python generate_cover_prompts.py -h", "desc": "查看帮助信息"},
        {"cmd": "python test_cover_prompts.py", "desc": "运行功能测试"},
        {
            "cmd": "python generate_cover_prompts.py --start 1 --end 1",
            "desc": "生成单个故事的封面提示词（故事1）",
        },
        {
            "cmd": "python generate_cover_prompts.py --start 1 --end 3",
            "desc": "生成前3个故事的封面提示词",
        },
        {
            "cmd": "python generate_cover_prompts.py --start 5",
            "desc": "从故事5开始生成所有后续故事",
        },
        {
            "cmd": "python generate_cover_prompts.py --end 10",
            "desc": "生成故事1到10的封面提示词",
        },
        {"cmd": "python generate_cover_prompts.py", "desc": "生成所有故事的封面提示词"},
        {
            "cmd": "python generate_cover_prompts.py -f",
            "desc": "强制重新生成所有封面提示词",
        },
    ]

    print("\n可用的示例命令:")
    for i, example in enumerate(examples, 1):
        print(f"{i}. {example['desc']}")
        print(f"   命令: {example['cmd']}")

    print("\n" + "=" * 60)

    while True:
        try:
            choice = input("\n请选择要执行的示例 (1-8) 或输入 'q' 退出: ").strip()

            if choice.lower() == "q":
                print("👋 再见!")
                break

            choice_num = int(choice)
            if 1 <= choice_num <= len(examples):
                example = examples[choice_num - 1]
                success = run_command(example["cmd"], example["desc"])

                if success:
                    print("✅ 命令执行成功")
                else:
                    print("❌ 命令执行失败")

                # 如果是生成命令，显示生成结果
                if (
                    "generate_cover_prompts.py" in example["cmd"]
                    and "--" in example["cmd"]
                ):
                    print("\n📁 检查生成的文件:")
                    cover_dir = "/Volumes/dhl/audio/scifi/full_story/cover_prompts"
                    if os.path.exists(cover_dir):
                        files = [f for f in os.listdir(cover_dir) if f.endswith(".txt")]
                        if files:
                            files.sort(key=lambda x: int(x.split(".")[0]))
                            print(f"已生成 {len(files)} 个封面提示词文件:")
                            for f in files[:5]:  # 显示前5个
                                print(f"  - {f}")
                            if len(files) > 5:
                                print(f"  ... 还有 {len(files) - 5} 个文件")
                        else:
                            print("  未找到生成的文件")
                    else:
                        print("  输出目录不存在")

            else:
                print("❌ 无效选择，请输入1-8之间的数字")

        except ValueError:
            print("❌ 请输入有效的数字")
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，再见!")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")


if __name__ == "__main__":
    main()
