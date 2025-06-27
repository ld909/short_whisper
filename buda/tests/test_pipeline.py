#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管道系统测试脚本
"""

import sys
import time
import random

def main():
    """测试脚本主函数"""
    script_name = sys.argv[0].split('/')[-1]
    
    print(f"开始执行测试脚本: {script_name}")
    
    # 模拟一些工作
    work_time = random.uniform(1, 3)  # 1-3秒的随机工作时间
    print(f"模拟工作 {work_time:.1f} 秒...")
    time.sleep(work_time)
    
    # 随机决定是否成功（90%成功率）
    if random.random() < 0.9:
        print(f"✅ {script_name} 执行成功")
        sys.exit(0)
    else:
        print(f"❌ {script_name} 执行失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
