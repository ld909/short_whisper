#!/bin/bash

# YouTube API 认证环境变量示例
# 请将此文件复制为 youtube_credentials.sh 并填入实际的值
# 然后运行 source youtube_credentials.sh 来设置环境变量

# English 频道的认证信息
export YOUTUBE_CLIENT_ID_EN='YOUR_EN_CLIENT_ID_HERE'
export YOUTUBE_CLIENT_SECRET_EN='YOUR_EN_CLIENT_SECRET_HERE'

# Japanese 频道的认证信息
export YOUTUBE_CLIENT_ID_JA='YOUR_JA_CLIENT_ID_HERE'
export YOUTUBE_CLIENT_SECRET_JA='YOUR_JA_CLIENT_SECRET_HERE'

# Korean 频道的认证信息
export YOUTUBE_CLIENT_ID_KO='YOUR_KO_CLIENT_ID_HERE'
export YOUTUBE_CLIENT_SECRET_KO='YOUR_KO_CLIENT_SECRET_HERE'

# Vietnamese 频道的认证信息
export YOUTUBE_CLIENT_ID_VI='YOUR_VI_CLIENT_ID_HERE'
export YOUTUBE_CLIENT_SECRET_VI='YOUR_VI_CLIENT_SECRET_HERE'

# 重定向URI（通常无需修改）
export YOUTUBE_REDIRECT_URI='urn:ietf:wg:oauth:2.0:oob'
