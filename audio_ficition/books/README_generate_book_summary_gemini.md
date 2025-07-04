# 📚 书籍总结生成脚本 - Google Gemini App 版本

基于原有的 `generate_book_summary.py` 修改，使用 Google Gemini App 作为生成服务。

## 🌟 主要特性

- 🤖 **使用 Google Gemini App**：替代原有的 AI Studio 服务
- 📁 **完全兼容**：与原脚本使用相同的路径和数据结构
- 🌐 **多语言支持**：支持英文(en)和中文(zh)书籍处理
- 📎 **PDF 自动识别**：自动检测并上传对应的 PDF 文件
- 🔄 **智能跳过**：自动跳过已生成的总结和连续失败的书籍
- 📊 **进度跟踪**：详细的处理进度和失败统计

## 🚀 使用方法

### 基础命令

```bash
# 生成所有可用的总结（默认行为）
python generate_book_summary_gemini.py

# 生成指定数量的总结
python generate_book_summary_gemini.py --count 10

# 生成所有可用的总结（显式指定）
python generate_book_summary_gemini.py --all

# 检查当前状态
python generate_book_summary_gemini.py --check-status
```

### 多语言支持

```bash
# 生成英文书籍总结（默认）
python generate_book_summary_gemini.py --count 10 --lang en

# 生成中文书籍总结
python generate_book_summary_gemini.py --count 10 --lang zh

# 检查中文书籍状态
python generate_book_summary_gemini.py --check-status --lang zh
```

### 自定义参数

```bash
# 指定浏览器ID
python generate_book_summary_gemini.py --ads-id your_browser_id

# 启用调试模式
python generate_book_summary_gemini.py --debug
```

## 📁 目录结构

脚本使用与原版本完全相同的目录结构：

```
📁 基础路径 (Intel Mac: /Volumes/dhl/audio, Apple Silicon: /Users/donghaoliu/Documents/audio)
└── books/
    ├── en/                     # 英文书籍
    │   ├── info/              # 书籍信息JSON文件
    │   ├── pdf/               # PDF文件
    │   ├── summary/           # 生成的总结 (输出目录)
    │   └── summary_json/      # 处理跟踪记录
    └── zh/                     # 中文书籍
        ├── info/
        ├── pdf/
        ├── summary/
        └── summary_json/
```

## ⚙️ 工作流程

1. **📖 载入书籍信息**：从 `info/` 目录读取书籍元数据
2. **📎 检查PDF文件**：验证对应的PDF文件是否存在
3. **🌐 打开Gemini App**：导航到 https://gemini.google.com/app
4. **📝 输入提示词**：将书籍信息和生成要求输入到对话框
5. **📤 上传PDF**：点击"+"按钮，选择"Upload files"上传PDF
6. **⏰ 等待60秒**：按用户要求等待后发送请求
7. **🚀 发送请求**：点击发送按钮开始生成
8. **⏳ 等待完成**：监控"stop"按钮，等待生成完成
9. **📄 提取结果**：从页面提取生成的总结内容
10. **💾 保存文件**：将总结保存到对应的语言目录

## 🔧 技术细节

### 元素选择器

脚本使用以下关键元素选择器：

- **+按钮**：`mat-icon[fonticon="add_2"]`
- **Upload files按钮**：`button:has-text("Upload files")`
- **文本框**：`rich-textarea .ql-editor[contenteditable="true"]`
- **发送按钮**：`mat-icon[fonticon="send"]`
- **停止按钮**：`mat-icon[fonticon="stop"]`
- **消息内容**：`message-content`

### 浏览器设置

- **浏览器ID**：默认使用 `k10i5y1s`
- **浏览器类型**：AdsPower + Playwright
- **连接方式**：CDP (Chrome DevTools Protocol)

## 📊 状态跟踪

脚本会在 `summary_json/` 目录下创建跟踪文件：

```json
{
  "uuid": {
    "title": "书籍标题",
    "total_attempts": 3,
    "failures": 0,
    "last_failure_time": null
  }
}
```

### 智能跳过机制

- 连续5次生成失败的书籍会被自动跳过
- 已存在有效总结的书籍会被跳过
- 没有对应PDF文件的书籍会被跳过

## ⚠️ 注意事项

1. **PDF文件依赖**：脚本依赖 `book_pdf_downloader.py` 生成的PDF文件
2. **浏览器要求**：需要 AdsPower 浏览器管理工具
3. **网络连接**：需要稳定的网络连接访问 Gemini App
4. **生成时间**：每本书大约需要5-10分钟生成时间
5. **文件大小**：确保PDF文件完整且不超过Gemini的限制

## 🔄 与原版本的区别

| 功能       | 原版本 (AI Studio)  | Gemini版本            |
| ---------- | ------------------- | --------------------- |
| 服务提供商 | Google AI Studio    | Google Gemini App     |
| URL        | aistudio.google.com | gemini.google.com/app |
| 上传方式   | Insert assets       | + → Upload files      |
| 等待时间   | 即时发送            | 等待60秒              |
| 界面元素   | AI Studio UI        | Gemini App UI         |
| 其他功能   | 完全相同            | 完全相同              |

## 🚀 开始使用

1. 确保已运行 `book_pdf_downloader.py` 下载PDF文件
2. 启动 AdsPower 浏览器管理工具
3. 运行脚本开始生成总结

```bash
python generate_book_summary_gemini.py --count 5 --lang en
```

生成的总结文件将保存在对应语言的 `summary/` 目录下，文件名格式为 `{uuid}.txt`。 