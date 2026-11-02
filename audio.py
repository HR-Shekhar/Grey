import math
import time
import random
import threading
import pygame
import numpy as np
import sounddevice as sd

class GreyVoice:
    def __init__(self, sample_rate=22050):
        self.sample_rate = sample_rate
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=2, buffer=512)
        except Exception as e:
            print(f"[Grey Voice] Warning: Audio init failed ({e})")

        self.is_speaking = False
        self.sound_start_time = 0.0
        self.sound_duration = 0.0

        # Formant frequencies [F1, F2] in Hz
        self.vowels = {
            'a': (800, 1200),
            'i': (280, 2250),
            'u': (320, 800),
            'e': (500, 1800),
            'o': (500, 950),
        }

        self.sound_bank = {
            "HAPPY": self._voice_happy,
            "SURPRISED": self._voice_surprised,
            "CURIOUS": self._voice_curious,
            "ANNOYED": self._voice_annoyed,
            "SAD": self._voice_sad,
            "DIZZY": self._voice_dizzy,
            "SLEEPY": self._voice_sleepy,
        }

    def _vocal_syllable(self, pitch_start, pitch_end, duration, vowel='u', consonant='p'):
        n_samples = int(self.sample_rate * duration)
        if n_samples <= 0:
            return np.zeros(0, dtype=np.float32)

        t = np.linspace(0, duration, n_samples, endpoint=False)
        pitch_curve = np.linspace(pitch_start, pitch_end, n_samples)
        pitch_curve += np.sin(2 * np.pi * 6.0 * t) * (pitch_start * 0.03)

        phase = 2 * np.pi * np.cumsum(pitch_curve) / self.sample_rate
        glottal = np.sin(phase) + 0.45 * np.sin(2 * phase) + 0.15 * np.sin(3 * phase)

        f1, f2 = self.vowels.get(vowel, (400, 1200))
        vocal_body = glottal * (0.6 + 0.25 * np.sin(2 * np.pi * f1 * t) + 0.15 * np.sin(2 * np.pi * f2 * t))

        if consonant in ['p', 'b', 't', 'k', 'm']:
            burst_len = min(int(self.sample_rate * 0.015), n_samples)
            burst = np.random.uniform(-0.4, 0.4, burst_len) * np.linspace(1, 0, burst_len)
            vocal_body[:burst_len] += burst

        attack = int(n_samples * 0.12)
        decay = int(n_samples * 0.35)
        envelope = np.ones(n_samples, dtype=np.float32)
        if attack > 0:
            envelope[:attack] = (1 - np.cos(np.linspace(0, np.pi, attack))) * 0.5
        if decay > 0:
            envelope[-decay:] = (1 + np.cos(np.linspace(0, np.pi, decay))) * 0.5

        return (vocal_body * envelope * 0.48).astype(np.float32)

    def _synth_gibberish(self):
        """Constructs a randomized, expressive creature word with 2 to 4 syllables."""
        num_syllables = random.randint(2, 4)
        vowel_pool = ['a', 'i', 'u', 'e', 'o']
        consonant_pool = ['p', 'b', 't', 'k', 'm', 'w']
        chunks = []

        base_pitch = random.randint(380, 520)

        for i in range(num_syllables):
            p_start = base_pitch + random.randint(-40, 60)
            # Raise pitch on the final syllable for an inquisitive tone
            p_end = p_start + (random.randint(60, 180) if i == num_syllables - 1 else random.randint(-60, 60))
            dur = random.uniform(0.08, 0.16)
            syl = self._vocal_syllable(
                p_start, p_end, dur,
                vowel=random.choice(vowel_pool),
                consonant=random.choice(consonant_pool)
            )
            chunks.append(syl)
            gap = np.zeros(int(self.sample_rate * random.uniform(0.02, 0.04)), dtype=np.float32)
            chunks.append(gap)
            base_pitch = p_end

        return np.concatenate(chunks)

    def _voice_happy(self):
        s1 = self._vocal_syllable(440, 580, 0.09, vowel='i', consonant='p')
        gap = np.zeros(int(self.sample_rate * 0.03), dtype=np.float32)
        s2 = self._vocal_syllable(580, 880, 0.16, vowel='a', consonant='k')
        return np.concatenate([s1, gap, s2])

    def _voice_surprised(self):
        return self._vocal_syllable(380, 780, 0.13, vowel='o', consonant='w')

    def _voice_curious(self):
        s1 = self._vocal_syllable(400, 480, 0.08, vowel='u', consonant='m')
        gap = np.zeros(int(self.sample_rate * 0.02), dtype=np.float32)
        s2 = self._vocal_syllable(480, 680, 0.14, vowel='i', consonant='p')
        return np.concatenate([s1, gap, s2])

    def _voice_annoyed(self):
        return self._vocal_syllable(260, 190, 0.18, vowel='u', consonant='b')

    def _voice_sad(self):
        return self._vocal_syllable(390, 240, 0.36, vowel='u', consonant='w')

    def _voice_dizzy(self):
        s1 = self._vocal_syllable(480, 380, 0.11, vowel='a', consonant='w')
        s2 = self._vocal_syllable(380, 460, 0.11, vowel='o', consonant='w')
        s3 = self._vocal_syllable(460, 320, 0.14, vowel='u', consonant='w')
        return np.concatenate([s1, s2, s3])

    def _voice_sleepy(self):
        return self._vocal_syllable(280, 200, 0.42, vowel='o', consonant='h')

    def speak(self, emotion):
        if self.is_speaking:
            return

        def _play_thread():
            try:
                if emotion == "GIBBERISH":
                    wave_data = self._synth_gibberish()
                elif emotion in self.sound_bank:
                    wave_data = self.sound_bank[emotion]()
                else:
                    return

                pcm_data = (wave_data * 32767).astype(np.int16)
                mixer_init = pygame.mixer.get_init()
                channels = mixer_init[2] if mixer_init else 2

                if channels == 2:
                    stereo_pcm = np.column_stack((pcm_data, pcm_data))
                    sound = pygame.sndarray.make_sound(stereo_pcm)
                else:
                    sound = pygame.sndarray.make_sound(pcm_data)

                self.sound_duration = len(wave_data) / self.sample_rate
                self.sound_start_time = time.time()
                self.is_speaking = True
                sound.play()

                time.sleep(self.sound_duration)
                self.is_speaking = False
            except Exception as e:
                self.is_speaking = False
                print(f"[Grey Voice] Playback error: {e}")

        threading.Thread(target=_play_thread, daemon=True).start()

    def get_lip_sync_scale(self):
        if not self.is_speaking:
            return 0.0

        elapsed = time.time() - self.sound_start_time
        if elapsed > self.sound_duration:
            self.is_speaking = False
            return 0.0

        flap = (math.sin(elapsed * 2.0 * math.pi * 14.0) + 1.0) / 2.0
        return max(0.0, min(1.0, flap))


