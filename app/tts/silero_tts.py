import torch
import soundfile as sf
import io

class SileroTTS:
    def __init__(self, sample_rate=48000, speaker='baya'):
        self.device = torch.device('cpu')
        self.sample_rate = sample_rate
        self.speaker = speaker
        self.model, self.example_text = torch.hub.load(
            repo_or_dir='snakers4/silero-models',
            model='silero_tts',
            language='ru',
            speaker='v3_1_ru'
        )

    def generate_audio(self, text):
        audio_array = self.model.apply_tts(
            text=text,
            speaker=self.speaker,
            sample_rate=self.sample_rate
        ).numpy()

        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_array, self.sample_rate, format='WAV')
        audio_buffer.seek(0)

        return audio_buffer