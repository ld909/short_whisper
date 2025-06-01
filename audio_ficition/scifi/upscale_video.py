"""
视频超分辨率处理工具

功能说明:
此脚本使用阿里云视频增强服务对视频文件进行超分辨率处理，提升视频质量和分辨率。
支持异步任务处理，自动轮询查询任务状态直到完成。

主要功能:
1. 自动扫描输入目录中的MP4文件（路径根据操作系统自动选择）
2. 调用阿里云视频增强服务进行异步超分辨率处理
3. 自动轮询查询任务状态和结果
4. 下载处理后的高清视频到指定目录
5. 支持断点续传，避免重复处理

输入:
- macOS: /Volumes/dhl/audio/scifi/starting_mp4/
- Ubuntu: /media/dhl/audio/scifi/starting_mp4/

输出:
- macOS: /Volumes/dhl/audio/scifi/mp4_upscaled/story_index.mp4
- Ubuntu: /media/dhl/audio/scifi/mp4_upscaled/story_index.mp4

使用方法:
1. 基本使用: python upscale_video.py
2. 指定比特率: python upscale_video.py --bitrate 10
3. 强制重新处理: python upscale_video.py --force
4. 指定处理范围: python upscale_video.py --start 1 --end 10

处理流程:
1. 检测操作系统并选择相应的媒体路径
2. 扫描starting_mp4目录中的所有MP4文件
3. 检查是否已存在超分后的文件（断点续传）
4. 提交异步任务到阿里云视频增强服务
5. 获取任务ID，开始轮询查询
6. 等待任务状态变为PROCESS_SUCCESS
7. 提取视频URL并下载到本地

注意:
- 需要设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET
- 处理本地文件，使用阿里云视频增强的advance接口
- 支持多种视频格式（mp4, avi, mov等）
- 默认最大等待时间为30分钟（1800秒）
- 每10秒查询一次任务状态
- 自动跳过点开头的系统文件
- 自动检测操作系统并使用相应的媒体挂载路径
"""

import os
import sys
import time
import argparse
import requests
import glob
import re
import platform
from tqdm import tqdm
from typing import Optional, List, Tuple

from alibabacloud_videoenhan20200320.client import Client as VideoEnhanClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_videoenhan20200320 import models as videoenhan_20200320_models
from alibabacloud_videoenhan20200320.models import (
    SuperResolveVideoAdvanceRequest,
)
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient

# 添加异步任务查询相关的导入
from alibabacloud_viapi20230117.client import Client as ViapiClient
from alibabacloud_viapi20230117.models import GetAsyncJobResultRequest


def create_client() -> VideoEnhanClient:
    """
    创建阿里云视频增强客户端
    @return: VideoEnhanClient
    @throws Exception
    """
    # 从环境变量获取访问密钥
    access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
    access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")

    if not access_key_id or not access_key_secret:
        print("错误: 未找到阿里云访问密钥")
        print(
            "请设置环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET"
        )
        print("例如:")
        print("export ALIBABA_CLOUD_ACCESS_KEY_ID='your-access-key-id'")
        print("export ALIBABA_CLOUD_ACCESS_KEY_SECRET='your-access-key-secret'")
        sys.exit(1)

    try:
        # 使用更标准的配置方式
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            endpoint="videoenhan.cn-shanghai.aliyuncs.com",
            region_id="cn-shanghai",
        )

        return VideoEnhanClient(config)
    except Exception as e:
        print(f"初始化阿里云客户端时出错: {e}")
        sys.exit(1)


