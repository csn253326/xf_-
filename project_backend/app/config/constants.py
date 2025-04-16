# \app\constants.py
# 文件类型白名单
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png"]
ALLOWED_VIDEO_TYPES = ["video/mp4", "video/quicktime"]


# API响应消息
ERROR_MESSAGES = {
    "invalid_file_type": "Unsupported file type",
    "file_size_exceeded": "File size exceeds 5MB limit"
}