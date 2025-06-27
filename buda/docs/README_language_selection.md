# 管道语言选择功能使用说明

## 概述

材料生成管道现在支持在命令行中选择要处理的语言。您可以指定一种或多种语言，管道将只处理选定的语言。

## 支持的语言

- `en` - 英语 (English)
- `ko` - 韩语 (Korean)
- `ja` - 日语 (Japanese)
- `vi` - 越南语 (Vietnamese)

## 使用方法

### 1. 使用默认语言
```bash
python main_pipeline.py
```
默认处理英语和韩语 (`en`, `ko`)

### 2. 指定单一语言
```bash
# 只处理韩语
python main_pipeline.py -l ko

# 只处理英语
python main_pipeline.py -l en
```

### 3. 指定多种语言
```bash
# 处理韩语和英语
python main_pipeline.py -l ko en

# 处理所有支持的语言
python main_pipeline.py -l en ko ja vi
```

### 4. 与其他参数结合使用
```bash
# 从步骤3开始，只处理韩语
python main_pipeline.py -l ko --start-from 3

# 恢复执行，处理英语和日语
python main_pipeline.py -l en ja --resume

# 查看状态，使用韩语配置
python main_pipeline.py -l ko --status
```

## 语言参数传递机制

管道会自动将语言参数传递给需要的脚本：

### 翻译脚本 (translate_srt_zh_multi.py)
- 接收完整语言名称：`-l English Korean`

### 其他多语言脚本
- 接收语言代码：`-l en ko`
- 包括：
  - `generate_mp3_clips.py`
  - `generate_subtitles.py`

## 配置文件

语言配置在 `pipeline_config.json` 中定义：

```json
{
  "languages": {
    "supported": ["en", "ko", "ja", "vi"],
    "default": ["en", "ko"],
    "mapping": {
      "en": "English",
      "ko": "Korean", 
      "ja": "Japanese",
      "vi": "Vietnamese"
    }
  }
}
```

## 错误处理

- 如果指定了不支持的语言，系统会发出警告并忽略该语言
- 如果所有指定的语言都不支持，系统会使用默认语言
- 系统会在日志中显示实际使用的语言列表

## 示例输出

```bash
$ python main_pipeline.py -l ko en --status
2025-06-27 11:22:51,513 - pipeline - INFO - 使用语言: ko, en
管道状态: 可恢复执行
管道ID: 20250627_111504
当前步骤: 2/18
已完成: 0 个步骤
失败步骤: 0 个
```

## 注意事项

1. 语言选择会影响所有标记为 `requires_languages: true` 的步骤
2. 不同脚本可能使用不同的语言代码格式，管道会自动处理转换
3. 语言参数只在相关步骤中传递，不会影响其他步骤的执行