def create_viapi_client() -> ViapiClient:
    """
    创建阿里云VIAPI客户端，用于查询异步任务结果
    @return: ViapiClient
    @throws Exception
    """
    # 从环境变量获取访问密钥
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

    Args:
        viapi_client: VIAPI客户端
        job_id: 任务ID（RequestId）
        max_wait_time: 最大等待时间（秒）

    Returns:
        成功时返回视频URL，失败时返回None
    """
    start_time = time.time()
    check_interval = 10  # 每10秒查询一次

    print(f"🔍 开始查询异步任务结果，任务ID: {job_id}")
    print(f"⏰ 最大等待时间: {max_wait_time}秒")

    while True:
        try:
            # 创建查询请求
            request = GetAsyncJobResultRequest(job_id=job_id)
            runtime = util_models.RuntimeOptions()

            # 查询任务状态
            response = viapi_client.get_async_job_result_with_options(request, runtime)

            if response and response.body and response.body.data:
                data = response.body.data

                # 获取状态和结果
                status = getattr(data, "status", None)
                if status is None:
                    status = getattr(data, "Status", None)

                result = getattr(data, "result", None)
                if result is None:
                    result = getattr(data, "Result", None)

                print(f"📊 任务状态: {status}")

                if status in ["PROCESS_SUCCESS", "FINISH"]:
                    # 任务完成，提取视频URL
                    if result:
                        try:
                            # 解析JSON结果
                            import json

                            if isinstance(result, str):
                                result_dict = json.loads(result)
                            else:
                                result_dict = result

                            # 查找视频URL
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
                    # 任务还在进行中
                    elapsed_time = time.time() - start_time
                    print(f"⏳ 任务进行中，已等待 {elapsed_time:.0f}秒...")

                    # 检查是否超时
                    if elapsed_time > max_wait_time:
                        print(f"⏰ 任务等待超时（{max_wait_time}秒）")
                        return None

                    # 等待一段时间后再次查询
                    print(f"💤 等待{check_interval}秒后再次查询...")
                    time.sleep(check_interval)
                    continue
                else:
                    print(f"❓ 未知任务状态: {status}")

                    # 如果状态为None，可能任务还没开始，继续等待
                    if status is None:
                        elapsed_time = time.time() - start_time
                        if elapsed_time < 60:  # 前60秒继续等待
                            print(f"💤 等待{check_interval}秒后再次查询...")
                            time.sleep(check_interval)
                            continue

                    return None
            else:
                print(f"❌ 查询响应为空或无数据")
                return None

        except Exception as e:
            print(f"❌ 查询异步任务结果时出错: {e}")

            # 检查是否超时
            elapsed_time = time.time() - start_time
            if elapsed_time > max_wait_time:
                print(f"⏰ 查询超时（{max_wait_time}秒）")
                return None

            # 等待后重试
            print(f"💤 等待{check_interval}秒后重试...")
            time.sleep(check_interval)


def upscale_video(
    client: VideoEnhanClient,
    video_path: str,
    bit_rate: int = 5,
    max_retries: int = 3,
) -> Optional[str]:
    """
    使用阿里云视频增强服务进行超分辨率处理

    Args:
        client: 阿里云视频增强客户端
        video_path: 本地视频文件路径
        bit_rate: 视频比特率（默认5）
        max_retries: 最大重试次数

    Returns:
        处理后的视频URL，失败时返回 None
    """

    # 检查文件是否存在
    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        return None

    # 检查文件大小
    file_size = os.path.getsize(video_path)
    print(f"📹 视频文件大小: {file_size / (1024*1024):.2f} MB")

    for attempt in range(max_retries):
        try:
            print(f"正在提交视频超分任务 (尝试 {attempt+1}/{max_retries})...")
            print(f"处理本地文件: {video_path}")

            # 打开本地视频文件
            with open(video_path, "rb") as video_file:
                # 创建视频超分请求（使用本地文件）
                request = SuperResolveVideoAdvanceRequest(
                    video_url_object=video_file, bit_rate=bit_rate
                )

                # 运行时选项
                runtime = util_models.RuntimeOptions()

                print("🚀 正在调用阿里云视频超分API...")

                # 调用API (使用advance方法处理本地文件)
                response = client.super_resolve_video_advance(request, runtime)

                if response and response.body:
                    # 检查是否是异步任务
                    if hasattr(response.body, "request_id"):
                        # 这是异步任务，提取RequestId
                        job_id = response.body.request_id
                        print(f"✅ 异步任务提交成功")
                        print(f"🆔 任务ID: {job_id}")

                        # 创建VIAPI客户端来查询任务结果
                        viapi_client = create_viapi_client()

                        # 查询异步任务结果
                        result_url = query_async_job_result(viapi_client, job_id)

                        if result_url:
                            return result_url
                        else:
                            print(f"❌ 异步任务查询失败")
                            return None

                    # 检查是否有直接的视频URL（同步返回）
                    elif (
                        hasattr(response.body, "data")
                        and response.body.data
                        and hasattr(response.body.data, "video_url")
                        and response.body.data.video_url
                    ):
                        # 获取处理后的视频URL
                        result_url = response.body.data.video_url
                        print(f"✅ 视频超分处理成功（同步返回）")
                        print(f"📥 处理后视频URL: {result_url}")
                        return result_url
                    else:
                        print(f"❌ API返回数据格式异常")
                        print(f"响应内容: {response}")
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


def download_video(video_url: str, output_path: str) -> bool:
    """
    下载处理后的视频到本地

    Args:
        video_url: 视频下载URL
        output_path: 输出文件路径

    Returns:
        下载成功返回True，失败返回False
    """
    try:
        print(f"📥 正在下载超分后的视频...")
        print(f"下载URL: {video_url}")
        print(f"保存到: {output_path}")

        # 创建输出目录
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # 下载视频
        response = requests.get(video_url, stream=True, timeout=60)
        response.raise_for_status()

        # 获取文件大小用于进度条
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

        # 验证文件是否下载成功
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


def get_base_media_path():
    """根据操作系统返回适当的媒体路径前缀"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return "/Volumes/dhl"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl"


