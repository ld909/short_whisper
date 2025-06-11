# YouTube发布状态追踪Excel生成器

这个脚本用于生成和维护YouTube发布状态的Excel追踪表格。

## 功能特性

- 🎬 **多主题支持**: 支持 scifi、thriller、romance、horror、fantasy 等多个主题
- 📊 **Excel生成**: 自动生成对应主题的Excel文件（如 `scifi.xlsx`）
- 🔄 **增量更新**: 支持 append-only 操作，不修改已有数据，只添加新文件
- 🚫 **文件过滤**: 自动排除Mac系统产生的点文件和小于1MB的无效文件
- 💾 **状态追踪**: 追踪每个MP4文件的发布状态

## 使用方法

### 基本命令

```bash
# 处理单个主题
python generate_publish_excel.py --topic scifi

# 处理多个主题
python generate_publish_excel.py --topic scifi,thriller,romance

# 处理所有支持的主题
python generate_publish_excel.py --all

# 强制重新生成Excel文件（忽略现有数据）
python generate_publish_excel.py --topic scifi --force

# 列出所有支持的主题
python generate_publish_excel.py --list-topics
```

### 参数说明

- `--topic`: 指定要处理的主题，支持多个主题用逗号分隔
- `--all`: 处理所有支持的主题
- `--force`: 强制重新生成Excel文件，忽略现有数据
- `--list-topics`: 列出所有支持的主题

## Excel文件格式

生成的Excel文件包含以下列：

| 列名           | 说明                    | 初始值        |
| -------------- | ----------------------- | ------------- |
| `mp4_name`     | MP4文件名（如 `1.mp4`） | 自动填入      |
| `if_published` | 是否已发布到YouTube     | `0`（未发布） |
| `publish_date` | 发布日期                | 空值          |

## 目录结构

### 输入目录
脚本会自动从以下目录读取MP4文件：

**macOS:**
```
/Volumes/dhl/audio/{主题}/mp4_with_subtitles/
```

**Linux:**
```
/mnt/dhl/audio/{主题}/mp4_with_subtitles/
```

### 输出目录
Excel文件会保存到：
```
publish_log/{主题}.xlsx
```

## 支持的主题

当前支持的主题包括：
- `scifi` - 科幻
- `thriller` - 惊悚
- `romance` - 浪漫
- `horror` - 恐怖
- `fantasy` - 奇幻

## 使用示例

### 1. 首次生成scifi主题的Excel
```bash
python generate_publish_excel.py --topic scifi
```

输出示例：
```
🎬 处理主题: SCIFI
📦 找到 33 个MP4文件
🆕 发现 33 个新MP4文件
📝 创建 33 条新记录
✅ Excel文件已保存: publish_log/scifi.xlsx
```

### 2. 增量更新（只添加新文件）
```bash
python generate_publish_excel.py --topic scifi
```

输出示例：
```
🎬 处理主题: SCIFI
📦 找到 35 个MP4文件
📄 已加载现有Excel: publish_log/scifi.xlsx (33 条记录)
🆕 发现 2 个新MP4文件
📝 创建 2 条新记录
```

### 3. 处理多个主题
```bash
python generate_publish_excel.py --topic scifi,thriller,romance
```

### 4. 处理所有主题
```bash
python generate_publish_excel.py --all
```

## 依赖安装

确保已安装必要的依赖：
```bash
pip install pandas openpyxl
```

或者使用项目的requirements.txt：
```bash
pip install -r requirements.txt
```

## 注意事项

1. **文件验证**: 只处理文件名格式为数字.mp4且大小超过1MB的文件
2. **Mac兼容性**: 自动排除以点开头的Mac系统文件
3. **数据安全**: 使用append-only模式，不会修改已有的发布状态数据
4. **排序**: Excel中的记录按MP4文件名中的数字顺序排序

## 后续手动操作

生成Excel文件后，您可以手动更新发布状态：

1. 打开对应的Excel文件（如 `publish_log/scifi.xlsx`）
2. 将已发布视频的 `if_published` 列改为 `1`
3. 在 `publish_date` 列填入发布日期（格式：YYYY-MM-DD）

这样就可以清楚地追踪每个视频的发布状态了。 