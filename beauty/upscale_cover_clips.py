"""
Beauty内容超分处理工具

功能说明:
此脚本综合了视频和图片的超分辨率处理功能，专门用于处理Beauty项目的内容。
使用阿里云视频增强和图像增强服务进行超分辨率处理。

主要功能:
1. 对指定index目录下的视频进行超分处理
2. 对指定index目录下的图片进行超分处理
3. 支持命令行指定index参数
4. 支持批量处理和断点续传

输入路径:
- 视频: /Users/donghaoliu/Documents/beauty/[index]/clips/*.mp4
- 图片: /Users/donghaoliu/Documents/beauty/[index]/cover_small/*.png

输出路径:
- 视频: /Users/donghaoliu/Documents/beauty/[index]/clips_large/
- 图片: /Users/donghaoliu/Documents/beauty/[index]/cover_large/

使用方法:
1. 处理指定index: python upscale_cover_clips.py --index 1
2. 强制重新处理: python upscale_cover_clips.py --index 2 --force
3. 指定视频比特率: python upscale_cover_clips.py --index 3 --bitrate 8
4. 指定图片超分倍数: python upscale_cover_clips.py --index 4 --scale 4
5. 只处理视频: python upscale_cover_clips.py --index 5 --video-only
6. 只处理图片: python upscale_cover_clips.py --index 6 --image-only

注意:
- 需要设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET
- 脚本支持断点续传，中断后可从上次停止的位置继续处理
- 自动排除以点开头的系统文件
"""

import os
import sys
import time
import argparse
import requests
import glob
import re
import io
from tqdm import tqdm
from typing import Optional, List, Tuple
from PIL import Image

# 阿里云视频增强相关导入
from alibabacloud_videoenhan20200320.client import Client as VideoEnhanClient
from alibabacloud_videoenhan20200320 import models as videoenhan_20200320_models
from alibabacloud_videoenhan20200320.models import SuperResolveVideoAdvanceRequest

# 阿里云图像增强相关导入
from alibabacloud_imageenhan20190930.client import Client as ImageEnhanClient
from alibabacloud_imageenhan20190930 import models as imageenhan_20190930_models
from alibabacloud_imageenhan20190930.models import (
    MakeSuperResolutionImageAdvanceRequest,
)

# 通用导入
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient

# 异步任务查询相关导入
from alibabacloud_viapi20230117.client import Client as ViapiClient
from alibabacloud_viapi20230117.models import GetAsyncJobResultRequest


def create_video_client() -> VideoEnhanClient:
    """
    创建阿里云视频增强客户端
    @return: VideoEnhanClient
    @throws Exception
    """
    access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
    access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")

    if not access_key_id or not access_key_secret:
        print("错误: 未找到阿里云访问密钥")
        print(
            "请设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET"
        )
        sys.exit(1)

    try:
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint="videoenhan.cn-shanghai.aliyuncs.com",
            region_id="cn-shanghai",
        )
        return VideoEnhanClient(config)
    except Exception as e:
        print(f"初始化阿里云视频客户端时出错: {e}")
        sys.exit(1)


def create_image_client() -> ImageEnhanClient:
    """
    创建阿里云图像增强客户端
    @return: ImageEnhanClient
    @throws Exception
    """
    access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
    access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")

    if not access_key_id or not access_key_secret:
        print("错误: 未找到阿里云访问密钥")
        print(
            "请设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET"
        )
        sys.exit(1)

    try:
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint="imageenhan.cn-shanghai.aliyuncs.com",
            region_id="cn-shanghai",
        )
        return ImageEnhanClient(config)
    except Exception as e:
        print(f"初始化阿里云图像客户端时出错: {e}")
        sys.exit(1)


def create_viapi_client() -> ViapiClient:
    """
    创建阿里云VIAPI客户端，用于查询异步任务结果
    @return: ViapiClient
    @throws Exception
    """
    access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
    access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")

    if not access_key_id or not access_key_secret:
        print("错误: 未找到阿里云访问密钥")
        sys.exit(1)

    try:
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint="viapi.cn-shanghai.aliyuncs.com",
        )
        return ViapiClient(config)
    except Exception as e:
        print(f"初始化VIAPI客户端时出错: {e}")
        sys.exit(1)


