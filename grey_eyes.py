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

    last_seen_time = time.time()
    last_state = False

    # Manual override control
    manual_override_until = 0.0

    mapping = {
        pygame.K_1: "NEUTRAL",
        pygame.K_2: "HAPPY",
        pygame.K_3: "CURIOUS",
        pygame.K_4: "SURPRISED",
        pygame.K_5: "SLEEPY",
        pygame.K_6: "ANNOYED",
        pygame.K_7: "SAD",
        pygame.K_8: "DIZZY",
    }

    print("\n--- Key Controls Active ---")
    print("Click on the Grey screen once, then press 1-8 to test emotions.")
    print("Manual emotions will hold for 6 seconds before returning to auto-mode.\n")

    running = True
    try:
        while running:
            clock.tick(FPS)
            now = time.time()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in mapping:
                        chosen_emotion = mapping[event.key]
                        renderer.set_emotion(chosen_emotion)
                        manual_override_until = now + 6.0  # Hold for 6 seconds
                        print(f"[Manual Trigger] Forced emotion -> {chosen_emotion} (locked for 6s)")

            # --- Autonomous Brain (ONLY runs when not in manual override) ---
            if now > manual_override_until:
                if vision.face_detected:
                    if not last_state:
                        renderer.set_emotion("SURPRISED")
                        last_seen_time = now
                    elif now - last_seen_time > 1.2:
                        renderer.set_emotion("HAPPY")
                    last_state = True
                else:
                    last_state = False
                    time_alone = now - last_seen_time
                    if time_alone > 16.0:
                        renderer.set_emotion("SLEEPY")
                    elif time_alone > 3.0:
                        renderer.set_emotion("NEUTRAL")

            # Update and Draw
            renderer.update(vision.face_detected, vision.target_x, vision.target_y)
            renderer.draw()
            pygame.display.flip()

    finally:
        vision.stop()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()