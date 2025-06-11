# YouTube 自动发布系统使用说明

## 简介

`auto_youtube_publish.py` 是一个基于 `generate_publish_excel.py` 生成的 Excel 文件的 YouTube 自动发布系统。该系统能够自动读取不同主题的视频信息，计算合理的发布时间，并自动发布到 YouTube。

## 功能特性

### 🎯 核心功能
- **多主题支持**: 支持 scifi、thriller、romance、horror、fantasy 等主题
- **智能时间计算**: 基于已发布视频的最远时间自动计算下一个发布时间
- **自动发布**: 使用 Playwright 自动化发布到 YouTube
- **状态更新**: 发布完成后自动更新 Excel 状态

### ⏰ 时间计算逻辑
1. **全部未发布**: 使用当前时间作为基准时间
2. **最远时间 < 当前时间**: 使用当前时间作为基准时间
3. **最远时间 >= 当前时间**: 使用最远时间作为基准时间
4. **下次发布时间** = 基准时间 + 指定间隔小时

### 📁 文件路径结构
```
# Excel 文件路径
publish_log/[主题].xlsx

# 视频文件路径 (基于 add_subtitles_to_videos.py 输出)
macOS: /Volumes/dhl/audio/[主题]/mp4_with_subtitles/[文件名]
Linux: /mnt/dhl/audio/[主题]/mp4_with_subtitles/[文件名]
```

## 安装要求

### 1. Python 依赖
```bash
pip install -r requirements.txt
```

主要依赖：
- `pandas>=1.3.0` - Excel 文件处理
- `openpyxl>=3.0.0` - Excel 文件读写
- `playwright>=1.40.0` - 浏览器自动化
- `urllib3>=1.26.0` - HTTP 请求处理

### 2. 浏览器设置
安装 Playwright 浏览器：
```bash
playwright install chromium
```

### 3. AdsPower 配置
- 安装并启动 AdsPower
- 配置浏览器实例（默认ID: kq316tr）
- 确保本地API已启用（端口50325）

## 使用方法

### 基本用法

#### 1. 单个主题发布
```bash
# 发布 scifi 主题，间隔4小时，最多1个视频
python auto_youtube_publish.py --topic scifi --interval 4 --max-count 1

# 发布 thriller 主题，间隔6小时，最多2个视频
python auto_youtube_publish.py --topic thriller --interval 6 --max-count 2
```

#### 2. 多个主题发布
```bash
# 同时处理多个主题
python auto_youtube_publish.py --topic scifi,thriller,romance --interval 4 --max-count 1

# 处理所有主题
python auto_youtube_publish.py --all --interval 4 --max-count 1
```

#### 3. 试运行模式
```bash
# 不实际发布，只显示将要执行的操作
python auto_youtube_publish.py --topic scifi --interval 4 --dry-run
```

### 命令行参数

| 参数             | 类型   | 默认值   | 说明                           |
| ---------------- | ------ | -------- | ------------------------------ |
| `--topic`        | string | -        | 指定主题，支持逗号分隔多个主题 |
| `--all`          | flag   | -        | 处理所有支持的主题             |
| `--interval`     | int    | 4        | 视频发布间隔小时数             |
| `--max-count`    | int    | 1        | 最大发布数量                   |
| `--ads-id`       | string | kq316tr  | AdsPower浏览器ID               |
| `--studio-url`   | string | 默认频道 | YouTube Studio频道URL          |
| `--wait-minutes` | int    | 30       | tab限制时等待分钟数            |
| `--dry-run`      | flag   | -        | 试运行模式                     |

### 支持的主题
- `scifi` - 科幻
- `thriller` - 惊悚
- `romance` - 浪漫
- `horror` - 恐怖
- `fantasy` - 奇幻

## 使用流程

### 1. 准备工作
确保已运行 `generate_publish_excel.py` 生成必要的 Excel 文件：
```bash
# 生成单个主题的Excel文件
python generate_publish_excel.py --topic scifi

# 生成所有主题的Excel文件
python generate_publish_excel.py --all
```

### 2. 检查文件结构
确认以下文件存在：
- `publish_log/scifi.xlsx` (或其他主题)
- `/Volumes/dhl/audio/scifi/mp4_with_subtitles/*.mp4` (macOS)
- `/mnt/dhl/audio/scifi/mp4_with_subtitles/*.mp4` (Linux)

