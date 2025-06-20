# X平台帖子生成器使用说明

## 功能概述

`generate_x_posts.py` 是一个专门为书籍总结生成X平台（原Twitter）病毒式传播帖子的脚本。它能够将书籍总结转化为3-4条推文的线程，遵循社交媒体增长专家的写作风格。

## 主要特性

- 🎯 **病毒式传播设计**: 基于社交媒体专家经验，生成具有强烈吸引力的推文线程
- 🔄 **断点续传**: 自动跳过已生成的帖子，支持增量处理
- 🍎 **跨系统支持**: 自动识别Intel Mac和Apple Silicon Mac，使用对应的路径
- 📁 **智能文件过滤**: 自动排除macOS系统生成的隐藏文件
- ⚡ **批量处理**: 支持批量生成多个书籍的X帖子

## 系统要求

- macOS系统（Intel或Apple Silicon）
- Python 3.x
- OpenAI API密钥（通过UNI_API_KEY环境变量）
- 依赖库：`openai`, `tqdm`

## 安装依赖

```bash
pip install openai tqdm
```

## 环境设置

设置OpenAI API密钥：

```bash
export UNI_API_KEY="your-api-key-here"
```

## 输入文件要求

- **书籍总结文件**: 由 `generate_book_summary.py` 生成的总结文件
- **文件位置**: 
  - Intel Mac: `/Volumes/dhl/audio/books/en/summary/{uuid}.txt`
  - Apple Silicon: `/Users/donghaoliu/Documents/audio/books/en/summary/{uuid}.txt`

## 输出文件

生成的X帖子保存在：
- Intel Mac: `/Volumes/dhl/audio/books/en/x_posts/{uuid}.txt`
- Apple Silicon: `/Users/donghaoliu/Documents/audio/books/en/x_posts/{uuid}.txt`

## 使用方法

### 基础使用

```bash
# 处理所有可用的书籍总结
python generate_x_posts.py

# 预览模式（不实际生成）
python generate_x_posts.py --preview

# 强制重新生成所有帖子
python generate_x_posts.py --force
```

### 高级选项

```bash
# 处理指定UUID的书籍
python generate_x_posts.py --uuid 12345678-abcd-efgh-ijkl-123456789012

# 限制处理数量
python generate_x_posts.py --count 10

# 启用详细调试信息
python generate_x_posts.py --debug

# 组合使用多个选项
python generate_x_posts.py --count 5 --force --debug
```

## 帖子生成规则

脚本遵循以下病毒式传播原则：

### RULE 1: 病毒式钩子（第1条推文）
- 开始于挑衅性问题、反直觉陈述或令人惊讶的真相
- 挑战常见信念，让人停止滚动
- 控制在250字符以内

### RULE 2: 核心理念（第2条推文）
- 揭示书籍最强大的中心论点
- 用最简单的语言解释
- 可能使用强有力的类比

### RULE 3: 应用价值（第3条推文）
- 解释为什么这个理念是游戏规则改变者
- 提供可操作的洞察或深刻的视角转变
- 这是读者的"顿悟"时刻

### RULE 4: 总结与行动号召（第4条推文）
- 以鼓舞人心的最终想法结束
- 温和地引导关注者获取完整总结
- 添加3-4个战略性标签

## 生成样式特点

- **平实语言**: 不使用学术行话
- **短句结构**: 清晰、简洁的句子
- **真实语调**: 真诚而深刻，避免营销炒作
- **朋友式交流**: 如同向聪明朋友解释精彩想法

## 错误处理

脚本包含完善的错误处理机制：

- **API失败重试**: 每个请求最多重试3次
- **文件验证**: 检查文件大小和有效性
- **网络问题**: 自动重试和错误报告
- **详细日志**: 每个处理步骤都有清晰的状态反馈

## 性能优化

- **断点续传**: 避免重复处理已完成的文件
- **批量处理**: 支持大量文件的高效处理
- **进度显示**: 实时显示处理进度
- **内存优化**: 逐个处理文件，避免内存溢出

## 故障排除

### 常见问题

1. **API密钥错误**
   ```
   ❌ 错误: 未找到OpenAI API密钥
   ```
   解决：确保正确设置 `UNI_API_KEY` 环境变量

2. **找不到总结文件**
   ```
   ❌ 总结目录不存在
   ```
   解决：先运行 `generate_book_summary.py` 生成总结文件

3. **权限问题**
   ```
   PermissionError: [Errno 13] Permission denied
   ```
   解决：检查目录写入权限，确保有足够的磁盘空间

### 调试技巧

- 使用 `--debug` 参数查看详细处理信息
- 使用 `--preview` 参数测试配置而不实际生成
- 检查生成的帖子文件内容和格式

## 最佳实践

1. **批量处理**: 建议使用 `--count` 参数进行小批量测试
2. **质量检查**: 定期检查生成的帖子质量和风格一致性
3. **备份策略**: 定期备份生成的X帖子文件
4. **API配额**: 注意API使用限制，避免短时间内大量请求

## 技术实现

- **模型**: 使用 GPT-4o-mini 模型
- **温度**: 0.7（平衡创造性和一致性）
- **最大Token**: 1000（确保完整响应）
- **重试机制**: 指数退避重试策略

## 版本历史

- v1.0: 初始版本，支持基础X帖子生成
- 支持Intel和Apple Silicon Mac
- 完整的断点续传功能
- 病毒式传播风格优化

## 相关脚本

- `generate_book_summary.py`: 生成书籍总结（前置依赖）
- `generate_youtube_descriptions.py`: 生成YouTube描述
- `generate_youtube_titles.py`: 生成YouTube标题

## 技术支持

如遇到问题，请检查：
1. 系统要求是否满足
2. API密钥是否正确配置
3. 输入文件是否存在且有效
4. 网络连接是否稳定 