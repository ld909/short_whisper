#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
书籍处理流水线控制器
自动化执行整个书籍处理流水线的所有步骤

📚 功能说明:
这是一个终极控制器脚本，负责按正确顺序执行整个书籍处理流水线：
1. chunk_book_summaries.py - 生成文本块
2. synthesize_book_audio.py - 生成MP3音频片段（仅Ubuntu）
3. merge_book_audio.py - 合并音频（仅Ubuntu）
4. upscale_book_thumbnails.py - 封面图片超分（方法cover）
5. generate_book_clips.py - 生成视频素材
6. generate_youtube_descriptions.py - 生成YouTube描述
7. generate_youtube_hashtags.py - 生成YouTube标签
8. generate_youtube_titles.py - 生成YouTube标题
9. merge_clips_with_audio.py - 生成最终视频

⚠️ 重要说明:
- 音频相关步骤（2、3）仅在Ubuntu系统上运行
- 其他步骤可在macOS和Ubuntu上运行
- 脚本会自动检测系统类型并跳过不兼容的步骤
- 支持单独运行每个步骤或完整流水线
- 支持中文(zh)和英文(en)两种语言主题
- 包含完整的错误处理和进度跟踪

💡 使用示例:
# 运行英文主题完整流水线
python book_processing_controller.py --full-pipeline --lang en

# 运行中文主题完整流水线
python book_processing_controller.py --full-pipeline --lang zh

# 运行指定步骤
python book_processing_controller.py --steps 1,2,3 --lang en

# 强制重新处理
python book_processing_controller.py --full-pipeline --force --lang zh

# 处理指定UUID
python book_processing_controller.py --uuid 12345678-abcd-efgh-ijkl-123456789012 --lang en

