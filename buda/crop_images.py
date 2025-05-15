#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import cv2
import numpy as np
from pathlib import Path
import multiprocessing
from tqdm import tqdm
import concurrent.futures
import time
import shutil
import argparse
import importlib.util
import platform


# 获取基础路径
def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"


# 常量定义 - 全局变量
BASE_PATH = get_base_path()
DEFAULT_SOURCE = os.path.join(BASE_PATH, "buda_images")
DEFAULT_TARGET = os.path.join(BASE_PATH, "buda_images_crop")
MAX_HEIGHT = 1000
NUM_WORKERS = min(32, multiprocessing.cpu_count())
BATCH_SIZE = 100
COMPRESSION_PARAMS = [cv2.IMWRITE_JPEG_QUALITY, 95, cv2.IMWRITE_JPEG_OPTIMIZE, 1]

# 运行时全局变量
source_dir = DEFAULT_SOURCE
target_dir = DEFAULT_TARGET


# 检查是否有GPU支持
def check_gpu_support():
    """检查是否有CUDA支持"""
    cuda_available = False
    # 检查CUDA是否可用
    try:
        cuda_available = cv2.cuda.getCudaEnabledDeviceCount() > 0
        if cuda_available:
            print(f"检测到CUDA设备: {cv2.cuda.getCudaEnabledDeviceCount()}个")
    except:
        pass

    # 检查是否有cupy库
    has_cupy = importlib.util.find_spec("cupy") is not None
    if has_cupy:
        print("检测到CuPy库，可以使用GPU加速")

    return cuda_available, has_cupy


def crop_image_standard(args):
    """
    标准方式裁剪图像，保留y坐标≤MAX_HEIGHT的部分
    """
    image_path, output_path = args

    # 检查目标文件是否已存在且比源文件新，如果是则跳过
    if os.path.exists(output_path):
        if os.path.getmtime(output_path) >= os.path.getmtime(image_path):
            return f"跳过 {os.path.basename(image_path)}，已经处理过"

    try:
        # 对于JPEG文件使用优化的读取方式
        if image_path.lower().endswith((".jpg", ".jpeg")):
            # 只读取图像的元数据信息来检查尺寸
            img = cv2.imread(
                image_path, cv2.IMREAD_REDUCED_COLOR_2
            )  # 降低解析分辨率，加快读取
            if img is None:
                return f"无法读取图像 {image_path}"

            height, width = img.shape[:2]

            # 如果图像高度小于等于指定高度，直接复制文件而不是解码/编码
            if height * 2 <= MAX_HEIGHT:  # 考虑缩小比例
                shutil.copy2(image_path, output_path)
                return (
                    f"图像 {os.path.basename(image_path)} 高度≤{MAX_HEIGHT}，直接复制"
                )

            # 需要裁剪，再完整加载图像
            img = cv2.imread(image_path)
        else:
            # 其他格式直接读取
            img = cv2.imread(image_path)
            if img is None:
                return f"无法读取图像 {image_path}"

            height, width = img.shape[:2]

            # 如果图像高度小于等于指定高度，直接复制文件
            if height <= MAX_HEIGHT:
                shutil.copy2(image_path, output_path)
                return (
                    f"图像 {os.path.basename(image_path)} 高度≤{MAX_HEIGHT}，直接复制"
                )

        # 裁剪y坐标≤MAX_HEIGHT的部分
        cropped_img = img[0:MAX_HEIGHT, 0:width]
        # 优化图像保存参数
        cv2.imwrite(output_path, cropped_img, COMPRESSION_PARAMS)

        # 释放内存
        del img, cropped_img

        return f"已裁剪并保存 {os.path.basename(image_path)}"
    except Exception as e:
        return f"处理图像 {image_path} 时出错: {e}"


