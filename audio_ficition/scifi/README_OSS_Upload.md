# 科幻故事封面图片OSS上传工具

这个工具用于将超分辨率处理后的封面图片上传到阿里云OSS存储。

## 安装依赖

首先需要安装阿里云OSS Python SDK V2：

```bash
pip install alibabacloud-oss-v2
```

## 环境变量配置

根据[阿里云OSS SDK V2文档](https://help.aliyun.com/zh/oss/developer-reference/get-started-with-oss-sdk-for-python-v2?spm=a2c4g.11186623.0.0.42b339b9YUqOCV#addadb57a9xyy)，需要设置环境变量：

### macOS/Linux (Zsh)
```bash
echo "export OSS_ACCESS_KEY_ID='YOUR_ACCESS_KEY_ID'" >> ~/.zshrc
echo "export OSS_ACCESS_KEY_SECRET='YOUR_ACCESS_KEY_SECRET'" >> ~/.zshrc
source ~/.zshrc
```

### macOS/Linux (Bash)
```bash
echo "export OSS_ACCESS_KEY_ID='YOUR_ACCESS_KEY_ID'" >> ~/.bash_profile
echo "export OSS_ACCESS_KEY_SECRET='YOUR_ACCESS_KEY_SECRET'" >> ~/.bash_profile
source ~/.bash_profile
```

### Windows CMD
```cmd
setx OSS_ACCESS_KEY_ID "YOUR_ACCESS_KEY_ID"
setx OSS_ACCESS_KEY_SECRET "YOUR_ACCESS_KEY_SECRET"
```

### Windows PowerShell
```powershell
[Environment]::SetEnvironmentVariable("OSS_ACCESS_KEY_ID", "YOUR_ACCESS_KEY_ID", [EnvironmentVariableTarget]::User)
[Environment]::SetEnvironmentVariable("OSS_ACCESS_KEY_SECRET", "YOUR_ACCESS_KEY_SECRET", [EnvironmentVariableTarget]::User)
```

## 使用方法

### 基本使用
```bash
python upload_cover_to_oss.py
```

### 强制重新上传所有图片
```bash
python upload_cover_to_oss.py -f
```

### 指定故事索引范围
```bash
python upload_cover_to_oss.py --start 1 --end 10
```

### 指定自定义bucket名称
```bash
python upload_cover_to_oss.py --bucket my-custom-bucket
```

### 组合使用
```bash
python upload_cover_to_oss.py -f --start 1 --end 50 --bucket audiocover
```

## 功能特性

- ✅ **断点续传**: 已上传的文件不会重复上传
- ✅ **进度显示**: 使用进度条显示上传进度
- ✅ **错误处理**: 详细的错误信息和重试机制
- ✅ **自动创建bucket**: 如果bucket不存在会自动创建
- ✅ **批量处理**: 支持批量上传多个图片
- ✅ **灵活配置**: 支持指定索引范围和bucket名称

## 输入输出

### 输入
- 本地超分图片目录: `/Volumes/dhl/audio/scifi/cover_img_large/`
- 图片文件格式: `{故事索引}.png`

### 输出
- OSS存储路径: `oss://audiocover/cover_images/{故事索引}.png`
- OSS区域: cn-shanghai (上海)

## 命令行参数

| 参数       | 简写 | 类型   | 默认值     | 说明                       |
| ---------- | ---- | ------ | ---------- | -------------------------- |
| `--force`  | `-f` | 布尔   | False      | 强制重新上传，忽略已有文件 |
| `--start`  | 无   | 整数   | 无         | 指定开始上传的故事索引     |
| `--end`    | 无   | 整数   | 无         | 指定结束上传的故事索引     |
| `--bucket` | 无   | 字符串 | audiocover | OSS bucket名称             |

## 注意事项

1. **访问密钥**: 确保正确设置了OSS访问密钥环境变量
2. **权限**: AccessKey需要有OSS的读写权限
3. **网络**: 确保网络连接正常，上传大文件时可能需要较长时间
4. **目录结构**: 脚本会在OSS中创建 `cover_images/` 目录来存储图片
5. **重启环境**: 设置环境变量后，请重启IDE或命令行界面确保变量生效

## 错误排查

### AccessDenied 错误
- 检查AccessKey ID和AccessKey Secret是否正确
- 确认RAM用户是否有OSS权限
- 检查bucket policy设置

### 网络连接错误
- 确认网络连接正常
- 检查阿里云服务状态
- 尝试重新运行脚本

### 文件不存在错误
- 确认超分图片目录存在
- 检查图片文件是否生成完成
- 先运行 `upscale_cover_images.py` 生成超分图片 