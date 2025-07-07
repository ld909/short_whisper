# Beauty视频音乐添加工具

## 功能简介

`add_music_to_beauty_clips.py` 脚本用于为 `merge_beauty_clips.py` 生成的静音4K美颜视频添加背景音乐。

## 主要功能

1. **随机音乐选择**：从 `assets/` 目录中随机选择MP3文件作为背景音乐
2. **智能音频匹配**：自动匹配音频长度到视频长度
   - 音频短于视频：循环拼接音频直到匹配视频长度
   - 音频长于视频：裁剪音频到视频长度
3. **硬件加速**：支持NVIDIA GPU和Intel GPU硬件加速
4. **断点续传**：自动跳过已处理的视频文件
5. **批量处理**：支持单个index或批量处理所有可用视频
6. **文件过滤**：自动排除Mac系统产生的点文件

## 系统要求

- **操作系统**：Ubuntu Linux（仅支持Ubuntu）
- **依赖软件**：
  - ffmpeg（建议支持硬件加速）
  - Python 3.6+
- **硬件建议**：
  - NVIDIA GPU（推荐，用于硬件加速）
  - 或 Intel集成显卡

## 目录结构

```
/mnt/dhl/beauty/
├── mp4_silent/          # 输入：静音视频文件
│   ├── 1.mp4
│   ├── 2.mp4
│   └── ...
└── mp4_music/           # 输出：带音乐的视频文件
    ├── 1.mp4
    ├── 2.mp4
    └── ...

/home/dhl/Documents/short_whisper/beauty/
└── assets/              # 音乐素材目录
    ├── Charm - Anno Domini Beats.mp3
    ├── Mas Cafe - Casa Rosa.mp3
    └── ...
```

## 使用方法

### 1. 处理单个视频

```bash
# 处理指定index的视频
python add_music_to_beauty_clips.py --index 1

# 强制重新处理（忽略已存在的输出文件）
python add_music_to_beauty_clips.py --index 2 --force

# 自定义背景音乐音量
python add_music_to_beauty_clips.py --index 3 --volume 0.3
```

### 2. 批量处理所有视频

```bash
# 处理所有可用的视频（默认模式）
python add_music_to_beauty_clips.py

# 强制重新处理所有视频
python add_music_to_beauty_clips.py --force

# 自定义音量进行批量处理
python add_music_to_beauty_clips.py --volume 0.15 --force
```

### 3. 命令行参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--index` | int | 无 | 指定要处理的index。不指定时处理所有可用的index |
| `--force` | flag | False | 强制重新处理（忽略断点续传） |
| `--volume` | float | 0.2 | 背景音乐音量 (0.0-1.0) |

## 音频处理策略

### 1. 音频循环拼接
当背景音乐时长短于视频时长时：
- 计算需要循环的次数
- 使用ffmpeg的`aloop`滤镜进行无缝循环
- 精确裁剪到视频长度

### 2. 音频裁剪
当背景音乐时长长于视频时长时：
- 从音频开头裁剪到视频长度
- 保持音频质量不变

### 3. 音量控制
- 默认音量：0.2（20%）
- 推荐范围：0.1-0.3
- 避免音乐盖过原始音频内容

## 硬件加速优化

### NVIDIA GPU加速
- 自动检测NVIDIA GPU
- 使用 `h264_nvenc` 编码器
- 显著提高处理速度

### Intel GPU加速  
- 支持Intel集成显卡
- 使用 `h264_qsv` 或 `vaapi` 编码器
- 适合没有独立显卡的设备

### CPU软件编码
- 当无可用GPU时自动回退
- 使用 `libx264` 编码器
- 处理速度较慢但兼容性好

## 输出质量参数

- **视频编码**：H.264
- **音频编码**：AAC 128kbps
- **像素格式**：YUV420P（最佳兼容性）
- **质量参数**：CRF 18（高质量）
- **优化设置**：支持流媒体快速播放

## 错误处理

### 1. 常见错误及解决方案

**错误**：系统不支持
```
❌ 错误：此脚本只支持Ubuntu系统
```
**解决**：只能在Ubuntu Linux系统上运行

**错误**：未找到ffmpeg
```
❌ 错误：未找到ffmpeg命令
```
**解决**：安装ffmpeg
```bash
sudo apt update && sudo apt install ffmpeg
```

**错误**：未找到输入文件
```
❌ 错误：mp4_silent目录不存在
```
**解决**：先运行 `merge_beauty_clips.py` 生成静音视频

**错误**：未找到音乐文件
```
❌ 错误：assets目录中未找到MP3文件
```
**解决**：确保 `assets/` 目录中有MP3文件

### 2. GPU加速失败处理
- 脚本会自动检测GPU失败并回退到CPU编码
- 不影响正常功能，只是处理速度较慢

## 性能优化建议

1. **使用GPU加速**：安装NVIDIA驱动或确保Intel GPU可用
2. **音乐文件质量**：使用高质量MP3文件（320kbps推荐）
3. **存储性能**：使用SSD存储提高IO性能
4. **内存要求**：建议16GB以上内存用于4K视频处理

## 工作流程集成

完整的Beauty视频处理流程：

1. **提取帧** → `extract_video_frames.py`
2. **人脸超分** → `face_sr_frames.py` 
3. **帧合并** → `merge_beauty_clips.py`
4. **添加音乐** → `add_music_to_beauty_clips.py` ⭐
5. **后续处理** → 上传、分享等

## 注意事项

1. **版权问题**：确保使用的音乐文件有合法使用权
2. **文件命名**：视频文件必须以数字命名（如1.mp4, 2.mp4）
3. **存储空间**：4K视频文件较大，确保有足够存储空间
4. **处理时间**：具体时间取决于视频长度和硬件性能

## 版权声明

本工具仅用于技术学习和个人使用，使用者需自行确保音乐文件的合法性。 