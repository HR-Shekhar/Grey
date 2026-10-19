import sys
import time
import pygame
from config import FPS, DEFAULT_WIDTH, DEFAULT_HEIGHT
from vision import GreyVision
from renderer import EyeRenderer

def main():
    pygame.init()
    display_info = pygame.display.Info()
    width = display_info.current_w or DEFAULT_WIDTH
    height = display_info.current_h or DEFAULT_HEIGHT

    screen = pygame.display.set_mode((width, height), pygame.FULLSCREEN | pygame.NOFRAME)
    pygame.display.set_caption("Grey")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    renderer = EyeRenderer(screen, width, height)
    vision = GreyVision()
    vision.start()

    # Behavioral State Tracking
    last_seen_time = time.time()
    lost_face_time = 0.0
    face_was_detected = False
    face_acquired_time = 0.0
    steady_start_time = 0.0

    # Rapid camera cover/uncover (occlusion) tracking
    occlusion_flaps = 0
    occlusion_window_start = time.time()

    manual_override_until = 0.0
    dizzy_lock_until = 0.0
    annoyed_lock_until = 0.0

    mapping = {
        pygame.K_1: "NEUTRAL", pygame.K_2: "HAPPY", pygame.K_3: "CURIOUS",
        pygame.K_4: "SURPRISED", pygame.K_5: "SLEEPY", pygame.K_6: "ANNOYED",
        pygame.K_7: "SAD", pygame.K_8: "DIZZY"
    }

    running = True
    try:
        while running:
            clock.tick(FPS)
            now = time.time()

            # Reset rapid occlusion window every 3.0 seconds
            if now - occlusion_window_start > 3.0:
                occlusion_flaps = 0
                occlusion_window_start = now

            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
                elif event.type == pygame.KEYDOWN and event.key in mapping:
                    renderer.set_emotion(mapping[event.key])
                    manual_override_until = now + 6.0

            # --- Behavioral Emotion Engine ---
            if now > manual_override_until:
                if now < dizzy_lock_until or now < annoyed_lock_until:
                    # Hold locked states for their full duration
                    pass

                elif vision.face_detected:
                    last_seen_time = now

                    # Newly appeared face
                    if not face_was_detected:
                        occlusion_flaps += 1
                        face_was_detected = True
                        face_acquired_time = now
                        steady_start_time = now

                        # Rapidly covering and uncovering the camera triggers ANNOYED
                        if occlusion_flaps >= 3:
                            renderer.set_emotion("ANNOYED")
                            annoyed_lock_until = now + 4.0
                            occlusion_flaps = 0
                        else:
                            renderer.set_emotion("SURPRISED")

                    else:
                        time_since_acquired = now - face_acquired_time

                        # 1. DIZZY: 3 side-to-side directional sweeps within 3 seconds
                        if vision.sweep_count >= 3:
                            renderer.set_emotion("DIZZY")
                            dizzy_lock_until = now + 4.5
                            vision.sweep_count = 0

                        # 2. Sudden proximity surge (lunging towards camera)
                        elif vision.area_delta > 0.09:
                            renderer.set_emotion("SURPRISED")
                            steady_start_time = now

                        # 3. ANNOYED: Erratic hand-waving / chaotic speed in front of face
                        elif time_since_acquired > 0.8 and (vision.speed > 0.65 or vision.sweep_count >= 2):
                            renderer.set_emotion("ANNOYED")
                            annoyed_lock_until = now + 3.5
                            steady_start_time = now

                        # 4. CURIOUS: Head tilt (>18 deg) or close-up calm look
                        elif vision.head_tilt > 18.0 or (vision.face_area > 0.35 and vision.speed < 0.15):
                            renderer.set_emotion("CURIOUS")

                        # 5. HAPPY: Calm presence for > 1.5s
                        elif now - steady_start_time > 1.5 and vision.speed < 0.25:
                            renderer.set_emotion("HAPPY")

                else:
                    # When face disappears
                    if face_was_detected:
                        lost_face_time = now
                        face_was_detected = False

                    time_alone = now - last_seen_time

                    # 1.5s delay before SAD triggers
                    if time_alone < 1.5:
                        renderer.set_emotion("NEUTRAL")  # Brief paused search
                    elif time_alone < 6.0:               # 1.5s to 6.0s (4.5s duration)
                        renderer.set_emotion("SAD")
                    elif time_alone > 18.0:
                        renderer.set_emotion("SLEEPY")
                    else:
                        renderer.set_emotion("NEUTRAL")

            renderer.update(vision.face_detected, vision.target_x, vision.target_y)
            renderer.draw()
            pygame.display.flip()

    finally:
        vision.stop()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()