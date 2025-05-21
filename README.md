# 音频增强器 (Audio Enhancer)

这是一个基于Python的音频增强工具，用于改善音频质量。该工具使用动态压缩器来控制音频的动态范围，使音频听起来更加平衡和专业。

## 特性

- 支持MP3和WAV格式的输入文件
- 输出增强后的MP3文件
- 可自定义的压缩器参数：
  - RMS/peak比例
  - 攻击时间
  - 释放时间
  - 阈值
  - 压缩比
  - 拐点半径
  - 补偿增益

## 安装

1. 克隆此仓库
2. 安装依赖项：

```bash
pip install -r requirements.txt
```

## 使用方法

基本用法：

```bash
python audio_enhancer.py input.mp3 output.mp3
```

使用自定义参数：

```bash
python audio_enhancer.py input.mp3 output.mp3 --rms-peak 0.2 --attack 25 --release 100 --threshold -11 --ratio 4 --knee 5 --makeup-gain 7
```

### 参数说明

- `input_file`：输入音频文件路径（MP3或WAV）
- `output_file`：输出音频文件路径（MP3）
- `--rms-peak`：RMS/peak比例（默认：0.2）
- `--attack`：攻击时间（毫秒）（默认：25.0）
- `--release`：释放时间（毫秒）（默认：100.0）
- `--threshold`：阈值（dB）（默认：-11.0）
- `--ratio`：压缩比（默认：4.0）
- `--knee`：拐点半径（dB）（默认：5.0）
- `--makeup-gain`：补偿增益（dB）（默认：7.0）

## 示例

处理WAV文件：

```bash
python audio_enhancer.py input.wav output.mp3
```

处理MP3文件：

```bash
python audio_enhancer.py input.mp3 output.mp3
```

## 默认参数

脚本使用以下默认参数值，这些值基于常见的音频压缩设置：

- RMS/peak: 0.2
- Attack: 25.0 ms
- Release: 100.0 ms
- Threshold: -11.0 dB
- Ratio: 4.0:1
- Knee radius: 5.0 dB
- Makeup gain: 7.0 dB 