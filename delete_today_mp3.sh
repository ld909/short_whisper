#!/bin/bash

# 删除今天创建的视频对应的mp3文件脚本

# 设置路径
TXT_DIR="/Volumes/dhl/buda_videos_youtube/multi_lang_txt"
MP3_DIR="/Volumes/dhl/buda_videos_youtube/multi_lang_mp3"

# 获取今天的日期
TODAY=$(date '+%Y-%m-%d')

echo "============================================================"
echo "删除今天创建的视频对应的mp3文件"
echo "============================================================"
echo "查找日期: $TODAY"
echo ""

# 检查目录是否存在
if [ ! -d "$TXT_DIR" ]; then
    echo "❌ 错误: txt目录不存在: $TXT_DIR"
    exit 1
fi

if [ ! -d "$MP3_DIR" ]; then
    echo "❌ 错误: mp3目录不存在: $MP3_DIR"
    exit 1
fi

# 查找今天创建的视频文件夹
echo "正在查找今天创建的视频文件夹..."
TODAY_VIDEOS=()

# 使用find命令查找今天创建的目录
while IFS= read -r -d '' dir; do
    if [ -d "$dir" ]; then
        dirname=$(basename "$dir")
        # 跳过隐藏目录和特殊目录
        if [[ "$dirname" != .* ]] && [[ "$dirname" != ".." ]]; then
            TODAY_VIDEOS+=("$dirname")
            echo "找到今天创建的视频: $dirname"
        fi
    fi
done < <(find "$TXT_DIR" -maxdepth 1 -type d -newerct "$TODAY" -print0)

# 检查是否找到视频
if [ ${#TODAY_VIDEOS[@]} -eq 0 ]; then
    echo "没有找到今天创建的视频文件夹"
    exit 0
fi

echo ""
echo "找到 ${#TODAY_VIDEOS[@]} 个今天创建的视频:"
for i in "${!TODAY_VIDEOS[@]}"; do
    echo "$((i+1)). ${TODAY_VIDEOS[i]}"
done

# 确认删除
echo ""
read -p "确认要删除这 ${#TODAY_VIDEOS[@]} 个视频的所有mp3文件吗? (y/N): " confirm

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "操作已取消"
    exit 0
fi

# 删除mp3文件夹
echo ""
echo "开始删除mp3文件..."
deleted_count=0

for video_name in "${TODAY_VIDEOS[@]}"; do
    mp3_path="$MP3_DIR/$video_name"
    
    if [ -d "$mp3_path" ]; then
        echo "正在删除: $mp3_path"
        if rm -rf "$mp3_path"; then
            echo "✅ 成功删除: $video_name"
            ((deleted_count++))
        else
            echo "❌ 删除失败: $video_name"
        fi
    else
        echo "⚠️  mp3目录不存在: $video_name"
    fi
done

echo ""
echo "删除完成! 共删除了 $deleted_count 个视频的mp3文件" 