# 调试模式
python book_processing_controller.py --full-pipeline --debug --lang zh
"""

import os
import sys
import time
import argparse
import platform
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class BookProcessingController:
    """书籍处理流水线控制器"""

    def __init__(self, debug=False, force=False, target_uuid=None, language="en"):
        self.debug = debug
        self.force = force
        self.target_uuid = target_uuid
        self.language = language
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.system = platform.system()

        # 设置语言相关配置
        self.setup_language_config()

        # 配置正确的媒体路径
        self.audio_base_dir = self._get_audio_base_dir()

        # 定义流水线步骤
        self.pipeline_steps = {
            1: {
                "name": "生成文本块",
                "script": "chunk_book_summaries.py",
                "description": "将书籍总结分割成适当大小的文本块",
                "ubuntu_only": False,
                "args": self._get_chunk_args,
            },
            2: {
                "name": "合成音频片段",
                "script": "synthesize_book_audio.py",
                "description": "使用f5-tts将文本块合成为音频文件",
                "ubuntu_only": True,
                "args": self._get_synthesize_args,
            },
            3: {
                "name": "合并音频文件",
                "script": "merge_book_audio.py",
                "description": "将音频片段合并为完整的书籍音频",
                "ubuntu_only": True,
                "args": self._get_merge_audio_args,
            },
            4: {
                "name": "封面图片超分",
                "script": "upscale_book_thumbnails.py",
                "description": "对书籍封面图片进行超分辨率处理",
                "ubuntu_only": False,
                "args": self._get_upscale_args,
            },
            5: {
                "name": "生成视频素材",
                "script": "generate_book_clips.py",
                "description": "生成1080p书籍宣传视频素材",
                "ubuntu_only": False,
                "args": self._get_clips_args,
            },
            6: {
                "name": "生成YouTube描述",
                "script": "generate_youtube_descriptions.py",
                "description": "基于书籍总结生成YouTube视频描述",
                "ubuntu_only": False,
                "args": self._get_description_args,
            },
            7: {
                "name": "生成YouTube标签",
                "script": "generate_youtube_hashtags.py",
                "description": "基于视频描述生成SEO优化的hashtag",
                "ubuntu_only": False,
                "args": self._get_hashtag_args,
            },
            8: {
                "name": "生成YouTube标题",
                "script": "generate_youtube_titles.py",
                "description": "基于书籍信息生成YouTube视频标题",
                "ubuntu_only": False,
                "args": self._get_title_args,
            },
            9: {
                "name": "合并最终视频",
                "script": "merge_clips_with_audio.py",
                "description": "将视频素材与音频合并，生成最终视频",
                "ubuntu_only": False,
                "args": self._get_merge_video_args,
            },
        }

        print(f"🖥️  系统类型: {self.system}")
        print(f"🌍 语言主题: {self.language_name}")
        print(f"📁 脚本目录: {self.script_dir}")
        print(f"🎵 音频路径: {self.audio_base_dir}")
        print(f"📚 书籍路径: {self.books_base_path}")
        if self.target_uuid:
            print(f"🎯 目标UUID: {self.target_uuid}")

    def setup_language_config(self):
        """根据语种设置配置"""
        if self.language == "zh":
            # 中文配置
            self.language_name = "中文"
        else:
            # 英文配置（默认）
            self.language_name = "English"

        logger.info(f"🌍 语言主题: {self.language_name}")

    def _get_audio_base_dir(self) -> str:
        """获取音频基础目录路径"""
        if self.system == "Linux":  # Ubuntu
            return "/media/dhl/audio"
        elif self.system == "Darwin":  # macOS
            # 检测Mac芯片类型
            machine = platform.machine()
            if machine == "x86_64":  # Intel Mac
                return "/Volumes/dhl/audio"
            else:  # Apple Silicon
                return "/Users/donghaoliu/Documents/audio"
        else:
            # 默认使用当前目录的audio子目录
            return os.path.join(os.path.expanduser("~"), "Documents", "audio")

    @property
    def books_base_path(self) -> str:
        """获取书籍基础路径"""
        return os.path.join(self.audio_base_dir, "books", self.language)

    def _get_chunk_args(self) -> List[str]:
        """获取chunk_book_summaries.py的参数"""
        args = ["--lang", self.language]
        if self.force:
            args.append("--no-resume")
        if self.debug:
            args.append("--preview")
        return args

    def _get_synthesize_args(self) -> List[str]:
        """获取synthesize_book_audio.py的参数"""
        args = ["--lang", self.language]
        if self.target_uuid:
            args.extend(["--uuid", self.target_uuid])
        if self.force:
            args.append("--force-regenerate")
        if self.debug:
            args.append("--preview")
        return args

    def _get_merge_audio_args(self) -> List[str]:
        """获取merge_book_audio.py的参数"""
        args = ["--lang", self.language]
        if self.target_uuid:
            args.extend(["--uuid", self.target_uuid])
        if self.force:
            args.append("--force-regenerate")
        if self.debug:
            args.append("--preview")
        return args

    def _get_upscale_args(self) -> List[str]:
        """获取upscale_book_thumbnails.py的参数"""
        args = ["--lang", self.language]
        if self.force:
            args.append("--force")
        if self.debug:
            args.append("--debug")
        return args

    def _get_clips_args(self) -> List[str]:
        """获取generate_book_clips.py的参数"""
        args = ["--lang", self.language]

        # 添加固定的视频生成参数
        args.extend(
            [
                "--no-preserve-aspect",
                "--video-width",
                "0.8",
                "--font-size",
                "126",
                "--video-center",
                "--summary-font-size",
                "40",
                "--summary-top-margin",
                "620",
                "--summary-right-margin",
                "620",
                "--icon-size",
                "32",
                "--icon-vertical-offset",
                "-5",
            ]
        )

        # 添加可选参数
        if self.force:
            args.append("--force")
        if self.debug:
            args.append("--debug")
        return args

    def _get_description_args(self) -> List[str]:
        """获取generate_youtube_descriptions.py的参数"""
        args = ["--lang", self.language]
        if self.target_uuid:
            args.extend(["--uuid", self.target_uuid])
        if self.force:
            args.append("--force")
        if self.debug:
            args.append("--debug")
        return args

    def _get_hashtag_args(self) -> List[str]:
        """获取generate_youtube_hashtags.py的参数"""
        args = ["--lang", self.language]
        if self.target_uuid:
            args.extend(["--uuid", self.target_uuid])
        if self.force:
            args.append("--force")
        return args

    def _get_title_args(self) -> List[str]:
        """获取generate_youtube_titles.py的参数"""
        args = ["--lang", self.language]
        if self.target_uuid:
            args.extend(["--uuid", self.target_uuid])
        if self.force:
            args.append("--force")
        if self.debug:
            args.append("--debug")
        return args

    def _get_merge_video_args(self) -> List[str]:
        """获取merge_clips_with_audio.py的参数"""
        args = ["--lang", self.language]
        if self.target_uuid:
            args.extend(["--uuid", self.target_uuid])
        if self.force:
            args.append("--force")
        if self.debug:
            args.append("--debug")
        return args

    def check_system_compatibility(self, step_number: int) -> bool:
        """检查步骤是否与当前系统兼容"""
        step = self.pipeline_steps[step_number]
        if step["ubuntu_only"] and self.system != "Linux":
            print(
                f"⚠️  步骤 {step_number} ({step['name']}) 仅支持Ubuntu系统，当前系统: {self.system}"
            )
            return False
        return True

    def execute_step(self, step_number: int) -> bool:
        """执行单个流水线步骤"""
        if step_number not in self.pipeline_steps:
            print(f"❌ 无效的步骤编号: {step_number}")
            return False

        step = self.pipeline_steps[step_number]

        # 检查系统兼容性
        if not self.check_system_compatibility(step_number):
            return False

        print(f"\n{'='*60}")
        print(f"🚀 执行步骤 {step_number}: {step['name']}")
        print(f"📄 脚本: {step['script']}")
        print(f"📝 描述: {step['description']}")
        print(f"🌍 语言: {self.language_name}")
        print(f"📁 音频路径: {self.audio_base_dir}")
        print(f"📚 书籍路径: {self.books_base_path}")
        print(f"{'='*60}")

        script_path = os.path.join(self.script_dir, step["script"])

        if not os.path.exists(script_path):
            print(f"❌ 脚本文件不存在: {script_path}")
            return False

        # 构建命令
        cmd = ["python", script_path]
        args = step["args"]()
        cmd.extend(args)

        print(f"🔄 执行命令: {' '.join(cmd)}")

        start_time = datetime.now()

        try:
            # 设置环境变量
            env = os.environ.copy()
            env["AUDIO_BASE_DIR"] = self.audio_base_dir
            env["BOOK_LANGUAGE"] = self.language

            # 执行脚本
            result = subprocess.run(
                cmd,
                cwd=self.script_dir,
                capture_output=False,  # 让输出直接显示在终端
                text=True,
                check=False,
                env=env,  # 传递环境变量
            )

            end_time = datetime.now()
            duration = end_time - start_time

            if result.returncode == 0:
                print(f"✅ 步骤 {step_number} 执行成功! 耗时: {duration}")
                return True
            else:
                print(f"❌ 步骤 {step_number} 执行失败! 退出代码: {result.returncode}")
                return False

        except Exception as e:
            end_time = datetime.now()
            duration = end_time - start_time
            print(f"❌ 步骤 {step_number} 执行异常: {e}, 耗时: {duration}")
            return False

    def run_pipeline(self, steps: Optional[List[int]] = None) -> bool:
        """运行流水线"""
        if steps is None:
            steps = list(self.pipeline_steps.keys())

        print(f"\n🔥 开始书籍处理流水线")
        print(f"📋 计划执行步骤: {steps}")
        print(f"🖥️  系统: {self.system}")
        print(f"🌍 语言主题: {self.language_name}")
        print(f"📚 书籍路径: {self.books_base_path}")
        print(f"🔄 强制重新处理: {'是' if self.force else '否'}")
        print(f"🐛 调试模式: {'是' if self.debug else '否'}")

        total_start_time = datetime.now()
        success_count = 0
        skipped_count = 0
        failed_count = 0

        for step_number in steps:
            if step_number not in self.pipeline_steps:
                print(f"⚠️  跳过无效步骤编号: {step_number}")
                continue

            step = self.pipeline_steps[step_number]

            # 检查系统兼容性
            if step["ubuntu_only"] and self.system != "Linux":
                print(
                    f"\n⏭️  跳过步骤 {step_number} ({step['name']}) - 仅支持Ubuntu系统"
                )
                skipped_count += 1
                continue

            # 执行步骤
            success = self.execute_step(step_number)
            if success:
                success_count += 1
            else:
                failed_count += 1
                print(f"\n💥 步骤 {step_number} 失败，是否继续？")
                user_input = input("继续执行下一步？ (y/n): ").strip().lower()
                if user_input not in ["y", "yes", "是"]:
                    print("❌ 用户中止流水线执行")
                    break

        total_end_time = datetime.now()
        total_duration = total_end_time - total_start_time

        # 输出最终统计
        print(f"\n{'='*60}")
        print(f"📊 流水线执行完成统计")
        print(f"{'='*60}")
        print(f"⏱️  总耗时: {total_duration}")
        print(f"🌍 语言主题: {self.language_name}")
        print(f"✅ 成功执行: {success_count} 个步骤")
        print(f"⏭️  跳过执行: {skipped_count} 个步骤")
        print(f"❌ 执行失败: {failed_count} 个步骤")
        print(
            f"📈 成功率: {success_count/(success_count+failed_count)*100:.1f}%"
            if (success_count + failed_count) > 0
            else "N/A"
        )

        if failed_count == 0:
            print(f"\n🎉 流水线执行完美成功!")
            return True
        else:
            print(f"\n⚠️  流水线执行部分失败，请检查错误信息")
            return False

    def show_pipeline_info(self):
        """显示流水线信息"""
        print(f"\n📋 书籍处理流水线步骤")
        print(f"🌍 语言主题: {self.language_name}")
        print(f"📚 书籍路径: {self.books_base_path}")
        print(f"{'='*80}")

        for step_num, step in self.pipeline_steps.items():
            ubuntu_mark = " (仅Ubuntu)" if step["ubuntu_only"] else ""
            compat_mark = "✅" if self.check_system_compatibility(step_num) else "❌"

            print(f"{compat_mark} 步骤 {step_num}: {step['name']}{ubuntu_mark}")
            print(f"   📄 脚本: {step['script']}")
            print(f"   📝 描述: {step['description']}")
            print()


def parse_step_list(step_str: str) -> List[int]:
    """解析步骤列表字符串"""
    if not step_str:
        return []

    steps = []
    for part in step_str.split(","):
        part = part.strip()
        if "-" in part:
            # 范围格式: 1-5
            try:
                start, end = map(int, part.split("-"))
                steps.extend(range(start, end + 1))
            except ValueError:
                print(f"⚠️  无效的步骤范围格式: {part}")
        else:
            # 单个步骤
            try:
                steps.append(int(part))
            except ValueError:
                print(f"⚠️  无效的步骤编号: {part}")

    return sorted(list(set(steps)))  # 去重并排序


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="📚 书籍处理流水线控制器",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python book_processing_controller.py --full-pipeline --lang en               # 运行英文主题完整流水线
  python book_processing_controller.py --full-pipeline --lang zh               # 运行中文主题完整流水线
  python book_processing_controller.py --steps 1,2,3 --lang en                 # 运行指定步骤
  python book_processing_controller.py --steps 1-5 --lang zh                   # 运行步骤范围
  python book_processing_controller.py --info --lang en                        # 显示流水线信息
  python book_processing_controller.py --uuid xxx --full-pipeline --lang zh    # 处理指定UUID

注意:
- 音频相关步骤(2,3)仅在Ubuntu系统运行
- 使用 --force 强制重新处理所有文件
- 使用 --debug 启用调试模式查看详细信息
- 支持中文(zh)和英文(en)两种语言主题
        """,
    )

    # 执行模式参数组
    execution_group = parser.add_mutually_exclusive_group(required=True)
    execution_group.add_argument(
        "--full-pipeline",
        action="store_true",
        help="运行完整的流水线（步骤1-9）",
    )
    execution_group.add_argument(
        "--steps",
        type=str,
        help="运行指定的步骤（例如: 1,3,5 或 1-5）",
    )
    execution_group.add_argument(
        "--info",
        action="store_true",
        help="显示流水线信息并退出",
    )

    # 语言参数
    parser.add_argument(
        "--lang",
        "-l",
        choices=["en", "zh"],
        default="en",
        help="语言主题: en(英文) 或 zh(中文) [默认: en]",
    )

    # 其他参数
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新处理，跳过已存在的文件",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式",
    )
    parser.add_argument(
        "--uuid",
        type=str,
        help="处理指定UUID的书籍",
    )

    args = parser.parse_args()

    print("📚 书籍处理流水线控制器")
    print("=" * 50)

    # 创建控制器实例
    controller = BookProcessingController(
        debug=args.debug,
        force=args.force,
        target_uuid=args.uuid,
        language=args.lang,
    )

    # 显示信息模式
    if args.info:
        controller.show_pipeline_info()
        return

    # 确定要执行的步骤
    if args.full_pipeline:
        steps = list(range(1, 10))  # 1-9
        print(f"🔥 运行完整流水线（步骤 1-9）- {controller.language_name}")
    else:
        steps = parse_step_list(args.steps)
        if not steps:
            print("❌ 没有指定有效的步骤")
            sys.exit(1)
        print(f"🎯 运行指定步骤: {steps} - {controller.language_name}")

    # 执行流水线
    success = controller.run_pipeline(steps)

    if success:
        print("\n🎉 任务完成!")
        sys.exit(0)
    else:
        print("\n❌ 任务执行过程中遇到错误!")
        sys.exit(1)


if __name__ == "__main__":
    main()
