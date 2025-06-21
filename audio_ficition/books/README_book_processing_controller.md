# 书籍处理流水线控制器使用说明

## 📚 概述

`book_processing_controller.py` 是一个终极自动化控制器脚本，负责按正确顺序执行整个书籍处理流水线的所有9个步骤，从文本块生成到最终视频输出。

## 🔧 功能特性

- **完整流水线自动化**: 一键执行所有9个处理步骤
- **系统兼容性检查**: 自动识别Ubuntu和macOS系统，跳过不兼容步骤
- **智能错误处理**: 包含详细的错误信息和用户交互选项
- **灵活执行模式**: 支持完整流水线、指定步骤、步骤范围执行
- **进度跟踪**: 实时显示执行进度、耗时统计和成功率
- **断点续传支持**: 各个步骤脚本原生支持断点续传
- **调试模式**: 提供详细的调试信息和预览模式

## 📋 流水线步骤

| 步骤 | 脚本名称 | 描述 | 系统要求 | 依赖步骤 |
|------|----------|------|----------|-----------|
| 1 | `chunk_book_summaries.py` | 生成文本块 | 全平台 | 书籍总结文件 |
| 2 | `synthesize_book_audio.py` | 合成音频片段 | 仅Ubuntu | 步骤1 |
| 3 | `merge_book_audio.py` | 合并音频文件 | 仅Ubuntu | 步骤2 |
| 4 | `upscale_book_thumbnails.py` | 封面图片超分 | 全平台 | 封面图片 |
| 5 | `generate_book_clips.py` | 生成视频素材 | 全平台 | 步骤4 |
| 6 | `generate_youtube_descriptions.py` | 生成YouTube描述 | 全平台 | 步骤3或9 |
| 7 | `generate_youtube_hashtags.py` | 生成YouTube标签 | 全平台 | 步骤6 |
| 8 | `generate_youtube_titles.py` | 生成YouTube标题 | 全平台 | 书籍信息 |
| 9 | `merge_clips_with_audio.py` | 合并最终视频 | 全平台 | 步骤3,5 |

## 💻 使用方法

### 基本用法

```bash
# 查看流水线信息
python book_processing_controller.py --info

# 运行完整流水线（推荐）
python book_processing_controller.py --full-pipeline

# 运行指定步骤
python book_processing_controller.py --steps 1,2,3

# 运行步骤范围
python book_processing_controller.py --steps 1-5

# 运行指定步骤范围，跳过某些步骤
python book_processing_controller.py --steps 1-3,5-7
```

### 高级选项

```bash
# 强制重新处理所有文件
python book_processing_controller.py --full-pipeline --force

# 启用调试模式
python book_processing_controller.py --full-pipeline --debug

# 处理指定UUID的书籍
python book_processing_controller.py --uuid 12345678-abcd-efgh-ijkl-123456789012 --full-pipeline

# 组合使用：指定UUID + 强制重新处理 + 调试模式
python book_processing_controller.py --uuid abc123 --steps 1-5 --force --debug
```

### 分段执行示例

```bash
# 仅在Ubuntu上运行音频处理步骤
python book_processing_controller.py --steps 1-3

# 在macOS上运行非音频步骤
python book_processing_controller.py --steps 4-9

# 只生成YouTube相关内容
python book_processing_controller.py --steps 6-8
```

## 🖥️ 系统兼容性

### Ubuntu系统
- **支持所有步骤**: 1-9
- **音频处理**: f5-tts 语音合成功能完整
- **推荐用法**: 完整流水线执行

### macOS系统
- **支持步骤**: 1, 4-9（跳过音频相关步骤2,3）
- **限制**: 无法进行音频合成和合并
- **使用建议**: 先在Ubuntu处理音频，再在macOS处理其他步骤

## 📊 输出说明

### 执行过程输出

```
🖥️  系统类型: Darwin
📁 脚本目录: /path/to/audio_ficition/books
🔥 运行完整流水线（步骤 1-9）

============================================================
🚀 执行步骤 1: 生成文本块
📄 脚本: chunk_book_summaries.py
📝 描述: 将书籍总结分割成适当大小的文本块
============================================================
🔄 执行命令: python chunk_book_summaries.py
... [脚本输出] ...
✅ 步骤 1 执行成功! 耗时: 0:02:15
```

### 最终统计

```
============================================================
📊 流水线执行完成统计
============================================================
⏱️  总耗时: 1:23:45
✅ 成功执行: 7 个步骤
⏭️  跳过执行: 2 个步骤
❌ 执行失败: 0 个步骤
📈 成功率: 100.0%

🎉 流水线执行完美成功!
```

