import os

os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"

FPS = 60
DEFAULT_WIDTH = 480
DEFAULT_HEIGHT = 320

BG_COLOR = (12, 15, 22)
HIGHLIGHT_COLOR = (255, 255, 255)

# Emotion Palettes: (Sclera Color, Pupil Color)
EMOTION_COLORS = {
    "NEUTRAL":   ((0, 240, 255),   (6, 32, 44)),     # Cyber Cyan
    "HAPPY":     ((46, 230, 166),  (5, 42, 30)),     # Emerald Green
    "CURIOUS":   ((255, 195, 0),   (48, 36, 0)),     # Amber Yellow
    "SURPRISED": ((255, 255, 255), (20, 25, 35)),   # Bright White
    "SLEEPY":    ((120, 110, 230), (22, 18, 48)),   # Dim Lavender
    "ANNOYED":   ((255, 75, 75),   (50, 10, 15)),    # Crimson Coral
    "SAD":       ((70, 130, 220),  (10, 25, 50)),    # Melancholy Blue
    "DIZZY":     ((180, 255, 60),  (35, 55, 10)),    # Neon Lime Green
}

CAM_WIDTH = 320
CAM_HEIGHT = 240