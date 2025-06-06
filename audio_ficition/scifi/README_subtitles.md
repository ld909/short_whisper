# NVIDIA ASR 字幕生成器使用指南

## 脚本名称
`generate_subtitles_with_nvasr.py` - 使用 NVIDIA NeMo ASR 模型生成字幕文件

## 功能描述
- 🎙️ 使用 NVIDIA NeMo ASR 进行语音识别
- 📝 生成 word-level 和 segment-level SRT 字幕文件
- 🔄 支持断点续传，跳过已生成的字幕
- 🗂️ 自动排除 macOS 生成的点文件
- ⚡ 智能环境检测和启动

## 环境要求
```bash
# 创建并激活 nvasr 环境
conda create -n nvasr python=3.8
conda activate nvasr
pip install nemo_toolkit[asr]
```

## 输入文件路径
- 音频文件: `/media/dhl/audio/scifi/mp3_merge/[故事索引]/story.mp3`

## 输出文件路径
- Word-level 字幕: `/mnt/dhl/audio/scifi/word_level_srt/[故事索引].srt`
- Segment-level 字幕: `/mnt/dhl/audio/scifi/seg_level_srt/[故事索引].srt`

## 使用方法

### 基本使用
```bash
python generate_subtitles_with_nvasr.py
```

### 强制重新处理（忽略已有字幕文件）
```bash
python generate_subtitles_with_nvasr.py -f
```

### 指定处理范围
```bash
# 处理故事 1-10
python generate_subtitles_with_nvasr.py --start 1 --end 10

# 只处理故事 5
python generate_subtitles_with_nvasr.py --story 5
```

### 指定 ASR 模型
```bash
python generate_subtitles_with_nvasr.py --model nvidia/parakeet-tdt-0.6b-v2
```

### 组合使用
```bash
python generate_subtitles_with_nvasr.py -f --start 1 --end 10 --model nvidia/parakeet-tdt-0.6b-v2
```

## 输出示例

### Word-level SRT 格式
```
1
00:00:00,000 --> 00:00:00,500
在

2
00:00:00,500 --> 00:00:01,000
遥远

3
00:00:01,000 --> 00:00:01,500
的
```

### Segment-level SRT 格式
```
1
00:00:00,000 --> 00:00:05,000
在遥远的未来，人类已经踏上了星际征程。

2
00:00:05,000 --> 00:00:10,000
科技的发展让我们能够探索银河系的每一个角落。
```

## 断点续传特性
- ✅ 自动检测已存在的字幕文件
- 🔄 只处理缺失或损坏的字幕
- 📊 显示处理进度和统计信息
- 💾 保存详细的处理日志

## 处理日志
脚本会生成详细的处理日志：`/mnt/dhl/audio/scifi/subtitle_generation_progress.json`

## 注意事项
1. 需要 NVIDIA GPU 支持
2. 首次运行会下载 ASR 模型（较大文件）
3. 处理时间取决于音频长度和 GPU 性能
4. 建议在充足的磁盘空间下运行

## 故障排除

### 环境问题
```bash
# 检查 conda 环境
conda env list

# 重新创建环境
conda remove -n nvasr --all
conda create -n nvasr python=3.8
conda activate nvasr
pip install nemo_toolkit[asr]
```

### GPU 问题
```bash
# 检查 GPU 状态
nvidia-smi

# 检查 CUDA 版本
nvcc --version
```

### 音频文件问题
确保音频文件路径正确且文件大小 > 1MB
```bash
ls -la /media/dhl/audio/scifi/mp3_merge/*/story.mp3
``` 