def crop_image_numpy(args):
    """
    使用NumPy高效裁剪图像，保留y坐标≤MAX_HEIGHT的部分
    """
    image_path, output_path = args

    # 检查目标文件是否已存在且比源文件新，如果是则跳过
    if os.path.exists(output_path):
        if os.path.getmtime(output_path) >= os.path.getmtime(image_path):
            return f"跳过 {os.path.basename(image_path)}，已经处理过"

    try:
        # 检查文件大小，对大文件使用优化方法
        file_size = os.path.getsize(image_path)

        # 小文件直接读取并处理
        if file_size < 1024 * 1024:  # 小于1MB的文件
            img = cv2.imread(image_path)
            if img is None:
                return f"无法读取图像 {image_path}"

            height, width = img.shape[:2]

            if height <= MAX_HEIGHT:
                shutil.copy2(image_path, output_path)
                return (
                    f"图像 {os.path.basename(image_path)} 高度≤{MAX_HEIGHT}，直接复制"
                )

            # 使用numpy切片操作，非常高效
            cropped_img = img[0:MAX_HEIGHT, :, :]
            cv2.imwrite(output_path, cropped_img, COMPRESSION_PARAMS)
            return f"已裁剪并保存 {os.path.basename(image_path)}"

        # 大文件使用内存映射方式处理，不需要完全加载到内存
        img_data = np.fromfile(image_path, dtype=np.uint8)
        img = cv2.imdecode(img_data, cv2.IMREAD_UNCHANGED)

        if img is None:
            return f"无法读取图像 {image_path}"

        height, width = img.shape[:2]

        if height <= MAX_HEIGHT:
            shutil.copy2(image_path, output_path)
            return f"图像 {os.path.basename(image_path)} 高度≤{MAX_HEIGHT}，直接复制"

        # 使用numpy高效处理
        cropped_img = img[0:MAX_HEIGHT, :, :]

        # 使用imencode直接编码到内存而不是磁盘
        _, buffer = cv2.imencode(".jpg", cropped_img, COMPRESSION_PARAMS)
        buffer.tofile(output_path)

        # 手动释放内存
        del img_data, img, cropped_img, buffer

        return f"已裁剪并保存(高效) {os.path.basename(image_path)}"
    except Exception as e:
        return f"处理图像 {image_path} 时出错: {e}"


def crop_image_cuda(args):
    """
    使用CUDA GPU加速裁剪图像
    """
    image_path, output_path = args

    # 检查目标文件是否已存在且比源文件新，如果是则跳过
    if os.path.exists(output_path):
        if os.path.getmtime(output_path) >= os.path.getmtime(image_path):
            return f"跳过 {os.path.basename(image_path)}，已经处理过"

    try:
        # 使用numpy先读取文件，避免OpenCV直接读取的IO开销
        img_data = np.fromfile(image_path, dtype=np.uint8)
        cpu_img = cv2.imdecode(img_data, cv2.IMREAD_UNCHANGED)

        if cpu_img is None:
            return f"无法读取图像 {image_path}"

        height, width = cpu_img.shape[:2]

        # 如果图像高度小于等于指定高度，直接复制文件
        if height <= MAX_HEIGHT:
            shutil.copy2(image_path, output_path)
            return f"图像 {os.path.basename(image_path)} 高度≤{MAX_HEIGHT}，直接复制"

        # 将图像上传到GPU
        gpu_img = cv2.cuda_GpuMat()
        gpu_img.upload(cpu_img)

        # 在GPU上裁剪
        gpu_cropped = gpu_img.rowRange(0, MAX_HEIGHT)

        # 下载回CPU
        cropped_img = gpu_cropped.download()

        # 保存裁剪后的图像
        _, buffer = cv2.imencode(".jpg", cropped_img, COMPRESSION_PARAMS)
        buffer.tofile(output_path)

        # 释放内存
        del img_data, cpu_img, cropped_img, buffer
        gpu_img.release()

        return f"已裁剪并保存(GPU) {os.path.basename(image_path)}"
    except Exception as e:
        # 如果GPU处理失败，回退到CPU处理
        return crop_image_numpy(args)


