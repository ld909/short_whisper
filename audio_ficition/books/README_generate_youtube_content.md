# YouTube内容生成器统一脚本

## 概述

`generate_youtube_content.py` 是一个统一的脚本，整合了三个YouTube内容生成功能：

1. **YouTube视频标题生成** (原 `generate_youtube_titles.py`)
2. **YouTube视频描述生成** (原 `generate_youtube_descriptions.py`)  
3. **YouTube hashtag标签生成** (原 `generate_youtube_hashtags.py`)

## 主要特性

### 🔄 Pipeline模式
- **推荐使用**：一次性生成所有类型的内容
- 按依赖顺序处理：标题 → 描述 → 标签
- 自动跳过已存在的内容，支持断点续传

### 🎯 单一类型模式
- 可单独生成某种特定类型的内容
- 适用于只需要更新特定类型内容的情况

### 🌍 多语言支持
- 支持中文(`zh`)和英文(`en`)两种语言主题
- 不同语言使用相应的AI提示词和处理逻辑

### 🤖 智能依赖检查
- 自动检查每种内容类型的前置依赖
- 缺少依赖时给出明确提示

## 安装要求

```bash
pip install google-genai
pip install tqdm
```

## 环境变量

```bash
export UNI_API_KEY='your-api-key'
```

## 使用方法

### 基础用法

#### Pipeline模式（推荐）
```bash
# 生成所有类型内容 - 英文
python generate_youtube_content.py --lang en --type all

# 生成所有类型内容 - 中文
python generate_youtube_content.py --lang zh --type all
```

#### 单一类型模式
```bash
# 仅生成标题
python generate_youtube_content.py --lang en --type titles

# 仅生成描述
python generate_youtube_content.py --lang zh --type descriptions

# 仅生成标签
python generate_youtube_content.py --lang en --type hashtags
```

### 高级选项

```bash
# 处理指定数量的文件
python generate_youtube_content.py --lang en --type all --count 10

# 强制重新生成已存在的内容
python generate_youtube_content.py --lang zh --type all --force

# 处理指定UUID的书籍
python generate_youtube_content.py --lang en --type descriptions --uuid abc123-def456-789

# 启用调试模式
python generate_youtube_content.py --lang en --type all --debug

# 检查当前处理状态
python generate_youtube_content.py --lang zh --status
```

## 输入依赖

### 标题生成依赖
- 📁 书籍信息文件：`{base_path}/books/{lang}/info/{uuid}.json`
- 📄 书籍总结文件：`{base_path}/books/{lang}/summary/{uuid}.txt` (可选，用于AI生成)

### 描述生成依赖
- 🎥 MP4视频文件：`{base_path}/books/{lang}/mp4_with_audio/{uuid}.mp4`
- 📄 书籍总结文件：`{base_path}/books/{lang}/summary/{uuid}.txt`

### 标签生成依赖
- 📝 YouTube描述文件：`{base_path}/books/{lang}/youtube_description/{uuid}.txt`

## 输出文件

- 📺 YouTube标题：`{base_path}/books/{lang}/youtube_titles/{uuid}.txt`
- 📝 YouTube描述：`{base_path}/books/{lang}/youtube_description/{uuid}.txt`
- 🏷️ YouTube标签：`{base_path}/books/{lang}/youtube_hashtags/{uuid}.txt`

## 系统路径配置

脚本会根据系统类型自动选择路径：

- **Intel Mac**: `/Volumes/dhl/audio`
- **Apple Silicon Mac**: `/Users/donghaoliu/Documents/audio`
- **Linux/Ubuntu**: `/media/dhl/audio`
- **环境变量**: `AUDIO_BASE_DIR`

## 处理流程

### Pipeline模式处理顺序

1. **标题生成**
   - 检查书籍信息文件
   - 加载书籍总结（如有）
   - 使用AI生成或使用简化格式
   - 保存标题文件

2. **描述生成**
   - 检查书籍总结文件
   - 使用AI基于总结生成描述
   - 保存描述文件

3. **标签生成**
   - 检查描述文件
   - 使用AI基于描述生成hashtag
   - 保存标签文件

### 依赖关系图

```
MP4文件 → 标题生成
     ↓
书籍总结 → 描述生成
     ↓
YouTube描述 → 标签生成
```

## AI模型配置

- **标题生成**: Gemini-1.5-Flash (温度: 0.8)
- **描述生成**: Gemini-2.5-Flash-Preview (带思考预算: 1024)
- **标签生成**: Gemini-2.5-Flash-Preview (带思考预算: 512)

## 错误处理

- ✅ 自动跳过Mac系统文件（`.DS_Store`等）
- ✅ 智能重试机制（最多3次）
- ✅ 详细的错误提示和建议
- ✅ 断点续传支持

## 性能优化

- 🚀 API调用间隔控制，避免请求过快
- 📊 进度条显示处理状态
- 💾 文件大小验证确保内容有效
- 🔍 依赖检查避免无效处理

## 使用示例

### 日常使用（推荐）
```bash
# 处理英文书籍的所有YouTube内容
python generate_youtube_content.py --lang en --type all

# 处理中文书籍的所有YouTube内容  
python generate_youtube_content.py --lang zh --type all
```

### 特定场景
```bash
# 只更新标题（比如改进了标题生成算法）
python generate_youtube_content.py --lang en --type titles --force

# 处理新增的5本书
python generate_youtube_content.py --lang zh --type all --count 5

# 检查当前进度
python generate_youtube_content.py --lang en --status
```

## 与原脚本的关系

此统一脚本替代了以下三个独立脚本：
- `generate_youtube_titles.py`
- `generate_youtube_descriptions.py` 
- `generate_youtube_hashtags.py`

原脚本仍然可以独立使用，但建议使用此统一脚本以获得更好的依赖管理和处理效率。

## 故障排除

### 常见问题

1. **缺少API密钥**
   ```bash
   export UNI_API_KEY='your-api-key'
   ```

2. **依赖文件缺失**
   - 检查前置脚本是否已运行
   - 使用 `--status` 参数检查文件状态

3. **AI生成失败**
   - 检查网络连接
   - 确认API密钥有效
   - 查看是否达到API限额

4. **路径问题**
   - 确认系统类型对应的路径存在
   - 可设置 `AUDIO_BASE_DIR` 环境变量

### 调试模式

```bash
python generate_youtube_content.py --lang en --type all --debug
```

调试模式会输出详细的处理信息，帮助定位问题。

## 更新日志

### v1.0.0
- 首次发布统一脚本
- 整合三个YouTube内容生成功能
- 支持Pipeline模式和单一类型模式
- 添加智能依赖检查和错误处理
- 支持中英文双语言 