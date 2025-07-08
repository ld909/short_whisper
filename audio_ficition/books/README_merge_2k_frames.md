# Beauty 2K视频合并工具

## 功能概述

`merge_2k_frames.py` 是一个用于将RealESRGAN超分辨率处理后的帧合并为2K MP4视频的工具。

## 主要特性

### 🎯 智能分辨率处理
- **输出分辨率**: 2560x1440 (2K)
- **帧率**: 24fps
- **调整策略**: 图像上下顶格，左右添加等宽黑边
- **保持宽高比**: 自动缩放以适应2K分辨率

### 🚀 系统优化
- **Ubuntu系统**: 自动使用GPU加速 (h264_nvenc)
- **其他系统**: 使用CPU模式 (libx264)
- **智能检测**: 自动检测系统类型和GPU支持

### 📁 路径配置
```
输入路径:
- Ubuntu: /mnt/dhl/beauty/face_sr_frames/[index]/
- Mac: /Volumes/dhl/beauty/face_sr_frames/[index]/
- 其他: /media/dhl/beauty/face_sr_frames/[index]/

输出路径:
- Ubuntu: /mnt/dhl/beauty/merged_2k_videos/[index].mp4
- Mac: /Volumes/dhl/beauty/merged_2k_videos/[index].mp4
- 其他: /media/dhl/beauty/merged_2k_videos/[index].mp4
```

## 使用方法

### 基本用法

```bash
# 处理所有可用的index（推荐）
python merge_2k_frames.py

# 处理单个index
python merge_2k_frames.py --index 1
python merge_2k_frames.py --index 2

# 强制重新处理（忽略断点续传）
python merge_2k_frames.py --force
python merge_2k_frames.py --index 1 --force
```

### 调试模式

```bash
# 查看ffmpeg命令但不执行（调试用）
python merge_2k_frames.py --index 1 --dry-run
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `--index N` | 指定处理的index编号 |
| `--force` | 强制重新处理，忽略已存在的视频 |
| `--dry-run` | 仅显示ffmpeg命令，不执行 |

## 依赖环境

### 必需软件
- **ffmpeg**: 视频处理核心工具
- **python 3.6+**: 运行环境

### 安装依赖
```bash
# Ubuntu
sudo apt update
sudo apt install ffmpeg

# Mac (使用Homebrew)
brew install ffmpeg

# 检查安装
ffmpeg -version
```

### GPU支持（可选）
- **Ubuntu + NVIDIA GPU**: 自动使用GPU加速
- **其他系统**: 使用CPU模式

## 输出质量设置

### 编码参数
- **GPU模式**: h264_nvenc, preset=medium, crf=23
- **CPU模式**: libx264, preset=medium, crf=23
- **像素格式**: yuv420p（兼容性最佳）

### 视频滤镜
```
scale=2560:1440:force_original_aspect_ratio=decrease,pad=2560:1440:(ow-iw)/2:(oh-ih)/2:black
```
- 先缩放到能容纳在2560x1440内的最大尺寸
- 然后添加黑边使其达到精确的2560x1440

## 文件命名支持

脚本智能检测输入文件的命名模式：

### 数字序列模式（推荐）
```
1.jpg, 2.jpg, 3.jpg, ...
```
- 使用ffmpeg的%d模式，效率最高
- 自动检测起始编号

### 通用模式
```
frame_001.jpg, img_01.jpg, ...
```
- 使用glob模式，兼容性最好
- 支持任意命名格式

## 处理流程

1. **系统检测**: 识别操作系统和GPU支持
2. **环境验证**: 检查ffmpeg安装和GPU驱动
3. **文件扫描**: 自动发现可处理的帧目录
4. **输入验证**: 检查帧文件数量和格式
5. **命令构建**: 根据系统和文件情况优化ffmpeg参数
6. **视频合并**: 执行ffmpeg处理并实时监控
7. **结果验证**: 检查输出文件大小和视频信息

## 断点续传

- **自动跳过**: 已存在的视频文件会被自动跳过
- **文件检查**: 验证文件大小（>1KB）确保完整性
- **强制重处理**: 使用`--force`参数可以覆盖已有文件

## 错误处理

### 常见问题

1. **ffmpeg未安装**
   ```
   ❌ 错误：未找到ffmpeg命令
   解决：sudo apt install ffmpeg
   ```

2. **GPU不可用**
   ```
   ⚠️ 警告：未检测到NVIDIA GPU，将回退到CPU模式
   说明：正常现象，会使用CPU编码
   ```

3. **输入目录不存在**
   ```
   ❌ 错误：face_sr_frames目录不存在
   解决：先运行 realesrgan_upscale_frames.py
   ```

4. **无jpg文件**
   ```
   ❌ 错误：输入目录中未找到jpg文件
   解决：检查RealESRGAN处理是否完成
   ```

## 性能优化

### GPU加速 (Ubuntu)
- 使用NVENC硬件编码器
- 显著提升处理速度
- 降低CPU占用

### CPU模式 (其他系统)
- 使用x264软件编码器
- 质量设置优化
- 合理的preset平衡速度和质量

## 示例输出

```bash
🚀 Beauty 2K视频合并工具
==================================================
✅ 系统检查：Ubuntu Linux (GPU加速模式)
✅ ffmpeg 已安装: ffmpeg version 4.4.2
✅ NVIDIA GPU 可用，将使用GPU加速
📂 自动发现 3 个index: [1, 2, 3]
🎯 开始处理 3 个帧目录...

==================== 处理 1/3: index 1 ====================
📁 输入目录: /mnt/dhl/beauty/face_sr_frames/1
📤 输出文件: /mnt/dhl/beauty/merged_2k_videos/1.mp4
✅ 输入帧文件检查通过
📊 jpg文件数量: 240
📏 图像分辨率: 1920x1080
📋 使用数字序列模式：%d.jpg (起始: 1)
🚀 开始合并视频...
🎯 目标分辨率: 2560x1440
🎬 帧率: 24fps
⚙️ 编码模式: GPU (NVENC)
✅ 视频合并完成!
📊 输出文件大小: 125.67 MB
📹 视频信息: 2560x1440, 时长: 10.00秒
✅ index 1 处理成功!
```

## 整合工作流

这个脚本是beauty视频处理流水线的一部分：

```
extract_video_frames.py → realesrgan_upscale_frames.py → merge_2k_frames.py
     提取帧                    超分辨率处理                 合并2K视频
```

完整的处理流程能够将原始视频转换为高质量的2K超分辨率视频。 