## 🔧 参数说明

### 必选参数（互斥）

- `--full-pipeline`: 运行完整流水线（步骤1-9）
- `--steps STEPS`: 运行指定步骤（如：1,3,5 或 1-5）
- `--info`: 仅显示流水线信息并退出

### 可选参数

- `--force`: 强制重新处理，跳过已存在的文件
- `--debug`: 启用调试模式，显示详细信息
- `--uuid UUID`: 只处理指定UUID的书籍

## ⚠️ 注意事项

### 1. 系统要求

- **Ubuntu**: 需要安装 f5-tts 用于音频合成
- **macOS**: 需要安装 FFmpeg 用于视频处理
- **网络**: 需要稳定网络访问Gemini API（步骤6,7）

### 2. 环境变量

```bash
# 必需的API密钥（用于步骤6,7）
export UNI_API_KEY="your-gemini-api-key"

# 可选的代理设置（用于步骤2）
export http_proxy="http://127.0.0.1:7897"
export https_proxy="http://127.0.0.1:7897"
```

### 3. 前置条件

- 书籍总结文件存在（由 `generate_book_summary.py` 生成）
- 书籍封面图片存在（由 `book_info_scraper.py` 下载）
- 书籍信息JSON文件存在（由 `book_info_scraper.py` 生成）

### 4. 错误处理

- 脚本失败时会提示是否继续执行下一步
- 可以输入 `y/yes/是` 继续，或 `n/no/否` 中止
- 使用 `--debug` 模式可获得更详细的错误信息

## 📁 输出目录结构

```
/Volumes/dhl/audio/books/en/  (macOS Intel)
├── chunks/                   # 步骤1输出：文本块
├── mp3_clips/               # 步骤2输出：音频片段
├── mp3/                     # 步骤3输出：完整音频
├── thumbnails_large/        # 步骤4输出：超分封面
├── 1080_clips/             # 步骤5输出：视频素材
├── youtube_description/     # 步骤6输出：YouTube描述
├── youtube_hashtags/        # 步骤7输出：YouTube标签
├── youtube_titles/          # 步骤8输出：YouTube标题
└── mp4_with_audio/         # 步骤9输出：最终视频
```

## 🚀 最佳实践

### 1. 分系统执行（推荐）

```bash
# 在Ubuntu上执行完整流水线
python book_processing_controller.py --full-pipeline

# 或者分步执行：
# Ubuntu上先处理音频相关
python book_processing_controller.py --steps 1-3
# 然后处理其他步骤
python book_processing_controller.py --steps 4-9
```

### 2. 调试新书籍

```bash
# 使用调试模式处理单本书籍
python book_processing_controller.py --uuid specific-uuid --full-pipeline --debug
```

### 3. 批量重新处理

```bash
# 强制重新处理所有书籍
python book_processing_controller.py --full-pipeline --force
```

### 4. 故障恢复

```bash
# 从指定步骤开始恢复
python book_processing_controller.py --steps 5-9  # 从第5步开始
```

## 🎯 常见使用场景

### 场景1: 新书籍完整处理

```bash
# 一键处理新书籍（Ubuntu环境）
python book_processing_controller.py --full-pipeline
```

### 场景2: 更新已有书籍

```bash
# 重新生成YouTube内容
python book_processing_controller.py --steps 6-8 --force
```

### 场景3: 测试单本书籍

```bash
# 测试指定书籍的完整流程
python book_processing_controller.py --uuid test-uuid --full-pipeline --debug
```

### 场景4: 跨系统协作

```bash
# Step 1: Ubuntu上处理音频
python book_processing_controller.py --steps 1-3

# Step 2: macOS上处理视频和元数据
python book_processing_controller.py --steps 4-9
```

## 🔍 故障排除

### 常见错误

1. **"仅支持Ubuntu系统"**: 在macOS上跳过音频步骤是正常的
2. **"脚本文件不存在"**: 检查脚本目录和文件名
3. **"API密钥未设置"**: 设置 UNI_API_KEY 环境变量
4. **网络连接错误**: 检查代理设置和网络连接

### 调试建议

1. 使用 `--info` 查看系统兼容性
2. 使用 `--debug` 获得详细输出
3. 检查前置文件是否存在
4. 验证环境变量设置

## 📈 性能优化

- 使用SSD存储可显著提升I/O性能
- 确保足够的磁盘空间（每本书籍约1-2GB）
- 在Ubuntu上使用GPU加速音频合成
- 批量处理时考虑系统资源限制 