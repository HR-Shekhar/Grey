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
        self.zzz_particles = []
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

        # --- Dynamic Smooth Mouth Engine ---
        self.mouth_center_x = self.center_x
        self.mouth_center_y = self.center_y + int(height * 0.25)
        self.base_mouth_w = int(width * 0.10)
        self.base_mouth_h = int(height * 0.05)

        # Mouth morph dimensions
        self.cur_m_w = float(self.base_mouth_w)
        self.cur_m_h = float(self.base_mouth_h)
        self.cur_oval_weight = 0.0      # 0.0 = Curves/Lines, 1.0 = Solid Vertical Oval
        self.cur_smile_curve = 0.0      # +1.0 = Happy smile, 0.0 = Cat/Neutral, -1.0 = Frown
        self.cur_speech_open = 0.0      # Jaw separation factor

        # Procedural talk cycle generator
        self.is_talking = False
        self.talk_phase = 0.0

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

        # Dizzy state
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

        # Hop animation state
        self.is_dormant = False
        self.hop_stage = "IDLE"     # "IDLE", "JUMPING_OUT", "LANDING"
        self.hop_anim_t = 0.0
        self._on_jump_finished = None

    def set_emotion(self, emotion_name):
        if emotion_name in EMOTION_COLORS and self.emotion != emotion_name:
            self.emotion = emotion_name
            self.target_color = EMOTION_COLORS[emotion_name][0]
            self.target_pupil_color = EMOTION_COLORS[emotion_name][1]

    def update(self, face_detected, target_x_norm, target_y_norm, mouth_open=0.0):
        now = time.time()

        # 1. Talking / Lip-Sync Modulation
        # If external mouth_open > 0, drive talking jaw
        if mouth_open > 0.05:
            self.is_talking = True
            self.talk_phase += 0.35
            target_jaw = mouth_open
        else:
            self.is_talking = False
            target_jaw = 0.0

        self.cur_speech_open += (target_jaw - self.cur_speech_open) * 0.30

        # 2. Target Morph Targets for Mouth
        bw = float(self.base_mouth_w)
        bh = float(self.base_mouth_h)

        if self.emotion in ["SURPRISED", "DIZZY"]:
            tgt_w = bw * 0.45
            tgt_h = bh * 1.85
            tgt_oval = 1.0
            tgt_curve = 0.0
        elif self.emotion == "HAPPY":
            tgt_w = bw * 1.20
            tgt_h = bh * 1.10
            tgt_oval = 0.0
            tgt_curve = 1.0
        elif self.emotion in ["ANNOYED", "SAD"]:
            tgt_w = bw * 0.90
            tgt_h = bh * 0.90
            tgt_oval = 0.0
            tgt_curve = -1.0
        elif self.emotion == "SLEEPY":
            tgt_w = bw * 0.60
            tgt_h = 4.0
            tgt_oval = 0.0
            tgt_curve = 0.0
        else:
            # NEUTRAL & CURIOUS: classic cute "w" cat mouth
            tgt_w = bw * 0.85
            tgt_h = bh * 0.80
            tgt_oval = 0.0
            tgt_curve = 0.0

        # Smooth mouth dimension interpolation
        self.cur_m_w += (tgt_w - self.cur_m_w) * 0.18
        self.cur_m_h += (tgt_h - self.cur_m_h) * 0.18
        self.cur_oval_weight += (tgt_oval - self.cur_oval_weight) * 0.20
        self.cur_smile_curve += (tgt_curve - self.cur_smile_curve) * 0.20

        # 3. Color Interpolation
        for i in range(3):
            self.curr_color[i] += (self.target_color[i] - self.curr_color[i]) * 0.08
            self.curr_pupil_color[i] += (self.target_pupil_color[i] - self.curr_pupil_color[i]) * 0.08

        # 4. Target Morph Values for Eyes
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

        # 5. Gaze Physics
        if self.emotion == "DIZZY":
            self.dizzy_angle += 0.20
            self.target_x = 0.0
            self.target_y = 0.0
            self.pupil_scale += (0.85 - self.pupil_scale) * 0.1
        elif self.emotion == "SAD":
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

        ease = 0.25 if self.emotion == "DIZZY" else (0.08 if self.emotion == "SAD" else 0.18)
        self.curr_x += (self.target_x - self.curr_x) * ease
        self.curr_y += (self.target_y - self.curr_y) * ease

        # 6. Blinking
        if self.sleep_transition < 0.5 and self.emotion != "DIZZY":
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
                    self.blink_interval = 0.18 if random.random() < 0.25 else random.uniform(2.5, 6.0)
        else:
            self.is_blinking = False
            self.blink_progress = 0.0

        # 7. Corner Zzz Particles
        if self.emotion == "SLEEPY" and self.sleep_transition > 0.7:
            if now - self.last_zzz_spawn > 0.9:
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

        # 0. Check if completely dormant (blank screen)
        if getattr(self, 'is_dormant', False) and getattr(self, 'hop_stage', 'IDLE') == "IDLE":
            return

        # --- HOP / JUMP PHYSICS ENGINE ---
        hop_offset_y = 0.0
        hop_scale_x = 1.0
        hop_scale_y = 1.0

        hop_stage = getattr(self, 'hop_stage', 'IDLE')

        if hop_stage == "JUMPING_OUT":
            self.hop_anim_t += 0.05
            t = self.hop_anim_t

            if t < 0.25:
                # 1. Anticipation: Squish down, widen out
                p = t / 0.25
                hop_scale_y = 1.0 - (p * 0.45)
                hop_scale_x = 1.0 + (p * 0.35)
                hop_offset_y = p * 25.0
            elif t < 0.80:
                # 2. Launch: Stretch vertically and blast off the top
                flight_p = (t - 0.25) / 0.55
                hop_scale_y = 1.45
                hop_scale_x = 0.72
                hop_offset_y = 25.0 - (flight_p ** 2.2) * (self.height + 220)
            else:
                # 3. Finished jump
                self.hop_stage = "IDLE"
                self.is_dormant = True
                if hasattr(self, '_on_jump_finished') and self._on_jump_finished:
                    cb = self._on_jump_finished
                    self._on_jump_finished = None
                    cb()
                return

        elif hop_stage == "LANDING":
            self.hop_anim_t += 0.05
            t = self.hop_anim_t

            if t < 0.55:
                # 1. Fall: Plunge down from sky stretched tall
                fall_p = (0.55 - t) / 0.55
                hop_scale_y = 1.35
                hop_scale_x = 0.78
                hop_offset_y = -(fall_p ** 2) * (self.height + 150)
            elif t < 0.85:
                # 2. Impact: Deep squash on landing
                squash_p = (t - 0.55) / 0.30
                bounce = math.sin(squash_p * math.pi)
                hop_scale_y = 1.0 - (bounce * 0.40)
                hop_scale_x = 1.0 + (bounce * 0.35)
                hop_offset_y = bounce * 18.0
            else:
                # 3. Recover to normal
                self.hop_stage = "IDLE"

        # Apply deformation to eye dimensions & baseline Y
        active_eye_w = int(self.base_eye_w * self.eye_scale_x * hop_scale_x)
        active_eye_h = int(self.base_eye_h * self.eye_scale_y * hop_scale_y)
        active_rest_y = self.rest_y + hop_offset_y

        blink_factor = (1.0 - (self.blink_progress * 0.95)) * (1.0 - self.sleep_transition)
        current_h = max(4, int(active_eye_h * blink_factor))
        current_w = int(active_eye_w * (1.0 + (self.blink_progress * 0.08)))
        current_radius = min(self.eye_radius, current_h // 2)

        left_box = pygame.Rect(
            int(self.left_x + self.curr_x - current_w // 2),
            int(active_rest_y + self.curr_y - current_h // 2),
            current_w, current_h
        )
        right_box = pygame.Rect(
            int(self.right_x + self.curr_x - current_w // 2),
            int(active_rest_y + self.curr_y - current_h // 2),
            current_w, current_h
        )

        eye_color = tuple(int(c) for c in self.curr_color)
        pupil_color = tuple(int(c) for c in self.curr_pupil_color)

        # --- 1. EYES RENDERING ---
        if self.sleep_transition > 0.85:
            arc_w = int(self.base_eye_w * 0.82 * hop_scale_x)
            arc_h = int(self.base_eye_h * 0.42 * hop_scale_y)
            steps = 16

            for center_pos_x in [self.left_x, self.right_x]:
                pts = []
                for s in range(steps + 1):
                    theta = (math.pi * s) / steps
                    px = int(center_pos_x - (arc_w // 2) * math.cos(theta))
                    py = int(active_rest_y - 2 + (arc_h // 2) * math.sin(theta))
                    pts.append((px, py))

                pygame.draw.lines(self.surface, eye_color, False, pts, 7)
                pygame.draw.circle(self.surface, eye_color, pts[0], 3)
                pygame.draw.circle(self.surface, eye_color, pts[-1], 3)
        else:
            for i, box in enumerate([left_box, right_box]):
                is_left_eye = (i == 0)
                pygame.draw.rect(self.surface, eye_color, box, border_radius=current_radius)

                if current_h > 24:
                    pw = int(active_eye_w * 0.38 * self.pupil_scale)
                    ph = int(active_eye_h * 0.42 * self.pupil_scale * blink_factor)

                    if self.emotion == "DIZZY":
                        orbit_rx = self.base_eye_w * 0.16 * hop_scale_x
                        orbit_ry = self.base_eye_h * 0.20 * hop_scale_y
                        direction = 1 if is_left_eye else -1
                        p_offset_x = math.cos(self.dizzy_angle * direction) * orbit_rx
                        p_offset_y = math.sin(self.dizzy_angle * direction) * orbit_ry
                    else:
                        p_offset_x = self.curr_x * 0.45
                        p_offset_y = self.curr_y * 0.45

                    pupil_rect = pygame.Rect(
                        int(box.centerx + p_offset_x - pw // 2),
                        int(box.centery + p_offset_y - ph // 2),
                        pw, ph
                    )
                    pygame.draw.rect(self.surface, pupil_color, pupil_rect, border_radius=int(pw // 2))

                    base_hl_x = pupil_rect.centerx - int(pw * 0.22)
                    base_hl_y = pupil_rect.centery - int(ph * 0.22)

                    hl_x = base_hl_x + int(p_offset_x * 0.20)
                    hl_y = base_hl_y + int(p_offset_y * 0.20)
                    hl_size = max(2, int(pw * 0.22))

                    pygame.draw.circle(self.surface, HIGHLIGHT_COLOR, (hl_x, hl_y), hl_size)
                    sec_x = hl_x + int(hl_size * 1.3)
                    sec_y = hl_y + int(hl_size * 1.3)
                    pygame.draw.circle(self.surface, HIGHLIGHT_COLOR, (sec_x, sec_y), max(1, hl_size // 2))

                # Eyelid Clipping
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
                    pts = [
                        (box.left - 5, box.top - 5),
                        (box.right + 5, box.top - 5),
                        (box.right + 5 if is_left_eye else box.left - 5, box.top + slant_drop)
                    ]
                    pygame.draw.polygon(self.surface, BG_COLOR, pts)

                if self.sad_slant > 0.01:
                    slant_drop = int(box.height * 0.40 * self.sad_slant)
                    pts = [
                        (box.left - 5, box.top - 5),
                        (box.right + 5, box.top - 5),
                        (box.left - 5 if is_left_eye else box.right + 5, box.top + slant_drop)
                    ]
                    pygame.draw.polygon(self.surface, BG_COLOR, pts)

        # 2. Floating Zzz Rendering (only when not hopping)
        if hop_stage == "IDLE":
            for p in self.zzz_particles:
                surf = pygame.font.SysFont("dejavusans", p["size"], bold=True).render("Z", True, eye_color)
                surf.set_alpha(int(p["alpha"]))
                self.surface.blit(surf, (int(p["x"]), int(p["y"])))

        # --- 3. RESPONSIVE MORPH MOUTH RENDERING ---
        # Mouth tracks gaze and body jump motion
        mx = self.mouth_center_x + int(self.curr_x * 0.45)
        my = self.mouth_center_y + int(self.curr_y * 0.45) + int(hop_offset_y)

        # Subtle breath motion
        breath = math.sin(time.time() * 3.5) * 1.2
        my += int(breath)

        speech_gap = int(self.cur_speech_open * 16.0)

        if self.emotion == "DIZZY":
            mx += int(math.sin(self.dizzy_angle * 1.5) * 4.0)

        oval_factor = self.cur_oval_weight

        # Scaled mouth bounds by hop squash & stretch
        cur_w = max(4, int(self.cur_m_w * hop_scale_x))
        cur_h = max(2, int(self.cur_m_h * hop_scale_y))

        # Branch A: Standing Vertical Oval (Surprised / Dizzy)
        if oval_factor > 0.15:
            ow = int(cur_w + (speech_gap * 0.3))
            oh = int(cur_h + speech_gap)
            oval_rect = pygame.Rect(mx - ow // 2, my - oh // 2, ow, oh)
            pygame.draw.ellipse(self.surface, eye_color, oval_rect)

        # Branch B: Expressive Curves (Cat 'w', Smile Arc, Frown Arc, Sleeping Slit)
        if oval_factor < 0.85:
            mw = cur_w
            mh = cur_h
            line_thick = max(2, int(8 * hop_scale_y))

            # 1. HAPPY (Smile Arc)
            if self.cur_smile_curve > 0.35:
                arc_h = int(mh * 1.8 + speech_gap)
                r_box = pygame.Rect(mx - mw // 2, my - int(mh * 0.4), mw, arc_h)
                pygame.draw.arc(self.surface, eye_color, r_box, math.pi, 2 * math.pi, line_thick)

            # 2. ANNOYED / SAD (Frown Arc)
            elif self.cur_smile_curve < -0.35:
                arc_h = int(mh * 1.6 + speech_gap)
                r_box = pygame.Rect(mx - mw // 2, my + 2, mw, arc_h)
                pygame.draw.arc(self.surface, eye_color, r_box, 0, math.pi, line_thick)

            # 3. SLEEPY (Flat Slit)
            elif self.emotion == "SLEEPY" and self.sleep_transition > 0.6:
                flat_w = int(mw * 0.45)
                pygame.draw.line(self.surface, eye_color, (mx - flat_w, my), (mx + flat_w, my), line_thick)

            # 4. NEUTRAL & CURIOUS (Deep Cat "w" Mouth)
            else:
                r = int(mw * 0.28)
                curve_h = int(r * 1.2 + (speech_gap * 0.6))
                steps = 14

                for offset in [-r, r]:
                    cx = mx + offset
                    pts = []
                    for step in range(steps + 1):
                        theta = math.pi + (math.pi * step / steps)
                        px = int(cx + r * math.cos(theta))
                        py = int(my - 4 + curve_h * math.sin(theta))
                        pts.append((px, py))

                    pygame.draw.lines(self.surface, eye_color, False, pts, line_thick)
                    for px, py in [pts[0], pts[-1]]:
                        pygame.draw.circle(self.surface, eye_color, (px, py), line_thick // 2)

    # hop animation methods
    def start_jump_out(self, on_finished=None):
        self.hop_stage = "JUMPING_OUT"
        self.hop_anim_t = 0.0
        self._on_jump_finished = on_finished

    def start_landing(self):
        self.is_dormant = False
        self.hop_stage = "LANDING"
        self.hop_anim_t = 0.0