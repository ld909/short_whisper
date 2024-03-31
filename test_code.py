import json

# 字符串格式的列表
string_list = '["item1", "item2", "item3"]'

# 将字符串转换为 Python 列表
python_list = json.loads(string_list)
print(python_list)
