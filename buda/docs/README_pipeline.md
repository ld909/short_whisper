# 材料生成管道 - 优化版本

## 概述

这是一个优化后的材料生成管道控制系统，支持配置文件管理、结构化日志记录、错误重试机制和断点续传功能。

## 主要改进

### 1. 配置文件管理
- 所有步骤和参数通过 `pipeline_config.json` 配置文件管理
- 支持系统特定规则（如Mac系统跳过规则）
- 可配置超时时间、重试次数等参数
- 支持单个步骤的配置覆盖

### 2. 结构化日志记录
- 使用Python logging模块提供结构化日志
- 同时输出到控制台和文件
- 支持不同日志级别（DEBUG, INFO, WARNING, ERROR）
- 每次执行生成独立的日志文件

### 3. 错误处理和重试机制
- 自动重试失败的步骤，可配置重试次数和间隔
- 更细粒度的错误分类和处理
- 支持手动重试、跳过或停止执行
- 详细的错误信息记录

### 4. 断点续传
- 记录执行状态，支持从中断点恢复执行
- 跳过已完成的步骤，避免重复执行
- 支持从指定步骤开始执行

## 文件结构

```
buda/
├── main_pipeline.py          # 主控脚本（优化版本）
├── pipeline_config.json      # 配置文件
├── pipeline_logger.py        # 日志模块
├── pipeline_state.py         # 状态管理模块
├── pipeline_state.json       # 执行状态记录（自动生成）
├── README_pipeline.md        # 使用说明
└── logs/                     # 日志目录（自动创建）
    └── pipeline_YYYYMMDD_HHMMSS.log
```

## 使用方法

### 基本使用

```bash
# 正常执行管道
python main_pipeline.py

# 显示当前状态
python main_pipeline.py --status

# 重置管道状态
python main_pipeline.py --reset
```

### 高级功能

```bash
# 恢复中断的执行
python main_pipeline.py --resume

# 从指定步骤开始执行
python main_pipeline.py --start-from 5

# 使用自定义配置文件
python main_pipeline.py --config my_config.json

# 使用自定义状态文件
python main_pipeline.py --state my_state.json
```

### 命令行参数

- `--resume`: 恢复中断的执行
- `--start-from N`: 从第N步开始执行
- `--status`: 显示当前状态
- `--reset`: 重置管道状态
- `--config FILE`: 指定配置文件路径
- `--state FILE`: 指定状态文件路径

## 配置文件说明

### pipeline_config.json 结构

```json
{
  "pipeline": {
    "name": "材料生成管道",
    "version": "1.0",
    "timeout_seconds": 3600,      // 默认超时时间
    "max_retries": 2,             // 默认重试次数
    "retry_delay_seconds": 5      // 重试间隔
  },
  "logging": {
    "level": "INFO",              // 日志级别
    "format": "...",              // 日志格式
    "console_output": true,       // 控制台输出
    "file_output": true,          // 文件输出
    "log_directory": "logs"       // 日志目录
  },
  "system_rules": {
    "mac_skip_scripts": [...],    // Mac系统跳过的脚本
    "mac_skip_reason": "..."      // 跳过原因
  },
  "steps": [
    {
      "script": "script_name.py",
      "step_number": "1",
      "description": "步骤描述",
      "required": true,
      "timeout_override": null,    // 覆盖默认超时
      "max_retries_override": null // 覆盖默认重试次数
    }
  ]
}
```

## 错误处理

当步骤执行失败时，系统会提供以下选项：

- `y` - 继续执行下一步
- `n` - 停止执行
- `r` - 重试当前步骤
- `q` - 退出管道

## 日志记录

### 日志级别
- **INFO**: 正常执行信息
- **WARNING**: 警告信息（如重试、跳过步骤）
- **ERROR**: 错误信息
- **DEBUG**: 调试信息

### 日志文件
- 位置: `logs/pipeline_YYYYMMDD_HHMMSS.log`
- 编码: UTF-8
- 格式: 时间戳 - 模块名 - 级别 - 消息

## 状态管理

### 状态文件 (pipeline_state.json)
记录以下信息：
- 管道执行ID和时间
- 当前执行状态
- 已完成和失败的步骤
- 每个步骤的详细执行信息

### 状态类型
- `not_started`: 未开始
- `running`: 正在执行
- `completed`: 完成
- `failed`: 失败
- `interrupted`: 中断
- `completed_with_failures`: 部分失败完成

## 最佳实践

1. **配置管理**: 根据需要调整配置文件中的参数
2. **日志监控**: 定期检查日志文件，了解执行情况
3. **状态恢复**: 利用断点续传功能，避免重复执行
4. **错误处理**: 合理使用重试和跳过功能
5. **定期清理**: 清理旧的日志文件和状态文件

## 兼容性

- 保持与原版本的核心逻辑兼容
- 支持所有原有的脚本和功能
- 向后兼容，可以无缝替换原版本

## 故障排除

### 常见问题

1. **配置文件不存在**
   - 确保 `pipeline_config.json` 文件存在
   - 检查文件路径和权限

2. **日志目录创建失败**
   - 检查目录权限
   - 确保有足够的磁盘空间

3. **状态文件损坏**
   - 使用 `--reset` 参数重置状态
   - 手动删除 `pipeline_state.json` 文件

4. **脚本执行失败**
   - 查看详细日志文件
   - 检查脚本文件是否存在
   - 验证脚本权限和依赖

### 调试模式

修改配置文件中的日志级别为 `DEBUG` 以获取更详细的信息：

```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

## 更新日志

### v1.0 (优化版本)
- 添加配置文件管理
- 实现结构化日志记录
- 支持错误重试机制
- 添加断点续传功能
- 改进用户交互体验
- 增强错误处理能力
