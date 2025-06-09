# AI Studio 多主题故事生成器

这是一个支持多种故事主题的AI Studio自动化生成工具，可以生成不同类型的故事内容。

## 🎯 支持的主题

### 当前可用主题

- **scifi** - 科幻故事
  - 包含未来科技、太空探索、时间旅行等元素
  - 使用 `gen_prompt` 模块生成参数
  
- **fantasy** - 奇幻故事  
  - 包含魔法、龙、精灵等奇幻元素
  - 使用 `fantasy_script_generator` 模块和配置文件生成参数

### 计划支持的主题

- **love** - 爱情故事（即将支持）
- **detective** - 侦探推理故事（即将支持）  
- **mystery** - 悬疑故事（即将支持）

## 📁 文件结构

```
audio_ficition/
├── audio_fiction/
│   ├── ai_studio_bot.py          # 主脚本（多主题版本）
│   ├── gen_prompt.py             # 科幻故事参数生成器
│   ├── test_themes.py            # 主题功能测试脚本
│   └── README_multi_theme.md     # 本说明文档
└── fantasy/
    ├── fantasy_script_generator.py  # 奇幻故事参数生成器
    ├── config.json                 # 奇幻故事配置文件
    └── README.md                   # 奇幻模块说明
```

## 🚀 使用方法

### 基本语法

```bash
python ai_studio_bot.py --theme <主题> [选项]
```

### 命令行参数

- `--theme, -t` (必需): 指定故事主题
- `--count, -c`: 生成故事数量（默认: 2）
- `--ads-id`: AdsPower浏览器ID（默认: kyencl7）
- `--list-themes`: 列出所有支持的主题

### 使用示例

```bash
# 列出所有支持的主题
python ai_studio_bot.py --list-themes

# 生成5个科幻故事
python ai_studio_bot.py --theme scifi --count 5

# 生成3个奇幻故事
python ai_studio_bot.py --theme fantasy --count 3

# 使用特定浏览器ID生成故事
python ai_studio_bot.py --theme scifi --count 2 --ads-id your_browser_id
```

## 📂 故事保存路径

故事按主题分别保存在不同目录中：

```
/Volumes/dhl/audio/
├── scifi/full_story/story_index/
│   ├── 1.txt
│   ├── 2.txt
│   └── ...
├── fantasy/full_story/story_index/
│   ├── 1.txt
│   ├── 2.txt
│   └── ...
└── [其他主题]/full_story/story_index/
    └── ...
```

## 🔄 断点续传功能

脚本会自动检测已存在的故事文件：

1. **智能索引管理**: 优先填补缺失的故事索引
2. **跳过已生成**: 不会重复生成已存在的故事
3. **动态检查**: 启动时自动分析现有故事情况

### 索引管理示例

```
现有文件: 1.txt, 2.txt, 4.txt, 5.txt
需要生成: 3个故事

结果:
- 优先生成 3.txt (填补缺失)
- 然后生成 6.txt, 7.txt (新增)
```

## 🧪 测试功能

运行测试脚本来验证功能：

```bash
# 测试所有主题功能
python test_themes.py
```

测试内容包括：
- 主题验证
- 目录路径生成
- 故事参数生成
- 各模块导入状态

## 🛠️ 扩展新主题

### 1. 添加主题配置

在 `ai_studio_bot.py` 中的 `SUPPORTED_THEMES` 字典添加新主题：

```python
SUPPORTED_THEMES = {
    # ... 现有主题 ...
    'new_theme': {
        'name': '新主题',
        'available': True,  # 设为True启用
        'description': '新主题故事生成说明'
    }
}
```

### 2. 实现参数生成器

在 `generate_story_prompt_by_theme` 函数中添加新主题的处理逻辑：

```python
elif theme == 'new_theme':
    # 实现新主题的参数生成逻辑
    return generate_new_theme_prompt()
```

### 3. 创建参数生成模块

参考 `fantasy_script_generator.py` 创建新主题的参数生成模块。

## ⚠️ 注意事项

1. **主题模块依赖**: 确保对应的参数生成模块可用
2. **配置文件**: fantasy主题需要 `config.json` 配置文件
3. **目录权限**: 确保对保存目录有写入权限
4. **浏览器连接**: 需要AdsPower浏览器正常运行

## 🐛 常见问题

### 主题不可用错误

```
❌ 主题 'fantasy' 暂不可用: fantasy主题不可用：fantasy_script_generator模块未找到
```

**解决方案**: 检查 `fantasy_script_generator.py` 和 `config.json` 是否存在

### 模块导入错误

**解决方案**: 确保所有依赖模块在正确路径下，检查Python路径设置

### 目录权限错误

**解决方案**: 确保对 `/Volumes/dhl/audio/` 目录有写入权限

## 📈 版本历史

- **v3.0**: 支持多主题架构，集成fantasy主题
- **v2.0**: 支持多窗口并发、智能热身、断点续传  
- **v1.0**: 基础scifi故事生成功能

## 🤝 贡献

欢迎添加新的故事主题！请遵循现有的架构模式：

1. 创建主题参数生成器
2. 更新主题配置
3. 添加测试用例
4. 更新文档 