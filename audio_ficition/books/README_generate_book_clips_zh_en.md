# 书籍 1080p MP4 Clip 生成器 - 中英文支持版本

## 📖 功能说明

这个脚本用于生成书籍的 1080p MP4 宣传片段，现在已支持中文和英文两种语言。

### 🎬 视频布局
- **左半边**: 静态封面图片 (来自 upscale_book_thumbnails.py 输出)
- **右半边上部分**: 书籍标题 (白色字体，黑色背景)
- **右半边下部分**: 放大的 MP4 素材 (来自 assets 目录)
- **右侧视频叠加**: 书籍摘要文字 (绿色，根据语言显示不同文字)

## 🌍 多语言支持

### 英文 (en)
- 摘要文字: "Book summary"
- 字体目录: `audio_ficition/books/font/en/`
- 推荐字体: Merriweather 或其他 M 开头字体

### 中文 (zh)
- 摘要文字: "书籍摘要"
- 字体目录: `audio_ficition/books/font/zh/`
- 推荐字体: 任何可用的中文字体

## 📁 路径配置

参考 `merge_book_audio.py` 的路径配置：

### 输入路径
```
/mnt/dhl/audio/books/{lang}/thumbnails_large/  # 超分封面图片
/mnt/dhl/audio/books/{lang}/info/              # 书籍信息JSON
audio_ficition/books/assets/                   # 背景视频
audio_ficition/books/font/{lang}/              # 字体文件
```

### 输出路径
```
/mnt/dhl/audio/books/{lang}/1080_clips/        # 生成的MP4文件
```

## 🔧 系统要求

- **操作系统**: 仅支持 Ubuntu/Linux 系统
- **依赖软件**: FFmpeg
- **Python库**: PIL, opencv-python, tqdm

## 📝 使用方法

### 基础使用
```bash
# 处理英文书籍 (默认)
python generate_book_clips.py

# 处理中文书籍
python generate_book_clips.py --language zh
```

### 高级选项
```bash
# 指定字体大小
python generate_book_clips.py --language zh --font-size 56

# 强制重新处理
python generate_book_clips.py --language en --force

# 启用调试模式
python generate_book_clips.py --language zh --debug

# 布局优化
python generate_book_clips.py --video-width 0.4 --video-center --language en

# 字体设置
python generate_book_clips.py --font-weight bold --language zh
python generate_book_clips.py --force-single-line --language en

# 摘要文字设置
python generate_book_clips.py --summary-font-size 30 --language zh
python generate_book_clips.py --no-book-summary --language en
```

## 🧪 配置测试

在使用前，建议先运行测试脚本验证配置：

```bash
python test_book_clips_config.py
```

这会检查：
- 系统兼容性
- 路径配置
- 字体文件
- 背景视频
- 目录结构

## 📦 准备工作

### 1. 字体准备
确保字体文件存在：
```
audio_ficition/books/font/en/     # 英文字体 (如 Merriweather-*.ttf)
audio_ficition/books/font/zh/     # 中文字体 (如 *.ttf)
```

### 2. 背景视频
确保背景视频存在：
```
audio_ficition/books/assets/plate_upscaled.mp4
```

### 3. 书籍素材
确保书籍素材已准备：
```bash
# 先运行超分脚本生成封面
python upscale_book_thumbnails.py --language en
python upscale_book_thumbnails.py --language zh
```

## 📊 输出格式

- **分辨率**: 1920x1080 (1080p)
- **格式**: MP4
- **编码**: H.264
- **命名**: `{uuid}.mp4`

## 🚀 批量处理示例

### 处理所有英文书籍
```bash
python generate_book_clips.py \
  --language en \
  --font-size 48 \
  --video-width 0.5 \
  --summary-font-size 24 \
  --debug
```

### 处理所有中文书籍
```bash
python generate_book_clips.py \
  --language zh \
  --font-size 52 \
  --video-width 0.4 \
  --summary-font-size 28 \
  --summary-right-margin 20 \
  --debug
```

## ⚠️ 注意事项

1. **系统限制**: 只支持 Ubuntu/Linux 系统
2. **路径依赖**: 依赖正确的目录结构和文件位置
3. **字体要求**: 确保对应语言的字体文件存在
4. **断点续传**: 默认跳过已存在的文件，使用 `--force` 强制重新处理
5. **Mac文件**: 自动跳过以点开头的 Mac 系统文件

## 🔍 故障排除

### 1. 字体问题
```bash
# 检查字体目录
ls -la audio_ficition/books/font/en/
ls -la audio_ficition/books/font/zh/

# 测试字体配置
python test_book_clips_config.py
```

### 2. 路径问题
确保路径结构正确：
```
/mnt/dhl/audio/books/
├── en/
│   ├── thumbnails_large/
│   ├── info/
│   └── 1080_clips/
└── zh/
    ├── thumbnails_large/
    ├── info/
    └── 1080_clips/
```

### 3. FFmpeg 问题
```bash
# 检查 FFmpeg 安装
ffmpeg -version

# 安装 FFmpeg (如果需要)
sudo apt update && sudo apt install ffmpeg
```

## 📈 性能优化

- 使用硬件编码器 (如果可用)
- 并行处理多个书籍
- 预合成静态部分以提高效率
- 智能标题溢出处理

## 🎯 最佳实践

1. **测试优先**: 先运行配置测试确保环境正确
2. **分批处理**: 大量书籍建议分批处理
3. **监控日志**: 使用 `--debug` 模式监控处理过程
4. **备份检查**: 处理前确保重要文件已备份

---

✨ **享受中英文书籍 MP4 Clip 的制作过程！** 