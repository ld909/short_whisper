# Z-Library 电子书URL爬虫

支持多语种、断点续传、URL去重和自动翻页的 Z-Library 电子书 URL 爬虫。

## 功能特点

- 🌍 **多语种支持**: 支持英文和中文 Z-Library 站点
- 🔄 **断点续传**: 支持中断后从上次位置继续爬取
- 🚫 **URL去重**: 自动过滤重复的书籍链接
- 📄 **自动翻页**: 自动点击"Load More"按钮加载更多内容
- 💾 **进度保存**: 实时保存爬取进度和结果
- 🎯 **智能过滤**: 自动过滤无效链接，只保留书籍相关URL

## 安装依赖

```bash
pip install requests beautifulsoup4 playwright
playwright install chromium
```

## 使用方法

### 1. 命令行模式

#### 爬取英文站点
```bash
# 全新开始爬取英文站点
python zlib_crawler.py --language en --max-pages 50

# 断点续传英文站点
python zlib_crawler.py --language en --resume --max-pages 100
```

#### 爬取中文站点
```bash
# 全新开始爬取中文站点
python zlib_crawler.py --language zh --max-pages 50

# 断点续传中文站点
python zlib_crawler.py --language zh --resume --max-pages 100
```

#### 参数说明
- `--language, -l`: 选择语种 (`en` 英文, `zh` 中文)
- `--max-pages, -p`: 最大爬取页数 (默认: 50)
- `--resume, -r`: 断点续传模式

### 2. 交互模式

直接运行脚本，按提示选择选项：

```bash
python zlib_crawler.py
```

交互界面：
```
🕷️ Z-Library 电子书URL爬虫
🌍 请选择语种:
1. 🇺🇸 English (英文)
2. 🇨🇳 中文

请选择语种 (1/2): 2

📖 请选择爬取模式:
1. 🆕 全新开始爬取
2. 🔄 断点续传

请选择模式 (1/2): 1
请输入最大爬取页数 (默认50): 100
```

## 输出文件

根据选择的语种，爬虫会生成不同的输出文件：

### 英文站点 (`--language en`)
- **URL文件**: `book_url.txt`
- **进度文件**: `crawler_progress.json`
- **日志文件**: `zlib_crawler.log`

### 中文站点 (`--language zh`)
- **URL文件**: `book_url_zh.txt`
- **进度文件**: `crawler_progress_zh.json`  
- **日志文件**: `zlib_crawler.log`

## 配置说明

### 语种配置

#### 英文站点
- 目标URL: `https://zlib.fi/`
- Load More按钮文本: ["Load more", "Load More", "Show more", "更多"]

#### 中文站点  
- 目标URL: `https://zh.zlib.fi/`
- Load More按钮文本: ["加载更多", "更多", "显示更多", "Load more", "Load More"]

### 进度文件格式

```json
{
  "last_page": 25,
  "total_books": 1250,
  "language": "zh"
}
```

## 使用示例

### 示例1: 爬取中文站点前30页
```bash
python zlib_crawler.py -l zh -p 30
```

### 示例2: 继续中文站点的断点续传
```bash
python zlib_crawler.py -l zh -r -p 100
```

### 示例3: 爬取英文站点并设置较大页数
```bash
python zlib_crawler.py -l en -p 200
```

## 注意事项

1. **网络稳定性**: 请确保网络连接稳定，避免频繁中断
2. **访问限制**: 部分地区可能需要使用代理访问 Z-Library
3. **爬取频率**: 脚本已内置随机延迟，避免过于频繁的请求
4. **文件管理**: 不同语种的文件会分别保存，避免覆盖

## 故障排除

### 常见问题

1. **无法访问目标网站**
   - 检查网络连接
   - 确认 Z-Library 镜像地址是否可用
   - 考虑使用代理

2. **找不到Load More按钮**
   - 可能已加载所有内容
   - 检查页面结构是否发生变化

3. **Playwright安装问题**
   ```bash
   playwright install chromium
   ```

4. **编码问题**
   - 确保终端支持 UTF-8 编码
   - Windows 用户可能需要设置环境变量

## 更新日志

- **v2.0**: 添加多语种支持 (英文/中文)
- **v1.0**: 基础爬虫功能，支持断点续传和URL去重 