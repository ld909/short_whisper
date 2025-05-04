# YouTube 视频上传工具

这个脚本用于将处理好的佛教视频自动上传到 YouTube，支持多语言发布。

## 功能特点

1. 从 `merge_mp4_mp3.py` 输出的目录获取对应语种的视频
2. 从 `title_translator_multi_lang.py` 生成的 JSON 文件中获取对应语种的标题
3. 自动处理关键词和视频描述的多语言翻译
4. 支持批量上传和断点续传
5. 使用不同语言频道对应的 OAuth 认证信息

## 安装依赖

首先安装所需的依赖项：

```bash
pip install -r requirements.txt
```

## 准备工作

1. 确保您拥有YouTube频道和相应的API访问权限
2. 将各语言频道的OAuth认证信息保存在`secret_json`目录下
   - 日语频道: `jp.json`
   - 英语频道: `en.json`
   - 韩语频道: `ko.json`
   - 越南语频道: `vi.json`
3. 确保已经使用`merge_mp4_mp3.py`生成了合并后的视频
4. 确保已经使用`title_translator_multi_lang.py`生成了多语言标题

## 使用方法

### 列出可用频道

```bash
python youtube_uploader.py --list-channels
```

### 列出频道的可用语言

```bash
python youtube_uploader.py --list-languages <channel>
```

### 显示多语言内容预览

查看所有语言的关键词和描述翻译：

```bash
python youtube_uploader.py --show-multilingual
```

### 上传指定频道和语言的所有视频

```bash
python youtube_uploader.py -c <channel> -l <language>
```

例如，上传buddha频道的日语视频：

```bash
python youtube_uploader.py -c buddha -l japanese
```

### 上传特定视频文件

```bash
python youtube_uploader.py -c <channel> -l <language> -f <filename>
```

### 指定自定义基础路径

```bash
python youtube_uploader.py -c <channel> -l <language> --base-path <path>
```

### 强制重新上传视频

```bash
python youtube_uploader.py -c <channel> -l <language> --force
```

## 首次使用认证流程

首次运行时，脚本会要求您进行YouTube API的OAuth认证：

1. 脚本会打开浏览器窗口或提供URL
2. 使用您的YouTube账号登录
3. 授权应用访问您的YouTube频道
4. 认证成功后，令牌将被保存，以后无需重复认证

如果无法自动打开浏览器，请使用以下命令：

```bash
python youtube_uploader.py -c <channel> -l <language> --noauth_local_webserver
```

## 注意事项

- 所有上传的视频默认设置为公开(`public`)
- 每个语言的关键词和描述会自动翻译到对应语言
- 上传记录会保存在`./upload_log/upload_log.txt`文件中
- 每个频道和语言组合都有单独的日志文件

## 目录结构

脚本期望的目录结构如下：

```
/[基础路径]/
  ├── mp4_with_audio/              # 合并后的视频
  │   └── [频道名]/
  │       └── [语言]/
  │           └── [视频文件].mp4
  │
  └── multi_lang_titles/           # 多语言标题数据
      └── [频道名]/
          └── [视频文件].json      # 包含多语言标题的JSON
```

## 故障排除

1. 如果遇到认证问题，请删除对应语言的`*-oauth2.json`文件并重试
2. 如果上传失败，脚本会自动重试，最多重试10次
3. 查看上传日志以获取详细的上传记录 