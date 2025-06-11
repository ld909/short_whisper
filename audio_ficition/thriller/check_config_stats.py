#!/usr/bin/env python3
import json

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

print("=== 配置文件各部分的数量统计 ===")
print()

# 检查story_settings
print("story_settings:")
for key, value in config["story_settings"].items():
    if isinstance(value, list):
        print(f"  {key}: {len(value)} 项")

print()

# 检查protagonist_elements
print("protagonist_elements:")
for key, value in config["protagonist_elements"].items():
    if isinstance(value, list):
        print(f"  {key}: {len(value)} 项")

print()

# 检查antagonist_elements
print("antagonist_elements:")
for key, value in config["antagonist_elements"].items():
    if isinstance(value, list):
        print(f"  {key}: {len(value)} 项")

print()

# 检查additional_story_elements
print("additional_story_elements:")
for key, value in config["additional_story_elements"].items():
    if isinstance(value, list):
        print(f"  {key}: {len(value)} 项")

print()

# 检查顶级列表
print("顶级列表:")
if "plot_twist_catalogue" in config:
    print(f'  plot_twist_catalogue: {len(config["plot_twist_catalogue"])} 项')
if "thematic_cores_catalogue" in config:
    print(f'  thematic_cores_catalogue: {len(config["thematic_cores_catalogue"])} 项')

print()
print("总统计:")
total_lists = 0
min_items = float("inf")
max_items = 0
under_50 = []

for section_key in [
    "story_settings",
    "protagonist_elements",
    "antagonist_elements",
    "additional_story_elements",
]:
    if section_key in config:
        for key, value in config[section_key].items():
            if isinstance(value, list):
                total_lists += 1
                count = len(value)
                min_items = min(min_items, count)
                max_items = max(max_items, count)
                if count < 50:
                    under_50.append(f"{section_key}.{key}: {count}")

# 检查顶级列表
for key in ["plot_twist_catalogue", "thematic_cores_catalogue"]:
    if key in config and isinstance(config[key], list):
        total_lists += 1
        count = len(config[key])
        min_items = min(min_items, count)
        max_items = max(max_items, count)
        if count < 50:
            under_50.append(f"{key}: {count}")

print(f"总列表数量: {total_lists}")
print(f"最少项目数: {min_items}")
print(f"最多项目数: {max_items}")
print(f"少于50项的列表数量: {len(under_50)}")

if under_50:
    print("少于50项的列表:")
    for item in under_50:
        print(f"  - {item}")
else:
    print("所有列表都有50个以上的项目！")