### 3. 配置 AdsPower
- 启动 AdsPower 应用
- 确保浏览器实例正常运行
- 登录 YouTube 账号

### 4. 执行发布
```bash
# 推荐的基本用法
python auto_youtube_publish.py --topic scifi --interval 4 --max-count 1
```

## 工作原理

### 1. 扫描阶段
- 读取指定主题的 Excel 文件
- 检查 `if_published == 0` 的视频
- 验证对应的 MP4 文件是否存在
- 排除Mac系统产生的点文件

### 2. 时间计算阶段
- 扫描所有主题的已发布视频
- 找到最远的发布时间
- 根据时间计算逻辑确定下次发布时间

### 3. 发布阶段
- 连接 AdsPower 浏览器
- 导航到 YouTube Studio
- 上传视频文件
- 设置标题、描述
- 配置发布时间
- 确认发布

### 4. 更新阶段
- 更新 Excel 中的 `if_published` 为 1
- 设置 `publish_date` 为发布时间
- 保存 Excel 文件

## 自动生成的内容

### 标题格式
- Sci-Fi: `Sci-Fi Story #[编号] - Epic Science Fiction Adventure`
- Thriller: `Thriller #[编号] - Heart-Pounding Suspense`
- Romance: `Romance #[编号] - Beautiful Love Story`
- Horror: `Horror #[编号] - Spine-Chilling Terror`
- Fantasy: `Fantasy #[编号] - Magical Adventure`

### 描述模板
每个主题都有对应的英文描述模板，描述视频的特色和吸引观众观看。

## 安全特性

### 文件验证
- 自动排除Mac系统产生的点文件
- 验证文件大小（大于1MB）
- 检查文件是否存在

### 浏览器管理
- 自动重试机制
- 优雅的错误处理
- 资源清理

### Excel 保护
- 读取前验证文件存在
- 更新后验证保存结果
- 详细的操作日志

## 常见问题

### Q: 如何更改发布间隔？
A: 使用 `--interval` 参数指定小时数，例如 `--interval 6` 表示间隔6小时。

### Q: 如何发布多个视频？
A: 使用 `--max-count` 参数，例如 `--max-count 3` 最多发布3个视频。

### Q: 如何测试不实际发布？
A: 使用 `--dry-run` 参数进行试运行，查看将要执行的操作。

### Q: 浏览器连接失败怎么办？
A: 
1. 检查 AdsPower 是否正常运行
2. 确认浏览器ID是否正确
3. 重启 AdsPower 应用
4. 检查本地API是否启用

### Q: Excel文件不存在怎么办？
A: 先运行 `python generate_publish_excel.py --topic [主题名]` 生成Excel文件。

### Q: 如何更改YouTube频道？
A: 使用 `--studio-url` 参数指定不同的YouTube Studio频道URL。

## 示例用法

### 典型的日常使用
```bash
# 每天发布一个scifi视频，间隔4小时
python auto_youtube_publish.py --topic scifi --interval 4 --max-count 1

# 一次性发布多个主题，每个主题1个视频
python auto_youtube_publish.py --all --interval 6 --max-count 1

# 批量发布thriller主题的3个视频
python auto_youtube_publish.py --topic thriller --interval 4 --max-count 3
```

### 测试和调试
```bash
# 试运行查看待发布视频
python auto_youtube_publish.py --topic scifi --dry-run

# 使用自定义浏览器ID
python auto_youtube_publish.py --topic scifi --ads-id custom_browser_id

# 设置更长的等待时间
python auto_youtube_publish.py --topic scifi --wait-minutes 60
```

## 注意事项

1. **确保Excel文件是最新的**: 运行前先更新Excel文件
2. **检查视频文件路径**: 确认视频文件在正确的目录中
3. **AdsPower配置**: 确保浏览器实例已登录YouTube
4. **网络连接**: 确保网络稳定，避免上传中断
5. **系统时间**: 确保系统时间准确，影响发布时间计算

## 监控和日志

系统会输出详细的执行日志，包括：
- 扫描结果统计
- 时间计算过程
- 发布操作步骤
- Excel更新状态
- 错误信息和建议

建议保存日志用于问题排查：
```bash
python auto_youtube_publish.py --topic scifi --interval 4 2>&1 | tee publish.log
``` 