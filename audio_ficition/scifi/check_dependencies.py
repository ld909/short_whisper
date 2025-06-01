#!/usr/bin/env python3
"""
依赖检查和安装脚本

检查 match_mp4_covers.py 脚本所需的依赖库是否已安装
"""

import sys
import subprocess
import importlib

def check_and_install_package(package_name, import_name=None):
    """检查并安装Python包"""
    if import_name is None:
        import_name = package_name
    
    try:
        importlib.import_module(import_name)
        print(f"✅ {package_name} 已安装")
        return True
    except ImportError:
        print(f"❌ {package_name} 未安装")
        
        try:
            print(f"正在安装 {package_name}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            print(f"✅ {package_name} 安装成功")
            return True
        except subprocess.CalledProcessError:
            print(f"❌ {package_name} 安装失败")
            return False

def main():
    """主函数"""
    print("🔍 检查 MP4 匹配脚本依赖...")
    print("=" * 40)
    
    # 需要检查的依赖包
    dependencies = [
        ("opencv-python", "cv2"),
        ("pillow", "PIL"),
        ("numpy", "numpy"),
        ("tqdm", "tqdm"),
    ]
    
    all_installed = True
    
    for package_name, import_name in dependencies:
        if not check_and_install_package(package_name, import_name):
            all_installed = False
    
    print("\n" + "=" * 40)
    if all_installed:
        print("🎉 所有依赖都已安装完成！")
        print("可以运行: python match_mp4_covers.py")
    else:
        print("⚠️ 部分依赖安装失败，请手动安装")
        print("手动安装命令:")
        for package_name, _ in dependencies:
            print(f"  pip install {package_name}")

if __name__ == "__main__":
    main() 