# GPU优化字幕处理系统

## 🚀 主要优化特性

你的 `add_subtitles_to_videos.py` 脚本已经完全重写为GPU优化并行处理版本，主要包含以下特性：

### 1. 🔥 GPU并行处理
- **多流并行**：同时处理多个视频文件，充分利用GPU资源
- **智能并行数计算**：根据GPU内存自动计算最优并行数
- **内存监控**：实时监控GPU内存使用情况

### 2. ⚡ 激进GPU参数优化
- **NVENC最大化设置**：使用最激进的编码参数
- **GPU缓存优化**：增加GPU帧缓存，减少CPU-GPU数据传输
- **多编码器支持**：支持NVENC、VideoToolbox、AMF等硬件编码器

### 3. 📊 实时监控和调优
- **GPU使用率监控**：实时显示GPU内存和利用率
- **性能基准测试**：自动测试最佳并行数
- **智能建议系统**：根据使用情况提供优化建议

## 🎯 使用方法

### 基础GPU使用
```bash
# GPU加速模式（保守设置）
python add_subtitles_to_videos.py --gpu

# GPU最大化模式（推荐）
python add_subtitles_to_videos.py --gpu-max

# 手动设置并行数
python add_subtitles_to_videos.py --gpu --gpu-parallel 6
```

### 实时监控模式
```bash
# 启用GPU监控，实时查看GPU使用情况
python add_subtitles_to_videos.py --gpu-max --gpu-monitor

# 带监控的处理特定范围
python add_subtitles_to_videos.py --gpu-max --gpu-monitor --start 1 --end 20
```

### GPU性能测试
```bash
# 快速GPU测试
python add_subtitles_to_videos.py --test-gpu

# 详细GPU信息和建议
python add_subtitles_to_videos.py --debug-gpu

# 性能基准测试（推荐先运行）
python add_subtitles_to_videos.py --benchmark-gpu
```

### 组合使用示例
```bash
# 完整的GPU优化处理
python add_subtitles_to_videos.py --gpu-max --gpu-monitor --force --start 1 --end 50

# 重新处理所有文件，最大化GPU利用率
python add_subtitles_to_videos.py --gpu-max --gpu-monitor -f
```

## 📈 性能提升效果

### 你的GPU：NVIDIA GeForce RTX 3060 (12GB)
- **建议并行数：3（保守）/ 5（最大化）**
- **预期加速比：3-5倍**
- **适合处理：1080p/4K视频字幕烧录**

### 性能对比（预估）
| 模式 | 并行数 | 预期速度提升 | GPU利用率 |
|------|--------|--------------|-----------|
| CPU模式 | 1 | 1x (基准) | 0% |
| GPU标准 | 3 | 3-4x | 60-70% |
| GPU最大化 | 5 | 4-6x | 80-95% |

## 🔍 GPU监控信息解读

### 实时监控显示
```
🚀 GPU状态: 内存 8524/12288MB (69.4%)
```
- **内存使用**：当前使用的GPU内存
- **利用率**：GPU内存使用百分比

### 处理完成后统计
```
🔍 GPU平均利用率: 87.3%
🚀 GPU并行效率: 92.1% (实际加速: 4.6x)
💡 GPU优化建议: GPU利用率很高(87.3%)，当前设置已接近最优
```

## ⚙️ GPU参数优化详解

### NVENC编码器优化
- **preset**: `p1` (最快预设)
- **tune**: `ll` (低延迟)
- **rc**: `vbr` (可变比特率)
- **surfaces**: `32` (增加编码表面数)
- **async_depth**: `4` (异步深度)

### 内存优化
- **extra_hw_frames**: `8` (增加GPU帧缓存)
- **hwaccel_output_format**: `cuda` (GPU格式输出)
- **bufsize**: 优化缓冲区大小

## 🛠️ 故障排除

### GPU利用率低（<70%）
```bash
# 增加并行数
python add_subtitles_to_videos.py --gpu --gpu-parallel 6

# 使用最大化模式
python add_subtitles_to_videos.py --gpu-max
```

### 内存不足错误
```bash
# 减少并行数
python add_subtitles_to_videos.py --gpu --gpu-parallel 2

# 使用保守模式
python add_subtitles_to_videos.py --gpu
```

### 性能基准测试
```bash
# 运行完整测试找到最佳设置
python add_subtitles_to_videos.py --benchmark-gpu
```

## 💡 最佳实践建议

1. **首次使用**：先运行 `--debug-gpu` 查看GPU信息
2. **性能测试**：运行 `--benchmark-gpu` 找到最佳并行数
3. **日常使用**：使用 `--gpu-max --gpu-monitor` 获得最佳性能
4. **大批量处理**：搭配 `--force` 重新处理所有文件
5. **监控优化**：根据GPU利用率调整并行数

## 🎯 预期效果

根据你的RTX 3060配置，使用GPU最大化模式预期可以获得：
- **4-6倍速度提升**
- **GPU利用率80-95%**
- **同时处理3-5个视频**
- **大幅减少处理时间**

现在你的GPU资源可以得到充分利用！🚀 