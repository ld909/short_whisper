# 中文书籍B站封面生成器

`generate_b_cover.py` 是专门为中文书籍生成4:3比例B站封面的脚本。

## 功能特点

✅ **4:3比例设计** - 生成1920x1440像素的B站标准封面  
✅ **智能合成** - 将书籍封面放在背景图左侧，保持比例不变形  
✅ **断点续传** - 自动跳过已生成的封面，支持中断续传  
✅ **跨平台支持** - 自动适配Mac、Linux系统的路径配置  
✅ **批量处理** - 支持批量生成和单个指定处理  

## 输入文件

- **背景图片**: `audio_ficition/books/assets/bg.jpg`
- **书籍封面**: `{media_path}/books/zh/thumbnails_large/{uuid}.png`

## 输出文件

- **B站封面**: `{media_path}/books/zh/b_cover/{uuid}.png`

其中 `{media_path}` 根据系统自动选择：
- Intel Mac: `/Volumes/dhl/audio`
- Apple Silicon: `/Users/donghaoliu/Documents/audio`  
- Linux: `/mnt/dhl/audio`

## 使用方法

```bash
# 生成所有B站封面
python generate_b_cover.py

# 生成指定数量的封面
python generate_b_cover.py --count 10

# 强制重新生成已存在的封面
python generate_b_cover.py --force

# 生成指定UUID的封面
python generate_b_cover.py --uuid abc123-def456-...

# 预览模式（不实际生成）
python generate_b_cover.py --preview --count 5

# 检查当前状态
python generate_b_cover.py --status

# 调试模式
python generate_b_cover.py --debug
```

## 前置条件

1. **依赖模块**: 需要安装 `Pillow` 图像处理库
   ```bash
   pip install Pillow
   ```

2. **输入文件**: 需要先运行 `upscale_book_thumbnails.py` 生成超分辨率书籍封面

3. **背景图片**: 确保 `assets/bg.jpg` 存在

## 技术规格

- **输出尺寸**: 1920×1440像素 (4:3比例)
- **书籍封面区域**: 左侧30%区域，保持原始比例
- **图片格式**: PNG (保持最佳质量)
- **合成方式**: 背景拉伸 + 封面左对齐垂直居中

## 处理流程

1. 🔍 扫描 `thumbnails_large` 目录中的书籍封面
2. 📋 检查已存在的B站封面（断点续传）
3. 🎨 背景图片拉伸到目标尺寸
4. 📚 书籍封面缩放并放置在左侧
5. 💾 保存为PNG格式的B站封面

## 示例输出

```
📊 处理完成统计:
  🎯 目标文件: 59 个
  ✅ 成功生成: 59 个  
  ❌ 生成失败: 0 个
  ⏭️ 跳过处理: 0 个
  📈 成功率: 100.0%
```

## 注意事项

- 自动排除Mac系统的点开头文件 (如`.DS_Store`)
- 支持大批量处理，建议分批执行
- 生成的文件约3MB左右，请确保有足够存储空间
- 如遇问题，可使用 `--debug` 参数查看详细日志 