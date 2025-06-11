#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证扩展配置文件的结构和内容
"""

import json
import sys


def verify_config(config_file):
    """验证配置文件"""

    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    print(f"正在验证配置文件: {config_file}")
    print("=" * 60)

    # 检查主要数组长度
    arrays_to_check = [
        ("story_settings.primary_horror_subgenres", "主要恐怖类型"),
        ("story_settings.secondary_horror_elements", "次要恐怖元素"),
        ("story_settings.horror_atmospheres", "恐怖氛围"),
        ("story_settings.settings_locations", "设定地点"),
        ("story_settings.time_periods", "时间段"),
        ("protagonist_elements.archetypes", "主角原型"),
        ("protagonist_elements.backgrounds", "主角背景"),
        ("protagonist_elements.psychological_traits", "心理特征"),
        ("protagonist_elements.fatal_flaws", "致命缺陷"),
        ("antagonist_elements.supernatural_entities", "超自然实体"),
        ("antagonist_elements.human_antagonists", "人类反派"),
        ("antagonist_elements.motivations", "反派动机"),
    ]

    for path, name in arrays_to_check:
        try:
            # 解析嵌套路径
            parts = path.split(".")
            data = config
            for part in parts:
                data = data[part]

            length = len(data)
            status = "✓" if length >= 50 else "⚠"
            print(f"{status} {name}: {length} 项")

            if length < 50:
                print(f"   需要再增加 {50 - length} 项")

        except KeyError as e:
            print(f"✗ {name}: 未找到路径 {path}")
        except Exception as e:
            print(f"✗ {name}: 错误 - {str(e)}")

    print("=" * 60)
    print("验证完成！")


if __name__ == "__main__":
    config_file = "config.json"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]

    try:
        verify_config(config_file)
    except FileNotFoundError:
        print(f"错误：找不到文件 {config_file}")
    except json.JSONDecodeError as e:
        print(f"错误：JSON格式错误 - {str(e)}")
    except Exception as e:
        print(f"错误：{str(e)}")
