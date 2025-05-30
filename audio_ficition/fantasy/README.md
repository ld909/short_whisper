# 奇幻脚本生成器

这是一个基于配置文件的奇幻有声书脚本参数生成器，能够从 `config.json` 中随机选择各种元素来创建独特的奇幻故事参数。

## 使用方法

在当前目录下运行：

```bash
# 生成故事参数
python fantasy_script_generator.py

# 检查配置使用情况
python test_config_usage.py
```

## 文件说明

- `config.json`: 配置文件，包含所有故事元素
- `fantasy_script_generator.py`: 主程序
- `test_config_usage.py`: 配置验证程序
- `README.md`: 说明文档

## 输出

程序会在 `/Volumes/dhl/audio/fantasy/story_param/` 目录下生成：
- 故事参数文件：`story_[数字].txt`
- 索引文件：`story_index.txt`

## 特点

- 使用 config.json 中的每一个配置项
- 每次运行产生不同的随机组合
- 生成完整的中文故事创作提示
- 自动移除 markdown 格式标记 