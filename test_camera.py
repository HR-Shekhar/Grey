import cv2
import os

# Locate cascade
cascade_path = '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml'
if not os.path.exists(cascade_path):
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'

face_cascade = cv2.CascadeClassifier(cascade_path)

# Scan video indices
for idx in range(5):
    cap = cv2.VideoCapture(idx)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"Device /dev/video{idx} is WORKING.")
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3)
            print(f"Faces detected on /dev/video{idx}: {len(faces)}")
        else:
            print(f"Device /dev/video{idx} opened but returned no frames.")
        cap.release()