# 多语言视频标题翻译工具使用说明

## 概述

`title_translator_multi_lang.py` 是一个自动化工具，用于将视频标题从中文翻译成多种语言（英语、日语、韩语、越南语）。

## 功能特点

- 🔄 **自动路径对接**: 直接读取 `mp3toscripts_faster.py` 的输出路径作为输入
- 🌐 **多语言支持**: 支持英语、日语、韩语、越南语翻译
- 🚀 **并发处理**: 支持批量并发翻译，提高处理效率
- 💾 **断点续传**: 支持中断后从停止位置继续翻译
- 🏷️ **标签过滤**: 自动去除标题中的标签（#tag格式）
- 📊 **进度显示**: 实时显示翻译进度

## 路径结构

### 输入路径
```
/home/dhl/Documents/video_materials/format_srt/{topic}/{channel}/{video_name}.srt
```
> 此路径与 `mp3toscripts_faster.py` 的输出路径完全一致

### 输出路径
```
/home/dhl/Documents/video_materials/multi_lang_titles/{channel}/{video_name}.json
```

## 使用方法

### 1. 基本使用
```bash
python title_translator_multi_lang.py [主题名称]
```

### 2. 指定目标语言
```bash
python title_translator_multi_lang.py [主题名称] -l English Japanese
```

### 3. 强制重新翻译
```bash
python title_translator_multi_lang.py [主题名称] -f
```

### 4. 设置批处理大小
```bash
python title_translator_multi_lang.py [主题名称] -b 10
```

## 命令行参数

| 参数 | 描述 | 默认值 |
|------|------|--------|
| `topic` | 主题名称（必需） | - |
| `-l, --languages` | 目标语言列表 | English Japanese Vietnamese Korean |
| `-f, --force` | 强制重新翻译，忽略已有翻译 | False |
| `-b, --batch_size` | 并发处理的批量大小 | 5 |

## 环境要求

### 1. API密钥设置
```bash
export UNI_API_KEY='your-openai-api-key'
```

### 2. Python依赖
```bash
pip install openai tqdm
```

### 3. 输入数据准备
确保已运行 `mp3toscripts_faster.py` 生成了SRT文件：
```bash
python mp3toscripts_faster.py
```

## 输出格式

每个视频会生成一个JSON文件，包含以下内容：
```json
{
  "original": "去除标签后的原始中文标题",
  "en": "English translation",
  "ja": "日本語の翻訳",
  "vi": "Bản dịch tiếng Việt", 
  "ko": "한국어 번역"
}
```

## 工作流程

1. **输入检查**: 验证 `mp3toscripts_faster.py` 输出的SRT文件路径
2. **文件扫描**: 扫描指定主题下的所有频道和SRT文件
3. **跳过检查**: 检查已翻译的文件，避免重复处理
4. **标题清理**: 去除文件名中的标签格式
5. **并发翻译**: 使用OpenAI API并发翻译到多种语言
6. **结果保存**: 将翻译结果保存为JSON文件

## 示例使用

假设你有以下目录结构：
```
/home/dhl/Documents/video_materials/format_srt/
├── buddhism/
│   ├── channel1/
│   │   ├── 佛法开示第一集.srt
│   │   └── 禅修指导_入门篇.srt
│   └── channel2/
│       └── 心经讲解.srt
```

运行翻译：
```bash
python title_translator_multi_lang.py buddhism
```

输出结果：
```
/home/dhl/Documents/video_materials/multi_lang_titles/
├── channel1/
│   ├── 佛法开示第一集.json
│   └── 禅修指导_入门篇.json
└── channel2/
    └── 心经讲解.json
```

## 注意事项

1. **API限制**: 注意OpenAI API的调用频率限制
2. **网络连接**: 确保网络连接稳定，翻译过程需要调用在线API
3. **磁盘空间**: 确保输出目录有足够的磁盘空间
4. **错误处理**: 脚本会自动重试失败的翻译，最多重试3次

## 故障排除

### 常见问题

**Q: 提示"API密钥未找到"错误**
A: 检查是否正确设置了环境变量 `UNI_API_KEY`

**Q: 提示"主题路径不存在"错误**  
A: 确认已运行 `mp3toscripts_faster.py` 并生成了相应的SRT文件

**Q: 翻译速度很慢**
A: 可以调整 `--batch_size` 参数来优化并发数量

**Q: 某些文件翻译失败**
A: 检查网络连接和API额度，脚本会显示失败的文件列表 