def get_input_directory():
    """获取输入目录路径"""
    base_path = get_base_media_path()
    return os.path.join(base_path, "audio", "scifi", "starting_mp4")


def get_output_directory():
    """获取输出目录路径"""
    base_path = get_base_media_path()
    return os.path.join(base_path, "audio", "scifi", "mp4_upscaled")


def get_input_videos(start_index: Optional[int] = None, end_index: Optional[int] = None) -> List[Tuple[str, int]]:
    """
    获取需要处理的输入视频文件列表
    
    Args:
        start_index: 开始索引（可选）
        end_index: 结束索引（可选）
    
    Returns:
        (文件路径, 故事索引) 的列表
    """
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        print(f"❌ 输入目录不存在: {input_dir}")
        return []
    
    # 获取所有MP4文件
    mp4_files = glob.glob(os.path.join(input_dir, "*.mp4"))
    
    # 过滤掉点开头的系统文件
    valid_files = []
    for mp4_file in mp4_files:
        basename = os.path.basename(mp4_file)
        
        # 跳过点开头的文件
        if basename.startswith('.'):
            continue
        
        # 提取故事索引
        match = re.match(r"(\d+)\.mp4", basename)
        if match:
            story_index = int(match.group(1))
            
            # 应用索引范围过滤
            if start_index is not None and story_index < start_index:
                continue
            if end_index is not None and story_index > end_index:
                continue
            
            valid_files.append((mp4_file, story_index))
    
    # 按索引排序
    valid_files.sort(key=lambda x: x[1])
    
    print(f"📁 在 {input_dir} 目录找到 {len(valid_files)} 个有效MP4文件")
    if valid_files:
        indices = [index for _, index in valid_files]
        print(f"📊 故事索引范围: {min(indices)} - {max(indices)}")
    
    return valid_files


def get_existing_upscaled_videos() -> set:
    """
    获取已存在的超分后视频文件索引集合
    
    Returns:
        已存在文件的故事索引集合
    """
    output_dir = get_output_directory()
    
    if not os.path.exists(output_dir):
        return set()
    
    # 获取所有输出MP4文件
    output_files = glob.glob(os.path.join(output_dir, "*.mp4"))
    existing_indices = set()
    
    for output_file in output_files:
        basename = os.path.basename(output_file)
        
        # 跳过点开头的文件
        if basename.startswith('.'):
            continue
        
        # 提取故事索引
        match = re.match(r"(\d+)\.mp4", basename)
        if match:
            story_index = int(match.group(1))
            existing_indices.add(story_index)
    
    return existing_indices


def generate_output_path(story_index: int) -> str:
    """
    生成输出文件路径
    
    Args:
        story_index: 故事索引
    
    Returns:
        输出文件的完整路径
    """
    output_dir = get_output_directory()
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, f"{story_index}.mp4")


