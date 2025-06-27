# VOICEVOX 测试脚本使用说明

## 概述

`test_voicevox.py` 是一个用于测试 VOICEVOX 语音合成引擎的 Python 脚本。它可以将文本转换为语音，支持多种说话人、语音参数调节，并能将 WAV 文件转换为 MP3 格式。

## 功能特性

- ✅ 检查依赖库和环境
- ✅ 连接 VOICEVOX Engine 并验证状态
- ✅ 获取可用说话人列表
- ✅ 文本转语音合成
- ✅ WAV 转 MP3 格式转换
- ✅ 支持语速、音调、语调、音量调节
- ✅ 批量测试多种声音
- ✅ 详细的日志记录

## 环境准备

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install voicevox-client pydub

# 安装 ffmpeg (音频转换工具)
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg
```

### 2. 启动 VOICEVOX Engine

VOICEVOX Engine 是语音合成的核心服务，需要单独运行。

#### 方法一：Docker 启动 (推荐)

```bash
# CPU 版本
docker run -d --rm -p 50021:50021 voicevox/voicevox_engine:cpu-ubuntu20.04-latest

# GPU 版本 (如果支持 CUDA)
docker run -d --rm --gpus all -p 50021:50021 voicevox/voicevox_engine:nvidia-ubuntu20.04-latest
```

#### 方法二：直接下载运行

1. 访问 [VOICEVOX 官网](https://voicevox.hiroshiba.jp/) 下载
2. 解压并运行可执行文件
3. 确保服务运行在端口 50021

### 3. 验证环境

```bash
# 检查服务是否正常
curl http://localhost:50021/version

# 或使用脚本检查
python test_voicevox.py --check-only
```

## 使用方法

### 基本用法

```bash
# 最简单的测试
python test_voicevox.py

# 指定文本和说话人
python test_voicevox.py --text "你好，世界！" --speaker 1

# 指定输出目录和文件名
python test_voicevox.py --output-dir audio_output --filename my_voice
```

### 参数说明

| 参数                 | 说明                   | 默认值                                     | 示例                   |
| -------------------- | ---------------------- | ------------------------------------------ | ---------------------- |
| `--text`, `-t`       | 要合成的文本           | "こんにちは！これはVOICEVOXのテストです。" | `--text "你好世界"`    |
| `--speaker`, `-s`    | 说话人ID               | 1                                          | `--speaker 8`          |
| `--output-dir`, `-o` | 输出目录               | "output"                                   | `--output-dir audio`   |
| `--filename`, `-f`   | 输出文件名(不含扩展名) | "test_voice"                               | `--filename hello`     |
| `--host`             | VOICEVOX Engine 主机   | "localhost"                                | `--host 192.168.1.100` |
| `--port`             | VOICEVOX Engine 端口   | 50021                                      | `--port 50021`         |
| `--no-mp3`           | 不转换为MP3            | False                                      | `--no-mp3`             |
| `--speed`            | 语速 (0.5-2.0)         | 1.0                                        | `--speed 1.2`          |
| `--pitch`            | 音调 (-0.15-0.15)      | 0.0                                        | `--pitch 0.05`         |
| `--intonation`       | 语调 (0.0-2.0)         | 1.0                                        | `--intonation 1.2`     |
| `--volume`           | 音量 (0.0-2.0)         | 1.0                                        | `--volume 0.8`         |

### 特殊功能

#### 1. 检查环境和连接

```bash
python test_voicevox.py --check-only
```

#### 2. 列出可用说话人

```bash
python test_voicevox.py --list-speakers
```

#### 3. 批量测试多种声音

```bash
python test_voicevox.py --test-batch
```

#### 4. 高级参数调节

```bash
# 快速语音
python test_voicevox.py --speed 1.5 --pitch 0.1

# 慢速低沉语音
python test_voicevox.py --speed 0.8 --pitch -0.1 --volume 0.7

# 高音量高语调
python test_voicevox.py --intonation 1.5 --volume 1.2
```

## 说话人ID参考

常用说话人ID（具体可用ID请运行 `--list-speakers` 查看）：

| ID  | 角色名       | 风格     |
| --- | ------------ | -------- |
| 1   | 四国めたん   | ノーマル |
| 2   | 四国めたん   | あまあま |
| 3   | 四国めたん   | ツンツン |
| 8   | 春日部つむぎ | ノーマル |
| 9   | 波音リツ     | ノーマル |
| 10  | 玄野武宏     | ノーマル |

## 输出文件

脚本会在指定的输出目录中生成以下文件：

- `{filename}.wav` - 原始 WAV 格式音频文件
- `{filename}.mp3` - 转换后的 MP3 格式音频文件（除非使用 --no-mp3）
- `voicevox_test.log` - 详细的运行日志

## 常见问题

### 1. 连接失败

```
❌ 无法连接到 VOICEVOX Engine
```

**解决方法：**
- 确保 VOICEVOX Engine 正在运行
- 检查端口 50021 是否被占用
- 尝试重启 VOICEVOX Engine

### 2. 依赖缺失

```
❌ voicevox-client 未安装
```

**解决方法：**
```bash
pip install voicevox-client pydub
```

### 3. ffmpeg 未找到

```
❌ ffmpeg 未安装或不在 PATH 中
```

**解决方法：**
参考环境准备章节安装 ffmpeg

### 4. 说话人ID无效

```
❌ 语音合成失败
```

**解决方法：**
- 使用 `--list-speakers` 查看可用ID
- 确保使用的ID存在

## 高级用法

### 1. Docker Compose 启动 VOICEVOX Engine

创建 `docker-compose.yml`：

```yaml
version: '3.8'
services:
  voicevox:
    image: voicevox/voicevox_engine:cpu-ubuntu20.04-latest
    ports:
      - "50021:50021"
    restart: unless-stopped
```

启动：
```bash
docker-compose up -d
```

### 2. 批量处理文本文件

```bash
# 创建文本文件
echo "你好，世界！" > text1.txt
echo "这是测试文本。" > text2.txt

# 逐个处理
for file in *.txt; do
    python test_voicevox.py --text "$(cat $file)" --filename "${file%.txt}"
done
```

### 3. 网络部署

如果 VOICEVOX Engine 部署在其他机器上：

```bash
python test_voicevox.py --host 192.168.1.100 --port 50021
```

## 故障排除

### 1. 启用详细日志

检查 `voicevox_test.log` 文件获取详细错误信息。

### 2. 手动测试连接

```bash
# 测试版本接口
curl http://localhost:50021/version

# 测试说话人接口
curl http://localhost:50021/speakers
```

### 3. 检查系统资源

VOICEVOX Engine 需要一定的系统资源：
- CPU: 现代多核处理器
- 内存: 至少 2GB 可用内存
- 存储: 几GB 的可用空间

## 许可证

本脚本遵循项目许可证。VOICEVOX 相关组件请参考其官方许可证条款。

## 支持

如有问题，请：
1. 检查日志文件 `voicevox_test.log`
2. 确认所有依赖已正确安装
3. 验证 VOICEVOX Engine 运行状态
4. 参考官方文档：https://voicevox.hiroshiba.jp/ 