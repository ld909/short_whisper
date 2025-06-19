# Podcast 语音识别和说话人识别工具

这个工具使用 WhisperX 对音频文件进行高精度语音识别和说话人识别。

## 功能特点

- 🎵 **多格式支持**: 支持 MP3, WAV, M4A, FLAC, OGG 格式
- 🎯 **词级别时间戳**: 提供精确的时间戳信息
- 👥 **说话人识别**: 自动识别不同说话人并分配标签
- 🚫 **智能过滤**: 自动排除 Mac 系统生成的点文件
- ⚡ **GPU 加速**: Linux 系统支持 CUDA GPU 加速
- 📊 **详细统计**: 提供说话人时长和比例统计

## 安装依赖

### 1. 安装 WhisperX

```bash
pip install whisperx
```

### 2. 获取 HuggingFace Token

说话人识别功能需要 HuggingFace Token：

1. 访问 [HuggingFace Settings](https://huggingface.co/settings/tokens)
2. 创建一个新的访问令牌
3. 在运行脚本时使用 `--hf-token` 参数提供

## 使用方法

### 基本用法

```bash
# 处理当前目录的所有音频文件
python podcast_speaker_recognition.py

# 处理指定文件
python podcast_speaker_recognition.py --file t.mp3

# 设置 HuggingFace Token 进行说话人识别
python podcast_speaker_recognition.py --hf-token YOUR_TOKEN
```

### 高级选项

```bash
# 预览模式 - 查看会处理哪些文件
python podcast_speaker_recognition.py --preview

# 强制重新处理已存在的文件
python podcast_speaker_recognition.py --force-regenerate

# 设置说话人数量限制
python podcast_speaker_recognition.py --min-speakers 2 --max-speakers 3

# 指定计算设备和模型
python podcast_speaker_recognition.py --device cuda --model large-v3
```

## 输出文件

处理完成后，每个音频文件会生成三个输出文件：

1. **`{filename}_transcript.txt`**: 带时间戳和说话人标签的转录文本
   ```
   [00:00.00 -> 00:05.20] SPEAKER_00: 欢迎收听今天的播客节目
   [00:05.20 -> 00:12.50] SPEAKER_01: 感谢邀请，很高兴能参与这个话题
   ```

2. **`{filename}_speakers.json`**: 说话人统计摘要
   ```json
   {
     "total_speakers": 2,
     "total_duration": 1800.5,
     "speakers": {
       "SPEAKER_00": {
         "total_duration": 900.2,
         "percentage": 50.0,
         "segment_count": 25
       }
     }
   }
   ```

3. **`{filename}_detailed.json`**: 完整的识别结果数据

## 系统要求

- **Python 3.8+**
- **Linux**: 支持 CUDA GPU 加速（推荐）
- **macOS**: 使用 CPU 计算（稳定可靠）
- **内存**: 至少 8GB RAM

## 注意事项

1. **首次运行**: 会自动下载模型文件，需要稳定的网络连接
2. **GPU 内存**: 使用 large-v2 模型建议至少 8GB GPU 内存
3. **处理时间**: 根据音频长度和硬件配置，处理时间约为音频长度的 0.1-0.5 倍

## 故障排除

### WhisperX 安装问题
```bash
# 如果安装失败，尝试升级 pip
pip install --upgrade pip
pip install whisperx
```

### CUDA 相关问题
```bash
# 检查 CUDA 是否可用
python -c "import torch; print(torch.cuda.is_available())"
```

### 内存不足
```bash
# 使用更小的模型和批量大小
python podcast_speaker_recognition.py --model base --batch-size 4 --compute-type int8
```

## 开发者信息

基于 [WhisperX](https://github.com/m-bain/whisperX) 项目开发，感谢 Max Bain 等开发者的杰出工作。 