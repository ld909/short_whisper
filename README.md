# 高效图像裁剪工具

这是一个高效的图像裁剪工具，可以快速裁剪大量图像，保留指定高度的部分。工具支持多种处理方式，包括标准OpenCV处理、NumPy优化处理以及GPU加速处理（如果可用）。

## 特点

- 多进程并行处理，充分利用CPU核心
- 自动检测和使用GPU加速（如果可用）
- 多种处理策略：标准、NumPy优化、CUDA GPU加速和CuPy加速
- 自动跳过已处理文件
- 智能处理：小图像直接复制而不裁剪
- 内置基准测试功能，自动选择最快方法
- 详细的进度显示和处理统计

## 安装

```bash
# 安装基本依赖
pip install -r requirements.txt

# 如果需要GPU加速，根据您的CUDA版本安装CuPy
# 例如，对于CUDA 11.x:
pip install cupy-cuda11x
```

## 使用方法

```bash
# 基本用法，使用默认参数
python crop_images.py

# 指定源和目标文件夹
python crop_images.py --source /path/to/source --target /path/to/target

# 选择处理方法
python crop_images.py --method numpy  # 使用NumPy优化方法
python crop_images.py --method cuda   # 使用CUDA GPU加速
python crop_images.py --method cupy   # 使用CuPy库GPU加速
python crop_images.py --method auto   # 自动选择最佳方法（默认）

# 运行基准测试，找出当前系统最快的方法
python crop_images.py --method benchmark

# 指定裁剪高度（默认1000像素）
python crop_images.py --height 800

# 指定工作进程数
python crop_images.py --workers 16
```

## 参数说明

- `--source`: 源图像文件夹路径
- `--target`: 目标图像文件夹路径
- `--method`: 处理方法，可选 standard/numpy/cuda/cupy/auto/benchmark
- `--height`: 裁剪高度（像素）
- `--workers`: 并行处理的进程数
