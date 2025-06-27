#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管道日志模块
提供结构化日志记录功能
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class PipelineLogger:
    """管道日志记录器"""
    
    def __init__(self, config: dict, pipeline_name: str = "pipeline"):
        self.config = config
        self.pipeline_name = pipeline_name
        self.logger = None
        self.log_file_path = None
        self._setup_logger()
    
    def _setup_logger(self):
        """设置日志记录器"""
        # 创建日志器
        self.logger = logging.getLogger(self.pipeline_name)
        self.logger.setLevel(getattr(logging, self.config.get('level', 'INFO')))
        
        # 清除已有的处理器
        self.logger.handlers.clear()
        
        # 创建格式化器
        formatter = logging.Formatter(
            self.config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        
        # 控制台输出
        if self.config.get('console_output', True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 文件输出
        if self.config.get('file_output', True):
            self._setup_file_handler(formatter)
    
    def _setup_file_handler(self, formatter):
        """设置文件处理器"""
        log_dir = Path(self.config.get('log_directory', 'logs'))
        log_dir.mkdir(exist_ok=True)
        
        # 生成日志文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f"{self.pipeline_name}_{timestamp}.log"
        self.log_file_path = log_dir / log_filename
        
        # 创建文件处理器
        file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def info(self, message: str, step_number: Optional[str] = None):
        """记录信息日志"""
        if step_number:
            message = f"[步骤 {step_number}] {message}"
        self.logger.info(message)
    
    def warning(self, message: str, step_number: Optional[str] = None):
        """记录警告日志"""
        if step_number:
            message = f"[步骤 {step_number}] {message}"
        self.logger.warning(message)
    
    def error(self, message: str, step_number: Optional[str] = None, exception: Optional[Exception] = None):
        """记录错误日志"""
        if step_number:
            message = f"[步骤 {step_number}] {message}"
        if exception:
            message = f"{message} - 异常: {str(exception)}"
        self.logger.error(message)
    
    def debug(self, message: str, step_number: Optional[str] = None):
        """记录调试日志"""
        if step_number:
            message = f"[步骤 {step_number}] {message}"
        self.logger.debug(message)
    
    def step_start(self, step_number: str, description: str, script_name: str):
        """记录步骤开始"""
        separator = "=" * 60
        self.info(f"\n{separator}")
        self.info(f"步骤 {step_number}: {description}", step_number)
        self.info(f"正在运行: {script_name}", step_number)
        self.info(f"{separator}")
    
    def step_success(self, step_number: str, description: str, duration: float):
        """记录步骤成功"""
        self.info(f"✅ 步骤完成: {description} (耗时: {duration:.2f}秒)", step_number)
    
    def step_failure(self, step_number: str, description: str, error_msg: str, duration: float):
        """记录步骤失败"""
        self.error(f"❌ 步骤失败: {description} (耗时: {duration:.2f}秒)", step_number)
        self.error(f"错误信息: {error_msg}", step_number)
    
    def step_skip(self, step_number: str, description: str, reason: str):
        """记录步骤跳过"""
        self.info(f"⏭️ 跳过步骤: {description}", step_number)
        self.info(f"跳过原因: {reason}", step_number)
    
    def step_retry(self, step_number: str, description: str, attempt: int, max_attempts: int):
        """记录步骤重试"""
        self.warning(f"🔄 重试步骤: {description} (第 {attempt}/{max_attempts} 次尝试)", step_number)
    
    def pipeline_start(self, total_steps: int):
        """记录管道开始"""
        self.info("🚀 开始执行材料生成管道...")
        self.info(f"总步骤数: {total_steps}")
        self.info(f"日志文件: {self.log_file_path}")
    
    def pipeline_complete(self, success_count: int, total_count: int, duration: float):
        """记录管道完成"""
        separator = "=" * 60
        self.info(f"\n{separator}")
        self.info("📊 执行报告")
        self.info(f"{separator}")
        self.info(f"总执行时间: {duration:.2f} 秒 ({duration/60:.1f} 分钟)")
        self.info(f"成功步骤: {success_count}")
        self.info(f"总步骤数: {total_count}")
        success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
        self.info(f"成功率: {success_rate:.1f}%")
        
        if success_count == total_count:
            self.info("🎉 所有步骤都成功完成！")
        else:
            failed_count = total_count - success_count
            self.warning(f"❌ 有 {failed_count} 个步骤失败")
        
        self.info(f"{separator}")
    
    def get_log_file_path(self) -> Optional[Path]:
        """获取日志文件路径"""
        return self.log_file_path
