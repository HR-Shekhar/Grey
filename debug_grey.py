import sys
import time
import pygame
from config import FPS, DEFAULT_WIDTH, DEFAULT_HEIGHT
from vision import GreyVision
from renderer import EyeRenderer

def main():
    pygame.init()
    pygame.font.init()
    debug_font = pygame.font.SysFont("monospace", 14, bold=True)

    display_info = pygame.display.Info()
    width = display_info.current_w or DEFAULT_WIDTH
    height = display_info.current_h or DEFAULT_HEIGHT

    screen = pygame.display.set_mode((width, height), pygame.FULLSCREEN | pygame.NOFRAME)
    pygame.display.set_caption("Grey Debugger")
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()

    renderer = EyeRenderer(screen, width, height)
    vision = GreyVision()
    vision.start()

    # Behavior & Timing State
    last_seen_time = time.time()
    lost_face_time = 0.0
    face_was_detected = False
    steady_start_time = 0.0
    manual_override_until = 0.0
    dizzy_lock_until = 0.0

    current_state = "NEUTRAL"

    key_map = {
        pygame.K_1: "NEUTRAL", pygame.K_2: "HAPPY", pygame.K_3: "CURIOUS",
        pygame.K_4: "SURPRISED", pygame.K_5: "SLEEPY", pygame.K_6: "ANNOYED",
        pygame.K_7: "SAD", pygame.K_8: "DIZZY"
    }

    def switch_emotion(new_emotion, reason):
        nonlocal current_state
        if current_state != new_emotion:
            current_state = new_emotion
            renderer.set_emotion(new_emotion)
            print(f"[{time.strftime('%H:%M:%S')}] TRIGGER -> {new_emotion:<9} | Reason: {reason}")

    print("\n==============================================")
    print("       GREY TRIGGER DIAGNOSTIC CONSOLE        ")
    print("==============================================")
    print("Press ESC to exit.")
    print("Press 1-8 to manually lock an emotion for 6s.\n")

    running = True
    try:
        while running:
            clock.tick(FPS)
            now = time.time()

            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
                elif event.type == pygame.KEYDOWN and event.key in key_map:
                    forced = key_map[event.key]
                    manual_override_until = now + 6.0
                    switch_emotion(forced, f"Manual Keypress ({pygame.key.name(event.key)})")

            # --- Behavioral Logic Engine ---
            if now > manual_override_until:
                if now < dizzy_lock_until:
                    pass  # Retain dizzy state for lock duration
                elif vision.face_detected:
                    last_seen_time = now

                    # 1. Edge Trigger: Initial sight or rapid lunge
                    if not face_was_detected:
                        switch_emotion("SURPRISED", "New face acquired in frame")
                        steady_start_time = now
                    elif vision.area_delta > 0.08:
                        switch_emotion("SURPRISED", f"Rapid approach surge (area_delta={vision.area_delta:.2f})")
                        steady_start_time = now

                    # 2. DIZZY: Rapid sweeps
                    elif vision.sweep_count >= 4:
                        dizzy_lock_until = now + 4.0
                        switch_emotion("DIZZY", f"Sweep count threshold reached ({vision.sweep_count})")

                    # 3. ANNOYED: Erratic speed or twitching
                    elif vision.speed > 0.55 or vision.sweep_count >= 2:
                        switch_emotion("ANNOYED", f"High motion instability (speed={vision.speed:.2f}, sweeps={vision.sweep_count})")
                        steady_start_time = now

                    # 4. CURIOUS: Head tilt or close-up stationary inspect
                    elif vision.head_tilt > 18.0:
                        switch_emotion("CURIOUS", f"Head tilt detected ({vision.head_tilt:.1f} deg)")
                    elif vision.face_area > 0.35 and vision.speed < 0.15:
                        switch_emotion("CURIOUS", f"Close stationary inspection (area={vision.face_area:.2f})")

                    # 5. HAPPY: Calm stability
                    elif now - steady_start_time > 1.5 and vision.speed < 0.25:
                        switch_emotion("HAPPY", "Calm presence detected (> 1.5s)")

                    face_was_detected = True

                else:
                    # When face departs
                    if face_was_detected:
                        lost_face_time = now
                        face_was_detected = False

                    time_alone = now - last_seen_time

                    # 6. SAD: Brief abandonment reaction
                    if time_alone < 4.5 and lost_face_time > 0:
                        switch_emotion("SAD", f"Target lost (grieving: {4.5 - time_alone:.1f}s remaining)")

                    # 7. SLEEPY: Inactivity
                    elif time_alone > 18.0:
                        switch_emotion("SLEEPY", f"Extended solitude ({time_alone:.1f}s without face)")

                    # 8. NEUTRAL: Solitary idle
                    else:
                        switch_emotion("NEUTRAL", f"Idle timeout ({time_alone:.1f}s alone)")

            # Render Scene
            renderer.update(vision.face_detected, vision.target_x, vision.target_y)
            renderer.draw()

            # --- On-Screen Debug HUD ---
            time_alone = max(0.0, now - last_seen_time)
            hud_lines = [
                f"STATE     : {renderer.emotion} {'[MANUAL]' if now <= manual_override_until else ''}",
                f"DETECTED  : {vision.face_detected}",
                f"AREA/D_A  : {vision.face_area:.2f} / {vision.area_delta:+.2f}",
                f"SPEED     : {vision.speed:.2f}",
                f"SWEEPS    : {vision.sweep_count}",
                f"HEAD TILT : {vision.head_tilt:.1f} deg",
                f"TIME ALONE: {time_alone:.1f}s",
            ]

            for i, line in enumerate(hud_lines):
                txt_surf = debug_font.render(line, True, (0, 255, 120))
                screen.blit(txt_surf, (8, 8 + (i * 16)))

            pygame.display.flip()

    finally:
        vision.stop()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()