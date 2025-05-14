# 短视频生成工具集

这个代码库包含一系列用于自动生成、处理和上传短视频的Python脚本工具。

## 字幕与音频同步测试工具

当视频中的字幕与音频不同步时，使用以下工具检测问题：

```bash
# 基本检查
python video_subtitle_sync_test.py -c <频道名> -l <语言> -f <文件名>

# 详细分析
python video_subtitle_sync_test.py -c <频道名> -l <语言> -f <文件名> --verbose --analyze-all

# 提取特定时间段进行分析（例如10-20秒处的片段）
python video_subtitle_sync_test.py -c <频道名> -l <语言> -f <文件名> --extract-section 10-20
```

功能说明:
- 检查文件时长一致性：比较原始MP3、无声视频、带字幕视频和最终视频的时长
- 分析SRT字幕时间戳：验证字幕是否覆盖整个音频，检查字幕间隔
- 音频语音模式分析：将音频强度与字幕时间进行对比，检测是否同步
- 问题区域提取：从视频中提取特定时间段进行详细分析

依赖：
```bash
pip install pysrt pydub matplotlib
```

## 主要处理流程

1. generate_subtitles.py: 从文本文件生成SRT字幕文件
2. add_subtitles_to_mp4.py: 为无声视频添加字幕
3. merge_mp4_mp3.py: 将带字幕的视频与音频合并成最终视频

## 视频字幕添加工具

这个脚本用于给视频文件自动添加SRT字幕。

## 功能

- 批量处理目录中的所有MP4视频文件
- 自动查找同名的SRT字幕文件
- 将字幕烧录到视频中生成新文件

## 依赖安装

使用以下命令安装所需的依赖：

```bash
pip install moviepy pysrt argparse
```

## 使用方法

1. 基本用法（使用默认目录）：

```bash
python add_sub_test.py
```

2. 指定目录：

```bash
python add_sub_test.py --dir /path/to/your/videos
```

## 注意事项

- 脚本会在同一目录下生成带有"_subbed"后缀的新视频文件
- 视频和字幕文件需要同名（仅扩展名不同）
- 字幕样式为白色字体、黑色背景，位于视频底部中央
