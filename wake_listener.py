import json
import queue
import time
import threading
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer

class UnifiedAudioListener(threading.Thread):
    """
    Single unified microphone stream that handles both:
    1. Wake-word / command detection ('grey', 'hop') via Vosk.
    2. Voice activity detection (user finished talking) for conversational replies.
    """
    def __init__(self, model_path="model", on_wake=None, on_hop=None, energy_threshold=0.035, silence_duration=0.6):
        super().__init__(daemon=True)
        self.on_wake = on_wake
        self.on_hop = on_hop
        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration

        self.running = True
        self.audio_q = queue.Queue()
        self.user_just_spoke = False

        self._is_talking = False
        self._last_voice_time = 0.0

        print("[AudioListener] Loading Vosk model...")
        self.model = Model(model_path)
        grammar = '["grey", "hop", "[unk]"]'
        self.rec = KaldiRecognizer(self.model, 16000, grammar)

        self.state = "WAITING_WAKE"
        self.command_timeout = 0.0

    def run(self):
        sample_rate = 16000
        block_size = 4000

        def callback(indata, frames, time_info, status):
            if not self.running:
                return

            raw_bytes = bytes(indata)
            self.audio_q.put(raw_bytes)

            # Compute RMS energy from the raw int16 buffer
            audio_data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            rms = np.sqrt(np.mean(audio_data ** 2)) if len(audio_data) > 0 else 0.0
            now = time.time()

            if rms > self.energy_threshold:
                self._is_talking = True
                self._last_voice_time = now
            else:
                if self._is_talking and (now - self._last_voice_time > self.silence_duration):
                    self._is_talking = False
                    self.user_just_spoke = True

        try:
            with sd.RawInputStream(samplerate=sample_rate, blocksize=block_size, dtype='int16',
                                   channels=1, callback=callback):
                print("[AudioListener] Unified audio stream active.")
                while self.running:
                    try:
                        data = self.audio_q.get(timeout=0.1)
                    except queue.Empty:
                        continue

                    now = time.time()
                    if self.state == "WAITING_COMMAND" and now > self.command_timeout:
                        print("[AudioListener] Command window expired. Returning to wake listening.")
                        self.state = "WAITING_WAKE"

                    if self.rec.AcceptWaveform(data):
                        res = json.loads(self.rec.Result())
                        text = res.get("text", "")

                        if "grey" in text:
                            print("[AudioListener] Heard wake-word: 'GREY'!")
                            self.state = "WAITING_COMMAND"
                            self.command_timeout = now + 4.5
                            if self.on_wake:
                                self.on_wake()

                        elif "hop" in text:
                            if self.state == "WAITING_COMMAND":
                                print("[AudioListener] Heard command: 'HOP'!")
                                self.state = "WAITING_WAKE"
                                if self.on_hop:
                                    self.on_hop()
                            else:
                                print("[AudioListener] Ignored 'hop' (not preceded by 'grey').")

        except Exception as e:
            print(f"[AudioListener] Error opening microphone stream: {e}")

    def has_spoken(self):
        if self.user_just_spoke:
            self.user_just_spoke = False
            return True
        return False

    def stop(self):
        self.running = False