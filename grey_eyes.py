import sys
import time
import pygame
from config import FPS, DEFAULT_WIDTH, DEFAULT_HEIGHT
from vision import GreyVision
from renderer import EyeRenderer
from audio import GreyVoice
from net_hop import GreyNetworkNode
from wake_listener import UnifiedAudioListener

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

    voice = GreyVoice()

    # --- Device Configuration ---
    DEVICE_ID = "pi_device_1"
    START_ACTIVE = True

    renderer.is_dormant = not START_ACTIVE

    def on_received_hop():
        print("[Grey Network] Inbound hop detected! Waking up...")
        renderer.start_landing()
        voice.speak("HAPPY")

    net = GreyNetworkNode(device_id=DEVICE_ID, is_active=START_ACTIVE, on_hop_in=on_received_hop)
    net.start()

    # --- Unified Audio Callbacks ---
    def handle_wake():
        if net.is_active and not renderer.is_dormant:
            renderer.set_emotion("CURIOUS")
            voice.speak("CURIOUS")

    def handle_hop():
        if net.is_active and not renderer.is_dormant:
            print("[Grey Command] Executing hop out sequence...")
            voice.speak("SURPRISED")
            renderer.start_jump_out(on_finished=lambda: net.send_hop())

    # Single microphone instance handling both wake-words and voice chatter
    listener = UnifiedAudioListener(
        model_path="model",
        on_wake=handle_wake,
        on_hop=handle_hop,
        energy_threshold=0.035,
        silence_duration=0.6
    )
    listener.start()

    # Behavioral State Tracking
    last_seen_time = time.time()
    lost_face_time = 0.0
    face_was_detected = False
    face_acquired_time = 0.0
    steady_start_time = 0.0

    occlusion_flaps = 0
    occlusion_window_start = time.time()

    manual_override_until = 0.0
    dizzy_lock_until = 0.0
    annoyed_lock_until = 0.0

    current_emotion = "NEUTRAL"

    def transition_to(new_emotion):
        nonlocal current_emotion
        if new_emotion != current_emotion:
            current_emotion = new_emotion
            renderer.set_emotion(new_emotion)
            voice.speak(new_emotion)

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

            if now - occlusion_window_start > 3.0:
                occlusion_flaps = 0
                occlusion_window_start = now

            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in mapping:
                        forced = mapping[event.key]
                        transition_to(forced)
                        manual_override_until = now + 6.0
                    elif event.key == pygame.K_h:
                        handle_hop()
                    elif event.key == pygame.K_j:
                        renderer.start_landing()
                        net.is_active = True

            # If dormant and settled, render blank frame and skip compute
            if not net.is_active and getattr(renderer, 'hop_stage', 'IDLE') == "IDLE":
                renderer.draw()
                pygame.display.flip()
                continue

            # Conversational chatter trigger
            if listener.has_spoken() and renderer.emotion != "SLEEPY" and not voice.is_speaking and listener.state != "WAITING_COMMAND":
                renderer.set_emotion("CURIOUS")
                current_emotion = "CURIOUS"
                voice.speak("GIBBERISH")

            # Behavioral Emotion Engine
            if now > manual_override_until:
                if now < dizzy_lock_until or now < annoyed_lock_until:
                    pass

                elif vision.face_detected:
                    last_seen_time = now

                    if not face_was_detected:
                        occlusion_flaps += 1
                        face_was_detected = True
                        face_acquired_time = now
                        steady_start_time = now

                        if occlusion_flaps >= 3:
                            transition_to("ANNOYED")
                            annoyed_lock_until = now + 4.0
                            occlusion_flaps = 0
                        else:
                            transition_to("SURPRISED")

                    else:
                        time_since_acquired = now - face_acquired_time

                        if vision.sweep_count >= 3:
                            transition_to("DIZZY")
                            dizzy_lock_until = now + 4.5
                            vision.sweep_count = 0

                        elif vision.area_delta > 0.09:
                            transition_to("SURPRISED")
                            steady_start_time = now

                        elif time_since_acquired > 0.8 and (vision.speed > 0.65 or vision.sweep_count >= 2):
                            transition_to("ANNOYED")
                            annoyed_lock_until = now + 3.5
                            steady_start_time = now

                        elif vision.head_tilt > 18.0 or (vision.face_area > 0.35 and vision.speed < 0.15):
                            transition_to("CURIOUS")

                        elif now - steady_start_time > 1.5 and vision.speed < 0.25:
                            if not voice.is_speaking:
                                transition_to("HAPPY")

                else:
                    if face_was_detected:
                        lost_face_time = now
                        face_was_detected = False

                    time_alone = now - last_seen_time

                    if time_alone < 1.5:
                        transition_to("NEUTRAL")
                    elif time_alone < 6.0:
                        transition_to("SAD")
                    elif time_alone > 18.0:
                        transition_to("SLEEPY")
                    else:
                        transition_to("NEUTRAL")

            lip_sync = voice.get_lip_sync_scale()
            renderer.update(vision.face_detected, vision.target_x, vision.target_y, mouth_open=lip_sync)
            renderer.draw()
            pygame.display.flip()

    finally:
        listener.stop()
        net.stop()
        vision.stop()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()