def crop_image_cupy(args):
    """
    使用CuPy库进行GPU加速裁剪
    需要安装: pip install cupy-cuda11x (对应CUDA版本)
    """
    import cupy as cp

    image_path, output_path = args

    # 检查目标文件是否已存在且比源文件新
    if os.path.exists(output_path):
        if os.path.getmtime(output_path) >= os.path.getmtime(image_path):
            return f"跳过 {os.path.basename(image_path)}，已经处理过"

    try:
        # 读取图像
        img_data = np.fromfile(image_path, dtype=np.uint8)
        cpu_img = cv2.imdecode(img_data, cv2.IMREAD_UNCHANGED)

        if cpu_img is None:
            return f"无法读取图像 {image_path}"

        height, width = cpu_img.shape[:2]

        # 如果图像高度小于等于指定高度，直接复制文件
        if height <= MAX_HEIGHT:
            shutil.copy2(image_path, output_path)
            return f"图像 {os.path.basename(image_path)} 高度≤{MAX_HEIGHT}，直接复制"

        # 转移到GPU
        gpu_img = cp.asarray(cpu_img)

        # 在GPU上裁剪
        gpu_cropped = gpu_img[:MAX_HEIGHT, :, :]

        # 转回CPU
        cropped_img = cp.asnumpy(gpu_cropped)

        # 保存裁剪后的图像
        _, buffer = cv2.imencode(".jpg", cropped_img, COMPRESSION_PARAMS)
        buffer.tofile(output_path)

        # 释放内存
        del img_data, cpu_img, cropped_img, buffer

        # 清除GPU内存缓存
        cp.get_default_memory_pool().free_all_blocks()

        return f"已裁剪并保存(CuPy) {os.path.basename(image_path)}"
    except Exception as e:
        # 如果GPU处理失败，回退到CPU处理
        return crop_image_numpy(args)


def select_best_method():
    """根据系统环境选择最佳处理方法"""
    cuda_available, has_cupy = check_gpu_support()

    if has_cupy:
        return "cupy"
    elif cuda_available:
        return "cuda"
    else:
        return "numpy"


def process_images(tasks, method="auto"):
    """
    处理图像任务列表
    """
    if method == "auto":
        method = select_best_method()

    # 根据方法选择处理函数
    if method == "cuda":
        crop_func = crop_image_cuda
    elif method == "cupy":
        crop_func = crop_image_cupy
    elif method == "numpy":
        crop_func = crop_image_numpy
    else:
        crop_func = crop_image_standard

    # 使用进程池处理图像
    with concurrent.futures.ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        results = list(
            tqdm(
                executor.map(crop_func, tasks, chunksize=16),
                total=len(tasks),
                desc=f"处理图像 (方法: {method})",
            )
        )

    return results, method


def benchmark(tasks):
    """
    对不同方法进行基准测试
    """
    methods = ["standard", "numpy"]
    cuda_available, has_cupy = check_gpu_support()

    if cuda_available:
        methods.append("cuda")
    if has_cupy:
        methods.append("cupy")

    # 对每种方法只处理前10张图像进行测试
    test_tasks = tasks[: min(10, len(tasks))]

    results = {}
    for method in methods:
        print(f"\n测试方法: {method}")
        start_time = time.time()

        # 选择处理函数
        if method == "cuda":
            crop_func = crop_image_cuda
        elif method == "cupy":
            crop_func = crop_image_cupy
        elif method == "numpy":
            crop_func = crop_image_numpy
        else:
            crop_func = crop_image_standard

        # 处理测试集
        for task in tqdm(test_tasks, desc=f"测试 {method}"):
            crop_func(task)

        elapsed = time.time() - start_time
        results[method] = elapsed
        print(
            f"{method}: {elapsed:.4f}秒, 平均 {elapsed/len(test_tasks)*1000:.2f}毫秒/图像"
        )

    # 找出最快的方法
    fastest_method = min(results, key=results.get)
    print(f"\n基准测试结果: 最快的方法是 {fastest_method}")
    return fastest_method


