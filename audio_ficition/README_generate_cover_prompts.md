# 科幻故事封面提示词生成器使用说明

## 功能概述

`generate_cover_prompts.py` 是一个专门为科幻故事生成文生图封面提示词的工具。它能够：

- 读取 `ai_studio_bot.py` 生成的故事内容
- 使用 GPT-4.1-mini 模型生成专业的文生图提示词
- 重点突出女主角（外星人）和男主角的特征
- 根据故事情节设计背景和场景
- 支持断点续传和批量处理

## 系统要求

- Python 3.7+
- 已安装所需依赖：`openai`, `tqdm`
- 设置环境变量 `UNI_API_KEY`

## 输入输出

### 输入
- **故事文件路径**: `/Volumes/dhl/audio/scifi/full_story/language_code/*.txt`
- **文件格式**: 纯文本文件，由 `ai_studio_bot.py` 生成

### 输出
- **封面提示词文件**: `/Volumes/dhl/audio/scifi/full_story/cover_prompts/[故事索引].txt`
- **内容格式**: 英文的文生图提示词

## 使用方法

### 基本使用
```bash
cd audio_ficition
python generate_cover_prompts.py
```

### 强制重新生成所有提示词
```bash
python generate_cover_prompts.py -f
```

### 指定故事索引范围
```bash
# 只处理故事 1-10
python generate_cover_prompts.py --start 1 --end 10

# 处理从故事 5 开始的所有故事
python generate_cover_prompts.py --start 5

# 处理到故事 20 为止的所有故事
python generate_cover_prompts.py --end 20
```

### 查看帮助信息
```bash
python generate_cover_prompts.py -h
```

## 提示词特色

生成的提示词会包含以下元素：

1. **女主角特征**：
   - 外星人身份
   - 性感年轻的形象
   - 大胸身材
   - 人形面貌但特殊肤色

2. **男主角特征**：
   - 根据故事内容描述特征

3. **背景场景**：
   - 科幻元素
   - 与故事情节相关

4. **整体氛围**：
   - 浪漫
   - 神秘
   - 具有视觉冲击力

## 示例输出

```
A beautiful alien female with ethereal blue-tinted skin and voluptuous figure, wearing futuristic attire, standing beside a handsome human male astronaut in silver space suit, against a backdrop of distant nebulae and cosmic aurora, romantic and mysterious atmosphere, highly detailed, cinematic lighting, science fiction art style
```

## 错误处理

- 脚本会自动重试失败的 API 请求（最多3次）
- 支持断点续传，已处理的故事不会重复生成
- 详细的错误日志和进度显示

## 注意事项

1. 确保已正确设置 `UNI_API_KEY` 环境变量
2. 故事文件必须存在且有内容
3. 生成过程中会有适当的延迟以避免API限制
4. 生成的提示词为英文，适合大多数文生图模型

## 技术细节

- **模型**: GPT-4.1-mini
- **最大Token数**: 500
- **超时时间**: 30秒
- **重试机制**: 3次，递增延迟
- **编码格式**: UTF-8 