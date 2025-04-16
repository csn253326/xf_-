# \project_frontend\gradio_app\main.py
import gradio as gr
import cv2
import numpy as np
from websockets.sync.client import connect
from utils.config import AppConfig
from datetime import datetime, timedelta, timezone
import jwt, sys
import json
import base64
import threading
import queue
import time

theme = gr.themes.Default(
    primary_hue="violet",
    secondary_hue="emerald"
).set(
    button_large_padding="20px"
)

frame_queue = queue.Queue(maxsize=20)
processing_active = threading.Event()

# ====================== 新增修改点 1：线程安全类 ======================
class ThreadSafeFrame:
    def __init__(self):
        self._frame = None
        self._lock = threading.Lock()

    def set(self, frame):
        with self._lock:
            self._frame = frame
            print("ThreadSafeFrame Set Successfully", file=sys.stderr)  # 验证设置成功

    def get(self):
        with self._lock:
            return self._frame

safe_frame = ThreadSafeFrame()

def generate_ws_token():
    payload = {
        "client_id": AppConfig.CLIENT_ID,
        "scopes": ["video_stream"],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=AppConfig.JWT_EXPIRE_MINUTES),
        "iss": AppConfig.JWT_ISSUER,
        "aud": AppConfig.JWT_AUDIENCE,
        "iat": datetime.now(timezone.utc)
    }
    token = jwt.encode(
        payload,
        AppConfig.JWT_SECRET_KEY,
        algorithm=AppConfig.JWT_ALGORITHM,
        headers = {
            "typ": "JWT",
            "alg": AppConfig.JWT_ALGORITHM
        }
    )
    print(f"Generated JWT:{token}")
    return token