def query_async_job_result(
    viapi_client: ViapiClient, job_id: str, max_wait_time: int = 1800
) -> Optional[str]:
    """
    查询异步任务结果，直到任务完成或超时
    """
    start_time = time.time()
    check_interval = 10  # 每10秒查询一次

    print(f"🔍 开始查询异步任务结果，任务ID: {job_id}")
    print(f"⏰ 最大等待时间: {max_wait_time}秒")

    while True:
        try:
            request = GetAsyncJobResultRequest(job_id=job_id)
            runtime = util_models.RuntimeOptions()
            response = viapi_client.get_async_job_result_with_options(request, runtime)

            if response and response.body and response.body.data:
                data = response.body.data
                status = getattr(data, "status", None)
                if status is None:
                    status = getattr(data, "Status", None)

                result = getattr(data, "result", None)
                if result is None:
                    result = getattr(data, "Result", None)

                print(f"📊 任务状态: {status}")

                if status in ["PROCESS_SUCCESS", "FINISH"]:
                    if result:
                        try:
                            import json

                            if isinstance(result, str):
                                result_dict = json.loads(result)
                            else:
                                result_dict = result

                            video_url = None
                            if "VideoUrl" in result_dict:
                                video_url = result_dict["VideoUrl"]
                            elif "videoUrl" in result_dict:
                                video_url = result_dict["videoUrl"]
                            elif "video_url" in result_dict:
                                video_url = result_dict["video_url"]

                            if video_url:
                                print(f"✅ 任务完成，获取到视频URL")
                                return video_url
                            else:
                                print(f"❌ 任务完成但未找到视频URL")
                                return None
                        except Exception as e:
                            print(f"❌ 解析结果数据时出错: {e}")
                            return None
                    else:
                        print(f"❌ 任务完成但未返回结果数据")
                        return None

                elif status in ["PROCESS_FAIL", "FAIL"]:
                    print(f"❌ 任务执行失败")
                    if result:
                        print(f"错误信息: {result}")
                    return None

                elif status in [
                    "PROCESS",
                    "RUNNING",
                    "PENDING",
                    "PROCESS_RUNNING",
                    "PROCESSING",
                ]:
                    elapsed_time = time.time() - start_time
                    print(f"⏳ 任务进行中，已等待 {elapsed_time:.0f}秒...")

                    if elapsed_time > max_wait_time:
                        print(f"⏰ 任务等待超时（{max_wait_time}秒）")
                        return None

                    print(f"💤 等待{check_interval}秒后再次查询...")
                    time.sleep(check_interval)
                    continue
                else:
                    print(f"❓ 未知任务状态: {status}")
                    if status is None:
                        elapsed_time = time.time() - start_time
                        if elapsed_time < 60:
                            print(f"💤 等待{check_interval}秒后再次查询...")
                            time.sleep(check_interval)
                            continue
                    return None
            else:
                print(f"❌ 查询响应为空或无数据")
                return None

        except Exception as e:
            print(f"❌ 查询异步任务结果时出错: {e}")
            elapsed_time = time.time() - start_time
            if elapsed_time > max_wait_time:
                print(f"⏰ 查询超时（{max_wait_time}秒）")
                return None
            print(f"💤 等待{check_interval}秒后重试...")
            time.sleep(check_interval)


