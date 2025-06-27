#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
材料生成管道主控脚本
按照指定顺序执行所有生成材料的脚本
优化版本：支持配置文件、结构化日志、错误重试和断点续传
"""

import os
import sys
import subprocess
import time
import platform
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from pipeline_logger import PipelineLogger
from pipeline_state import PipelineState


class PipelineController:
    """管道控制器 - 优化版本"""

    def __init__(self, config_file: str = "pipeline_config.json", state_file: str = "pipeline_state.json", languages: Optional[List[str]] = None):
        self.script_dir = Path(__file__).parent
        self.config = self._load_config(self.script_dir / "config" / config_file)
        self.logger = PipelineLogger(self.config["logging"], "pipeline")
        self.state = PipelineState(self.script_dir / "data" / state_file)
        self.steps = self.config["steps"]
        
        # 设置语言配置
        self.languages = self._setup_languages(languages)
        self.logger.info(f"使用语言: {', '.join(self.languages)}")
        
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """加载配置文件"""
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise RuntimeError(f"无法加载配置文件: {e}")

    def _setup_languages(self, languages: Optional[List[str]]) -> List[str]:
        """设置语言配置"""
        if languages is None:
            # 使用配置文件中的默认语言
            return self.config.get("languages", {}).get("default", ["en", "ko"])
        
        # 验证语言是否支持
        supported_languages = self.config.get("languages", {}).get("supported", ["en", "ko", "ja", "vi"])
        valid_languages = []
        
        for lang in languages:
            if lang in supported_languages:
                valid_languages.append(lang)
            else:
                self.logger.warning(f"不支持的语言: {lang}，将被忽略")
        
        if not valid_languages:
            self.logger.warning("没有有效的语言，使用默认语言")
            return self.config.get("languages", {}).get("default", ["en", "ko"])
        
        return valid_languages

    def _get_language_args(self, step_config: Dict[str, Any]) -> List[str]:
        """获取语言参数"""
        if not step_config.get("requires_languages", False):
            return []
        
        script_name = step_config["script"]
        
        # 根据不同脚本使用不同的语言格式
        if script_name == "translate_srt_zh_multi.py":
            # 翻译脚本使用完整语言名称
            language_mapping = self.config.get("languages", {}).get("mapping", {})
            lang_names = [language_mapping.get(lang, lang) for lang in self.languages]
            return ["-l"] + lang_names
        else:
            # 其他脚本使用语言代码
            return ["-l"] + self.languages

    def _should_skip_step(self, step_config: Dict[str, Any]) -> tuple[bool, str]:
        """检查是否应该跳过步骤"""
        script_name = step_config["script"]
        
        # 检查Mac系统跳过规则
        if platform.system() == "Darwin":
            mac_skip_scripts = self.config["system_rules"]["mac_skip_scripts"]
            if script_name in mac_skip_scripts:
                return True, self.config["system_rules"]["mac_skip_reason"]
        
        # 检查是否已完成
        step_number = step_config["step_number"]
        if self.state.is_step_completed(step_number):
            return True, "步骤已完成，跳过执行"
        
        return False, ""

    def _get_step_config(self, step_config: Dict[str, Any]) -> Dict[str, Any]:
        """获取步骤配置参数"""
        pipeline_config = self.config["pipeline"]
        
        return {
            "timeout": step_config.get("timeout_override") or pipeline_config["timeout_seconds"],
            "max_retries": step_config.get("max_retries_override") or pipeline_config["max_retries"],
            "retry_delay": pipeline_config["retry_delay_seconds"]
        }

    def _execute_script(self, script_path: Path, timeout: int, step_config: Dict[str, Any]) -> subprocess.CompletedProcess:
        """执行脚本"""
        # 构建命令行参数
        cmd = [sys.executable, str(self.script_dir / "src" / script_path.name)]
        
        # 添加语言参数
        language_args = self._get_language_args(step_config)
        if language_args:
            cmd.extend(language_args)
            self.logger.info(f"添加语言参数: {' '.join(language_args)}")
        
        return subprocess.run(
            cmd,
            cwd=self.script_dir,
            text=True,
            timeout=timeout,
        )

    def run_script(self, step_config: Dict[str, Any], step_index: int) -> bool:
        """运行单个脚本，支持重试机制"""
        script_name = step_config["script"]
        step_number = step_config["step_number"]
        description = step_config["description"]
        
        # 检查是否跳过
        should_skip, skip_reason = self._should_skip_step(step_config)
        if should_skip:
            self.logger.step_skip(step_number, description, skip_reason)
            return True

        # 获取配置参数
        config = self._get_step_config(step_config)
        script_path = self.script_dir / script_name

        if not script_path.exists():
            error_msg = f"脚本文件 {script_name} 不存在"
            self.logger.error(error_msg, step_number)
            self.state.complete_step(step_number, False, error_msg)
            return False

        # 记录步骤开始
        self.state.start_step(step_index, step_number, script_name, description)
        self.logger.step_start(step_number, description, script_name)
        
        # 重试机制
        max_attempts = config["max_retries"] + 1
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                self.logger.step_retry(step_number, description, attempt, max_attempts)
                time.sleep(config["retry_delay"])
            
            self.state.record_step_attempt(step_number)
            step_start_time = time.time()
            
            try:
                result = self._execute_script(script_path, config["timeout"], step_config)
                step_duration = time.time() - step_start_time
                
                if result.returncode == 0:
                    self.logger.step_success(step_number, description, step_duration)
                    self.state.complete_step(step_number, True)
                    return True
                else:
                    error_msg = f"脚本退出代码: {result.returncode}"
                    self.logger.step_failure(step_number, description, error_msg, step_duration)
                    
                    # 如果还有重试机会，继续尝试
                    if attempt < max_attempts:
                        continue
                    else:
                        self.state.complete_step(step_number, False, error_msg)
                        return False

            except subprocess.TimeoutExpired:
                step_duration = time.time() - step_start_time
                error_msg = f"脚本执行超时 ({config['timeout']}秒)"
                self.logger.step_failure(step_number, description, error_msg, step_duration)
                
                if attempt < max_attempts:
                    continue
                else:
                    self.state.complete_step(step_number, False, error_msg)
                    return False
                    
            except Exception as e:
                step_duration = time.time() - step_start_time
                error_msg = f"脚本执行异常: {str(e)}"
                self.logger.error(error_msg, step_number, e)
                self.logger.step_failure(step_number, description, error_msg, step_duration)
                
                if attempt < max_attempts:
                    continue
                else:
                    self.state.complete_step(step_number, False, error_msg)
                    return False

        return False

    def _handle_step_failure(self, step_config: Dict[str, Any]) -> str:
        """处理步骤失败，返回用户选择"""
        step_number = step_config["step_number"]
        description = step_config["description"]
        script_name = step_config["script"]
        
        print(f"\n步骤 {step_number} 失败: {description} ({script_name})")
        print("选择操作:")
        print("  y - 继续执行下一步")
        print("  n - 停止执行")
        print("  r - 重试当前步骤")
        print("  q - 退出管道")
        
        while True:
            user_input = input("请选择 (y/n/r/q): ").lower().strip()
            if user_input in ['y', 'n', 'r', 'q']:
                return user_input
            print("无效输入，请输入 y、n、r 或 q")

    def run_pipeline(self, resume: bool = False, start_from: Optional[int] = None):
        """运行完整管道"""
        # 检查是否可以恢复执行
        if resume and self.state.can_resume():
            resume_info = self.state.get_resume_info()
            self.logger.info(f"恢复执行管道 {resume_info['pipeline_id']}")
            self.logger.info(f"从步骤 {resume_info['current_step'] + 1} 开始")
            start_index = resume_info['current_step']
        elif start_from is not None:
            self.logger.info(f"从指定步骤 {start_from} 开始执行")
            start_index = start_from - 1
        else:
            # 开始新的管道执行
            pipeline_id = self.state.start_pipeline(len(self.steps))
            self.logger.pipeline_start(len(self.steps))
            start_index = 0

        failed_steps = []
        
        try:
            # 执行所有步骤
            for i in range(start_index, len(self.steps)):
                step_config = self.steps[i]
                
                while True:  # 重试循环
                    success = self.run_script(step_config, i)
                    
                    if success:
                        break
                    else:
                        failed_steps.append({
                            "step_number": step_config["step_number"],
                            "description": step_config["description"],
                            "script_name": step_config["script"]
                        })
                        
                        # 处理失败
                        user_choice = self._handle_step_failure(step_config)
                        
                        if user_choice == 'q':
                            self.logger.info("用户选择退出管道执行")
                            self.state.complete_pipeline("interrupted")
                            return
                        elif user_choice == 'n':
                            self.logger.info("用户选择停止执行")
                            self.state.complete_pipeline("failed")
                            return
                        elif user_choice == 'r':
                            self.logger.info("用户选择重试当前步骤")
                            # 从失败步骤列表中移除，准备重试
                            failed_steps = [f for f in failed_steps 
                                          if f["step_number"] != step_config["step_number"]]
                            continue
                        else:  # user_choice == 'y'
                            self.logger.info("继续执行下一步...")
                            break

            # 完成管道执行
            if not failed_steps:
                self.state.complete_pipeline("completed")
            else:
                self.state.complete_pipeline("completed_with_failures")
                
        except KeyboardInterrupt:
            self.logger.warning("用户中断执行")
            self.state.complete_pipeline("interrupted")
            raise
        except Exception as e:
            self.logger.error(f"管道执行出现未预期错误: {str(e)}", exception=e)
            self.state.complete_pipeline("failed")
            raise
        finally:
            # 生成最终报告
            self._generate_report(failed_steps)

    def _generate_report(self, failed_steps: List[Dict[str, str]]):
        """生成执行报告"""
        summary = self.state.get_execution_summary()
        
        self.logger.pipeline_complete(
            summary["success_count"],
            summary["total_steps"],
            summary["duration"]
        )
        
        if failed_steps:
            self.logger.warning(f"失败的步骤 ({len(failed_steps)} 个):")
            for step in failed_steps:
                self.logger.warning(f"  - 步骤 {step['step_number']}: {step['description']} ({step['script_name']})")
        
        # 输出日志文件位置
        log_file = self.logger.get_log_file_path()
        if log_file:
            self.logger.info(f"详细日志已保存到: {log_file}")

    def show_status(self):
        """显示当前状态"""
        if self.state.can_resume():
            resume_info = self.state.get_resume_info()
            print(f"管道状态: 可恢复执行")
            print(f"管道ID: {resume_info['pipeline_id']}")
            print(f"当前步骤: {resume_info['current_step'] + 1}/{resume_info['total_steps']}")
            print(f"已完成: {resume_info['success_count']} 个步骤")
            print(f"失败步骤: {len(resume_info['failed_steps'])} 个")
        else:
            summary = self.state.get_execution_summary()
            print(f"管道状态: {summary['status']}")
            if summary['pipeline_id']:
                print(f"管道ID: {summary['pipeline_id']}")
                print(f"成功率: {summary['success_rate']:.1f}%")

    def reset_pipeline(self):
        """重置管道状态"""
        self.state.reset_state()
        self.logger.info("管道状态已重置")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="材料生成管道控制器")
    parser.add_argument("--resume", action="store_true", help="恢复中断的执行")
    parser.add_argument("--start-from", type=int, help="从指定步骤开始执行")
    parser.add_argument("--status", action="store_true", help="显示当前状态")
    parser.add_argument("--reset", action="store_true", help="重置管道状态")
    parser.add_argument("--config", default="pipeline_config.json", help="配置文件路径")
    parser.add_argument("--state", default="pipeline_state.json", help="状态文件路径")
    parser.add_argument("-l", "--languages", nargs="+", 
                       choices=["en", "ko", "ja", "vi"],
                       help="指定要处理的语言 (默认: en ko)")
    
    args = parser.parse_args()
    
    try:
        controller = PipelineController(args.config, args.state, args.languages)
        
        if args.status:
            controller.show_status()
        elif args.reset:
            controller.reset_pipeline()
        else:
            controller.run_pipeline(resume=args.resume, start_from=args.start_from)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断执行")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 管道执行出现未预期错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