def draw_results(frame_bytes: bytes, json_result: str) -> np.ndarray:
    """返回RGB格式的numpy数组"""
    try:
        frame = cv2.imdecode(np.frombuffer(frame_bytes, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)

        height, width = frame.shape[:2]
        predictions = json.loads(json_result).get("predictions", [])

        for pred in predictions:
            x1 = int(pred["bbox"][0] * width)
            y1 = int(pred["bbox"][1] * height)
            x2 = int(pred["bbox"][2] * width)
            y2 = int(pred["bbox"][3] * height)

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{pred['label']} {pred['confidence']:.2f}"
            (text_width, text_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - text_height - 10), (x1 + text_width + 5, y1 - 5), (0, 255, 0), -1)
            cv2.putText(frame, label, (x1 + 2, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # 转换为RGB格式
    except Exception as e:
        print(f"绘图错误: {str(e)}")
        return np.zeros((480, 640, 3), dtype=np.uint8)

# ====================== 新增修改点 2：优化VideoProcessor ======================
class VideoProcessor:
    def __init__(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._init_check()
        self.is_running = True
        self.frame_lock = threading.Lock()

    def _init_check(self):
        if not self.cap.isOpened():
            raise ConnectionError("摄像头初始化失败")

    def gen_frames(self):
        print("摄像头线程启动|线程ID:",threading.get_ident())#摄像头调试
        while self.is_running:
            with self.frame_lock:
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.1)
                    continue
            print(f"捕获帧|队列大小：{frame_queue.qsize()}")#调试4
            time.sleep(1/30)
            _, jpeg = cv2.imencode('.jpg', frame)
            yield jpeg.tobytes()

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()

# ====================== 新增修改点 3：重构WebSocketClient ======================
class WebSocketClient(threading.Thread):
    def __init__(self, ws_url):
        super().__init__()
        self.ws_url = ws_url
        self.websocket = None
        self.running = True
        self.last_ping = time.time()

    def run(self):
        try:
            with connect(self.ws_url) as websocket:
                self.websocket = websocket
                self._authenticate(websocket)
                self._process_stream()
        except Exception as e:
            print(f"WebSocket错误: {str(e)}")
        finally:
            self.running = False

    def _authenticate(self, websocket):
        auth_msg = json.dumps({
            "type": "auth",
            "token": generate_ws_token()
        })
        websocket.send(auth_msg)
        response = json.loads(websocket.recv())
        if response.get("status") != "success":
            raise ConnectionError("认证失败")

    def _process_stream(self):
        print("WebSocket连接成功|URL:", self.ws_url)#调试5
        while self.running:
            try:
                if time.time() - self.last_ping > 30:
                    self.websocket.ping()
                    self.last_ping = time.time()

                if not frame_queue.empty():
                    frame_data = frame_queue.get_nowait()
                    print("Frame Data Retrieved:",len(frame_data),file=sys.stderr)
                    self.websocket.send(json.dumps({
                        "type": "frame",
                        "data": base64.b64encode(frame_data).decode('utf-8')
                    }))
                    print("Frame Sent Sent Successfully", file=sys.stderr)
                    result = self.websocket.recv(timeout=5)
                    print("Frame Result Received Successfully", file=sys.stderr)  # 验证接收成功
                    safe_frame.set((
                        frame_data,
                        json.loads(result).get("predictions", [])
                    ))
                    print("Safe Frame Set:", len(frame_data), file=sys.stderr)  # 验证数据写入
                    print(f"发送帧数据|大小：{len(frame_data)}bytes")
            except Exception as e:
                print(f"流处理错误: {str(e)}")
                break

# ====================== 新增修改点 4：重构生成器函数 ======================
def result_generator():
    print("生成器启动|当前线程：",threading.current_thread().name)#调试1
    client = WebSocketClient(
        f"ws://{AppConfig.BACKEND_HOST}:{AppConfig.BACKEND_PORT}"
        f"{AppConfig.API_ENDPOINTS['gender_detection']}"
    )
    client.start()

    # 预定义标准尺寸的空白帧（RGB格式）
    default_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    last_valid_frame = default_frame.copy()

    while processing_active.is_set():
        try:
            # 获取最新帧数据（带线程锁）
            frame_data, result = safe_frame.get() or (None, None)
            if frame_data and result:
                # 关键修改点1：确保图像处理返回RGB格式
                processed = draw_results(frame_data, json.dumps(result))
                # 强制转换为uint8类型并验证形状
                processed = processed.astype(np.uint8)
                assert processed.shape == (480, 640, 3), "Invalid frame shape"
                print(f"🖼️ 处理后帧信息 | shape: {processed.shape} | dtype: {processed.dtype}",file=sys.stderr)#调试3
                last_valid_frame = processed.copy()
                yield processed
            else:
                # 关键修改点2：保留最后一帧并添加提示
                temp_frame = last_valid_frame.copy()
                cv2.putText(temp_frame, "等待数据...", (50, 240),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                yield temp_frame.astype(np.uint8)
        except Exception as e:
            print(f"生成器错误: {str(e)}")
            # 返回标准化错误帧
            error_frame = default_frame.copy()
            cv2.putText(error_frame, "视频流异常", (50, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            yield error_frame
        # 关键修改点3：精确控制帧率（30FPS）
        time.sleep(1 / 30)

def create_demo():
    with gr.Blocks(theme=theme, title="实时人脸分析系统") as demo:
        error_box = gr.Textbox(visible=False, label="错误详情")
        gr.Markdown("##  实时人脸特征分析系统")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 控制面板")
                start_btn = gr.Button("启动实时分析", variant="primary")
                stop_btn = gr.Button("停止分析", variant="stop")

            with gr.Column(scale=2):
                output_image = gr.Image(
                    type="numpy",
                    label="实时画面",
                    format="webp",
                    streaming=True,
                    height=480,
                    width=640,
                    elem_id="live_feed",
                )

        @start_btn.click(inputs=None,
    outputs=output_image,  # 明确绑定到输出组件
    concurrency_limit=1)
        def start_processing():
            processing_active.set()
            threading.Thread(target=video_capture, daemon=True).start()
            for frame in result_generator():
                yield frame

        def video_capture():
            try:
                processor = VideoProcessor()
                for frame in processor.gen_frames():
                    if not processing_active.is_set():
                        break
                    try:
                        if frame_queue.full():
                            frame_queue.get_nowait()
                        frame_queue.put_nowait(frame)
                        print(f"Frame Queue Size After Put:{frame_queue.qsize()}",file=sys.stderr)
                    except queue.Empty:
                        pass
            except Exception as e:
                error_box.value = f"摄像头错误: {str(e)}"
                error_box.visible = True

        @stop_btn.click()
        def stop_processing():
            processing_active.clear()
            frame_queue.queue.clear()
            # 新增资源释放逻辑
            if hasattr(demo, 'ws_client') and demo.ws_client.is_alive():
                demo.ws_client.running = False
                demo.ws_client.join()
            return None

    return demo

if __name__ == "__main__":
    demo = create_demo()
    demo.queue().launch(
        max_threads=2,
        server_port=7860,
        show_error=True,
        share=False
    )