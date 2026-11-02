import os
import time
import threading
import math
import cv2
from config import CAM_WIDTH, CAM_HEIGHT

os.environ["OPENCV_LOG_LEVEL"] = "ERROR"

class GreyVision(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.target_x = 0.0
        self.target_y = 0.0
        self.face_detected = False
        self.running = True

        # Behavioral metrics
        self.face_area = 0.0
        self.area_delta = 0.0
        self.speed = 0.0
        self.head_tilt = 0.0      # In degrees
        self.sweep_count = 0      # Horizontal side-to-side rapid sweeps
        
        self.last_x = 0.0
        self.last_y = 0.0
        self.last_area = 0.0
        self.last_dir_x = 0
        self.sweep_timer = time.time()

        model_path = os.path.join(os.path.dirname(__file__), "face_detection_yunet.onnx")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}.")

        self.detector = cv2.FaceDetectorYN.create(
            model=model_path,
            config="",
            input_size=(CAM_WIDTH, CAM_HEIGHT),
            score_threshold=0.6,
            nms_threshold=0.3,
            top_k=5000
        )

    def run(self):
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

        if not cap.isOpened():
            print("[Grey Vision] ERROR: Failed to open /dev/video0")
            return

        print("[Grey Vision] Behavioral Neural Vision active.")

        while self.running:
            try:
                ret, frame = cap.read()
                if not ret or frame is None or frame.size == 0:
                    time.sleep(0.01)
                    continue

                h, w, _ = frame.shape
                self.detector.setInputSize((w, h))
                _, faces = self.detector.detect(frame)

                now = time.time()

                if faces is not None and len(faces) > 0:
                    biggest_face = max(faces, key=lambda f: f[2] * f[3])
                    fx, fy, fw, fh = biggest_face[0:4]
                    area = (fw * fh) / float(w * h)

                    cx = (fx + fw / 2.0) / float(w)
                    cy = (fy + fh / 2.0) / float(h)
                    norm_x = -(cx - 0.5) * 2.0
                    norm_y = (cy - 0.5) * 2.0

                    # Area surge
                    if self.last_area > 0.0:
                        self.area_delta = area - self.last_area
                    self.last_area = area
                    self.face_area = area

                    # Speed
                    dx = norm_x - self.last_x
                    dy = norm_y - self.last_y
                    self.speed = math.hypot(dx, dy)

                    # Sweep count
                    current_dir = 1 if dx > 0.07 else (-1 if dx < -0.07 else 0)
                    if current_dir != 0 and current_dir != self.last_dir_x:
                        self.sweep_count += 1
                        self.last_dir_x = current_dir

                    if now - self.sweep_timer > 3.0:
                        self.sweep_count = 0
                        self.sweep_timer = now

                    # Safe landmarks retrieval
                    if len(biggest_face) >= 8:
                        r_eye_x, r_eye_y = biggest_face[4], biggest_face[5]
                        l_eye_x, l_eye_y = biggest_face[6], biggest_face[7]
                        eye_dx = l_eye_x - r_eye_x
                        eye_dy = l_eye_y - r_eye_y
                        self.head_tilt = abs(math.degrees(math.atan2(eye_dy, eye_dx)))
                    else:
                        self.head_tilt = 0.0

                    self.last_x = norm_x
                    self.last_y = norm_y

                    self.target_x = max(-1.0, min(1.0, norm_x))
                    self.target_y = max(-1.0, min(1.0, norm_y))
                    self.face_detected = True
                else:
                    self.face_detected = False
                    self.speed = 0.0
                    self.area_delta = 0.0
                    self.head_tilt = 0.0
                    self.sweep_count = 0
                    self.last_area = 0.0

            except Exception as e:
                # Catch internal C++ thread faults cleanly
                pass

            time.sleep(0.015)

        cap.release()

    def stop(self):
        self.running = False