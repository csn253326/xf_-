# \app\utils\image_utils.py
import cv2
import tempfile
import os
from pathlib import Path
import logging

def process_image(input_path: str) -> str:
    """处理图像并返回输出文件路径"""
    output_path = None
    try:
        # 验证输入文件
        input_path_obj = Path(input_path)
        if not input_path_obj.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        if input_path_obj.stat().st_size == 0:
            raise ValueError("输入文件为空")

        # 读取图像
        image = cv2.imread(str(input_path))
        if image is None:
            raise ValueError(f"无法解码图像文件: {input_path}")

        # 图像处理
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)

        # 创建临时文件
        fd, output_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)  # 立即关闭描述符

        # 保存结果并验证
        success = cv2.imwrite(
            output_path,
            edges,
            [int(cv2.IMWRITE_JPEG_QUALITY), 95]
        )
        if not success or not Path(output_path).exists():
            raise RuntimeError("图像保存失败")

        return output_path

    except Exception as e:
        # 清理临时文件
        if output_path and Path(output_path).exists():
            try:
                Path(output_path).unlink()
            except Exception as cleanup_error:
                logging.warning(f"清理临时文件失败: {cleanup_error}")
        # 记录日志后重新抛出异常
        logging.error(f"图像处理失败: {str(e)}", exc_info=True)
        raise