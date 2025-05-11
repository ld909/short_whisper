# 视频字幕添加工具

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
