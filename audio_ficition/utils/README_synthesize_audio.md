# 多主题音频合成脚本使用说明

## 📖 概述

`synthesize_audio.py` 是一个功能强大的多主题音频合成脚本，使用 f5-tts 将 `chunk_stories.py` 输出的文本块合成为高质量的音频文件。

## 🔧 系统要求

- **操作系统**: 仅支持 Ubuntu Linux 系统
- **Python环境**: Python 3.8+
- **依赖库**: f5-tts, torch, torchaudio 等
- **硬件**: 建议使用GPU加速

## 📚 支持的主题

| 主题ID | 中文名称 | 描述 |
|--------|----------|------|
| `scifi` | 科幻 | 科幻故事，包含未来科技、太空探索、时间旅行等元素 |
| `thriller` | 惊悚 | 惊悚故事，包含紧张刺激、悬念等元素 |
| `horror` | 恐怖 | 恐怖故事，包含惊悚、悬疑、超自然等元素 |
| `romance` | 爱情 | 爱情故事，包含浪漫情节、感情发展等元素 |
| `fantasy` | 奇幻 | 奇幻故事，包含魔法、龙、精灵等奇幻元素 |

## 📁 目录结构

### 输入目录
```
/home/dhl/Documents/audio/chunks/
├── scifi/
│   ├── 1/
│   │   ├── 1.txt
│   │   ├── 2.txt
│   │   └── ...
│   ├── 2/
│   └── ...
├── thriller/
├── horror/
├── romance/
└── fantasy/
```

### 输出目录
```
/home/dhl/Documents/audio/mp3_clips/
├── scifi/
│   ├── 1/
│   │   ├── 1.mp3
│   │   ├── 2.mp3
│   │   └── ...
│   ├── 2/
│   └── ...
├── thriller/
├── horror/
├── romance/
└── fantasy/
```

## 🚀 使用方法

### 基本用法

```bash
# 处理所有默认主题
python synthesize_audio.py

# 处理指定主题
python synthesize_audio.py --theme scifi

# 处理多个主题
python synthesize_audio.py --theme scifi,horror,fantasy
```

### 预览模式

```bash
# 预览模式 - 查看将要处理的文件
python synthesize_audio.py --preview

# 预览指定主题
python synthesize_audio.py --preview --theme scifi
```

### 断点续传控制

```bash
# 默认启用断点续传（跳过已存在的有效文件）
python synthesize_audio.py

# 禁用断点续传（重新处理所有文件）
python synthesize_audio.py --no-resume

# 强制重新生成所有文件
python synthesize_audio.py --force-regenerate
```

### 自定义配置

```bash
# 指定自定义输入输出目录
python synthesize_audio.py \
  --input-base-dir /path/to/chunks \
  --output-base-dir /path/to/output

# 指定参考音频文件
python synthesize_audio.py --ref-audio /path/to/reference.mp3

# 指定模型
python synthesize_audio.py --model F5TTS_v1_Base

# 禁用代理
python synthesize_audio.py --no-proxy
```

### 查看帮助

```bash
# 查看所有支持的主题
python synthesize_audio.py --list-themes

# 查看完整帮助信息
python synthesize_audio.py --help
```

## 🔄 断点续传功能

脚本内置智能断点续传功能：

1. **自动扫描已完成文件**: 启动时自动扫描输出目录，识别已存在的有效音频文件
2. **文件有效性检查**: 检查文件大小、格式等，自动删除损坏的文件
3. **进度显示**: 显示完成进度、待处理文件数量等统计信息
4. **智能跳过**: 跳过已处理的文件，只处理新增或失败的文件

## 🚫 自动文件过滤

脚本会自动排除Mac系统产生的文件：

- 以 `.` 开头的隐藏文件（如 `.DS_Store`）
- 以 `._` 开头的临时文件
- 非txt格式的文件

## 📊 统计报告

处理完成后，脚本会显示详细的统计报告：

```
=== 🎉 处理完成总结 ===
📊 处理统计:
  - 文件总数: 2254 个
  - 成功处理: 1251 个
  - 处理失败: 0 个
  - 跳过文件: 1003 个
  - 成功率: 100.0%

📋 各主题详情:
  - 科幻: 成功 1251 个，失败 0 个，跳过 1003 个
  - 惊悚: 成功 850 个，失败 0 个，跳过 600 个
  ...

📝 音频文件已保存到: /home/dhl/Documents/audio/mp3_clips
📁 目录结构: mp3_clips/{theme}/{story_index}/{chunk_index}.mp3
```

## ⚡ 性能优化

- **GPU加速**: 自动使用GPU进行音频合成
- **智能等待**: 每个文件处理后等待2秒，避免GPU过热
- **代理支持**: 支持代理下载模型文件
- **错误处理**: 完善的错误处理机制，避免中断

## 🐛 故障排除

### 常见问题

1. **系统检查失败**
   ```bash
   ❌ 此脚本只能在Ubuntu系统上运行！
   ```
   - 确保在Ubuntu系统上运行脚本

2. **找不到输入文件**
   ```bash
   ❌ [科幻] 输入目录不存在: /home/dhl/Documents/audio/chunks/scifi
   ```
   - 确保先运行 `chunk_stories.py` 生成文本块
   - 检查输入目录路径是否正确

3. **参考音频文件缺失**
   ```bash
   ❌ 参考音频文件不存在: /path/to/ref_audio.mp3
   ```
   - 确保参考音频文件存在且可访问
   - 使用 `--ref-audio` 参数指定正确路径

4. **GPU内存不足**
   - 减少并发处理数量
   - 检查GPU内存使用情况
   - 重启脚本释放显存

### 调试技巧

1. **使用预览模式**: 先用 `--preview` 查看将要处理的文件
2. **单主题测试**: 使用 `--theme scifi` 测试单个主题
3. **检查日志**: 注意观察终端输出的详细日志信息
4. **强制重新生成**: 使用 `--force-regenerate` 重新生成有问题的文件

## 📋 命令行参数完整列表

| 参数 | 描述 | 默认值 |
|------|------|--------|
| `--theme`, `-t` | 要处理的主题（逗号分隔） | 所有主题 |
| `--input-base-dir` | 输入基础目录 | `/home/dhl/Documents/audio/chunks` |
| `--output-base-dir` | 输出基础目录 | `/home/dhl/Documents/audio/mp3_clips` |
| `--ref-audio` | 参考音频文件路径 | 默认参考音频 |
| `--model` | f5-tts模型名称 | `F5TTS_v1_Base` |
| `--preview` | 预览模式 | False |
| `--force-regenerate` | 强制重新生成 | False |
| `--no-resume` | 禁用断点续传 | False |
| `--proxy` | 启用代理 | True |
| `--no-proxy` | 禁用代理 | False |
| `--list-themes` | 列出支持的主题 | False |
| `--help` | 显示帮助信息 | False |

## 📝 使用建议

1. **首次运行**: 建议先使用预览模式查看要处理的文件
2. **批量处理**: 可以分批处理主题，避免一次性处理过多文件
3. **定期检查**: 定期检查输出文件的质量和完整性
4. **备份重要文件**: 定期备份生成的音频文件
5. **监控资源**: 注意监控GPU温度和内存使用情况

## 🔗 相关脚本

- `chunk_stories.py`: 生成文本块（本脚本的输入来源）
- `generate_publish_excel.py`: 生成发布表格
- `auto_youtube_publish.py`: 自动发布到YouTube

---

�� 如有问题或建议，请联系开发团队。 