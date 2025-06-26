#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_tyro.py 错误处理机制测试脚本

测试不同类型的API错误和重试机制
"""

import os
import sys
import time
from unittest.mock import patch, MagicMock
from openai import OpenAI

# 添加当前目录到Python路径，以便导入fix_tyro模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fix_tyro import fix_typos, print_api_stats, api_stats, stats_lock


def reset_stats():
    """重置统计数据"""
    with stats_lock:
        for key in api_stats:
            api_stats[key] = 0


def test_network_error_retry():
    """测试网络错误重试机制"""
    print("=" * 60)
    print("测试1: 网络连接错误重试机制")
    print("=" * 60)

    reset_stats()

    # 模拟网络连接错误
    def mock_create(*args, **kwargs):
        raise ConnectionError("Network connection failed")

    with patch("fix_tyro.setup_uni_client") as mock_setup:
        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_setup.return_value = mock_client

        # 设置环境变量
        os.environ["UNI_API_KEY"] = "test_key"

        result = fix_typos("测试句子", "", "uni", max_retries=2)

        print(f"返回结果: {result}")
        print(f"API调用失败，应该返回原句")

        # 验证统计数据
        print(f"总调用次数: {api_stats['total_calls']}")
        print(f"网络错误次数: {api_stats['network_errors']}")
        print(f"重试次数: {api_stats['retry_calls']}")
        print(f"失败调用次数: {api_stats['failed_calls']}")


def test_rate_limit_error():
    """测试API限流错误处理"""
    print("\n" + "=" * 60)
    print("测试2: API限流错误处理")
    print("=" * 60)

    reset_stats()

    # 模拟API限流错误
    def mock_create(*args, **kwargs):
        raise Exception("Rate limit exceeded")

    with patch("fix_tyro.setup_uni_client") as mock_setup:
        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_setup.return_value = mock_client

        result = fix_typos("测试句子", "", "uni", max_retries=1)

        print(f"返回结果: {result}")
        print(f"API限流错误，应该返回原句")

        # 验证统计数据
        print(f"总调用次数: {api_stats['total_calls']}")
        print(f"限流错误次数: {api_stats['rate_limit_errors']}")
        print(f"重试次数: {api_stats['retry_calls']}")
        print(f"失败调用次数: {api_stats['failed_calls']}")


def test_auth_error():
    """测试认证错误处理（不应该重试）"""
    print("\n" + "=" * 60)
    print("测试3: 认证错误处理（不重试）")
    print("=" * 60)

    reset_stats()

    # 模拟认证错误
    def mock_create(*args, **kwargs):
        raise Exception("Unauthorized: Invalid API key")

    with patch("fix_tyro.setup_uni_client") as mock_setup:
        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_setup.return_value = mock_client

        result = fix_typos("测试句子", "", "uni", max_retries=3)

        print(f"返回结果: {result}")
        print(f"认证错误，不应该重试，直接返回原句")

        # 验证统计数据
        print(f"总调用次数: {api_stats['total_calls']}")
        print(f"认证错误次数: {api_stats['auth_errors']}")
        print(f"重试次数: {api_stats['retry_calls']} (应该为0)")
        print(f"失败调用次数: {api_stats['failed_calls']}")


def test_successful_call():
    """测试成功的API调用"""
    print("\n" + "=" * 60)
    print("测试4: 成功的API调用")
    print("=" * 60)

    reset_stats()

    # 模拟成功的API响应
    def mock_create(*args, **kwargs):
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "修正后的句子"
        return mock_response

    with patch("fix_tyro.setup_uni_client") as mock_setup:
        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_setup.return_value = mock_client

        result = fix_typos("测试句子", "", "uni", max_retries=3)

        print(f"返回结果: {result}")
        print(f"API调用成功，应该返回修正后的句子")

        # 验证统计数据
        print(f"总调用次数: {api_stats['total_calls']}")
        print(f"成功调用次数: {api_stats['successful_calls']}")
        print(f"重试次数: {api_stats['retry_calls']} (应该为0)")
        print(f"失败调用次数: {api_stats['failed_calls']} (应该为0)")


def test_retry_then_success():
    """测试重试后成功的场景"""
    print("\n" + "=" * 60)
    print("测试5: 重试后成功的场景")
    print("=" * 60)

    reset_stats()

    call_count = 0

    # 模拟前两次失败，第三次成功
    def mock_create(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise ConnectionError("Network temporarily unavailable")
        else:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "最终修正的句子"
            return mock_response

    with patch("fix_tyro.setup_uni_client") as mock_setup:
        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create
        mock_setup.return_value = mock_client

        start_time = time.time()
        result = fix_typos("测试句子", "", "uni", max_retries=3)
        end_time = time.time()

        print(f"返回结果: {result}")
        print(f"总耗时: {end_time - start_time:.2f}秒")
        print(f"前两次失败，第三次成功")

        # 验证统计数据
        print(f"总调用次数: {api_stats['total_calls']}")
        print(f"成功调用次数: {api_stats['successful_calls']}")
        print(f"网络错误次数: {api_stats['network_errors']}")
        print(f"重试次数: {api_stats['retry_calls']}")
        print(f"失败调用次数: {api_stats['failed_calls']}")


def main():
    """运行所有测试"""
    print("fix_tyro.py 错误处理机制测试")
    print("测试将验证重试机制、错误分类和统计功能")

    # 设置环境变量
    os.environ["UNI_API_KEY"] = "test_key_for_testing"

    try:
        test_network_error_retry()
        test_rate_limit_error()
        test_auth_error()
        test_successful_call()
        test_retry_then_success()

        print("\n" + "=" * 60)
        print("所有测试完成")
        print("=" * 60)
        print_api_stats()

    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