def main():
    # 使用全局变量
    global source_dir, target_dir, MAX_HEIGHT, NUM_WORKERS

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="高效图像裁剪工具")
    parser.add_argument(
        "--source",
        type=str,
        default=DEFAULT_SOURCE,
        help=f"源图像文件夹，默认: {DEFAULT_SOURCE}",
    )
    parser.add_argument(
        "--target",
        type=str,
        default=DEFAULT_TARGET,
        help=f"目标图像文件夹，默认: {DEFAULT_TARGET}",
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["standard", "numpy", "cuda", "cupy", "auto", "benchmark"],
        default="auto",
        help="裁剪方法: standard(标准), numpy(优化), cuda(GPU), cupy(GPU库), auto(自动选择), benchmark(基准测试)",
    )
    parser.add_argument(
        "--height", type=int, default=MAX_HEIGHT, help=f"裁剪高度，默认{MAX_HEIGHT}像素"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=NUM_WORKERS,
        help=f"工作进程数，默认{NUM_WORKERS}",
    )

    args = parser.parse_args()

    # 更新全局变量
    source_dir = args.source
    target_dir = args.target
    MAX_HEIGHT = args.height
    NUM_WORKERS = args.workers

    # 打印系统和路径信息
    print(f"当前操作系统: {platform.system()}")
    print(f"使用基础路径: {BASE_PATH}")
    print(f"源图像目录: {source_dir}")
    print(f"目标图像目录: {target_dir}")

    # 确保目标文件夹存在
    os.makedirs(target_dir, exist_ok=True)

    start_time = time.time()

    # 获取所有图像文件
    image_files = [
        f
        for f in os.listdir(source_dir)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp"))
    ]

    if not image_files:
        print(f"在 {source_dir} 中没有找到图像文件")
        return

    total_files = len(image_files)
    print(f"找到 {total_files} 个图像文件，开始处理...")

    # 准备参数列表
    tasks = []
    for filename in image_files:
        source_path = os.path.join(source_dir, filename)
        target_path = os.path.join(target_dir, filename)

        # 如果是常规文件，加入处理列表
        if os.path.isfile(source_path):
            tasks.append((source_path, target_path))

    # 如果是基准测试模式
    if args.method == "benchmark":
        fastest_method = benchmark(tasks)
        print(f"使用最快的方法 '{fastest_method}' 处理所有图像...")
        method = fastest_method
    else:
        method = args.method

    # 处理图像
    print(f"使用方法: {method}, 进程数: {NUM_WORKERS}, 裁剪高度: {MAX_HEIGHT}")
    results, actual_method = process_images(tasks, method=method)
    print(f"实际使用的处理方法: {actual_method}")

    # 统计结果
    skipped = sum(1 for r in results if r and "跳过" in r)
    copied = sum(1 for r in results if r and "直接复制" in r)
    cropped = sum(1 for r in results if r and "已裁剪" in r)
    errors = sum(1 for r in results if r and "出错" in r)

    end_time = time.time()
    elapsed = end_time - start_time

    print(f"\n处理完成！用时: {elapsed:.2f}秒")
    print(f"总计: {total_files}张图像")
    print(f"- 跳过: {skipped}张")
    print(f"- 直接复制: {copied}张")
    print(f"- 已裁剪: {cropped}张")
    print(f"- 处理出错: {errors}张")

    if total_files > 0 and elapsed > 0:
        print(f"平均处理速度: {total_files/elapsed:.2f}张/秒")
        print(f"每张图像平均处理时间: {elapsed*1000/total_files:.2f}毫秒")


if __name__ == "__main__":
    main()