def upscale_video(
    client: VideoEnhanClient, video_path: str, bit_rate: int = 5, max_retries: int = 3
) -> Optional[str]:
    """
    使用阿里云视频增强服务进行超分辨率处理
    """
    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        return None

    file_size = os.path.getsize(video_path)
    print(f"📹 视频文件大小: {file_size / (1024*1024):.2f} MB")

    for attempt in range(max_retries):
        try:
            print(f"正在提交视频超分任务 (尝试 {attempt+1}/{max_retries})...")
            print(f"处理本地文件: {video_path}")

            with open(video_path, "rb") as video_file:
                request = SuperResolveVideoAdvanceRequest(
                    video_url_object=video_file, bit_rate=bit_rate
                )
                runtime = util_models.RuntimeOptions()
                print("🚀 正在调用阿里云视频超分API...")
                response = client.super_resolve_video_advance(request, runtime)

                if response and response.body:
                    if hasattr(response.body, "request_id"):
                        job_id = response.body.request_id
                        print(f"✅ 异步任务提交成功")
                        print(f"🆔 任务ID: {job_id}")

                        viapi_client = create_viapi_client()
                        result_url = query_async_job_result(viapi_client, job_id)

                        if result_url:
                            return result_url
                        else:
                            print(f"❌ 异步任务查询失败")
                            return None

                    elif (
                        hasattr(response.body, "data")
                        and response.body.data
                        and hasattr(response.body.data, "video_url")
                        and response.body.data.video_url
                    ):
                        result_url = response.body.data.video_url
                        print(f"✅ 视频超分处理成功（同步返回）")
                        print(f"📥 处理后视频URL: {result_url}")
                        return result_url
                    else:
                        print(f"❌ API返回数据格式异常")
                        return None
                else:
                    print(f"❌ API响应为空")
                    return None

        except Exception as e:
            print(f"视频超分处理出错 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                retry_delay = (attempt + 1) * 10
                print(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print(f"达到最大重试次数 ({max_retries})，处理失败")
                return None


def upscale_image(
    client: ImageEnhanClient,
    image_path: str,
    upscale_factor: int = 2,
    max_retries: int = 3,
):
    """
    使用阿里云图像增强服务进行超分辨率处理
    """
    if not os.path.exists(image_path):
        print(f"❌ 图片文件不存在: {image_path}")
        return None

    for attempt in range(max_retries):
        try:
            print(f"正在处理图片超分 (尝试 {attempt+1}/{max_retries})...")
            print(f"处理本地文件: {image_path}")

            with open(image_path, "rb") as img_file:
                request = MakeSuperResolutionImageAdvanceRequest(
                    url_object=img_file,
                    mode="base",
                    upscale_factor=upscale_factor,
                )
                runtime = util_models.RuntimeOptions()
                response = client.make_super_resolution_image_advance(request, runtime)

                if (
                    response
                    and response.body
                    and response.body.data
                    and response.body.data.url
                ):
                    result_url = response.body.data.url
                    print(f"正在下载超分后的图片...")
                    img_response = requests.get(result_url, timeout=30)
                    img_response.raise_for_status()
                    print(f"✅ 图片超分处理成功")
                    return img_response.content
                else:
                    print(f"❌ API返回数据格式异常或未包含图片URL")
                    return None

        except Exception as e:
            print(f"图片超分处理出错 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                retry_delay = (attempt + 1) * 5
                print(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print(f"达到最大重试次数 ({max_retries})，处理失败")
                return None


def download_video(video_url: str, output_path: str) -> bool:
    """
    下载处理后的视频到本地
    """
    try:
        print(f"📥 正在下载超分后的视频...")
        print(f"下载URL: {video_url}")
        print(f"保存到: {output_path}")

        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        response = requests.get(video_url, stream=True, timeout=60)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))

        with open(output_path, "wb") as f:
            if total_size > 0:
                with tqdm(
                    total=total_size, unit="B", unit_scale=True, desc="下载进度"
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            else:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ 视频下载成功")
            print(f"📁 文件路径: {output_path}")
            print(f"📏 文件大小: {file_size / (1024*1024):.2f} MB")
            return True
        else:
            print(f"❌ 文件下载后未找到: {output_path}")
            return False

    except Exception as e:
        print(f"❌ 下载视频时出错: {e}")
        return False


def save_upscaled_image(image_data: bytes, output_path: str) -> bool:
    """
    保存超分后的图片到文件
    """
    if not image_data:
        print(f"⚠️ 警告: 图片数据为空，跳过保存")
        return False

    try:
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        image = Image.open(io.BytesIO(image_data))
        image.save(output_path, "PNG")

        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"📁 已保存超分图片到: {output_path} (大小: {file_size} 字节)")
            return True
        else:
            print(f"❌ 文件保存后未找到: {output_path}")
            return False

    except Exception as e:
        print(f"❌ 保存图片到 {output_path} 时出错: {e}")
        return False


def get_video_files(index: int) -> List[str]:
    """
    获取指定index目录下的视频文件列表
    """
    video_dir = f"/Users/donghaoliu/Documents/beauty/{index}/clips"

    if not os.path.exists(video_dir):
        print(f"❌ 视频目录不存在: {video_dir}")
        return []

    mp4_files = glob.glob(os.path.join(video_dir, "*.mp4"))
    # 过滤掉点开头的系统文件
    valid_files = [f for f in mp4_files if not os.path.basename(f).startswith(".")]

    print(f"📹 在目录 {video_dir} 找到 {len(valid_files)} 个MP4文件")
    return sorted(valid_files)


def get_image_files(index: int) -> List[str]:
    """
    获取指定index目录下的图片文件列表
    """
    image_dir = f"/Users/donghaoliu/Documents/beauty/{index}/cover_small"

    if not os.path.exists(image_dir):
        print(f"❌ 图片目录不存在: {image_dir}")
        return []

    image_files = glob.glob(os.path.join(image_dir, "*.png"))
    # 过滤掉点开头的系统文件
    valid_files = [f for f in image_files if not os.path.basename(f).startswith(".")]

    print(f"🖼️ 在目录 {image_dir} 找到 {len(valid_files)} 个PNG文件")
    return sorted(valid_files)


def get_existing_upscaled_videos(index: int) -> set:
    """
    获取已存在的超分视频文件名集合
    """
    output_dir = f"/Users/donghaoliu/Documents/beauty/{index}/clips_large"

    if not os.path.exists(output_dir):
        return set()

    output_files = glob.glob(os.path.join(output_dir, "*.mp4"))
    existing_files = set()

    for output_file in output_files:
        basename = os.path.basename(output_file)
        if not basename.startswith("."):
            existing_files.add(basename)

    return existing_files


def get_existing_upscaled_images(index: int) -> set:
    """
    获取已存在的超分图片文件名集合
    """
    output_dir = f"/Users/donghaoliu/Documents/beauty/{index}/cover_large"

    if not os.path.exists(output_dir):
        return set()

    output_files = glob.glob(os.path.join(output_dir, "*.png"))
    existing_files = set()

    for output_file in output_files:
        basename = os.path.basename(output_file)
        if not basename.startswith("."):
            existing_files.add(basename)

    return existing_files


def process_videos(
    index: int, video_client: VideoEnhanClient, bit_rate: int = 5, force: bool = False
) -> bool:
    """
    处理指定index的视频超分
    """
    print(f"\n🎬 开始处理 index {index} 的视频超分...")

    # 获取视频文件列表
    video_files = get_video_files(index)
    if not video_files:
        print(f"未找到 index {index} 的视频文件")
        return False

    # 获取已存在的超分视频
    existing_videos = get_existing_upscaled_videos(index)

    # 过滤需要处理的视频
    videos_to_process = []
    for video_path in video_files:
        filename = os.path.basename(video_path)
        if force or filename not in existing_videos:
            videos_to_process.append(video_path)
        else:
            print(f"⏭️ 跳过已存在的视频: {filename}")

    if not videos_to_process:
        print(f"✅ index {index} 的所有视频都已完成超分处理")
        return True

    print(f"📊 需要处理的视频数量: {len(videos_to_process)}")

    success_count = 0
    failure_count = 0

    with tqdm(total=len(videos_to_process), desc=f"index {index} 视频超分进度") as pbar:
        for video_path in videos_to_process:
            filename = os.path.basename(video_path)
            output_path = (
                f"/Users/donghaoliu/Documents/beauty/{index}/clips_large/{filename}"
            )

            print(f"\n=== 处理视频: {filename} ===")

            # 进行视频超分处理
            result_url = upscale_video(video_client, video_path, bit_rate)

            if result_url:
                if download_video(result_url, output_path):
                    success_count += 1
                    print(f"✅ 视频 {filename} 超分处理成功")
                else:
                    failure_count += 1
                    print(f"❌ 视频 {filename} 下载失败")
            else:
                failure_count += 1
                print(f"❌ 视频 {filename} 超分处理失败")

            pbar.update(1)

            # 添加延迟，避免API调用过于频繁
            if success_count + failure_count < len(videos_to_process):
                time.sleep(2)

    print(f"\n=== 视频处理完成统计 ===")
    print(f"✅ 成功处理: {success_count}/{len(videos_to_process)} 个视频")
    print(f"❌ 处理失败: {failure_count}/{len(videos_to_process)} 个视频")
    print(f"📊 成功率: {success_count/len(videos_to_process)*100:.1f}%")

    return success_count > 0


def process_images(
    index: int,
    image_client: ImageEnhanClient,
    upscale_factor: int = 2,
    force: bool = False,
) -> bool:
    """
    处理指定index的图片超分
    """
    print(f"\n🖼️ 开始处理 index {index} 的图片超分...")

    # 获取图片文件列表
    image_files = get_image_files(index)
    if not image_files:
        print(f"未找到 index {index} 的图片文件")
        return False

    # 获取已存在的超分图片
    existing_images = get_existing_upscaled_images(index)

    # 过滤需要处理的图片
    images_to_process = []
    for image_path in image_files:
        filename = os.path.basename(image_path)
        if force or filename not in existing_images:
            images_to_process.append(image_path)
        else:
            print(f"⏭️ 跳过已存在的图片: {filename}")

    if not images_to_process:
        print(f"✅ index {index} 的所有图片都已完成超分处理")
        return True

    print(f"📊 需要处理的图片数量: {len(images_to_process)}")

    success_count = 0
    failure_count = 0

    with tqdm(total=len(images_to_process), desc=f"index {index} 图片超分进度") as pbar:
        for image_path in images_to_process:
            filename = os.path.basename(image_path)
            output_path = (
                f"/Users/donghaoliu/Documents/beauty/{index}/cover_large/{filename}"
            )

            print(f"\n=== 处理图片: {filename} ===")

            # 进行图片超分处理
            upscaled_data = upscale_image(image_client, image_path, upscale_factor)

            if upscaled_data:
                if save_upscaled_image(upscaled_data, output_path):
                    success_count += 1
                    print(f"✅ 图片 {filename} 超分处理成功")
                else:
                    failure_count += 1
                    print(f"❌ 图片 {filename} 保存失败")
            else:
                failure_count += 1
                print(f"❌ 图片 {filename} 超分处理失败")

            pbar.update(1)

            # 添加延迟，避免API调用过于频繁
            if success_count + failure_count < len(images_to_process):
                time.sleep(2)

    print(f"\n=== 图片处理完成统计 ===")
    print(f"✅ 成功处理: {success_count}/{len(images_to_process)} 个图片")
    print(f"❌ 处理失败: {failure_count}/{len(images_to_process)} 个图片")
    print(f"📊 成功率: {success_count/len(images_to_process)*100:.1f}%")

    return success_count > 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Beauty内容超分处理工具")

    parser.add_argument(
        "--index", type=int, required=True, help="指定要处理的index目录（必填）"
    )
    parser.add_argument("--force", action="store_true", help="强制重新处理所有文件")
    parser.add_argument("--bitrate", type=int, default=5, help="视频比特率（默认: 5）")
    parser.add_argument(
        "--scale",
        type=int,
        choices=[2, 4],
        default=2,
        help="图片超分倍数，支持2x或4x（默认: 2）",
    )
    parser.add_argument("--video-only", action="store_true", help="只处理视频文件")
    parser.add_argument("--image-only", action="store_true", help="只处理图片文件")

    args = parser.parse_args()

    # 验证参数
    if args.index <= 0:
        print("❌ 错误：index必须大于0")
        return

    if args.video_only and args.image_only:
        print("❌ 错误：不能同时指定 --video-only 和 --image-only")
        return

    print("🔍 Beauty内容超分处理器")
    print("=" * 50)
    print(f"📂 处理目录: index {args.index}")
    print(f"🎬 视频比特率: {args.bitrate}")
    print(f"🖼️ 图片超分倍数: {args.scale}x")
    print(f"🔄 强制重新处理: {'是' if args.force else '否'}")

    # 确定处理模式
    process_videos_flag = not args.image_only
    process_images_flag = not args.video_only

    print(f"🎯 处理模式: ", end="")
    if process_videos_flag and process_images_flag:
        print("视频 + 图片")
    elif process_videos_flag:
        print("仅视频")
    elif process_images_flag:
        print("仅图片")

    print()

    # 检查目录是否存在
    base_dir = f"/Users/donghaoliu/Documents/beauty/{args.index}"
    if not os.path.exists(base_dir):
        print(f"❌ 错误：目录不存在 {base_dir}")
        return

    # 创建客户端
    video_client = None
    image_client = None

    if process_videos_flag:
        print("🔧 初始化视频增强客户端...")
        video_client = create_video_client()
        print("✅ 视频增强客户端初始化成功")

    if process_images_flag:
        print("🔧 初始化图像增强客户端...")
        image_client = create_image_client()
        print("✅ 图像增强客户端初始化成功")

    # 处理视频
    video_success = True
    if process_videos_flag:
        video_success = process_videos(
            args.index, video_client, args.bitrate, args.force
        )

    # 处理图片
    image_success = True
    if process_images_flag:
        image_success = process_images(args.index, image_client, args.scale, args.force)

    # 输出最终结果
    print(f"\n{'='*60}")
    print(f"🎉 index {args.index} 处理完成!")

    if process_videos_flag:
        print(f"🎬 视频处理: {'✅ 成功' if video_success else '❌ 失败'}")

    if process_images_flag:
        print(f"🖼️ 图片处理: {'✅ 成功' if image_success else '❌ 失败'}")

    overall_success = video_success and image_success
    print(f"📊 总体结果: {'✅ 成功' if overall_success else '❌ 失败'}")
    print(f"{'='*60}")

    if overall_success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
