# -*- coding: utf-8 -*-
"""
简单的封面图片OSS上传工具
"""

import os
import sys
import glob
import re
import oss2
from oss2.credentials import EnvironmentVariableCredentialsProvider


def create_oss_bucket(bucket_name: str) -> oss2.Bucket:
    """创建阿里云OSS Bucket对象"""
    access_key_id = os.environ.get("OSS_ACCESS_KEY_ID")
    access_key_secret = os.environ.get("OSS_ACCESS_KEY_SECRET")

    if not access_key_id or not access_key_secret:
        print("错误: 请设置环境变量 OSS_ACCESS_KEY_ID 和 OSS_ACCESS_KEY_SECRET")
        sys.exit(1)

    auth = oss2.ProviderAuthV4(EnvironmentVariableCredentialsProvider())
    endpoint = "https://oss-cn-shanghai.aliyuncs.com"
    region = "cn-shanghai"
    bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)
    return bucket


def upload_images():
    """上传图片到OSS"""
    bucket_name = "audiocover"
    bucket = create_oss_bucket(bucket_name)

    # 图片目录
    image_dir = "/Volumes/dhl/audio/scifi/cover_img_small"

    # 获取所有png文件
    png_files = glob.glob(os.path.join(image_dir, "*.png"))

    for file_path in png_files:
        filename = os.path.basename(file_path)
        match = re.match(r"(\d+)\.png", filename)

        if not match:
            continue

        story_index = match.group(1)
        object_key = f"cover_images/{story_index}.png"

        try:
            with open(file_path, "rb") as f:
                result = bucket.put_object(object_key, f)

            if result.status == 200:
                print(f"✅ 上传成功: {filename}")
            else:
                print(f"❌ 上传失败: {filename}")

        except Exception as e:
            print(f"❌ 上传出错: {filename} - {e}")


if __name__ == "__main__":
    upload_images()
