#!/usr/bin/env python3
"""
代理设置测试脚本
用于验证代理配置是否正确工作
"""

import os
import requests
import urllib.request

def setup_proxy():
    """设置代理环境变量"""
    proxy_host = "127.0.0.1"
    proxy_port = "7897"  # 使用混合代理端口
    proxy_url = f"http://{proxy_host}:{proxy_port}"
    
    # 设置HTTP和HTTPS代理
    os.environ['HTTP_PROXY'] = proxy_url
    os.environ['HTTPS_PROXY'] = proxy_url
    os.environ['http_proxy'] = proxy_url
    os.environ['https_proxy'] = proxy_url
    
    # 设置不使用代理的地址（本地地址）
    os.environ['NO_PROXY'] = 'localhost,127.0.0.1,::1'
    os.environ['no_proxy'] = 'localhost,127.0.0.1,::1'
    
    print(f"已设置代理: {proxy_url}")
    return proxy_url

def test_proxy_connection():
    """测试代理连接"""
    proxy_url = setup_proxy()
    
    print("正在测试代理连接...")
    
    # 测试1: 使用requests库
    try:
        response = requests.get('https://httpbin.org/ip', timeout=10)
        print(f"通过requests访问成功，IP信息: {response.json()}")
    except Exception as e:
        print(f"requests测试失败: {e}")
    
    # 测试2: 使用urllib
    try:
        with urllib.request.urlopen('https://httpbin.org/ip', timeout=10) as response:
            data = response.read().decode('utf-8')
            print(f"通过urllib访问成功，响应: {data}")
    except Exception as e:
        print(f"urllib测试失败: {e}")
    
    # 显示当前环境变量
    print("\n当前代理环境变量:")
    for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
        print(f"{key}: {os.environ.get(key, '未设置')}")

if __name__ == "__main__":
    test_proxy_connection() 