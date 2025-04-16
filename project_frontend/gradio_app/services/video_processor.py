import cv2

def draw_detections(frame, results, model_type):
    h, w = frame.shape[:2]
    for det in results:
        x1, y1, x2, y2 = det["bbox"]
        label = f"{det['label']} {det['confidence']:.2f}"

        # 转换为整数坐标
        x1 = int(x1 * w)
        y1 = int(y1 * h)
        x2 = int(x2 * w)
        y2 = int(y2 * h)

        # 绘制方框
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # 根据模型类型调整标签颜色
        text_color = (255, 0, 0) if model_type == "gender" else (0, 0, 255)
        cv2.putText(frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
    return frame

