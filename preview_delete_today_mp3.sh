#!/bin/bash

# 预览今天创建的视频对应的mp3文件脚本（只查看，不删除）

# 设置路径
TXT_DIR="/Volumes/dhl/buda_videos_youtube/multi_lang_txt"
MP3_DIR="/Volumes/dhl/buda_videos_youtube/multi_lang_mp3"

# 获取今天的日期
TODAY=$(date '+%Y-%m-%d')

echo "============================================================"
echo "预览今天创建的视频对应的mp3文件（只查看，不删除）"
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

echo ""
echo "对应的mp3文件夹详情:"
echo "----------------------------------------"

total_size=0
total_files=0

for video_name in "${TODAY_VIDEOS[@]}"; do
    mp3_path="$MP3_DIR/$video_name"
    
    if [ -d "$mp3_path" ]; then
        echo "📁 $video_name"
        echo "   路径: $mp3_path"
        
        # 计算文件夹大小和文件数量
        if command -v du >/dev/null 2>&1; then
            size=$(du -sh "$mp3_path" 2>/dev/null | cut -f1)
            echo "   大小: $size"
        fi
        
        file_count=$(find "$mp3_path" -type f 2>/dev/null | wc -l)
        echo "   文件数: $file_count"
        
        # 显示子目录（语种）
        echo "   语种目录:"
        for lang_dir in "$mp3_path"/*; do
            if [ -d "$lang_dir" ]; then
                lang_name=$(basename "$lang_dir")
                lang_file_count=$(find "$lang_dir" -name "*.mp3" 2>/dev/null | wc -l)
                echo "     - $lang_name ($lang_file_count 个mp3文件)"
            fi
        done
        
        total_files=$((total_files + file_count))
        echo ""
    else
        echo "⚠️  mp3目录不存在: $video_name"
        echo ""
    fi
done

echo "----------------------------------------"
echo "总计: $total_files 个文件将被删除"
echo ""
echo "💡 如果确认要删除，请运行: ./delete_today_mp3.sh" 