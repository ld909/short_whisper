# YouTube 视频自动上传工具

这个工具使用 Playwright 自动化浏览器操作，帮助您登录 YouTube Studio 并上传视频。

## 环境要求

- Python 3.7+
- Playwright 1.30+

## 安装依赖

```bash
pip install playwright
playwright install chromium
```

## 使用方法

1. 复制示例配置文件并修改：

```bash
cp youtube_config_example.json youtube_config.json
```

2. 修改 `youtube_config.json` 填入您的账户信息和视频信息

3. 运行上传脚本：

```bash
python youtube_upload.py youtube_config.json
```

## 解决常见问题

### 1. "This browser or app may not be secure" 错误

这是 Google 检测到自动化浏览器的安全提示。解决方法：

- 脚本现已使用持久化上下文模式，保存浏览器状态到用户目录中
- 添加了更多反检测措施，修改了浏览器指纹信息
- 如果仍然遇到问题，请按照以下步骤操作：
  
  a. 使用常规浏览器登录您的 Google 账号
  b. 导出 cookies 并保存为 `youtube_cookies.json` 文件
  c. 将此文件放在脚本同目录下
  d. 再次运行脚本，它将自动使用 cookies 登录

### 2. 验证问题

如果遇到需要验证的情况，脚本会：

1. 保存验证页面截图以供分析
2. 等待 2 分钟让您完成手动验证
3. 之后会自动保存 cookies 以便下次使用

## 高级配置选项

- `headless`: 设为 `true` 可以在无界面模式下运行（验证时不推荐）
- `save_cookies`: 是否保存成功登录后的 cookies
- `ignore_cookies`: 设为 `true` 可以忽略已保存的 cookies
- `keep_browser_open`: 设为 `true` 可以在上传完成后保持浏览器打开

## 最近更新

- 修复了 `user_data_dir` 参数问题，使用 `launch_persistent_context` 代替
- 改进了浏览器指纹伪装，减少被识别为自动化工具的概率
- 优化了登录流程，提高成功率

## 故障排除

如遇到问题，请检查：

1. 网络连接是否稳定
2. Google 账户是否开启了两步验证
3. 日志文件 `youtube_upload.log` 中的详细错误信息 
4. 确保 Playwright 版本至少为 1.30 