class MicListener(threading.Thread):
    """Listens to the webcam mic and flags when the user finishes speaking."""
    def __init__(self, energy_threshold=0.035, silence_duration=0.55):
        super().__init__(daemon=True)
        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration
        self.running = True
        self.user_just_spoke = False

        self._is_talking = False
        self._last_voice_time = 0.0

    def run(self):
        block_size = 1024
        sample_rate = 16000

        def audio_callback(indata, frames, time_info, status):
            if not self.running:
                return

            # Calculate RMS energy of current audio buffer
            rms = np.sqrt(np.mean(indata**2))
            now = time.time()

            if rms > self.energy_threshold:
                self._is_talking = True
                self._last_voice_time = now
            else:
                if self._is_talking and (now - self._last_voice_time > self.silence_duration):
                    # User was speaking and has now paused
                    self._is_talking = False
                    self.user_just_spoke = True

        try:
            with sd.InputStream(channels=1, samplerate=sample_rate, blocksize=block_size, callback=audio_callback):
                print("[Grey Mic] Microphone listener active.")
                while self.running:
                    time.sleep(0.05)
        except Exception as e:
            print(f"[Grey Mic] Warning: Could not open default input device ({e})")

    def has_spoken(self):
        if self.user_just_spoke:
            self.user_just_spoke = False
            return True
        return False

    def stop(self):
        self.running = False