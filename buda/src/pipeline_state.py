#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管道状态管理模块
支持断点续传和执行状态记录
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class PipelineState:
    """管道状态管理器"""
    
    def __init__(self, state_file: str = "pipeline_state.json"):
        self.state_file = Path(state_file)
        self.state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """加载状态文件"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # 返回默认状态
        return {
            "pipeline_id": None,
            "start_time": None,
            "end_time": None,
            "status": "not_started",  # not_started, running, completed, failed, interrupted
            "current_step": 0,
            "total_steps": 0,
            "success_count": 0,
            "failed_steps": [],
            "completed_steps": [],
            "step_details": {}
        }
    
    def _save_state(self):
        """保存状态到文件"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"警告: 无法保存状态文件: {e}")
    
    def start_pipeline(self, total_steps: int) -> str:
        """开始管道执行"""
        pipeline_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.state.update({
            "pipeline_id": pipeline_id,
            "start_time": time.time(),
            "end_time": None,
            "status": "running",
            "current_step": 0,
            "total_steps": total_steps,
            "success_count": 0,
            "failed_steps": [],
            "completed_steps": [],
            "step_details": {}
        })
        self._save_state()
        return pipeline_id
    
    def complete_pipeline(self, status: str = "completed"):
        """完成管道执行"""
        self.state.update({
            "end_time": time.time(),
            "status": status
        })
        self._save_state()
    
    def start_step(self, step_index: int, step_number: str, script_name: str, description: str):
        """开始执行步骤"""
        self.state["current_step"] = step_index
        self.state["step_details"][step_number] = {
            "script_name": script_name,
            "description": description,
            "start_time": time.time(),
            "end_time": None,
            "status": "running",
            "attempts": 0,
            "error_message": None
        }
        self._save_state()
    
    def complete_step(self, step_number: str, success: bool, error_message: Optional[str] = None):
        """完成步骤执行"""
        if step_number in self.state["step_details"]:
            step_detail = self.state["step_details"][step_number]
            step_detail.update({
                "end_time": time.time(),
                "status": "success" if success else "failed",
                "error_message": error_message
            })
            
            if success:
                self.state["success_count"] += 1
                if step_number not in self.state["completed_steps"]:
                    self.state["completed_steps"].append(step_number)
            else:
                if step_number not in self.state["failed_steps"]:
                    self.state["failed_steps"].append(step_number)
        
        self._save_state()
    
    def record_step_attempt(self, step_number: str):
        """记录步骤尝试次数"""
        if step_number in self.state["step_details"]:
            self.state["step_details"][step_number]["attempts"] += 1
            self._save_state()
    
    def is_step_completed(self, step_number: str) -> bool:
        """检查步骤是否已完成"""
        return step_number in self.state["completed_steps"]
    
    def get_failed_steps(self) -> List[str]:
        """获取失败的步骤"""
        return self.state["failed_steps"].copy()
    
    def get_completed_steps(self) -> List[str]:
        """获取已完成的步骤"""
        return self.state["completed_steps"].copy()
    
    def get_current_step(self) -> int:
        """获取当前步骤索引"""
        return self.state["current_step"]
    
    def get_success_count(self) -> int:
        """获取成功步骤数"""
        return self.state["success_count"]
    
    def get_pipeline_status(self) -> str:
        """获取管道状态"""
        return self.state["status"]
    
    def get_step_duration(self, step_number: str) -> Optional[float]:
        """获取步骤执行时长"""
        if step_number in self.state["step_details"]:
            step_detail = self.state["step_details"][step_number]
            if step_detail["start_time"] and step_detail["end_time"]:
                return step_detail["end_time"] - step_detail["start_time"]
        return None
    
    def get_step_attempts(self, step_number: str) -> int:
        """获取步骤尝试次数"""
        if step_number in self.state["step_details"]:
            return self.state["step_details"][step_number]["attempts"]
        return 0
    
    def can_resume(self) -> bool:
        """检查是否可以恢复执行"""
        return (self.state["status"] in ["running", "interrupted"] and 
                self.state["current_step"] < self.state["total_steps"])
    
    def get_resume_info(self) -> Dict[str, Any]:
        """获取恢复执行信息"""
        if not self.can_resume():
            return {}
        
        return {
            "pipeline_id": self.state["pipeline_id"],
            "current_step": self.state["current_step"],
            "total_steps": self.state["total_steps"],
            "success_count": self.state["success_count"],
            "completed_steps": self.state["completed_steps"],
            "failed_steps": self.state["failed_steps"]
        }
    
    def reset_state(self):
        """重置状态"""
        self.state = {
            "pipeline_id": None,
            "start_time": None,
            "end_time": None,
            "status": "not_started",
            "current_step": 0,
            "total_steps": 0,
            "success_count": 0,
            "failed_steps": [],
            "completed_steps": [],
            "step_details": {}
        }
        self._save_state()
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        duration = 0
        if self.state["start_time"]:
            end_time = self.state["end_time"] or time.time()
            duration = end_time - self.state["start_time"]
        
        return {
            "pipeline_id": self.state["pipeline_id"],
            "status": self.state["status"],
            "duration": duration,
            "total_steps": self.state["total_steps"],
            "success_count": self.state["success_count"],
            "failed_count": len(self.state["failed_steps"]),
            "success_rate": (self.state["success_count"] / self.state["total_steps"] * 100) 
                           if self.state["total_steps"] > 0 else 0
        }
