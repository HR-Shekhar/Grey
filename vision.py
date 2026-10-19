import os
import time
import threading
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

        model_path = os.path.join(os.path.dirname(__file__), "face_detection_yunet.onnx")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}. Please download face_detection_yunet.onnx.")

        # Initialize OpenCV DNN YuNet detector
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

        print("[Grey Vision] OpenCV YuNet Neural Face Tracker active on /dev/video0.")
        last_state = False

        while self.running:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.02)
                continue

            # Ensure input size matches frame dimensions
            h, w, _ = frame.shape
            self.detector.setInputSize((w, h))

            # Run inference
            _, faces = self.detector.detect(frame)

            if faces is not None and len(faces) > 0:
                # Find the single LARGEST face by area (bbox: [x, y, w, h])
                biggest_face = None
                max_area = 0.0

                for face in faces:
                    fx, fy, fw, fh = face[0:4]
                    area = fw * fh
                    if area > max_area:
                        max_area = area
                        biggest_face = (fx, fy, fw, fh)

                if biggest_face:
                    fx, fy, fw, fh = biggest_face
                    cx = (fx + fw / 2.0) / w
                    cy = (fy + fh / 2.0) / h

                    # Invert X for natural mirror tracking
                    norm_x = -(cx - 0.5) * 2.0
                    norm_y = (cy - 0.5) * 2.0

                    self.target_x = max(-1.0, min(1.0, norm_x))
                    self.target_y = max(-1.0, min(1.0, norm_y))
                    self.face_detected = True

                    if not last_state:
                        print("[Grey] Locked onto closest face.")
                        last_state = True
            else:
                self.face_detected = False
                if last_state:
                    print("[Grey] Lost target. Idling.")
                    last_state = False

            time.sleep(0.02)

        cap.release()

    def stop(self):
        self.running = False