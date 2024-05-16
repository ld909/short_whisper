import json

# 创建嵌套的字典
data = {"code": {"fireship": "Add Toast Message Notifications to your Angular App"}}

# 将字典转换为JSON格式的字符串，并指定缩进
json_data = json.dumps(data, indent=4)

# 将JSON字符串写入文件
with open("./upload_log/bad.json", "w") as file:
    file.write(json_data)
