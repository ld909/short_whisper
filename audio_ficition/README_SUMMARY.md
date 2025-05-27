# 科幻故事封面提示词生成器 - 项目总结

## 🎯 项目概述

根据您的需求，我已经成功创建了一个完整的科幻故事封面提示词生成系统。这个系统能够读取由 `ai_studio_bot.py` 生成的故事内容，并使用GPT-4.1-mini模型生成专业的文生图封面提示词。

## 📁 文件结构

```
audio_ficition/
├── generate_cover_prompts.py      # 主脚本 - 封面提示词生成器
├── test_cover_prompts.py          # 测试脚本 - 验证功能
├── example_usage.py               # 示例脚本 - 交互式使用指南
├── README_generate_cover_prompts.md  # 详细使用说明
└── README_SUMMARY.md              # 项目总结（本文件）
```

## 🚀 核心功能

### 1. 主脚本 `generate_cover_prompts.py`

**功能特点:**
- ✅ 读取 `ai_studio_bot.py` 的输出故事内容
- ✅ 使用与 `generate_key_phrases.py` 相同的模型调用方式
- ✅ 实现了您指定的系统提示词
- ✅ 重点突出女主角（外星人）和男主角特征
- ✅ 支持断点续传和批量处理
- ✅ 完善的错误处理和重试机制

**输入输出:**
- **输入**: `/Volumes/dhl/audio/scifi/full_story/language_code/*.txt`
- **输出**: `/Volumes/dhl/audio/scifi/full_story/cover_prompts/[故事索引].txt`

### 2. 系统提示词设计

严格按照您的要求设计：

```
你是一个伟大的文生图提示词大师，能够根据一个故事，生成文生图的提示词。
提示词一定要体现女主和男主，女主是外星人，性感年轻，大胸身材，人形面貌，
就是肤色不太一样。背景等都是根据故事和情节进行设计哈，一定要体现女主的魅力和动人。
```

### 3. 生成效果展示

**生成的提示词示例:**
```
Star Law Marshal Kaelen Vance, rugged human male, sharp intense eyes, wearing 
futuristic tactical space suit with cold, steely demeanor, standing confidently; 
beside him stands Lyra, alluring young female alien, humanoid form with large 
bust and slender figure, skin a shimmering iridescent metal texture shifting 
through blues, greens, violets, and coppery bronzes, radiant golden eyes glowing 
softly, subtle inner light pulsing warmly from her body...
```

## 🛠️ 使用方法

### 基本使用
```bash
cd audio_ficition
python generate_cover_prompts.py
```

### 常用参数
```bash
# 生成特定范围的故事
python generate_cover_prompts.py --start 1 --end 10

# 强制重新生成
python generate_cover_prompts.py -f

# 查看帮助
python generate_cover_prompts.py -h
```

### 交互式使用
```bash
python example_usage.py
```

## 🧪 测试验证

已创建完整的测试系统：

1. **功能测试**: `python test_cover_prompts.py`
2. **实际测试**: 已成功生成故事1的封面提示词
3. **验证结果**: 生成的提示词完全符合要求

## 📊 技术实现

### 模型配置
- **模型**: GPT-4.1-mini
- **API**: UNI API (与 generate_key_phrases.py 一致)
- **最大Token**: 500
- **超时时间**: 30秒
- **重试机制**: 3次，递增延迟

### 代码特点
- 📝 **可读性强**: 详细的中文注释和文档
- 🔄 **可恢复性**: 支持断点续传
- 🛡️ **健壮性**: 完善的错误处理
- 📈 **可扩展性**: 模块化设计，易于维护

## 🎯 完成度检查

✅ **需求1**: 读取ai_studio_bot.py的输出 - 完成  
✅ **需求2**: 使用与generate_key_phrases.py相同的模型方式 - 完成  
✅ **需求3**: 实现指定的系统提示词 - 完成  
✅ **需求4**: 脚本名称清晰易懂 - 完成  

## 📋 依赖要求

已更新 `requirements.txt`:
```
openai>=1.0.0
tqdm>=4.62.0
```

## 🚀 快速开始

1. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```

2. **设置API密钥**:
   ```bash
   export UNI_API_KEY='your-api-key'
   ```

3. **运行测试**:
   ```bash
   python test_cover_prompts.py
   ```

4. **生成提示词**:
   ```bash
   python generate_cover_prompts.py --start 1 --end 3
   ```

## 🎉 项目价值

这个工具将显著提升您的科幻故事创作流程：

1. **自动化**: 从故事文本到视觉提示词的完全自动化
2. **专业性**: AI生成的提示词专业且具有吸引力
3. **一致性**: 确保所有封面都突出女主角的魅力
4. **效率**: 批量处理，大大节省时间
5. **质量**: 基于GPT-4.1-mini的高质量输出

---

🎨 **现在您可以为所有科幻故事生成专业的封面提示词了！** 