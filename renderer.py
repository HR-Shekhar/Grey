import pygame
import random
import time
import math
from config import BG_COLOR, HIGHLIGHT_COLOR, EMOTION_COLORS

class EyeRenderer:
    def __init__(self, surface, width, height):
        self.surface = surface
        self.width = width
        self.height = height

        # Font setup for sleeping Zzz animation
        pygame.font.init()
        self.zzz_font = pygame.font.SysFont("dejavusans", 22, bold=True)
        self.zzz_particles = []  # List of active particles: dict(x, y, alpha, size, seed)
        self.last_zzz_spawn = time.time()

        # Eye Geometry
        self.base_eye_w = int(width * 0.22)
        self.base_eye_h = int(self.base_eye_w * 1.25)
        self.eye_radius = int(self.base_eye_w * 0.32)

        self.center_x = width // 2
        self.center_y = height // 2
        self.spacing = int(width * 0.20)

        self.left_x = self.center_x - self.spacing
        self.right_x = self.center_x + self.spacing
        self.rest_y = self.center_y - int(height * 0.05)

        self.max_offset_x = width * 0.07
        self.max_offset_y = height * 0.08

        # Mouth Geometry (Shifted downwards)
        self.mouth_center_x = self.center_x
        self.mouth_center_y = self.center_y + int(height * 0.25)
        self.base_mouth_w = int(width * 0.08)
        self.base_mouth_h = int(height * 0.04)

        # Motion & Easing
        self.curr_x, self.curr_y = 0.0, 0.0
        self.target_x, self.target_y = 0.0, 0.0
        self.pupil_scale = 1.0

        # Current Emotion
        self.emotion = "NEUTRAL"
        self.target_color = EMOTION_COLORS["NEUTRAL"][0]
        self.curr_color = list(self.target_color)
        self.target_pupil_color = EMOTION_COLORS["NEUTRAL"][1]
        self.curr_pupil_color = list(self.target_pupil_color)

        # Morph Weights (0.0 to 1.0)
        self.happy_squint = 0.0
        self.annoyed_slant = 0.0
        self.sad_slant = 0.0
        self.sleep_transition = 0.0
        self.eye_scale_x = 1.0
        self.eye_scale_y = 1.0

        # Dizzy State
        self.dizzy_angle = 0.0

        # Blinking
        self.is_blinking = False
        self.blink_progress = 0.0
        self.blink_speed = 0.16
        self.blink_dir = 1
        self.last_blink = time.time()
        self.blink_interval = random.uniform(2.5, 5.0)

        # Idle Glances
        self.last_glance = time.time()
        self.glance_interval = random.uniform(1.5, 3.5)

    def set_emotion(self, emotion_name):
        if emotion_name in EMOTION_COLORS and self.emotion != emotion_name:
            self.emotion = emotion_name
            self.target_color = EMOTION_COLORS[emotion_name][0]
            self.target_pupil_color = EMOTION_COLORS[emotion_name][1]

    def draw_w_mouth(self, color, x, y, size, thickness=8):
        """Draws a bold, smooth 'w' cat-smile shape without pygame.draw.arc clipping."""
        r = size // 2
        steps = 14

        for offset in [-r, r]:
            cx = x + offset
            pts = []
            for step in range(steps + 1):
                theta = math.pi + (math.pi * step / steps)
                px = int(cx + r * math.cos(theta))
                py = int(y + r * math.sin(theta))
                pts.append((px, py))

            pygame.draw.lines(self.surface, color, False, pts, thickness)
            for px, py in [pts[0], pts[-1]]:
                pygame.draw.circle(self.surface, color, (px, py), thickness // 2)

    def update(self, face_detected, target_x_norm, target_y_norm):
        now = time.time()

        # 1. Color Interpolation
        for i in range(3):
            self.curr_color[i] += (self.target_color[i] - self.curr_color[i]) * 0.08
            self.curr_pupil_color[i] += (self.target_pupil_color[i] - self.curr_pupil_color[i]) * 0.08

        # 2. Target Morph Values
        target_happy = 1.0 if self.emotion == "HAPPY" else 0.0
        target_annoyed = 1.0 if self.emotion == "ANNOYED" else 0.0
        target_sad = 1.0 if self.emotion == "SAD" else 0.0
        target_sleep = 1.0 if self.emotion == "SLEEPY" else 0.0

        target_scale_x = 1.15 if self.emotion == "SURPRISED" else (0.92 if self.emotion in ["CURIOUS", "ANNOYED"] else 1.0)
        target_scale_y = 1.25 if self.emotion == "SURPRISED" else (0.85 if self.emotion == "SAD" else 1.0)

        self.happy_squint += (target_happy - self.happy_squint) * 0.15
        self.annoyed_slant += (target_annoyed - self.annoyed_slant) * 0.15
        self.sad_slant += (target_sad - self.sad_slant) * 0.15
        self.sleep_transition += (target_sleep - self.sleep_transition) * 0.10
        self.eye_scale_x += (target_scale_x - self.eye_scale_x) * 0.15
        self.eye_scale_y += (target_scale_y - self.eye_scale_y) * 0.15

        # 3. Gaze & Focus Physics
        if self.emotion == "DIZZY":
            self.dizzy_angle += 0.22
            self.pupil_scale += (0.8 - self.pupil_scale) * 0.1
        elif self.emotion == "SAD":
            # Sad glances search lower ground
            if now - self.last_glance > 1.2:
                self.target_x = random.uniform(-self.max_offset_x * 0.6, self.max_offset_x * 0.6)
                self.target_y = self.max_offset_y * random.uniform(0.4, 0.75)
                self.last_glance = now
            self.pupil_scale += (0.85 - self.pupil_scale) * 0.08
        elif self.emotion == "SLEEPY":
            self.target_x = 0.0
            self.target_y = self.max_offset_y * 0.3
        elif face_detected:
            self.target_x = target_x_norm * self.max_offset_x
            self.target_y = target_y_norm * self.max_offset_y
            self.pupil_scale += (1.2 - self.pupil_scale) * 0.1
        else:
            self.pupil_scale += (0.95 - self.pupil_scale) * 0.05
            if now - self.last_glance > self.glance_interval:
                self.target_x = random.uniform(-self.max_offset_x * 0.7, self.max_offset_x * 0.7)
                self.target_y = random.uniform(-self.max_offset_y * 0.7, self.max_offset_y * 0.7)
                self.last_glance = now
                self.glance_interval = random.uniform(1.5, 4.0)

        ease = 0.08 if self.emotion == "SAD" else 0.18
        self.curr_x += (self.target_x - self.curr_x) * ease
        self.curr_y += (self.target_y - self.curr_y) * ease

        # 4. Blink Logic (Suppressed during deep sleep)
        if self.sleep_transition < 0.5:
            if not self.is_blinking and (now - self.last_blink > self.blink_interval):
                self.is_blinking = True
                self.blink_progress = 0.0
                self.blink_dir = 1

            if self.is_blinking:
                self.blink_progress += self.blink_speed * self.blink_dir
                if self.blink_progress >= 1.0:
                    self.blink_progress = 1.0
                    self.blink_dir = -1
                elif self.blink_progress <= 0.0:
                    self.blink_progress = 0.0
                    self.is_blinking = False
                    self.last_blink = now
                    self.blink_interval = 0.18 if (random.random() < 0.25 and self.emotion not in ["SLEEPY", "DIZZY"]) else random.uniform(2.5, 6.0)

        # 5. Corner Zzz Particles
        if self.emotion == "SLEEPY" and self.sleep_transition > 0.7:
            if now - self.last_zzz_spawn > 0.9:
                # Spawn in top-right corner
                self.zzz_particles.append({
                    "x": int(self.width * 0.82) + random.randint(-10, 15),
                    "y": int(self.height * 0.28),
                    "alpha": 255,
                    "size": random.randint(28, 42),
                    "seed": random.uniform(0, 100)
                })
                self.last_zzz_spawn = now

        for p in self.zzz_particles[:]:
            p["y"] -= 0.8
            p["x"] += math.sin(now * 1.8 + p["seed"]) * 0.5
            p["alpha"] -= 2.2
            if p["alpha"] <= 0:
                self.zzz_particles.remove(p)

    def draw(self):
        self.surface.fill(BG_COLOR)

        active_eye_w = int(self.base_eye_w * self.eye_scale_x)
        active_eye_h = int(self.base_eye_h * self.eye_scale_y)

        blink_factor = (1.0 - (self.blink_progress * 0.95)) * (1.0 - self.sleep_transition)
        current_h = max(4, int(active_eye_h * blink_factor))
        current_w = int(active_eye_w * (1.0 + (self.blink_progress * 0.08)))
        current_radius = min(self.eye_radius, current_h // 2)

        left_box = pygame.Rect(
            int(self.left_x + self.curr_x - current_w // 2),
            int(self.rest_y + self.curr_y - current_h // 2),
            current_w, current_h
        )
        right_box = pygame.Rect(
            int(self.right_x + self.curr_x - current_w // 2),
            int(self.rest_y + self.curr_y - current_h // 2),
            current_w, current_h
        )

        eye_color = tuple(int(c) for c in self.curr_color)
        pupil_color = tuple(int(c) for c in self.curr_pupil_color)

        # --- 1. EYES RENDERING ---
        if self.sleep_transition > 0.85:
            # Cute upward sleeping crescents (peaceful, happy sleep: ∪ shape)
            arc_w = int(self.base_eye_w * 0.82)
            arc_h = int(self.base_eye_h * 0.42)
            steps = 16

            for center_pos_x in [self.left_x, self.right_x]:
                pts = []
                for s in range(steps + 1):
                    # Upward smile arc (angle from 0 to pi curving underneath)
                    theta = (math.pi * s) / steps
                    px = int(center_pos_x - (arc_w // 2) * math.cos(theta))
                    py = int(self.rest_y - 2 + (arc_h // 2) * math.sin(theta))
                    pts.append((px, py))

                pygame.draw.lines(self.surface, eye_color, False, pts, 7)
                pygame.draw.circle(self.surface, eye_color, pts[0], 3)
                pygame.draw.circle(self.surface, eye_color, pts[-1], 3)
        else:
            # Active open eyes
            for i, box in enumerate([left_box, right_box]):
                is_left_eye = (i == 0)

                pygame.draw.rect(self.surface, eye_color, box, border_radius=current_radius)

                # Pupils & Parallax Catchlights
                if current_h > 24:
                    pw = int(active_eye_w * 0.38 * self.pupil_scale)
                    ph = int(active_eye_h * 0.42 * self.pupil_scale * blink_factor)

                    if self.emotion == "DIZZY":
                        orbit_r = self.base_eye_w * 0.20
                        direction = 1 if is_left_eye else -1
                        p_offset_x = math.cos(self.dizzy_angle * direction) * orbit_r
                        p_offset_y = math.sin(self.dizzy_angle) * orbit_r
                    else:
                        p_offset_x = self.curr_x * 0.45
                        p_offset_y = self.curr_y * 0.45

                    pupil_rect = pygame.Rect(
                        int(box.centerx + p_offset_x - pw // 2),
                        int(box.centery + p_offset_y - ph // 2),
                        pw, ph
                    )
                    pygame.draw.rect(self.surface, pupil_color, pupil_rect, border_radius=int(pw // 2))

                    # Catchlight parallax calculations
                    base_hl_x = pupil_rect.centerx - int(pw * 0.22)
                    base_hl_y = pupil_rect.centery - int(ph * 0.22)

                    hl_shift_x = int(p_offset_x * 0.25)
                    hl_shift_y = int(p_offset_y * 0.25)

                    hl_x = base_hl_x + hl_shift_x
                    hl_y = base_hl_y + hl_shift_y
                    hl_size = max(2, int(pw * 0.22))

                    pygame.draw.circle(self.surface, HIGHLIGHT_COLOR, (hl_x, hl_y), hl_size)
                    sec_x = hl_x + int(hl_size * 1.3)
                    sec_y = hl_y + int(hl_size * 1.3)
                    pygame.draw.circle(self.surface, HIGHLIGHT_COLOR, (sec_x, sec_y), max(1, hl_size // 2))

                # Eyelid Clipping Masks
                if self.happy_squint > 0.01:
                    cut_h = int(box.height * 0.22 * self.happy_squint)
                    cut_rect = pygame.Rect(
                        box.left - int(box.width * 0.1),
                        box.bottom - cut_h,
                        int(box.width * 1.2),
                        cut_h * 2
                    )
                    pygame.draw.ellipse(self.surface, BG_COLOR, cut_rect)

                if self.annoyed_slant > 0.01:
                    slant_drop = int(box.height * 0.45 * self.annoyed_slant)
                    if is_left_eye:
                        pts = [
                            (box.left - 5, box.top - 5),
                            (box.right + 5, box.top - 5),
                            (box.right + 5, box.top + slant_drop),
                        ]
                    else:
                        pts = [
                            (box.left - 5, box.top - 5),
                            (box.right + 5, box.top - 5),
                            (box.left - 5, box.top + slant_drop),
                        ]
                    pygame.draw.polygon(self.surface, BG_COLOR, pts)

                if self.sad_slant > 0.01:
                    slant_drop = int(box.height * 0.40 * self.sad_slant)
                    if is_left_eye:
                        pts = [
                            (box.left - 5, box.top - 5),
                            (box.right + 5, box.top - 5),
                            (box.left - 5, box.top + slant_drop),
                        ]
                    else:
                        pts = [
                            (box.left - 5, box.top - 5),
                            (box.right + 5, box.top - 5),
                            (box.right + 5, box.top + slant_drop),
                        ]
                    pygame.draw.polygon(self.surface, BG_COLOR, pts)

        # 2. Floating Zzz Rendering
        for p in self.zzz_particles:
            surf = pygame.font.SysFont("dejavusans", p["size"], bold=True).render("Z", True, eye_color)
            surf.set_alpha(int(p["alpha"]))
            self.surface.blit(surf, (int(p["x"]), int(p["y"])))

        # 3. Animated Mouth Rendering
        mx = self.mouth_center_x + int(self.curr_x * 0.45)
        my = self.mouth_center_y + int(self.curr_y * 0.45)

        breath = math.sin(time.time() * 3.5) * 1.2
        my += int(breath)

        mouth_thick = 8

        if self.emotion in ["SURPRISED", "DIZZY"]:
            # Solid standing vertical oval
            oval_w = int(self.base_mouth_w * 0.38)
            oval_h = int(self.base_mouth_h * 1.70)
            solid_oval = pygame.Rect(mx - oval_w // 2, my - oval_h // 2, oval_w, oval_h)
            pygame.draw.ellipse(self.surface, eye_color, solid_oval)

        elif self.emotion == "HAPPY":
            r_box = pygame.Rect(
                mx - int(self.base_mouth_w * 0.65), 
                my - int(self.base_mouth_h * 0.4), 
                int(self.base_mouth_w * 1.3), 
                self.base_mouth_h * 2
            )
            pygame.draw.arc(self.surface, eye_color, r_box, math.pi, 2 * math.pi, mouth_thick)

        elif self.emotion in ["NEUTRAL", "CURIOUS"]:
            self.draw_w_mouth(eye_color, mx, my - 6, int(self.base_mouth_w * 0.5), thickness=mouth_thick)

        elif self.emotion in ["ANNOYED", "SAD"]:
            r_box = pygame.Rect(
                mx - int(self.base_mouth_w * 0.55), 
                my + 2, 
                int(self.base_mouth_w * 1.1), 
                self.base_mouth_h * 2
            )
            pygame.draw.arc(self.surface, eye_color, r_box, 0, math.pi, mouth_thick)

        elif self.emotion == "SLEEPY":
            flat_w = int(self.base_mouth_w * 0.4)
            pygame.draw.line(self.surface, eye_color, (mx - flat_w, my), (mx + flat_w, my), mouth_thick)