def process_videos_batch(
    bit_rate: int = 5, 
    force: bool = False, 
    start_index: Optional[int] = None, 
    end_index: Optional[int] = None
) -> bool:
    """
    批量处理视频超分的主要函数
    
    Args:
        bit_rate: 视频比特率
        force: 是否强制重新处理
        start_index: 开始索引
        end_index: 结束索引
    
    Returns:
        处理成功返回True，失败返回False
    """
    
    # 获取需要处理的视频列表
    input_videos = get_input_videos(start_index, end_index)
    
    if not input_videos:
        print("❌ 未找到需要处理的视频文件")
        return False
    
    # 获取已存在的超分视频
    existing_videos = get_existing_upscaled_videos()
    
    # 过滤需要处理的视频
    videos_to_process = []
    for video_path, story_index in input_videos:
        if force or story_index not in existing_videos:
            videos_to_process.append((video_path, story_index))
        else:
            print(f"⏭️ 跳过已存在的故事 {story_index}")
    
    if not videos_to_process:
        print("✅ 所有视频都已完成超分处理")
        return True
    
    print(f"\n=== 📊 批量超分处理统计 ===")
    print(f"总视频数量: {len(input_videos)}")
    print(f"已处理数量: {len(existing_videos)}")
    print(f"需要处理: {len(videos_to_process)}")
    print(f"比特率: {bit_rate}")
    print(f"强制重新处理: {'是' if force else '否'}")
    
    if start_index is not None or end_index is not None:
        print(f"处理范围: {start_index or '开始'} - {end_index or '结束'}")
    
    indices = [index for _, index in videos_to_process]
    print(f"处理的故事索引: {sorted(indices)}")
    
    # 创建阿里云客户端
    client = create_client()
    print("✅ 阿里云视频增强客户端初始化成功")
    
    # 统计变量
    success_count = 0
    failure_count = 0
    
    # 批量处理视频
    with tqdm(total=len(videos_to_process), desc="批量超分进度") as pbar:
        for video_path, story_index in videos_to_process:
            print(f"\n=== 处理故事 {story_index} ===")
            print(f"输入文件: {video_path}")
            
            # 生成输出路径
            output_path = generate_output_path(story_index)
            print(f"输出文件: {output_path}")
            
            # 检查输入文件
            if not os.path.exists(video_path):
                print(f"❌ 输入视频文件不存在: {video_path}")
                failure_count += 1
                pbar.update(1)
                continue
            
            # 检查文件大小
            file_size = os.path.getsize(video_path)
            if file_size == 0:
                print(f"❌ 输入视频文件为空: {video_path}")
                failure_count += 1
                pbar.update(1)
                continue
            
            print(f"📹 视频文件大小: {file_size / (1024*1024):.2f} MB")
            
            # 进行视频超分处理
            result_url = upscale_video(client, video_path, bit_rate)
            
            if result_url:
                # 下载处理后的视频
                if download_video(result_url, output_path):
                    success_count += 1
                    print(f"✅ 故事 {story_index} 超分处理成功")
                else:
                    failure_count += 1
                    print(f"❌ 故事 {story_index} 视频下载失败")
            else:
                failure_count += 1
                print(f"❌ 故事 {story_index} 超分处理失败")
            
            pbar.update(1)
            
            # 在处理间隔添加短暂延迟，避免API调用过于频繁
            if success_count + failure_count < len(videos_to_process):
                time.sleep(2)
    
    # 输出最终统计
    print(f"\n=== 📈 批量超分完成统计 ===")
    print(f"✅ 成功处理: {success_count}/{len(videos_to_process)} 个视频")
    print(f"❌ 处理失败: {failure_count}/{len(videos_to_process)} 个视频")
    print(f"📊 成功率: {success_count/len(videos_to_process)*100:.1f}%")
    
    return success_count > 0


def main():
    """主函数"""
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="批量对视频进行超分辨率处理")

    # 添加命令行参数
    parser.add_argument(
        "--bitrate",
        type=int,
        default=5,
        help="视频比特率 (默认: 5)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新处理所有视频",
    )
    parser.add_argument(
        "--start",
        type=int,
        help="开始处理的视频索引",
    )
    parser.add_argument(
        "--end",
        type=int,
        help="结束处理的视频索引",
    )

    # 解析命令行参数
    args = parser.parse_args()
    
    # 验证参数
    if args.start is not None and args.end is not None:
        if args.start > args.end:
            print("❌ 错误：开始索引不能大于结束索引")
            return
        if args.start <= 0 or args.end <= 0:
            print("❌ 错误：索引必须大于 0")
            return

    print("🔍 批量视频超分辨率处理器")
    print("=" * 50)
    
    # 显示系统信息和路径
    system_name = platform.system()
    print(f"🖥️ 检测到操作系统: {system_name}")
    print(f"📂 输入目录: {get_input_directory()}")
    print(f"📁 输出目录: {get_output_directory()}")
    print()

    # 批量处理视频超分
    success = process_videos_batch(args.bitrate, args.force, args.start, args.end)

    if success:
        print("\n🎉 批量视频超分处理任务完成!")
        sys.exit(0)
    else:
        print("\n❌ 批量视频超分处理任务失败!")
        sys.exit(1)


if __name__ == "__main__":
    main()
