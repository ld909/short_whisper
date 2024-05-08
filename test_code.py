import os

absolute_path = "/path/to/directory/filename.txt"
file_name = os.path.basename(absolute_path)

print(file_name)  # 输出: filename.txt
