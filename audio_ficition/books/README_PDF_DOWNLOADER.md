# 📥 书籍PDF下载脚本使用说明

## 功能概述

`book_pdf_downloader.py` 是一个基于 `book_info_scraper.py` 生成的书籍信息，使用 Playwright 自动下载书籍PDF文件的脚本。

## 主要特性

### 🤖 智能下载策略
- **情况1**: 直接下载PDF文件（优先选择）
- **情况2**: 通过格式转换获得PDF（epub/mobi -> PDF）
- **情况3**: 跳过标记为低质量的PDF文件
- **情况4**: 无PDF可用时自动跳过

### 🔄 断点续传
- 自动检测已下载的PDF文件
- 跳过已完成的下载任务
- 支持中断后继续下载

### 🌐 浏览器自动化
- 使用 AdsPower 浏览器实现环境隔离
- Playwright 精确控制网页操作
- 智能等待和错误重试机制

## 安装要求

### 1. 依赖包
```bash
pip install playwright tqdm urllib3
```

### 2. Playwright 浏览器
```bash
playwright install chromium
```

### 3. AdsPower 浏览器
- 确保 AdsPower 已启动
- 配置好浏览器环境（默认使用 `kq316tr`）
- 启用本地API（端口：50325）

## 使用方法

### 基本命令

```bash
# 下载10本书的PDF
python book_pdf_downloader.py --count 10

# 下载所有可用的PDF
python book_pdf_downloader.py --all

# 使用指定的AdsPower浏览器ID
python book_pdf_downloader.py --count 5 --ads-id your_browser_id

# 启用调试模式
python book_pdf_downloader.py --count 3 --debug
```

### 参数说明

- `--count, -c`: 要下载的PDF数量（不指定则下载所有）
- `--all`: 下载所有可用的PDF文件
- `--ads-id`: AdsPower 浏览器ID（默认：kq316tr）
- `--debug, -d`: 启用调试模式，显示详细日志

## 文件结构

### 输入文件
脚本需要以下由 `book_info_scraper.py` 生成的文件：
```
/Volumes/dhl/audio/books/en/
├── info/                    # 书籍信息JSON文件
│   ├── uuid1.json
│   ├── uuid2.json
│   └── ...
└── uuid_mapping.json       # URL到UUID的映射
```

### 输出文件
```
/Volumes/dhl/audio/books/en/
├── pdf/                     # 下载的PDF文件
│   ├── uuid1.pdf
│   ├── uuid2.pdf
│   └── ...
└── pdf_download_progress.json  # 下载进度记录
```

## 下载策略详解

### 情况1：直接PDF下载
当页面提供高质量PDF文件时：
```html
<a class="addDownloadedBook">
  <b class="book-property__extension">pdf</b>
  <!-- 没有 low-quality-icon -->
</a>
```

### 情况2：格式转换
当需要从其他格式转换为PDF时：
```html
<a class="converterLink" data-convert_to="pdf">PDF</a>
```
脚本会：
1. 点击转换链接
2. 等待转换完成（最多5分钟）
3. 下载转换后的PDF文件

### 情况3：低质量PDF（跳过）
当PDF标记为低质量时：
```html
<a class="addDownloadedBook">
  <b class="book-property__extension">pdf</b>
  <i class="low-quality-icon" title="Users reported that this is a bad file"></i>
</a>
```

### 情况4：无PDF可用（跳过）
当显示"There are no other formats"时自动跳过。

## 进度管理

### 下载进度文件
`pdf_download_progress.json` 记录：
```json
{
  "completed": ["uuid1", "uuid2"],
  "failed": [
    {"uuid": "uuid3", "reason": "下载失败原因"}
  ],
  "skipped": [
    {"uuid": "uuid4", "reason": "无PDF格式可用"}
  ]
}
```

### 断点续传
脚本会自动：
- 检查已存在的PDF文件
- 读取进度记录文件
- 跳过已完成的下载
- 从中断处继续

## 错误处理

### 常见问题

1. **AdsPower连接失败**
   ```
   错误: API返回状态码 xxx
   ```
   - 确保AdsPower已启动
   - 检查本地API是否启用
   - 验证浏览器ID是否正确

2. **页面加载超时**
   ```
   访问页面超时
   ```
   - 检查网络连接
   - 确认目标网站可访问
   - 可能需要等待后重试

3. **下载菜单未出现**
   ```
   下载菜单未出现
   ```
   - 页面结构可能已变化
   - 检查是否需要登录
   - 确认下载按钮选择器

### 重试机制
- 网络错误自动重试
- 页面加载失败重试
- 下载失败会记录原因

## 性能优化

### 下载速度
- 随机延迟2-5秒避免被封
- 每5本书保存一次进度
- 支持中断后快速恢复

### 资源管理
- 自动清理浏览器资源
- 定期保存进度文件
- 内存使用优化

## 监控和日志

### 实时监控
脚本显示：
- 当前处理的书籍信息
- 下载进度条
- 成功/失败/跳过统计

### 日志级别
- `INFO`: 正常操作信息
- `WARNING`: 非致命错误
- `ERROR`: 严重错误
- `DEBUG`: 详细调试信息（需开启debug模式）

## 示例输出

```
📥 准备下载 10 本书籍的PDF
📱 使用 AdsPower ID: kq316tr
正在连接AdsPower...
成功连接AdsPower，WebSocket地址: ws://127.0.0.1:9222/...
📚 已加载 50 本书籍信息
📁 已存在 5 个PDF文件
📥 准备下载 10 本书的PDF
正在使用Playwright连接浏览器...
✅ 成功连接到浏览器！
🌐 浏览器已准备就绪

📥 下载PDF: 100%|██████████| 10/10 [05:23<00:00, 32.3s/it]

🎯 下载完成!
✅ 成功下载: 7 本
⏭️ 跳过: 2 本
❌ 失败: 1 本
📊 总计处理: 10 本
📁 PDF文件保存在: /Volumes/dhl/audio/books/en/pdf
```

## 注意事项

1. **合法使用**: 仅下载您有权访问的书籍
2. **网站条款**: 遵守目标网站的使用条款
3. **频率控制**: 脚本已内置延迟，避免过度请求
4. **存储空间**: 确保有足够的磁盘空间存储PDF文件
5. **网络稳定**: 建议在稳定的网络环境下运行

## 故障排除

### 检查清单
- [ ] AdsPower 是否正常运行
- [ ] 浏览器ID 是否正确
- [ ] 网络连接是否稳定
- [ ] 存储空间是否充足
- [ ] 书籍信息文件是否存在

### 重新开始
如果需要重新下载所有PDF：
```bash
# 删除进度文件
rm /Volumes/dhl/audio/books/en/pdf_download_progress.json

# 删除已下载的PDF（可选）
rm -rf /Volumes/dhl/audio/books/en/pdf/*

# 重新运行脚本
python book_pdf_downloader.py --all
``` 