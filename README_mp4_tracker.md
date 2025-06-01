# MP4发布状态跟踪器使用说明

## 功能简介

这个脚本 `generate_mp4_publish_tracker.py` 用于扫描 `merge_mp4_mp3.py` 输出的MP4文件，并生成Excel跟踪表来管理视频发布状态。

## 主要特点

- ✅ 自动扫描所有MP4文件
- ✅ 按语言创建不同的Excel工作表
- ✅ 只添加新文件，不修改已有记录
- ✅ 支持增量更新
- ✅ 跨平台支持（Mac/Linux）

## 安装依赖

```bash
pip install pandas openpyxl
```

## 使用方法

### 1. 基本使用（推荐）

扫描所有频道和语言，生成完整的跟踪表：

```bash
python generate_mp4_publish_tracker.py
```

### 2. 只处理特定频道

```bash
python generate_mp4_publish_tracker.py -c buddha
```

### 3. 自定义输出文件名

```bash
python generate_mp4_publish_tracker.py -o my_video_tracker.xlsx
```

### 4. 查看可用频道和语言

```bash
# 列出所有频道
python generate_mp4_publish_tracker.py --list-channels

# 列出所有语言
python generate_mp4_publish_tracker.py --list-languages
```

### 5. 使用自定义路径

```bash
python generate_mp4_publish_tracker.py --base-path /path/to/your/custom/base
```

## 输出文件格式

生成的Excel文件包含以下结构：

- **工作表**: 每种语言一个工作表（如：chinese, english, spanish 等）
- **列结构**:
  - `MP4名称`: 视频文件名
  - `是否发布`: 是否计划发布（默认值：1）
  - `是否已经发布`: 是否已经发布（默认值：0）

## 使用场景

### 第一次运行
脚本会扫描所有MP4文件并创建新的Excel文件。

### 后续运行（增量更新）
- 脚本只会添加新发现的MP4文件
- 保持已有记录的所有数据不变
- 适合定期运行以跟踪新视频

## 目录结构

脚本会扫描以下目录结构：
```
/media/dhl/buda_videos_youtube/mp4_with_audio/  (Linux)
└── 频道名/
    └── 语言名/
        ├── video1.mp4
        ├── video2.mp4
        └── ...
```

## 注意事项

1. 确保已安装必要的Python库：`pandas` 和 `openpyxl`
2. 脚本会自动检测操作系统并使用对应的路径
3. Excel文件会保存在脚本运行的当前目录
4. 工作表名称会自动截断到31个字符（Excel限制）

## 示例输出

```
检测到系统: Linux
使用基础路径: /media/dhl/buda_videos_youtube
MP4输入目录: /media/dhl/buda_videos_youtube/mp4_with_audio

开始扫描MP4文件...
扫描频道: buddha, dharma

扫描完成:
总计发现 150 个MP4文件
- chinese: 75 个文件
- english: 75 个文件

发现现有跟踪文件: mp4_publish_tracker.xlsx
- 工作表 'chinese': 70 条现有记录
- 工作表 'english': 70 条现有记录

处理语言: chinese
- 现有记录: 70 个
- 发现新文件: 5 个

处理语言: english
- 现有记录: 70 个
- 发现新文件: 5 个

✅ 跟踪文件已更新: mp4_publish_tracker.xlsx
新增 10 个MP4文件记录

处理完成！ 