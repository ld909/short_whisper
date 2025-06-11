# Thriller Story Parameter Generator

惊悚故事脚本参数生成器

## 功能概述

自动生成高质量的惊悚小说故事参数，支持6种主流惊悚子类型：

- **Psychological Thriller** (心理惊悚) - 侧重内心冲突和心理操纵
- **Legal Thriller** (法律惊悚) - 以法律体系和法庭辩论为背景
- **Action/Adventure Thriller** (动作/冒险惊悚) - 高节奏动作和追逐场面
- **Spy/Espionage Thriller** (间谍惊悚) - 国际阴谋和情报活动
- **Crime Thriller** (犯罪惊悚) - 执法者与罪犯的智力较量
- **Techno-Thriller** (科技惊悚) - 科技失控或被滥用的威胁

## 使用方法

### 基本使用
```bash
# 生成1个故事参数
python thriller_script_generator.py

# 生成多个故事参数
python thriller_script_generator.py -n 5

# 查看帮助
python thriller_script_generator.py --help
```

### 输出说明
- **输出目录**: `/Volumes/dhl/audio/thriller/story_param/`
- **文件格式**: `{索引号}.txt` (例如: 1.txt, 2.txt, 3.txt...)
- **内容**: 完整的英文故事创作提示词，可直接用于AI生成150,000+词的有声书脚本

### 生成的故事参数包含
- 核心惊悚蓝图（子类型、悬念机制、节奏技巧等）
- 详细角色设定（主角、反派、配角）
- 完整情节结构（引发事件、转折、高潮、结局）
- 具体设定环境（地点、时间、环境压力）
- 调查/揭示元素（线索发现、证据类型、反转触发）

### 特色功能
1. **自动索引管理** - 避免覆盖已有文件
2. **多样化组合** - 丰富的故事元素随机组合
3. **类型特化元素** - 针对不同子类型的专门配置
4. **专业级质量** - 诺贝尔奖水准的故事参数生成
5. **Mac系统适配** - 自动排除系统生成的点文件

## 配置文件
`config.json` 包含所有可选的故事元素配置，支持自定义修改。

## 注意事项
- 确保 `config.json` 文件与脚本在同一目录
- 输出目录会自动创建
- 生成的提示词为英文，适合国际化内容创作

---
*版本: 1.0 | 作者: 惊悚故事生成系统* 