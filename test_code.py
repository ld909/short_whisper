import os

# 指定目录路径
directory = "/Users/donghaoliu/doc/video_material/zh_tag/code/fireship"

# 遍历目录下的所有文件
for filename in os.listdir(directory):
    # 检查文件名是否包含 "_title"
    if "_title" in filename:
        # 构建新的文件名
        new_filename = filename.replace("_title", "")

        # 构建完整的文件路径
        old_path = os.path.join(directory, filename)
        new_path = os.path.join(directory, new_filename)

        # 重命名文件
        os.rename(old_path, new_path)

        print(f"Renamed: {filename} -> {new_filename}")

print("File renaming completed.")
