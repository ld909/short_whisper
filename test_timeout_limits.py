#!/usr/bin/env python3
"""
测试脚本：验证音频时长限制修改
验证30分钟限制是否已正确修改为120分钟
"""

import re
import os

def test_timeout_limits():
    """测试音频时长限制是否已从30分钟改为120分钟"""
    print("🔍 测试音频时长限制设置...")
    
    # 测试文件路径
    files_to_check = [
        "buda/mp3tofineEngsrt.py",
        "buda/after_whisper_controller.py"
    ]
    
    results = {}
    
    for file_path in files_to_check:
        print(f"\n📁 检查文件: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在: {file_path}")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查各种时长限制相关的设置
        checks = {
            "7200秒限制": len(re.findall(r'>\s*7200', content)),
            "120分钟提及": len(re.findall(r'120.*(?:分钟|min)', content)),
            "1800秒限制": len(re.findall(r'>\s*1800', content)),
            "30分钟提及": len(re.findall(r'30.*(?:分钟|min)', content)),
            "3600秒限制": len(re.findall(r'>\s*3600', content)),
            "60分钟提及": len(re.findall(r'60.*(?:分钟|min)', content))
        }
        
        results[file_path] = checks
        
        for check_name, count in checks.items():
            if count > 0:
                print(f"  ✅ {check_name}: {count} 处")
            else:
                print(f"  ⚪ {check_name}: {count} 处")
    
    # 验证结果
    print("\n" + "="*50)
    print("🎯 修改验证结果:")
    print("="*50)
    
    mp3_file_correct = False
    video_file_correct = False
    
    # 检查mp3tofineEngsrt.py
    if "buda/mp3tofineEngsrt.py" in results:
        mp3_results = results["buda/mp3tofineEngsrt.py"]
        if mp3_results["7200秒限制"] > 0 and mp3_results["120分钟提及"] > 0 and mp3_results["1800秒限制"] == 0:
            print("✅ buda/mp3tofineEngsrt.py: 30分钟 → 120分钟 修改成功")
            mp3_file_correct = True
        else:
            print("❌ buda/mp3tofineEngsrt.py: 修改可能不完整")
    
    # 检查after_whisper_controller.py
    if "buda/after_whisper_controller.py" in results:
        video_results = results["buda/after_whisper_controller.py"]
        if video_results["7200秒限制"] > 0 and video_results["120分钟提及"] > 0:
            print("✅ buda/after_whisper_controller.py: 60分钟 → 120分钟 修改成功")
            video_file_correct = True
        else:
            print("❌ buda/after_whisper_controller.py: 修改可能不完整")
    
    if mp3_file_correct and video_file_correct:
        print("\n🎉 所有音频时长限制已成功修改为120分钟！")
        print("📋 修改摘要:")
        print("   • MP3音频处理: 30分钟 → 120分钟")
        print("   • MP4视频处理: 60分钟 → 120分钟")
        print("   • 数值变更: 1800秒/3600秒 → 7200秒")
    else:
        print("\n⚠️  修改可能不完整，请检查代码")
    
    print("="*50)

if __name__ == "__main__":
    test_timeout_limits() 