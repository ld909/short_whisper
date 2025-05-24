#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
材料生成管道主控脚本
按照指定顺序执行所有生成材料的脚本
"""

import os
import sys
import subprocess
import time
from pathlib import Path

class PipelineController:
    """管道控制器"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.success_count = 0
        self.total_steps = 16  # 总步骤数
        
    def run_script(self, script_name, step_number, description):
        """运行单个脚本"""
        print(f"\n{'='*60}")
        print(f"步骤 {step_number}: {description}")
        print(f"正在运行: {script_name}")
        print(f"{'='*60}")
        
        script_path = self.script_dir / script_name
        
        if not script_path.exists():
            print(f"❌ 错误: 脚本文件 {script_name} 不存在")
            return False
            
        try:
            # 运行脚本
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=self.script_dir,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            
            if result.returncode == 0:
                print(f"✅ 步骤 {step_number} 完成: {description}")
                self.success_count += 1
                return True
            else:
                print(f"❌ 步骤 {step_number} 失败: {description}")
                print(f"错误输出: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ 步骤 {step_number} 超时: {description}")
            return False
        except Exception as e:
            print(f"❌ 步骤 {step_number} 异常: {description}")
            print(f"异常信息: {str(e)}")
            return False
    
    def run_pipeline(self):
        """运行完整管道"""
        print("🚀 开始执行材料生成管道...")
        start_time = time.time()
        
        # 定义所有步骤
        steps = [
            ("mp3tofineEngsrt.py", "1", "生成原始 srt 文件"),
            ("fix_tyro.py", "2", "生成修复的中文 srt 文件"),
            ("split_sentences_zh_srt.py", "2.1", "对中文进行分句得到分句后的txt"),
            ("translate_srt_zh_multi.py", "3", "得到不同语种的 txt"),
            ("generate_mp3_clips.py", "4.1", "生成多语种 mp3 clips (第1次)"),
            ("generate_mp3_clips.py", "4.2", "生成多语种 mp3 clips (第2次)"),
            ("generate_mp3_clips.py", "4.3", "生成多语种 mp3 clips (第3次)"),
            ("check_and_regenerate_mp3.py", "4.1", "检查 mp3 进度，删除坏 mp3，重新生成对应 mp3 clip"),
            ("generate_subtitles.py", "5", "得到不同语言对应 srt 字幕"),
            ("merge_mp3.py", "6", "把 mp3 clips 合成为一个 mp3"),
            ("merge_mp4_clips_by_audio_duration.py", "7", "生成无声且无字幕的 mp4"),
            ("add_subtitles_to_mp4.py", "8", "给无声的 mp4 增加字幕"),
            ("merge_mp4_mp3.py", "9", "给 mp4 添加音频"),
            ("title_translator_multi_lang.py", "10.1", "生成多语言标题翻译结果"),
            ("shorten_titles_multi_lang.py", "10.2", "生成简化多语种标题"),
            ("generate_key_phrases.py", "11", "生成多语种的封面关键词和简化标题"),
            ("generate_multilingual_thumbnails.py", "12", "生成多语种封面"),
            ("generate_multi_lang_descriptions.py", "13", "生成多语种视频描述")
        ]
        
        failed_steps = []
        
        # 执行所有步骤
        for script_name, step_num, description in steps:
            success = self.run_script(script_name, step_num, description)
            if not success:
                failed_steps.append((step_num, description, script_name))
                
                # 询问是否继续
                user_input = input(f"\n步骤 {step_num} 失败。是否继续执行下一步？(y/n/q): ").lower()
                if user_input == 'q':
                    print("❌ 用户选择退出管道执行")
                    break
                elif user_input == 'n':
                    print("❌ 用户选择停止执行")
                    break
                else:
                    print("⏭️ 继续执行下一步...")
        
        # 生成报告
        self.generate_report(start_time, failed_steps)
    
    def generate_report(self, start_time, failed_steps):
        """生成执行报告"""
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n{'='*60}")
        print("📊 执行报告")
        print(f"{'='*60}")
        print(f"总执行时间: {duration:.2f} 秒 ({duration/60:.1f} 分钟)")
        print(f"成功步骤: {self.success_count}")
        print(f"总步骤数: {len(failed_steps) + self.success_count}")
        print(f"成功率: {(self.success_count / (len(failed_steps) + self.success_count)) * 100:.1f}%")
        
        if failed_steps:
            print(f"\n❌ 失败的步骤 ({len(failed_steps)} 个):")
            for step_num, description, script_name in failed_steps:
                print(f"  - 步骤 {step_num}: {description} ({script_name})")
        else:
            print("\n🎉 所有步骤都成功完成！")
        
        print(f"{'='*60}")


def main():
    """主函数"""
    try:
        controller = PipelineController()
        controller.run_pipeline()
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断执行")
    except Exception as e:
        print(f"\n\n❌ 管道执行出现未预期错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 